"""
Pizzomania - Flask agentic demo.

Files:
    app.py               - backend logic + API (this file)
    templates/index.html - page structure
    static/style.css     - visual styling (V1: hero, photography, colour system)
    static/app.js        - frontend behaviour

Run:
    pip3 install -r requirements.txt
    python3 app.py

Opens at http://0.0.0.0:PORT (see PORT constant below).
"""

import os
import math
import random
import string
from urllib.parse import quote

import requests
from flask import Flask, jsonify, render_template, request, session

# ============================================================
# HAND-EDITABLE CONSTANTS
# ============================================================
# GEMINI_API_KEY = "PASTE_YOUR_GEMINI_API_KEY_HERE"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "PASTE_YOUR_GEMINI_API_KEY_HERE")
AGENT_NAME = "pizzomania"
PORT = 8083
# ============================================================

app = Flask(__name__)
app.secret_key = "healthy-pizza-demo-secret-key-change-me"

GEMINI_ENABLED = bool(GEMINI_API_KEY) and GEMINI_API_KEY != "PASTE_YOUR_GEMINI_API_KEY_HERE"
_genai_client = None
if GEMINI_ENABLED:
    try:
        from google import genai
        _genai_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        GEMINI_ENABLED = False
        _genai_client = None

# ------------------------------------------------------------
# IMAGES
# Hotlinked from Wikimedia Commons (free, no key, stable CDN) via the
# Special:FilePath redirect. If a filename ever gets renamed on Commons,
# the <img> has a CSS/JS fallback in the frontend so it never shows a
# broken-image icon.
# ------------------------------------------------------------
def wiki_img(filename, width=700):
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(filename)}?width={width}"


HERO_IMAGE = wiki_img("Pizza slices with various toppings.jpg", width=1600)

# ------------------------------------------------------------
# MENU DATA
# ------------------------------------------------------------
ALLOWED_SIZES = {
    "single": ["Small", "Medium", "Large"],
    "family": ["Large", "Family"],
    "kids": ["Small", "Medium"],
}
SIZE_PRICE_STEP = {"Small": 0.0, "Medium": 3.0, "Large": 6.0, "Family": 10.0}
SIZE_CAL_STEP = {"Small": 0, "Medium": 150, "Large": 300, "Family": 600}

CRUSTS = [
    {"name": "Classic", "price": 0.0, "cal": 0},
    {"name": "Thin & Crispy", "price": 0.0, "cal": -60},
    {"name": "Cauliflower (Gluten-Free)", "price": 2.5, "cal": -90},
    {"name": "Wholemeal", "price": 1.0, "cal": -30},
]

TOPPINGS = [
    {"name": "Extra Vegan Cheese", "price": 1.5, "cal": 80},
    {"name": "Mushroom", "price": 1.0, "cal": 20},
    {"name": "Baby Spinach", "price": 1.0, "cal": 10},
    {"name": "Kalamata Olives", "price": 1.2, "cal": 30},
    {"name": "Roasted Pumpkin", "price": 1.5, "cal": 60},
    {"name": "Chargrilled Chicken", "price": 2.5, "cal": 90},
    {"name": "Pepperoni", "price": 2.0, "cal": 120},
    {"name": "Semi-Dried Tomato", "price": 1.2, "cal": 25},
    {"name": "Red Onion", "price": 0.8, "cal": 15},
    {"name": "Jalapenos", "price": 1.0, "cal": 10},
    {"name": "Fresh Basil", "price": 0.8, "cal": 5},
    {"name": "Pineapple", "price": 1.0, "cal": 40},
]

