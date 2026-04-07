from utils.scorer import score_noticia


CASES = [
    {
        "kind": "relevant",
        "title": "Supermercado nacional anuncia que congela precios de más de 70 productos",
        "source": "Meganoticias",
        "excerpt": "La iniciativa de Tottus busca aliviar el bolsillo de los clientes con precios estables en productos esenciales.",
    },
    {
        "kind": "relevant",
        "title": "Cencosud inicia proceso de refinanciamiento de Bonos 2027 emitidos en mercados internacionales",
        "source": "diarioestrategia",
        "excerpt": "La compañía lanzó una oferta para adquirir bonos y refinanciar pasivos.",
    },
    {
        "kind": "relevant",
        "title": "Mercado Libre anuncia inversión histórica en Chile por US$ 750 millones",
        "source": "portalinnova",
        "excerpt": "La inversión fortalecerá la operación logística y ampliará la red de distribución.",
    },
    {
        "kind": "relevant",
        "title": "Comercio electrónico bordeó los US$ 10 mil millones en 2025",
        "source": "ccs",
        "excerpt": "La Cámara de Comercio de Santiago estima que el e-commerce cerró 2025 con crecimiento real sobre 9%.",
    },
    {
        "kind": "relevant",
        "title": "Pymes con Impacto cierra con más de 500 empresas y foco en sostenibilidad",
        "source": "ccs",
        "excerpt": "Programa fortalece la sostenibilidad de pymes proveedoras y su integración a cadenas de suministro más competitivas.",
    },
    {
        "kind": "relevant",
        "title": "Cenco Malls anuncia acuerdo para adquirir participación mayoritaria en Plaza Central",
        "source": "cencosud",
        "excerpt": "La operación fortalece la presencia regional de la compañía en centros comerciales.",
    },
    {
        "kind": "low-value-retail",
        "title": "Vamos a volver a hacerlo en otro mall: Premia2 anuncia nuevo lanzamiento de dinero pese al caos en Mallplaza Vespucio",
        "source": "Meganoticias",
        "excerpt": "La plataforma anunció otro evento tras el caos ocurrido en el centro comercial.",
    },
    {
        "kind": "noise",
        "title": "El líder supremo de Irán dijo que la muerte de su jefe de inteligencia no frenará la ofensiva",
        "source": "infobaeamerica",
        "excerpt": "El régimen iraní insistió en mantener su cohesión en Medio Oriente.",
    },
    {
        "kind": "noise",
        "title": "Kaiser en modo oposición: Gobierno al debe y pide que proyecto de reconstrucción venga separado",
        "source": "elmostrador",
        "excerpt": "El líder del partido cuestionó al Ejecutivo por el alza de combustibles.",
    },
    {
        "kind": "noise",
        "title": "Operativo municipal contra el comercio ambulante en Viña del Mar termina con seis detenidos",
        "source": "biobiochile",
        "excerpt": "El despliegue dejó varios detenidos tras fiscalizaciones en el centro.",
    },
]


if __name__ == "__main__":
    for case in CASES:
        score = score_noticia(
            title=case["title"],
            source=case["source"],
            excerpt=case["excerpt"],
        )
        print(f"[{case['kind']}] score={score:>2} | {case['title']}")
