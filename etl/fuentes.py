"""
fuentes.py — Registro de fuentes oficiales.

=============================================================================
ESTE ES EL ÚNICO ARCHIVO QUE TOCÁS PARA ACTUALIZAR DATOS.
=============================================================================

Cuando salga una nueva versión de un archivo oficial:

  1. Descargá el archivo nuevo y ponelo en la carpeta `fuentes/`.
  2. Cambiá acá abajo el valor de `archivo` y de `cobertura`.
  3. Actualizá `revisado` con la fecha de hoy.
  4. Corré:  python etl/exportar_json.py

No hace falta tocar ningún otro archivo. Los controles de calidad avisan
si algo salió mal.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_FUENTES = RAIZ / "fuentes"
DIR_SALIDA = RAIZ / "web" / "src" / "data"


# --- Base metodológica del sitio -------------------------------------------
# Cambiar sólo si cambia la metodología, no en cada actualización.
UNIVERSO = "apnf"           # Administración Pública No Financiera
TIPO_DATO = "ejecutado"     # lo que se gastó, no lo que se presupuestó
BASE_CONTABLE = "devengado"
UNIDAD = "millones"         # de pesos corrientes


# --- Fuentes ----------------------------------------------------------------
FUENTES = {
    "serie_aif": {
        "archivo": "serie_aif-apnf-2025.xlsx",
        "nombre": "Serie AIF-APNF de las provincias, 2005-2025",
        "organismo": "Dirección Nacional de Coordinación Fiscal con las Provincias (MECON)",
        "url": "https://www.argentina.gob.ar/economia/sechacienda/"
               "coordinacion-fiscal-provincial/ejecucion-presupuestaria-provincial",
        "cobertura": "24 jurisdicciones, 2005-2025, ejecución devengada, APNF, en millones de $",
        "frecuencia": "anual",
        "revisado": "2026-08-03",
    },
    "poblacion_proyecciones": {
        "archivo": "c1_proyecciones_prov_2010_2040.xls",
        "nombre": "Proyecciones de población por provincia 2010-2040",
        "organismo": "INDEC",
        "url": "https://www.indec.gob.ar/ftp/cuadros/poblacion/c1_proyecciones_prov_2010_2040.xls",
        "cobertura": "24 jurisdicciones, 2010-2040, base Censo 2010",
        "frecuencia": "esporádica",
        "revisado": "2026-08-03",
    },
    "poblacion_censo": {
        "archivo": "c2022_tp_c_resumen.xlsx",
        "nombre": "Censo Nacional de Población 2022 — cuadro resumen",
        "organismo": "INDEC",
        "url": "https://www.indec.gob.ar/ftp/cuadros/poblacion/c2022_tp_c_resumen.xlsx",
        "cobertura": "24 jurisdicciones, conteo real 2022",
        "frecuencia": "decenal",
        "revisado": "2026-08-03",
    },
    "serie_ff": {
        "archivo": "serie_ff-apnf.xlsx",
        "nombre": "Gasto por finalidad y función de las provincias, 2005-2024",
        "organismo": "Dirección Nacional de Coordinación Fiscal con las Provincias (MECON)",
        "url": "https://www.argentina.gob.ar/economia/sechacienda/"
               "coordinacion-fiscal-provincial/ejecucion-presupuestaria-provincial",
        "cobertura": "24 jurisdicciones, 2005-2024, APNF, en millones de $",
        "frecuencia": "anual",
        "revisado": "2026-08-05",
    },
    "alicuotas": {
        "archivo": "alicuotas_provinciales.xlsx",
        "nombre": "Alícuotas de impuestos provinciales",
        "organismo": "Compilación propia a partir de las leyes impositivas provinciales",
        "url": "",
        "cobertura": "24 jurisdicciones · Ingresos Brutos y Sellos",
        "frecuencia": "anual",
        "revisado": "2026-08-04",
        # A diferencia del resto, esto NO viene de un organismo público en un
        # archivo único: se compiló leyendo las leyes impositivas de cada
        # provincia. El sitio lo publica marcado como tal y pide que le
        # reporten errores, en vez de darle la misma autoridad que a la serie
        # del MECON. Cuando cada alícuota tenga su norma y su enlace al
        # boletín oficial, se puede sacar esta advertencia.
        "revisada_por_terceros": False,
    },
    "mapa": {
        "archivo": "mapa-ign/provincias.json",
        "nombre": "Capa Provincia del Instituto Geográfico Nacional",
        "organismo": "Instituto Geográfico Nacional de la República Argentina",
        "url": "https://www.ign.gob.ar/",
        "cobertura": "24 jurisdicciones · WGS 84 · proyección cónica de Albers · "
                     "incluye Malvinas, Georgias del Sur, Sandwich del Sur y "
                     "el Sector Antártico Argentino",
        "frecuencia": "sin cambios",
        "revisado": "2026-08-06",
        # Los términos del IGN exigen esta leyenda visible en cualquier obra
        # derivada, y prohíben modificar los límites o suprimir la toponimia.
        "atribucion_obligatoria":
            "FUENTE: Instituto Geográfico Nacional de la República Argentina.",
    },
    "ipc": {
        "archivo": "sh_ipc_aperturas.xls",
        "nombre": "Índice de Precios al Consumidor por región",
        "organismo": "INDEC",
        "url": "https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_aperturas.xls",
        "cobertura": "6 regiones, desde dic-2016, base dic-2016=100",
        "frecuencia": "mensual",
        "revisado": "2026-08-03",
    },
}


def ruta(clave):
    """Ruta absoluta al archivo de una fuente."""
    p = DIR_FUENTES / FUENTES[clave]["archivo"]
    if not p.exists():
        raise FileNotFoundError(
            f"Falta la fuente '{clave}': se esperaba {p}\n"
            f"  Descargala de: {FUENTES[clave]['url']}\n"
            f"  y guardala en la carpeta fuentes/ con ese nombre exacto."
        )
    return p


def cita(clave):
    """Bloque de atribución que acompaña a cada número publicado en el sitio."""
    f = FUENTES[clave]
    return {
        "nombre": f["nombre"],
        "organismo": f["organismo"],
        "url": f["url"],
        "cobertura": f["cobertura"],
        "revisado": f["revisado"],
    }