PIZZAS = [
    # ---------------- SINGLE ----------------
    {"id": "s1", "category": "single", "name": "Garden Veggie Delight",
     "description": "Roasted capsicum, mushroom, red onion, baby spinach, vegan cheese.",
     "base_price": 14.90, "base_cal": 620, "tags": ["Vegan", "Healthy Choice"],
     "image": wiki_img("Vegetable pizza Denpasar Bali.JPG")},
    {"id": "s2", "category": "single", "name": "Margherita Fresca",
     "description": "Fresh tomato, basil, light mozzarella on a classic base.",
     "base_price": 13.90, "base_cal": 580, "tags": ["Vegetarian", "Healthy Choice"],
     "image": wiki_img("Pizza Margherita (14703152728).jpg")},
    {"id": "s3", "category": "single", "name": "Mediterranean Falafel",
     "description": "Falafel, hummus drizzle, olives, spinach, semi-dried tomato.",
     "base_price": 15.50, "base_cal": 640, "tags": ["Vegan"],
     "image": wiki_img("Mediterranean Pizza from BJ's Restaurant & Brewhouse.jpg")},
    {"id": "s4", "category": "single", "name": "Lean BBQ Chicken & Corn",
     "description": "Grilled chicken breast, corn, red onion, light BBQ base.",
     "base_price": 15.90, "base_cal": 650, "tags": ["Healthy Choice"],
     "image": wiki_img("B.B.Q. Chicken Pizza (26679384893).jpg")},
    # ---------------- FAMILY ----------------
    {"id": "f1", "category": "family", "name": "Family Veggie Feast",
     "description": "A generous mix of roast vegetables and vegan cheese. Serves 4-6.",
     "base_price": 24.90, "base_cal": 1800, "tags": ["Vegan", "Healthy Choice"],
     "image": wiki_img("Vegetable pizza Denpasar Bali.JPG")},
    {"id": "f2", "category": "family", "name": "Family Margherita",
     "description": "Classic tomato and cheese the whole family can agree on. Serves 4-6.",
     "base_price": 23.90, "base_cal": 1700, "tags": ["Vegetarian"],
     "image": wiki_img("Margherita Pizza.jpg")},
    {"id": "f3", "category": "family", "name": "Family Lean Supreme",
     "description": "Chicken, capsicum, mushroom, olives, light cheese. Serves 4-6.",
     "base_price": 26.90, "base_cal": 1950, "tags": ["Healthy Choice"],
     "image": wiki_img("Round Table chicken & garlic pizza.JPG")},
    {"id": "f4", "category": "family", "name": "Family BBQ Chicken",
     "description": "Grilled chicken, corn, red onion, smoky BBQ base. Serves 4-6.",
     "base_price": 27.90, "base_cal": 2000, "tags": [],
     "image": wiki_img("BBQ Chicken Pizza Hut.jpg")},
    # ---------------- KIDS ----------------
    {"id": "k1", "category": "kids", "name": "Mini Cheese Smiles",
     "description": "Mild cheese and tomato base, cut into smiley slices.",
     "base_price": 9.90, "base_cal": 420, "tags": ["Vegetarian"],
     "image": wiki_img("Pizza slice.jpg")},
    {"id": "k2", "category": "kids", "name": "Veggie Stars",
     "description": "Corn, capsicum and vegan cheese, cut into fun star shapes.",
     "base_price": 10.50, "base_cal": 400, "tags": ["Vegan"],
     "image": wiki_img("Pizza quasi Margherita.jpg")},
    {"id": "k3", "category": "kids", "name": "Ham & Pineapple Buddies",
     "description": "A kid-favourite: ham and pineapple, mild cheese.",
     "base_price": 10.90, "base_cal": 450, "tags": [],
     "image": wiki_img("Ham and pineapple pizza, The Mill Pizza.jpg")},
    {"id": "k4", "category": "kids", "name": "Mini Margherita Munchkins",
     "description": "Simple tomato and mozzarella, cut into small squares.",
     "base_price": 9.50, "base_cal": 400, "tags": ["Vegetarian"],
     "image": wiki_img("Margherita's Pizza.jpg")},
]
PIZZA_BY_ID = {p["id"]: p for p in PIZZAS}

# ------------------------------------------------------------
# STORES (hardcoded lat/long — approximate)
# ------------------------------------------------------------
STORES = [
    {"id": "castle_hill", "name": "Healthy Pizza Castle Hill",
     "address": "12 Old Northern Rd, Castle Hill NSW 2154", "lat": -33.7333, "lon": 150.9821},
    {"id": "schofields", "name": "Healthy Pizza Schofields",
     "address": "5 Railway Tce, Schofields NSW 2762", "lat": -33.7167, "lon": 150.8667},
    {"id": "rouse_hill", "name": "Healthy Pizza Rouse Hill",
     "address": "8 Guildford Rd, Rouse Hill NSW 2155", "lat": -33.6833, "lon": 150.9167},
    {"id": "marsden_park", "name": "Healthy Pizza Marsden Park",
     "address": "3 Garfield Rd, Marsden Park NSW 2765", "lat": -33.7167, "lon": 150.8500},
]

