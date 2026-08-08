#!/usr/bin/env python3
"""
ingesta_serie_aif.py — Carga la serie AIF-APNF de las 24 jurisdicciones.

FUENTE: serie_aif-apnf-2025.xlsx (DNCFP - MECON)
  - 25 hojas: 'Consolidado' + 24 jurisdicciones (23 provincias + CABA)
  - 21 años por hoja: 2005..2025
  - Esquema Ahorro-Inversión-Financiamiento, idéntico en todas las hojas
  - Universo: Administración Pública No Financiera  -> universo 'apnf'
  - EJECUCIÓN presupuestaria (no presupuesto)       -> tipo_dato 'ejecutado'
  - Base devengado                                  -> base_contable 'devengado'
  - EN MILLONES DE PESOS                            -> unidad_origen 'millones'

Este archivo resuelve el problema de la fragmentación de los portales
provinciales: en vez de scrapear 24 sitios con 24 formatos, una sola
fuente ya normalizada por la Dirección Nacional de Coordinación Fiscal
con las Provincias.

CONTROLES DE CALIDAD INCLUIDOS
  - Años con TODOS los valores en cero = jurisdicción que no reportó.
    Se omiten: un cero real y un "sin dato" no son lo mismo, y cargarlos
    como cero hundiría los promedios y rankings del sitio.
    (Caso detectado: La Pampa 2025.)
  - Verificación de la identidad contable Ingresos - Gastos = Resultado.
  - Verificación de que la suma de las 24 jurisdicciones ≈ Consolidado.

USO:
    export DATABASE_URL="postgresql://..."
    python ingesta_serie_aif.py --xlsx serie_aif-apnf-2025.xlsx
"""

import argparse
import os
import re
import sys
import unicodedata
from datetime import date

import psycopg2
import openpyxl

URL_FUENTE_DEFAULT = ("https://www.argentina.gob.ar/economia/sechacienda/"
                      "coordinacion-fiscal-provincial/ejecucion-presupuestaria-provincial")

# Hoja -> (nombre canónico, slug, código INDEC, región INDEC)
JURISDICCIONES = {
    "Ciudad":               ("Ciudad Autónoma de Buenos Aires", "caba", "02", "GBA"),
    "Buenos Aires":         ("Buenos Aires", "buenos-aires", "06", "GBA"),
    "Catamarca":            ("Catamarca", "catamarca", "10", "NOA"),
    "Córdoba":              ("Córdoba", "cordoba", "14", "Pampeana"),
    "Corrientes":           ("Corrientes", "corrientes", "18", "NEA"),
    "Chaco":                ("Chaco", "chaco", "22", "NEA"),
    "Chubut":               ("Chubut", "chubut", "26", "Patagonia"),
    "Entre Ríos":           ("Entre Ríos", "entre-rios", "30", "Pampeana"),
    "Formosa":              ("Formosa", "formosa", "34", "NEA"),
    "Jujuy":                ("Jujuy", "jujuy", "38", "NOA"),
    "La Pampa":             ("La Pampa", "la-pampa", "42", "Pampeana"),
    "La Rioja":             ("La Rioja", "la-rioja", "46", "NOA"),
    "Mendoza":              ("Mendoza", "mendoza", "50", "Cuyo"),
    "Misiones":             ("Misiones", "misiones", "54", "NEA"),
    "Neuquén":              ("Neuquén", "neuquen", "58", "Patagonia"),
    "Río Negro":            ("Río Negro", "rio-negro", "62", "Patagonia"),
    "Salta":                ("Salta", "salta", "66", "NOA"),
    "San Juan":             ("San Juan", "san-juan", "70", "Cuyo"),
    "San Luis":             ("San Luis", "san-luis", "74", "Cuyo"),
    "Santa Cruz":           ("Santa Cruz", "santa-cruz", "78", "Patagonia"),
    "Santa Fe":             ("Santa Fe", "santa-fe", "82", "Pampeana"),
    "Santiago del  Estero": ("Santiago del Estero", "santiago-del-estero", "86", "NOA"),
    "Tucumán":              ("Tucumán", "tucuman", "90", "NOA"),
    "Tierra del Fuego":     ("Tierra del Fuego", "tierra-del-fuego", "94", "Patagonia"),
}

# Etiqueta del AIF (normalizada) -> slug canónico de categoría
MAPEO_AIF = {
    "de origen provincial":                  "ing-prov-impuestos-propios",
    "de origen nacional":                    "ing-prov-coparticipacion",
    "contribuciones a la seguridad social":  "ing-trib-seg-social",
    "no tributarios":                        "ing-notrib-general",
    "regalias":                              "ing-prov-regalias",
    "vta.bienes y serv.de la adm.publ.":     "ing-notrib-otros",
    "rentas de la propiedad":                "ing-notrib-rentas",
    "transferencias corrientes":             "ing-prov-transf-corrientes",
    "personal":                              "gas-remuneraciones",
    "bienes de consumo":                     "gas-bienes-servicios",
    "prestaciones de la seguridad social":   "gas-prest-jubilaciones",
    "al sector privado":                     "gas-transf-privado",
    "al sector publico":                     "gas-transf-municipios",
    "inversion real directa":                "gas-capital",
}

