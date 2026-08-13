"""Apply the V12 catalog + order-evidence lifecycle wiring to app.py.

Run from the repository root on branch v12-ai-trust-observability:
    python3 scripts/apply_v12_catalog_and_evidence.py

The script is deliberately idempotent and refuses to proceed if expected
anchors are missing, so it cannot silently rewrite an unexpected app.py.
"""
from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

# 1) Import the expanded catalog.
old = "from rag import retrieve_context, rag_status\n"
new = old + "from menu_catalog import MENU_EXTRAS, MENU_BUNDLES, MENU_CATEGORIES, menu_search, extras_by_category\n"
if "from menu_catalog import" not in text:
    if old not in text:
        raise SystemExit("ABORT: expected rag import anchor not found")
    text = text.replace(old, new, 1)

# 2) Extend /api/menu while retaining all existing pizza fields.
old = '''@app.route("/api/menu")\ndef api_menu():\n    return jsonify({\n        "pizzas": PIZZAS,\n        "allowed_sizes": ALLOWED_SIZES,\n        "crusts": CRUSTS,\n        "toppings": TOPPINGS,\n        "size_price_step": SIZE_PRICE_STEP,\n    })\n'''
new = '''@app.route("/api/menu")\ndef api_menu():\n    return jsonify({\n        "pizzas": PIZZAS,\n        "extras": MENU_EXTRAS,\n        "bundles": MENU_BUNDLES,\n        "categories": MENU_CATEGORIES,\n        "allowed_sizes": ALLOWED_SIZES,\n        "crusts": CRUSTS,\n        "toppings": TOPPINGS,\n        "size_price_step": SIZE_PRICE_STEP,\n    })\n\n\n@app.route("/api/menu/search")\ndef api_menu_search():\n    query = request.args.get("q", "")\n    category = request.args.get("category", "all")\n    max_price_raw = request.args.get("max_price")\n    dietary_raw = request.args.get("dietary", "")\n    max_price = float(max_price_raw) if max_price_raw else None\n    dietary = [x.strip() for x in dietary_raw.split(",") if x.strip()]\n    return jsonify({\n        "ok": True,\n        "items": menu_search(query=query, category=category, max_price=max_price, dietary=dietary),\n        "category": category,\n    })\n'''
if "/api/menu/search" not in text:
    if old not in text:
        raise SystemExit("ABORT: expected /api/menu block not found")
    text = text.replace(old, new, 1)

# 3) Add evidence events when the real order status changes. This expects the
# existing in-memory evidence registry and evidence helper imports already
# installed by the earlier V12 runtime step.
old = '''@app.route("/api/order/status", methods=["GET", "POST"])\ndef api_order_status():\n'''
if old not in text:
    # Preserve existing implementation if its decorator differs; the script
    # should not guess.
    raise SystemExit("ABORT: expected api_order_status decorator not found; inspect app.py manually")

# Inject only once immediately after the function's status assignment. We use
# a stable anchor from the current V11 implementation.
anchor = '''    status = order_status_for_order(order)\n'''
if "record_evidence(evidence_chain, \"status_changed\"" not in text:
    if anchor not in text:
        raise SystemExit("ABORT: expected order status calculation anchor not found")
    replacement = '''    status = order_status_for_order(order)\n    # V12: append evidence only for real status observations; never fabricate\n    # future kitchen/delivery events at checkout.\n    evidence_chain = ORDER_EVIDENCE_BY_NUMBER.get(order_number)\n    if evidence_chain is not None:\n        last_status = order.get("_evidence_last_status")\n        if status != last_status:\n            record_evidence(evidence_chain, "status_changed", {\n                "order_number": order_number,\n                "status": status,\n            }, actor="order-status")\n            order["_evidence_last_status"] = status\n'''
    text = text.replace(anchor, replacement, 1)

APP.write_text(text, encoding="utf-8")
print("Applied V12 catalog + evidence lifecycle wiring to app.py")
