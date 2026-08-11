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

import math
import os
import random
import re
import secrets
import string
from datetime import datetime, timezone
from urllib.parse import quote

import requests
from flask import Flask, jsonify, render_template, request, session

# ============================================================
# HAND-EDITABLE CONSTANTS
# ============================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
AGENT_NAME = "Pizzomania"
PORT = 8083
# ============================================================

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-pizzomania-secret-change-me")

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
# All customer-facing product photography is served locally for consistent
# branding and predictable performance.
# ------------------------------------------------------------
HERO_IMAGE = "/static/images/hero-pizza.webp"

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
     "image": "/static/images/pizzas/garden.webp",
     "rating": 4.7, "reviews": 312},
    {"id": "s2", "category": "single", "name": "Margherita Fresca",
     "description": "Fresh tomato, basil, light mozzarella on a classic base.",
     "base_price": 13.90, "base_cal": 580, "tags": ["Vegetarian", "Healthy Choice"],
     "image": "/static/images/pizzas/margherita.webp",
     "rating": 4.8, "reviews": 405},
    {"id": "s3", "category": "single", "name": "Mediterranean Falafel",
     "description": "Falafel, hummus drizzle, olives, spinach, semi-dried tomato.",
     "base_price": 15.50, "base_cal": 640, "tags": ["Vegan"],
     "image": "/static/images/pizzas/mediterranean.webp",
     "rating": 4.6, "reviews": 178},
    {"id": "s4", "category": "single", "name": "Lean BBQ Chicken & Corn",
     "description": "Grilled chicken breast, corn, red onion, light BBQ base.",
     "base_price": 15.90, "base_cal": 650, "tags": ["Healthy Choice"],
     "image": "/static/images/pizzas/bbq.webp",
     "rating": 4.7, "reviews": 264},
    # ---------------- FAMILY ----------------
    {"id": "f1", "category": "family", "name": "Family Veggie Feast",
     "description": "A generous mix of roast vegetables and vegan cheese. Serves 4-6.",
     "base_price": 24.90, "base_cal": 1800, "tags": ["Vegan", "Healthy Choice"],
     "image": "/static/images/pizzas/family_veggie.webp",
     "rating": 4.8, "reviews": 190},
    {"id": "f2", "category": "family", "name": "Family Margherita",
     "description": "Classic tomato and cheese the whole family can agree on. Serves 4-6.",
     "base_price": 23.90, "base_cal": 1700, "tags": ["Vegetarian"],
     "image": "/static/images/pizzas/family_margherita.webp",
     "rating": 4.9, "reviews": 233},
    {"id": "f3", "category": "family", "name": "Family Lean Supreme",
     "description": "Chicken, capsicum, mushroom, olives, light cheese. Serves 4-6.",
     "base_price": 26.90, "base_cal": 1950, "tags": ["Healthy Choice"],
     "image": "/static/images/pizzas/family_supreme.webp",
     "rating": 4.6, "reviews": 121},
    {"id": "f4", "category": "family", "name": "Family BBQ Chicken",
     "description": "Grilled chicken, corn, red onion, smoky BBQ base. Serves 4-6.",
     "base_price": 27.90, "base_cal": 2000, "tags": [],
     "image": "/static/images/pizzas/family_bbq.webp",
     "rating": 4.7, "reviews": 208},
    # ---------------- KIDS ----------------
    {"id": "k1", "category": "kids", "name": "Mini Cheese Smiles",
     "description": "Mild cheese and tomato base, cut into smiley slices.",
     "base_price": 9.90, "base_cal": 420, "tags": ["Vegetarian"],
     "image": "/static/images/pizzas/kids_cheese.webp",
     "rating": 4.9, "reviews": 356},
    {"id": "k2", "category": "kids", "name": "Veggie Stars",
     "description": "Corn, capsicum and vegan cheese, cut into fun star shapes.",
     "base_price": 10.50, "base_cal": 400, "tags": ["Vegan"],
     "image": "/static/images/pizzas/kids_veggie.webp",
     "rating": 4.5, "reviews": 142},
    {"id": "k3", "category": "kids", "name": "Ham & Pineapple Buddies",
     "description": "A kid-favourite: ham and pineapple, mild cheese.",
     "base_price": 10.90, "base_cal": 450, "tags": [],
     "image": "/static/images/pizzas/kids_ham_pineapple.webp",
     "rating": 4.6, "reviews": 289},
    {"id": "k4", "category": "kids", "name": "Mini Margherita Munchkins",
     "description": "Simple tomato and mozzarella, cut into small squares.",
     "base_price": 9.50, "base_cal": 400, "tags": ["Vegetarian"],
     "image": "/static/images/pizzas/kids_mini_margherita.webp",
     "rating": 4.8, "reviews": 197},
]
PIZZA_BY_ID = {p["id"]: p for p in PIZZAS}

