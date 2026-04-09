from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import date
from typing import List

# Sign On Stuff:
# cd C:\Users\camer\OneDrive\Documents\4250dummyproject\4250-Semester-Project\4250-Semester-Project\backend
# python -m uvicorn app.main:app --reload
# http://127.0.0.1:8000/
# http://127.0.0.1:8000/docs

from .models import ItemCreate, Item, CheckoutCreate, CheckoutRecord, ReturnRequest
from .storage import read_items, write_items, read_checkouts, write_checkouts, next_id

app = FastAPI(title="Inventory Lending Tracker API", version="1.0.0")

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """
    Return the HTML template for the homepage.

    Parameters
    ----------
    request : Request
        The request object to pass to the template.

    Returns
    -------
    HTMLResponse
        The HTML response containing the rendered template.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/items", response_model=List[Item])
def get_items():
    return read_items()


@app.post("/api/items", response_model=Item)
def add_item(payload: ItemCreate):
    items = read_items()

    for it in items:
        if (
            it["name"].strip().lower() == payload.name.strip().lower() and it["category"].strip().lower() == payload.category.strip().lower()
        ):
            it["quantity"] += payload.quantity
            write_items(items)
            return it

    new_item = {
        "id": next_id(items),
        "name": payload.name.strip(),
        "category": payload.category.strip(),
        "quantity": payload.quantity,
    }
    items.append(new_item)
    write_items(items)
    return new_item


@app.get("/api/checkedout", response_model=List[CheckoutRecord])
def get_checked_out():
    checkouts = read_checkouts()
    return [c for c in checkouts if not c.get("returned", False)]


@app.post("/api/checkout", response_model=CheckoutRecord)
def checkout_item(payload: CheckoutCreate):
    items = read_items()
    checkouts = read_checkouts()

    item = next((i for i in items if i["id"] == payload.item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item["quantity"] <= 0:
        raise HTTPException(status_code=400, detail="Item is out of stock (quantity is 0)")

    item["quantity"] -= 1

    new_checkout = {
        "id": next_id(checkouts),
        "item_id": payload.item_id,
        "borrower": payload.borrower.strip(),
        "checkout_date": payload.checkout_date.isoformat(),
        "due_date": payload.due_date.isoformat() if payload.due_date else None,
        "returned": False,
        "return_date": None,
    }

    checkouts.append(new_checkout)
    write_items(items)
    write_checkouts(checkouts)
    return new_checkout


@app.post("/api/return", response_model=CheckoutRecord)
def return_item(payload: ReturnRequest):
    items = read_items()
    checkouts = read_checkouts()

    checkout = next((c for c in checkouts if c["id"] == payload.checkout_id), None)
    if not checkout:
        raise HTTPException(status_code=404, detail="Checkout record not found")

    if checkout.get("returned", False):
        raise HTTPException(status_code=400, detail="Item already returned")

    item = next((i for i in items if i["id"] == checkout["item_id"]), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item for this checkout no longer exists")

    checkout["returned"] = True
    checkout["return_date"] = payload.return_date.isoformat()
    item["quantity"] += 1

    write_items(items)
    write_checkouts(checkouts)
    return checkout


@app.get("/api/health")
def health():
    return {"status": "ok", "date": date.today().isoformat()}