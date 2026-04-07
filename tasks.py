from invoke import task

import config as ENV


PYTHON = "PYTHONPATH=src ./.venv/bin/python"


def _available_sources() -> list[str]:
    return sorted(scraper.source for scraper in ENV.SCRAPERS)


@task(help={"source": "Fuente específica a probar. Usa 'inv list-sources' para ver opciones válidas."})
def test_scrapers(c, source=""):
    """Prueba scrapers. Todos por defecto; usa --source para uno específico."""
    command = f"{PYTHON} src/scripts/test_scrapers.py"
    if source:
        command += f" --source {source}"
    c.run(command, pty=True)


@task
def list_sources(c):
    """Lista las fuentes válidas para usar con inv test-scrapers --source=..."""
    print("Fuentes disponibles:")
    for source in _available_sources():
        print(f"- {source}")


@task
def run_news(c):
    """Ejecuta el flujo normal: scrapeo, filtro, guardado y envío a contactos registrados."""
    c.run(f"{PYTHON} src/main.py", pty=True)


@task
def review_csv(c):
    """Genera el CSV de revisión y lo envía por WhatsApp a Francisco."""
    c.run(f"{PYTHON} src/scripts/export_scrape_review_csv.py", pty=True)
