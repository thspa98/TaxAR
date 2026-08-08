#!/usr/bin/env python3
"""
ingesta_cordoba.py — Ingesta de datos fiscales de la Provincia de Córdoba.

Lee DOS fuentes complementarias y las carga marcando correctamente el
universo institucional y el tipo de dato (ver notas de comparabilidad
en 01_schema.sql):

  A) presupuesto_provincial_-_cordoba_1.xls  (consolidado MECON)
     - EN MILLONES de $ARS
     - 17 hojas: una por año, 2010..2026 -> serie histórica completa
     - col(1) = Administración Central  -> universo 'central'
     - col(5) = TOTAL Adm. Pública No Financiera -> universo 'apnf'
     - Es PRESUPUESTO (aprobado por ley), no ejecutado

  B) 04.0-Erogaciones-por-Finalidad-y-Objeto-del-Gasto...pdf
     - EN PESOS (se normaliza a millones al cargar)
     - Clasificación FUNCIONAL (Salud, Educación, Seguridad...)
     - Solo Administración General Centralizada -> universo 'central'
     - Es PRESUPUESTO

USO:
    export DATABASE_URL="postgresql://..."
    python ingesta_cordoba.py --xls presupuesto_provincial_-_cordoba_1.xls \\
        --pdf-funcional 04.0-Erogaciones-por-Finalidad-y-Objeto-del-Gasto-Todas-las-fuentes.pdf \\
        --anio 2026
"""

import argparse
import os
import re
import sys
from datetime import date

import psycopg2
import xlrd
import pdfplumber

JURISDICCION = {"nombre": "Córdoba", "slug": "cordoba", "nivel": "provincial",
                "codigo_indec": "14", "region_indec": "Pampeana"}

# ------------------------------------------------------------------
# A) Mapeo del esquema Ahorro-Inversión-Financiamiento (xls MECON)
#    etiqueta en la hoja -> slug canónico (clasificación económica)
# ------------------------------------------------------------------
MAPEO_AIF = {
    # Ingresos
    "impuestos provinciales":            "ing-prov-impuestos-propios",
    "impuestos nacionales":              "ing-prov-coparticipacion",
    "contribuciones de la seguridad social": "ing-trib-seg-social",
    "ingresos no impositivos":           "ing-notrib-general",
    "vta.bienes y serv.de la adm.publ.": "ing-notrib-otros",
    "rentas de la propiedad":            "ing-notrib-rentas",
    "transferencias corrientes":         "ing-prov-transf-corrientes",
    # Gastos
    "personal":                          "gas-remuneraciones",
    "bienes y servicios":                "gas-bienes-servicios",
    "prestaciones de la seguridad social": "gas-prest-jubilaciones",
    "al sector privado":                 "gas-transf-privado",
    "a municipios":                      "gas-transf-municipios",
    "inversión real directa":            "gas-capital",
}

# Filas del AIF que son KPIs headline (no categorías de detalle)
FILAS_HEADLINE = {
    "vi. ingresos totales":            "ingresos_totales",
    "vii. gastos totales":             "gastos_totales",
    "viii. gasto primario":            "gastos_primarios",
    "xii.resultado primario":          "resultado_primario",
    "xiii. resultado financiero":      "resultado_financiero",
}

# ------------------------------------------------------------------
# B) Mapeo de la clasificación FUNCIONAL (pdf Planilla 04)
# ------------------------------------------------------------------
MAPEO_FUNCIONAL = {
    "1-administración gubernamental":     "fun-administracion",
    "2-servicios de seguridad y justicia": "fun-seguridad",
    "3-servicios sociales":                "fun-sociales",
    "4-servicios económicos":              "fun-economicos",
    "5-deuda pública":                     "fun-deuda",
    "6-a clasificar":                      "fun-a-clasificar",
    # nivel 2 dentro de Servicios Sociales
    "1-salud":                             "fun-soc-salud",
    "4-educación y cultura":               "fun-soc-educacion",
    "2-promoción y asistencia social":     "fun-soc-promocion",
    # nivel 2 dentro de Seguridad
    "1-seguridad interior":                "fun-seg-interior",
    "2-sistema penal":                     "fun-seg-penal",
    "4-justicia":                          "fun-seg-justicia",
}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower().lstrip(". "))


