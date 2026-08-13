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

import json
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
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from rag import retrieve_context, rag_status
from v12_runtime import gemini_model, new_evidence_chain, record_evidence, evidence_status
from menu_catalog import MENU_EXTRAS, MENU_BUNDLES, MENU_CATEGORIES, menu_search

# ============================================================
# HAND-EDITABLE CONSTANTS
# ============================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
GEMINI_MODEL = gemini_model()
GEMINI_INIT_ERROR = None
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
    except Exception as exc:
        GEMINI_ENABLED = False
        _genai_client = None
        GEMINI_INIT_ERROR = str(exc)

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
    {"id": "s5", "category": "single", "name": "Inferno Spicy Chicken",
     "description": "Chargrilled chicken, jalapenos, roasted capsicum, red onion and mozzarella with a smoky spicy base.",
     "base_price": 16.90, "base_cal": 690, "tags": ["Spicy"],
     "image": "/static/images/pizzas/inferno.webp",
     "rating": 4.8, "reviews": 241},
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
ORDER_EVIDENCE_BY_NUMBER = {}
AGENT_EVENTS = []

def record_agent_event(agent, event, detail, tool=None):
    AGENT_EVENTS.append({"time": datetime.now(timezone.utc).isoformat(), "agent": agent, "event": event, "detail": detail, "tool": tool})
    del AGENT_EVENTS[:-100]

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
            interaction = _genai_client.interactions.create(
                model=GEMINI_MODEL,
                input=prompt_text,
                system_instruction=(
                    "You are the Pizzomania delivery assistant. Return only a short, warm, "
                    "plain-language confirmation. Never invent delivery eligibility, prices, "
                    "distances or store facts; use only the facts provided in the user input."
                ),
                store=False,
            )
            text = (getattr(interaction, "output_text", "") or "").strip()
            if text:
                record_agent_event("Delivery Agent", "LLM response", "Gemini Interactions API generated the delivery/pickup message.")
                return text, "gemini-interactions"
        except Exception as exc:
            record_agent_event("Delivery Agent", "LLM fallback", f"Gemini Interactions API failed; deterministic message used: {exc}")

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
    return msg, ("deterministic-no-key" if not GEMINI_ENABLED else "deterministic-gemini-error")


def make_order_number():
    return "PM-" + "".join(random.choices(string.digits, k=6))


# ------------------------------------------------------------
# PIZZOMANIA AI — PHASE 1
# ------------------------------------------------------------
AGENT_MAX_ROUNDS = 3
AGENT_REQUEST_TIMEOUT_SECONDS = 30


def _normalise(s):
    return re.sub(r"[^a-z0-9 ]+", " ", str(s or "").lower()).strip()


