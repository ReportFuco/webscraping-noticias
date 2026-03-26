from scrapers import *
from dotenv import load_dotenv
from os import getenv


load_dotenv()


# Variables de Bases de datos
DATABASE_USER=getenv("DATABASE_USER", "")
DATABASE_PASSWORD=getenv("DATABASE_PASSWORD", "")
DATABASE_NAME=getenv("DATABASE_NAME", "")

# Credenciales de Evolution API
EVOLUTION_CREDENCIALS={
    "url": getenv("URL_EVOLUTION", ""),
    "instance": getenv("INSTANCE_EVOLUTION", ""),
    "api_key": getenv("APIKEY_EVOLUTION", "")
}

SCRAPERS: list[type[BaseScraper]] = [
    MeganoticiasScraper,
    BioBioScraper,
    TheClinicScraper,
    ElMostradorScraper,
    WalmartChileScraper,
    PortalInnovaScraper,
    PublimetroScraper,
    DFScraper,
    DFLabScraper,
    DFRetailScraper,
    CCSScraper,
]
SCORE_MINIMO = 2

__all__=[
    "DATABASE_USER", "DATABASE_PASSWORD", "DATABASE_NAME",
    "EVOLUTION_CREDENCIALS", "SCORE_MINIMO", "SCRAPERS"
]
