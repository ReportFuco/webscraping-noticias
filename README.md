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
- **excerpts concurrentes con `httpx.AsyncClient`** (concurrencia = 8)
- **scoring endurecido** para bajar ruido policial/internacional genérico
- **envío por WhatsApp** con límite actual de **20 noticias por usuario**, partido
  en varios mensajes para no pasarse del tope de 4.096 caracteres de WhatsApp
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

### Cobertura por país

| País | Fuentes |
|---|---|
| Chile | 19 |
| España | 3 (JustRetail, Retail Actual, EjePrime) |
| Argentina | 2 (El Cronista, Infobae América) |
| Perú | 2 (Gestión, Perú Retail) |
| Colombia | 2 (Valora Analitik, La República) |
| México | 1 (Expansión) |
| Brasil, Ecuador, Uruguay, Bolivia, Paraguay | ninguna |

Brasil sigue sin fuente después de evaluarlo: los medios retail del país no son
utilizables hoy —el feed de Mercado&Consumo está congelado desde agosto de 2026 y
SBVC no resuelve por DNS— y los generalistas no rinden. Medido el 7 de septiembre
de 2026 sobre una corrida real, Estadão Economia dejó 0 noticias de 40 y Bloomberg
Línea 3 de 60, ninguna de retail. Sumarlos habría sido costo de red sin señal.

Por la misma razón quedaron fuera Merca2.0 (2 de 40), Modaes (las notas devuelven
403 y son de pago) y The Logistics World, El Economista y Portafolio (sin RSS o
detrás de Cloudflare).

### Fuentes evaluadas el 8 de septiembre de 2026

Se sumaron cuatro, midiendo cada feed candidato con el scorer del propio
proyecto —cuántos ítems pasan `SCORE_MINIMO`— igual que en la evaluación de
Brasil:

| Fuente | País | Rinde | Grupo |
|---|---|---|---|
| La República (sección empresas) | Colombia | 8 de 60 | frecuentes |
| Chócale | Chile | 2 de 10 | frecuentes |
| SOFOFA | Chile | 4 de 10 | diarios |
| Revista Logistec | Chile | 2 de 10 | diarios |

De La República hay que usar `/rss/empresas` y no `/rss`: el feed general deja
2 de 60 y el de empresas 8 de 60, al mismo costo de red.

Quedaron fuera, con el número medido al lado: **iProfesional** (Argentina, 2 de
49 y ambos falsos positivos), **PortalPortuario** (1 de 15, y era un crucero en
Kiel), **El Universo** (Ecuador, 2 de 100 en el feed general; su feed de
economía existe pero viene vacío), **Mercado Negro** (Perú, 403 de Cloudflare
en la home y en el feed) y **Mall & Retail** (Colombia, el más pertinente del
país pero sin RSS parseable: necesita scraper de HTML propio).

Sin RSS usable, o sea que hoy exigirían Playwright: Emol, Cooperativa, T13, CNN
Chile, El Dínamo, Ámbito, La Nación, El Observador (Uruguay), Primicias
(Ecuador), 5días (Paraguay), El Deber (Bolivia), Semana, Infomercado e
InfoNegocios. **ASACH**, el gremio de supermercados de Chile, quedó fuera por
otra razón: su dominio ya no resuelve.

### Nota
- algunas fuentes pueden requerir ajustes puntuales con el tiempo por cambios de HTML, rate limiting o bloqueos anti-bot.
- `DFLab` fue retirado de la ejecución activa, pero su clase no fue eliminada del código.
- `AmericaRetail` también está fuera del flujo: su clase funciona, pero el sitio no
  publica desde el 1 de agosto de 2026 y su contenido era moda y lujo, no consumo.
- la portada de Perú Retail responde 403 (Cloudflare) pero su feed y sus notas
  responden 200; que `curl` a la home falle no significa que la fuente esté caída.
- `Chócale` lleva headers propios: su WAF responde 403 al User-Agent Chrome/122 que declara `BaseScraper` y 200 a uno actual. El UA compartido ya tiene más de dos años; subirlo es una limpieza pendiente aparte.
- `SOFOFA` pierde cerca de la mitad de sus notas al guardar: varias páginas del sitio no declaran `og:image` y `noticia.img` es NOT NULL.

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
0 7-23/2 * * * cd /ruta/a/webscraping-noticias && ./scripts/run_scraper.sh >> /ruta/a/webscraping-noticias/logs/cron.log 2>&1
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
- `latercera_pulso` dejó Playwright y pasó al feed RSS de Arc: 20 noticias por corrida en vez de las 9 que alcanzaba a renderizar la portada
- cuatro fuentes nuevas: La República (empresas), Chócale, SOFOFA y Revista Logistec

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