def search_menu(query="", tags=None, max_price=None, max_cal=None):
    """Search the authoritative Pizzomania catalog across pizzas and non-pizza items."""
    query_n = _normalise(query)
    tags = [str(t).strip().lower() for t in (tags or []) if str(t).strip()]
    tokens = query_n.split()
    results = []

    synonyms = {
        "spicy": ["spicy", "jalapeno", "jalapenos", "hot", "inferno", "chili", "fiery"],
        "hot": ["spicy", "jalapeno", "jalapenos", "hot", "inferno", "chili", "fiery"],
        "cheesy": ["cheese", "mozzarella"],
        "cheese": ["cheese", "mozzarella"],
        "loaded": ["loaded", "supreme", "bbq"],
        "healthy": ["healthy", "light", "lean"],
        "veggie": ["veggie", "vegetarian", "vegan", "vegetable"],
        "vegetarian": ["vegetarian"],
        "vegan": ["vegan"],
        "kids": ["kids"],
        "family": ["family"],
    }

    # ------------------------------------------------------------
    # PIZZAS — preserve the existing authoritative behavior
    # ------------------------------------------------------------
    for p in PIZZAS:
        hay = _normalise(
            p["name"] + " " + p["description"] + " " + " ".join(p["tags"])
        )
        tag_hay = {t.lower() for t in p["tags"]}

        if tags and not all(t in tag_hay for t in tags):
            continue
        if max_price is not None and p["base_price"] > float(max_price):
            continue
        if max_cal is not None and p["base_cal"] > int(max_cal):
            continue

        score = 0.0

        for token in tokens:
            if token in hay:
                score += 4.0
            elif any(term in hay for term in synonyms.get(token, [])):
                score += 3.0

        if tokens and score <= 0:
            continue

        score += float(p.get("rating") or 0) * 0.15

        results.append({
            "id": p["id"],
            "item_type": "pizza",
            "category": p["category"],
            "name": p["name"],
            "description": p["description"],
            "base_price": p["base_price"],
            "base_cal": p["base_cal"],
            "price": p["base_price"],
            "calories": p["base_cal"],
            "tags": p["tags"],
            "dietary": p.get("dietary", []),
            "image": p["image"],
            "rating": p.get("rating"),
            "reviews": p.get("reviews"),
            "_score": score,
        })

    # ------------------------------------------------------------
    # NON-PIZZA — delegate to the authoritative V12 catalog
    # ------------------------------------------------------------
    category = "all"

    if any(t in tokens for t in ("drink", "drinks")):
        category = "drinks"
    elif any(t in tokens for t in ("snack", "snacks", "side", "sides")):
        category = "sides"
    elif any(t in tokens for t in ("dip", "dips")):
        category = "dips"
    elif any(t in tokens for t in ("dessert", "desserts", "sweet")):
        category = "desserts"

    dietary = []

    if "vegan" in tokens:
        dietary.append("vegan")
    elif "vegetarian" in tokens or "veggie" in tokens:
        dietary.append("vegetarian")

    # Remove category words from the search phrase so the catalog
    # search focuses on the actual product intent.
    catalog_tokens = [
        t for t in tokens
        if t not in {
            "drink", "drinks",
            "snack", "snacks",
            "side", "sides",
            "dip", "dips",
            "dessert", "desserts",
            "sweet",
            "vegan", "vegetarian", "veggie",
        }
    ]

    catalog_query = " ".join(catalog_tokens)

    # Preserve useful semantic synonyms for the catalog search.
    if "spicy" in catalog_tokens or "hot" in catalog_tokens:
        catalog_query += " spicy"
    if "cheesy" in catalog_tokens or "cheese" in catalog_tokens:
        catalog_query += " cheese"
    if "loaded" in catalog_tokens:
        catalog_query += " loaded"

    extras = menu_search(
        query=catalog_query.strip(),
        category=category,
        max_price=max_price,
        dietary=dietary,
    )

    for item in extras:
        results.append({
            "id": item["id"],
            "item_type": "menu_item",
            "category": item["category"],
            "name": item["name"],
            "description": item["description"],
            "price": item["price"],
            "calories": item["calories"],
            "tags": item.get("tags", []),
            "dietary": item.get("dietary", []),
            "image": item.get("image"),
            "_score": 2.0,
        })

    # Explicit non-pizza intent should outrank unrelated pizza results.
    if category != "all":
        results = [
            item for item in results
            if item["item_type"] == "menu_item"
        ]

    results.sort(
        key=lambda x: (
            -x["_score"],
            -float(x.get("rating") or 0),
            float(x.get("price") or x.get("base_price") or 0),
        )
    )

    for item in results:
        item.pop("_score", None)

    return {
        "matches": results[:8],
        "count": len(results),
    }


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


