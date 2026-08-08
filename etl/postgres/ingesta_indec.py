#!/usr/bin/env python3
"""
ingesta_indec.py — Carga población e IPC de INDEC.

FUENTES
  1) c1_proyecciones_prov_2010_2040.xls
     Población total por año (2010-2040) y jurisdicción. Base Censo 2010.
  2) c2022_tp_c_resumen.xlsx
     Conteo REAL del Censo Nacional 2022.
  3) sh_ipc_aperturas.xls
     IPC por región (GBA, Pampeana, NOA, NEA, Cuyo, Patagonia),
     dic-2016 en adelante, hoja 'Índices aperturas'.

AJUSTE CENSAL (importante)
  Las proyecciones base Censo 2010 se desvían del censo real 2022:
      Santa Cruz -12,1% | Chaco -8,0% | Chubut -7,3% | Corrientes +6,4%
  Usar la proyección cruda para el gasto per cápita subestimaría el de
  Santa Cruz en ~12% y falsearía los rankings del sitio.

  Solución aplicada: se calcula un factor por jurisdicción
      factor = poblacion_censo_2022 / poblacion_proyectada_2022
  y se reescala toda la serie. Esto conserva la FORMA de la proyección
  (el crecimiento año a año, que es lo que la proyección estima bien) y
  ancla el NIVEL al dato observado. Es el ajuste intercensal estándar.

  Se guardan las tres series para que el cálculo sea auditable:
      poblacion_proyectada -> cruda, como la publica INDEC
      poblacion_censo      -> el conteo real 2022
      poblacion            -> la ajustada; es la que usan los per cápita

USO
    export DATABASE_URL="postgresql://..."
    python ingesta_indec.py --poblacion c1_proyecciones_prov_2010_2040.xls \\
        --censo c2022_tp_c_resumen.xlsx --ipc sh_ipc_aperturas.xls
"""

import argparse
import os
import sys
import unicodedata
from datetime import date, datetime, timedelta

import psycopg2
import xlrd
import openpyxl

URL_POBLACION = "https://www.indec.gob.ar/ftp/cuadros/poblacion/c1_proyecciones_prov_2010_2040.xls"
URL_CENSO     = "https://www.indec.gob.ar/ftp/cuadros/poblacion/c2022_tp_c_resumen.xlsx"
URL_IPC       = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_aperturas.xls"

# nombre normalizado (INDEC) -> slug de jurisdicciones
SLUG = {
    "total del pais": None,                      # se ignora: no es jurisdicción
    "caba": "caba",
    "ciudad autonoma de buenos aires": "caba",
    "buenos aires": "buenos-aires",
    "catamarca": "catamarca",
    "cordoba": "cordoba",
    "corrientes": "corrientes",
    "chaco": "chaco",
    "chubut": "chubut",
    "entre rios": "entre-rios",
    "formosa": "formosa",
    "jujuy": "jujuy",
    "la pampa": "la-pampa",
    "la rioja": "la-rioja",
    "mendoza": "mendoza",
    "misiones": "misiones",
    "neuquen": "neuquen",
    "rio negro": "rio-negro",
    "salta": "salta",
    "san juan": "san-juan",
    "san luis": "san-luis",
    "santa cruz": "santa-cruz",
    "santa fe": "santa-fe",
    # TYPO EN EL ARCHIVO DE INDEC: la hoja del c1 se llama "82-SANTE FE".
    # Sin este alias, Santa Fe (3ª economía provincial) quedaba fuera del
    # cálculo per cápita sin ningún error visible.
    "sante fe": "santa-fe",
    "santiago del estero": "santiago-del-estero",
    "tucuman": "tucuman",
    # El nombre largo varía entre archivos de INDEC (con y sin "Argentina")
    "tierra del fuego": "tierra-del-fuego",
    "tierra del fuego, antartida e islas del atlantico sur": "tierra-del-fuego",
    "tierra del fuego, antartida argentina e islas del atlantico sur": "tierra-del-fuego",
}

REGIONES_IPC = {
    "region gba": "GBA",
    "region pampeana": "Pampeana",
    "region noroeste": "NOA",
    "region noreste": "NEA",
    "region cuyo": "Cuyo",
    "region patagonia": "Patagonia",
}


def nrm(s):
    if s is None:
        return ""
    s = "".join(c for c in unicodedata.normalize("NFD", str(s))
                if unicodedata.category(c) != "Mn")
    return " ".join(s.strip().lower().split())


def serial_a_fecha(n):
    return datetime(1899, 12, 30) + timedelta(days=float(n))


# ---------- helpers de base ----------

def jur_id(cur, slug):
    cur.execute("SELECT id FROM jurisdicciones WHERE slug=%s", (slug,))
    r = cur.fetchone()
    return r[0] if r else None


