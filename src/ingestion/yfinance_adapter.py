import yfinance as yf
import pandas as pd
from .base import FetchAdapter

class YFinanceAdapter(FetchAdapter):
    def fetch(self, symbol: str, start: pd.Timestamp | None) -> pd.DataFrame:
        kwargs = {"interval": "1d"}
        kwargs["start"] = start.strftime("%Y-%m-%d") if start else None
        if start is None:
            kwargs["period"] = "max"
            kwargs.pop("start")

        df = yf.Ticker(symbol).history(**kwargs)
        if df.empty:
            return df

        df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
        df.index.name = "date"
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df