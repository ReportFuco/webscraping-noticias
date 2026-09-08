from .rss import RSSScraper


class RevistaLogistecScraper(RSSScraper):
    """
    Revista Logistec (Chile), supply chain y logística comercial.

    Es la única fuente de la lista que cubre el lado logístico del retail
    —centros de distribución, última milla, transporte— desde Chile y no desde
    España. Pasaron 2 de 10 en la medición del 8 de septiembre de 2026.

    Va en el grupo `diarios`: es una revista, publica por tandas y no a lo
    largo del día.

    El feed cuelga de `/index.php/` porque el sitio expone Joomla sin reescribir
    la URL; `/feed/` a secas responde 404.
    """

    source = "revistalogistec"
    country = "CL"
    BASE_URL = "https://www.revistalogistec.com"
    URL = "https://www.revistalogistec.com/index.php/feed/"