# ------------------------------------------------------------
# STORES (hardcoded lat/long — approximate)
# ------------------------------------------------------------
STORES = [
    {"id": "castle_hill", "name": "Pizzomania Castle Hill",
     "address": "12 Old Northern Rd, Castle Hill NSW 2154", "lat": -33.7333, "lon": 150.9821,
     "rating": 4.8, "reviews": 512},
    {"id": "schofields", "name": "Pizzomania Schofields",
     "address": "5 Railway Tce, Schofields NSW 2762", "lat": -33.7167, "lon": 150.8667,
     "rating": 4.6, "reviews": 298},
    {"id": "rouse_hill", "name": "Pizzomania Rouse Hill",
     "address": "8 Guildford Rd, Rouse Hill NSW 2155", "lat": -33.6833, "lon": 150.9167,
     "rating": 4.7, "reviews": 341},
    {"id": "marsden_park", "name": "Pizzomania Marsden Park",
     "address": "3 Garfield Rd, Marsden Park NSW 2765", "lat": -33.7167, "lon": 150.8500,
     "rating": 4.7, "reviews": 276},
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
# DEALS (demo/informational only — not applied to pricing yet)
# ------------------------------------------------------------
DEALS = [
    {"icon": "🎉", "title": "Family Friday", "desc": "15% off any Family pizza, every Friday.", "code": "FAMFRI15", "image": None},
    {"icon": "🚚", "title": "Free delivery over $30", "desc": "Spend $30 or more and delivery is on us.", "code": None, "image": None},
    {"icon": "🧒", "title": "Kids Eat Happy", "desc": "A free juice box with every Kids pizza.", "code": "KIDSJUICE", "image": None},
    {"icon": "🔥", "title": "Mania Deal", "desc": "2 pizzas. $28. Pick any two pizzas from our Mania range.", "code": "MANIA28",
     "image": "/static/images/mania-deal.webp"},
]


# Demo-only server-side order registry. Replace with a database for production.
ORDERS_BY_NUMBER = {}

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
        headers = {"User-Agent": "PizzomaniaApp-Demo/1.0 (demo contact: pizza-demo@example.com)"}
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
    return "PM-" + "".join(random.choices(string.digits, k=6))


# ------------------------------------------------------------
# PIZZOMANIA AI — PHASE 1
# ------------------------------------------------------------
AGENT_MAX_ROUNDS = 4


def _normalise(s):
    return re.sub(r"[^a-z0-9 ]+", " ", str(s or "").lower()).strip()


def search_menu(query="", tags=None, max_price=None, max_cal=None):
    """Search the authoritative PIZZAS catalog using deterministic filters."""
    query_n = _normalise(query)
    tags = [str(t).strip().lower() for t in (tags or []) if str(t).strip()]
    results = []
    for p in PIZZAS:
        hay = _normalise(p["name"] + " " + p["description"] + " " + " ".join(p["tags"]))
        if query_n and not all(token in hay for token in query_n.split()):
            continue
        tag_hay = {t.lower() for t in p["tags"]}
        if tags and not all(t in tag_hay for t in tags):
            continue
        if max_price is not None and p["base_price"] > float(max_price):
            continue
        if max_cal is not None and p["base_cal"] > int(max_cal):
            continue
        results.append({
            "id": p["id"], "name": p["name"], "description": p["description"],
            "base_price": p["base_price"], "base_cal": p["base_cal"],
            "tags": p["tags"], "image": p["image"], "rating": p.get("rating"), "reviews": p.get("reviews")
        })
    results.sort(key=lambda x: (-float(x.get("rating") or 0), x["base_price"]))
    return {"matches": results[:8], "count": len(results)}


def build_pizza(pizza_id, size=None, crust=None, toppings=None, qty=1):
    """Validate an AI-proposed pizza and return authoritative price/calories."""
    pizza = PIZZA_BY_ID.get(pizza_id)
    if not pizza:
        return {"ok": False, "error": "Unknown pizza."}
    allowed_sizes = ALLOWED_SIZES[pizza["category"]]
    size = size if size in allowed_sizes else allowed_sizes[0]
    crust = crust if crust in [c["name"] for c in CRUSTS] else "Classic"
    valid_toppings = {t["name"] for t in TOPPINGS}
    toppings = [t for t in (toppings or []) if t in valid_toppings]
    try:
        qty = max(1, min(10, int(qty)))
    except Exception:
        qty = 1
    price, cal, pizza, crust_obj, topping_objs = calc_pizza_price_and_cal(pizza_id, size, crust, toppings)
    return {
        "ok": True,
        "pizza": {
            "id": pizza["id"], "name": pizza["name"], "description": pizza["description"],
            "image": pizza["image"], "size": size, "crust": crust_obj["name"],
            "toppings": [t["name"] for t in topping_objs], "qty": qty,
            "unit_price": price, "total_price": round(price * qty, 2), "calories": cal,
            "tags": pizza["tags"], "rating": pizza.get("rating"), "reviews": pizza.get("reviews")
        }
    }


def check_delivery_range(address):
    """Geocode an address and check the nearest Pizzomania kitchen."""
    results, fallback = geocode_address(address)
    if not results:
        results = DUMMY_ADDRESSES
        fallback = True
    chosen = results[0]
    store, distance_km = nearest_store(chosen["lat"], chosen["lon"])
    return {
        "ok": True, "address": chosen, "fallback": fallback,
        "store": {"id": store["id"], "name": store["name"], "address": store["address"]},
        "distance_km": distance_km, "can_deliver": distance_km <= MAX_DELIVERY_KM,
        "delivery_fee": 0.0 if distance_km <= MAX_DELIVERY_KM else None,
        "free_delivery_threshold": 30.0,
    }


TRACKER_STAGE_DEFS = [
    {"key": "placed", "label": "Order placed", "pct": 0.00},
    {"key": "prep", "label": "Preparing", "pct": 0.12},
    {"key": "bake", "label": "Baking", "pct": 0.42},
    {"key": "quality", "label": "Quality check", "pct": 0.72},
    {"key": "out", "label": "Out for delivery", "pct": 0.88},
    {"key": "done", "label": "Delivered", "pct": 1.00},
]

def _ensure_order_owner():
    """Return a stable per-session owner token for demo order privacy."""
    owner = session.get("order_owner_id")
    if not owner:
        owner = secrets.token_urlsafe(24)
        session["order_owner_id"] = owner
    return owner

def _order_status(order):
    placed = datetime.fromisoformat(order["placed_at"].replace("Z", "+00:00"))
    elapsed = max(0.0, (datetime.now(timezone.utc) - placed).total_seconds())
    eta_seconds = max(1, int(order.get("eta_minutes", 15)) * 60)
    fraction = min(1.0, elapsed / eta_seconds)
    idx = 0
    for i, stage in enumerate(TRACKER_STAGE_DEFS):
        if fraction >= stage["pct"]:
            idx = i
    fulfilment = order.get("fulfilment")
    labels = [x["label"] for x in TRACKER_STAGE_DEFS]
    labels[4] = "Ready for pickup" if fulfilment == "pickup" else "Out for delivery"
    labels[5] = "Picked up" if fulfilment == "pickup" else "Delivered"
    remaining = max(0, math.ceil((eta_seconds - elapsed) / 60))
    return {
        "stage_key": TRACKER_STAGE_DEFS[idx]["key"],
        "stage_index": idx,
        "status": labels[idx],
        "remaining_min": remaining,
        "stages": labels,
        "fraction": fraction,
    }

def get_order_for_session(order_number):
    order = ORDERS_BY_NUMBER.get(str(order_number).upper())
    if not order:
        return None, {"ok": False, "found": False, "error": "I couldn't find that order on this demo server."}
    owner = session.get("order_owner_id")
    if not owner or order.get("owner_id") != owner:
        return None, {"ok": False, "found": False, "error": "I can't access that order from this session."}
    return order, None

def check_order_status(order_number):
    order, error = get_order_for_session(order_number)
    if error:
        return error
    status = _order_status(order)
    return {"ok": True, "found": True, "order_number": order["order_number"], "status": status["status"],
            "stage_key": status["stage_key"], "eta_minutes": status["remaining_min"],
            "total": order["total"], "store": order["store"]["name"]}


def _agent_tools():
    return {
        "search_menu": search_menu,
        "build_pizza": build_pizza,
        "check_delivery_range": check_delivery_range,
        "check_order_status": check_order_status,
    }


def _tool_schemas():
    return [
        {"name": "search_menu", "description": "Search Pizzomania's authoritative menu. Use for preferences, dietary tags, price or calorie constraints.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}, "max_price": {"type": "number"}, "max_cal": {"type": "integer"}}, "required": []}},
        {"name": "build_pizza", "description": "Validate a pizza configuration and return the authoritative price and calories. Use only after selecting a real pizza.", "parameters": {"type": "object", "properties": {"pizza_id": {"type": "string"}, "size": {"type": "string"}, "crust": {"type": "string"}, "toppings": {"type": "array", "items": {"type": "string"}}, "qty": {"type": "integer"}}, "required": ["pizza_id"]}},
        {"name": "check_delivery_range", "description": "Check whether a delivery address is within 20km of the nearest Pizzomania kitchen.", "parameters": {"type": "object", "properties": {"address": {"type": "string"}}, "required": ["address"]}},
        {"name": "check_order_status", "description": "Look up a Pizzomania demo order by order number.", "parameters": {"type": "object", "properties": {"order_number": {"type": "string"}}, "required": ["order_number"]}},
    ]


def _fallback_agent(message):
    """Useful no-key demo mode. It never invents a price; all results come from tools."""
    text = _normalise(message)
    tools = _agent_tools()
    trace = []
    if re.search(r"\bpm[- ]?\d{6}\b", text):
        order_no = re.search(r"\bpm[- ]?\d{6}\b", text).group(0).upper().replace(" ", "-")
        result = tools["check_order_status"](order_no)
        trace.append({"label": "Checking your order", "tool": "check_order_status"})
        if result.get("found"):
            return {"reply": f"Your order {order_no} is currently **{result['status']}** at {result['store']}.", "suggestions": [], "trace": trace}
        return {"reply": result["error"], "suggestions": [], "trace": trace}

    max_price = None
    m = re.search(r"(?:under|below|less than|up to)\s*\$?\s*(\d+(?:\.\d+)?)", text)
    if m: max_price = float(m.group(1))
    max_cal = None
    m = re.search(r"(?:under|below|less than|up to)\s*(\d+)\s*(?:cal|calories)", text)
    if m: max_cal = int(m.group(1))
    tags=[]
    if "vegan" in text: tags.append("vegan")
    if "vegetarian" in text: tags.append("vegetarian")
    query = ""
    for token in ["spicy", "mushroom", "pepperoni", "chicken", "margherita", "veggie", "bbq", "falafel"]:
        if token in text: query = token; break
    result = tools["search_menu"](query=query, tags=tags, max_price=max_price, max_cal=max_cal)
    trace.append({"label": "Checking the menu", "tool": "search_menu"})
    matches = result["matches"]
    if not matches:
        return {"reply": "I couldn't find a pizza that fits all of those requirements. Try relaxing one constraint and I'll have another look.", "suggestions": [], "trace": trace}
    picks=[]
    for m in matches[:3]:
        built = tools["build_pizza"](m["id"])
        trace.append({"label": f"Checking {m['name']}", "tool": "build_pizza"})
        if built.get("ok"): picks.append(built["pizza"])
    best=picks[0]
    reason=[]
    if tags: reason.append("your dietary preference")
    if max_price is not None: reason.append(f"your ${max_price:.0f} budget")
    if max_cal is not None: reason.append(f"your {max_cal} calorie limit")
    why = " and ".join(reason) if reason else "what you described"
    return {"reply": f"I'd start with **{best['name']}** — it fits {why}. You can customize it before it reaches your cart.", "suggestions": picks, "trace": trace}


def _gemini_agent(message, history, context):
    from google.genai import types
    declarations=[]
    for schema in _tool_schemas():
        declarations.append(types.FunctionDeclaration(name=schema["name"], description=schema["description"], parameters_json_schema=schema["parameters"]))
    tool=types.Tool(function_declarations=declarations)
    system = ("You are Pizzomania AI, a concise pizza ordering co-pilot. Help the user build a pizza. "
              "Use tools for authoritative menu, configuration, delivery and order facts. Never invent products, toppings, prices, calories, delivery eligibility or order status. "
              "Do not reveal hidden reasoning or chain-of-thought. Return friendly concise answers. "
              "When a user wants a pizza, use search_menu then build_pizza to validate a concrete suggestion. "
              "A pizza proposal is only a suggestion until the user approves it.")
    contents=[]
    for turn in (history or [])[-8:]:
        role="model" if turn.get("role") in ("assistant","model") else "user"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=str(turn.get("content", "")))]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=f"Current context: {context or {}}\nUser: {message}")]))
    trace=[]; suggestions=[]
    for _ in range(AGENT_MAX_ROUNDS):
        response=_genai_client.models.generate_content(model="gemini-2.5-flash", contents=contents, config=types.GenerateContentConfig(tools=[tool], temperature=0.4, system_instruction=system))
        candidate=response.candidates[0]
        parts=candidate.content.parts
        calls=[part.function_call for part in parts if getattr(part, "function_call", None)]
        if not calls:
            text=(response.text or "").strip()
            return {"reply": text or "I can help you build a pizza.", "suggestions": suggestions, "trace": trace}
        contents.append(candidate.content)
        for call in calls:
            name=call.name; args=dict(call.args or {})
            fn=_agent_tools().get(name)
            if not fn:
                result={"ok":False,"error":"Unknown tool."}
            else:
                try: result=fn(**args)
                except Exception as exc: result={"ok":False,"error":str(exc)}
            trace.append({"label": {"search_menu":"Checking the menu","build_pizza":"Validating your pizza","check_delivery_range":"Checking delivery range","check_order_status":"Checking your order"}.get(name, "Checking"), "tool": name})
            if name=="build_pizza" and result.get("ok"): suggestions.append(result["pizza"])
            contents.append(types.Content(role="user", parts=[types.Part.from_function_response(name=name, response={"result": result})]))
    return {"reply":"I got a little stuck while building that. Try describing the pizza again in a simpler way.","suggestions":suggestions,"trace":trace}


