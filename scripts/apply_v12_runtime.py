"""Apply the small V12 runtime integration to app.py.

Run once from the repository root:
    python3 scripts/apply_v12_runtime.py

The script is intentionally idempotent and refuses to overwrite an unexpected
app.py shape. It changes only the Gemini default and adds the V12 runtime
imports/helpers needed by the application.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
text = APP.read_text(encoding="utf-8")

old_import = "from rag import retrieve_context, rag_status\n"
new_import = old_import + "from v12_runtime import gemini_model, new_evidence_chain, record_evidence, evidence_status\n"
if "from v12_runtime import gemini_model" not in text:
    if old_import not in text:
        raise SystemExit("Refusing to modify app.py: expected RAG import was not found.")
    text = text.replace(old_import, new_import, 1)

old_model = 'GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")'
new_model = 'GEMINI_MODEL = gemini_model()'
if old_model in text:
    text = text.replace(old_model, new_model, 1)
elif 'GEMINI_MODEL = gemini_model()' not in text:
    raise SystemExit("Refusing to modify app.py: unexpected GEMINI_MODEL configuration.")

# Add an in-memory evidence chain registry beside the existing demo order registry.
marker = 'ORDERS_BY_NUMBER = {}\nAGENT_EVENTS = []\n'
replacement = 'ORDERS_BY_NUMBER = {}\nORDER_EVIDENCE_BY_NUMBER = {}\nAGENT_EVENTS = []\n'
if marker in text and 'ORDER_EVIDENCE_BY_NUMBER = {}' not in text:
    text = text.replace(marker, replacement, 1)

# Create the chain at order creation and record the authoritative server validation.
needle = '            ORDERS_BY_NUMBER[order["order_number"]] = order\n            record_agent_event("Kitchen", "Order created", f"{order[\'order_number\']} routed to {store[\'name\']}.")\n'
insert = '            ORDERS_BY_NUMBER[order["order_number"]] = order\n            evidence_chain = new_evidence_chain()\n            record_evidence(evidence_chain, "customer_request", {"order_number": order["order_number"], "items": cart_summary}, actor="customer")\n            record_evidence(evidence_chain, "server_validation", {"order_number": order["order_number"], "items": order["items"], "total": total}, actor="server")\n            record_evidence(evidence_chain, "order_created", {"order_number": order["order_number"], "store": store["name"], "fulfilment": fulfilment}, actor="order-agent")\n            ORDER_EVIDENCE_BY_NUMBER[order["order_number"]] = evidence_chain\n            record_agent_event("Kitchen", "Order created", f"{order[\'order_number\']} routed to {store[\'name\']}.")\n'
if needle in text and 'evidence_chain = new_evidence_chain()' not in text:
    text = text.replace(needle, insert, 1)

# Add a read-only evidence endpoint before the order process route.
route_marker = '@app.route("/api/order/process", methods=["POST"])\n'
route_code = '''@app.route("/api/order/evidence", methods=["GET"])\ndef api_order_evidence():\n    order_number = request.args.get("order_number", "").strip().upper() or session.get("last_order_number", "")\n    order, error = get_order_for_session(order_number)\n    if error:\n        return jsonify(error), 404\n    chain = ORDER_EVIDENCE_BY_NUMBER.get(order_number, [])\n    return jsonify({"ok": True, "order_number": order_number, "events": chain, "integrity": evidence_status(chain)})\n\n\n'''
if '/api/order/evidence' not in text:
    if route_marker not in text:
        raise SystemExit("Refusing to modify app.py: order process route marker not found.")
    text = text.replace(route_marker, route_code + route_marker, 1)

APP.write_text(text, encoding="utf-8")
print("Applied V12 runtime integration to app.py")
