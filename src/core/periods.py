import re
import pandas as pd

_SHORT = {"d": "day", "w": "week", "m": "month", "y": "year"}
_PATTERN = re.compile(r"^(\d+)\s*([a-zA-Z]+)$")

def parse_period(period: str) -> pd.DateOffset:
    """
    Convertit une chaîne en pd.DateOffset.
    Exemples acceptés : '6month', '6m', '1year', '1y', '52week', '3d', '90day'
    """
    if not period:
        raise ValueError("Période vide")
    s = period.strip().lower().rstrip("s")  # tolère le pluriel

    m = _PATTERN.match(s)
    if not m:
        raise ValueError(
            f"Période invalide : {period!r}. "
            "Exemples valides : '6month', '6m', '1year', '52week', '3d'"
        )
    n = int(m.group(1))
    unit_raw = m.group(2)
    unit = _SHORT.get(unit_raw, unit_raw)

    mapping = {
        "day": "days",
        "week": "weeks",
        "month": "months",
        "year": "years",
    }
    if unit not in mapping:
        raise ValueError(f"Unité inconnue : {unit_raw!r}")

    return pd.DateOffset(**{mapping[unit]: n})