from scrapers import *
from dotenv import load_dotenv
from os import getenv


load_dotenv()


# Variables de Bases de datos
DATABASE_USER=getenv("DATABASE_USER", "")
DATABASE_PASSWORD=getenv("DATABASE_PASSWORD", "")
DATABASE_NAME=getenv("DATABASE_NAME", "")
DATABASE_HOST=getenv("DATABASE_HOST", "127.0.0.1")
DATABASE_PORT=getenv("DATABASE_PORT", "5432")

# Credenciales de Evolution API
EVOLUTION_CREDENCIALS={
    "url": getenv("URL_EVOLUTION", ""),
    "instance": getenv("INSTANCE_EVOLUTION", ""),
    "api_key": getenv("APIKEY_EVOLUTION", "")
}

# Medios y portales que publican durante todo el día: corren en cada ciclo.
SCRAPERS_FRECUENTES: list[type[BaseScraper]] = [
    MeganoticiasScraper,
    BioBioScraper,
    TheClinicScraper,
    ElMostradorScraper,
    PortalInnovaScraper,
    PublimetroScraper,
    DFScraper,
    DFRetailScraper,
    CCSScraper,
    AndaScraper,
    InfobaeAmericaScraper,
    GestionScraper,
    DiarioEstrategiaScraper,
    LaTerceraPulsoScraper,
    CronistaScraper,
    ValoraAnalitikScraper,
    JustRetailScraper,
    RetailActualScraper,
    PeruRetailScraper,
    ExpansionScraper,
    EjePrimeScraper,
]

# Salas de prensa corporativas y similares: publican una o dos veces al mes, así
# que revisarlas cada 3 horas es trabajo perdido. Medido sobre 30 días:
# smu 3.760 revisadas → 3 noticias, capital 2.214 → 2, walmartchile 1.256 → 3,
# cencosud 396 → 3. Corren una vez al día (SCRAPER_GRUPO=diarios).
SCRAPERS_DIARIOS: list[type[BaseScraper]] = [
    WalmartChileScraper,
    CencosudMediosScraper,
    SMUScraper,
    CapitalScraper,
]

# Unión de ambos grupos. Es lo que usan `inv list-sources`, `test_scrapers.py` y
# cualquier consumidor que necesite el catálogo completo de fuentes.
SCRAPERS: list[type[BaseScraper]] = SCRAPERS_FRECUENTES + SCRAPERS_DIARIOS

GRUPOS_SCRAPERS: dict[str, list[type[BaseScraper]]] = {
    "frecuentes": SCRAPERS_FRECUENTES,
    "diarios": SCRAPERS_DIARIOS,
    "todos": SCRAPERS,
}

SCORE_MINIMO = 3
MAX_NEWS_AGE_DAYS = 4

# Noticias por usuario y por corrida. Cada una pesa ~450 caracteres, o sea que
# 20 son ~8.200: el doble del limite de un mensaje de WhatsApp. Por eso el
# envio se parte en varios mensajes (`MAX_CARACTERES_MENSAJE`); subir este
# numero sin eso hacia que Evolution rechazara el envio entero.
MAX_NOTICIAS_POR_ENVIO = 20

# Tope por mensaje. WhatsApp corta el texto en 4.096 caracteres; se deja aire
# porque el corte se calcula antes de agregar el encabezado de la parte.
MAX_CARACTERES_MENSAJE = 3500
MAX_SCRAPER_WORKERS = 10

# Reintentos por fuente. Las fallas dominantes son timeouts transitorios de
# Playwright y 5xx puntuales de RSS, que se recuperan al segundo intento.
SCRAPER_MAX_INTENTOS = 3
SCRAPER_BACKOFF_SEGUNDOS = 5

# API
JWT_SECRET = getenv("JWT_SECRET", "")

__all__ = [
    "DATABASE_USER", "DATABASE_PASSWORD", "DATABASE_NAME", "DATABASE_HOST", "DATABASE_PORT",
    "EVOLUTION_CREDENCIALS", "SCORE_MINIMO", "SCRAPERS",
    "SCRAPERS_FRECUENTES", "SCRAPERS_DIARIOS", "GRUPOS_SCRAPERS",
    "SCRAPER_MAX_INTENTOS", "SCRAPER_BACKOFF_SEGUNDOS",
    "MAX_NEWS_AGE_DAYS", "MAX_SCRAPER_WORKERS",
    "MAX_NOTICIAS_POR_ENVIO", "MAX_CARACTERES_MENSAJE",
    "JWT_SECRET",
]
