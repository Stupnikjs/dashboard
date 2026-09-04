from __future__ import annotations

import math
import time
from dataclasses import dataclass

import yfinance as yf


def _number(value) -> float | None:
    if value is None:
        return None

    try:
        value = float(value)
        if not math.isfinite(value):
            return None
        return value
    except (TypeError, ValueError):
        return None


def _score_range(
    value: float | None,
    thresholds: list[tuple[float, float]],
    default: float = 0,
) -> float:
    if value is None:
        return default

    for minimum, points in thresholds:
        if value >= minimum:
            return points

    return 0


def _debt_score(debt_to_ebitda: float | None) -> float:
    if debt_to_ebitda is None:
        return 0
    if debt_to_ebitda < 1:
        return 25
    if debt_to_ebitda < 1.5:
        return 23
    if debt_to_ebitda < 2:
        return 20
    if debt_to_ebitda < 3:
        return 15
    if debt_to_ebitda < 4:
        return 8
    if debt_to_ebitda < 6:
        return 3
    return 0


def _liquidity_score(current_ratio: float | None,
                     quick_ratio: float | None) -> float:
    score = 0

    if current_ratio is not None:
        if current_ratio >= 2:
            score += 7
        elif current_ratio >= 1.5:
            score += 6
        elif current_ratio >= 1.2:
            score += 4
        elif current_ratio >= 1:
            score += 2

    if quick_ratio is not None:
        if quick_ratio >= 1.5:
            score += 5
        elif quick_ratio >= 1:
            score += 4
        elif quick_ratio >= 0.7:
            score += 2

    return min(score, 12)


def _quality_score(info: dict) -> float:
    score = 0

    roe = _number(info.get("returnOnEquity"))
    roa = _number(info.get("returnOnAssets"))
    margin = _number(info.get("profitMargins"))
    operating_margin = _number(info.get("operatingMargins"))

    if roe is not None:
        if roe >= 0.25:
            score += 6
        elif roe >= 0.15:
            score += 5
        elif roe >= 0.10:
            score += 3
        elif roe > 0:
            score += 1

    if roa is not None:
        if roa >= 0.10:
            score += 5
        elif roa >= 0.05:
            score += 4
        elif roa > 0:
            score += 2

    if margin is not None:
        if margin >= 0.20:
            score += 5
        elif margin >= 0.10:
            score += 4
        elif margin > 0:
            score += 2

    if operating_margin is not None:
        if operating_margin >= 0.20:
            score += 5
        elif operating_margin >= 0.10:
            score += 4
        elif operating_margin > 0:
            score += 2

    return min(score, 20)


def _cashflow_score(info: dict) -> float:
    score = 0

    fcf = _number(info.get("freeCashflow"))
    ocf = _number(info.get("operatingCashflow"))
    revenue_growth = _number(info.get("revenueGrowth"))
    earnings_growth = _number(info.get("earningsGrowth"))

    if fcf is not None and fcf > 0:
        score += 7

    if ocf is not None and ocf > 0:
        score += 5

    if revenue_growth is not None:
        if revenue_growth > 0.05:
            score += 4
        elif revenue_growth > 0:
            score += 3
        elif revenue_growth > -0.05:
            score += 1

    if earnings_growth is not None:
        if earnings_growth > 0.05:
            score += 4
        elif earnings_growth > 0:
            score += 3
        elif earnings_growth > -0.05:
            score += 1

    return min(score, 20)


def _valuation_score(info: dict) -> float:
    """
    Score volontairement simple.

    On préfère le forward PE / PE et EV/EBITDA.
    Les multiples manquants ne pénalisent pas excessivement.
    """
    score = 0

    forward_pe = _number(info.get("forwardPE"))
    trailing_pe = _number(info.get("trailingPE"))
    ev_ebitda = _number(info.get("enterpriseToEbitda"))

    if forward_pe is not None and forward_pe > 0:
        if forward_pe < 10:
            score += 12
        elif forward_pe < 15:
            score += 9
        elif forward_pe < 20:
            score += 6
        elif forward_pe < 30:
            score += 3

    if trailing_pe is not None and trailing_pe > 0:
        if trailing_pe < 10:
            score += 8
        elif trailing_pe < 15:
            score += 6
        elif trailing_pe < 20:
            score += 4
        elif trailing_pe < 30:
            score += 2

    if ev_ebitda is not None and ev_ebitda > 0:
        if ev_ebitda < 8:
            score += 10
        elif ev_ebitda < 12:
            score += 8
        elif ev_ebitda < 16:
            score += 5
        elif ev_ebitda < 22:
            score += 2

    return min(score, 30)


