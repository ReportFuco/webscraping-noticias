from utils import score_noticia, EvolutionWhatsApp
from database import create_db, get_session
from models import Noticia, Usuario
from sqlalchemy.exc import IntegrityError
import config as ENV


bot = EvolutionWhatsApp(**ENV.EVOLUTION_CREDENCIALS)

def procesar_noticias():
    session = next(get_session())
    total_nuevas = 0
    
    # Mensaje 
    bot.enviar_mensaje(
        "56978086719", 
        "Comenzando el scraping", 
        delay=1200
    )

    for ScraperClass in ENV.SCRAPERS:
        scraper = ScraperClass()
        print(f"\n▶ Scrapeando {scraper.source}...")

        try:
            noticias = scraper.fetch()
        except Exception as e:
            print(f"  ✗ Error en {scraper.source}: {e}")
            continue

        for noticia in noticias:
            score = score_noticia(noticia.title)

            if score < ENV.SCORE_MINIMO:
                continue

            db_noticia = Noticia(
                title=noticia.title,
                url=noticia.url,
                img=noticia.img,
                date_preview=noticia.date_preview,
                source=noticia.source,
                score=score,
            )

            try:
                session.add(db_noticia)
                session.commit()
                session.refresh(db_noticia)
                print(f"  ✔ [{score}/10] {noticia.title[:60]}...")
                total_nuevas += 1
            except IntegrityError:
                session.rollback()
                continue

    bot.enviar_mensaje(
        numero="56978086719",
        mensaje=f"Proceso terminado — {total_nuevas} noticias nuevas guardadas",
        delay=1200
    )


if __name__ == "__main__":

    create_db()
    procesar_noticias()