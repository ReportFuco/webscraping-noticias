from .rss import RSSScraper


class EjePrimeScraper(RSSScraper):
    """
    EjePrime (España), negocio inmobiliario.

    Es la fuente menos obvia de las tres: no cubre comercio sino los ladrillos
    donde ocurre. Entra por las notas de afluencia a centros comerciales y
    disponibilidad de locales en calle, que son señal de consumo y que ningún
    otro medio de la lista publica. El resto de su feed (oficinas, residencial)
    lo descarta el scorer.
    """

    source = "ejeprime"
    country = "ES"
    BASE_URL = "https://www.ejeprime.com"
    URL = "https://www.ejeprime.com/rss.xml"
