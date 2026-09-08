"""
Tests de los helpers que viven en BaseScraper. Antes estaban duplicados en 18
scrapers y no los cubría nada.
"""
import pytest

from scrapers.base import BaseScraper


class _Scraper(BaseScraper):
    source = "test"
    BASE_URL = "https://ejemplo.cl"

    def fetch(self):
        return []


@pytest.fixture
def s():
    return _Scraper()


# --- _clean_text ------------------------------------------------------------


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("<p>Hola <b>mundo</b></p>", "Hola mundo"),
        ("Falabella &amp; Cencosud", "Falabella & Cencosud"),
        ("guion &#8211; largo", "guion – largo"),
        ("  espacios   colapsados \n\t ya ", "espacios colapsados ya"),
    ],
)
def test_clean_text(s, entrada, esperado):
    assert s._clean_text(entrada) == esperado


@pytest.mark.parametrize("vacio", [None, "", "   ", "<br>", "<p></p>"])
def test_clean_text_devuelve_none_si_no_queda_nada(s, vacio):
    assert s._clean_text(vacio) is None


def test_clean_text_come_entidades_que_parecen_tags(s):
    """
    Comportamiento conocido: `html.unescape` corre antes de quitar etiquetas,
    así que '&lt;algo&gt;' se convierte en '<algo>' y luego se elimina como si
    fuera un tag. No se corrige porque es el comportamiento que ya tenían los
    scrapers y no aparece en titulares reales; queda documentado para que un
    cambio de orden en `_clean_text` sea una decisión consciente.
    """
    assert s._clean_text("&lt;no es tag&gt;") is None


# --- _absolute_url ----------------------------------------------------------


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("https://otro.cl/nota", "https://otro.cl/nota"),
        ("http://otro.cl/nota", "http://otro.cl/nota"),
        ("//cdn.ejemplo.cl/img.jpg", "https://cdn.ejemplo.cl/img.jpg"),
        ("/noticias/1", "https://ejemplo.cl/noticias/1"),
        ("noticias/1", "https://ejemplo.cl/noticias/1"),
    ],
)
def test_absolute_url(s, entrada, esperado):
    assert s._absolute_url(entrada) == esperado


def test_absolute_url_none(s):
    assert s._absolute_url(None) is None
    assert s._absolute_url("") is None


# --- contrato de la clase ---------------------------------------------------


def test_headers_tienen_user_agent_y_idioma(s):
    assert "User-Agent" in s.HEADERS
    assert "Accept-Language" in s.HEADERS


def test_logger_usa_el_nombre_de_la_fuente(s):
    assert s.logger.name == "scraper.test"


def test_country_por_defecto_es_cl(s):
    assert s.country == "CL"


def test_todos_los_scrapers_declaran_source_unico():
    """Dos fuentes con el mismo `source` se pisarían en las stats por fuente."""
    import config as ENV

    fuentes = [c.source for c in ENV.SCRAPERS]
    assert len(fuentes) == len(set(fuentes)), f"sources duplicados: {fuentes}"


def test_scrapers_que_resuelven_urls_relativas_declaran_base_url():
    """
    `_absolute_url` sin BASE_URL genera URLs rotas del tipo '/noticia'. Este
    test evita que alguien agregue un scraper que la use sin declararla.
    """
    import inspect

    import config as ENV

    faltantes = []
    for cls in ENV.SCRAPERS:
        try:
            codigo = inspect.getsource(cls)
        except OSError:  # pragma: no cover
            continue
        if "_absolute_url" in codigo and not cls.BASE_URL:
            faltantes.append(cls.source)

    assert not faltantes, f"usan _absolute_url sin BASE_URL: {faltantes}"