# Dummy addresses used when live geocoding fails/times out/returns nothing.
# Mix of near (should be cateredable) and far (should trigger the >20km message).
DUMMY_ADDRESSES = [
    {"label": "12 Old Northern Rd, Castle Hill NSW 2154", "lat": -33.7325, "lon": 150.9807},
    {"label": "5 Railway Tce, Schofields NSW 2762", "lat": -33.7150, "lon": 150.8690},
    {"label": "8 Guildford Rd, Rouse Hill NSW 2155", "lat": -33.6820, "lon": 150.9190},
    {"label": "3 Garfield Rd, Marsden Park NSW 2765", "lat": -33.7190, "lon": 150.8530},
    {"label": "45 George St, Sydney NSW 2000", "lat": -33.8650, "lon": 151.2094},
    {"label": "10 Beach Rd, Cronulla NSW 2230", "lat": -34.0286, "lon": 151.1550},
    {"label": "22 Pittwater Rd, Manly NSW 2095", "lat": -33.7969, "lon": 151.2870},
    {"label": "1 Bells Line of Rd, Kurmond NSW 2757", "lat": -33.5892, "lon": 150.6764},
]

MAX_DELIVERY_KM = 20.0


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_store(lat, lon):
    best, best_d = None, None
    for s in STORES:
        d = haversine_km(lat, lon, s["lat"], s["lon"])
        if best_d is None or d < best_d:
            best, best_d = s, d
    return best, round(best_d, 1)


def geocode_address(query):
    """Try OpenStreetMap Nominatim (free, no key). Returns (results, used_fallback)."""
    try:
        headers = {"User-Agent": "HealthyPizzaApp-Demo/1.0 (demo contact: pizza-demo@example.com)"}
        params = {
            "q": query,
            "format": "json",
            "countrycodes": "au",
            "limit": 5,
            "viewbox": "150.60,-33.55,151.10,-33.85",
            "bounded": 0,
        }
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=params, headers=headers, timeout=5,
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            return [], True
        results = [
            {"label": d.get("display_name"), "lat": float(d["lat"]), "lon": float(d["lon"])}
            for d in data
        ]
        return results, False
    except Exception:
        return [], True


def calc_pizza_price_and_cal(pizza_id, size, crust_name, topping_names):
    pizza = PIZZA_BY_ID.get(pizza_id)
    if not pizza:
        raise ValueError("Unknown pizza selected.")
    allowed = ALLOWED_SIZES[pizza["category"]]
    if size not in allowed:
        raise ValueError(f"'{size}' is not a valid size for this pizza.")
    base_size = allowed[0]
    size_price = SIZE_PRICE_STEP[size] - SIZE_PRICE_STEP[base_size]
    size_cal = SIZE_CAL_STEP[size] - SIZE_CAL_STEP[base_size]

    crust = next((c for c in CRUSTS if c["name"] == crust_name), CRUSTS[0])
    topping_objs = [t for t in TOPPINGS if t["name"] in (topping_names or [])]

    price = pizza["base_price"] + size_price + crust["price"] + sum(t["price"] for t in topping_objs)
    cal = pizza["base_cal"] + size_cal + crust["cal"] + sum(t["cal"] for t in topping_objs)
    return round(price, 2), max(cal, 0), pizza, crust, topping_objs


def cart_totals(cart):
    return round(sum(item["unit_price"] * item["qty"] for item in cart), 2)


