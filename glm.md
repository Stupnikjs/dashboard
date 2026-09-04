# Filtre de Drawdown — Implémentation

Voici les nouveaux fichiers à créer et les modifications à apporter.

---

## 1. Nouveau fichier : `indicators/performance.py`

```python
# indicators/performance.py
import pandas as pd

def drawdown(df: pd.DataFrame, column: str = "close") -> pd.Series:
    """
    Série de drawdown en % (valeurs négatives ou nulles).
    drawdown(t) = (price(t) - running_max(t)) / running_max(t) * 100
    """
    price = df[column]
    running_max = price.cummax()
    return (price - running_max) / running_max * 100

def max_drawdown(df: pd.DataFrame, column: str = "close") -> float:
    """Drawdown maximum sur la période du DataFrame (en %, négatif)."""
    if df.empty:
        return 0.0
    return float(drawdown(df, column).min())
```

---

## 2. Nouveau fichier : `core/periods.py`

```python
# core/periods.py
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
```

---

## 3. Nouveau fichier : `core/filter_parser.py`

```python
# core/filter_parser.py
import shlex

def parse_filter_args(filter_str: str) -> dict:
    """
    Parse une chaîne de filtre style CLI.

    Exemple : '-draw-down 40 -period 6month -direction min'
    → {'draw_down': '40', 'period': '6month', 'direction': 'min'}

    Flags booléens (sans valeur) sont aussi supportés : '-rsi' → {'rsi': True}
    """
    s = filter_str.strip()
    if not s:
        return {}
    tokens = shlex.split(s)
    result: dict = {}
    i = 0
    while i < len(tokens):
        key = tokens[i].lstrip("-").replace("-", "_")
        if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
            result[key] = tokens[i + 1]
            i += 2
        else:
            result[key] = True
            i += 1
    return result
```

---

## 4. Nouveau fichier : `core/filters.py`

```python
# core/filters.py
import logging
import pandas as pd
from indicators.performance import drawdown
from .periods import parse_period

logger = logging.getLogger(__name__)

def filter_by_drawdown(
    data: dict[str, pd.DataFrame | None],
    threshold_pct: float,
    period: pd.DateOffset | str,
    direction: str = "min",
) -> list[str]:
    """
    Filtre les tickers selon leur drawdown maximum sur la période donnée.

    Paramètres
    ----------
    data : dict ticker → DataFrame (ou None)
    threshold_pct : float
        Seuil en % (ex : 40 pour 40 %).
    period : pd.DateOffset ou str
        Fenêtre de temps ('6month', '1year', ...).
    direction : str
        'min'  → conserve les actifs dont |drawdown| >= threshold
                 (ex : actions qui ont chuté d'au moins 40 %)
        'max'  → conserve les actifs dont |drawdown| <= threshold
                 (ex : actions qui n'ont pas baissé plus de 40 %)

    Retourne
    --------
    Liste des tickers conservés.
    """
    if isinstance(period, str):
        period = parse_period(period)

    today = pd.Timestamp.today().normalize()
    cutoff = today - period

    kept: list[str] = []
    for ticker, df in data.items():
        if df is None or df.empty:
            continue
        window = df.loc[df.index >= cutoff]
        if window.empty:
            continue
        mdd = abs(float(drawdown(window).min()))

        if direction == "min" and mdd >= threshold_pct:
            kept.append(ticker)
        elif direction == "max" and mdd <= threshold_pct:
            kept.append(ticker)

    logger.info(
        "Filtre drawdown %s %.1f%% sur %s → %d/%d tickers conservés",
        direction, threshold_pct, period, len(kept), len(data),
    )
    return kept
```

---

## 5. Fichier modifié : `app/streamlit_app.py`

