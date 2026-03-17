# utils.py
import re
from datetime import datetime


def normalizar_fecha(fecha_str: str) -> str:
    """
    Normaliza diferentes formatos de fecha a DD/MM/YYYY
    
    Formatos soportados:
    - "Martes 10 Febrero, 2026 | 16:25" → "10/02/2026"
    - "2026-02-10 00:00:00" → "10/02/2026"
    - "10/02/2026" → "10/02/2026" (ya normalizado)
    - "Feb. 10 2026" → "10/02/2026"
    """
    fecha_str = fecha_str.strip()
    
    # Mapeo de meses en español
    meses = {
        "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
        "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
        "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12",
        "ene": "01", "feb": "02", "mar": "03", "abr": "04",
        "may": "05", "jun": "06", "jul": "07", "ago": "08",
        "sep": "09", "oct": "10", "nov": "11", "dic": "12",
    }
    
    # Caso 1: Formato SQL "2026-02-10 00:00:00" o "2026-02-10"
    sql_match = re.match(r'(\d{4})-(\d{2})-(\d{2})', fecha_str)
    if sql_match:
        year, month, day = sql_match.groups()
        return f"{day}/{month}/{year}"
    
    # Caso 2: "Martes 10 Febrero, 2026 | 16:25" (BioBio)
    # Patrón: día_semana DIA MES, AÑO | HORA
    biobio_match = re.search(r'\b(\d{1,2})\s+(\w+),?\s+(\d{4})', fecha_str)
    if biobio_match:
        day, month_str, year = biobio_match.groups()
        month = meses.get(month_str.lower(), "01")
        return f"{day.zfill(2)}/{month}/{year}"
    
    # Caso 3: Ya está en formato DD/MM/YYYY
    if re.match(r'\d{2}/\d{2}/\d{4}', fecha_str):
        return fecha_str
    
    # Caso 4: Fallback - intentar parsear con datetime
    try:
        # Intenta varios formatos comunes
        for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
            try:
                dt = datetime.strptime(fecha_str, fmt)
                return dt.strftime("%d/%m/%Y")
            except ValueError:
                continue
    except:
        pass
    
    return fecha_str