def periodo_anual(cur, anio):
    cur.execute("SELECT id FROM periodos WHERE anio=%s AND mes IS NULL AND tipo='anual'", (anio,))
    r = cur.fetchone()
    if r:
        return r[0]
    cur.execute("""INSERT INTO periodos (anio,mes,tipo,fecha_inicio,fecha_fin)
                   VALUES (%s,NULL,'anual',%s,%s) RETURNING id""",
                (anio, date(anio,1,1), date(anio,12,31)))
    return cur.fetchone()[0]


def periodo_mensual(cur, anio, mes):
    cur.execute("SELECT id FROM periodos WHERE anio=%s AND mes=%s AND tipo='mensual'", (anio, mes))
    r = cur.fetchone()
    if r:
        return r[0]
    fin = date(anio + (mes == 12), (mes % 12) + 1, 1) - timedelta(days=1)
    cur.execute("""INSERT INTO periodos (anio,mes,tipo,fecha_inicio,fecha_fin)
                   VALUES (%s,%s,'mensual',%s,%s) RETURNING id""",
                (anio, mes, date(anio,mes,1), fin))
    return cur.fetchone()[0]


def fuente(cur, nombre, url, notas=""):
    cur.execute("SELECT id FROM fuentes WHERE nombre=%s AND url=%s", (nombre, url))
    r = cur.fetchone()
    if r:
        return r[0]
    cur.execute("""INSERT INTO fuentes (jurisdiccion_id,nombre,organismo,url,tipo_archivo,
                                        frecuencia_actualizacion,ultima_revision,notas)
                   VALUES (NULL,%s,'INDEC',%s,'xls','anual',CURRENT_DATE,%s) RETURNING id""",
                (nombre, url, notas))
    return cur.fetchone()[0]


def upsert_contexto(cur, jid, pid, tipo, valor, fid):
    cur.execute("""INSERT INTO indicadores_contexto
                     (jurisdiccion_id,periodo_id,tipo_indicador,valor,fuente_id)
                   VALUES (%s,%s,%s,%s,%s)
                   ON CONFLICT (jurisdiccion_id,periodo_id,tipo_indicador)
                   DO UPDATE SET valor=EXCLUDED.valor""",
                (jid, pid, tipo, valor, fid))


# ---------- 1) población ----------

def leer_proyecciones(path):
    """{slug: {anio: poblacion}}"""
    wb = xlrd.open_workbook(path)
    out = {}
    for hoja in wb.sheet_names():
        if hoja == "GraphData":
            continue
        nombre = hoja.split("-", 1)[1] if "-" in hoja else hoja
        slug = SLUG.get(nrm(nombre))
        if not slug:
            continue
        sh = wb.sheet_by_name(hoja)
        serie = {}
        for r in range(sh.nrows):
            a = sh.cell_value(r, 0)
            v = sh.cell_value(r, 1)
            if isinstance(a, float) and 1900 < a < 2100 and isinstance(v, float) and v > 0:
                serie[int(a)] = v
        if serie:
            out[slug] = serie
    return out


def leer_censo(path):
    """{slug: poblacion_2022}"""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["cuadro_resumen"]
    out = {}
    for r in range(1, ws.max_row + 1):
        j = ws.cell(r, 1).value
        v = ws.cell(r, 2).value
        if not j or not isinstance(v, (int, float)):
            continue
        slug = SLUG.get(nrm(j))
        if slug:
            out[slug] = float(v)
    return out


