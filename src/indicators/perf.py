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