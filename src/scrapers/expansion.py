from .rss import RSSScraper


class ExpansionScraper(RSSScraper):
    """
    Expansión (México), sección Empresas. Tapa el hueco de MX, que no tenía
    ninguna fuente.

    Va a `/rss/empresas` y no al feed general a propósito: medidos el mismo
    día, el general dejó 2 noticias de 20 y ambas eran política fiscal, y este
    dejó 5 de 39 encabezadas por OXXO, Tiendas 3B y el IEPS a las tienditas.
    Mismo medio, mismo scorer, la diferencia es de dónde se lee.
    """

    source = "expansion"
    country = "MX"
    BASE_URL = "https://expansion.mx"
    URL = "https://expansion.mx/rss/empresas"
