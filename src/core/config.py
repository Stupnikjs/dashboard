from pathlib import Path
from dataclasses import dataclass
import json

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "ohlcv"
WATCHLIST_PATH = ROOT / "watchlist.json"

@dataclass(frozen=True)
class WatchlistEntry:
    ticker: str
    label: str | None = None
    asset_class: str | None = None

def load_watchlist() -> list[WatchlistEntry]:
    raw = json.loads(WATCHLIST_PATH.read_text())
    return [WatchlistEntry(**entry) for entry in raw["watchlist"]]