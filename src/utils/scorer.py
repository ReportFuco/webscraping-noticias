import unicodedata
import re

# Palabras de alto impacto — peso 3
HIGH_IMPACT = [
    "walmart", "lider", "jumbo", "tottus", "unimarc", "santa isabel",
    "cencosud", "smu", "falabella", "ripley", "paris",
    "sodimac", "easy", "mall", "centro comercial",
    "oxxo", "mass",
    "coca-cola", "unilever", "agrosuper", "soprole"
]

# Palabras de tema principal — peso 2
TOPIC_WORDS = [
    "retail", "supermercado", "hipermercado",
    "tienda", "local", "cadena", "comercio",
    "mayorista", "conveniencia",
    "formato", "canal", "punto de venta",
    "merchandising", "trade marketing",
    "consumo masivo", "bienes de consumo"
]


# Palabras de contexto — peso 1
CONTEXT_WORDS = [
    "apertura", "expansión", "inauguración", "cierre",
    "sucursal", "locales", "tiendas",
    "ventas", "utilidades", "ingresos",
    "consumidor", "demanda", "mercado",
    "precios", "inflación", "promoción",
    "góndola", "abastecimiento", "logística",
    "proveedores", "distribución"
]

def _normalize(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z\s]", "", text)
    return text


def score_noticia(title: str) -> int:
    """
    Puntúa una noticia según sus keywords.
    Retorna un score entre 0 y 10.
    """
    normalized = _normalize(title)
    words = normalized.split()
    raw_score = 0

    for word in words:
        if any(kw in word for kw in HIGH_IMPACT):
            raw_score += 4
        elif any(kw in word for kw in TOPIC_WORDS):
            raw_score += 3
        elif any(kw in word for kw in CONTEXT_WORDS):
            raw_score += 1

    # Clamp entre 0 y 10
    return min(raw_score, 10)