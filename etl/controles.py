"""
controles.py — Verificación automática de los datos antes de publicarlos.

Los cuatro errores más graves que aparecieron en este proyecto no los
encontró nadie leyendo: los encontraron controles como estos.

  · La Pampa 2025 venía toda en cero — la habría mostrado como la provincia
    que menos gasta del país.
  · La hoja de Córdoba 2021 era copia exacta de 2020.
  · INDEC escribió "SANTE FE" y Santa Fe desaparecía de los rankings per
    cápita sin ningún error visible.
  · Una extracción de PDF tomaba el subtotal del bloque de páginas
    equivocado: 0,55% de diferencia, invisible a ojo.

Regla del proyecto: toda fuente nueva trae su propio control contra un total
publicado por el organismo, más un control de cobertura que confirme que no
falta ninguna jurisdicción.

Severidades:
  error   — no se publica; hay que arreglarlo
  aviso   — se publica, pero el sitio debe aclararlo al lector
  ok      — verificado
"""

from jurisdicciones import JURISDICCIONES, nombre

TOLERANCIA_CONSOLIDADO = 0.5   # % de diferencia admitido contra la hoja oficial
TOLERANCIA_IDENTIDAD = 1.0     # millones de $ (redondeo de la fuente)


def _r(control, severidad, detalle, **extra):
    return {"control": control, "severidad": severidad, "detalle": detalle, **extra}


def control_cobertura(series, poblacion):
    """¿Está cada jurisdicción esperada, y tiene población?"""
    res = []
    faltan_fiscal = sorted(set(JURISDICCIONES) - set(series))
    if faltan_fiscal:
        res.append(_r("cobertura_fiscal", "error",
                      f"Sin datos fiscales: {', '.join(faltan_fiscal)}. "
                      "Revisar los nombres de hoja en el archivo AIF."))
    else:
        res.append(_r("cobertura_fiscal", "ok",
                      f"Las {len(JURISDICCIONES)} jurisdicciones tienen serie fiscal."))

    faltan_pob = sorted(set(JURISDICCIONES) - set(poblacion))
    if faltan_pob:
        res.append(_r("cobertura_poblacion", "error",
                      f"Sin población: {', '.join(faltan_pob)}. "
                      "Suele ser un typo en los nombres de hoja de INDEC "
                      "(ya pasó con 'SANTE FE'). Agregar el alias en jurisdicciones.py."))
    else:
        res.append(_r("cobertura_poblacion", "ok",
                      f"Las {len(JURISDICCIONES)} jurisdicciones tienen población."))
    return res


def control_suma_consolidado(series, consolidado):
    """La suma de las 24 jurisdicciones debe reproducir la hoja Consolidado.

    Es el control más fuerte que tiene el pipeline: si el mapeo de filas o la
    lectura de columnas estuvieran mal, esta suma no cerraría.
    """
    if not consolidado:
        return [_r("suma_consolidado", "aviso",
                   "El archivo no trae hoja Consolidado: no se pudo verificar la suma.")]
    peor, detalle_peor = 0.0, None
    comparados = 0
    for anio, oficial in sorted(consolidado.items()):
        ofi = oficial.get("gastos_totales")
        if not ofi:
            continue
        suma = sum(s[anio]["gastos_totales"] for s in series.values()
                   if anio in s and s[anio].get("gastos_totales") is not None)
        dif = abs(suma - ofi) / ofi * 100
        comparados += 1
        if dif > peor:
            peor, detalle_peor = dif, (anio, suma, ofi)

    if peor > TOLERANCIA_CONSOLIDADO:
        a, suma, ofi = detalle_peor
        return [_r("suma_consolidado", "error",
                   f"En {a} la suma de las jurisdicciones ({suma:,.0f} M) no coincide "
                   f"con el Consolidado oficial ({ofi:,.0f} M): {peor:.3f}% de diferencia.")]
    return [_r("suma_consolidado", "ok",
               f"La suma de las jurisdicciones reproduce el Consolidado oficial en "
               f"{comparados} años (peor diferencia: {peor:.3f}%).")]


def control_identidad_contable(series):
    """Ingresos totales − Gastos totales = Resultado financiero."""
    fallas = []
    revisadas = 0
    for slug, serie in series.items():
        for anio, d in serie.items():
            i, g, rf = d.get("ingresos_totales"), d.get("gastos_totales"), d.get("resultado_financiero")
            if None in (i, g, rf):
                continue
            revisadas += 1
            if abs((i - g) - rf) > TOLERANCIA_IDENTIDAD:
                fallas.append(f"{nombre(slug)} {anio}")
    if fallas:
        return [_r("identidad_contable", "error",
                   f"{len(fallas)} series no cumplen Ingresos − Gastos = Resultado: "
                   f"{', '.join(fallas[:6])}{'…' if len(fallas) > 6 else ''}")]
    return [_r("identidad_contable", "ok",
               f"Las {revisadas} series cumplen Ingresos − Gastos = Resultado financiero.")]


