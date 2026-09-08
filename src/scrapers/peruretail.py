from .rss import RSSScraper


class PeruRetailScraper(RSSScraper):
    """
    Perú Retail, el medio retail más grande de Perú.

    Cuidado al depurarlo: la portada del sitio responde 403 (Cloudflare), pero
    el feed y las notas sueltas responden 200. Que `curl https://www.peru-retail.com`
    falle no significa que la fuente esté caída.
    """

    source = "peruretail"
    country = "PE"
    BASE_URL = "https://www.peru-retail.com"
    URL = "https://www.peru-retail.com/feed/"
