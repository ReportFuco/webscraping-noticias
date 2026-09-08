import asyncio
import html
import json
import re
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
}

META_PATTERNS = [
    r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
    r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:description["\']',
    r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']',
]

# Mismo orden de preferencia que las bajadas: og primero, luego el equivalente
# de Twitter. Van los dos sentidos porque el orden de los atributos dentro del
# <meta> depende del CMS y no hay forma de asumir uno.
IMG_PATTERNS = [
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']',
    r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:image["\']',
    r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\'](.*?)["\']',
    r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']twitter:image["\']',
]

JSON_LD_PATTERN = r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
P_TAG_PATTERN = r"<p[^>]*>(.*?)</p>"


@dataclass(frozen=True)
class MetadatosPagina:
    """Lo que se saca de una sola visita a la nota: bajada e imagen.

    Las dos cosas salen del mismo HTML, así que pedirlas por separado sería
    bajar la página dos veces. `img` es `None` cuando la nota no declara
    og:image ni twitter:image.
    """

    excerpt: str | None = None
    img: str | None = None


def _clean_text(text: str, max_chars: int = 500) -> str:
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars].strip()


def _extract_meta_description(raw_html: str) -> str | None:
    for pattern in META_PATTERNS:
        match = re.search(pattern, raw_html, re.IGNORECASE | re.DOTALL)
        if match:
            text = _clean_text(match.group(1))
            if text:
                return text
    return None


def _extract_from_json_ld(raw_html: str) -> str | None:
    matches = re.findall(JSON_LD_PATTERN, raw_html, re.IGNORECASE | re.DOTALL)
    for match in matches:
        try:
            payload = json.loads(match.strip())
        except Exception:
            continue

        candidates = payload if isinstance(payload, list) else [payload]
        for item in candidates:
            if not isinstance(item, dict):
                continue

            for key in ["description", "headline", "alternativeHeadline"]:
                value = item.get(key)
                if isinstance(value, str):
                    text = _clean_text(value)
                    if text and len(text) >= 40:
                        return text

            article_body = item.get("articleBody")
            if isinstance(article_body, str):
                text = _clean_text(article_body)
                if text and len(text) >= 40:
                    return text
    return None


def _extract_first_paragraph(raw_html: str) -> str | None:
    paragraphs = re.findall(P_TAG_PATTERN, raw_html, re.IGNORECASE | re.DOTALL)
    for paragraph in paragraphs:
        text = _clean_text(paragraph)
        if len(text) >= 80:
            return text
    return None


def _extract_excerpt_from_html(raw_html: str, max_chars: int = 500) -> str | None:
    for extractor in (_extract_meta_description, _extract_from_json_ld, _extract_first_paragraph):
        text = extractor(raw_html)
        if text:
            return text[:max_chars].strip()
    return None


def _extract_image_from_html(raw_html: str, base_url: str = "") -> str | None:
    """
    Devuelve la imagen de portada declarada por la nota, absoluta.

    Existe porque hay feeds RSS que no traen imagen (Perú Retail, Expansión,
    EjePrime): sin esto, cada scraper de esos medios tendría que bajar la nota
    por su cuenta, duplicando la visita que el pipeline ya hace para la bajada.
    """
    for pattern in IMG_PATTERNS:
        match = re.search(pattern, raw_html, re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        url = html.unescape(match.group(1)).strip()
        if not url:
            continue
        # Algunos CMS publican la og:image relativa o protocol-relative.
        if url.startswith("//"):
            return f"https:{url}"
        if url.startswith(("http://", "https://")):
            return url
        if base_url:
            return urljoin(base_url, url)
    return None


async def _fetch_metadatos(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    url: str,
    max_chars: int = 500,
) -> tuple[str, MetadatosPagina]:
    async with semaphore:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError:
            return url, MetadatosPagina()

        raw_html = response.text[:300000]
        # `response.url` y no `url`: tras un redirect, una og:image relativa se
        # resuelve contra el destino real y no contra la URL que traía el feed.
        return url, MetadatosPagina(
            excerpt=_extract_excerpt_from_html(raw_html, max_chars=max_chars),
            img=_extract_image_from_html(raw_html, base_url=str(response.url)),
        )


async def extraer_metadatos_batch_async(
    urls: list[str],
    timeout: int = 20,
    max_chars: int = 500,
    concurrency: int = 4,
) -> dict[str, MetadatosPagina]:
    unique_urls = list(dict.fromkeys(urls))
    if not unique_urls:
        return {}

    semaphore = asyncio.Semaphore(max(1, concurrency))
    async with httpx.AsyncClient(
        headers=DEFAULT_HEADERS,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        results = await asyncio.gather(
            *[_fetch_metadatos(client, semaphore, url, max_chars=max_chars) for url in unique_urls]
        )

    return dict(results)


def extraer_metadatos_batch(
    urls: list[str],
    timeout: int = 20,
    max_chars: int = 500,
    concurrency: int = 4,
) -> dict[str, MetadatosPagina]:
    return asyncio.run(
        extraer_metadatos_batch_async(
            urls,
            timeout=timeout,
            max_chars=max_chars,
            concurrency=concurrency,
        )
    )


async def extraer_bajadas_batch_async(
    urls: list[str],
    timeout: int = 20,
    max_chars: int = 500,
    concurrency: int = 4,
) -> dict[str, str | None]:
    metadatos = await extraer_metadatos_batch_async(
        urls,
        timeout=timeout,
        max_chars=max_chars,
        concurrency=concurrency,
    )
    return {url: meta.excerpt for url, meta in metadatos.items()}


def extraer_bajadas_batch(
    urls: list[str],
    timeout: int = 20,
    max_chars: int = 500,
    concurrency: int = 4,
) -> dict[str, str | None]:
    """
    Solo las bajadas. La usan los scripts de auditoría y backfill, a los que la
    imagen no les sirve de nada; el pipeline usa `extraer_metadatos_batch`.
    """
    return {
        url: meta.excerpt
        for url, meta in extraer_metadatos_batch(
            urls,
            timeout=timeout,
            max_chars=max_chars,
            concurrency=concurrency,
        ).items()
    }


def extraer_bajada(url: str, timeout: int = 20, max_chars: int = 500) -> str | None:
    """
    Extrae una bajada corta desde la URL de la noticia.
    Prioriza og:description, description y JSON-LD.
    Usa un primer párrafo como fallback.
    """
    return extraer_bajadas_batch([url], timeout=timeout, max_chars=max_chars, concurrency=1).get(url)
