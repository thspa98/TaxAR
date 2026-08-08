#!/usr/bin/env python3
"""
exportar_json.py — Convierte las fuentes oficiales en los datos del sitio.

    python etl/exportar_json.py

Lee los archivos de `fuentes/`, corre los controles de calidad y escribe
`web/src/data/*.json`. El sitio no consulta ninguna base de datos: lee esos
JSON, que quedan versionados junto al código. Eso hace que cada número
publicado sea rastreable hasta el archivo oficial que lo originó — que es
justamente lo que se le pide a un sitio de transparencia.

Si algún control da ERROR, no se escribe nada.

Archivos que genera:
    meta.json           qué se generó, cuándo, con qué fuentes y qué controles
    jurisdicciones.json catálogo de las 24 + población por año
    series.json         ingresos, gastos y resultados por jurisdicción y año
    categorias.json     de dónde sale y en qué se va la plata, por año
    ipc.json            índices y deflactores por región
    rankings.json       tops ya calculados, listos para mostrar
    glosario.json       explicaciones en lenguaje llano
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import controles
import fuentes as F
import lectores as L
from jurisdicciones import JURISDICCIONES, region
from finalidades import (ANIOS_ESTIMADOS, FINALIDADES, FUNCIONES, NOTA_ESTIMADOS)
from taxonomia import BASES_IMPONIBLES, CATEGORIAS, GLOSARIO, IMPUESTOS

ANIO_BASE_MIN = 2010     # antes de 2010 no hay proyecciones de población


# =============================================================================
# Cálculos derivados
# =============================================================================

def calcular_deflactores(ipc_anual_por_region):
    """
    Deflactor de cada año, expresado en pesos del año más reciente completo.

        deflactor = indice_base / indice_del_anio

    Multiplicar un monto nominal por su deflactor lo lleva a pesos de hoy.
    """
    out, base = {}, {}
    for reg, serie in ipc_anual_por_region.items():
        if not serie:
            continue
        anio_base = max(serie)
        base[reg] = anio_base
        out[reg] = {a: serie[anio_base] / v for a, v in serie.items()}
    return out, base


def per_capita(gasto_millones, poblacion):
    """Millones de $ y habitantes -> $ por habitante."""
    if not gasto_millones or not poblacion:
        return None
    return gasto_millones * 1_000_000 / poblacion


def presion_impositiva(cats, poblacion):
    """
    Cuánto recauda la provincia en impuestos PROPIOS por cada habitante.

    ADVERTENCIA METODOLÓGICA — esto NO es la presión impositiva en el sentido
    técnico. La presión impositiva se define como recaudación sobre el producto
    bruto geográfico: qué porcentaje de lo que produce una provincia se lleva
    el fisco. Para calcularla haría falta el PBG por provincia, que INDEC no
    publica de forma sistemática ni comparable entre jurisdicciones.

    Lo que sí se puede calcular con datos oficiales y comparables es esto: los
    pesos de Ingresos Brutos, Inmobiliario, Automotor y Sellos que recauda la
    provincia dividido por su población. Es un proxy razonable y directo — es
    literalmente cuánto le sacan al habitante promedio — pero sube en provincias
    ricas simplemente porque hay más actividad para gravar, no porque las
    alícuotas sean más altas.

    El sitio lo llama por su nombre exacto ("impuestos provinciales por
    habitante") y explica la diferencia, en vez de titular "presión impositiva"
    y dejar que el lector saque una conclusión que el dato no sostiene.
    """
    propios = cats.get("impuestos-propios")
    if propios is None or not poblacion:
        return None
    return propios * 1_000_000 / poblacion


def dependencia(cats):
    """
    % de la recaudación tributaria que llega de la Nación en vez de recaudarla
    la provincia. Es el indicador que mejor explica el federalismo fiscal
    argentino a alguien sin formación económica.
    """
    nac = cats.get("coparticipacion")
    prov = cats.get("impuestos-propios")
    if nac is None or prov is None or (nac + prov) == 0:
        return None
    return nac / (nac + prov) * 100


# =============================================================================
# Armado de cada archivo
# =============================================================================

def armar_jurisdicciones(poblacion, diagnostico, series):
    out = {}
    for slug, meta in JURISDICCIONES.items():
        pob = poblacion.get(slug, {})
        d = diagnostico.get(slug, {})
        anios_jur = sorted(series.get(slug, {}))
        out[slug] = {
            "slug": slug,
            **meta,
            # Último año con dato propio. Puede ser anterior al de referencia
            # del sitio si la jurisdicción no reportó; la ficha lo avisa.
            "ultimo_anio": max(anios_jur) if anios_jur else None,
            "poblacion": {str(a): round(v) for a, v in sorted(pob.items())},
            "censo2022": round(d["censo_2022"]) if d.get("censo_2022") else None,
            "ajuste_censal": {
                "factor": d.get("factor"),
                "desvio_pct": d.get("desvio_pct"),
                "proyeccion_indec_2022": round(d["proyectada_2022"]) if d.get("proyectada_2022") else None,
            },
        }
    return out


def armar_series(series, poblacion, deflactores, categorias):
    """Serie principal: un registro por jurisdicción y año, con todo resuelto."""
    out = {}
    for slug, serie in series.items():
        reg = region(slug)
        defl_reg = deflactores.get(reg, {})
        filas = []
        for anio in sorted(serie):
            d = serie[anio]
            pob = poblacion.get(slug, {}).get(anio)
            gt = d.get("gastos_totales")
            it = d.get("ingresos_totales")
            k = defl_reg.get(anio)
            cats = categorias.get(slug, {}).get(anio, {})
            filas.append({
                "anio": anio,
                "ingresos_totales": _n(it),
                "gastos_totales": _n(gt),
                "gastos_primarios": _n(d.get("gastos_primarios")),
                "resultado_financiero": _n(d.get("resultado_financiero")),
                "resultado_primario": _n(d.get("resultado_primario")),
                "resultado_economico": _n(d.get("resultado_economico")),
                "intereses": _n(d.get("intereses")),
                "poblacion": round(pob) if pob else None,
                "gasto_per_capita": _n(per_capita(gt, pob), 0),
                "ingreso_per_capita": _n(per_capita(it, pob), 0),
                # pesos constantes: None cuando no hay IPC, nunca un valor inventado
                "gastos_constantes": _n(gt * k) if (gt is not None and k) else None,
                "ingresos_constantes": _n(it * k) if (it is not None and k) else None,
                "deflactor": round(k, 4) if k else None,
                "dependencia_nacion": _n(dependencia(cats), 1),
                "impuestos_propios": _n(cats.get("impuestos-propios")),
                "impuestos_por_habitante": _n(presion_impositiva(cats, pob), 0),
                "coparticipacion": _n(cats.get("coparticipacion")),
                "coparticipacion_por_habitante": _n(
                    cats["coparticipacion"] * 1_000_000 / pob, 0)
                    if (cats.get("coparticipacion") is not None and pob) else None,
                "resultado_sobre_ingresos": _n(d["resultado_financiero"] / it * 100, 1)
                    if (it and d.get("resultado_financiero") is not None) else None,
            })
        out[slug] = filas

    _agregar_reparto(out)
    return out


def _agregar_reparto(series_json):
    """
    Compara la tajada de coparticipación de cada provincia con su tajada de
    población. Es el número que explica el régimen de un vistazo.

        indice = (% de la coparticipación que recibe) / (% de la población que tiene)

    Un índice de 1 significa que recibe exactamente lo proporcional a su gente.
    Por encima, recibe más; por debajo, menos.

    No es un error del sistema: los coeficientes de la Ley 23.548 se fijaron en
    1988 y no se actualizan por población, así que las provincias que más
    crecieron desde entonces reciben cada año una porción menor por habitante.
    Sí es el dato que casi nunca se muestra.
    """
    anios = {f["anio"] for filas in series_json.values() for f in filas}
    for anio in anios:
        tc = tp = 0.0
        for filas in series_json.values():
            f = next((x for x in filas if x["anio"] == anio), None)
            if f and f.get("coparticipacion") and f.get("poblacion"):
                tc += f["coparticipacion"]
                tp += f["poblacion"]
        if not tc or not tp:
            continue
        for filas in series_json.values():
            f = next((x for x in filas if x["anio"] == anio), None)
            if not f or not f.get("coparticipacion") or not f.get("poblacion"):
                continue
            sc = f["coparticipacion"] / tc * 100
            sp = f["poblacion"] / tp * 100
            f["share_coparticipacion"] = round(sc, 3)
            f["share_poblacion"] = round(sp, 3)
            f["indice_reparto"] = round(sc / sp, 3)


def armar_finalidad(datos, totales, poblacion):
    """
    En qué gasta cada provincia: monto, porcentaje del total y por habitante.

    El porcentaje es lo que permite comparar provincias de tamaños muy
    distintos; el per cápita, lo que permite decir si una escuela o un hospital
    recibe más o menos plata por persona atendida.
    """
    out = {"finalidades": FINALIDADES, "funciones": FUNCIONES,
           "anios_estimados": ANIOS_ESTIMADOS, "nota_estimados": NOTA_ESTIMADOS,
           "fuente": F.cita("serie_ff"), "datos": {}, "rankings": {}}

    for slug, por_anio in datos.items():
        filas = []
        for anio in sorted(por_anio):
            d = por_anio[anio]
            tot = totales.get(slug, {}).get(anio)
            pob = poblacion.get(slug, {}).get(anio)
            fila = {"anio": anio, "total": _n(tot), "estimado": anio in ANIOS_ESTIMADOS}
            for k in list(FINALIDADES) + list(FUNCIONES):
                v = d.get(k)
                if v is None:
                    continue
                fila[k] = _n(v)
                if tot:
                    fila[f"{k}_pct"] = _n(v / tot * 100, 2)
                if pob:
                    fila[f"{k}_hab"] = _n(v * 1_000_000 / pob, 0)
            filas.append(fila)
        out["datos"][slug] = filas

    # rankings por año de las funciones que más le importan al lector
    anios = sorted({f["anio"] for fs in out["datos"].values() for f in fs})
    for anio in anios:
        r = {}
        for campo in ("salud_hab", "educacion_hab", "salud_pct", "educacion_pct",
                      "seguridad_hab", "administracion_pct"):
            datos_campo = []
            for slug, fs in out["datos"].items():
                f = next((x for x in fs if x["anio"] == anio), None)
                if f and f.get(campo) is not None:
                    datos_campo.append((slug, f[campo]))
            datos_campo.sort(key=lambda x: x[1], reverse=True)
            if datos_campo:
                r[campo] = [{"slug": s, "valor": v, "puesto": i + 1}
                            for i, (s, v) in enumerate(datos_campo)]
        if r:
            out["rankings"][str(anio)] = r
    return out


def armar_categorias(categorias):
    out = {}
    for slug, por_anio in categorias.items():
        out[slug] = {str(a): {k: _n(v) for k, v in sorted(c.items())}
                     for a, c in sorted(por_anio.items())}
    return out


def armar_rankings(series_json):
    """
    Rankings ya ordenados, por año. Se calculan una sola vez acá en vez de en
    el navegador: el sitio queda más rápido y, sobre todo, el número que ve el
    lector se calcula en un único lugar auditable.
    """
    anios = sorted({f["anio"] for filas in series_json.values() for f in filas})
    out = {}
    for anio in anios:
        fila = {}
        for slug, filas in series_json.items():
            f = next((x for x in filas if x["anio"] == anio), None)
            if f:
                fila[slug] = f
        if not fila:
            continue

        def top(campo, reverse=True):
            datos = [(s, f[campo]) for s, f in fila.items() if f.get(campo) is not None]
            datos.sort(key=lambda x: x[1], reverse=reverse)
            return [{"slug": s, "valor": v, "puesto": i + 1}
                    for i, (s, v) in enumerate(datos)]

        out[str(anio)] = {
            "gasto_total": top("gastos_totales"),
            "gasto_per_capita": top("gasto_per_capita"),
            "dependencia_nacion": top("dependencia_nacion"),
            "resultado_sobre_ingresos": top("resultado_sobre_ingresos"),
            "impuestos_por_habitante": top("impuestos_por_habitante"),
            "coparticipacion_por_habitante": top("coparticipacion_por_habitante"),
        }
    return out


def armar_ipc(ipc_mensual, ipc_anual, deflactores, anios_base, parciales):
    return {
        "mensual": {reg: {f"{a}-{m:02d}": round(v, 4) for (a, m), v in sorted(s.items())}
                    for reg, s in ipc_mensual.items()},
        "anual": {reg: {str(a): round(v, 4) for a, v in sorted(s.items())}
                  for reg, s in ipc_anual.items()},
        "deflactores": {reg: {str(a): round(v, 6) for a, v in sorted(s.items())}
                        for reg, s in deflactores.items()},
        "anio_base": {reg: a for reg, a in anios_base.items()},
        "anios_incompletos": parciales,
        "nota": "El IPC oficial de INDEC arranca en dic-2016, así que los años "
                "fiscales 2005-2016 no se pueden deflactar con esta fuente. Además, "
                "el IPC 2007-2015 está cuestionado por la intervención del INDEC en "
                "ese período: completar la serie exige elegir una fuente alternativa "
                "(San Luis, CABA o series privadas reconstruidas) y explicitar la "
                "decisión. Mientras tanto el sitio muestra 'sin dato'.",
        "fuente": F.cita("ipc"),
    }


def _n(v, dec=2):
    """Redondeo consistente. None se preserva: 'sin dato' no es cero."""
    return None if v is None else round(v, dec)


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 78)
    print("TaxAR — generación de los datos del sitio")
    print("=" * 78)

    print("\nLeyendo fuentes oficiales…")
    series, categorias, consolidado, omitidos = L.leer_serie_aif(F.ruta("serie_aif"))
    print(f"  serie AIF          {len(series)} jurisdicciones, "
          f"{sum(len(s) for s in series.values())} años-jurisdicción")

    proy = L.leer_proyecciones(F.ruta("poblacion_proyecciones"))
    censo = L.leer_censo(F.ruta("poblacion_censo"))
    poblacion, diagnostico = L.ajustar_por_censo(proy, censo)
    print(f"  población          {len(poblacion)} jurisdicciones (ajustada al Censo 2022)")

    mapa_indec, mapa_nombres, mapa_ajenos = L.leer_mapa(F.ruta("mapa"))
    print(f"  mapa IGN           {len(mapa_indec)} jurisdicciones cruzadas por código INDEC")

    ff_datos, ff_tot, ff_faltan = L.leer_finalidad(F.ruta("serie_ff"))
    print(f"  finalidad/función  {len(ff_datos)} jurisdicciones, "
          f"{sum(len(v) for v in ff_datos.values())} años-jurisdicción")

    alic, impuestos_alic, sin_reconocer = L.leer_alicuotas(F.ruta("alicuotas"))
    print(f"  alícuotas          {len(alic)} jurisdicciones × {len(impuestos_alic)} impuestos")

    ipc_mensual = L.leer_ipc(F.ruta("ipc"))
    ipc_a, parciales = L.ipc_anual(ipc_mensual)
    deflactores, anios_base = calcular_deflactores(ipc_a)
    print(f"  IPC                {len(ipc_mensual)} regiones, "
          f"{sum(len(s) for s in ipc_mensual.values())} observaciones mensuales")

    # deflactores mapeados por jurisdicción, para el control
    defl_por_jur = {s: deflactores.get(region(s), {}) for s in series}

    resultados = controles.correr_todos(
        series, consolidado, omitidos, poblacion, diagnostico, defl_por_jur,
        categorias, (mapa_indec, mapa_nombres, mapa_ajenos), (alic, impuestos_alic, sin_reconocer),
        (ff_datos, ff_tot, ff_faltan))
    errores = controles.imprimir(resultados)
    if errores:
        print("\nNo se escribió ningún archivo: hay controles en ERROR.")
        return 1

    print("\nGenerando archivos…")
    F.DIR_SALIDA.mkdir(parents=True, exist_ok=True)

    juris = armar_jurisdicciones(poblacion, diagnostico, series)
    series_json = armar_series(series, poblacion, deflactores, categorias)
    rankings = armar_rankings(series_json)

    anios = sorted({f["anio"] for fs in series_json.values() for f in fs})

    # El sitio encabeza con el año MÁS RECIENTE disponible, no con el último
    # completo: un dato de hace dos años es peor servicio que un dato reciente
    # al que le falta una provincia.
    #
    # Pero el faltante no se puede ocultar. Se registra acá quién no reportó
    # cada año, para que el sitio lo diga en voz alta —en el ranking, en los
    # totales del país y en la ficha de esa provincia— en vez de mostrar 23
    # jurisdicciones haciendo de cuenta que son 24.
    anio_ref = max(anios)
    sin_reporte = {}
    for a in anios:
        faltan = sorted(s for s, fs in series_json.items()
                        if not any(f["anio"] == a for f in fs))
        if faltan:
            sin_reporte[str(a)] = faltan
    completos = [a for a in anios if str(a) not in sin_reporte]

    meta = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "universo": F.UNIVERSO,
        "tipo_dato": F.TIPO_DATO,
        "base_contable": F.BASE_CONTABLE,
        "unidad": "millones de pesos corrientes",
        "cobertura": {
            "jurisdicciones": len(series),
            "anio_desde": min(anios),
            "anio_hasta": max(anios),
            "anio_referencia": anio_ref,
            "anio_ultimo_completo": max(completos) if completos else anio_ref,
            "sin_reporte": sin_reporte,
        },
        "advertencia_comparabilidad":
            "Todas las cifras corresponden al mismo universo (Administración Pública "
            "No Financiera), el mismo tipo de dato (ejecutado) y la misma base contable "
            "(devengado). Mezclar universos distintos cambia los resultados de forma "
            "drástica: el resultado financiero de Córdoba 2026 es 439.906 M en "
            "administración central pero 12.996 M contando la APNF, porque la Caja de "
            "Jubilaciones tiene un déficit de 418.575 M. Es una diferencia de 34 veces.",
        "fuentes": {k: F.cita(k) for k in F.FUENTES},
        "controles": resultados,
    }

    salidas = {
        "meta.json": meta,
        "jurisdicciones.json": juris,
        "series.json": series_json,
        "categorias.json": armar_categorias(categorias),
        "ipc.json": armar_ipc(ipc_mensual, ipc_a, deflactores, anios_base, parciales),
        "rankings.json": rankings,
        "glosario.json": {"categorias": CATEGORIAS, "conceptos": GLOSARIO},
        "mapa.json": {
            "indec_a_slug": mapa_indec,
            "slug_a_indec": {s: i for i, s in mapa_indec.items()},
            "nombres_ign": mapa_nombres,
            "fuente": F.cita("mapa"),
            "atribucion": F.FUENTES["mapa"]["atribucion_obligatoria"],
            "nota_territorio":
                "El mapa dibuja el territorio tal como lo define el Instituto Geográfico "
                "Nacional, incluidos las Islas Malvinas, las Georgias del Sur, las Sandwich "
                "del Sur y el Sector Antártico Argentino, que integran la provincia de "
                "Tierra del Fuego, Antártida e Islas del Atlántico Sur. Las cifras fiscales "
                "del sitio, en cambio, corresponden a la actividad continental: es lo que "
                "las provincias ejecutan y reportan.",
        },
        "finalidad.json": armar_finalidad(ff_datos, ff_tot, poblacion),
        "alicuotas.json": {
            "impuestos": IMPUESTOS,
            "orden": impuestos_alic,
            "bases": BASES_IMPONIBLES,
            "datos": alic,
            "fuente": F.cita("alicuotas"),
            "revisada_por_terceros": F.FUENTES["alicuotas"]["revisada_por_terceros"],
            "advertencia":
                "Estas alícuotas son una compilación a partir de las leyes impositivas "
                "provinciales, no una publicación oficial única como el resto de los datos "
                "del sitio. Cada provincia tiene además alícuotas diferenciales por nivel "
                "de facturación, por actividad y por si el contribuyente está o no radicado "
                "en la jurisdicción, así que el número que te toca puede diferir. Si ves un "
                "error, escribinos: se corrige.",
        },
    }

    for nombre_archivo, contenido in salidas.items():
        destino = F.DIR_SALIDA / nombre_archivo
        destino.write_text(
            json.dumps(contenido, ensure_ascii=False, indent=1, sort_keys=False),
            encoding="utf-8")
        kb = destino.stat().st_size / 1024
        print(f"  {nombre_archivo:<22} {kb:>8.1f} KB")

    print(f"\nListo. {len(salidas)} archivos en {F.DIR_SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