def _drop_score(info: dict) -> float:
    """
    V1 : utilise la distance au plus haut 52 semaines.

    max = 20 points pour une baisse >= 50 %.
    """
    current = _number(info.get("currentPrice"))
    high_52 = _number(info.get("fiftyTwoWeekHigh"))

    if current is None or high_52 is None or high_52 <= 0:
        return 0

    drop = 1 - current / high_52

    if drop >= 0.50:
        return 20
    if drop >= 0.40:
        return 16
    if drop >= 0.30:
        return 12
    if drop >= 0.20:
        return 8
    if drop >= 0.10:
        return 4

    return 0


def _deterioration_penalty(info: dict) -> float:
    penalty = 0

    revenue_growth = _number(info.get("revenueGrowth"))
    earnings_growth = _number(info.get("earningsGrowth"))

    if revenue_growth is not None:
        if revenue_growth < -0.20:
            penalty += 8
        elif revenue_growth < -0.10:
            penalty += 5

    if earnings_growth is not None:
        if earnings_growth < -0.30:
            penalty += 8
        elif earnings_growth < -0.15:
            penalty += 5

    return min(penalty, 15)


def calculate_watch_score(info: dict) -> dict:
    debt = _number(info.get("totalDebt"))
    ebitda = _number(info.get("ebitda"))

    debt_to_ebitda = None
    if debt is not None and ebitda is not None and ebitda > 0:
        debt_to_ebitda = debt / ebitda

    valuation = _valuation_score(info)
    drop = _drop_score(info)
    balance = _debt_score(debt_to_ebitda)
    balance += _liquidity_score(
        _number(info.get("currentRatio")),
        _number(info.get("quickRatio")),
    )

    quality = _quality_score(info)
    cashflow = _cashflow_score(info)
    penalty = _deterioration_penalty(info)

    score = valuation + drop + balance + quality + cashflow - penalty

    return {
        "watch_score": round(max(0, min(100, score)), 1),
        "drop_score": round(drop, 1),
        "valuation_score": round(valuation, 1),
        "balance_score": round(balance, 1),
        "quality_score": round(quality, 1),
        "cashflow_score": round(cashflow, 1),
        "deterioration_penalty": round(penalty, 1),
        "debt_to_ebitda": (
            round(debt_to_ebitda, 2)
            if debt_to_ebitda is not None
            else None
        ),
    }


def fetch_info(symbol: str) -> dict:
    return yf.Ticker(symbol).info


def screen_tickers(
    tickers: list[str],
    delay: float = 0.0,
) -> list[dict]:
    results = []

    for symbol in tickers:
        try:
            info = fetch_info(symbol)
            score = calculate_watch_score(info)

            results.append({
                "ticker": symbol,
                "name": info.get("shortName") or info.get("longName"),
                **score,
                "price": _number(
                    info.get("currentPrice")
                    or info.get("regularMarketPrice")
                ),
                "pe": _number(info.get("trailingPE")),
                "forward_pe": _number(info.get("forwardPE")),
                "ev_ebitda": _number(info.get("enterpriseToEbitda")),
                "roe": _number(info.get("returnOnEquity")),
                "roa": _number(info.get("returnOnAssets")),
                "current_ratio": _number(info.get("currentRatio")),
                "quick_ratio": _number(info.get("quickRatio")),
                "fcf": _number(info.get("freeCashflow")),
                "revenue_growth": _number(info.get("revenueGrowth")),
                "earnings_growth": _number(info.get("earningsGrowth")),
            })

        except Exception as exc:
            results.append({
                "ticker": symbol,
                "name": None,
                "watch_score": None,
                "error": str(exc),
            })

        if delay:
            time.sleep(delay)

    return sorted(
        results,
        key=lambda x: x.get("watch_score") or -1,
        reverse=True,
    )