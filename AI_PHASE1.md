# Pizzomania AI — Phase 1

## What was added

- `POST /api/agent/ask` — conversational AI endpoint.
- Deterministic fallback mode when `GEMINI_API_KEY` is not configured.
- Gemini function-calling tools:
  - `search_menu`
  - `build_pizza`
  - `check_delivery_range`
  - `check_order_status`
- Server-side `build_pizza` validation. The backend remains authoritative for price and calories.
- Demo-only `ORDERS_BY_NUMBER` registry populated after successful checkout.
- Pizzomania AI section between deals and menu.
- AI modal with quick prompts, chat history, activity/status display, pizza suggestions, Customize and Add to cart actions.
- Floating `Build My Pizza` button.
- Dedicated local images for the remaining pizzas.

## Run

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="your-key"
export FLASK_SECRET_KEY="your-secret"
python app.py
```

Without `GEMINI_API_KEY`, the AI UI still works in deterministic demo mode for common requests such as:

- `something vegetarian under $15`
- `something spicy and cheesy`
- `something under 600 calories`
- `surprise me under $18`
- `where is order PM-123456`

## Important design rule

The AI can propose a pizza, but it does not own the price/calorie truth. `build_pizza()` calls the existing server-side pricing/validation function before the frontend can add the suggestion to the cart.

`ORDERS_BY_NUMBER` is intentionally in-memory for this demo. Replace it with a database-backed order repository before production use.


## V7 additions

- Gemini credentials are loaded from `GEMINI_API_KEY` or `GOOGLE_API_KEY` and `.env` is supported through `python-dotenv`.
- `/api/ai/status` reports configuration state without exposing the key.
- Build My Pizza has a stronger deterministic parser for spicy, cheesy, budget, calorie, dietary and follow-up modification requests.
- RAG is integrated through `rag.py` and the `knowledge/` folder.
- The animated flow lives at `/agent-flow` rather than on the home page.
- `/admin` shows the agent roster, tools, RAG/Gemini health and recent agent events.

### Gemini setup

Create a local `.env` file (never commit it):

```text
GEMINI_API_KEY=your-real-key
GEMINI_MODEL=gemini-2.5-flash
FLASK_SECRET_KEY=your-random-secret
```

Restart Flask after changing the key. Open `/admin` to confirm that Gemini is reported as enabled.

### RAG

The current RAG implementation is intentionally lightweight: it retrieves relevant chunks from Markdown files in `knowledge/` using token overlap, then injects those chunks into the Gemini system context. This is enough for a demo and keeps the project dependency-light. For production, replace the retrieval function with embeddings + a vector store (for example pgvector) while keeping the same `retrieve_context(query, top_k)` interface.