def _fallback_agent(message, history=None, context=None):
    """Useful no-key demo mode. Parses common intent instead of returning a fixed default."""
    text = _normalise(message)
    tools = _agent_tools()
    trace = []
    record_agent_event("Pizza AI", "Fallback analysis", f"Parsed user request: {message}")

    if re.search(r"\bpm[- ]?\d{6}\b", text):
        order_no = re.search(r"\bpm[- ]?\d{6}\b", text).group(0).upper().replace(" ", "-")
        result = tools["check_order_status"](order_no)
        trace.append({"label": "Checking your order", "tool": "check_order_status"})
        record_agent_event("Order Agent", "Order lookup", order_no, "check_order_status")
        if result.get("found"):
            return {"reply": f"Your order {order_no} is currently **{result['status']}** at {result['store']}.", "suggestions": [], "trace": trace}
        return {"reply": result["error"], "suggestions": [], "trace": trace}

    last_proposal=(context or {}).get("lastProposal") or {}
    if last_proposal and any(x in text for x in ("spicier", "more spicy", "hotter", "extra cheese", "more cheese", "remove mushroom", "without mushroom", "no mushroom")):
        toppings=list(last_proposal.get("toppings") or [])
        if any(x in text for x in ("spicier", "more spicy", "hotter")) and "Jalapenos" not in toppings:
            toppings.append("Jalapenos")
        if any(x in text for x in ("extra cheese", "more cheese")) and "Extra Vegan Cheese" not in toppings:
            toppings.append("Extra Vegan Cheese")
        if any(x in text for x in ("remove mushroom", "without mushroom", "no mushroom")):
            toppings=[t for t in toppings if t != "Mushroom"]
        built=tools["build_pizza"](last_proposal.get("id"), size=last_proposal.get("size"), crust=last_proposal.get("crust"), toppings=toppings, qty=last_proposal.get("qty",1))
        trace.append({"label":"Updating your pizza","tool":"build_pizza"})
        if built.get("ok"):
            p=built["pizza"]
            record_agent_event("Pizza Builder", "Follow-up modification", p["name"], "build_pizza")
            return {"reply":f"Done — I updated **{p['name']}** based on your last pizza. You can review the new configuration below.","suggestions":[p],"trace":trace}

    max_price = None
    m = re.search(r"(?:under|below|less than|up to|budget(?: of)?)\s*\$?\s*(\d+(?:\.\d+)?)", text)
    if m: max_price = float(m.group(1))
    max_cal = None
    m = re.search(r"(?:under|below|less than|up to)\s*(\d+)\s*(?:cal|calories)", text)
    if m: max_cal = int(m.group(1))

    tags=[]
    if "vegan" in text: tags.append("vegan")
    elif "vegetarian" in text or "veggie" in text: tags.append("vegetarian")

    # Map conversational intent to menu terms.
    intent_terms = [
        ("spicy", "spicy"), ("hot", "spicy"), ("inferno", "inferno"),
        ("pepperoni", "pepperoni"), ("mushroom", "mushroom"),
        ("chicken", "chicken"), ("bbq", "bbq"), ("barbecue", "bbq"),
        ("margherita", "margherita"), ("falafel", "falafel"),
        ("cheesy", ""), ("cheese", ""), ("loaded", "supreme"),
    ]
    query = next((term for word, term in intent_terms if word in text), "")

    # Search broadly when the natural-language query is descriptive rather than a product name.
    result = tools["search_menu"](query=query, tags=tags, max_price=max_price, max_cal=max_cal)
    trace.append({"label": "Checking the menu", "tool": "search_menu"})
    record_agent_event("Menu Agent", "Menu search", f"Found {result['count']} matching menu items.", "search_menu")

    matches = result["matches"]
    if "kids" in text or "children" in text:
        kids = [m for m in matches if m.get("category") == "kids"]
        if kids: matches = kids
    elif "family" in text or "group" in text or "party" in text:
        family = [m for m in matches if m.get("category") == "family"]
        if family: matches = family
    if not matches and query:
        result = tools["search_menu"](query="", tags=tags, max_price=max_price, max_cal=max_cal)
        matches = result["matches"]
    if not matches:
        return {"reply": "I couldn't find a pizza that fits all of those requirements. Try relaxing one constraint and I'll have another look.", "suggestions": [], "trace": trace}

    # Score candidates against conversational cues so the fallback is not always the first menu item.
    def score(m):
        hay=_normalise(m["name"]+" "+m["description"]+" "+" ".join(m["tags"]))
        score=float(m.get("rating") or 0)
        for word in text.split():
            if len(word)>3 and word in hay: score += 1.5
        if "spicy" in text and "spicy" in hay: score += 5
        if "cheesy" in text and "cheese" in hay: score += 2
        if "loaded" in text and any(x in hay for x in ("supreme","loaded","bbq")): score += 4
        return score
    matches=sorted(matches,key=score,reverse=True)[:3]

    picks=[]
    requested_size = "Large" if "large" in text else None
    requested_crust = "Thin & Crispy" if "thin" in text else ("Cauliflower (Gluten-Free)" if "gluten" in text or "gluten free" in text else "Classic")
    topping_map={
        "extra cheese":"Extra Vegan Cheese", "mushroom":"Mushroom", "mushrooms":"Mushroom",
        "spinach":"Baby Spinach", "olives":"Kalamata Olives", "jalapeno":"Jalapenos",
        "jalapenos":"Jalapenos", "basil":"Fresh Basil", "pineapple":"Pineapple",
        "pepperoni":"Pepperoni", "chicken":"Chargrilled Chicken",
    }
    requested_toppings=[]
    for phrase,topping in topping_map.items():
        if phrase in text and topping not in requested_toppings: requested_toppings.append(topping)
    for m in matches:
        built=tools["build_pizza"](m["id"], size=requested_size, crust=requested_crust, toppings=requested_toppings)
        trace.append({"label": f"Validating {m['name']}", "tool":"build_pizza"})
        record_agent_event("Pizza Builder", "Configuration validated", m["name"], "build_pizza")
        if built.get("ok"): picks.append(built["pizza"])
    if not picks:
        return {"reply":"I found menu matches, but couldn't validate a configuration. Try another request.","suggestions":[],"trace":trace}

    best=picks[0]
    reason=[]
    if tags: reason.append("your dietary preference")
    if max_price is not None: reason.append(f"your ${max_price:.0f} budget")
    if max_cal is not None: reason.append(f"your {max_cal} calorie limit")
    if "spicy" in text: reason.append("your spicy craving")
    if "cheesy" in text: reason.append("your cheesy craving")
    why=" and ".join(reason) if reason else "what you described"
    return {"reply":f"I'd start with **{best['name']}** — it fits {why}. You can customize it before it reaches your cart.","suggestions":picks,"trace":trace}


