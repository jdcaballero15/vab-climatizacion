from datetime import date, datetime
from zoneinfo import ZoneInfo

# La empresa trabaja en Argentina: "hoy" es el día de allá, no el del servidor (en UTC).
BUSINESS_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def business_today() -> date:
    return datetime.now(BUSINESS_TZ).date()


def format_date(value: date) -> str:
    """dd/mm/aaaa, como se muestran las fechas en la interfaz."""
    return value.strftime("%d/%m/%Y")