def control_anios_omitidos(omitidos):
    """Años que la fuente trajo en cero y el pipeline descartó."""
    if not omitidos:
        return [_r("anios_sin_reporte", "ok", "Ninguna jurisdicción dejó años sin reportar.")]
    partes = [f"{nombre(s)} ({', '.join(map(str, a))})" for s, a in sorted(omitidos.items())]
    return [_r("anios_sin_reporte", "aviso",
               "Años descartados por venir con todos los valores en cero — la "
               "jurisdicción no reportó. Se omiten en vez de cargarse como cero, "
               "que los haría aparecer como el gasto más bajo del país: "
               + "; ".join(partes),
               afectados={s: a for s, a in omitidos.items()})]


def control_duplicados(series):
    """Años consecutivos idénticos: casi siempre una hoja copiada en el original.

    Pasó de verdad: la hoja de Córdoba 2021 en el archivo de presupuestos era
    copia exacta de 2020, con 220 celdas idénticas y el número de ley vacío.
    """
    sospechas = []
    for slug, serie in series.items():
        anios = sorted(serie)
        for a, b in zip(anios, anios[1:]):
            if b - a != 1:
                continue
            if serie[a] and serie[a] == serie[b]:
                sospechas.append(f"{nombre(slug)}: {a} y {b} son idénticos")
    if sospechas:
        return [_r("duplicados", "aviso",
                   "Años consecutivos con valores idénticos, posible hoja duplicada "
                   "en la fuente: " + "; ".join(sospechas))]
    return [_r("duplicados", "ok", "No hay años consecutivos idénticos.")]


def control_categorias_vs_totales(series, categorias):
    """El desglose nunca puede superar al total que dice la propia fuente.

    Es un control de sanidad barato que atrapa la clase de error más difícil de
    ver: una etiqueta que aparece dos veces en el archivo y se suma dos veces en
    una sola categoría. Pasó con "Transferencias corrientes", que en el AIF está
    tanto en el bloque de ingresos (lo que la provincia recibe) como en el de
    gastos (lo que gira a municipios y privados). Sumar ambas inflaba los
    ingresos de cada provincia en más de un billón de pesos, sin romper nada:
    los totales seguían bien y la identidad contable seguía cerrando.
    """
    from taxonomia import CATEGORIAS
    fallas = []
    for slug, por_anio in categorias.items():
        for anio, cats in por_anio.items():
            d = series.get(slug, {}).get(anio, {})
            for bloque, campo in (("ingreso", "ingresos_totales"), ("gasto", "gastos_totales")):
                total = d.get(campo)
                if not total:
                    continue
                suma = sum(v for k, v in cats.items() if CATEGORIAS[k]["bloque"] == bloque)
                if suma > total * 1.001:
                    fallas.append(f"{nombre(slug)} {anio} {bloque}: "
                                  f"desglose {suma:,.0f} > total {total:,.0f}")
    if fallas:
        return [_r("desglose_vs_total", "error",
                   f"{len(fallas)} casos donde la suma de las categorías supera al total "
                   f"declarado por la fuente. Suele ser una etiqueta contada dos veces: "
                   f"{fallas[0]}" + (f" (y {len(fallas)-1} más)" if len(fallas) > 1 else ""))]
    return [_r("desglose_vs_total", "ok",
               "En todas las series el desglose por categoría cierra dentro del total.")]


