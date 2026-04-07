import re
import unicodedata

# Marcas / actores muy relevantes para retail-supermercados
HIGH_IMPACT = [
    "walmart", "express de lider", "acuenta",
    "jumbo", "tottus", "unimarc", "santa isabel", "super 10",
    "cencosud", "smu", "falabella", "ripley", "paris",
    "sodimac", "easy", "mall plaza", "mallplaza", "parque arauco",
    "oxxo", "mass", "alvi", "mayorista 10",
    "mercado libre", "mercadolibre", "spid", "ok market",
    "copec pronto", "upa",
]

# Términos ambiguos que requieren contexto adicional
AMBIGUOUS_BRANDS = {
    "lider": [
        "supermercado", "supermercados", "walmart", "local", "locales",
        "tienda", "tiendas", "sucursal", "sucursales", "express", "acuenta",
        "retail", "retailer", "apertura", "aperturas",
    ],
    "paris": [
        "tienda", "tiendas", "retail", "retailer", "falabella", "cencosud",
        "ripley", "mall", "malls", "centro comercial",
    ],
}

# Proveedores / fabricantes / actores ligados al canal
SUPPLIER_WORDS = [
    "coca cola", "ccu", "unilever", "agrosuper", "soprole", "nestle",
    "carozzi", "arcor", "ideal", "bimbo", "pepsico", "mondelez",
    "softys", "procter", "colun",
]

# Tema principal retail / comercio / negocios ligados al canal
TOPIC_WORDS = [
    "retail", "retailer", "supermercado", "supermercados",
    "hipermercado", "hipermercados", "tienda", "tiendas",
    "mayorista", "conveniencia", "consumo masivo",
    "canal supermercadista", "canal tradicional", "canal moderno",
    "punto de venta", "ecommerce", "comercio electronico", "omnicanal", "marketplace",
    "farmacia", "farmacias", "mejoramiento del hogar",
    "centro comercial", "centros comerciales", "mall", "malls",
    "comercio", "camara de comercio", "pymes", "negocios",
]

# Operación indirecta relevante para retail/comercio
INDIRECT_WORDS = [
    "logistica", "distribucion", "ultima milla", "despacho",
    "bodega", "bodegas", "centro de distribucion", "centros de distribucion",
    "inventario", "abastecimiento", "quiebre de stock", "reposicion",
    "proveedor", "proveedores", "cadena de suministro", "supply chain",
    "ticket promedio", "trafico",
    "promocion", "promociones", "descuentos", "ofertas",
    "margen", "margenes", "apertura", "aperturas", "inauguracion",
    "expansion", "expansiones", "cierre", "cierres",
    "sucursal", "sucursales", "adquisicion", "adquisiciones",
    "inversion", "inversiones", "ventas", "ingresos", "utilidades",
    "foodservice", "canal horeca", "gremio", "informalidad",
    "estados financieros", "bonos", "refinanciamiento", "ebitda",
]

# Expresiones que hacen más probable que una noticia indirecta sí sea útil
RETAIL_CONNECTORS = [
    "supermercado", "supermercados", "retail", "retailer",
    "tienda", "tiendas", "consumo masivo",
    "canal", "canal supermercadista", "punto de venta", "mall", "malls",
    "centro comercial", "centros comerciales",
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
    "detenidos", "detenido", "operativo", "ambulante", "fiscalizaciones",
]

# Términos internacionales que suelen meter ruido cuando no hay señal retail concreta
GENERIC_WORLD_WORDS = [
    "francia", "ucrania", "rusia", "iran", "israel", "guerra", "onu",
    "trump", "hezbollah", "otan", "kiev", "moscu", "pyongyang", "siria",
]

# Temas de alto valor para negocio retail/comercio/malls/pymes
BUSINESS_POSITIVE_WORDS = [
    "apertura", "aperturas", "inauguracion", "expansion", "expansiones",
    "nuevo local", "nuevos locales", "nueva tienda", "nuevas tiendas",
    "precios congelados", "congela precios", "promocion", "promociones",
    "descuentos", "ofertas", "inversion", "inversiones", "resultados",
    "estados financieros", "ventas", "ingresos", "utilidades", "ebitda",
    "margen", "margenes", "logistica", "distribucion", "ultima milla",
    "centro de distribucion", "abastecimiento", "proveedores", "marketplace",
    "ecommerce", "comercio electronico", "omnicanal", "bonos", "refinanciamiento",
    "adquisicion", "adquisiciones", "cadena de suministro", "pymes",
    "camara de comercio", "comercio", "centro comercial", "mall", "malls",
]

# Temas que suelen ser retail, pero de poco valor informativo para el objetivo del feed
LOW_VALUE_RETAIL_WORDS = [
    "caos", "avalancha", "lesionados", "heridos", "influencer", "viral",
    "regala dinero", "lanzamiento de dinero", "disturbios", "show", "evento no autorizado",
]

# Señales transversales de negocio/comercio que deben ayudar a entrar si no hay ruido fuerte
COMMERCE_BUSINESS_HINTS = [
    "comercio", "camara de comercio", "ecommerce", "comercio electronico",
    "pymes", "negocios", "abastecimiento", "proveedores", "cadena de suministro",
    "centro comercial", "mall", "malls", "inversion", "adquisicion",
]