def _gemini_tool_declarations():
    """Return Interactions API function declarations in the current schema."""
    return [
        {
            "type": "function",
            "name": schema["name"],
            "description": schema["description"],
            "parameters": schema["parameters"],
        }
        for schema in _tool_schemas()
    ]


def _interaction_text(interaction):
    return (getattr(interaction, "output_text", "") or "").strip()


def _interaction_steps(interaction):
    return list(getattr(interaction, "steps", None) or [])


def _gemini_agent(message, history, context, interaction_id=None):
    """Run Pizzomania AI through Interactions API with bounded, fail-safe tool use."""
    rag = retrieve_context(message, top_k=4)
    record_agent_event(
        "Pizza AI",
        "RAG retrieval",
        f"Retrieved {len(rag['chunks'])} knowledge chunks.",
    )

    system = (
        "You are Pizzomania AI, a concise pizza ordering co-pilot. Help the user build "
        "a pizza and complete ordering tasks. Use tools for authoritative menu, "
        "configuration, delivery and order facts. Never invent products, toppings, "
        "prices, calories, delivery eligibility or order status. Do not reveal hidden "
        "reasoning or chain-of-thought. Return friendly concise answers. "
        "When a user wants a pizza, use search_menu first. If search_menu returns zero "
        "matches, do NOT call build_pizza. Only call build_pizza using a pizza_id returned "
        "by the latest search_menu call. Never invent a pizza_id or repeatedly build "
        "unrelated/default pizzas. A pizza proposal is only a suggestion until the user "
        "approves it. Use retrieved knowledge only as supporting context; authoritative "
        "menu/pricing/order facts come from tools. After you receive a successful "
        "build_pizza result, stop calling tools and provide the user with a concise "
        "recommendation. For follow-up changes, modify the current proposal and then "
        "stop after the successful validation.\n\n"
        f"RETRIEVED KNOWLEDGE:\n{rag['context']}\n\n"
        f"CURRENT APP CONTEXT:\n{context or {}}"
    )

    tool_declarations = _gemini_tool_declarations()
    trace = []
    suggestions = []
    last_built = None
    candidate_ids = set()

    def create_turn(input_value, previous_id=None, tools=None, prompt_system=system):
        kwargs = {
            "model": GEMINI_MODEL,
            "input": input_value,
            "system_instruction": prompt_system,
            "store": True,
        }
        if previous_id:
            kwargs["previous_interaction_id"] = previous_id
        if tools is not None:
            kwargs["tools"] = tools
        return _genai_client.interactions.create(**kwargs)

    # Follow-ups modify the existing proposal instead of starting a new search.
    last_proposal = (context or {}).get("lastProposal") or {}

    if interaction_id and last_proposal.get("id"):
        pizza_id = str(last_proposal["id"])
        candidate_ids.add(pizza_id)

        followup_system = system + (
            "\n\nFOLLOW-UP MODE: The user is modifying the previously validated pizza. "
            f"The current pizza_id is {pizza_id}. "
            f"The current pizza is {last_proposal.get('name', 'the previous pizza')}, "
            f"size {last_proposal.get('size', 'current size')}, "
            f"crust {last_proposal.get('crust', 'current crust')}, "
            f"with toppings {last_proposal.get('toppings', [])}. "
            "Do not call search_menu. Modify this existing pizza using build_pizza only. "
            "Preserve the existing size, crust, quantity and toppings unless the user "
            "explicitly changes them. Add requested toppings rather than replacing "
            "existing toppings."
        )

        followup_tools = [
            d for d in tool_declarations
            if d.get("name") == "build_pizza"
        ]

        interaction = create_turn(
            message,
            previous_id=interaction_id,
            tools=followup_tools,
            prompt_system=followup_system,
        )

    elif interaction_id:
        interaction = create_turn(
            message,
            previous_id=interaction_id,
            tools=tool_declarations,
        )

    else:
        history_text = ""
        if history:
            compact = history[-8:]
            history_text = "\nCONVERSATION SO FAR:\n" + "\n".join(
                f"{t.get('role', 'user').upper()}: {t.get('content', '')}"
                for t in compact
            )

        prompt = f"{history_text}\n\nUSER:\n{message}".strip()
        interaction = create_turn(
            prompt,
            tools=tool_declarations,
        )

    for round_no in range(AGENT_MAX_ROUNDS):
        calls = [
            step
            for step in _interaction_steps(interaction)
            if getattr(step, "type", None) == "function_call"
        ]

        if not calls:
            text = _interaction_text(interaction)
            if last_built and not suggestions:
                suggestions.append(last_built)
            return {
                "reply": text or "I can help you build a pizza.",
                "suggestions": suggestions,
                "trace": trace,
                "interaction_id": getattr(interaction, "id", None),
            }

        function_results = []

        for call in calls:
            name = getattr(call, "name", "")
            args = getattr(call, "arguments", {}) or {}
            fn = _agent_tools().get(name)

            if not fn:
                result = {"ok": False, "error": "Unknown tool."}
            elif (
                name == "build_pizza"
                and str(args.get("pizza_id")) not in candidate_ids
            ):
                result = {
                    "ok": False,
                    "error": (
                        "That pizza was not returned by the latest menu search. "
                        "Call search_menu first and use a returned pizza_id."
                    ),
                }
            else:
                try:
                    result = fn(**dict(args))
                except Exception as exc:
                    result = {"ok": False, "error": str(exc)}

            if name == "search_menu":
                candidate_ids = {
                    str(item["id"])
                    for item in result.get("matches", [])
                }

            trace.append({
                "label": {
                    "search_menu": "Checking the menu",
                    "build_pizza": "Validating your pizza",
                    "check_delivery_range": "Checking delivery range",
                    "check_order_status": "Checking your order",
                }.get(name, "Checking"),
                "tool": name,
            })

            record_agent_event(
                {
                    "search_menu": "Menu Agent",
                    "build_pizza": "Pizza Builder",
                    "check_delivery_range": "Delivery Agent",
                    "check_order_status": "Order Agent",
                }.get(name, "Pizza AI"),
                "Tool call",
                f"{name} executed.",
                name,
            )

            if name == "build_pizza" and result.get("ok"):
                last_built = result["pizza"]
                suggestions.append(last_built)

            function_results.append({
                "type": "function_result",
                "name": name,
                "call_id": getattr(call, "id", None),
                "result": [
                    {
                        "type": "text",
                        "text": json.dumps(result),
                    }
                ],
            })

        if last_built:
            final_system = (
                system
                + "\nA validated pizza is already available. Do not call any tools. "
                "Summarize the updated pizza and invite the user to customize it "
                "further or add it to cart."
            )
            interaction = create_turn(
                function_results,
                previous_id=getattr(interaction, "id", None),
                tools=[],
                prompt_system=final_system,
            )
        else:
            interaction = create_turn(
                function_results,
                previous_id=getattr(interaction, "id", None),
                tools=tool_declarations,
            )

    if last_built:
        p = last_built
        return {
            "reply": (
                f"I found a match: **{p['name']}** at "
                f"**${p['total_price']:.2f}**. You can review and customize it "
                "below before adding it to your cart."
            ),
            "suggestions": [last_built],
            "trace": trace,
            "interaction_id": getattr(interaction, "id", None),
        }

    return {
        "reply": (
            "I couldn't complete that request quickly enough. Try a shorter "
            "request such as ‘spicy under $18’ and I'll build it for you."
        ),
        "suggestions": [],
        "trace": trace,
        "interaction_id": getattr(interaction, "id", None),
    }


