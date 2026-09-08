from .rss import RSSScraper


class ChocaleScraper(RSSScraper):
    """
    Chócale (Chile), medio de marketing, consumo y retail.

    Publica poco volumen pero casi todo es del tema: en la medición del 8 de
    septiembre de 2026 pasaron 2 de 10 y las dos eran retail puro (el primer
    despacho de Walmart Chile con dron y la apertura de Auto City de Cenco
    Malls). Esa densidad es mejor que la de cualquier generalista chileno que
    evaluamos.

    El feed vive en el dominio sin `www`: `www.chocale.cl` redirige acá.

    **Headers propios a propósito.** Su WAF rechaza con 403 el User-Agent de
    `BaseScraper`, que declara Chrome/122, y responde 200 con uno actual — o
    incluso sin User-Agent. No es anti-bot: es una regla contra navegadores
    viejos, y el nuestro ya tiene más de dos años. Se sobreescribe solo acá
    para no cambiarle los headers a las otras 28 fuentes, que hoy funcionan.
    """

    source = "chocale"
    country = "CL"
    BASE_URL = "https://chocale.cl"
    URL = "https://chocale.cl/feed/"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
