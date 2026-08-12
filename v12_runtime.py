"""V12 runtime integration helpers.

Keeps trust/observability wiring isolated so app.py can adopt it without
changing the existing order/evidence data model. Production storage can later
replace the in-memory chain.
"""
from __future__ import annotations

import os
from order_evidence import append_event, verify_chain

# V12 runtime default. GEMINI_MODEL remains an explicit deployment override.
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"


def gemini_model() -> str:
    return os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)


def new_evidence_chain() -> list[dict]:
    return []


def record_evidence(chain: list[dict], event_type: str, payload: dict, actor: str = "system") -> dict:
    return append_event(chain, event_type, payload, actor=actor)


def evidence_status(chain: list[dict]) -> dict:
    return verify_chain(chain)


ORDER_EVIDENCE_EVENTS = (
    "customer_request",
    "ai_recommendation",
    "customer_approval",
    "server_validation",
    "order_created",
    "kitchen_preparation",
    "quality_check",
    "dispatch",
    "delivery_completed",
)
