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
