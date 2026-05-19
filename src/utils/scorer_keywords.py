HIGH_IMPACT = [
    "walmart", "express de lider", "acuenta",
    "jumbo", "tottus", "unimarc", "santa isabel", "super 10",
    "cencosud", "smu", "falabella", "ripley", "paris",
    "sodimac", "easy", "mall plaza", "mallplaza", "parque arauco",
    "oxxo", "mass", "alvi", "mayorista 10",
    "mercado libre", "mercadolibre", "spid", "ok market",
    "copec pronto", "upa",
]

AMBIGUOUS_BRANDS = {
    "lider": [
        "supermercado", "supermercados", "walmart", "local", "locales",
        "tienda", "tiendas", "sucursal", "sucursales", "express", "acuenta",
        "retail", "retailer", "apertura", "aperturas",
    ],
    "paris": [
        "tienda", "tiendas", "retail", "retailer", "falabella", "cencosud",
        "ripley", "mall", "malls", "centro comercial",
    ],
}

SUPPLIER_WORDS = [
    "coca cola", "ccu", "unilever", "agrosuper", "soprole", "nestle",
    "carozzi", "arcor", "ideal", "bimbo", "pepsico", "mondelez",
    "softys", "procter", "colun",
]

TOPIC_WORDS = [
    "retail", "retailer", "supermercado", "supermercados",
    "hipermercado", "hipermercados", "tienda", "tiendas",
    "mayorista", "conveniencia", "consumo masivo",
    "canal supermercadista", "canal tradicional", "canal moderno",
    "punto de venta", "ecommerce", "comercio electronico", "omnicanal", "marketplace",
    "farmacia", "farmacias", "mejoramiento del hogar",
    "centro comercial", "centros comerciales", "mall", "malls",
]

INDIRECT_WORDS = [
    "logistica", "distribucion", "ultima milla", "despacho",
    "bodega", "bodegas", "centro de distribucion", "centros de distribucion",
    "inventario", "abastecimiento", "quiebre de stock", "reposicion",
    "proveedor", "proveedores", "cadena de suministro", "supply chain",
    "ticket promedio", "trafico",
    "promocion", "promociones", "descuentos", "ofertas",
    "margen", "margenes", "apertura", "aperturas", "inauguracion",
    "expansion", "expansiones", "cierre", "cierres",
    "sucursal", "sucursales", "adquisicion", "adquisiciones",
    "inversion", "inversiones", "ventas", "ingresos", "utilidades",
    "foodservice", "canal horeca", "gremio", "informalidad",
    "estados financieros", "bonos", "refinanciamiento", "ebitda",
]

NEGATIVE_HINTS = [
    "presidente", "senador", "diputado", "ministro", "gobierno",
    "elecciones", "moneda", "gabinete",
]

CRIME_WORDS = [
    "robo", "robos", "ladron", "ladrones", "asalto", "asaltos", "homicidio",
    "homicidios", "asesinato", "asesinatos", "cadena perpetua", "perpetua",
    "carabinero", "carabineros", "fiscalia", "tribunal", "juez",
    "condena", "condenado", "condenaron", "prision", "crimen", "delito",
    "detenidos", "detenido", "operativo", "ambulante", "fiscalizaciones",
]

GENERIC_WORLD_WORDS = [
    "francia", "ucrania", "rusia", "iran", "israel", "guerra", "onu",
    "trump", "hezbollah", "otan", "kiev", "moscu", "pyongyang", "siria",
]

BUSINESS_POSITIVE_WORDS = [
    "apertura", "aperturas", "inauguracion", "expansion", "expansiones",
    "nuevo local", "nuevos locales", "nueva tienda", "nuevas tiendas",
    "precios congelados", "congela precios", "promocion", "promociones",
    "descuentos", "ofertas", "inversion", "inversiones", "resultados",
    "estados financieros", "ventas", "ingresos", "utilidades", "ebitda",
    "margen", "margenes", "logistica", "distribucion", "ultima milla",
    "centro de distribucion", "abastecimiento", "proveedores", "marketplace",
    "ecommerce", "comercio electronico", "omnicanal", "bonos", "refinanciamiento",
    "adquisicion", "adquisiciones", "cadena de suministro", "pymes",
    "camara de comercio", "comercio", "centro comercial", "mall", "malls",
]

LOW_VALUE_RETAIL_WORDS = [
    "caos", "avalancha", "lesionados", "heridos", "influencer", "viral",
    "regala dinero", "lanzamiento de dinero", "disturbios", "show", "evento no autorizado",
]

COMMERCE_BUSINESS_HINTS = [
    "comercio", "camara de comercio", "pymes", "negocios",
    "abastecimiento", "proveedores", "cadena de suministro",
    "inversion", "adquisicion",
]

MACRO_WORDS = [
    "inflacion", "ipc", "combustibles", "petroleo", "energia", "iva",
    "crecimiento", "recesion", "deuda", "credito", "tasas",
]

STRONG_RETAIL_SIGNAL_THRESHOLD = 2
