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

SCRAPERS: list[type[BaseScraper]] = [
    MeganoticiasScraper,
    BioBioScraper,
    TheClinicScraper,
    ElMostradorScraper,
    WalmartChileScraper,
    PortalInnovaScraper,
    PublimetroScraper,
    DFScraper,
    DFRetailScraper,
    CCSScraper,
    AndaScraper,
    InfobaeAmericaScraper,
    CencosudMediosScraper,
    SMUScraper,
    GestionScraper,
    DiarioEstrategiaScraper,
    LaTerceraPulsoScraper,
]
SCORE_MINIMO = 3

__all__=[
    "DATABASE_USER", "DATABASE_PASSWORD", "DATABASE_NAME", "DATABASE_HOST", "DATABASE_PORT",
    "EVOLUTION_CREDENCIALS", "SCORE_MINIMO", "SCRAPERS"
]
