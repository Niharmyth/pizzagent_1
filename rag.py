"""Lightweight RAG layer with evaluation/observability for Pizzomania.

The demo still uses dependency-free token retrieval, but V12 adds measurable
retrieval quality from a small ground-truth evaluation set. MRR/Recall/Precision
are computed against known relevant chunks; groundedness is explicitly labelled
as a proxy until an LLM evaluator is wired in.
"""
from pathlib import Path
import json
import re
import time

ROOT = Path(__file__).resolve().parent
KNOWLEDGE_DIR = ROOT / "knowledge"
EVAL_FILE = ROOT / "evaluation" / "rag_eval.json"

_RETRIEVAL_STATS = {"queries": 0, "latency_ms": [], "scores": []}


def _tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _load_chunks():
    chunks = []
    if not KNOWLEDGE_DIR.exists():
        return chunks
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        parts = re.split(r"\n(?=##? )|\n\n+", text)
        for i, part in enumerate(parts):
            part = part.strip()
            if len(part) < 30:
                continue
            chunks.append({"source": path.name, "chunk": i, "text": part, "tokens": _tokens(part)})
    return chunks


CHUNKS = _load_chunks()


def _load_eval():
    if not EVAL_FILE.exists():
        return []
    try:
        data = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("cases", [])
    except Exception:
        return []


EVAL_CASES = _load_eval()


def retrieve_context(query, top_k=4):
    started = time.perf_counter()
    q = _tokens(query)
    scored = []
    for item in CHUNKS:
        overlap = len(q & item["tokens"])
        if overlap:
            score = overlap / max(1, len(q))
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [item for _, item in scored[:top_k]]
    scores = [score for score, _ in scored[:top_k]]
    elapsed = (time.perf_counter() - started) * 1000
    _RETRIEVAL_STATS["queries"] += 1
    _RETRIEVAL_STATS["latency_ms"].append(elapsed)
    _RETRIEVAL_STATS["scores"].extend(scores)
    context = "\n\n---\n\n".join(f"Source: {item['source']}\n{item['text']}" for item in selected)
    return {"chunks": selected, "context": context or "No relevant knowledge was found.", "retrieval_ms": round(elapsed, 2), "scores": scores}


def _eval_metrics():
    if not EVAL_CASES or not CHUNKS:
        return {"cases": 0, "mrr": 0.0, "recall_at_1": 0.0, "recall_at_3": 0.0, "recall_at_5": 0.0, "precision_at_5": 0.0, "groundedness_proxy": 0.0}
    reciprocal, r1, r3, r5, p5, grounded = [], [], [], [], [], []
    for case in EVAL_CASES:
        query = case.get("query", "")
        relevant = {(x.get("source"), int(x.get("chunk", -1))) for x in case.get("relevant", [])}
        q = _tokens(query)
        scored = []
        for item in CHUNKS:
            overlap = len(q & item["tokens"])
            if overlap:
                scored.append((overlap / max(1, len(q)), item))
        scored.sort(key=lambda x: x[0], reverse=True)
        ranked = [(x["source"], x["chunk"]) for _, x in scored[:5]]
        rank = next((i + 1 for i, key in enumerate(ranked) if key in relevant), None)
        reciprocal.append(1 / rank if rank else 0)
        r1.append(1 if any(x in relevant for x in ranked[:1]) else 0)
        r3.append(1 if any(x in relevant for x in ranked[:3]) else 0)
        r5.append(1 if any(x in relevant for x in ranked[:5]) else 0)
        p5.append(sum(1 for x in ranked[:5] if x in relevant) / 5)
        expected = _tokens(case.get("expected_answer", ""))
        retrieved = set().union(*(x["tokens"] for _, x in scored[:5])) if scored else set()
        grounded.append(len(expected & retrieved) / max(1, len(expected)))
    n = len(EVAL_CASES)
    return {
        "cases": n,
        "mrr": round(sum(reciprocal) / n, 3),
        "recall_at_1": round(sum(r1) / n, 3),
        "recall_at_3": round(sum(r3) / n, 3),
        "recall_at_5": round(sum(r5) / n, 3),
        "precision_at_5": round(sum(p5) / n, 3),
        "groundedness_proxy": round(sum(grounded) / n, 3),
    }


def rag_status():
    metrics = _eval_metrics()
    latencies = _RETRIEVAL_STATS["latency_ms"]
    scores = _RETRIEVAL_STATS["scores"]
    return {
        "enabled": bool(CHUNKS),
        "documents": len({x["source"] for x in CHUNKS}),
        "chunks": len(CHUNKS),
        "mode": "local-token-retrieval",
        "upgrade_path": "Replace retrieve_context() with an embedding/vector-store retriever when the knowledge base grows.",
        "evaluation": metrics,
        "live": {
            "queries": _RETRIEVAL_STATS["queries"],
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
            "avg_retrieval_score": round(sum(scores) / len(scores), 3) if scores else 0.0,
        },
        "groundedness_note": "Groundedness shown as a retrieval/evidence overlap proxy; use an LLM judge for production groundedness.",
    }
