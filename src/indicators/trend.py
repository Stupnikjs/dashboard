import pandas as pd

def sma(df: pd.DataFrame, window: int, column: str = "close") -> pd.Series:
    return df[column].rolling(window=window).mean()

def ema(df: pd.DataFrame, window: int, column: str = "close") -> pd.Series:
    return df[column].ewm(span=window, adjust=False).mean()

def bollinger_bands(df: pd.DataFrame, window: int = 20, num_std: float = 2, column: str = "close"):
    mid = sma(df, window, column)
    std = df[column].rolling(window=window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower