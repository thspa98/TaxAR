"""
finalidades.py — En qué gasta el Estado, no cuánto.

El resto del sitio responde "cuánto gasta cada provincia". Esto responde la
pregunta que de verdad le importa al ciudadano: **en qué**.

La clasificación funcional tiene dos niveles y el archivo oficial los mezcla en
la misma columna, sin sangría que los distinga:

    Administración gubernamental      <- finalidad
    Servicios de seguridad            <- finalidad
    Servicios sociales                <- finalidad
      Salud                           <- función (hija de Servicios sociales)
      Promoción y asistencia social   <- función
      ...
    Servicios económicos              <- finalidad
    Deuda pública                     <- finalidad
    TOTAL

Las 5 finalidades suman el total. Las 9 funciones suman "Servicios sociales".
Contar los dos niveles juntos duplicaría la mitad del presupuesto, que es
exactamente el error que ya cometimos dos veces con otras fuentes. Por eso acá
cada nivel se declara explícito y el control verifica las dos sumas.
"""

# Las cinco finalidades. Suman el total del gasto.
FINALIDADES = {
    "administracion": {
        "etiqueta": "Administración",
        "explica": "Lo que cuesta que el Estado funcione como organización: la legislatura, "
                   "la justicia, la recaudación de impuestos, las áreas de gobierno.",
        "color": "#64748B",
    },
    "seguridad": {
        "etiqueta": "Seguridad",
        "explica": "Policía, bomberos, servicio penitenciario y defensa civil.",
        "color": "#B45309",
    },
    "social": {
        "etiqueta": "Servicios sociales",
        "explica": "Salud, educación, jubilaciones, vivienda y asistencia social. En casi "
                   "todas las provincias es más de la mitad del presupuesto.",
        "color": "#1A2B48",
    },
    "economicos": {
        "etiqueta": "Servicios económicos",
        "explica": "Lo que el Estado pone para que funcione la economía: energía, "
                   "transporte, riego, apoyo a la producción, comunicaciones.",
        "color": "#0F766E",
    },
    "deuda": {
        "etiqueta": "Deuda pública",
        "explica": "Los intereses de la deuda tomada en años anteriores. No compra nada "
                   "nuevo: es lo que cuesta haber gastado de más antes.",
        "color": "#DC2626",
    },
}

# Las nueve funciones dentro de Servicios sociales.
FUNCIONES = {
    "salud": {
        "etiqueta": "Salud",
        "explica": "Hospitales públicos, centros de salud, vacunación, medicamentos y el "
                   "personal que los atiende.",
        "color": "#059669",
    },
    "educacion": {
        "etiqueta": "Educación y cultura",
        "explica": "Escuelas y universidades provinciales, sueldos docentes, infraestructura "
                   "escolar, museos y bibliotecas. Suele ser la función más grande.",
        "color": "#2D4A7A",
    },
    "prevision": {
        "etiqueta": "Jubilaciones y pensiones",
        "explica": "Lo que paga la caja previsional provincial. En varias provincias tiene "
                   "déficit y se cubre con el resto de los impuestos.",
        "color": "#7C3AED",
    },
    "asistencia": {
        "etiqueta": "Asistencia social",
        "explica": "Programas sociales, comedores, ayuda directa a familias y a personas en "
                   "situación de vulnerabilidad.",
        "color": "#D4AF37",
    },
    "vivienda": {
        "etiqueta": "Vivienda y urbanismo",
        "explica": "Construcción de viviendas sociales, urbanización de barrios y "
                   "regularización de tierras.",
        "color": "#F97316",
    },
    "agua": {
        "etiqueta": "Agua y cloacas",
        "explica": "Redes de agua potable y saneamiento. Un gasto poco visible que define la "
                   "salud cotidiana de un barrio.",
        "color": "#0EA5E9",
    },
    "urbanos": {
        "etiqueta": "Otros servicios urbanos",
        "explica": "Alumbrado, recolección, espacios verdes y servicios de ciudad que en "
                   "algunas provincias están a cargo del gobierno provincial.",
        "color": "#94A3B8",
    },
    "ciencia": {
        "etiqueta": "Ciencia y técnica",
        "explica": "Investigación e institutos científicos provinciales. En casi todas es "
                   "una porción muy chica del presupuesto.",
        "color": "#8B5CF6",
    },
    "trabajo": {
        "etiqueta": "Trabajo",
        "explica": "Programas de empleo, capacitación laboral y fiscalización del trabajo.",
        "color": "#A8B4C8",
    },
}

# Etiqueta normalizada del archivo -> clave, con su nivel.
MAPEO_FF = {
    # finalidades
    "administracion gubernamental":  ("administracion", "finalidad"),
    "servicios de seguridad":        ("seguridad", "finalidad"),
    "servicios sociales":            ("social", "finalidad"),
    "servicios economicos":          ("economicos", "finalidad"),
    "deuda publica":                 ("deuda", "finalidad"),
    # funciones (hijas de servicios sociales)
    "salud":                         ("salud", "funcion"),
    "promocion y asistencia social": ("asistencia", "funcion"),
    "seguridad social":              ("prevision", "funcion"),
    "educacion y cultura":           ("educacion", "funcion"),
    "ciencia y tecnica":             ("ciencia", "funcion"),
    "trabajo":                       ("trabajo", "funcion"),
    "vivienda y urbanismo":          ("vivienda", "funcion"),
    "agua potable y alcantarillado": ("agua", "funcion"),
    "otros servicios urbanos":       ("urbanos", "funcion"),
}

# El propio archivo aclara que estos años no son medidos sino estimados por la
# fuente. El sitio lo dice al lector en vez de presentarlos como iguales.
ANIOS_ESTIMADOS = [2009, 2013, 2017, 2018]

NOTA_ESTIMADOS = (
    "La Dirección Nacional de Coordinación Fiscal aclara que la desagregación por función "
    "de 2009, 2013, 2017 y 2018 son estimaciones propias en base a otras fuentes, no datos "
    "reportados por las provincias. Se publican igual porque completan la serie, pero "
    "conviene no leerlos con la misma confianza que el resto."
)
