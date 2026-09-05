"""
src/screener/cli.py

Screener d'opportunités : scanne un univers d'instruments (indépendant de
la watchlist du portefeuille, voir `screener.universe`), liste ceux en
drawdown sur une période donnée, et exporte les lignes retenues dans un
CSV au même format que le CSV d'entrée.

Usage :
    python -m screener.cli -csv instruments.csv -draw-down 40 -period 6month
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import pandas as pd

from core.config import ROOT, DATA_DIR
from core.periods import parse_period
from storage.parquet_cache import ParquetCache
from ingestion.updater import Updater
from ingestion.yfinance_adapter import YFinanceAdapter
from indicators.perf import drawdown, max_drawdown

from .universe import load_universe_csv, COLUMNS

# Cache dédié au screener, séparé de data/ohlcv (watchlist du portefeuille) :
# les instruments scannés ici n'ont rien à voir avec ceux détenus.
CACHE_DIR = ROOT / "data" / "cache_screen"

# Extrait (nombre, unité) d'une période style '6month'/'6m'/'1year' pour
# construire un nom de fichier abrégé (ex: '6month' -> '6m').
_PERIOD_PATTERN = re.compile(r"^(\d+)\s*([a-zA-Z]+)$")


def _abbreviate_period(period: str) -> str:
    s = period.strip().lower().rstrip("s")
    m = _PERIOD_PATTERN.match(s)
    if not m:
        return period
    n, unit = m.group(1), m.group(2)
    return f"{n}{unit[0]}"


def _default_out_path(threshold: float, period: str) -> str:
    threshold_str = str(int(threshold)) if threshold.is_integer() else str(threshold).replace(".", "_")
    return f"down{threshold_str}over{_abbreviate_period(period)}.csv"


# Anti rate-limit Yahoo : un scan complet interroge potentiellement des
# centaines de tickers d'affilée, ce qui déclenche des échecs en cascade
_REQUEST_DELAY_S = 0.3

_TRAILING_DIGIT = re.compile(r"\d+$")


def _strip_disambiguation_digit(ticker: str) -> str:
    base, sep, suffix = ticker.rpartition(".")
    if not sep:
        base, suffix = ticker, ""
    stripped_base = _TRAILING_DIGIT.sub("", base)
    return f"{stripped_base}.{suffix}" if sep else stripped_base


def _fetch_with_fallback(updater: Updater, yahoo_ticker: str):
    df = updater.update_symbol(yahoo_ticker)
    if df is not None and not df.empty:
        return df

    stripped = _strip_disambiguation_digit(yahoo_ticker)
    if stripped != yahoo_ticker:
        time.sleep(_REQUEST_DELAY_S)
        return updater.update_symbol(stripped)

    return df


def _screen(csv_path: str, threshold: float, period: str) -> tuple[list[dict], pd.DataFrame]:
    """Retourne (lignes pour l'affichage console, sous-DataFrame de l'univers
    d'origine -- mêmes colonnes que le CSV d'entrée -- pour les instruments
    retenus)."""
    universe = load_universe_csv(Path(DATA_DIR, csv_path))
    updater = Updater(ParquetCache(CACHE_DIR), YFinanceAdapter())
    cutoff = pd.Timestamp.today().normalize() - parse_period(period)

    display_rows = []
    matched_index = []

    for row in universe.itertuples():
        df = _fetch_with_fallback(updater, row.yahoo_ticker)
        time.sleep(_REQUEST_DELAY_S)
        if df is None or df.empty:
            continue

        df_period = df[df.index >= cutoff]
        if df_period.empty:
            continue

        # On supprime les lignes où le prix de clôture est manquant
        df_period = df_period.dropna(subset=["close"])
        if df_period.empty:
            continue
        
        current_dd = float(drawdown(df_period).iloc[-1])
        if abs(current_dd) < threshold:
            continue

        display_rows.append({
            "ticker": row.yahoo_ticker,
            "label": row.label,
            "current_drawdown": current_dd,
            "max_drawdown": max_drawdown(df_period),
        })
        matched_index.append(row.Index)

    display_rows.sort(key=lambda r: r["current_drawdown"])  # pire en premier
    matched_df = universe.loc[matched_index, COLUMNS]
    return display_rows, matched_df


def build_parser() -> argparse.ArgumentParser:
    """Construit le parser d'arguments CLI."""
    parser = argparse.ArgumentParser(
        description="Screener d'opportunités en drawdown sur un univers d'instruments.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "-csv", 
        dest="csv_path",
        required=True,
        help="Chemin du fichier CSV de l'univers d'instruments à scanner (ex: instruments.csv)."
    )
    
    parser.add_argument(
        "-draw-down", 
        dest="draw_down",
        type=float,
        default=20.0,
        help="Seuil de drawdown minimum en pourcentage (ex: 40 pour -40%%)."
    )
    
    parser.add_argument(
        "-period", 
        type=str,
        default="6month",
        help="Période d'évaluation du drawdown (ex: '6month', '1y', '52week')."
    )
    
    parser.add_argument(
        "-out", 
        dest="out_path",
        type=str,
        default=None,
        help="Chemin du fichier CSV de sortie. Si non spécifié, généré automatiquement."
    )
    
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    threshold = args.draw_down
    period = args.period
    out_path = args.out_path or _default_out_path(threshold, period)

    display_rows, matched_df = _screen(args.csv_path, threshold, period)

    if not display_rows:
        print(f"Aucun instrument avec un drawdown >= {threshold:.1f}% sur {period}.")
        return

    print(f"\n=== OPPORTUNITÉS EN DRAWDOWN (>= {threshold:.1f}%, période {period}) ===")
    print(f"{'Ticker':<10} {'Label':<25} {'Drawdown courant':>18} {'Pire drawdown':>16}")
    for r in display_rows:
        print(f"{r['ticker']:<10} {r['label']:<25} {r['current_drawdown']:>17.2f}% {r['max_drawdown']:>15.2f}%")

    matched_df.to_csv(out_path, header=False, index=False)
    print(f"\n{len(matched_df)} ligne(s) exportée(s) vers {out_path}")


if __name__ == "__main__":
    main()