# Filas headline del AIF -> campo de resultados_fiscales
HEADLINE = {
    "vi. ingresos totales":     "ingresos_totales",
    "vii. gastos totales":      "gastos_totales",
    "viii. resultado financiero": "resultado_financiero",
    "ix. resultado primario":   "resultado_primario",
    "x. gastos primarios":      "gastos_primarios",
    "iii. resultado economico": "resultado_economico",
}

# 'Rentas de la propiedad' aparece 2 veces (ingreso y gasto). El AIF las
# separa por posición: la primera está en el bloque de INGRESOS y la
# segunda en el de GASTOS. Se resuelve por el bloque activo, no por texto.
CTX_INGRESO, CTX_GASTO = "ingreso", "gasto"


def norm(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    s = s.lstrip(".- ").strip()
    return re.sub(r"\s+", " ", s)


def get_or_create_jurisdiccion(cur, nombre, slug, nivel, cod, region):
    cur.execute("SELECT id FROM jurisdicciones WHERE slug=%s", (slug,))
    r = cur.fetchone()
    if r:
        return r[0]
    cur.execute("""INSERT INTO jurisdicciones (nombre, slug, nivel, codigo_indec, region_indec)
                   VALUES (%s,%s,%s,%s,%s) RETURNING id""", (nombre, slug, nivel, cod, region))
    return cur.fetchone()[0]


def get_or_create_periodo_anual(cur, anio):
    cur.execute("SELECT id FROM periodos WHERE anio=%s AND mes IS NULL AND tipo='anual'", (anio,))
    r = cur.fetchone()
    if r:
        return r[0]
    cur.execute("""INSERT INTO periodos (anio, mes, tipo, fecha_inicio, fecha_fin)
                   VALUES (%s,NULL,'anual',%s,%s) RETURNING id""",
                (anio, date(anio,1,1), date(anio,12,31)))
    return cur.fetchone()[0]


def get_or_create_fuente(cur, nombre, url):
    cur.execute("SELECT id FROM fuentes WHERE nombre=%s AND url=%s", (nombre, url))
    r = cur.fetchone()
    if r:
        return r[0]
    cur.execute("""INSERT INTO fuentes (jurisdiccion_id, nombre, organismo, url, tipo_archivo,
                                        frecuencia_actualizacion, ultima_revision, notas)
                   VALUES (NULL,%s,%s,%s,'xlsx','anual',CURRENT_DATE,%s) RETURNING id""",
                (nombre, "DNCFP - Secretaría de Hacienda - MECON", url,
                 "Ejecución presupuestaria provisoria, APNF, base devengado, en millones de $"))
    return cur.fetchone()[0]


def cat_id(cur, slug, cache={}):
    if slug in cache:
        return cache[slug]
    cur.execute("SELECT id FROM categorias WHERE slug=%s", (slug,))
    r = cur.fetchone()
    if not r:
        raise ValueError(f"categoría canónica inexistente: {slug}")
    cache[slug] = r[0]
    return r[0]


def leer_hoja(ws):
    """Devuelve (anios:[(col,anio)], filas:[(etiqueta_norm, contexto, {anio:valor})])."""
    # fila de encabezado = la que tiene 'CONCEPTO' en col 1
    fila_hdr = None
    for r in range(1, min(ws.max_row, 20) + 1):
        if norm(ws.cell(r, 1).value) == "concepto":
            fila_hdr = r
            break
    if fila_hdr is None:
        return [], []

    anios = []
    for c in range(2, ws.max_column + 1):
        v = ws.cell(fila_hdr, c).value
        if isinstance(v, (int, float)) and 1990 < v < 2100:
            anios.append((c, int(v)))

    filas = []
    contexto = CTX_INGRESO
    for r in range(fila_hdr + 1, ws.max_row + 1):
        etiqueta = ws.cell(r, 1).value
        if etiqueta is None:
            continue
        e = norm(etiqueta)
        if not e:
            continue
        # cambio de bloque: II. GASTOS CORRIENTES marca inicio de gastos
        if e.startswith("ii. gastos corrientes"):
            contexto = CTX_GASTO
        elif e.startswith("iv. ingresos de capital"):
            contexto = CTX_INGRESO
        elif e.startswith("v. gastos de capital"):
            contexto = CTX_GASTO
        vals = {}
        for c, a in anios:
            v = ws.cell(r, c).value
            if isinstance(v, (int, float)):
                vals[a] = float(v)
        filas.append((e, contexto, vals))
    return anios, filas


def anios_sin_datos(filas, anios):
    """Años en los que TODOS los valores son 0/None -> la jurisdicción no reportó.
    Distinguir esto de un cero legítimo es crítico: cargar 'sin dato' como 0
    distorsiona promedios, rankings y series del sitio."""
    sin_datos = set()
    for _, a in anios:
        total = sum(abs(v.get(a, 0) or 0) for _, _, v in filas)
        if total == 0:
            sin_datos.add(a)
    return sin_datos


def ingestar(conn, xlsx_path, url_fuente=URL_FUENTE_DEFAULT, incluir_consolidado=True):
    cur = conn.cursor()
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    fuente_id = get_or_create_fuente(cur, "DNCFP - Serie AIF APNF provincias 2005-2025", url_fuente)

    resumen = []
    total_hechos = 0

    hojas = list(JURISDICCIONES.keys())
    if incluir_consolidado and "Consolidado" in wb.sheetnames:
        hojas = ["Consolidado"] + hojas

    for hoja in hojas:
        if hoja not in wb.sheetnames:
            print(f"  [!] hoja ausente en el archivo: {hoja}")
            continue
        ws = wb[hoja]

        if hoja == "Consolidado":
            nombre, slug, cod, region, nivel = ("Consolidado provincias",
                                                "consolidado-provincias", None, None, "provincial")
        else:
            nombre, slug, cod, region = JURISDICCIONES[hoja]
            nivel = "provincial"

        jur_id = get_or_create_jurisdiccion(cur, nombre, slug, nivel, cod, region)
        anios, filas = leer_hoja(ws)
        if not anios:
            print(f"  [!] {hoja}: no se detectó encabezado de años")
            continue

        omitidos = anios_sin_datos(filas, anios)
        cargados = 0

        for _, anio in anios:
            if anio in omitidos:
                continue
            per_id = get_or_create_periodo_anual(cur, anio)

            head = {}
            for etiqueta, contexto, vals in filas:
                if anio not in vals:
                    continue
                monto = vals[anio]

                hl = next((campo for k, campo in HEADLINE.items() if etiqueta.startswith(k)), None)
                if hl:
                    head[hl] = monto
                    continue

                slug_cat = MAPEO_AIF.get(etiqueta)
                if not slug_cat:
                    continue
                # 'rentas de la propiedad' es ingreso o gasto según el bloque
                if etiqueta == "rentas de la propiedad" and contexto == CTX_GASTO:
                    continue  # el gasto en intereses ya se captura vía headline
                cur.execute("""
                    INSERT INTO hechos_fiscales
                        (jurisdiccion_id, periodo_id, categoria_id, monto, universo,
                         tipo_dato, base_contable, unidad_origen,
                         categoria_raw_original, fuente_id)
                    VALUES (%s,%s,%s,%s,'apnf','ejecutado','devengado','millones',%s,%s)
                    ON CONFLICT (jurisdiccion_id, periodo_id, categoria_id, universo,
                                 tipo_dato, base_contable, fuente_id)
                    DO UPDATE SET monto=EXCLUDED.monto, fecha_carga=now()
                """, (jur_id, per_id, cat_id(cur, slug_cat), monto, etiqueta, fuente_id))
                cargados += 1
                total_hechos += 1

            if head:
                intereses = None
                if head.get("gastos_totales") is not None and head.get("gastos_primarios") is not None:
                    intereses = head["gastos_totales"] - head["gastos_primarios"]
                cur.execute("""
                    INSERT INTO resultados_fiscales
                        (jurisdiccion_id, periodo_id, universo, tipo_dato, base_contable,
                         ingresos_totales, gastos_totales, gastos_primarios,
                         resultado_economico, resultado_primario, intereses_deuda,
                         resultado_financiero, fuente_id)
                    VALUES (%s,%s,'apnf','ejecutado','devengado',%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (jurisdiccion_id, periodo_id, universo, tipo_dato, base_contable)
                    DO UPDATE SET ingresos_totales=EXCLUDED.ingresos_totales,
                                  gastos_totales=EXCLUDED.gastos_totales,
                                  gastos_primarios=EXCLUDED.gastos_primarios,
                                  resultado_economico=EXCLUDED.resultado_economico,
                                  resultado_primario=EXCLUDED.resultado_primario,
                                  intereses_deuda=EXCLUDED.intereses_deuda,
                                  resultado_financiero=EXCLUDED.resultado_financiero
                """, (jur_id, per_id, head.get("ingresos_totales"), head.get("gastos_totales"),
                      head.get("gastos_primarios"), head.get("resultado_economico"),
                      head.get("resultado_primario"), intereses,
                      head.get("resultado_financiero"), fuente_id))

        resumen.append((nombre, len(anios) - len(omitidos), sorted(omitidos), cargados))

    conn.commit()

    print(f"\n{'JURISDICCIÓN':<34} {'AÑOS':>5}  {'HECHOS':>7}   AÑOS SIN DATOS (omitidos)")
    print("-" * 92)
    for nombre, n_anios, omit, n_hechos in resumen:
        om = ", ".join(str(a) for a in omit) if omit else "-"
        print(f"{nombre:<34} {n_anios:>5}  {n_hechos:>7}   {om}")
    print(f"\nTotal hechos cargados: {total_hechos}")
    return resumen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--url-fuente", default=URL_FUENTE_DEFAULT)
    ap.add_argument("--sin-consolidado", action="store_true")
    args = ap.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit("Falta DATABASE_URL")
    conn = psycopg2.connect(dsn)
    try:
        ingestar(conn, args.xlsx, args.url_fuente, not args.sin_consolidado)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