def parse_num_es(s: str) -> float:
    """'1.234.567.000' -> 1234567000.0 ; maneja negativos."""
    s = s.strip()
    neg = s.startswith("-")
    s = s.lstrip("-").replace(".", "")
    if not s or not s.isdigit():
        raise ValueError(f"no numérico: {s!r}")
    v = float(s)
    return -v if neg else v


# ---------------- helpers de base ----------------

def get_or_create_jurisdiccion(cur):
    cur.execute("SELECT id FROM jurisdicciones WHERE slug=%s", (JURISDICCION["slug"],))
    r = cur.fetchone()
    if r:
        return r[0]
    cur.execute(
        """INSERT INTO jurisdicciones (nombre, slug, nivel, codigo_indec, region_indec)
           VALUES (%s,%s,%s,%s,%s) RETURNING id""",
        (JURISDICCION["nombre"], JURISDICCION["slug"], JURISDICCION["nivel"],
         JURISDICCION["codigo_indec"], JURISDICCION["region_indec"]))
    return cur.fetchone()[0]


def get_or_create_periodo_anual(cur, anio):
    cur.execute("SELECT id FROM periodos WHERE anio=%s AND mes IS NULL AND tipo='anual'", (anio,))
    r = cur.fetchone()
    if r:
        return r[0]
    cur.execute("""INSERT INTO periodos (anio, mes, tipo, fecha_inicio, fecha_fin)
                   VALUES (%s, NULL, 'anual', %s, %s) RETURNING id""",
                (anio, date(anio,1,1), date(anio,12,31)))
    return cur.fetchone()[0]


def get_or_create_fuente(cur, jur_id, nombre, url, tipo_archivo):
    cur.execute("SELECT id FROM fuentes WHERE url=%s AND nombre=%s", (url, nombre))
    r = cur.fetchone()
    if r:
        return r[0]
    cur.execute("""INSERT INTO fuentes (jurisdiccion_id, nombre, organismo, url,
                                        tipo_archivo, frecuencia_actualizacion, ultima_revision)
                   VALUES (%s,%s,%s,%s,%s,'anual',CURRENT_DATE) RETURNING id""",
                (jur_id, nombre, "Ministerio de Economía y Gestión Pública de Córdoba",
                 url, tipo_archivo))
    return cur.fetchone()[0]


def cat_id(cur, slug):
    cur.execute("SELECT id FROM categorias WHERE slug=%s", (slug,))
    r = cur.fetchone()
    if not r:
        raise ValueError(f"categoría canónica inexistente: {slug}")
    return r[0]


def upsert_hecho(cur, jur_id, per_id, categoria_id, monto_millones, universo,
                 tipo_dato, unidad_origen, raw, fuente_id):
    cur.execute("""
        INSERT INTO hechos_fiscales
            (jurisdiccion_id, periodo_id, categoria_id, monto, universo,
             tipo_dato, base_contable, unidad_origen, categoria_raw_original, fuente_id)
        VALUES (%s,%s,%s,%s,%s,%s,'devengado',%s,%s,%s)
        ON CONFLICT (jurisdiccion_id, periodo_id, categoria_id, universo, tipo_dato, base_contable, fuente_id)
        DO UPDATE SET monto = EXCLUDED.monto,
                      categoria_raw_original = EXCLUDED.categoria_raw_original,
                      fecha_carga = now()
    """, (jur_id, per_id, categoria_id, monto_millones, universo, tipo_dato,
          unidad_origen, raw, fuente_id))


# ---------------- A) XLS MECON ----------------

