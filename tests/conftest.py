import sys
from pathlib import Path

# El proyecto se ejecuta siempre con PYTHONPATH=src; los tests hacen lo mismo
# para poder importar `utils`, `scrapers`, etc. sin instalar el paquete.
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
