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
from .database import init_db, get_connection

app = FastAPI(title="Inventory Lending Tracker API", version="1.0.0")

init_db()

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
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/login")
def login(payload: dict):
    username = payload.get("username", "").strip()
    password = payload.get("password", "").strip()

    if username == "admin" and password == "password123":
        return {"message": "Login successful"}

    raise HTTPException(status_code=401, detail="Invalid username or password")


@app.get("/api/items", response_model=List[Item])
def get_items():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM items ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/api/items", response_model=Item)
def add_item(payload: ItemCreate):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT * FROM items
        WHERE LOWER(name) = LOWER(?) AND LOWER(category) = LOWER(?)
        """,
        (payload.name.strip(), payload.category.strip()),
    )
    existing = cur.fetchone()

    if existing:
        new_quantity = existing["quantity"] + payload.quantity
        cur.execute(
            "UPDATE items SET quantity = ? WHERE id = ?",
            (new_quantity, existing["id"]),
        )
        conn.commit()

        cur.execute("SELECT * FROM items WHERE id = ?", (existing["id"],))
        updated = cur.fetchone()
        conn.close()
        return dict(updated)

    cur.execute(
        """
        INSERT INTO items (name, category, quantity)
        VALUES (?, ?, ?)
        """,
        (payload.name.strip(), payload.category.strip(), payload.quantity),
    )
    conn.commit()

    item_id = cur.lastrowid
    cur.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    new_item = cur.fetchone()
    conn.close()

    return dict(new_item)


@app.delete("/api/items/{item_id}")
def delete_item(item_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    item = cur.fetchone()

    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found")

    cur.execute(
        """
        SELECT * FROM checkouts
        WHERE item_id = ? AND returned = 0
        """,
        (item_id,),
    )
    active_checkout = cur.fetchone()

    if active_checkout:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Cannot delete an item that is currently checked out",
        )

    cur.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    return {"message": "Item deleted successfully"}


@app.get("/api/checkedout", response_model=List[CheckoutRecord])
def get_checked_out():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM checkouts WHERE returned = 0 ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/api/checkout", response_model=CheckoutRecord)
def checkout_item(payload: CheckoutCreate):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM items WHERE id = ?", (payload.item_id,))
    item = cur.fetchone()

    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found")

    if item["quantity"] <= 0:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Item is out of stock (quantity is 0)",
        )

    cur.execute(
        "UPDATE items SET quantity = quantity - 1 WHERE id = ?",
        (payload.item_id,),
    )

    cur.execute(
        """
        INSERT INTO checkouts (item_id, borrower, checkout_date, due_date, returned, return_date)
        VALUES (?, ?, ?, ?, 0, NULL)
        """,
        (
            payload.item_id,
            payload.borrower.strip(),
            payload.checkout_date.isoformat(),
            payload.due_date.isoformat() if payload.due_date else None,
        ),
    )
    conn.commit()

    checkout_id = cur.lastrowid
    cur.execute("SELECT * FROM checkouts WHERE id = ?", (checkout_id,))
    new_checkout = cur.fetchone()
    conn.close()

    return dict(new_checkout)


@app.post("/api/return", response_model=CheckoutRecord)
def return_item(payload: ReturnRequest):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM checkouts WHERE id = ?", (payload.checkout_id,))
    checkout = cur.fetchone()

    if not checkout:
        conn.close()
        raise HTTPException(status_code=404, detail="Checkout record not found")

    if checkout["returned"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Item already returned")

    cur.execute("SELECT * FROM items WHERE id = ?", (checkout["item_id"],))
    item = cur.fetchone()

    if not item:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail="Item for this checkout no longer exists",
        )

    cur.execute(
        """
        UPDATE checkouts
        SET returned = 1, return_date = ?
        WHERE id = ?
        """,
        (payload.return_date.isoformat(), payload.checkout_id),
    )

    cur.execute(
        """
        UPDATE items
        SET quantity = quantity + 1
        WHERE id = ?
        """,
        (checkout["item_id"],),
    )

    conn.commit()

    cur.execute("SELECT * FROM checkouts WHERE id = ?", (payload.checkout_id,))
    updated_checkout = cur.fetchone()
    conn.close()

    return dict(updated_checkout)


@app.get("/api/health")
def health():
    return {"status": "ok", "date": date.today().isoformat()}