@app.route("/api/agent/ask", methods=["POST"])
def api_agent_ask():
    data=request.get_json(force=True) or {}
    message=(data.get("message") or "").strip()
    if not message: return jsonify({"ok":False,"error":"Tell me what you're craving."}),400
    history=data.get("history") or []
    context=data.get("context") or {}
    interaction_id=(data.get("interaction_id") or "").strip() or None
    try:
        if GEMINI_ENABLED and _genai_client is not None:
            result=_gemini_agent(message, history, context, interaction_id); mode="gemini-interactions"
        else:
            result=_fallback_agent(message, history, context); mode=("deterministic-no-key" if not GEMINI_ENABLED else "deterministic-gemini-error")
        return jsonify({"ok":True,"mode":mode,**result})
    except Exception as exc:
        fallback=_fallback_agent(message, history, context)
        return jsonify({"ok":True,"mode":"deterministic-fallback","warning":str(exc),**fallback})

# ------------------------------------------------------------
# ROUTES
# ------------------------------------------------------------
@app.route("/agent-flow", methods=["GET"])
def agent_flow_page():
    return render_template("agent_flow.html", agent_name=AGENT_NAME)

@app.route("/admin", methods=["GET"])
def admin_page():
    return render_template("admin.html", agent_name=AGENT_NAME)

