# Cron de noticias

Hay **dos** entradas, porque no todas las fuentes rinden a la misma cadencia.

## Grupos

| Grupo | Fuentes | Cadencia | Por qué |
|---|---|---|---|
| `frecuentes` | 21 medios y portales | cada 3 h | publican durante todo el día |
| `diarios` | walmartchile, cencosud, smu, capital | 1 vez al día | salas de prensa corporativas: publican 1-2 veces al mes |

El grupo se elige con la variable `SCRAPER_GRUPO`. Sin ella, corren todas
(`todos`).

## Crontab actual

```cron
CRON_TZ=America/Santiago

# Medios y portales: cada 3 horas
0 7,10,13,16,19,22 * * * cd /root/.openclaw/workspace/webscraping-noticias && SCRAPER_GRUPO=frecuentes SCRAPER_TRIGGER=cron ./scripts/run_scraper.sh >> /root/.openclaw/workspace/webscraping-noticias/logs/cron.log 2>&1

# Salas de prensa corporativas: una vez al día
30 8 * * * cd /root/.openclaw/workspace/webscraping-noticias && SCRAPER_GRUPO=diarios SCRAPER_TRIGGER=cron-diario ./scripts/run_scraper.sh >> /root/.openclaw/workspace/webscraping-noticias/logs/cron.log 2>&1
```

`SCRAPER_TRIGGER` queda guardado en `scraperun.trigger`, así que se puede
distinguir en la base qué disparó cada corrida.

## Manualmente

```bash
inv run-news                      # todas
inv run-news --grupo frecuentes
inv run-news --grupo diarios
```

## Revisar logs

```bash
tail -f /root/.openclaw/workspace/webscraping-noticias/logs/news_scraper.log
tail -f /root/.openclaw/workspace/webscraping-noticias/logs/cron.log
```

Los logs rotan solos: los de la app vía `RotatingFileHandler`
(`src/utils/logging_config.py`, 10 MB × 5), los del shell vía
`/etc/logrotate.d/webscraping-noticias`.
