"""Order evidence lifecycle helpers for Pizzomania V12.

The helpers deliberately record only events that the application can actually
observe. They do not invent kitchen or delivery events. Call the corresponding
function when the real/demo order state transitions occur.
"""

from datetime import datetime, timezone


def _event(chain, event_type, payload, actor):
    from order_evidence import record_evidence
    return record_evidence(chain, event_type, payload, actor=actor)


def record_customer_request(chain, order_number, items, fulfilment):
    return _event(chain, "customer_request", {
        "order_number": order_number,
        "items": items,
        "fulfilment": fulfilment,
    }, "customer")


def record_ai_recommendation(chain, order_number, recommendation, agent="Pizzomania AI"):
    return _event(chain, "ai_recommendation", {
        "order_number": order_number,
        "recommendation": recommendation,
    }, agent)


def record_customer_approval(chain, order_number, approved=True):
    return _event(chain, "customer_approval", {
        "order_number": order_number,
        "approved": bool(approved),
    }, "customer")


def record_server_validation(chain, order_number, items, total):
    return _event(chain, "server_validation", {
        "order_number": order_number,
        "items": items,
        "total": total,
    }, "server")


def record_order_created(chain, order_number, store, fulfilment):
    return _event(chain, "order_created", {
        "order_number": order_number,
        "store": store,
        "fulfilment": fulfilment,
    }, "order-agent")


def record_status_transition(chain, order_number, status, actor="order-agent", metadata=None):
    return _event(chain, "order_status", {
        "order_number": order_number,
        "status": status,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }, actor)
