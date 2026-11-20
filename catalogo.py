"""Catálogo de ingredientes reconocidos.

Sirve para rechazar entradas que no son comida ("nada", "hola", "asdf"),
unificar plurales y variantes ("tomates" -> "tomate", "frijoles" -> "fríjol")
y sugerir el nombre correcto cuando hay errores de escritura.
"""

import difflib
import unicodedata

INGREDIENTES = {
    # Granos, harinas y cereales
    "arroz", "arroz integral", "fríjol", "fríjol rojo", "lenteja", "garbanzo", "arveja",
    "maíz", "mazorca", "harina de maíz", "harina de trigo", "harina", "maicena", "avena",
    "quinua", "pasta", "espagueti", "macarrones", "fideos", "pan", "pan tajado", "arepa",
    "tortilla", "galleta", "cereal", "trigo", "cebada", "granola",
    # Lácteos y huevos
    "huevo", "leche", "leche en polvo", "leche condensada", "leche de coco", "queso",
    "queso costeño", "queso campesino", "queso mozzarella", "queso parmesano", "queso crema",
    "cuajada", "suero costeño", "mantequilla", "margarina", "crema de leche", "yogur", "kumis",
    # Carnes, aves y embutidos
    "pollo", "pechuga de pollo", "muslo de pollo", "alas de pollo", "pernil de pollo",
    "carne de res", "carne molida", "lomo de res", "sobrebarriga", "costilla de res",
    "cerdo", "lomo de cerdo", "costilla de cerdo", "chuleta de cerdo", "tocino", "chicharrón",
    "chorizo", "salchicha", "salchichón", "jamón", "mortadela", "morcilla", "pavo", "hígado",
    "carne", "res", "cordero", "hueso",
    # Pescados y mariscos
    "pescado", "tilapia", "mojarra", "bagre", "salmón", "trucha", "atún", "sardina",
    "camarón", "calamar", "pulpo", "mejillón", "langostino", "bacalao",
    # Tubérculos y plátanos
    "papa", "papa criolla", "papa pastusa", "yuca", "ñame", "batata", "arracacha",
    "plátano", "plátano verde", "plátano maduro", "banano",
    # Verduras y hortalizas
    "zanahoria", "cebolla", "cebolla larga", "cebolla morada", "cebolla cabezona", "ajo",
    "tomate", "tomate chonto", "pimentón", "ají", "jalapeño", "pepino", "lechuga", "repollo",
    "espinaca", "acelga", "brócoli", "coliflor", "calabacín", "ahuyama", "calabaza",
    "berenjena", "champiñón", "aguacate", "habichuela", "apio", "rábano", "remolacha",
    "alcachofa", "espárrago", "puerro", "kale", "rúgula", "maíz tierno", "palmito",
    # Hierbas y especias
    "cilantro", "perejil", "albahaca", "orégano", "comino", "laurel", "tomillo", "romero",
    "hierbabuena", "menta", "canela", "clavo", "clavo de olor", "nuez moscada", "paprika",
    "pimienta", "pimienta negra", "cúrcuma", "jengibre", "color", "achiote", "azafrán",
    "anís", "curry", "sazonador", "triguisar",
    # Frutas
    "limón", "naranja", "mandarina", "manzana", "pera", "guayaba", "mango", "piña", "papaya",
    "fresa", "mora", "lulo", "maracuyá", "uva", "sandía", "melón", "coco", "kiwi", "durazno",
    "cereza", "arándano", "uchuva", "granadilla", "tamarindo", "guanábana", "feijoa",
    "ciruela", "pitahaya", "curuba", "zapote", "níspero", "mamoncillo", "uva pasa",
    # Frutos secos y semillas
    "maní", "almendra", "nuez", "marañón", "pistacho", "ajonjolí", "chía", "linaza",
    "semilla de girasol", "avellana",
    # Despensa, salsas y otros
    "sal", "azúcar", "azúcar morena", "panela", "miel", "aceite", "aceite de oliva",
    "vinagre", "salsa de soya", "salsa de tomate", "mayonesa", "mostaza", "salsa negra",
    "salsa bbq", "pasta de tomate", "tomate en lata", "caldo de pollo", "caldo de gallina",
    "caldo de res", "chocolate", "cacao", "café", "té", "gelatina", "levadura",
    "polvo de hornear", "bicarbonato", "esencia de vainilla", "vainilla", "agua",
    "vino blanco", "vino tinto", "cerveza", "crema de maní", "mermelada", "arequipe",
    "bocadillo", "coco rallado", "leche de almendra", "tofu", "soya", "agua de panela",
    "hielo", "chocolate en polvo",
}

# Variantes y sinónimos -> nombre del catálogo
_SINONIMOS = {
    "frijol": "fríjol", "frijol rojo": "fríjol rojo", "patata": "papa", "pimiento": "pimentón",
    "chile": "ají", "palta": "aguacate", "elote": "mazorca", "choclo": "mazorca",
    "zapallo": "ahuyama", "calabacin": "calabacín", "hongo": "champiñón",
    "champinon": "champiñón", "jitomate": "tomate", "carne picada": "carne molida",
    "yogurt": "yogur", "ketchup": "salsa de tomate", "maizena": "maicena",
    "spaghetti": "espagueti", "pechuga": "pechuga de pollo", "huevos": "huevo",
    "comino molido": "comino", "cebollin": "cebolla larga", "cebolla junca": "cebolla larga",
}

_NO_PLURALIZAR = {"de", "con", "del", "en", "la", "el"}


def _clave(texto: str) -> str:
    """Minúsculas, sin tildes (salvo la ñ) y espacios simples."""
    texto = " ".join(texto.lower().split()).replace("ñ", "\0")
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return sin_tildes.replace("\0", "ñ")


_INDICE = {_clave(n): n for n in INGREDIENTES}
_INDICE.update({_clave(k): v for k, v in _SINONIMOS.items()})


def _singulares(clave: str) -> list[str]:
    """Variantes en singular: 'papas criollas' -> 'papa criolla', 'limones' -> 'limon'."""
    variantes = []
    for sufijo in ("es", "s"):
        palabras = [
            p[: -len(sufijo)] if p not in _NO_PLURALIZAR and len(p) > 3 and p.endswith(sufijo) else p
            for p in clave.split()
        ]
        variantes.append(" ".join(palabras))
    return variantes


def buscar(nombre: str) -> str | None:
    """Devuelve el nombre del catálogo que corresponde a `nombre`, o None."""
    clave = _clave(nombre)
    for candidata in (clave, *_singulares(clave)):
        if candidata in _INDICE:
            return _INDICE[candidata]
    return None


def sugerencias(nombre: str, maximo: int = 3) -> list[str]:
    """Nombres parecidos del catálogo, para mensajes de '¿quisiste decir…?'."""
    parecidos = difflib.get_close_matches(_clave(nombre), _INDICE.keys(), n=maximo * 2, cutoff=0.72)
    resultado: list[str] = []
    for p in parecidos:
        nombre_catalogo = _INDICE[p]
        if nombre_catalogo not in resultado:
            resultado.append(nombre_catalogo)
    return resultado[:maximo]


def listar() -> list[str]:
    return sorted(INGREDIENTES, key=_clave)
