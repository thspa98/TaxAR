"""
taxonomia.py — Cómo se llama cada concepto fiscal en el sitio.

El archivo oficial dice "Prestaciones de la Seguridad Social". Un ciudadano
sin formación económica lee "Jubilaciones y pensiones". Este módulo hace esa
traducción, y es el que le da al sitio su tono explicativo.

Cada categoría tiene:
  etiqueta   — el nombre corto que se muestra
  explica    — una frase en lenguaje llano, sin jerga
  bloque     — 'ingreso' o 'gasto'
  color      — para que el mismo concepto tenga el mismo color en todo el sitio
"""

# etiqueta normalizada del AIF -> slug canónico
#
# CUIDADO al agregar filas: el AIF es jerárquico y varias etiquetas son
# subrubros de otras. "Regalías" y "Otros No Tributarios" son hijos de
# "No Tributarios"; mapear el padre Y el hijo cuenta la misma plata dos veces.
# Por eso acá se mapean siempre las hojas del árbol, nunca los totales
# intermedios. El control `desglose_vs_total` verifica que se cumpla.
MAPEO_AIF = {
    # --- ingresos (hojas de I. INGRESOS CORRIENTES) ---
    "de origen provincial":                 "impuestos-propios",
    "de origen nacional":                   "coparticipacion",
    "contribuciones a la seguridad social": "aportes-jubilatorios",
    "regalias":                             "regalias",
    "otros no tributarios":                 "no-tributarios",
    "vta.bienes y serv.de la adm.publ.":    "venta-bienes-servicios",
    "rentas de la propiedad":               "rentas-propiedad",
    "transferencias corrientes":            "transferencias-recibidas",

    # --- gastos (hojas de II. GASTOS CORRIENTES y V. GASTOS DE CAPITAL) ---
    "personal":                             "sueldos",
    "bienes de consumo":                    "bienes-servicios",
    "servicios":                            "bienes-servicios",
    "servicios no personales":              "bienes-servicios",
    "prestaciones de la seguridad social":  "jubilaciones",
    "al sector privado":                    "transferencias-privado",
    "al sector publico":                    "transferencias-municipios",
    "inversion real directa":               "obra-publica",
}

CATEGORIAS = {
    # --- de dónde sale la plata ---
    "impuestos-propios": {
        "etiqueta": "Impuestos provinciales",
        "explica": "Lo que la provincia recauda por su cuenta: Ingresos Brutos, "
                   "Inmobiliario, Automotor y Sellos.",
        "bloque": "ingreso", "color": "#2D4A7A",
    },
    "coparticipacion": {
        "etiqueta": "Envíos de la Nación",
        "explica": "Plata que la provincia recibe del Estado nacional, sobre todo "
                   "por coparticipación. No la recauda ella.",
        "bloque": "ingreso", "color": "#D4AF37",
    },
    "aportes-jubilatorios": {
        "etiqueta": "Aportes jubilatorios",
        "explica": "Los descuentos del sueldo de los empleados que financian la caja "
                   "previsional provincial.",
        "bloque": "ingreso", "color": "#3B5998",
    },
    "no-tributarios": {
        "etiqueta": "Tasas y multas",
        "explica": "Ingresos que no son impuestos ni regalías: tasas, multas y aranceles.",
        "bloque": "ingreso", "color": "#64748B",
    },
    "venta-bienes-servicios": {
        "etiqueta": "Venta de bienes y servicios",
        "explica": "Lo que el Estado provincial cobra por servicios que presta, como "
                   "agua, energía o trámites arancelados.",
        "bloque": "ingreso", "color": "#A8B4C8",
    },
    "regalias": {
        "etiqueta": "Regalías",
        "explica": "Lo que cobran las provincias por dejar extraer petróleo, gas o "
                   "minerales de su territorio. Explica por qué las patagónicas tienen "
                   "tanto dinero por habitante.",
        "bloque": "ingreso", "color": "#0F766E",
    },
    "rentas-propiedad": {
        "etiqueta": "Rentas financieras",
        "explica": "Intereses que gana la provincia por el dinero que tiene colocado.",
        "bloque": "ingreso", "color": "#94A3B8",
    },
    "transferencias-recibidas": {
        "etiqueta": "Transferencias recibidas",
        "explica": "Fondos que llegan por programas específicos, además de la "
                   "coparticipación automática.",
        "bloque": "ingreso", "color": "#F5D060",
    },

    # --- en qué se va ---
    "sueldos": {
        "etiqueta": "Sueldos estatales",
        "explica": "Lo que se paga a los empleados públicos: docentes, médicos, "
                   "policías y administración. Suele ser el gasto más grande.",
        "bloque": "gasto", "color": "#1A2B48",
    },
    "jubilaciones": {
        "etiqueta": "Jubilaciones y pensiones",
        "explica": "Lo que paga la caja previsional de la provincia a sus jubilados. "
                   "En varias provincias tiene déficit y se cubre con impuestos.",
        "bloque": "gasto", "color": "#7C3AED",
    },
    "bienes-servicios": {
        "etiqueta": "Funcionamiento",
        "explica": "Lo que cuesta que el Estado ande, sin contar sueldos: insumos, luz, "
                   "alquileres y servicios contratados.",
        "bloque": "gasto", "color": "#0EA5E9",
    },
    "transferencias-privado": {
        "etiqueta": "Ayuda social y subsidios",
        "explica": "Plata que va a personas, comedores, cooperativas y empresas "
                   "privadas.",
        "bloque": "gasto", "color": "#059669",
    },
    "transferencias-municipios": {
        "etiqueta": "Envíos a municipios",
        "explica": "Lo que la provincia le gira a sus municipios y a otros organismos "
                   "públicos.",
        "bloque": "gasto", "color": "#F97316",
    },
    "obra-publica": {
        "etiqueta": "Obra pública",
        "explica": "Rutas, escuelas, hospitales, viviendas. Es lo primero que se "
                   "recorta cuando falta dinero.",
        "bloque": "gasto", "color": "#DC2626",
    },
}

