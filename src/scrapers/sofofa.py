from .rss import RSSScraper


class SofofaScraper(RSSScraper):
    """
    SOFOFA, el gremio industrial chileno.

    Aporta lo que un medio no publica: inversión, empleo y agenda regulatoria
    vistos desde las empresas socias, varias de ellas proveedores de
    supermercados. Pasaron 4 de 10 en la medición del 8 de septiembre de 2026.

    **Rinde menos de lo que sugiere ese número**: la mitad de sus notas no
    tiene portada. El feed trae imagen en unas pocas y varias páginas del sitio
    no declaran `og:image`, así que el pipeline las descarta al guardar
    (`noticia.img` es NOT NULL). Medido sobre 6 notas, solo 3 llegaron con
    portada. Se aceptó igual porque es una fuente de una corrida al día y lo
    que sí pasa no lo publica nadie más.

    Va en el grupo `diarios` porque publica de a poco: revisarlo cada dos horas
    sería el mismo trabajo perdido que con las salas de prensa corporativas.

    El sitio se sirve desde `web.sofofa.cl`, pero el feed está en el dominio
    principal.
    """

    source = "sofofa"
    country = "CL"
    BASE_URL = "https://www.sofofa.cl"
    URL = "https://www.sofofa.cl/feed/"
