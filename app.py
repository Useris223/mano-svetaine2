import os, json, base64, sqlite3
from decimal import Decimal
from functools import wraps
from datetime import datetime

import requests
from flask import (
    Flask, render_template, request, jsonify,
    session, redirect, url_for
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

# -------------------- PAYPAL --------------------
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
PAYPAL_ENV = os.environ.get("PAYPAL_ENV", "sandbox")

PAYPAL_BASE = (
    "https://api-m.sandbox.paypal.com"
    if PAYPAL_ENV == "sandbox"
    else "https://api-m.paypal.com"
)

def paypal_token():
    auth = base64.b64encode(
        f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode()
    ).decode()
    r = requests.post(
        f"{PAYPAL_BASE}/v1/oauth2/token",
        headers={"Authorization": f"Basic {auth}"},
        data={"grant_type": "client_credentials"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]

# -------------------- DATABASE --------------------
DB_PATH = "data/shop.db"
os.makedirs("data", exist_ok=True)

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    con = db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS products(
            id TEXT PRIMARY KEY,
            brand TEXT, title TEXT, price TEXT,
            condition TEXT, size TEXT, ship TEXT,
            status TEXT, image TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paypal_order_id TEXT,
            amount TEXT,
            currency TEXT,
            status TEXT,
            payer_email TEXT,
            items_json TEXT,
            created_at TEXT
        )
    """)
    con.commit()
    con.close()

init_db()

def all_products():
    con = db()
    rows = con.execute("SELECT * FROM products").fetchall()
    con.close()
    return [dict(r) for r in rows]

# -------------------- CART --------------------
def cart_get():
    return session.get("cart", {})

def cart_set(c):
    session["cart"] = c
    session.modified = True

def cart_items():
    items = []
    total = Decimal("0.00")
    products = {p["id"]: p for p in all_products()}
    for pid, qty in cart_get().items():
        if pid in products:
            p = products[pid]
            line = Decimal(p["price"]) * qty
            total += line
            items.append({
                "id": pid,
                "title": p["title"],
                "price": p["price"],
                "qty": qty,
                "line_total": f"{line:.2f}"
            })
    return items, f"{total:.2f}"

# -------------------- PAGES --------------------
@app.get("/")
def index():
    return render_template(
        "index.html",
        title="TopShopp Deals",
        products=all_products(),
        year=datetime.now().year
    )

@app.get("/cart")
def cart_page():
    items, total = cart_items()
    return render_template(
        "cart.html",
        title="Krepšelis",
        items=items,
        total=total,
        paypal_client_id=PAYPAL_CLIENT_ID,
        year=datetime.now().year
    )

@app.get("/success")
def success():
    return render_template(
        "success.html",
        title="Apmokėta",
        order_id=request.args.get("order_id"),
        year=datetime.now().year
    )

# -------------------- CART API --------------------
@app.post("/api/cart/add")
def cart_add():
    pid = request.json.get("id")
    cart = cart_get()
    cart[pid] = cart.get(pid, 0) + 1
    cart_set(cart)
    return jsonify(ok=True)

@app.post("/api/cart/update")
def cart_update():
    pid = request.json.get("id")
    qty = int(request.json.get("qty"))
    cart = cart_get()
    if qty <= 0:
        cart.pop(pid, None)
    else:
        cart[pid] = qty
    cart_set(cart)
    return jsonify(ok=True)

@app.post("/api/cart/clear")
def cart_clear():
    cart_set({})
    return jsonify(ok=True)

# -------------------- PAYPAL API --------------------
@app.post("/api/paypal/create-order")
def create_order():
    items, total = cart_items()
    token = paypal_token()
    r = requests.post(
        f"{PAYPAL_BASE}/v2/checkout/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {"currency_code": "EUR", "value": total}
            }]
        },
        timeout=15
    )
    r.raise_for_status()
    return jsonify(ok=True, id=r.json()["id"])

@app.post("/api/paypal/capture-order")
def capture_order():
    order_id = request.json.get("orderID")
    token = paypal_token()
    r = requests.post(
        f"{PAYPAL_BASE}/v2/checkout/orders/{order_id}/capture",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15
    )
    data = r.json()
    items, total = cart_items()

    con = db()
    con.execute("""
        INSERT INTO orders(paypal_order_id, amount, currency, status, payer_email, items_json, created_at)
        VALUES (?,?,?,?,?,?,?)
    """, (
        order_id, total, "EUR",
        data.get("status", ""),
        data.get("payer", {}).get("email_address", ""),
        json.dumps(items),
        datetime.now().isoformat()
    ))
    con.commit()
    con.close()

    cart_set({})
    return jsonify(ok=True)

# -------------------- ADMIN --------------------
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "admin")

def admin_required(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get("admin"):
            return redirect("/admin/login")
        return f(*a, **k)
    return w

@app.get("/admin/login")
def admin_login():
    return render_template("admin_login.html", title="Admin", year=datetime.now().year)

@app.post("/admin/login")
def admin_login_post():
    if request.form.get("token") == ADMIN_TOKEN:
        session["admin"] = True
        return redirect("/admin/products")
    return "Wrong token", 403

@app.get("/admin/products")
@admin_required
def admin_products():
    return render_template(
        "admin_products.html",
        products=all_products(),
        title="Admin products",
        year=datetime.now().year
    )

@app.get("/admin/products/new")
@admin_required
def admin_new():
    return render_template("admin_edit.html", p=None, year=datetime.now().year)

@app.post("/admin/products/save")
@admin_required
def admin_save():
    f = request.form
    con = db()
    con.execute("""
        INSERT OR REPLACE INTO products
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        f["id"], f["brand"], f["title"], f["price"],
        f["condition"], f["size"], f["ship"],
        f["status"], f["image"]
    ))
    con.commit()
    con.close()
    return redirect("/admin/products")
