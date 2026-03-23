# Cron de noticias

## Comando recomendado

```bash
cd /root/.openclaw/workspace/webscraping-noticias && ./scripts/run_scraper.sh
```

## Ejemplo de cron cada 3 horas

```cron
0 */3 * * * cd /root/.openclaw/workspace/webscraping-noticias && ./scripts/run_scraper.sh >> /root/.openclaw/workspace/webscraping-noticias/logs/cron.log 2>&1
```

## Ejemplo 4 veces al día

```cron
0 7,11,15,19 * * * cd /root/.openclaw/workspace/webscraping-noticias && ./scripts/run_scraper.sh >> /root/.openclaw/workspace/webscraping-noticias/logs/cron.log 2>&1
```

## Revisar logs

```bash
tail -f /root/.openclaw/workspace/webscraping-noticias/logs/news_scraper.log
tail -f /root/.openclaw/workspace/webscraping-noticias/logs/cron.log
```
