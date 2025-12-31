import os
import base64
from decimal import Decimal
from datetime import datetime

import requests
from flask import Flask, render_template, request, jsonify, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

# ---- Discord invite (įrašyk savo linką Render Environment arba čia) ----
DISCORD_INVITE = os.environ.get("DISCORD_INVITE", "https://discord.gg/PAKEISK_SITA")

# ---- Maintenance banner ----
SITE_NOTICE = os.environ.get("SITE_NOTICE", "⚠️ Svetainė kuriama – kai kurios funkcijos gali neveikti.")

# ---- Demo products ----
PRODUCTS = [
    {"id": "L1", "brand": "NIKE", "title": "Air Jordan 4 “Black Cat”", "price": "350.00", "condition": "9/10",
     "size": "EU 42", "ship": "24h", "status": "available", "image": "/static/products/L1.jpg"},
    {"id": "L3", "brand": "APPLE", "title": "iPhone 15 Pro 256GB", "price": "920.00", "condition": "New",
     "size": "256GB", "ship": "Same day", "status": "available", "image": "/static/products/L3.jpg"},
    {"id": "L5", "brand": "SONY", "title": "PlayStation 5 (Disc)", "price": "430.00", "condition": "New",
     "size": "Disc", "ship": "24h", "status": "available", "image": "/static/products/L5.jpg"},
]

def get_product(pid: str):
    return next((p for p in PRODUCTS if p["id"] == pid), None)

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
            "image": prod.get("image", ""),
            "price": f"{price:.2f}",
            "qty": int(qty),
            "line_total": f"{line:.2f}",
        })
    return items, f"{total:.2f}"

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
    return render_template(
        "index.html",
        title="TopShopp Deals",
        year=datetime.now().year,
        products=PRODUCTS,
        discord_invite=DISCORD_INVITE,
        site_notice=SITE_NOTICE,
    )

@app.get("/cart")
def cart_page():
    items, total = cart_items()
    return render_template(
        "cart.html",
        title="Krepšelis",
        year=datetime.now().year,
        items=items,
        total=total,
        paypal_client_id=PAYPAL_CLIENT_ID,
        paypal_env=PAYPAL_ENV,
        discord_invite=DISCORD_INVITE,
        site_notice=SITE_NOTICE,
    )

@app.get("/success")
def success_page():
    order_id = request.args.get("order_id", "")
    return render_template(
        "success.html",
        title="Apmokėta",
        year=datetime.now().year,
        order_id=order_id,
        discord_invite=DISCORD_INVITE,
        site_notice=SITE_NOTICE,
    )

# -----------------------------
# Cart API
# -----------------------------
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
# -----------------------------
@app.post("/api/paypal/create-order")
def paypal_create_order():
    items, total = cart_items()
    if Decimal(total) <= 0:
        return jsonify({"ok": False, "error": "Krepšelis tuščias."}), 400

    token = paypal_access_token()

    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {"currency_code": "EUR", "value": total}
        }],
        "application_context": {
            "brand_name": "TopShopp Deals",
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
    if not r.ok:
        return jsonify({"ok": False, "error": "PayPal capture nepavyko.", "details": r.json()}), 400

    # success -> clear cart
    cart_set({})
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(debug=True)
