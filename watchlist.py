import json
from pathlib import Path

_WATCHLIST_PATH = Path(__file__).parent / ".watchlist.json"


def load_watchlist() -> list[str]:
    if not _WATCHLIST_PATH.exists():
        return []
    try:
        return json.loads(_WATCHLIST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_watchlist(zips: list[str]) -> None:
    _WATCHLIST_PATH.write_text(json.dumps(zips, indent=2), encoding="utf-8")


def add_zip(zip_code: str) -> None:
    wl = load_watchlist()
    if zip_code not in wl:
        wl.append(zip_code)
        save_watchlist(wl)


def remove_zip(zip_code: str) -> None:
    save_watchlist([z for z in load_watchlist() if z != zip_code])