def ingestar_xls(conn, path, anio, url_fuente):
    """Carga el esquema AIF. Col 1 = Adm.Central (universo 'central'),
       col 5 = TOTAL APNF (universo 'apnf'). Valores YA en millones."""
    cur = conn.cursor()
    jur_id = get_or_create_jurisdiccion(cur)
    per_id = get_or_create_periodo_anual(cur, anio)
    fuente_id = get_or_create_fuente(
        cur, jur_id, f"MECON - Presupuesto provincial Córdoba {anio}", url_fuente, "xls")

    wb = xlrd.open_workbook(path)
    hojas = [n for n in wb.sheet_names() if n.strip() == str(anio)]
    if not hojas:
        raise SystemExit(f"No hay hoja para el año {anio}. Disponibles: {wb.sheet_names()}")
    sh = wb.sheet_by_name(hojas[0])

    # Detectar la columna TOTAL por su ENCABEZADO, no por posición.
    # (Algunas hojas —2020, p.ej.— traen columnas vacías de relleno al final;
    #  usar ncols-1 apuntaba a una columna vacía y perdía el universo 'apnf'.)
    col_central, col_total = 1, None
    for r in range(min(12, sh.nrows)):
        for c in range(sh.ncols):
            if str(sh.cell_value(r, c)).strip().upper() == "TOTAL":
                col_total = c
                break
        if col_total is not None:
            break
    if col_total is None:
        col_total = sh.ncols - 1  # fallback

    headline = {"central": {}, "apnf": {}}
    n_hechos = 0

    for r in range(sh.nrows):
        etiqueta = str(sh.cell_value(r, 0)).strip()
        if not etiqueta:
            continue
        clave = norm(etiqueta)

        # ¿es una fila headline?
        hl = next((v for k, v in FILAS_HEADLINE.items() if clave.startswith(k)), None)
        if hl:
            for universo, col in (("central", col_central), ("apnf", col_total)):
                val = sh.cell_value(r, col)
                if isinstance(val, (int, float)) and val != "":
                    headline[universo][hl] = float(val)
            continue

        # ¿es una categoría de detalle mapeada?
        slug = MAPEO_AIF.get(clave.lstrip("- ").strip())
        if not slug:
            continue
        cid = cat_id(cur, slug)
        for universo, col in (("central", col_central), ("apnf", col_total)):
            val = sh.cell_value(r, col)
            if not isinstance(val, (int, float)) or val == "":
                continue
            upsert_hecho(cur, jur_id, per_id, cid, float(val), universo,
                         "presupuesto", "millones", etiqueta, fuente_id)
            n_hechos += 1

    # headline -> resultados_fiscales
    for universo, vals in headline.items():
        if not vals:
            continue
        intereses = None
        if "resultado_primario" in vals and "resultado_financiero" in vals:
            intereses = vals["resultado_primario"] - vals["resultado_financiero"]
        cur.execute("""
            INSERT INTO resultados_fiscales
                (jurisdiccion_id, periodo_id, universo, tipo_dato, base_contable,
                 ingresos_totales, gastos_primarios, resultado_primario, intereses_deuda,
                 resultado_financiero, fuente_id)
            VALUES (%s,%s,%s,'presupuesto','devengado',%s,%s,%s,%s,%s,%s)
            ON CONFLICT (jurisdiccion_id, periodo_id, universo, tipo_dato, base_contable)
            DO UPDATE SET ingresos_totales=EXCLUDED.ingresos_totales,
                          gastos_primarios=EXCLUDED.gastos_primarios,
                          resultado_primario=EXCLUDED.resultado_primario,
                          intereses_deuda=EXCLUDED.intereses_deuda,
                          resultado_financiero=EXCLUDED.resultado_financiero
        """, (jur_id, per_id, universo, vals.get("ingresos_totales"),
              vals.get("gastos_primarios"), vals.get("resultado_primario"),
              intereses, vals.get("resultado_financiero"), fuente_id))

    conn.commit()
    print(f"[XLS] año {anio}: {n_hechos} hechos cargados (universos central + apnf)")
    for u, v in headline.items():
        if v:
            print(f"   {u:>9}: ing_tot={v.get('ingresos_totales',0):>14,.0f} M | "
                  f"res_fin={v.get('resultado_financiero',0):>12,.0f} M")
    return headline


