import json
from pathlib import Path
from typing import List, Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ITEMS_FILE = DATA_DIR / "items.json"
CHECKOUTS_FILE = DATA_DIR / "checkouts.json"

def _ensure_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not ITEMS_FILE.exists():
        ITEMS_FILE.write_text("[]", encoding="utf-8")
    if not CHECKOUTS_FILE.exists():
        CHECKOUTS_FILE.write_text("[]", encoding="utf-8")

def read_items() -> List[Dict[str, Any]]:
    _ensure_files()
    return json.loads(ITEMS_FILE.read_text(encoding="utf-8") or "[]")

def write_items(items: List[Dict[str, Any]]) -> None:
    _ensure_files()
    ITEMS_FILE.write_text(json.dumps(items, indent=2, default=str), encoding="utf-8")

def read_checkouts() -> List[Dict[str, Any]]:
    _ensure_files()
    return json.loads(CHECKOUTS_FILE.read_text(encoding="utf-8") or "[]")

def write_checkouts(checkouts: List[Dict[str, Any]]) -> None:
    _ensure_files()
    CHECKOUTS_FILE.write_text(json.dumps(checkouts, indent=2, default=str), encoding="utf-8")

def next_id(records: List[Dict[str, Any]]) -> int:
    return (max((r.get("id", 0) for r in records), default=0) + 1)
