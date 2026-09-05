"""
src/screener/universe.py

Univers d'instruments à scanner pour repérer des opportunités --
totalement indépendant de la watchlist (`core.config.load_watchlist`),
qui elle sert au suivi de ce qui est déjà en portefeuille.

Charge un export CSV type XTB listant tous les instruments tradables
(pas seulement ceux détenus).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# Colonnes de l'export CSV XTB, sans en-tête. C'est aussi l'ordre de colonnes
# utilisé pour réexporter un sous-ensemble de lignes dans le même format.
COLUMNS = [
    "ticker", "label", "currency", "min_lot", "unused",
    "margin_1", "margin_2", "hours", "days", "asset_class",
]

# Suffixes XTB (place de cotation encodée dans le ticker) -> Yahoo Finance.
# Ex : 'CPRI.US' -> 'CPRI', 'HSBA.UK' -> 'HSBA.L'.
_XTB_TO_YAHOO_SUFFIX = {
    ".US": "",
    ".UK": ".L",
    ".FR": ".PA",
    ".DE": ".DE",
    ".NL": ".AS",
    ".IT": ".MI",
    ".ES": ".MC",
    ".PT": ".LS",
    ".BE": ".BR",
    ".CH": ".SW",
    ".DK": ".CO",
    ".NO": ".OL",
    ".SE": ".ST",
    ".FI": ".HE",
    ".PL": ".WA",
}


def _xtb_ticker_to_yahoo(ticker: str) -> str:
    if ticker in _TICKER_OVERRIDES:
        return _TICKER_OVERRIDES[ticker]
    for xtb_suffix, yahoo_suffix in _XTB_TO_YAHOO_SUFFIX.items():
        if ticker.endswith(xtb_suffix):
            return ticker[: -len(xtb_suffix)] + yahoo_suffix
    return ticker


# Tickers pour lesquels la substitution de suffixe générique ne suffit pas :
# - Nordique (.ST/.CO/.OL) : Yahoo exige un tiret avant la lettre de classe
#   d'action (ex: 'ERIC-B.ST'), que XTB n'utilise pas ('ERICB.SE').
# - US : quelques cas où le ticker Yahoo réel diffère du ticker XTB pour
#   d'autres raisons (classe d'action, notation CFD).
# Liste non-exhaustive, à compléter au fil des exécutions.
_TICKER_OVERRIDES = {
    "ERICB.SE": "ERIC-B.ST",
    "ASSAB.SE": "ASSA-B.ST",
    "ATCOA.SE": "ATCO-A.ST",
    "ATCOB.SE": "ATCO-B.ST",
    "BETSB.SE": "BETS-B.ST",
    "CARLB.DK": "CARL-B.CO",
    "COLOB.DK": "COLO-B.CO",
    "ELUXB.SE": "ELUX-B.ST",
    "FINGB.SE": "FING-B.ST",
    "GETIB.SE": "GETI-B.ST",
    "HOLMB.SE": "HOLM-B.ST",
    "HUSQB.SE": "HUSQ-B.ST",
    "INDUA.SE": "INDU-A.ST",
    "INVEB.SE": "INVE-B.ST",
    "KINVB.SE": "KINV-B.ST",
    "HMB.SE": "HM-B.ST",
    "ESSITYB.SE": "ESSITY-B.ST",
    "ALKB.DK": "ALK-B.CO",
    "GOOGC.US": "GOOG",
    "BFB.US": "BF-B",
    "BRKB.US": "BRK-B",
}


def load_universe_csv(path: Path, asset_class: str = "Stock") -> pd.DataFrame:
    """
    Charge l'univers depuis un export CSV type XTB, sans en-tête :
    ticker,nom,devise,lot_min,?,marge1,marge2,horaires,jours,type

    Exemple de ligne :
    CPRI.US,Capri Holdings Ltd,USD,50,0,0.30%,0.50%,15:30 - 22:00,Mon - Fri,Stock

    - Ne garde que les lignes dont le type == `asset_class` (défaut "Stock").
    - Ignore les instruments "CLOSE ONLY" (ticker suffixé '*' : encore
      listés par XTB mais impossible d'y ouvrir une nouvelle position).
    - Ajoute une colonne `yahoo_ticker` (conversion du ticker XTB, seul
      format que yfinance sait résoudre) sans toucher à `ticker`, qui reste
      la valeur XTB d'origine -- nécessaire pour pouvoir réexporter les
      lignes retenues dans le même format que le CSV d'entrée.
    """
    df = pd.read_csv(path, header=None, names=COLUMNS)

    df = df[df["asset_class"] == asset_class]
    df = df[~df["ticker"].str.endswith("*") & ~df["label"].str.contains("CLOSE ONLY", na=False)]
    df = df.copy()
    df["yahoo_ticker"] = df["ticker"].map(_xtb_ticker_to_yahoo)

    return df