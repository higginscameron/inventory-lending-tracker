from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date
import json
from pathlib import Path

app = FastAPI(title="Inventory Lending Tracker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in Sprint 2
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent / "data"
ITEMS_FILE = DATA_DIR / "items.json"
CHECKOUTS_FILE = DATA_DIR / "checkouts.json"

def ensure_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not ITEMS_FILE.exists():
        ITEMS_FILE.write_text("[]", encoding="utf-8")
    if not CHECKOUTS_FILE.exists():
        CHECKOUTS_FILE.write_text("[]", encoding="utf-8")

def read_json(path: Path) -> List[Dict[str, Any]]:
    ensure_files()
    return json.loads(path.read_text(encoding="utf-8") or "[]")

def write_json(path: Path, data: List[Dict[str, Any]]) -> None:
    ensure_files()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def next_id(records: List[Dict[str, Any]]) -> int:
    return max([r.get("id", 0) for r in records], default=0) + 1

class ItemCreate(BaseModel):
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    quantity: int = Field(ge=0)

class Item(ItemCreate):
    id: int

class CheckoutCreate(BaseModel):
    item_id: int
    borrower: str = Field(min_length=1)
    checkout_date: date
    due_date: Optional[date] = None

class CheckoutRecord(BaseModel):
    id: int
    item_id: int
    borrower: str
    checkout_date: str
    due_date: Optional[str] = None
    returned: bool
    return_date: Optional[str] = None

class ReturnRequest(BaseModel):
    checkout_id: int
    return_date: date

@app.get("/api/health")
def health():
    return {"status": "ok", "date": date.today().isoformat()}

@app.get("/api/items", response_model=List[Item])
def get_items():
    return read_json(ITEMS_FILE)

@app.post("/api/items", response_model=Item)
def add_item(payload: ItemCreate):
    items = read_json(ITEMS_FILE)

    # Merge by name+category (optional but nice)
    for it in items:
        if it["name"].strip().lower() == payload.name.strip().lower() and it["category"].strip().lower() == payload.category.strip().lower():
            it["quantity"] += payload.quantity
            write_json(ITEMS_FILE, items)
            return it

    new_item = {
        "id": next_id(items),
        "name": payload.name.strip(),
        "category": payload.category.strip(),
        "quantity": payload.quantity,
    }
    items.append(new_item)
    write_json(ITEMS_FILE, items)
    return new_item

@app.get("/api/checkedout", response_model=List[CheckoutRecord])
def checked_out():
    checkouts = read_json(CHECKOUTS_FILE)
    return [c for c in checkouts if not c.get("returned", False)]

@app.post("/api/checkout", response_model=CheckoutRecord)
def checkout(payload: CheckoutCreate):
    items = read_json(ITEMS_FILE)
    checkouts = read_json(CHECKOUTS_FILE)

    item = next((i for i in items if i["id"] == payload.item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item["quantity"] <= 0:
        raise HTTPException(status_code=400, detail="Item out of stock (quantity is 0)")

    item["quantity"] -= 1

    record = {
        "id": next_id(checkouts),
        "item_id": payload.item_id,
        "borrower": payload.borrower.strip(),
        "checkout_date": payload.checkout_date.isoformat(),
        "due_date": payload.due_date.isoformat() if payload.due_date else None,
        "returned": False,
        "return_date": None,
    }
    checkouts.append(record)

    write_json(ITEMS_FILE, items)
    write_json(CHECKOUTS_FILE, checkouts)
    return record

@app.post("/api/return", response_model=CheckoutRecord)
def return_item(payload: ReturnRequest):
    items = read_json(ITEMS_FILE)
    checkouts = read_json(CHECKOUTS_FILE)

    checkout = next((c for c in checkouts if c["id"] == payload.checkout_id), None)
    if not checkout:
        raise HTTPException(status_code=404, detail="Checkout record not found")
    if checkout.get("returned"):
        raise HTTPException(status_code=400, detail="Item already returned")

    item = next((i for i in items if i["id"] == checkout["item_id"]), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item no longer exists")

    checkout["returned"] = True
    checkout["return_date"] = payload.return_date.isoformat()
    item["quantity"] += 1

    write_json(ITEMS_FILE, items)
    write_json(CHECKOUTS_FILE, checkouts)
    return checkout
