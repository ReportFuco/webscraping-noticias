"""
Tests de `RSSScraper`, la base que comparten Perú Retail, Expansión y EjePrime.

Sin red: se le pasa XML literal a los helpers. Lo que se cubre es lo que puede
romper una fuente entera en silencio — una fecha que no parsea o un feed con
basura al final dejan la fuente en cero sin lanzar excepción.
"""
from datetime import date
from xml.etree import ElementTree as ET

import pytest

from scrapers.rss import RSSScraper


class _Feed(RSSScraper):
    source = "test"
    country = "PE"
    URL = "https://ejemplo.pe/feed/"


@pytest.fixture
def s():
    return _Feed()


def item(xml: str) -> ET.Element:
    envoltura = (
        '<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" '
        'xmlns:media="http://search.yahoo.com/mrss/"><channel><item>'
        + xml
        + "</item></channel></rss>"
    )
    return ET.fromstring(envoltura).find("./channel/item")


# --- _parse_fecha -----------------------------------------------------------


def test_parsea_pubdate_rfc822(s):
    assert s._parse_fecha("Mon, 07 Sep 2026 21:46:32 +0000") == date(2026, 9, 7)


def test_parsea_pubdate_con_zona_horaria_con_nombre(s):
    assert s._parse_fecha("Mon, 07 Sep 2026 17:43:36 GMT") == date(2026, 9, 7)


@pytest.mark.parametrize("valor", [None, "", "ayer", "2026-13-45"])
def test_fecha_ilegible_devuelve_none(s, valor):
    assert s._parse_fecha(valor) is None


# --- _xml_limpio ------------------------------------------------------------


def test_recorta_el_script_que_cloudflare_pega_despues_del_rss(s):
    crudo = b"<rss><channel></channel></rss>\n<script>window.__CF$cv$params</script>"
    assert s._xml_limpio(crudo) == b"<rss><channel></channel></rss>"
    # Y lo importante: lo recortado vuelve a ser parseable.
    assert ET.fromstring(s._xml_limpio(crudo)).tag == "rss"


def test_un_feed_sano_pasa_intacto(s):
    crudo = b"<rss><channel></channel></rss>"
    assert s._xml_limpio(crudo) == crudo


def test_sin_cierre_de_rss_no_inventa_nada(s):
    crudo = b"<html>esto no es un feed</html>"
    assert s._xml_limpio(crudo) == crudo


# --- _extraer_imagen --------------------------------------------------------


def test_saca_la_imagen_de_media_content(s):
    assert s._extraer_imagen(
        item('<media:content url="https://cdn.pe/a.jpg" />')
    ) == "https://cdn.pe/a.jpg"


def test_saca_la_imagen_de_media_thumbnail(s):
    assert s._extraer_imagen(
        item('<media:thumbnail url="https://cdn.pe/t.jpg" />')
    ) == "https://cdn.pe/t.jpg"


def test_saca_la_imagen_del_enclosure(s):
    assert s._extraer_imagen(
        item('<enclosure url="https://cdn.pe/e.jpg" type="image/jpeg" />')
    ) == "https://cdn.pe/e.jpg"


def test_ignora_un_enclosure_que_no_es_imagen(s):
    # Los feeds con podcast adjuntan audio en el mismo lugar.
    assert s._extraer_imagen(
        item('<enclosure url="https://cdn.pe/audio.mp3" type="audio/mpeg" />')
    ) is None


def test_saca_la_imagen_del_cuerpo_de_wordpress(s):
    cuerpo = '<content:encoded><![CDATA[<p>hola</p><img src="https://cdn.pe/w.jpg" />]]></content:encoded>'
    assert s._extraer_imagen(item(cuerpo)) == "https://cdn.pe/w.jpg"


def test_sin_imagen_devuelve_none_y_no_revienta(s):
    # El pipeline la completa después con la og:image de la nota.
    assert s._extraer_imagen(item("<title>sin foto</title>")) is None
