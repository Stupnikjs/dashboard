import logging
import pandas as pd
from storage.base import Cache
from .base import FetchAdapter

logger = logging.getLogger(__name__)

class Updater:
    def __init__(self, cache: Cache, adapter: FetchAdapter):
        self.cache = cache
        self.adapter = adapter

    def update_symbol(self, symbol: str) -> pd.DataFrame | None:
        cached = self.cache.load(symbol)

        try:
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
                if combined.empty:
                    logger.warning("Aucune donnée récupérée pour %s (ticker invalide ?)", symbol)
                    return None
        except Exception:
            logger.exception("Échec de mise à jour pour %s, cache existant conservé", symbol)
            return cached  # dégrade gracieusement plutôt que de planter tout le batch

        self.cache.save(symbol, combined)
        return combined

    def update_all(self, tickers: list[str]) -> dict[str, pd.DataFrame | None]:
        return {t: self.update_symbol(t) for t in tickers}