def _hoja_de_anio(wb, anio):
    """Resuelve el nombre real de la hoja de un año.
    Ojo: algunas hojas vienen con espacios ('2014 '), por eso no se puede
    usar wb.sheet_by_name(str(anio)) directamente."""
    for n in wb.sheet_names():
        if n.strip() == str(anio):
            return wb.sheet_by_name(n)
    raise KeyError(f"sin hoja para {anio}")


def detectar_anios_duplicados(path):
    """Control de calidad del ORIGEN: detecta hojas de años distintos cuyo
    contenido numérico es idéntico. Ocurre cuando la fuente publica una
    hoja sin actualizar (copia del año anterior).

    Caso real detectado en el archivo de Córdoba: la hoja 2021 es copia
    exacta de la de 2020 (220 celdas numéricas iguales, 0 distintas) y
    además el nº de ley de 2021 figura vacío. Cargar esa hoja como si
    fuera 2021 publicaría datos falsos en el sitio.
    """
    wb = xlrd.open_workbook(path)
    anios = sorted(int(n.strip()) for n in wb.sheet_names() if n.strip().isdigit())
    sospechosos = []
    for prev, act in zip(anios, anios[1:]):
        try:
            sp, sa = _hoja_de_anio(wb, prev), _hoja_de_anio(wb, act)
        except KeyError:
            continue
        iguales = distintos = 0
        for r in range(min(sp.nrows, sa.nrows)):
            for c in range(min(6, sp.ncols, sa.ncols)):
                a, b = sp.cell_value(r, c), sa.cell_value(r, c)
                if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a and b:
                    if abs(a - b) < 1e-9:
                        iguales += 1
                    else:
                        distintos += 1
        if iguales > 20 and distintos == 0:
            sospechosos.append((prev, act, iguales))
    return sospechosos


def ingestar_xls_serie_historica(conn, path, url_fuente, omitir_duplicados=True):
    """Carga TODOS los años disponibles en el xls (2010..2026)."""
    wb = xlrd.open_workbook(path)
    anios = []
    for n in wb.sheet_names():
        s = n.strip()
        if s.isdigit():
            anios.append(int(s))
    print(f"[XLS] serie histórica detectada: {min(anios)}..{max(anios)} ({len(anios)} años)")

    dup = detectar_anios_duplicados(path)
    a_omitir = set()
    if dup:
        print("\n  *** CONTROL DE CALIDAD DEL ORIGEN ***")
        for prev, act, n in dup:
            print(f"  [!] La hoja {act} es IDENTICA a la de {prev} ({n} celdas iguales, 0 distintas).")
            print(f"      La fuente probablemente no actualizó esa hoja.")
            if omitir_duplicados:
                print(f"      -> Se OMITE {act} para no publicar datos de {prev} como si fueran de {act}.")
                a_omitir.add(act)
        print()

    for a in sorted(anios):
        if a in a_omitir:
            continue
        try:
            ingestar_xls(conn, path, a, url_fuente)
        except Exception as e:
            print(f"   [!] año {a} omitido: {e}")
    return anios


# ---------------- B) PDF funcional ----------------

