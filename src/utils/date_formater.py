import re
from datetime import date, datetime


_MESES: dict[str, int] = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4,
    "may": 5, "jun": 6, "jul": 7, "ago": 8,
    "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}


def normalizar_fecha(fecha_str: str | None) -> date | None:
    """Parsea cualquier formato de fecha scrapeado y retorna un objeto date. Retorna None si no parsea."""
    if not fecha_str:
        return None
    s = fecha_str.strip()

    # ISO: "2026-02-10", "2026-02-10T16:25:00+00:00", "2026-02-10 16:25:00"
    iso = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            pass

    # DD/MM/YYYY
    dmy_slash = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if dmy_slash:
        try:
            return date(int(dmy_slash.group(3)), int(dmy_slash.group(2)), int(dmy_slash.group(1)))
        except ValueError:
            pass

    # DD-MM-YYYY
    dmy_dash = re.match(r"^(\d{2})-(\d{2})-(\d{4})$", s)
    if dmy_dash:
        try:
            return date(int(dmy_dash.group(3)), int(dmy_dash.group(2)), int(dmy_dash.group(1)))
        except ValueError:
            pass

    # "Martes 10 Febrero, 2026 | 16:25" or "10 Febrero 2026"
    biobio = re.search(r"\b(\d{1,2})\s+(\w+),?\s+(\d{4})", s)
    if biobio:
        month = _MESES.get(biobio.group(2).lower())
        if month:
            try:
                return date(int(biobio.group(3)), month, int(biobio.group(1)))
            except ValueError:
                pass

    # "Abr 17" or "May 04" — mes abreviado + día sin año (Meganoticias)
    month_day = re.match(r"^([A-Za-záéíóúÁÉÍÓÚ]{3,4})\s+(\d{1,2})$", s)
    if month_day:
        month = _MESES.get(month_day.group(1).lower())
        if month:
            try:
                return date(datetime.now().year, month, int(month_day.group(2)))
            except ValueError:
                pass

    return None
