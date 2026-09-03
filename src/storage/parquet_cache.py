from pathlib import Path
import pandas as pd
from .base import Cache

class ParquetCache(Cache):
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def _path(self, symbol: str) -> Path:
        return self.data_dir / f"{symbol}.parquet"

    def load(self, symbol: str) -> pd.DataFrame | None:
        path = self._path(symbol)
        return pd.read_parquet(path) if path.exists() else None

    def save(self, symbol: str, df: pd.DataFrame) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        df.to_parquet(self._path(symbol))