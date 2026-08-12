# Pizzomania V7

## Fixed
- Mobile layout: hero, AI builder, address checkout and responsive controls were tightened for narrow screens.
- Live Agent Visualization moved off the homepage to `/agent-flow`.
- Build My Pizza deterministic mode now parses spicy, cheesy, budget, calorie, dietary, family/kids and follow-up modification requests instead of returning a fixed/default suggestion.
- AI conversation history no longer sends the current user message twice to Gemini.
- Gemini configuration now loads from environment variables or a local `.env` file via `python-dotenv` and supports `GEMINI_API_KEY` or `GOOGLE_API_KEY`.
- Added `/api/ai/status` so configuration can be diagnosed without exposing credentials.
- Address entry now provides debounced autocomplete suggestions as the customer types and supports verified selection.
- Added a read-only `/admin` page showing agents, tools, RAG/Gemini health and recent agent events.

## Added
- Lightweight RAG layer in `rag.py`.
- `knowledge/` Markdown knowledge base.
- RAG context is injected into Gemini before generation.
- Standalone animated agent flow page.
- Admin agent/process dashboard.

## Guardrails
- AI never owns authoritative pricing/calorie values.
- Order status remains server-side and canonical.
- Order lookup remains session-scoped.
- `.env` must never be committed.

## RAG roadmap
Current retrieval is intentionally dependency-free token overlap. For production, replace `retrieve_context()` with embeddings and a vector store such as PostgreSQL + pgvector while keeping the same interface.