@app.route("/api/agent/ask", methods=["POST"])
def api_agent_ask():
    data=request.get_json(force=True) or {}
    message=(data.get("message") or "").strip()
    if not message: return jsonify({"ok":False,"error":"Tell me what you're craving."}),400
    history=data.get("history") or []
    context=data.get("context") or {}
    try:
        if GEMINI_ENABLED and _genai_client is not None:
            result=_gemini_agent(message, history, context); mode="gemini"
        else:
            result=_fallback_agent(message); mode="deterministic"
        return jsonify({"ok":True,"mode":mode,**result})
    except Exception as exc:
        fallback=_fallback_agent(message)
        return jsonify({"ok":True,"mode":"deterministic-fallback","warning":str(exc),**fallback})

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


@app.route("/api/deals")
def api_deals():
    return jsonify({"deals": DEALS})


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


@app.route("/api/order/status", methods=["GET"])
def api_order_status():
    order_number = request.args.get("order_number", "").strip().upper()
    if not order_number:
        order_number = session.get("last_order_number", "")
    order, error = get_order_for_session(order_number)
    if error:
        return jsonify(error), 404
    status = _order_status(order)
    return jsonify({"ok": True, "order": order, "status": status})


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

        delivery_fee = 0.0 if fulfilment == "pickup" else (0.0 if subtotal >= 30 else 4.99 if can_fulfil else 0.0)
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
                "placed_at": datetime.now(timezone.utc).isoformat(),
                "owner_id": _ensure_order_owner(),
            }
            ORDERS_BY_NUMBER[order["order_number"]] = order
            session["last_order_number"] = order["order_number"]
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
