import re
import unicodedata

# Marcas / actores muy relevantes para retail-supermercados
HIGH_IMPACT = [
    "walmart", "lider", "express de lider", "acuenta",
    "jumbo", "tottus", "unimarc", "santa isabel", "super 10",
    "cencosud", "smu", "falabella", "ripley", "paris",
    "sodimac", "easy", "mall plaza", "mallplaza", "parque arauco",
    "oxxo", "mass", "alvi", "mayorista 10",
    "mercado libre", "mercadolibre", "spid", "ok market",
    "copec pronto", "upa",
]

# Proveedores / fabricantes / actores ligados al canal
SUPPLIER_WORDS = [
    "coca cola", "ccu", "unilever", "agrosuper", "soprole", "nestle",
    "carozzi", "arcor", "ideal", "bimbo", "pepsico", "mondelez",
    "softys", "procter", "colun",
]

# Tema principal retail
TOPIC_WORDS = [
    "retail", "retailer", "supermercado", "supermercados",
    "hipermercado", "hipermercados", "tienda", "tiendas",
    "comercio", "comercial",
    "mayorista", "conveniencia", "consumo masivo",
    "canal supermercadista", "canal tradicional", "canal moderno",
    "punto de venta", "ecommerce", "omnicanal", "marketplace",
    "farmacia", "farmacias", "mejoramiento del hogar",
]

# Operación indirecta relevante para retail
INDIRECT_WORDS = [
    "logistica", "distribucion", "ultima milla", "despacho",
    "bodega", "bodegas", "centro de distribucion", "centros de distribucion",
    "inventario", "abastecimiento", "quiebre de stock", "reposicion",
    "proveedor", "proveedores", "cadena de suministro", "supply chain",
    "consumidor", "consumidores", "ticket promedio", "trafico",
    "promocion", "promociones", "descuentos", "ofertas",
    "precio", "precios", "margen", "margenes", "ventas", "ingresos",
    "utilidades", "apertura", "aperturas", "inauguracion",
    "expansion", "expansiones", "cierre", "cierres",
    "sucursal", "sucursales",
    "foodservice", "canal horeca",
]

# Expresiones que hacen más probable que una noticia indirecta sí sea útil
RETAIL_CONNECTORS = [
    "supermercado", "supermercados", "retail", "retailer", "comercio",
    "tienda", "tiendas", "consumo masivo",
    "canal", "canal supermercadista", "punto de venta", "mall", "malls",
    "centro comercial",
]

# Términos de macro/política que suelen meter ruido si aparecen solos
NEGATIVE_HINTS = [
    "presidente", "senador", "diputado", "ministro", "gobierno",
    "elecciones", "fiscal", "iran", "moneda", "gabinete",
    "seguridad", "homicidio", "asesinato", "asalto",
]

# Términos policiales/judiciales que suelen generar falsos positivos por palabras como tienda/local
CRIME_WORDS = [
    "robo", "robos", "ladron", "ladrones", "asalto", "asaltos", "homicidio",
    "homicidios", "asesinato", "asesinatos", "cadena perpetua", "perpetua",
    "carabinero", "carabineros", "fiscalia", "fiscal", "tribunal", "juez",
    "condena", "condenado", "condenaron", "prision", "crimen", "delito",
]

# Términos internacionales que suelen meter ruido cuando no hay señal retail concreta
GENERIC_WORLD_WORDS = [
    "francia", "ucrania", "rusia", "iran", "israel", "guerra", "onu",
    "trump", "hezbollah", "otan", "kiev", "moscu",
]

# Términos macroeconómicos que solo deberían entrar si están conectados al canal
MACRO_WORDS = [
    "inflacion", "ipc", "combustibles", "petroleo", "energia", "iva",
    "crecimiento", "recesion", "deuda", "credito", "tasas",
]


STRONG_RETAIL_SIGNAL_THRESHOLD = 1


def _normalize(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _keyword_in_text(keyword: str, text: str) -> bool:
    pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"
    return re.search(pattern, text) is not None


def _count_matches(text: str, keywords: list[str]) -> list[str]:
    return [kw for kw in keywords if _keyword_in_text(kw, text)]


def score_noticia(title: str, url: str = "", source: str = "", excerpt: str = "") -> int:
    """
    Puntúa una noticia según su relación con retail/supermercados.
    Mezcla retail directo con señales indirectas operativas del canal.
    Retorna un score entre 0 y 10.
    """
    combined_text = " ".join(part for part in [title, excerpt, url, source] if part)
    normalized = _normalize(combined_text)
    if not normalized:
        return 0

    high_matches = _count_matches(normalized, HIGH_IMPACT)
    supplier_matches = _count_matches(normalized, SUPPLIER_WORDS)
    topic_matches = _count_matches(normalized, TOPIC_WORDS)
    indirect_matches = _count_matches(normalized, INDIRECT_WORDS)
    connector_matches = _count_matches(normalized, RETAIL_CONNECTORS)
    negative_matches = _count_matches(normalized, NEGATIVE_HINTS)
    macro_matches = _count_matches(normalized, MACRO_WORDS)
    crime_matches = _count_matches(normalized, CRIME_WORDS)
    world_matches = _count_matches(normalized, GENERIC_WORLD_WORDS)

    strong_retail_signal = bool(high_matches or topic_matches or supplier_matches)
    weak_retail_signal = bool(connector_matches or indirect_matches)

    raw_score = 0

    # Capa 1: retail directo
    raw_score += len(high_matches) * 4
    raw_score += len(topic_matches) * 3

    # Capa 2: proveedores ligados al canal
    raw_score += len(supplier_matches) * 2
    if supplier_matches and (topic_matches or connector_matches or indirect_matches):
        raw_score += 2

    # Capa 3: retail indirecto / operación del canal
    if strong_retail_signal:
        raw_score += len(indirect_matches) * 1
    elif len(indirect_matches) >= 3 and connector_matches:
        raw_score += 1

    # Bonos por combinaciones útiles
    if high_matches and topic_matches:
        raw_score += 2
    if len(high_matches) >= 2:
        raw_score += 2
    if topic_matches and len(indirect_matches) >= 2:
        raw_score += 2
    if supplier_matches and len(indirect_matches) >= 1:
        raw_score += 1
    if high_matches and len(indirect_matches) >= 1:
        raw_score += 1

    # Macro solo suma si está conectada al canal retail
    if macro_matches and strong_retail_signal:
        raw_score += 1

    # Penalizaciones para bajar ruido macro/político genérico
    if negative_matches and not strong_retail_signal:
        raw_score -= 2

    if macro_matches and not strong_retail_signal:
        raw_score -= 1

    # Penalizaciones más agresivas para policial/judicial genérico
    if crime_matches and not strong_retail_signal:
        raw_score -= 4
    elif crime_matches and not high_matches:
        raw_score -= 2

    # Internacional genérico sin conexión retail real
    if world_matches and not strong_retail_signal:
        raw_score -= 3

    # Si solo hay señales débiles, no dejar que escale demasiado
    if not strong_retail_signal and weak_retail_signal:
        raw_score = min(raw_score, 1)

    # Casos sin señal retail real deben quedar fuera
    if not strong_retail_signal and raw_score < STRONG_RETAIL_SIGNAL_THRESHOLD:
        return 0

    return max(0, min(raw_score, 10))
