import pandas as pd
from .storage.base import Cache
from .base import FetchAdapter

class Updater:
    def __init__(self, cache: Cache, adapter: FetchAdapter):
        self.cache = cache
        self.adapter = adapter

    def update_symbol(self, symbol: str) -> pd.DataFrame:
        cached = self.cache.load(symbol)

        if cached is not None and not cached.empty:
            start = cached.index.max() + pd.Timedelta(days=1)
            if start.date() > pd.Timestamp.today().date():
                return cached
            new_data = self.adapter.fetch(symbol, start)
            if new_data.empty:
                return cached
            combined = pd.concat([cached, new_data])
            combined = combined[~combined.index.duplicated(keep="last")].sort_index()
        else:
            combined = self.adapter.fetch(symbol, None)

        self.cache.save(symbol, combined)
        return combined

    def update_all(self, watchlist: list[str]) -> dict[str, pd.DataFrame]:
        return {s: self.update_symbol(s) for s in watchlist}