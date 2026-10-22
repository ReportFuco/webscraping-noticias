# Cron de noticias

Hay **dos** entradas, porque no todas las fuentes rinden a la misma cadencia.

## Grupos

| Grupo | Fuentes | Cadencia | Por qué |
|---|---|---|---|
| `frecuentes` | 23 medios y portales | cada 2 h | publican durante todo el día |
| `diarios` | walmartchile, cencosud, smu, capital, sofofa, revistalogistec | 1 vez al día | salas de prensa y gremios: publican 1-2 veces al mes |

El grupo se elige con la variable `SCRAPER_GRUPO`. Sin ella, corren todas
(`todos`).

## Crontab actual

Vive en el crontab de `report-fuco` (`crontab -e` con ese usuario), no en el
de root. Hasta el 2026-10-22 el proyecto corría como root dentro de
`/root/.openclaw/workspace`; se movió al retirar OpenClaw del servidor. La API
(`noticias-api.service`) también corre como `report-fuco` desde esta ruta. Los
navegadores de Playwright están en `~report-fuco/.cache/ms-playwright`.

```cron
CRON_TZ=America/Santiago

# Medios y portales: cada 2 horas
0 7-23/2 * * * cd /home/report-fuco/proyectos/webscraping-noticias && SCRAPER_GRUPO=frecuentes SCRAPER_TRIGGER=cron ./scripts/run_scraper.sh >> /home/report-fuco/proyectos/webscraping-noticias/logs/cron.log 2>&1

# Salas de prensa corporativas: una vez al día
30 8 * * * cd /home/report-fuco/proyectos/webscraping-noticias && SCRAPER_GRUPO=diarios SCRAPER_TRIGGER=cron-diario ./scripts/run_scraper.sh >> /home/report-fuco/proyectos/webscraping-noticias/logs/cron.log 2>&1
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
tail -f /home/report-fuco/proyectos/webscraping-noticias/logs/news_scraper.log
tail -f /home/report-fuco/proyectos/webscraping-noticias/logs/cron.log
```

Los logs rotan solos: los de la app vía `RotatingFileHandler`
(`src/utils/logging_config.py`, 10 MB × 5), los del shell vía
`/etc/logrotate.d/webscraping-noticias`.