def control_mapa(por_indec, nombres, ajenos=None):
    """Las 24 jurisdicciones tienen que cruzar con el mapa del IGN por código INDEC.

    Si un código no cruza, esa provincia queda muerta en el mapa: se dibuja
    pero al hacerle click no pasa nada, y el sitio compila igual.
    """
    esperados = {m["indec"]: s for s, m in JURISDICCIONES.items()}
    faltan = sorted(nombre(s) for i, s in esperados.items() if i not in por_indec)
    sobran = sorted(set(por_indec) - set(esperados))
    res = []
    if faltan:
        res.append(_r("cobertura_mapa", "error",
                      f"Sin contorno en el mapa: {', '.join(faltan)}. "
                      "Revisar los códigos INDEC en provincias.json."))
    elif sobran:
        res.append(_r("cobertura_mapa", "aviso",
                      f"El mapa trae códigos que el sitio no conoce: {', '.join(sobran)}."))
    else:
        res.append(_r("cobertura_mapa", "ok",
                      f"Las {len(por_indec)} jurisdicciones cruzan con el mapa del IGN "
                      "por código INDEC."))

    # Todo slug que salga del mapa tiene que existir como ficha del sitio. Si no,
    # el click lleva a un 404 y nada lo avisa.
    huerfanos = sorted(set(por_indec.values()) - set(JURISDICCIONES))
    if huerfanos:
        res.append(_r("mapa_slugs", "error",
                      f"El mapa devuelve slugs sin ficha: {', '.join(huerfanos)}. "
                      "El click llevaría a una página inexistente."))
    else:
        res.append(_r("mapa_slugs", "ok",
                      "Cada provincia del mapa apunta a una ficha que existe."))

    if ajenos:
        pares = ", ".join(f"{nombre(s)} (el mapa la llama '{a}')" for s, a in sorted(ajenos.items()))
        res.append(_r("mapa_slugs_distintos", "aviso",
                      f"El mapa usa otro slug para {len(ajenos)} jurisdicción(es); se usa el "
                      f"del sitio: {pares}."))
    return res


def control_alicuotas(alicuotas, impuestos, sin_reconocer):
    """Cobertura del cuadro de alícuotas y avisos de lectura."""
    res = []
    if sin_reconocer:
        res.append(_r("alicuotas_nombres", "error",
                      f"No se reconocieron estas jurisdicciones del cuadro de alícuotas: "
                      f"{', '.join(sin_reconocer)}. Agregar el alias en ALIAS_INDEC."))

    faltan = sorted(set(JURISDICCIONES) - set(alicuotas))
    if faltan:
        res.append(_r("alicuotas_cobertura", "aviso",
                      f"Sin alícuotas cargadas: {', '.join(nombre(s) for s in faltan)}. "
                      "El sitio muestra 'sin dato' para esas jurisdicciones."))
    else:
        res.append(_r("alicuotas_cobertura", "ok",
                      f"Las {len(alicuotas)} jurisdicciones tienen alícuotas, "
                      f"para {len(impuestos)} impuestos."))

    huecos = []
    for slug, d in alicuotas.items():
        faltantes = [i for i in impuestos if i not in d]
        if faltantes:
            huecos.append(f"{nombre(slug)} ({', '.join(faltantes)})")
    if huecos:
        res.append(_r("alicuotas_huecos", "aviso",
                      "Celdas vacías en el cuadro: " + "; ".join(huecos[:6])
                      + (f" y {len(huecos)-6} más" if len(huecos) > 6 else "")))

    # Rangos absurdos: una alícuota provincial fuera de 0-30% es casi seguro un
    # error de tipeo o de unidad (un 0,035 leído como 3,5 en vez de 0,35).
    raros = [f"{nombre(s)} {i}: {v['min']}-{v['max']}%"
             for s, d in alicuotas.items() for i, v in d.items()
             if v["max"] > 30 or v["min"] < 0]
    if raros:
        res.append(_r("alicuotas_rango", "error",
                      "Alícuotas fuera de un rango plausible (0-30%), probable error de "
                      "unidad: " + "; ".join(raros[:5])))
    else:
        res.append(_r("alicuotas_rango", "ok",
                      "Todas las alícuotas caen dentro de un rango plausible."))
    return res


def control_finalidad(datos, totales, faltantes):
    """
    Verifica las dos sumas de la clasificación funcional.

      1. Las 5 finalidades tienen que dar el TOTAL que declara el archivo.
      2. Las 9 funciones tienen que dar exactamente "Servicios sociales".

    Si alguna no cierra, o el mapeo de filas está mal o se está contando un
    nivel dentro del otro — el error que ya apareció dos veces en este proyecto
    con otras fuentes.
    """
    from finalidades import FINALIDADES, FUNCIONES

    res = []
    if faltantes:
        res.append(_r("finalidad_hojas", "error",
                      f"Hojas del archivo de finalidad no reconocidas: {', '.join(faltantes)}."))

    falt_jur = sorted(set(JURISDICCIONES) - set(datos))
    if falt_jur:
        res.append(_r("finalidad_cobertura", "aviso",
                      f"Sin gasto por finalidad: {', '.join(nombre(s) for s in falt_jur)}."))
    else:
        n = sum(len(v) for v in datos.values())
        res.append(_r("finalidad_cobertura", "ok",
                      f"Las {len(datos)} jurisdicciones tienen gasto por finalidad "
                      f"({n} años-jurisdicción)."))

    malas_fin, malas_fun = [], []
    for slug, por_anio in datos.items():
        for anio, d in por_anio.items():
            tot = totales.get(slug, {}).get(anio)
            if tot:
                suma = sum(d.get(k, 0) for k in FINALIDADES)
                if abs(suma - tot) > max(1.0, tot * 0.005):
                    malas_fin.append(f"{nombre(slug)} {anio}: {suma:,.0f} vs {tot:,.0f}")
            social = d.get("social")
            if social:
                suma_f = sum(d.get(k, 0) for k in FUNCIONES)
                if abs(suma_f - social) > max(1.0, social * 0.005):
                    malas_fun.append(f"{nombre(slug)} {anio}: {suma_f:,.0f} vs {social:,.0f}")

    if malas_fin:
        res.append(_r("finalidad_suma_total", "error",
                      f"{len(malas_fin)} casos donde las 5 finalidades no dan el total "
                      f"declarado: {malas_fin[0]}"))
    else:
        res.append(_r("finalidad_suma_total", "ok",
                      "En todas las series las cinco finalidades suman el total del archivo."))

    if malas_fun:
        res.append(_r("finalidad_suma_social", "error",
                      f"{len(malas_fun)} casos donde las funciones no dan Servicios sociales: "
                      f"{malas_fun[0]}"))
    else:
        res.append(_r("finalidad_suma_social", "ok",
                      "En todas las series las funciones suman exactamente Servicios sociales."))
    return res


