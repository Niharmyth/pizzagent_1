"""Static verification for the V12 runtime integration.

Run after applying scripts/apply_v12_runtime.py:
    python3 scripts/verify_v12_runtime.py
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
app = (root / "app.py").read_text(encoding="utf-8")
version = (root / "VERSION.json").read_text(encoding="utf-8")

checks = {
    "V12 metadata": '"version": "12.0.0"' in version,
    "runtime import": "from v12_runtime import gemini_model" in app,
    "Gemini 3.5 runtime default": 'GEMINI_MODEL = gemini_model()' in app,
    "evidence registry": "ORDER_EVIDENCE_BY_NUMBER = {}" in app,
    "evidence creation": "evidence_chain = new_evidence_chain()" in app,
    "server validation evidence": '"server_validation"' in app,
    "order-created evidence": '"order_created"' in app,
    "evidence endpoint": '/api/order/evidence' in app,
    "V11 spicy pizza retained": "Inferno Spicy Chicken" in app,
    "candidate grounding retained": "candidate_ids" in app,
}

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    raise SystemExit(f"V12 runtime verification failed: {', '.join(failed)}")
print("V12 runtime integration checks passed.")
