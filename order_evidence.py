"""V12 order evidence primitives.

This module provides a small append-only hash-chain abstraction for the demo.
It is intentionally independent of Flask/session storage so production storage
can later replace the in-memory list without changing the event format.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone


def _canonical(event: dict) -> str:
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def append_event(chain: list[dict], event_type: str, payload: dict, actor: str = "system") -> dict:
    previous_hash = chain[-1]["hash"] if chain else "GENESIS"
    event = {
        "sequence": len(chain) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "actor": actor,
        "payload": payload,
        "previous_hash": previous_hash,
    }
    event["hash"] = hashlib.sha256(_canonical(event).encode("utf-8")).hexdigest()
    chain.append(event)
    return event


def verify_chain(chain: list[dict]) -> dict:
    previous = "GENESIS"
    for index, event in enumerate(chain, start=1):
        if event.get("sequence") != index or event.get("previous_hash") != previous:
            return {"valid": False, "failed_sequence": index, "reason": "sequence or previous hash mismatch"}
        body = {k: v for k, v in event.items() if k != "hash"}
        expected = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
        if expected != event.get("hash"):
            return {"valid": False, "failed_sequence": index, "reason": "event hash mismatch"}
        previous = event["hash"]
    return {"valid": True, "events": len(chain), "head_hash": previous if chain else "GENESIS"}
