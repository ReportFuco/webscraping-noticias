"""
Regresión del scorer.

Las aserciones son sobre el *contrato* (¿pasa o no el corte de SCORE_MINIMO?),
no sobre el número exacto: el score se afina seguido y fijar valores exactos
haría que estos tests fallen en cada ajuste sin señalar un problema real.
"""
import pytest

from config import SCORE_MINIMO
from utils.scorer import score_noticia

# --- casos que DEBEN pasar el corte -----------------------------------------

RELEVANTES = [
    (
        "Supermercado nacional anuncia que congela precios de más de 70 productos",
        "Meganoticias",
        "La iniciativa de Tottus busca aliviar el bolsillo de los clientes con "
        "precios estables en productos esenciales.",
    ),
    (
        "Cencosud inicia proceso de refinanciamiento de Bonos 2027 emitidos en "
        "mercados internacionales",
        "diarioestrategia",
        "La compañía lanzó una oferta para adquirir bonos y refinanciar pasivos.",
    ),
    (
        "Mercado Libre anuncia inversión histórica en Chile por US$ 750 millones",
        "portalinnova",
        "La inversión fortalecerá la operación logística y ampliará la red de "
        "distribución.",
    ),
    (
        "Comercio electrónico bordeó los US$ 10 mil millones en 2025",
        "ccs",
        "La Cámara de Comercio de Santiago estima que el e-commerce cerró 2025 "
        "con crecimiento real sobre 9%.",
    ),
    (
        "Pymes con Impacto cierra con más de 500 empresas y foco en sostenibilidad",
        "ccs",
        "Programa fortalece la sostenibilidad de pymes proveedoras y su "
        "integración a cadenas de suministro más competitivas.",
    ),
    (
        "Cenco Malls anuncia acuerdo para adquirir participación mayoritaria en "
        "Plaza Central",
        "cencosud",
        "La operación fortalece la presencia regional de la compañía en centros "
        "comerciales.",
    ),
]

# --- casos que NO deben pasar el corte --------------------------------------

RUIDO = [
    (
        "Vamos a volver a hacerlo en otro mall: Premia2 anuncia nuevo lanzamiento "
        "de dinero pese al caos en Mallplaza Vespucio",
        "Meganoticias",
        "La plataforma anunció otro evento tras el caos ocurrido en el centro comercial.",
    ),
    (
        "El líder supremo de Irán dijo que la muerte de su jefe de inteligencia no "
        "frenará la ofensiva",
        "infobaeamerica",
        "El régimen iraní insistió en mantener su cohesión en Medio Oriente.",
    ),
    (
        "Kaiser en modo oposición: Gobierno al debe y pide que proyecto de "
        "reconstrucción venga separado",
        "elmostrador",
        "El líder del partido cuestionó al Ejecutivo por el alza de combustibles.",
    ),
    (
        "Operativo municipal contra el comercio ambulante en Viña del Mar termina "
        "con seis detenidos",
        "biobiochile",
        "El despliegue dejó varios detenidos tras fiscalizaciones en el centro.",
    ),
]


@pytest.mark.parametrize("title,source,excerpt", RELEVANTES)
def test_noticias_relevantes_pasan_el_corte(title, source, excerpt):
    score = score_noticia(title=title, source=source, excerpt=excerpt)
    assert score >= SCORE_MINIMO, f"score={score} quedó bajo el corte para: {title}"


@pytest.mark.parametrize("title,source,excerpt", RUIDO)
def test_ruido_no_pasa_el_corte(title, source, excerpt):
    score = score_noticia(title=title, source=source, excerpt=excerpt)
    assert score < SCORE_MINIMO, f"score={score} pasó el corte y no debería: {title}"


# --- invariantes del scorer -------------------------------------------------


def test_score_siempre_en_rango():
    """El scorer promete devolver un entero entre 0 y 10."""
    casos = RELEVANTES + RUIDO
    for title, source, excerpt in casos:
        score = score_noticia(title=title, source=source, excerpt=excerpt)
        assert isinstance(score, int)
        assert 0 <= score <= 10


def test_texto_vacio_da_cero():
    assert score_noticia("", "", "") == 0


def test_source_y_url_no_crean_relevancia_por_si_solos():
    """
    Regla explícita del diseño: la metadata solo refuerza una señal retail que
    ya existe en el texto. Un título sin señal no debe pasar solo porque venga
    de una fuente retail.
    """
    score = score_noticia(
        title="Reunión del comité central discute el calendario de sesiones",
        url="https://www.df.cl/empresas/retail/nota",
        source="dfretail",
        excerpt="La instancia definió las fechas de las próximas reuniones.",
    )
    assert score < SCORE_MINIMO


def test_marca_ambigua_necesita_contexto():
    """
    'Lider' es marca ambigua: solo cuenta como señal retail si aparece junto a
    contexto de supermercado/tienda. Sin contexto no debe puntuar como retail.
    """
    sin_contexto = score_noticia(
        title="El líder del sindicato anunció una nueva jornada de movilización",
        source="biobiochile",
        excerpt="El dirigente convocó a sus bases para la próxima semana.",
    )
    con_contexto = score_noticia(
        title="Lider abre nuevo supermercado en Antofagasta",
        source="Meganoticias",
        excerpt="La cadena inaugura un local con foco en abastecimiento local.",
    )
    assert sin_contexto < SCORE_MINIMO
    assert con_contexto >= SCORE_MINIMO


def test_acentos_y_mayusculas_no_afectan():
    """El scorer normaliza (minúsculas + sin acentos) antes de buscar keywords."""
    a = score_noticia(
        title="CENCOSUD ANUNCIÓ UNA INVERSIÓN EN LOGÍSTICA",
        source="df",
        excerpt="La compañía destinará recursos a su centro de distribución.",
    )
    b = score_noticia(
        title="cencosud anuncio una inversion en logistica",
        source="df",
        excerpt="La compania destinara recursos a su centro de distribucion.",
    )
    assert a == b