# Filas de titular del esquema AIF -> campo del sitio
HEADLINE = {
    "vi. ingresos totales":       "ingresos_totales",
    "vii. gastos totales":        "gastos_totales",
    "viii. resultado financiero": "resultado_financiero",
    "ix. resultado primario":     "resultado_primario",
    "x. gastos primarios":        "gastos_primarios",
    "iii. resultado economico":   "resultado_economico",
}

# Los impuestos provinciales tal como los siente una persona, no como los
# nombra el código fiscal.
IMPUESTOS = {
    "iibb-comercio": {
        "etiqueta": "Ingresos Brutos — comercio y servicios",
        "corto": "IIBB comercio",
        "explica": "Se cobra sobre la facturación de cada negocio, en cada etapa de la "
                   "cadena. No lo pagás vos directamente, pero está incorporado en el "
                   "precio de casi todo lo que comprás: es el impuesto provincial que más "
                   "recauda y el que más se nota en el bolsillo sin que se vea.",
        "quien": "Lo paga el comercio y se traslada al precio",
        "base": "sobre la facturación",
        "color": "#1A2B48",
    },
    "iibb-industria": {
        "etiqueta": "Ingresos Brutos — industria y producción primaria",
        "corto": "IIBB industria",
        "explica": "La misma lógica, pero para fábricas y producción agropecuaria. Casi "
                   "todas las provincias la tienen mucho más baja —a veces en cero— para "
                   "no encarecer lo que se produce dentro de su territorio.",
        "quien": "Lo paga la industria radicada en la provincia",
        "base": "sobre la facturación",
        "color": "#2D4A7A",
    },
    "sellos-contratos": {
        "etiqueta": "Sellos sobre contratos",
        "corto": "Sellos contratos",
        "explica": "Se paga al firmar un contrato: un alquiler, un préstamo, un acuerdo "
                   "comercial. Es de los pocos impuestos provinciales que una persona "
                   "común paga de forma consciente y de una sola vez.",
        "quien": "Lo pagan las partes que firman",
        "base": "sobre el monto total del contrato",
        "color": "#D4AF37",
    },
    "sellos-inmuebles": {
        "etiqueta": "Sellos sobre compraventa de inmuebles",
        "corto": "Sellos inmuebles",
        "explica": "Lo que se paga al escriturar una casa o un departamento, además de los "
                   "honorarios y los gastos. Sobre el precio de una propiedad, un punto "
                   "porcentual son muchos pesos.",
        "quien": "Se reparte entre comprador y vendedor",
        "base": "sobre el precio de la operación",
        "color": "#0F766E",
    },
}

