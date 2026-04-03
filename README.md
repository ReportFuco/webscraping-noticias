# Webscraping Noticias

Scraper de noticias orientado a **retail, supermercados, consumo masivo, logística comercial y señales corporativas relevantes**.

El proyecto:
- agrega noticias desde múltiples medios/sitios corporativos,
- extrae `excerpt` para mejorar relevancia,
- puntúa cada noticia con un scorer propio,
- guarda en PostgreSQL,
- evita duplicados por URL,
- y envía resúmenes por WhatsApp mediante Evolution API.

## Estado actual

Hoy el proyecto ya incluye:
- **PostgreSQL** como base principal
- **scraping multi-fuente**
- **deduplicación por URL antes de insertar**
- **excerpts concurrentes con `httpx.AsyncClient`** (concurrencia segura = 4)
- **scoring endurecido** para bajar ruido policial/internacional genérico
- **envío por WhatsApp** con límite actual de **10 noticias por usuario**
- relación de vistas/envíos con **`ON DELETE CASCADE`** para limpiar referencias al borrar noticias

## Cobertura de fuentes

Actualmente el proyecto combina scrapers de:
- medios generalistas
- prensa económica y de negocios
- sitios corporativos y centros de medios
- gremios, asociaciones y actores del ecosistema retail

La cobertura está pensada para capturar señales de:
- supermercados y retail
- consumo masivo
- aperturas/cierres
- resultados financieros
- logística comercial
- inversión y expansión

### Nota
- algunas fuentes pueden requerir ajustes puntuales con el tiempo por cambios de HTML, rate limiting o bloqueos anti-bot.
- `DFLab` fue retirado de la ejecución activa, pero su clase no fue eliminada del código.

## Estructura

```text
webscraping-noticias/
├── .env
├── .env.example
├── compose.yaml
├── CRON.md
├── logs/
├── requirements.txt
├── scripts/
│   └── run_scraper.sh
└── src/
    ├── config.py
    ├── database.py
    ├── main.py
    ├── models/
    ├── scrapers/
    ├── services/
    └── utils/
```

## Stack

- Python 3.12
- SQLModel / SQLAlchemy
- PostgreSQL
- httpx
- Playwright
- Evolution API (WhatsApp)

## Variables de entorno

`.env.example`

```env
# PostgreSQL
DATABASE_USER=
DATABASE_PASSWORD=
DATABASE_NAME=

# Evolution API (opcional / legado)
URL_EVOLUTION=
INSTANCE_EVOLUTION=
APIKEY_EVOLUTION=
```

## Instalación local

```bash
git clone https://github.com/ReportFuco/webscraping-noticias.git
cd webscraping-noticias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Base de datos con Docker

Levantar PostgreSQL con Docker Compose:

```bash
docker compose -f compose.yaml up -d
```

## Ejecutar scraper

```bash
cd webscraping-noticias
./scripts/run_scraper.sh
```

Ese comando hace el flujo completo:
1. scrapea fuentes
2. deduplica
3. extrae excerpts
4. puntúa
5. guarda noticias nuevas
6. envía pendientes por WhatsApp

## Cron

Ver `CRON.md`.

Ejemplo:

```cron
0 */3 * * * cd /ruta/a/webscraping-noticias && ./scripts/run_scraper.sh >> /ruta/a/webscraping-noticias/logs/cron.log 2>&1
```

## Modelo de datos principal

### `noticia`
Guarda la noticia curada:
- `title`
- `url` (única)
- `img`
- `date_preview`
- `source`
- `excerpt`
- `score`
- `created_at`

### `usuario`
Usuarios que reciben noticias por WhatsApp.

### `usuarionoticiavista`
Registra qué noticias ya fueron consideradas/enviadas por usuario.

Actualmente la FK hacia `noticia` usa:
- **`ON DELETE CASCADE`**

Eso evita errores al borrar noticias que ya tenían marcas de envío/visto.

## Scoring actual

El scorer prioriza:
- marcas retail y supermercados
- resultados financieros
- aperturas/cierres
- logística comercial
- consumo masivo
- inversión relevante para retail

Y penaliza con más fuerza:
- crónica policial
- judicial
- internacional genérico
- falsos positivos por palabras ambiguas como “cadena” o “local”

## Mejoras recientes importantes

- excerpts paralelos con concurrencia controlada
- mejor control de duplicados antes de insertar
- límite de envío por usuario subido de **5 → 10**
- fecha agregada al mensaje de WhatsApp
- corrección de URLs públicas de SMU
- limpieza de noticias SMU antiguas para no empujar noticias viejas por cron
- borrado en cascada para referencias de vistas/envíos

## Logs

```bash
tail -f logs/news_scraper.log
tail -f logs/cron.log
```

## Observaciones operativas

- El proyecto hoy está optimizado para **estabilidad + relevancia**, no para scraping masivo agresivo.
- La extracción async se usa solo en `excerpt`, que era donde más convenía acelerar sin volver frágil el pipeline.
- Si quieres medir sin enviar WhatsApp, hoy conviene ejecutar un flujo manual/dry-run controlado desde Python en vez de usar directamente `run_scraper.sh`.

## Próximos pasos razonables

- agregar modo `dry-run` oficial por CLI
- seguir afinando scorer/fuentes internacionales
- separar benchmarking de delivery
- eventualmente agregar métricas/reportes de calidad del feed