def ingestar_poblacion(conn, path_proy, path_censo):
    cur = conn.cursor()
    fid_p = fuente(cur, "INDEC - Proyecciones provinciales 2010-2040 (base Censo 2010)",
                   URL_POBLACION, "Cuadro 1. Población total por año y jurisdicción.")
    fid_c = fuente(cur, "INDEC - Censo Nacional 2022 (cuadro resumen)", URL_CENSO,
                   "Conteo real de población por jurisdicción.")

    proy = leer_proyecciones(path_proy)
    censo = leer_censo(path_censo)

    # CONTROL DE COBERTURA: toda jurisdicción provincial de la base debe
    # tener población. Sin esto un typo en el archivo origen (pasó: la hoja
    # de Santa Fe viene escrita "SANTE FE") deja a una provincia sin dato
    # per cápita y desaparece de los rankings sin ningún error visible.
    cur.execute("SELECT slug FROM jurisdicciones WHERE nivel='provincial' "
                "AND slug <> 'consolidado-provincias'")
    esperadas = {r[0] for r in cur.fetchall()}
    faltantes = esperadas - set(proy)
    if faltantes:
        print(f"  [!] SIN POBLACIÓN ({len(faltantes)}): {', '.join(sorted(faltantes))}")
        print("      Revisar nombres de hoja en el archivo de INDEC.\n")

    print(f"{'JURISDICCIÓN':<24}{'PROY 2022':>13}{'CENSO 2022':>13}{'DESVÍO':>9}{'FACTOR':>9}")
    print("-" * 70)

    n_años = n_jur = 0
    desvios = []
    for slug, serie in sorted(proy.items()):
        jid = jur_id(cur, slug)
        if jid is None:
            print(f"  [!] jurisdicción no encontrada en la base: {slug}")
            continue

        cens = censo.get(slug)
        p2022 = serie.get(2022)
        factor = (cens / p2022) if (cens and p2022) else 1.0
        if cens and p2022:
            desvio = (cens - p2022) / p2022 * 100
            desvios.append((abs(desvio), slug, desvio))
            print(f"{slug:<24}{p2022:>13,.0f}{cens:>13,.0f}{desvio:>8.1f}%{factor:>9.4f}")

        # censo 2022 como dato propio
        if cens:
            upsert_contexto(cur, jid, periodo_anual(cur, 2022), "poblacion_censo", cens, fid_c)

        for anio, val in serie.items():
            pid = periodo_anual(cur, anio)
            upsert_contexto(cur, jid, pid, "poblacion_proyectada", val, fid_p)
            upsert_contexto(cur, jid, pid, "poblacion", val * factor, fid_p)
            n_años += 1
        n_jur += 1

    conn.commit()
    print(f"\nCargadas {n_jur} jurisdicciones × ~{n_años//max(n_jur,1)} años "
          f"({n_años} registros × 2 series).")
    if desvios:
        peor = sorted(desvios, reverse=True)[:3]
        print("Mayores ajustes aplicados: " +
              " | ".join(f"{s} {d:+.1f}%" for _, s, d in peor))
    return len(proy)


# ---------- 2) IPC ----------

def ingestar_ipc(conn, path):
    cur = conn.cursor()
    fid = fuente(cur, "INDEC - IPC aperturas por región", URL_IPC,
                 "Índices por región. Serie desde dic-2016 (base dic-2016=100).")
    wb = xlrd.open_workbook(path)
    sh = wb.sheet_by_name("Índices aperturas")

    total = 0
    resumen = []
    for r in range(sh.nrows):
        etiqueta = nrm(sh.cell_value(r, 0))
        region = REGIONES_IPC.get(etiqueta)
        if not region:
            continue
        # fila r = fechas ; la fila 'Nivel general' está unas filas abajo
        fechas = {}
        for c in range(1, sh.ncols):
            v = sh.cell_value(r, c)
            if isinstance(v, float) and v > 40000:
                fechas[c] = serial_a_fecha(v)
        if not fechas:
            continue
        fila_ng = None
        for rr in range(r + 1, min(r + 6, sh.nrows)):
            if nrm(sh.cell_value(rr, 0)) == "nivel general":
                fila_ng = rr
                break
        if fila_ng is None:
            continue
        n = 0
        for c, f in fechas.items():
            val = sh.cell_value(fila_ng, c)
            if not isinstance(val, float) or val <= 0:
                continue
            pid = periodo_mensual(cur, f.year, f.month)
            cur.execute("""INSERT INTO indicadores_costo_vida
                             (region_indec,periodo_id,indicador,valor,fuente_id)
                           VALUES (%s,%s,'ipc_general',%s,%s)
                           ON CONFLICT (region_indec,periodo_id,indicador)
                           DO UPDATE SET valor=EXCLUDED.valor""",
                        (region, pid, val, fid))
            n += 1
            total += 1
        fs = sorted(fechas.values())
        resumen.append((region, fs[0].strftime("%Y-%m"), fs[-1].strftime("%Y-%m"), n))

    conn.commit()
    print(f"\n{'REGIÓN':<14}{'DESDE':>9}{'HASTA':>9}{'MESES':>8}")
    print("-" * 42)
    for reg, d, h, n in resumen:
        print(f"{reg:<14}{d:>9}{h:>9}{n:>8}")
    print(f"\nTotal registros IPC: {total}")
    print("LIMITACIÓN: la serie oficial arranca en dic-2016. Los años fiscales "
          "2005-2016 no se pueden deflactar con esta fuente.")
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poblacion")
    ap.add_argument("--censo")
    ap.add_argument("--ipc")
    args = ap.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit("Falta DATABASE_URL")
    conn = psycopg2.connect(dsn)
    try:
        if args.poblacion and args.censo:
            print("=" * 70 + "\nPOBLACIÓN (con ajuste censal)\n" + "=" * 70)
            ingestar_poblacion(conn, args.poblacion, args.censo)
        if args.ipc:
            print("\n" + "=" * 70 + "\nIPC POR REGIÓN\n" + "=" * 70)
            ingestar_ipc(conn, args.ipc)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