def gemini_delivery_message(cart_summary, fulfilment, store, distance_km, can_fulfil):
    """Ask Gemini for a friendly outcome message, or fall back to a deterministic one."""
    if fulfilment == "pickup":
        prompt_text = (
            f"You are a friendly pizza shop assistant. A customer chose PICKUP from "
            f"{store['name']} ({store['address']}). Their order: {cart_summary}. "
            f"Write a short (2-3 sentence), warm, plain-language confirmation suitable "
            f"for a senior or a child, confirming pickup is available."
        )
    elif can_fulfil:
        prompt_text = (
            f"You are a friendly pizza shop assistant. A customer ordered delivery. "
            f"Their order: {cart_summary}. The nearest kitchen is {store['name']} "
            f"({store['address']}), which is {distance_km}km away (within our 20km "
            f"delivery range). Write a short (2-3 sentence), warm, plain-language "
            f"message confirming delivery is available, suitable for a senior or a child."
        )
    else:
        prompt_text = (
            f"You are a friendly pizza shop assistant. A customer ordered delivery. "
            f"Their order: {cart_summary}. The nearest kitchen is {store['name']} "
            f"({store['address']}), which is {distance_km}km away, outside our 20km "
            f"delivery range. Write a short (2-3 sentence), warm, plain-language message "
            f"explaining delivery isn't available due to distance, and suggest pickup "
            f"instead, suitable for a senior or a child."
        )

    if GEMINI_ENABLED and _genai_client is not None:
        try:
            response = _genai_client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt_text
            )
            text = (response.text or "").strip()
            if text:
                return text, "gemini"
        except Exception:
            pass  # fall through to deterministic message

    if fulfilment == "pickup":
        msg = (f"You're all set! Head to {store['name']} at {store['address']} and "
               f"we'll have your order ready for pickup.")
    elif can_fulfil:
        msg = (f"Good news — you're only {distance_km}km from our {store['name']} "
               f"kitchen, well within our 20km delivery range. Your order is on its way!")
    else:
        msg = (f"We're sorry, {store['name']} is {distance_km}km away, which is past our "
               f"20km delivery limit. We can't deliver this time, but you're welcome to "
               f"pick up your order from {store['name']} at {store['address']} instead.")
    return msg, "deterministic"


def make_order_number():
    return "HP-" + "".join(random.choices(string.digits, k=6))


# ------------------------------------------------------------
# ROUTES
# ------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", agent_name=AGENT_NAME, hero_image=HERO_IMAGE)


@app.route("/api/menu")
def api_menu():
    return jsonify({
        "pizzas": PIZZAS,
        "allowed_sizes": ALLOWED_SIZES,
        "crusts": CRUSTS,
        "toppings": TOPPINGS,
        "size_price_step": SIZE_PRICE_STEP,
    })


@app.route("/api/stores")
def api_stores():
    return jsonify({"stores": STORES})


@app.route("/api/cart", methods=["GET"])
def api_cart_get():
    cart = session.get("cart", [])
    return jsonify({"cart": cart, "subtotal": cart_totals(cart)})


@app.route("/api/cart/add", methods=["POST"])
def api_cart_add():
    data = request.get_json(force=True) or {}
    pizza_id = data.get("pizza_id")
    size = data.get("size")
    crust = data.get("crust")
    toppings = data.get("toppings") or []
    try:
        qty = max(1, int(data.get("qty", 1)))
    except (TypeError, ValueError):
        qty = 1

    try:
        price, cal, pizza, crust_obj, topping_objs = calc_pizza_price_and_cal(
            pizza_id, size, crust, toppings
        )
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    cart = session.get("cart", [])
    cart.append({
        "pizza_id": pizza_id,
        "name": pizza["name"],
        "category": pizza["category"],
        "size": size,
        "crust": crust_obj["name"],
        "toppings": [t["name"] for t in topping_objs],
        "unit_price": price,
        "calories": cal,
        "qty": qty,
    })
    session["cart"] = cart
    return jsonify({"ok": True, "cart": cart, "subtotal": cart_totals(cart)})


@app.route("/api/cart/remove", methods=["POST"])
def api_cart_remove():
    data = request.get_json(force=True) or {}
    idx = data.get("index")
    cart = session.get("cart", [])
    if idx is None or not isinstance(idx, int) or not (0 <= idx < len(cart)):
        return jsonify({"ok": False, "error": "Invalid item."}), 400
    cart.pop(idx)
    session["cart"] = cart
    return jsonify({"ok": True, "cart": cart, "subtotal": cart_totals(cart)})


@app.route("/api/cart/clear", methods=["POST"])
def api_cart_clear():
    session["cart"] = []
    return jsonify({"ok": True, "cart": [], "subtotal": 0})


