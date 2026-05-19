import re
import unicodedata

from .scorer_keywords import (
    AMBIGUOUS_BRANDS,
    BUSINESS_POSITIVE_WORDS,
    COMMERCE_BUSINESS_HINTS,
    CRIME_WORDS,
    GENERIC_WORLD_WORDS,
    HIGH_IMPACT,
    INDIRECT_WORDS,
    LOW_VALUE_RETAIL_WORDS,
    MACRO_WORDS,
    NEGATIVE_HINTS,
    STRONG_RETAIL_SIGNAL_THRESHOLD,
    SUPPLIER_WORDS,
    TOPIC_WORDS,
)


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
    weak_retail_signal = bool(indirect_matches or commerce_hint_matches)

    raw_score = 0

    # Capa 1: retail directo
    raw_score += len(high_matches) * 4
    raw_score += len(topic_matches) * 3

    # Capa 2: proveedores ligados al canal
    raw_score += len(supplier_matches) * 2
    if supplier_matches and (topic_matches or indirect_matches):
        raw_score += 2

    # Capa 3: retail indirecto / operación del canal
    if strong_retail_signal:
        raw_score += len(indirect_matches) * 1

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
    if commerce_hint_matches and not (high_matches or topic_matches or supplier_matches) and not (world_matches or crime_matches):
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
