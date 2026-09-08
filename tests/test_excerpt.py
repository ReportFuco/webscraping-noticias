"""
Tests del extractor de la imagen de portada. Sin red: todo sobre HTML literal.

Existe porque los feeds RSS de Perú Retail, Expansión y EjePrime no traen
imagen y el pipeline la saca de la nota; si esto se rompe, esas fuentes dejan
de guardar noticias en silencio (`main.py` las descarta por no tener `img`).
"""
import pytest

from utils.excerpt import _extract_image_from_html


BASE = "https://medio.cl/nota/uno"


def test_saca_la_og_image():
    html = '<meta property="og:image" content="https://cdn.medio.cl/foto.jpg">'
    assert _extract_image_from_html(html, BASE) == "https://cdn.medio.cl/foto.jpg"


def test_acepta_los_atributos_al_reves():
    # El orden dentro del <meta> depende del CMS.
    html = '<meta content="https://cdn.medio.cl/foto.jpg" property="og:image">'
    assert _extract_image_from_html(html, BASE) == "https://cdn.medio.cl/foto.jpg"


def test_cae_a_twitter_image_si_no_hay_og():
    html = '<meta name="twitter:image" content="https://cdn.medio.cl/tw.jpg">'
    assert _extract_image_from_html(html, BASE) == "https://cdn.medio.cl/tw.jpg"


def test_prefiere_og_sobre_twitter():
    html = (
        '<meta name="twitter:image" content="https://cdn.medio.cl/tw.jpg">'
        '<meta property="og:image" content="https://cdn.medio.cl/og.jpg">'
    )
    assert _extract_image_from_html(html, BASE) == "https://cdn.medio.cl/og.jpg"


@pytest.mark.parametrize(
    "valor,esperado",
    [
        ("/wp-content/foto.jpg", "https://medio.cl/wp-content/foto.jpg"),
        ("//cdn.medio.cl/foto.jpg", "https://cdn.medio.cl/foto.jpg"),
        ("foto.jpg", "https://medio.cl/nota/foto.jpg"),
    ],
)
def test_resuelve_urls_no_absolutas(valor, esperado):
    html = '<meta property="og:image" content="%s">' % valor
    assert _extract_image_from_html(html, BASE) == esperado


def test_desescapa_entidades():
    html = '<meta property="og:image" content="https://cdn.cl/f.jpg?a=1&amp;b=2">'
    assert _extract_image_from_html(html, BASE) == "https://cdn.cl/f.jpg?a=1&b=2"


def test_sin_meta_devuelve_none():
    assert _extract_image_from_html("<html><body>sin nada</body></html>", BASE) is None


def test_ignora_una_og_image_vacia():
    html = (
        '<meta property="og:image" content="">'
        '<meta name="twitter:image" content="https://cdn.medio.cl/tw.jpg">'
    )
    assert _extract_image_from_html(html, BASE) == "https://cdn.medio.cl/tw.jpg"


def test_sin_base_no_inventa_una_url_relativa():
    html = '<meta property="og:image" content="/foto.jpg">'
    assert _extract_image_from_html(html, "") is None
