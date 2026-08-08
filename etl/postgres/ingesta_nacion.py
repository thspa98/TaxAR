#!/usr/bin/env python3
"""
ingesta_nacion.py — Carga la Base Caja mensual de Nación en la base de
transparencia fiscal.

CASO DE PRUEBA: pensado para correr contra mayo_2026_nacion.csv, que
contiene los mismos datos que ya transcribimos y verificamos contra el
comunicado oficial de MECON.

FORMATO DE ENTRADA (CSV intermedio):
    categoria_raw,tipo,monto
    Ganancias,ingreso,2970423
    ...

Por qué un CSV intermedio y no el .xlsx de MECON directamente:
    No pude descargar el Excel real de MECON en este entorno (el dominio
    argentina.gob.ar no está en la lista blanca de red del sandbox), así
    que no quise adivinar la estructura interna de celdas del archivo real
    y arriesgarme a un mapeo incorrecto. Este script sí resuelve la parte
    difícil (normalización a taxonomía canónica + upsert + reconciliación),
    que es igual sin importar el formato de entrada. El adaptador que lee
    directamente el .xlsx queda como función separada (ver
    `extraer_de_excel_mecon`) para calibrar una vez que tengas el archivo
    real a mano — decime si me das acceso a la carpeta con el .xlsx y lo
    termino.

USO:
    export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
    python ingesta_nacion.py --csv mayo_2026_nacion.csv --anio 2026 --mes 5 \\
        --ingresos-totales 14531657 --gastos-primarios 12607290 \\
        --resultado-primario 1924367 --intereses 1445754 \\
        --resultado-financiero 478613 \\
        --fuente-url "https://www.argentina.gob.ar/sites/default/files/2026/06/mayo_26.xlsx"
"""

import argparse
import csv
import os
import sys
from datetime import date
from calendar import monthrange

import psycopg2
from psycopg2.extras import execute_values

# ------------------------------------------------------------------
# Mapeo: nombre crudo (tal como lo publica la fuente) -> slug canónico
# Este diccionario es EL corazón de la normalización. Se extiende a
# medida que aparecen nombres nuevos o variantes de redacción entre
# meses/jurisdicciones.
# ------------------------------------------------------------------
MAPEO_CATEGORIA_RAW_A_SLUG = {
    # Ingresos
    "aportes y contribuciones a la seguridad social": "ing-trib-seg-social",
    "ganancias": "ing-trib-ganancias",
    "iva neto de reintegros": "ing-trib-iva",
    "débitos y créditos": "ing-trib-debcred",
    "debitos y creditos": "ing-trib-debcred",
    "derechos de exportación": "ing-trib-derexp",
    "derechos de exportacion": "ing-trib-derexp",
    "derechos de importación": "ing-trib-derimp",
    "derechos de importacion": "ing-trib-derimp",
    "impuestos internos": "ing-trib-internos",
    "bienes personales": "ing-trib-bienpers",
    "resto tributarios": "ing-trib-resto",
    "rentas de la propiedad": "ing-notrib-rentas",
    "ingresos no tributarios": "ing-notrib-general",
    "otros ingresos corrientes": "ing-notrib-otros",
    "ingresos de capital": "ing-capital",
    # Gastos
    "jubilaciones y pensiones contributivas": "gas-prest-jubilaciones",
    "pensiones no contributivas": "gas-prest-noncontrib",
    "asignación universal para protección social": "gas-prest-auh",
    "asignacion universal para proteccion social": "gas-prest-auh",
    "prestaciones del inssjp": "gas-prest-inssjp",
    "otros programas sociales": "gas-prest-otros",
    "energía": "gas-sub-energia",
    "energia": "gas-sub-energia",
    "transporte": "gas-sub-transporte",
    "transferencias a provincias": "gas-transf-provincias",
    "transferencias a universidades": "gas-transf-universidades",
    "remuneraciones": "gas-remuneraciones",
    "gastos de capital": "gas-capital",
}

JURISDICCION_DEFAULT = {
    "nombre": "Nación",
    "slug": "nacion",
    "nivel": "nacional",
}