```python
# app/streamlit_app.py

import streamlit as st
import pandas as pd
from core.config import DATA_DIR, load_watchlist
from core.filters import filter_by_drawdown
from core.filter_parser import parse_filter_args
from storage.parquet_cache import ParquetCache
from ingestion.yfinance_adapter import YFinanceAdapter
from ingestion.updater import Updater
from visualize.charts import build_chart, resample_weekly

def main():
    st.set_page_config(layout="wide")
    st.title("Dashboard financier")

    # ------------------------------------------------------------------
    # Sidebar : indicateurs + filtre
    # ------------------------------------------------------------------
    with st.sidebar:
        st.header("Indicateurs")
        show_sma = st.multiselect("SMA (semaines)", [10, 20, 50], default=[20])
        show_bollinger = st.checkbox("Bandes de Bollinger", value=False)
        show_rsi = st.checkbox("RSI", value=False)

        st.divider()
        st.header("Filtre de watchlist")
        st.caption(
            "Syntaxe style CLI, par exemple :\n\n"
            "`-draw-down 40 -period 6month`\n\n"
            "`-draw-down 25 -period 1y -direction max`"
        )
        filter_str = st.text_input(
            "Filtre",
            value="",
            placeholder="-draw-down 40 -period 6month",
        )

    # ------------------------------------------------------------------
    # Chargement des données
    # ------------------------------------------------------------------
    watchlist = load_watchlist()
    tickers = [entry.ticker for entry in watchlist]
    updater = Updater(ParquetCache(DATA_DIR), YFinanceAdapter())

    @st.cache_data(ttl=3600)
    def get_data():
        return updater.update_all(tickers)

    if st.button("🔄 Forcer le refresh"):
        get_data.clear()

    data = get_data()

    # ------------------------------------------------------------------
    # Application du filtre
    # ------------------------------------------------------------------
    filtered_entries = watchlist
    if filter_str.strip():
        params = parse_filter_args(filter_str)
        if "draw_down" in params and "period" in params:
            try:
                threshold = float(params["draw_down"])
                direction = str(params.get("direction", "min"))
                kept = filter_by_drawdown(
                    data, threshold, params["period"], direction
                )
                filtered_entries = [e for e in watchlist if e.ticker in kept]
                st.info(
                    f"Filtre : drawdown {direction} {threshold}% "
                    f"sur {params['period']} → {len(filtered_entries)} actif(s)"
                )
            except (ValueError, TypeError) as exc:
                st.error(f"Filtre invalide : {exc}")
        else:
            st.warning(
                "Le filtre nécessite au moins "
                "`-draw-down <pct>` et `-period <durée>`."
            )

    if not filtered_entries:
        st.warning("Aucun actif ne correspond au filtre.")
        return

    # ------------------------------------------------------------------
    # Navigation entre les actifs filtrés
    # ------------------------------------------------------------------
    if "page_idx" not in st.session_state:
        st.session_state.page_idx = 0

    # sécurité si l'index dépasse après filtrage
    if st.session_state.page_idx >= len(filtered_entries):
        st.session_state.page_idx = 0

    labels = [entry.label or entry.ticker for entry in filtered_entries]

    col_prev, col_select, col_next = st.columns([1, 6, 1])
    with col_prev:
        if st.button("◀", use_container_width=True):
            st.session_state.page_idx = (
                st.session_state.page_idx - 1
            ) % len(filtered_entries)
    with col_select:
        st.session_state.page_idx = st.selectbox(
            "Actif",
            range(len(filtered_entries)),
            index=st.session_state.page_idx,
            format_func=lambda i: labels[i],
            label_visibility="collapsed",
        )
    with col_next:
        if st.button("▶", use_container_width=True):
            st.session_state.page_idx = (
                st.session_state.page_idx + 1
            ) % len(filtered_entries)

    entry = filtered_entries[st.session_state.page_idx]
    df = data[entry.ticker]

    if df is None:
        st.error(f"{entry.ticker} : échec de récupération")
        return

    weekly_df = resample_weekly(df)
    fig = build_chart(
        weekly_df,
        entry.label or entry.ticker,
        show_sma=show_sma,
        show_bollinger=show_bollinger,
        show_rsi=show_rsi,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Dernière donnée : {df.index.max().date()}")


if __name__ == "__main__":
    main()
```

---

## Résumé de l'architecture

```
src/
├── core/
│   ├── config.py          (existant)
│   ├── periods.py         ← NOUVEAU : parse '6month' → pd.DateOffset
│   ├── filter_parser.py   ← NOUVEAU : parse '-draw-down 40 -period 6month'
│   └── filters.py         ← NOUVEAU : filter_by_drawdown()
├── indicators/
│   ├── trend.py           (existant)
│   ├── momentum.py        (existant)
│   └── performance.py     ← NOUVEAU : drawdown(), max_drawdown()
├── app/
│   └── streamlit_app.py   ← MODIFIÉ : sidebar avec champ de filtre
└── ...
```

## Utilisation

| Syntaxe dans le champ Streamlit | Effet |
|---|---|
| `-draw-down 40 -period 6month` | Actifs ayant chuté d'**au moins 40 %** sur 6 mois |
| `-draw-down 40 -period 6month -direction max` | Actifs n'ayant **pas baissé plus de 40 %** sur 6 mois |
| `-draw-down 20 -period 1y` | Au moins 20 % de drawdown sur 1 an |
| `-draw-down 15 -period 52w` | Au moins 15 % de drawdown sur 52 semaines |

Le `parse_period` accepte les formes courtes (`6m`, `1y`, `52w`, `3d`) et le pluriel (`6months`). Le filtre s'applique **avant** la navigation : seuls les actifs correspondants apparaissent dans le sélecteur.