# Cómo se calcula la base sobre la que se aplica cada alícuota.
#
# Para Ingresos Brutos y Sellos la base es obvia —la facturación, el monto del
# contrato— y por eso las alícuotas se pueden comparar directo entre provincias.
# Para Inmobiliario y Automotor no: la alícuota se aplica sobre una valuación
# que cada provincia calcula con su propio criterio, así que dos provincias con
# la misma alícuota pueden cobrar montos muy distintos por la misma casa.
# Publicar sólo las alícuotas de esos dos sería engañoso; esto explica por qué.
BASES_IMPONIBLES = {
    "inmobiliario": {
        "etiqueta": "Inmobiliario",
        "estandar": "Valuación fiscal catastral: el valor de la tierra más el de la "
                    "superficie edificada, según el registro de la provincia.",
        "por_que_importa": "La valuación catastral casi nunca coincide con el precio de "
                           "mercado, y cada provincia la actualiza cuando quiere. Dos "
                           "provincias con la misma alícuota pueden cobrar montos muy "
                           "distintos por la misma casa.",
        "variantes": [
            ("CABA", "Usa la Valuación Fiscal Homogénea (VFH) multiplicada por un "
                     "coeficiente de revaluación que se fija cada año."),
            ("Buenos Aires", "Aplica la valuación catastral pero ajustada por el Valor "
                             "Inmobiliario de Referencia (VIR)."),
            ("Todas", "Los terrenos baldíos pagan un recargo de entre 100% y 300% extra "
                      "sobre la base de la tierra, para desalentar la especulación."),
            ("Buenos Aires y Córdoba", "Impuesto complementario: suman las valuaciones de "
                                       "todos los inmuebles de un mismo titular y aplican "
                                       "una alícuota más alta sobre ese total. Tener tres "
                                       "propiedades chicas no paga lo mismo que tres "
                                       "dueños distintos con una cada uno."),
        ],
        "especiales": ["CABA", "Buenos Aires", "Córdoba", "Santa Fe", "Mendoza"],
    },
    "automotor": {
        "etiqueta": "Automotor (patente)",
        "estandar": "La tabla de valuación de la DNRPA, el registro nacional del automotor. "
                    "Es la misma para todo el país.",
        "por_que_importa": "Que la base sea nacional hace a la patente el más comparable de "
                           "los cuatro: si dos provincias usan la tabla DNRPA, la diferencia "
                           "de lo que pagás por el mismo auto es la diferencia de alícuota.",
        "variantes": [
            ("23 de 24 jurisdicciones", "Usan directamente la tabla DNRPA para autos "
                                        "particulares."),
            ("CABA y Buenos Aires", "Suelen aplicar coeficientes de ajuste propios cuando "
                                    "la tabla nacional se aparta del valor de mercado."),
            ("Córdoba, Santa Fe, Mendoza y Entre Ríos", "Para camiones y colectivos no usan "
                                                        "el valor comercial sino el peso, la "
                                                        "capacidad de carga o la cantidad de "
                                                        "ejes."),
        ],
        "especiales": ["Buenos Aires", "CABA", "Córdoba", "Santa Fe", "Mendoza", "Entre Ríos"],
    },
}

