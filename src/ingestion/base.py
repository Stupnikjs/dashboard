from typing import Protocol
import pandas as pd

class FetchAdapter(Protocol):
    def fetch(self, symbol: str, start: pd.Timestamp | None) -> pd.DataFrame:
        """Retourne un DataFrame OHLCV indexé par date, ou vide si rien de neuf."""
        ...