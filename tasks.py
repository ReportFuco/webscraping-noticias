from pathlib import Path
import sys

from invoke import task

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

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


@task
def db_migrate(c, message="migration"):
    """Genera una migración Alembic a partir de los cambios en los modelos."""
    c.run(f'PYTHONPATH=src ./.venv/bin/alembic revision --autogenerate -m "{message}"', pty=True)


@task
def db_upgrade(c):
    """Aplica todas las migraciones pendientes (alembic upgrade head)."""
    c.run("PYTHONPATH=src ./.venv/bin/alembic upgrade head", pty=True)


@task
def db_downgrade(c):
    """Revierte la última migración (alembic downgrade -1)."""
    c.run("PYTHONPATH=src ./.venv/bin/alembic downgrade -1", pty=True)


@task
def serve(c, host="0.0.0.0", port=8000, reload=True):
    """Levanta la API FastAPI con uvicorn."""
    reload_flag = "--reload" if reload else ""
    c.run(
        f"PYTHONPATH=src ./.venv/bin/uvicorn api.app:app --host {host} --port {port} {reload_flag}",
        pty=True,
    )