GLOSARIO = {
    "resultado_financiero": {
        "etiqueta": "Resultado financiero",
        "explica": "Todo lo que entró menos todo lo que salió, incluidos los "
                   "intereses de la deuda. Si es negativo, la provincia gastó más de "
                   "lo que recaudó y tuvo que endeudarse.",
    },
    "resultado_primario": {
        "etiqueta": "Resultado primario",
        "explica": "Lo mismo, pero sin contar los intereses de la deuda. Sirve para "
                   "ver si las cuentas cierran dejando de lado deudas del pasado.",
    },
    "intereses": {
        "etiqueta": "Intereses de la deuda",
        "explica": "Lo que se paga por deuda tomada antes. No compra nada nuevo: es "
                   "el costo de haber gastado de más en años anteriores.",
    },
    "ingresos_totales": {
        "etiqueta": "Ingresos totales",
        "explica": "Toda la plata que entró a la provincia en el año: impuestos "
                   "propios, envíos de la Nación, regalías y otros.",
    },
    "gastos_totales": {
        "etiqueta": "Gastos totales",
        "explica": "Toda la plata que gastó la provincia en el año, incluidos "
                   "sueldos, obra pública e intereses.",
    },
    "dependencia": {
        "etiqueta": "Dependencia de la Nación",
        "explica": "De cada 100 pesos de impuestos que maneja la provincia, cuántos "
                   "le llegan de la Nación en vez de recaudarlos ella. Cuanto más "
                   "alto, menos autonomía tiene para decidir.",
    },
    "territorio_continental": {
        "etiqueta": "Datos continentales",
        "explica": "Todas las cifras fiscales del sitio corresponden a la parte continental "
                   "del país. La provincia de Tierra del Fuego, Antártida e Islas del "
                   "Atlántico Sur incluye en su nombre y en el mapa la Antártida, las "
                   "Malvinas y las islas del Atlántico Sur, pero su ejecución presupuestaria "
                   "reportada corresponde a la actividad en la Isla Grande. El mapa muestra "
                   "el territorio completo porque así lo define el Instituto Geográfico "
                   "Nacional; los números, no.",
    },
    "masa_coparticipable": {
        "etiqueta": "Masa coparticipable",
        "explica": "La bolsa de impuestos nacionales que se reparte con las provincias. No "
                   "entra todo lo que recauda la Nación: quedan afuera las retenciones a la "
                   "exportación, los derechos de importación y los aportes jubilatorios. Qué "
                   "impuesto entra y cuál no es una decisión con consecuencias enormes.",
    },
    "distribucion_primaria": {
        "etiqueta": "Distribución primaria",
        "explica": "El primer corte: cuánto de la masa coparticipable se queda la Nación y "
                   "cuánto va al conjunto de las provincias.",
    },
    "distribucion_secundaria": {
        "etiqueta": "Distribución secundaria",
        "explica": "El segundo corte: cómo se reparte entre las 24 jurisdicciones la parte "
                   "que les corresponde. Son porcentajes fijos escritos en 1988, sin criterio "
                   "objetivo declarado.",
    },
    "transferencias_discrecionales": {
        "etiqueta": "Transferencias discrecionales",
        "explica": "Envíos de la Nación que no siguen ninguna fórmula: los decide el Poder "
                   "Ejecutivo caso por caso. Suelen tener destino específico —una obra, un "
                   "programa— y pueden aumentar o desaparecer de un año a otro. Es donde se "
                   "juega la negociación política entre un gobernador y el gobierno nacional.",
    },
    "correspondencia_fiscal": {
        "etiqueta": "Correspondencia fiscal",
        "explica": "La relación entre lo que un gobierno le cobra a sus propios vecinos y lo "
                   "que gasta. Cuando casi toda la plata viene de afuera, el votante no siente "
                   "el costo de lo que su provincia gasta, y eso debilita el control que "
                   "ejerce sobre quien gobierna.",
    },
    "atn": {
        "etiqueta": "Aportes del Tesoro Nacional (ATN)",
        "explica": "Un fondo del 1% de la masa coparticipable que la Nación reserva para "
                   "auxiliar provincias en emergencia. A diferencia del resto, no se gira "
                   "automáticamente: lo asigna el gobierno nacional cuando decide.",
    },
    "impuestos_por_habitante": {
        "etiqueta": "Impuestos provinciales por habitante",
        "explica": "Cuánto recauda la provincia de Ingresos Brutos, Inmobiliario, "
                   "Automotor y Sellos por cada persona que vive en ella. Es la parte de "
                   "la carga impositiva que decide la provincia, no la Nación.",
    },
    "presion_impositiva": {
        "etiqueta": "Presión impositiva",
        "explica": "En sentido técnico es la recaudación medida contra lo que produce la "
                   "provincia, y para calcularla hace falta el producto bruto geográfico, "
                   "que no se publica de forma comparable entre las 24 jurisdicciones. "
                   "El sitio muestra en cambio los impuestos provinciales por habitante, "
                   "que sí es comparable y sale de datos oficiales.",
    },
    "per_capita": {
        "etiqueta": "Gasto por habitante",
        "explica": "El gasto total dividido por la cantidad de habitantes. Es la única "
                   "forma justa de comparar una provincia de 17 millones con una de "
                   "200 mil.",
    },
    "pesos_constantes": {
        "etiqueta": "Pesos constantes",
        "explica": "Los montos ajustados por inflación, para que un peso de 2017 y uno "
                   "de 2025 valgan lo mismo. Sin este ajuste, con la inflación "
                   "argentina cualquier serie larga parece crecer aunque en realidad "
                   "haya caído.",
    },
}
