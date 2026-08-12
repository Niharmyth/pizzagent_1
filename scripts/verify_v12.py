"""Small dependency-free V12 verification script."""
import json
from pathlib import Path

from order_evidence import append_event, verify_chain
from rag import rag_status, retrieve_context

ROOT = Path(__file__).resolve().parents[1]
version = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))
assert version["version"] == "12.0.0"
assert version["baseline_commit"] == "45216f9c866d81353105479dbffb5430f25f48e6"

result = retrieve_context("Is delivery free for orders over 30 dollars?", top_k=4)
assert result["chunks"], "Expected at least one RAG result"
metrics = rag_status()["evaluation"]
assert metrics["cases"] >= 1
assert 0 <= metrics["mrr"] <= 1
assert 0 <= metrics["recall_at_5"] <= 1
assert 0 <= metrics["precision_at_5"] <= 1

chain = []
append_event(chain, "CUSTOMER_REQUEST", {"text": "vegetarian pizza"}, "customer")
append_event(chain, "SERVER_VALIDATION", {"dietary": "vegetarian"}, "server")
assert verify_chain(chain)["valid"]

print("V12 verification passed")
print(json.dumps({"version": version["version"], "rag": metrics, "evidence": verify_chain(chain)}, indent=2))