def ingestar_pdf_funcional(conn, path, anio, url_fuente):
    """Extrae la columna 'Total General' de la Planilla 04 (clasificación
       funcional). Valores EN PESOS -> se dividen por 1e6 para guardar en
       millones, consistente con el resto de la base."""
    cur = conn.cursor()
    jur_id = get_or_create_jurisdiccion(cur)
    per_id = get_or_create_periodo_anual(cur, anio)
    fuente_id = get_or_create_fuente(
        cur, jur_id, f"Córdoba - Planilla 04 Finalidad y Objeto {anio}", url_fuente, "pdf")

    # La Planilla 04 reparte los objetos del gasto en DOS bloques de páginas.
    # Solo el SEGUNDO bloque trae la columna "Total General" (el total de la
    # finalidad). En el primer bloque, el último número de cada fila es apenas
    # el subtotal de ese bloque — tomarlo daría un total equivocado.
    # Por eso se identifica la página por su ENCABEZADO: es válida solo si
    # "Total General" aparece como encabezado de columna (antes de los datos).
    encontrados = {}
    total_general = None
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            lineas = t.split("\n")
            # el encabezado son las primeras líneas, antes de la primera fila de datos
            idx_primer_dato = next(
                (i for i, l in enumerate(lineas) if re.match(r"^\d+-\D", l.strip())),
                len(lineas))
            encabezado = " ".join(lineas[:idx_primer_dato])
            if "Total General" not in encabezado:
                continue  # página del primer bloque: no tiene el total de la finalidad

            for line in lineas:
                ls = line.strip()
                m = re.match(r"^(\d+-[A-Za-zÁÉÍÓÚÑáéíóúñ&\s\.]+?)\s+(-?[\d.]+(?:\s+-?[\d.]+)*)$", ls)
                if not m:
                    continue
                etiqueta, nums_str = m.group(1).strip(), m.group(2)
                slug = MAPEO_FUNCIONAL.get(norm(etiqueta))
                if not slug:
                    continue
                try:
                    total = parse_num_es(nums_str.split()[-1])
                except ValueError:
                    continue
                encontrados[slug] = (total, etiqueta)

            # Total General global (fila final de la página)
            for i, line in enumerate(lineas):
                if line.strip() == "Total General" and i + 1 < len(lineas):
                    try:
                        total_general = parse_num_es(lineas[i+1].split()[-1])
                    except (ValueError, IndexError):
                        pass

    n = 0
    suma_n1 = 0.0
    NIVEL1 = {"fun-administracion","fun-seguridad","fun-sociales",
              "fun-economicos","fun-deuda","fun-a-clasificar"}
    for slug, (valor_pesos, etiqueta) in encontrados.items():
        monto_millones = valor_pesos / 1_000_000
        upsert_hecho(cur, jur_id, per_id, cat_id(cur, slug), monto_millones,
                     "central", "presupuesto", "pesos", etiqueta, fuente_id)
        n += 1
        if slug in NIVEL1:
            suma_n1 += valor_pesos

    conn.commit()
    print(f"[PDF] funcional {anio}: {n} categorías cargadas (universo central, "
          f"convertidas de pesos a millones)")

    if total_general:
        diff = abs(suma_n1 - total_general)
        pct = diff / abs(total_general) * 100 if total_general else 0
        estado = "OK" if pct < 0.01 else "REVISAR"
        print(f"   Control: suma finalidades N1 = {suma_n1/1e6:>14,.0f} M")
        print(f"            Total General PDF   = {total_general/1e6:>14,.0f} M  [{estado}] dif={pct:.4f}%")
    return encontrados


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xls")
    ap.add_argument("--pdf-funcional")
    ap.add_argument("--anio", type=int, default=2026)
    ap.add_argument("--serie-historica", action="store_true",
                    help="cargar todos los años del xls, no solo --anio")
    ap.add_argument("--url-xls",
        default="https://www.argentina.gob.ar/sites/default/files/presupuesto_provincial_-_cordoba_1.xls")
    ap.add_argument("--url-pdf", default="https://transparencia.cba.gov.ar/")
    args = ap.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit("Falta DATABASE_URL")
    conn = psycopg2.connect(dsn)
    try:
        if args.xls:
            if args.serie_historica:
                ingestar_xls_serie_historica(conn, args.xls, args.url_xls)
            else:
                ingestar_xls(conn, args.xls, args.anio, args.url_xls)
        if args.pdf_funcional:
            ingestar_pdf_funcional(conn, args.pdf_funcional, args.anio, args.url_pdf)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