@app.route("/api/address/lookup", methods=["POST"])
def api_address_lookup():
    data = request.get_json(force=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"ok": False, "error": "Please enter an address."}), 400
    results, used_fallback = geocode_address(query)
    if used_fallback or not results:
        return jsonify({"ok": True, "fallback": True, "results": DUMMY_ADDRESSES})
    return jsonify({"ok": True, "fallback": False, "results": results})


@app.route("/api/order/process", methods=["POST"])
def api_order_process():
    data = request.get_json(force=True) or {}
    cart = session.get("cart", [])
    fulfilment = data.get("fulfilment")  # "pickup" | "delivery"
    store_id = data.get("store_id")
    address = data.get("address")  # {"label":..,"lat":..,"lon":..}

    if not cart:
        return jsonify({"ok": False, "error": "Your cart is empty."}), 400
    if fulfilment not in ("pickup", "delivery"):
        return jsonify({"ok": False, "error": "Choose pickup or delivery."}), 400

    subtotal = cart_totals(cart)
    cart_summary = "; ".join(
        f"{i['qty']}x {i['size']} {i['name']} ({i['crust']}"
        + (f" + {', '.join(i['toppings'])}" if i["toppings"] else "") + ")"
        for i in cart
    )

    steps = [{
        "step": 1, "title": "PLAN",
        "detail": (
            f"Order: {cart_summary}. Fulfilment: {fulfilment}."
            + (f" Address entered: {address.get('label')}." if fulfilment == "delivery" and address else "")
            + " I will check whether the nearest kitchen is within 20km before confirming."
        ),
    }]

    try:
        if fulfilment == "pickup":
            store = next((s for s in STORES if s["id"] == store_id), None)
            if store is None:
                return jsonify({"ok": False, "error": "Please choose a store."}), 400
            distance_km = 0.0
            can_fulfil = True
            steps.append({
                "step": 2, "title": "TOOL USE",
                "detail": f"Pickup selected directly at {store['name']} — no address lookup needed.",
            })
        else:
            if not address or "lat" not in address or "lon" not in address:
                return jsonify({"ok": False, "error": "Please select a verified address."}), 400
            store, distance_km = nearest_store(address["lat"], address["lon"])
            can_fulfil = distance_km <= MAX_DELIVERY_KM
            steps.append({
                "step": 2, "title": "TOOL USE",
                "detail": (
                    f"Looked up '{address.get('label')}'. Computed distance to all 4 kitchens "
                    f"using the Haversine formula. Nearest: {store['name']} at {distance_km}km."
                ),
            })

        delivery_fee = 0.0 if fulfilment == "pickup" else (4.99 if can_fulfil else 0.0)
        total = round(subtotal + delivery_fee, 2)

        gemini_message, mode = gemini_delivery_message(cart_summary, fulfilment, store, distance_km, can_fulfil)
        steps.append({
            "step": 3, "title": "REASON",
            "detail": (
                f"Sent the order summary, nearest kitchen and distance to Gemini "
                f"({'live call' if mode == 'gemini' else 'deterministic demo mode — no API key configured'}) "
                f"and asked for a plain-language delivery/pickup message."
            ),
        })

        order = None
        if can_fulfil:
            prep_minutes = 15
            eta_minutes = prep_minutes if fulfilment == "pickup" else prep_minutes + round(distance_km * 2)
            order = {
                "order_number": make_order_number(),
                "items": cart,
                "subtotal": subtotal,
                "delivery_fee": delivery_fee,
                "total": total,
                "fulfilment": fulfilment,
                "store": store,
                "address": address if fulfilment == "delivery" else None,
                "distance_km": distance_km,
                "eta_minutes": eta_minutes,
            }
            session["cart"] = []  # order placed, clear the cart

        steps.append({"step": 4, "title": "FINAL ANSWER", "detail": gemini_message})

        return jsonify({
            "ok": True,
            "can_fulfil": can_fulfil,
            "steps": steps,
            "gemini_message": gemini_message,
            "gemini_mode": mode,
            "order": order,
        })
    except Exception as e:
        steps.append({
            "step": 4, "title": "FINAL ANSWER",
            "detail": f"Something went wrong while checking your order: {e}. Please try again.",
        })
        return jsonify({"ok": False, "error": str(e), "steps": steps}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