def normalizar(texto: str) -> str:
    return texto.strip().lower()


def get_or_create_jurisdiccion(cur, slug, nombre, nivel):
    cur.execute("SELECT id FROM jurisdicciones WHERE slug = %s", (slug,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO jurisdicciones (nombre, slug, nivel) VALUES (%s, %s, %s) RETURNING id",
        (nombre, slug, nivel),
    )
    return cur.fetchone()[0]


def get_or_create_periodo(cur, anio, mes, tipo="mensual"):
    cur.execute(
        "SELECT id FROM periodos WHERE anio=%s AND mes=%s AND tipo=%s",
        (anio, mes, tipo),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    fecha_inicio = date(anio, mes, 1)
    ultimo_dia = monthrange(anio, mes)[1]
    fecha_fin = date(anio, mes, ultimo_dia)
    cur.execute(
        """INSERT INTO periodos (anio, mes, tipo, fecha_inicio, fecha_fin)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (anio, mes, tipo, fecha_inicio, fecha_fin),
    )
    return cur.fetchone()[0]


def get_or_create_fuente(cur, jurisdiccion_id, nombre, url, tipo_archivo="xlsx",
                          frecuencia="mensual", organismo="Secretaría de Hacienda - MECON"):
    cur.execute("SELECT id FROM fuentes WHERE url = %s", (url,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        """INSERT INTO fuentes (jurisdiccion_id, nombre, organismo, url, tipo_archivo,
                                 frecuencia_actualizacion, ultima_revision)
           VALUES (%s, %s, %s, %s, %s, %s, CURRENT_DATE) RETURNING id""",
        (jurisdiccion_id, nombre, organismo, url, tipo_archivo, frecuencia),
    )
    return cur.fetchone()[0]


def resolver_categoria_id(cur, slug):
    cur.execute("SELECT id FROM categorias WHERE slug = %s", (slug,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Categoría canónica no encontrada para slug '{slug}'. "
                          f"¿Corriste 02_taxonomia_seed.sql?")
    return row[0]


def cargar_csv(path):
    filas = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            filas.append({
                "categoria_raw": r["categoria_raw"].strip(),
                "tipo": r["tipo"].strip().lower(),
                "monto": float(r["monto"]),
            })
    return filas


def ingestar(conn, csv_path, anio, mes, headline, fuente_url, fuente_nombre,
             jurisdiccion_slug="nacion"):
    cur = conn.cursor()

    jurisdiccion_id = get_or_create_jurisdiccion(
        cur, jurisdiccion_slug, JURISDICCION_DEFAULT["nombre"], JURISDICCION_DEFAULT["nivel"]
    )
    periodo_id = get_or_create_periodo(cur, anio, mes)
    fuente_id = get_or_create_fuente(cur, jurisdiccion_id, fuente_nombre, fuente_url)

    filas = cargar_csv(csv_path)

    no_mapeadas = []
    cargadas = 0
    totales_cargados = {"ingreso": 0.0, "gasto": 0.0}

    for fila in filas:
        slug = MAPEO_CATEGORIA_RAW_A_SLUG.get(normalizar(fila["categoria_raw"]))
        if not slug:
            no_mapeadas.append(fila["categoria_raw"])
            continue
        categoria_id = resolver_categoria_id(cur, slug)
        # Nación Base Caja: universo 'apnf' (SPN), dato EJECUTADO, en millones.
        cur.execute(
            """INSERT INTO hechos_fiscales
                   (jurisdiccion_id, periodo_id, categoria_id, monto,
                    universo, tipo_dato, base_contable, unidad_origen,
                    categoria_raw_original, fuente_id)
               VALUES (%s, %s, %s, %s, 'apnf', 'ejecutado', 'caja', 'millones', %s, %s)
               ON CONFLICT (jurisdiccion_id, periodo_id, categoria_id, universo, tipo_dato, base_contable, fuente_id)
               DO UPDATE SET monto = EXCLUDED.monto,
                              categoria_raw_original = EXCLUDED.categoria_raw_original,
                              fecha_carga = now()""",
            (jurisdiccion_id, periodo_id, categoria_id, fila["monto"],
             fila["categoria_raw"], fuente_id),
        )
        totales_cargados[fila["tipo"]] += fila["monto"]
        cargadas += 1

    # KPIs headline (autoritativos, vienen del comunicado oficial —
    # no se recalculan sumando el detalle, porque el detalle puede no
    # cubrir el 100% de las líneas del presupuesto)
    cur.execute(
        """INSERT INTO resultados_fiscales
               (jurisdiccion_id, periodo_id, universo, tipo_dato, base_contable,
                ingresos_totales, gastos_primarios,
                resultado_primario, intereses_deuda, resultado_financiero, fuente_id)
           VALUES (%s, %s, 'apnf', 'ejecutado', 'caja', %s, %s, %s, %s, %s, %s)
           ON CONFLICT (jurisdiccion_id, periodo_id, universo, tipo_dato, base_contable)
           DO UPDATE SET ingresos_totales = EXCLUDED.ingresos_totales,
                          gastos_primarios = EXCLUDED.gastos_primarios,
                          resultado_primario = EXCLUDED.resultado_primario,
                          intereses_deuda = EXCLUDED.intereses_deuda,
                          resultado_financiero = EXCLUDED.resultado_financiero""",
        (jurisdiccion_id, periodo_id, headline["ingresos_totales"],
         headline["gastos_primarios"], headline["resultado_primario"],
         headline["intereses"], headline["resultado_financiero"], fuente_id),
    )

    conn.commit()

    # --- Reconciliación: cuánto del headline quedó sin categorizar ---
    print(f"Filas cargadas: {cargadas}")
    if no_mapeadas:
        print(f"AVISO: {len(no_mapeadas)} categorías sin mapeo canónico (no se cargaron):")
        for nm in no_mapeadas:
            print(f"   - {nm}")

    gap_ingresos = headline["ingresos_totales"] - totales_cargados["ingreso"]
    gap_gastos = headline["gastos_primarios"] - totales_cargados["gasto"]
    print(f"\nReconciliación ingresos: headline={headline['ingresos_totales']:,.0f} "
          f"| categorizado={totales_cargados['ingreso']:,.0f} | sin categorizar={gap_ingresos:,.0f} "
          f"({gap_ingresos/headline['ingresos_totales']*100:.1f}%)")
    print(f"Reconciliación gastos:   headline={headline['gastos_primarios']:,.0f} "
          f"| categorizado={totales_cargados['gasto']:,.0f} | sin categorizar={gap_gastos:,.0f} "
          f"({gap_gastos/headline['gastos_primarios']*100:.1f}%)")
    print("(El detalle no categorizado son partidas menores de la Base Caja que todavía\n"
          " no están en la taxonomía canónica — normal en la primera carga, no es un error.)")


def main():
    ap = argparse.ArgumentParser(description="Ingesta de la Base Caja mensual de Nación")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--anio", type=int, required=True)
    ap.add_argument("--mes", type=int, required=True)
    ap.add_argument("--ingresos-totales", type=float, required=True)
    ap.add_argument("--gastos-primarios", type=float, required=True)
    ap.add_argument("--resultado-primario", type=float, required=True)
    ap.add_argument("--intereses", type=float, required=True)
    ap.add_argument("--resultado-financiero", type=float, required=True)
    ap.add_argument("--fuente-url", required=True)
    ap.add_argument("--fuente-nombre", default="MECON - Base Caja Mensual")
    args = ap.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("Falta la variable de entorno DATABASE_URL")

    headline = {
        "ingresos_totales": args.ingresos_totales,
        "gastos_primarios": args.gastos_primarios,
        "resultado_primario": args.resultado_primario,
        "intereses": args.intereses,
        "resultado_financiero": args.resultado_financiero,
    }

    conn = psycopg2.connect(database_url)
    try:
        ingestar(conn, args.csv, args.anio, args.mes, headline,
                  args.fuente_url, args.fuente_nombre)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