# Términos macroeconómicos que solo deberían entrar si están conectados al canal
MACRO_WORDS = [
    "inflacion", "ipc", "combustibles", "petroleo", "energia", "iva",
    "crecimiento", "recesion", "deuda", "credito", "tasas",
]


STRONG_RETAIL_SIGNAL_THRESHOLD = 2


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


def _ambiguous_brand_matches(text: str) -> list[str]:
    matches: list[str] = []
    for brand, context_words in AMBIGUOUS_BRANDS.items():
        if not _keyword_in_text(brand, text):
            continue
        if any(_keyword_in_text(ctx, text) for ctx in context_words):
            matches.append(brand)
    return matches


def score_noticia(title: str, url: str = "", source: str = "", excerpt: str = "") -> int:
    """
    Puntúa una noticia según su relación con retail/supermercados.
    Se apoya principalmente en título + excerpt y usa source/url solo como señal auxiliar.
    Retorna un score entre 0 y 10.
    """
    primary_text = " ".join(part for part in [title, excerpt] if part)
    normalized_primary = _normalize(primary_text)
    if not normalized_primary:
        return 0

    metadata_text = _normalize(" ".join(part for part in [url, source] if part))

    high_matches = _count_matches(normalized_primary, HIGH_IMPACT)
    high_matches += _ambiguous_brand_matches(normalized_primary)
    supplier_matches = _count_matches(normalized_primary, SUPPLIER_WORDS)
    topic_matches = _count_matches(normalized_primary, TOPIC_WORDS)
    indirect_matches = _count_matches(normalized_primary, INDIRECT_WORDS)
    connector_matches = _count_matches(normalized_primary, RETAIL_CONNECTORS)
    negative_matches = _count_matches(normalized_primary, NEGATIVE_HINTS)
    macro_matches = _count_matches(normalized_primary, MACRO_WORDS)
    crime_matches = _count_matches(normalized_primary, CRIME_WORDS)
    world_matches = _count_matches(normalized_primary, GENERIC_WORLD_WORDS)
    business_positive_matches = _count_matches(normalized_primary, BUSINESS_POSITIVE_WORDS)
    low_value_retail_matches = _count_matches(normalized_primary, LOW_VALUE_RETAIL_WORDS)
    commerce_hint_matches = _count_matches(normalized_primary, COMMERCE_BUSINESS_HINTS)

    # Source/URL solo ayudan si ya hay señal retail en el texto principal.
    source_high_matches = _count_matches(metadata_text, HIGH_IMPACT) if metadata_text else []
    source_topic_matches = _count_matches(metadata_text, TOPIC_WORDS) if metadata_text else []

    strong_retail_signal = bool(high_matches or topic_matches or supplier_matches or commerce_hint_matches)
    weak_retail_signal = bool(connector_matches or indirect_matches or commerce_hint_matches)

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
    elif len(indirect_matches) >= 2 and connector_matches:
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

    # Priorizar noticias más útiles para negocio
    if strong_retail_signal:
        raw_score += min(len(business_positive_matches), 3)

    # Abrir un poco más comercio/malls/pymes/negocios sin abrir la puerta a guerra o política
    if not strong_retail_signal and commerce_hint_matches and not (world_matches or crime_matches):
        raw_score += 2

    # La metadata solo refuerza; no crea relevancia por sí sola
    if strong_retail_signal and (source_high_matches or source_topic_matches):
        raw_score += 1

    # Macro solo suma si está conectada al canal retail
    if macro_matches and strong_retail_signal:
        raw_score += 1

    # Penalizaciones para bajar ruido macro/político genérico
    if negative_matches and not strong_retail_signal:
        raw_score -= 3
    elif negative_matches and not high_matches:
        raw_score -= 1

    if macro_matches and not strong_retail_signal:
        raw_score -= 2

    # Penalizaciones más agresivas para policial/judicial genérico
    if crime_matches and not strong_retail_signal:
        raw_score -= 4
    elif crime_matches and not high_matches:
        raw_score -= 2

    # Internacional genérico sin conexión retail real
    if world_matches and not strong_retail_signal:
        raw_score -= 4

    # Castigar retail de poco valor editorial para este feed
    if low_value_retail_matches:
        raw_score -= 5
        if any(_keyword_in_text(x, normalized_primary) for x in ["regala dinero", "lanzamiento de dinero", "influencer", "caos", "disturbios"]):
            raw_score = min(raw_score, 2)

    # Si es retail pero sin señal de negocio útil, mantenerlo debajo del corte
    if strong_retail_signal and not business_positive_matches and low_value_retail_matches:
        raw_score = min(raw_score, 2)

    # Si solo hay señales débiles, no dejar que escale demasiado
    if not strong_retail_signal and weak_retail_signal:
        raw_score = min(raw_score, 1)

    # Casos sin señal retail real deben quedar fuera
    if not strong_retail_signal and raw_score < STRONG_RETAIL_SIGNAL_THRESHOLD:
        return 0

    return max(0, min(raw_score, 10))
