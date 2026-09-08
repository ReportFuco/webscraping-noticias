from .rss import RSSScraper


class LaTerceraPulsoScraper(RSSScraper):
    """
    Pulso, la sección de negocios de La Tercera.

    Antes esto abría Chromium con Playwright, bajaba la portada del canal y
    reconstruía a mano los objetos JSON que Arc deja incrustados en el HTML.
    Funcionaba, pero la portada solo lista lo que alcanza a renderizar: en la
    corrida del 7 de septiembre de 2026 dejó 9 noticias. Arc publica el mismo
    canal como RSS y ahí vienen 39, de las cuales 7 pasan el mínimo del scorer.
    Más cobertura, sin navegador y sin parseo frágil.

    El feed no trae imagen —ni `media:content` ni `<img>` en el
    `content:encoded`—, así que la portada la resuelve el pipeline con la
    `og:image` de la nota, que La Tercera sí publica. La visita a la nota
    ocurre igual para sacar el excerpt, o sea que no es un request extra.

    `?outputType=xml` es obligatorio: sin ese parámetro Arc devuelve JSON.
    """

    source = "latercera_pulso"
    country = "CL"
    BASE_URL = "https://www.latercera.com"
    URL = "https://www.latercera.com/arc/outboundfeeds/rss/category/pulso/?outputType=xml"
