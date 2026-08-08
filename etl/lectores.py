"""
lectores.py — Un lector por fuente oficial.

Cada función abre un archivo y devuelve estructuras Python limpias. Nada más:
no calculan indicadores ni escriben nada. Así, cuando una fuente cambia de
formato, se arregla una sola función y el resto del pipeline no se entera.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path

import openpyxl
import xlrd

from jurisdicciones import HOJA_AIF, REGIONES_IPC, nrm, slug_indec
from taxonomia import CATEGORIAS, HEADLINE, MAPEO_AIF

CTX_INGRESO, CTX_GASTO = "ingreso", "gasto"


def _serial_a_fecha(n):
    """Los .xls guardan fechas como número de días desde 1899-12-30."""
    return datetime(1899, 12, 30) + timedelta(days=float(n))


# =============================================================================
# 1) Serie AIF — el corazón del sitio
# =============================================================================

def _leer_hoja_aif(ws):
    """Devuelve (anios, filas). Cada fila es (etiqueta, bloque, {anio: valor})."""
    fila_hdr = None
    for r in range(1, min(ws.max_row, 20) + 1):
        if nrm(ws.cell(r, 1).value) == "concepto":
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
    bloque = CTX_INGRESO
    for r in range(fila_hdr + 1, ws.max_row + 1):
        etiqueta = nrm(ws.cell(r, 1).value)
        if not etiqueta:
            continue
        # El AIF alterna bloques de ingreso y gasto. Hay conceptos que aparecen
        # en los dos ("Rentas de la propiedad" es ingreso arriba y gasto abajo),
        # así que se distinguen por posición, no por texto.
        if etiqueta.startswith("ii. gastos corrientes"):
            bloque = CTX_GASTO
        elif etiqueta.startswith("iv. ingresos de capital"):
            bloque = CTX_INGRESO
        elif etiqueta.startswith("v. gastos de capital"):
            bloque = CTX_GASTO

        vals = {}
        for c, a in anios:
            v = ws.cell(r, c).value
            if isinstance(v, (int, float)):
                vals[a] = float(v)
        filas.append((etiqueta, bloque, vals))
    return anios, filas


def _anios_vacios(filas, anios):
    """Años donde TODO es cero: la jurisdicción no reportó.

    Un cero real y un 'sin dato' no son lo mismo. Cargar el segundo como cero
    haría que la provincia aparezca como la que menos gasta del país.
    """
    vacios = set()
    for _, a in anios:
        if sum(abs(v.get(a, 0) or 0) for _, _, v in filas) == 0:
            vacios.add(a)
    return vacios


def leer_serie_aif(path):
    """
    Devuelve:
      series      {slug: {anio: {ingresos_totales, gastos_totales, ...}}}
      categorias  {slug: {anio: {slug_categoria: monto}}}
      consolidado {anio: {campo: monto}}   — la hoja oficial de control
      omitidos    {slug: [anios sin datos]}
    """
    # Sin read_only: ese modo está pensado para recorrer fila por fila y hace
    # que el acceso por celda (que es como se lee el AIF) sea muy lento.
    wb = openpyxl.load_workbook(path, data_only=True)
    series, categorias, omitidos = {}, {}, {}
    consolidado = {}

    hojas = list(HOJA_AIF.items())
    if "Consolidado" in wb.sheetnames:
        hojas.append(("Consolidado", "__consolidado__"))

    for hoja, slug in hojas:
        if hoja not in wb.sheetnames:
            continue
        anios, filas = _leer_hoja_aif(wb[hoja])
        if not anios:
            continue

        vacios = _anios_vacios(filas, anios)
        if vacios and slug != "__consolidado__":
            omitidos[slug] = sorted(vacios)

        s_jur, c_jur = {}, {}
        for _, anio in anios:
            if anio in vacios:
                continue
            head, cats = {}, {}
            for etiqueta, bloque, vals in filas:
                if anio not in vals:
                    continue
                monto = vals[anio]

                hl = next((campo for k, campo in HEADLINE.items()
                           if etiqueta.startswith(k)), None)
                if hl:
                    head[hl] = monto
                    continue

                cat = MAPEO_AIF.get(etiqueta)
                if not cat:
                    continue
                # El AIF repite varias etiquetas en los dos bloques:
                # "Transferencias corrientes" es plata que la provincia RECIBE
                # arriba y plata que GIRA abajo; "Rentas de la propiedad" son
                # intereses ganados arriba e intereses pagados abajo.
                # Sumar ambas ocurrencias en una sola categoría inflaba los
                # ingresos de cada provincia en más de un billón de pesos.
                # Cada categoría declara su bloque en taxonomia.py y sólo se
                # toma la ocurrencia que corresponde.
                if CATEGORIAS[cat]["bloque"] != bloque:
                    continue
                cats[cat] = cats.get(cat, 0.0) + monto

            if not head:
                continue
            if head.get("gastos_totales") is not None and head.get("gastos_primarios") is not None:
                head["intereses"] = head["gastos_totales"] - head["gastos_primarios"]
            s_jur[anio] = head
            if cats:
                c_jur[anio] = cats

        if slug == "__consolidado__":
            consolidado = s_jur
        else:
            series[slug] = s_jur
            categorias[slug] = c_jur

    wb.close()
    return series, categorias, consolidado, omitidos


# =============================================================================
# 2) Población — proyecciones INDEC + censo real 2022
# =============================================================================

def leer_proyecciones(path):
    """{slug: {anio: poblacion}} — serie cruda, base Censo 2010."""
    wb = xlrd.open_workbook(path)
    out = {}
    for hoja in wb.sheet_names():
        if hoja == "GraphData":
            continue
        # las hojas se llaman "06-BUENOS AIRES", "82-SANTE FE", ...
        etiqueta = hoja.split("-", 1)[1] if "-" in hoja else hoja
        slug = slug_indec(etiqueta)
        if not slug:
            continue
        sh = wb.sheet_by_name(hoja)
        serie = {}
        for r in range(sh.nrows):
            a, v = sh.cell_value(r, 0), sh.cell_value(r, 1)
            if isinstance(a, float) and 1900 < a < 2100 and isinstance(v, float) and v > 0:
                serie[int(a)] = v
        if serie:
            out[slug] = serie
    return out


def leer_censo(path):
    """{slug: poblacion_2022} — conteo real."""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["cuadro_resumen"]
    out = {}
    for r in range(1, ws.max_row + 1):
        j, v = ws.cell(r, 1).value, ws.cell(r, 2).value
        if not j or not isinstance(v, (int, float)):
            continue
        slug = slug_indec(j)
        if slug:
            out[slug] = float(v)
    wb.close()
    return out


def ajustar_por_censo(proyecciones, censo):
    """
    Reescala cada serie proyectada para que su valor 2022 coincida con el censo.

        factor = censo_2022 / proyectado_2022

    Conserva la FORMA de la proyección (el crecimiento año a año, que es lo que
    la proyección estima bien) y ancla el NIVEL al dato observado. Es el ajuste
    intercensal estándar.

    Sin esto, el gasto por habitante de Santa Cruz quedaría subestimado ~14%
    y el ranking per cápita del sitio sería incorrecto.

    Devuelve (ajustada, diagnostico).
    """
    ajustada, diagnostico = {}, {}
    for slug, serie in proyecciones.items():
        p2022 = serie.get(2022)
        c2022 = censo.get(slug)
        factor = (c2022 / p2022) if (p2022 and c2022) else 1.0
        ajustada[slug] = {a: v * factor for a, v in serie.items()}
        diagnostico[slug] = {
            "proyectada_2022": p2022,
            "censo_2022": c2022,
            "factor": round(factor, 6),
            "desvio_pct": round((c2022 - p2022) / p2022 * 100, 2) if (p2022 and c2022) else None,
        }
    return ajustada, diagnostico


# =============================================================================
# 3) IPC — para poder mostrar pesos constantes
# =============================================================================

def leer_ipc(path):
    """{region: {(anio, mes): indice}} — nivel general, base dic-2016 = 100."""
    wb = xlrd.open_workbook(path)
    sh = wb.sheet_by_name("Índices aperturas")
    out = {}

    for r in range(sh.nrows):
        region = REGIONES_IPC.get(nrm(sh.cell_value(r, 0)))
        if not region:
            continue
        fechas = {}
        for c in range(1, sh.ncols):
            v = sh.cell_value(r, c)
            if isinstance(v, float) and v > 40000:      # serial de fecha
                fechas[c] = _serial_a_fecha(v)
        if not fechas:
            continue
        fila_ng = next((rr for rr in range(r + 1, min(r + 6, sh.nrows))
                        if nrm(sh.cell_value(rr, 0)) == "nivel general"), None)
        if fila_ng is None:
            continue
        serie = {}
        for c, f in fechas.items():
            val = sh.cell_value(fila_ng, c)
            if isinstance(val, float) and val > 0:
                serie[(f.year, f.month)] = val
        if serie:
            out[region] = serie
    return out


# =============================================================================
# 3 bis) Gasto por finalidad y función — en qué se gasta
# =============================================================================

# Cómo se llama cada hoja en serie_ff-apnf.xlsx (difiere del AIF).
HOJA_FF = dict(HOJA_AIF)
HOJA_FF.pop("Ciudad", None)
HOJA_FF.pop("Buenos Aires", None)
HOJA_FF.pop("Santiago del  Estero", None)
HOJA_FF.update({
    "CABA": "caba",
    "Bs Aires": "buenos-aires",
    "Santiago del Estero": "santiago-del-estero",
})


def leer_finalidad(path):
    """
    Devuelve ({slug: {anio: {clave: monto}}}, {slug: {anio: total}}, faltantes).

    Cada registro trae las 5 finalidades y las 9 funciones por separado, nunca
    mezcladas: sumarlas juntas duplicaría todo el bloque social.
    """
    from finalidades import MAPEO_FF

    wb = openpyxl.load_workbook(path, data_only=True)
    datos, totales, faltantes = {}, {}, []

    for hoja, slug in HOJA_FF.items():
        if hoja not in wb.sheetnames:
            faltantes.append(hoja)
            continue
        ws = wb[hoja]

        fila_hdr = next((r for r in range(1, min(ws.max_row, 20) + 1)
                         if nrm(ws.cell(r, 1).value).startswith("finalidad y funcion")), None)
        if fila_hdr is None:
            faltantes.append(hoja)
            continue

        anios = [(c, int(ws.cell(fila_hdr, c).value))
                 for c in range(2, ws.max_column + 1)
                 if isinstance(ws.cell(fila_hdr, c).value, (int, float))
                 and 1990 < ws.cell(fila_hdr, c).value < 2100]

        por_anio, tot_anio = {}, {}
        for r in range(fila_hdr + 1, ws.max_row + 1):
            etiqueta = nrm(ws.cell(r, 1).value)
            if not etiqueta:
                continue
            if etiqueta.startswith("nota"):
                break

            if etiqueta == "total":
                for c, a in anios:
                    v = ws.cell(r, c).value
                    if isinstance(v, (int, float)):
                        tot_anio[a] = float(v)
                continue

            mapeo = MAPEO_FF.get(etiqueta)
            if not mapeo:
                continue
            clave, _nivel = mapeo
            for c, a in anios:
                v = ws.cell(r, c).value
                if isinstance(v, (int, float)):
                    por_anio.setdefault(a, {})[clave] = float(v)

        # Años en cero: la jurisdicción no desagregó ese año.
        por_anio = {a: d for a, d in por_anio.items() if sum(abs(x) for x in d.values()) > 0}
        if por_anio:
            datos[slug] = por_anio
            totales[slug] = {a: v for a, v in tot_anio.items() if a in por_anio}

    wb.close()
    return datos, totales, faltantes


# =============================================================================
# 4) Alícuotas — lo que paga una persona, no lo que recauda la provincia
# =============================================================================

# Encabezado del Excel -> clave del impuesto en el sitio
COLUMNAS_ALICUOTAS = {
    "iibb comercio / servicios":      "iibb-comercio",
    "iibb industria / primario":      "iibb-industria",
    "impuesto de sellos (contratos)": "sellos-contratos",
    "impuesto de sellos (inmuebles)": "sellos-inmuebles",
}


def _alicuota(v):
    """
    Normaliza una celda a {min, max}, ambos en porcentaje.

    El archivo mezcla dos formatos en la misma columna: la mayoría de las
    celdas vienen como texto ("3,5% a 5,0%") y algunas como número de Excel
    (0.045, que es 4,5%). Leer sólo uno de los dos formatos dejaría celdas
    vacías sin que salte ningún error, así que se aceptan los dos y se
    devuelve siempre la misma estructura.
    """
    if v is None:
        return None
    # número de Excel: 0.045 -> 4,5%
    if isinstance(v, (int, float)):
        try:
            if v != v:          # NaN
                return None
        except TypeError:
            return None
        p = round(float(v) * 100, 3)
        return {"min": p, "max": p, "rango": False}

    txt = str(v).strip()
    if not txt:
        return None
    nums = [float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", txt)]
    if not nums:
        return None
    if len(nums) == 1:
        return {"min": nums[0], "max": nums[0], "rango": False}
    lo, hi = min(nums), max(nums)
    return {"min": round(lo, 3), "max": round(hi, 3), "rango": lo != hi}


def leer_alicuotas(path):
    """
    {slug: {impuesto: {min, max, rango}}} — las alícuotas de cada provincia.

    A diferencia del resto del sitio, esto NO sale de una fuente oficial única:
    es una compilación a partir de las leyes impositivas provinciales. Por eso
    el sitio la publica marcada como tal e invita a reportar errores, en vez de
    presentarla con la misma autoridad que la serie del MECON.
    """
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[wb.sheetnames[0]]

    # mapear columnas por su encabezado, no por posición: si mañana el archivo
    # trae una columna nueva o cambia el orden, sigue funcionando.
    cols = {}
    for c in range(2, ws.max_column + 1):
        clave = COLUMNAS_ALICUOTAS.get(nrm(ws.cell(1, c).value))
        if clave:
            cols[c] = clave

    out, sin_reconocer = {}, []
    for r in range(2, ws.max_row + 1):
        etiqueta = ws.cell(r, 1).value
        if not etiqueta:
            continue
        # "Buenos Aires (PBA)" -> se limpia el paréntesis antes de buscar el slug
        limpio = re.sub(r"\s*\([^)]*\)", "", str(etiqueta)).strip()
        slug = slug_indec(limpio)
        if not slug:
            sin_reconocer.append(str(etiqueta))
            continue
        fila = {}
        for c, clave in cols.items():
            a = _alicuota(ws.cell(r, c).value)
            if a:
                fila[clave] = a
        if fila:
            out[slug] = fila

    wb.close()
    return out, sorted(set(cols.values())), sin_reconocer


# =============================================================================
# 5) Mapa — la geometría de las provincias
# =============================================================================

def leer_mapa(path):
    """
    Cruza el catálogo del mapa del IGN con las jurisdicciones del sitio.

    El mapa ya no se dibuja acá: lo dibuja el componente `mapa-argentina.js`,
    que trae la geometría del IGN con Malvinas, las islas del Atlántico Sur y
    el Sector Antártico. Lo que sí hace falta es la tabla de equivalencias
    entre el código INDEC que devuelve el componente y el slug interno, y
    verificar que las 24 crucen.

    Devuelve ({indec: slug}, {slug: nombre oficial del IGN}).
    """
    import json as _json

    catalogo = _json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(catalogo, dict):
        catalogo = list(catalogo.values())

    # El slug lo manda SIEMPRE el sitio, nunca el archivo externo. El mapa del
    # IGN llama a la 94 "tierra-del-fuego-antartida-e-islas-del-atlantico-sur"
    # y acá es "tierra-del-fuego": copiar el suyo mandaba el click a una ficha
    # que no existe, sin romper el build ni disparar ningún error.
    from jurisdicciones import JURISDICCIONES
    mio_por_indec = {m["indec"]: s for s, m in JURISDICCIONES.items()}

    por_indec, nombres, ajenos = {}, {}, {}
    for x in catalogo:
        ind = str(x.get("indec", "")).zfill(2)
        slug_sitio = mio_por_indec.get(ind)
        if not slug_sitio:
            continue
        por_indec[ind] = slug_sitio
        nombres[slug_sitio] = x.get("nombreCompleto") or x.get("nombre")
        if x.get("slug") and x["slug"] != slug_sitio:
            ajenos[slug_sitio] = x["slug"]
    return por_indec, nombres, ajenos


def ipc_anual(ipc_mensual):
    """
    Promedio anual del índice por región. Sólo se calcula para años con los
    12 meses: un promedio de 3 meses no es comparable con uno de 12 y produciría
    un deflactor sesgado.

    Devuelve ({region: {anio: indice}}, {region: [anios incompletos]}).
    """
    anual, parciales = {}, {}
    for region, serie in ipc_mensual.items():
        por_anio = {}
        for (a, m), v in serie.items():
            por_anio.setdefault(a, []).append(v)
        anual[region] = {a: sum(vs) / len(vs) for a, vs in por_anio.items() if len(vs) == 12}
        parciales[region] = sorted(a for a, vs in por_anio.items() if len(vs) != 12)
    return anual, parciales