def control_deflactabilidad(series, ipc_por_anio):
    """Qué proporción de la serie se puede expresar en pesos constantes."""
    total = sum(len(s) for s in series.values())
    con_ipc = sum(1 for slug, s in series.items() for a in s
                  if a in ipc_por_anio.get(slug, {}))
    sin_ipc = total - con_ipc
    if sin_ipc:
        return [_r("deflactabilidad", "aviso",
                   f"{sin_ipc} de {total} series no se pueden expresar en pesos "
                   "constantes: el IPC oficial de INDEC arranca en dic-2016. "
                   "El sitio muestra 'sin dato' en vez de estimar un número.",
                   deflactables=con_ipc, no_deflactables=sin_ipc)]
    return [_r("deflactabilidad", "ok", f"Las {total} series son deflactables.")]


def control_poblacion_ajuste(diagnostico):
    """Informa los desvíos entre proyección y censo, que el ajuste corrige."""
    grandes = sorted(
        ((d["desvio_pct"], s) for s, d in diagnostico.items() if d["desvio_pct"] is not None),
        key=lambda x: abs(x[0]), reverse=True)[:4]
    if not grandes:
        return [_r("ajuste_censal", "aviso", "No se pudo calcular el ajuste censal.")]
    txt = ", ".join(f"{nombre(s)} {d:+.1f}%" for d, s in grandes)
    return [_r("ajuste_censal", "ok",
               "Población reescalada al Censo 2022. Mayores correcciones sobre la "
               f"proyección de INDEC: {txt}. Sin este ajuste los rankings por "
               "habitante quedarían mal ordenados.")]


def correr_todos(series, consolidado, omitidos, poblacion, diagnostico, ipc_por_anio,
                 categorias=None, formas_mapa=None, alicuotas=None, finalidad=None):
    res = []
    res += control_cobertura(series, poblacion)
    if formas_mapa is not None:
        res += control_mapa(*formas_mapa)
    if alicuotas is not None:
        res += control_alicuotas(*alicuotas)
    if finalidad is not None:
        res += control_finalidad(*finalidad)
    res += control_suma_consolidado(series, consolidado)
    res += control_identidad_contable(series)
    if categorias is not None:
        res += control_categorias_vs_totales(series, categorias)
    res += control_duplicados(series)
    res += control_anios_omitidos(omitidos)
    res += control_poblacion_ajuste(diagnostico)
    res += control_deflactabilidad(series, ipc_por_anio)
    return res


def imprimir(resultados):
    simbolo = {"ok": "OK   ", "aviso": "AVISO", "error": "ERROR"}
    print("\n" + "=" * 78)
    print("CONTROLES DE CALIDAD")
    print("=" * 78)
    for r in resultados:
        print(f"[{simbolo[r['severidad']]}] {r['control']}")
        for linea in _envolver(r["detalle"], 72):
            print(f"         {linea}")
    errores = [r for r in resultados if r["severidad"] == "error"]
    print("-" * 78)
    print(f"{len(resultados)} controles · {len(errores)} errores · "
          f"{sum(1 for r in resultados if r['severidad'] == 'aviso')} avisos")
    return errores


def _envolver(texto, ancho):
    palabras, linea, out = texto.split(), "", []
    for p in palabras:
        if len(linea) + len(p) + 1 > ancho:
            out.append(linea)
            linea = p
        else:
            linea = f"{linea} {p}".strip()
    if linea:
        out.append(linea)
    return out