@app.route("/api/ai/status", methods=["GET"])
def api_ai_status():
    return jsonify({
        "ok": True, "gemini_configured": bool(GEMINI_API_KEY), "gemini_enabled": GEMINI_ENABLED,
        "model": GEMINI_MODEL, "api": "Interactions API", "sdk_loaded": _genai_client is not None,
        "init_error": GEMINI_INIT_ERROR, "rag": rag_status(),
    })

@app.route("/api/admin/overview", methods=["GET"])
def api_admin_overview():
    return jsonify({
        "ok": True,
        "agents": [
            {"id":"pizza_ai","name":"Pizzomania AI","role":"Intent + conversation orchestration","status":"active"},
            {"id":"menu_agent","name":"Menu Agent","role":"Searches authoritative menu and dietary/price constraints","tools":["search_menu"]},
            {"id":"pizza_builder","name":"Pizza Builder","role":"Builds and server-validates pizza configurations","tools":["build_pizza"]},
            {"id":"delivery_agent","name":"Delivery Agent","role":"Checks address, nearest kitchen and delivery eligibility","tools":["check_delivery_range"]},
            {"id":"order_agent","name":"Order Agent","role":"Tracks session-owned orders and order status","tools":["check_order_status"]},
            {"id":"rag_agent","name":"Knowledge / RAG","role":"Retrieves supporting Pizzomania knowledge before generation","tools":["retrieve_context"]},
            {"id":"kitchen","name":"Kitchen Flow","role":"Drives the preparation/status visualization","tools":["_order_status"]},
        ],
        "events": list(reversed(AGENT_EVENTS[-40:])),
        "ai": {"gemini_configured":bool(GEMINI_API_KEY),"gemini_enabled":GEMINI_ENABLED,"model":GEMINI_MODEL,"api":"Interactions API","init_error":GEMINI_INIT_ERROR},
        "rag": rag_status(),
    })

@app.route("/")
def index():
    return render_template("index.html", agent_name=AGENT_NAME, hero_image=HERO_IMAGE)


@app.route("/api/menu")
def api_menu():
    return jsonify({
        "pizzas": PIZZAS,
        "extras": MENU_EXTRAS,
        "bundles": MENU_BUNDLES,
        "categories": MENU_CATEGORIES,
        "allowed_sizes": ALLOWED_SIZES,
        "crusts": CRUSTS,
        "toppings": TOPPINGS,
        "size_price_step": SIZE_PRICE_STEP,
    })


