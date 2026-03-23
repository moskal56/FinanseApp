from datetime import datetime


def parse_amount(raw: str) -> float:
    value = float(raw.replace(",", "."))
    if value < 0:
        raise ValueError("Kwota nie może być ujemna.")
    return round(value, 2)


def validate_date(raw: str) -> str:
    datetime.strptime(raw, "%Y-%m-%d")
    return raw
