import os
import base64
from decimal import Decimal, ROUND_HALF_UP

import requests
from flask import Flask, render_template, request, jsonify, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

# -----------------------------
# Demo products (replace with DB later)
# Prices are EUR strings for simplicity
# -----------------------------
PRODUCTS = [
    {"id": "L1", "brand": "NIKE",  "title": "Air Jordan 4 “Black Cat”", "price": "350.00", "condition": "9/10", "size": "EU 42", "ship": "24h", "status": "available"},
    {"id": "L3", "brand": "APPLE", "title": "iPhone 15 Pro 256GB",      "price": "920.00", "condition": "New",  "size": "256GB", "ship": "Same day", "status": "available"},
    {"id": "L5", "brand": "SONY",  "title": "PlayStation 5 (Disc)",     "price": "430.00", "condition": "New",  "size": "Disc",  "ship": "24h", "status": "available"},
]

def get_product(pid: str):
    return next((p for p in PRODUCTS if p["id"] == pid), None)

def money(x: Decimal) -> str:
    return str(x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

# -----------------------------
# Cart helpers (session-based)
# cart: {"L1": 1, "L3": 2}
# -----------------------------
def cart_get():
    return session.get("cart", {})

def cart_set(cart):
    session["cart"] = cart
    session.modified = True

def cart_items():
    cart = cart_get()
    items = []
    total = Decimal("0.00")
    for pid, qty in cart.items():
        prod = get_product(pid)
        if not prod:
            continue
        price = Decimal(prod["price"])
        line = price * Decimal(qty)
        total += line
        items.append({
            "id": pid,
            "brand": prod["brand"],
            "title": prod["title"],
            "price": prod["price"],
            "qty": qty,
            "line_total": money(line),
        })
    return items, money(total)

# -----------------------------
# PayPal config
# -----------------------------
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
PAYPAL_ENV = os.environ.get("PAYPAL_ENV", "sandbox").lower()  # sandbox | live

PAYPAL_BASE = "https://api-m.sandbox.paypal.com" if PAYPAL_ENV == "sandbox" else "https://api-m.paypal.com"

def paypal_access_token() -> str:
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise RuntimeError("PayPal env vars missing: PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET")

    auth = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode()).decode()
    r = requests.post(
        f"{PAYPAL_BASE}/v1/oauth2/token",
        headers={"Authorization": f"Basic {auth}"},
        data={"grant_type": "client_credentials"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["access_token"]

# -----------------------------
# Pages
# -----------------------------
@app.get("/")
def index():
    return render_template("index.html", title="Resell Studio — shop", products=PRODUCTS)

@app.get("/cart")
def cart_page():
    items, total = cart_items()
    return render_template("cart.html", title="Krepšelis", items=items, total=total, paypal_client_id=PAYPAL_CLIENT_ID, paypal_env=PAYPAL_ENV)

@app.get("/success")
def success_page():
    order_id = request.args.get("order_id", "")
    return render_template("success.html", title="Apmokėta", order_id=order_id)

# -----------------------------
# Cart API
# -----------------------------
@app.get("/api/cart")
def api_cart():
    items, total = cart_items()
    return jsonify({"ok": True, "items": items, "total": total})

@app.post("/api/cart/add")
def api_cart_add():
    data = request.get_json(silent=True) or {}
    pid = (data.get("id") or "").strip()
    qty = int(data.get("qty") or 1)

    prod = get_product(pid)
    if not prod:
        return jsonify({"ok": False, "error": "Prekė nerasta."}), 404
    if prod.get("status") != "available":
        return jsonify({"ok": False, "error": "Prekė nepasiekiama."}), 400
    if qty < 1 or qty > 10:
        return jsonify({"ok": False, "error": "Neteisingas kiekis."}), 400

    cart = cart_get()
    cart[pid] = int(cart.get(pid, 0)) + qty
    cart_set(cart)
    return jsonify({"ok": True})

@app.post("/api/cart/update")
def api_cart_update():
    data = request.get_json(silent=True) or {}
    pid = (data.get("id") or "").strip()
    qty = int(data.get("qty") or 1)

    cart = cart_get()
    if pid not in cart:
        return jsonify({"ok": False, "error": "Prekė ne krepšelyje."}), 404

    if qty <= 0:
        cart.pop(pid, None)
    else:
        cart[pid] = min(max(qty, 1), 10)
    cart_set(cart)
    return jsonify({"ok": True})

@app.post("/api/cart/clear")
def api_cart_clear():
    cart_set({})
    return jsonify({"ok": True})

# -----------------------------
# PayPal Checkout API
# Frontend will call:
#   POST /api/paypal/create-order
#   POST /api/paypal/capture-order  {orderID}
# -----------------------------
@app.post("/api/paypal/create-order")
def paypal_create_order():
    items, total = cart_items()
    if Decimal(total) <= 0:
        return jsonify({"ok": False, "error": "Krepšelis tuščias."}), 400

    token = paypal_access_token()

    # Create order (EUR)
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {
                "currency_code": "EUR",
                "value": total
            }
        }],
        "application_context": {
            "brand_name": "Resell Studio",
            "landing_page": "NO_PREFERENCE",
            "user_action": "PAY_NOW",
            "return_url": url_for("success_page", _external=True),
            "cancel_url": url_for("cart_page", _external=True),
        }
    }

    r = requests.post(
        f"{PAYPAL_BASE}/v2/checkout/orders",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        json=payload,
        timeout=20,
    )
    r.raise_for_status()
    order = r.json()
    return jsonify({"ok": True, "id": order["id"]})

@app.post("/api/paypal/capture-order")
def paypal_capture_order():
    data = request.get_json(silent=True) or {}
    order_id = (data.get("orderID") or "").strip()
    if not order_id:
        return jsonify({"ok": False, "error": "Trūksta orderID."}), 400

    token = paypal_access_token()

    r = requests.post(
        f"{PAYPAL_BASE}/v2/checkout/orders/{order_id}/capture",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        timeout=20,
    )
    # PayPal returns details even on some errors, so handle gracefully:
    if not r.ok:
        return jsonify({"ok": False, "error": "PayPal capture nepavyko.", "details": r.json()}), 400

    capture = r.json()

    # IMPORTANT: if capture ok, clear cart
    cart_set({})

    return jsonify({"ok": True, "capture": capture})

# -----------------------------
# Inquiry (your existing idea)
# -----------------------------
@app.post("/api/inquiry")
def inquiry():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    contact = (data.get("contact") or "").strip()
    message = (data.get("message") or "").strip()
    if not (name and contact and message):
        return jsonify({"ok": False, "error": "Užpildyk visus laukus."}), 400

    return jsonify({"ok": True, "note": "Inquiry gauta ✅"})

if __name__ == "__main__":
    app.run(debug=True)