@app.route("/api/menu/search")
def api_menu_search():
    query = (request.args.get("query") or "").strip()
    category = (request.args.get("category") or "all").strip().lower()
    max_price_raw = request.args.get("max_price")
    dietary_raw = request.args.get("dietary") or ""

    max_price = None
    if max_price_raw:
        try:
            max_price = float(max_price_raw)
        except ValueError:
            return jsonify({"ok": False, "error": "max_price must be numeric"}), 400

    dietary = [x.strip() for x in dietary_raw.split(",") if x.strip()]

    return jsonify({
        "ok": True,
        "query": query,
        "category": category,
        "results": menu_search(
            query=query,
            category=category,
            max_price=max_price,
            dietary=dietary,
        ),
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


@app.route("/api/address/autocomplete", methods=["GET"])
def api_address_autocomplete():
    query=(request.args.get("q") or "").strip()
    if len(query)<3:
        return jsonify({"ok":True,"results":[]})
    results, used_fallback=geocode_address(query)
    return jsonify({"ok":True,"fallback":used_fallback,"results":results[:5]})

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
    stage_key = status["stage_key"]

    chain = ORDER_EVIDENCE_BY_NUMBER.get(order_number, [])

    status_events = {
        "prep": ("kitchen_preparation", "kitchen"),
        "bake": ("kitchen_preparation", "kitchen"),
        "quality": ("quality_check", "quality-control"),
        "out": (
            "dispatch",
            "pickup-agent" if order.get("fulfilment") == "pickup" else "delivery-agent",
        ),
        "done": (
            "order_completed"
            if order.get("fulfilment") == "pickup"
            else "delivery_completed",
            "pickup-agent"
            if order.get("fulfilment") == "pickup"
            else "delivery-agent",
        ),
    }

    event_info = status_events.get(stage_key)

    if event_info:
        event_type, actor = event_info

        if not any(event.get("type") == event_type for event in chain):
            record_evidence(
                chain,
                event_type,
                {
                    "order_number": order_number,
                    "stage_key": stage_key,
                    "status": status["status"],
                },
                actor=actor,
            )

    return jsonify({
        "ok": True,
        "order": order,
        "status": status,
        "evidence": evidence_status(chain),
    })


@app.route("/api/order/evidence", methods=["GET"])
def api_order_evidence():
    order_number = request.args.get("order_number", "").strip().upper() or session.get("last_order_number", "")
    order, error = get_order_for_session(order_number)
    if error:
        return jsonify(error), 404
    chain = ORDER_EVIDENCE_BY_NUMBER.get(order_number, [])
    return jsonify({"ok": True, "order_number": order_number, "events": chain, "integrity": evidence_status(chain)})


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
        record_agent_event("Order Agent", "Order planning", f"{fulfilment} order with subtotal ${subtotal:.2f}.")
        if fulfilment == "pickup":
            store = next((s for s in STORES if s["id"] == store_id), None)
            if store is None:
                return jsonify({"ok": False, "error": "Please choose a store."}), 400
            distance_km = 0.0
            can_fulfil = True
            record_agent_event("Delivery Agent", "Kitchen lookup", f"Nearest kitchen {store['name']} at {distance_km}km.", "check_delivery_range")
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
                f"Sent the order summary, nearest kitchen and distance to the language model "
                f"({'live Gemini call' if mode == 'gemini' else 'deterministic fallback — Gemini is not configured' if mode == 'deterministic-no-key' else 'deterministic fallback — Gemini call failed; see Admin for diagnostics'}) "
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
            evidence_chain = new_evidence_chain()
            record_evidence(evidence_chain, "customer_request", {"order_number": order["order_number"], "items": cart_summary}, actor="customer")
            record_evidence(evidence_chain, "server_validation", {"order_number": order["order_number"], "items": order["items"], "total": total}, actor="server")
            record_evidence(evidence_chain, "order_created", {"order_number": order["order_number"], "store": store["name"], "fulfilment": fulfilment}, actor="order-agent")
            ORDER_EVIDENCE_BY_NUMBER[order["order_number"]] = evidence_chain
            record_agent_event("Kitchen", "Order created", f"{order['order_number']} routed to {store['name']}.")
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
