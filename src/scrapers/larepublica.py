from .rss import RSSScraper


class LaRepublicaScraper(RSSScraper):
    """
    La República (Colombia), diario económico.

    **Usa el feed de `empresas`, no el general.** Medido el 8 de septiembre de
    2026 sobre la misma corrida: `/rss` dejó 2 de 60 noticias sobre el mínimo
    del scorer y `/rss/empresas` dejó 8 de 60, con Grupo Éxito, aperturas de
    tiendas e inversión. Es el mismo costo de red por cuatro veces la señal.

    Cubre el hueco que Valora Analitik no alcanza: Valora es mercado de
    capitales y esta es la sección de empresas.
    """

    source = "larepublica"
    country = "CO"
    BASE_URL = "https://www.larepublica.co"
    URL = "https://www.larepublica.co/rss/empresas"
