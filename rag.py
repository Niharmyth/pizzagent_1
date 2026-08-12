"""Lightweight, dependency-free RAG layer for the Pizzomania demo.

It indexes markdown/text files from knowledge/ and retrieves the most relevant
chunks using token overlap. This is intentionally small so the demo works
without a vector database. The interface is designed so it can later be
replaced by pgvector, Vertex AI Vector Search, Pinecone, etc.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
KNOWLEDGE_DIR = ROOT / "knowledge"


def _tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _load_chunks():
    chunks = []
    if not KNOWLEDGE_DIR.exists():
        return chunks
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        # Split on headings / blank paragraphs while retaining useful context.
        parts = re.split(r"\n(?=##? )|\n\n+", text)
        for i, part in enumerate(parts):
            part = part.strip()
            if len(part) < 30:
                continue
            chunks.append({"source": path.name, "chunk": i, "text": part, "tokens": _tokens(part)})
    return chunks


CHUNKS = _load_chunks()


def retrieve_context(query, top_k=4):
    q = _tokens(query)
    scored = []
    for item in CHUNKS:
        overlap = len(q & item["tokens"])
        if overlap:
            # Small preference for exact phrase-ish relevance via token coverage.
            score = overlap / max(1, len(q))
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [item for _, item in scored[:top_k]]
    context = "\n\n---\n\n".join(
        f"Source: {item['source']}\n{item['text']}" for item in selected
    )
    return {"chunks": selected, "context": context or "No relevant knowledge was found."}


def rag_status():
    return {
        "enabled": bool(CHUNKS),
        "documents": len({x["source"] for x in CHUNKS}),
        "chunks": len(CHUNKS),
        "mode": "local-token-retrieval",
        "upgrade_path": "Replace retrieve_context() with an embedding/vector-store retriever when the knowledge base grows."
    }
