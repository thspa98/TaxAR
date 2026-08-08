"""
jurisdicciones.py — Catálogo canónico de las 24 jurisdicciones.

Una jurisdicción se escribe distinto en cada archivo oficial. Este módulo es
el único lugar donde viven esas equivalencias, así que agregar una fuente
nueva con otra grafía se resuelve tocando un solo diccionario.

OJO con los alias: no son decorativos. El archivo de proyecciones de INDEC
trae la hoja de Santa Fe escrita "82-SANTE FE". Sin ese alias, la tercera
economía provincial del país queda sin población y desaparece de todos los
rankings per cápita — sin que salte ningún error.
"""

import re
import unicodedata


def nrm(s):
    """Normaliza texto: sin tildes, minúsculas, espacios colapsados."""
    if s is None:
        return ""
    s = "".join(c for c in unicodedata.normalize("NFD", str(s))
                if unicodedata.category(c) != "Mn")
    s = s.strip().lower().lstrip(".- ").strip()
    return re.sub(r"\s+", " ", s)


# slug -> metadatos canónicos
# La región IPC determina con qué índice se deflacta cada provincia.
JURISDICCIONES = {
    "caba":                {"nombre": "Ciudad Autónoma de Buenos Aires", "corto": "CABA",             "indec": "02", "region": "GBA",       "gentilicio": "porteños"},
    "buenos-aires":        {"nombre": "Buenos Aires",                    "corto": "Buenos Aires",     "indec": "06", "region": "GBA",       "gentilicio": "bonaerenses"},
    "catamarca":           {"nombre": "Catamarca",                       "corto": "Catamarca",        "indec": "10", "region": "NOA",       "gentilicio": "catamarqueños"},
    "cordoba":             {"nombre": "Córdoba",                         "corto": "Córdoba",          "indec": "14", "region": "Pampeana",  "gentilicio": "cordobeses"},
    "corrientes":          {"nombre": "Corrientes",                      "corto": "Corrientes",       "indec": "18", "region": "NEA",       "gentilicio": "correntinos"},
    "chaco":               {"nombre": "Chaco",                           "corto": "Chaco",            "indec": "22", "region": "NEA",       "gentilicio": "chaqueños"},
    "chubut":              {"nombre": "Chubut",                          "corto": "Chubut",           "indec": "26", "region": "Patagonia", "gentilicio": "chubutenses"},
    "entre-rios":          {"nombre": "Entre Ríos",                      "corto": "Entre Ríos",       "indec": "30", "region": "Pampeana",  "gentilicio": "entrerrianos"},
    "formosa":             {"nombre": "Formosa",                         "corto": "Formosa",          "indec": "34", "region": "NEA",       "gentilicio": "formoseños"},
    "jujuy":               {"nombre": "Jujuy",                           "corto": "Jujuy",            "indec": "38", "region": "NOA",       "gentilicio": "jujeños"},
    "la-pampa":            {"nombre": "La Pampa",                        "corto": "La Pampa",         "indec": "42", "region": "Pampeana",  "gentilicio": "pampeanos"},
    "la-rioja":            {"nombre": "La Rioja",                        "corto": "La Rioja",         "indec": "46", "region": "NOA",       "gentilicio": "riojanos"},
    "mendoza":             {"nombre": "Mendoza",                         "corto": "Mendoza",          "indec": "50", "region": "Cuyo",      "gentilicio": "mendocinos"},
    "misiones":            {"nombre": "Misiones",                        "corto": "Misiones",         "indec": "54", "region": "NEA",       "gentilicio": "misioneros"},
    "neuquen":             {"nombre": "Neuquén",                         "corto": "Neuquén",          "indec": "58", "region": "Patagonia", "gentilicio": "neuquinos"},
    "rio-negro":           {"nombre": "Río Negro",                       "corto": "Río Negro",        "indec": "62", "region": "Patagonia", "gentilicio": "rionegrinos"},
    "salta":               {"nombre": "Salta",                           "corto": "Salta",            "indec": "66", "region": "NOA",       "gentilicio": "salteños"},
    "san-juan":            {"nombre": "San Juan",                        "corto": "San Juan",         "indec": "70", "region": "Cuyo",      "gentilicio": "sanjuaninos"},
    "san-luis":            {"nombre": "San Luis",                        "corto": "San Luis",         "indec": "74", "region": "Cuyo",      "gentilicio": "puntanos"},
    "santa-cruz":          {"nombre": "Santa Cruz",                      "corto": "Santa Cruz",       "indec": "78", "region": "Patagonia", "gentilicio": "santacruceños"},
    "santa-fe":            {"nombre": "Santa Fe",                        "corto": "Santa Fe",         "indec": "82", "region": "Pampeana",  "gentilicio": "santafesinos"},
    "santiago-del-estero": {"nombre": "Santiago del Estero",             "corto": "Sgo. del Estero",  "indec": "86", "region": "NOA",       "gentilicio": "santiagueños"},
    "tucuman":             {"nombre": "Tucumán",                         "corto": "Tucumán",          "indec": "90", "region": "NOA",       "gentilicio": "tucumanos"},
        # Nombre oficial completo. El `corto` es el que va en tablas y rankings:
    # 52 caracteres en una barra horizontal desbalancean cualquier gráfico.
    "tierra-del-fuego":    {"nombre": "Tierra del Fuego, Antártida e Islas del Atlántico Sur",
                            "corto": "Tierra del Fuego", "indec": "94", "region": "Patagonia",
                            "gentilicio": "fueguinos"},
}

# Cómo se llama cada hoja en serie_aif-apnf-2025.xlsx
HOJA_AIF = {
    "Ciudad": "caba",
    "Buenos Aires": "buenos-aires",
    "Catamarca": "catamarca",
    "Córdoba": "cordoba",
    "Corrientes": "corrientes",
    "Chaco": "chaco",
    "Chubut": "chubut",
    "Entre Ríos": "entre-rios",
    "Formosa": "formosa",
    "Jujuy": "jujuy",
    "La Pampa": "la-pampa",
    "La Rioja": "la-rioja",
    "Mendoza": "mendoza",
    "Misiones": "misiones",
    "Neuquén": "neuquen",
    "Río Negro": "rio-negro",
    "Salta": "salta",
    "San Juan": "san-juan",
    "San Luis": "san-luis",
    "Santa Cruz": "santa-cruz",
    "Santa Fe": "santa-fe",
    "Santiago del  Estero": "santiago-del-estero",   # dos espacios en el original
    "Tucumán": "tucuman",
    "Tierra del Fuego": "tierra-del-fuego",
}

# Cómo aparece cada jurisdicción en los archivos de INDEC (ya normalizado)
ALIAS_INDEC = {
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
    "sante fe": "santa-fe",          # TYPO REAL en c1_proyecciones (INDEC)
    "santiago del estero": "santiago-del-estero",
    "tucuman": "tucuman",
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


def slug_indec(nombre):
    """Traduce un nombre tal como aparece en INDEC al slug canónico."""
    return ALIAS_INDEC.get(nrm(nombre))


def region(slug):
    return JURISDICCIONES[slug]["region"]


def nombre(slug):
    return JURISDICCIONES[slug]["nombre"]
