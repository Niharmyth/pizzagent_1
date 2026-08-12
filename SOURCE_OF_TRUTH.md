# Pizzomania — Source of Truth

**Canonical version:** V7 — Pizzomania Visual + Phase 1 AI + RAG + Live Agentic Flow + Admin

## Rule

This repository's `main` branch is the **single source of truth** for Pizzomania.

Do not build future changes from old ZIP files, exported snapshots, generated derivative folders, or prior ChatGPT/Claude working copies.

## Development workflow

1. Pull/clone the latest `main` before making changes.
2. Make the change in a feature branch.
3. Rebase/merge the feature branch onto the latest `main` before final review.
4. Run the verification checks and the full app regression test.
5. Merge the approved change into `main`.
6. Push `main` before handing the codebase to another tool/person.
7. The next change must start from that pushed `main`.

## Visual baseline

V5 visual improvements are part of this canonical version:

- real responsive HTML hero
- clean pizza-only hero image
- transparent Pizzomania logo
- subtle background pattern
- local dedicated pizza photography
- correct `$30+` free-delivery messaging

## AI baseline

Phase 1 AI and the live agentic flow are part of this canonical version:

- Build My Pizza AI
- server-side menu/pizza validation
- Gemini tool calling with deterministic fallback
- session-scoped demo order lookup
- event-driven agentic flow visualization on `/agent-flow`
- Build My Pizza deterministic intent analysis when Gemini is unavailable
- local RAG retrieval layer feeding the AI context
- read-only `/admin` agent/process dashboard
- one canonical backend order-status calculation

## Required guardrails

- AI never owns authoritative price/calorie values.
- AI never directly bypasses the existing cart validation.
- Order status is calculated once by the backend and consumed by both the tracker and AI.
- Order lookup requires the current session to own the order.
- Customer-facing pizza imagery is local; no Wikimedia dependency.
- Gemini credentials are loaded from environment or `.env`; never commit `.env`.

## Verification

Run:

```bash
python -m py_compile app.py
node --check static/app.js
python scripts/verify_pizzomania.py
```

GitHub Actions runs the same checks on pushes and pull requests.


## Gemini API baseline

- The canonical agent integration uses Google's **Interactions API**.
- Default model: `gemini-3.6-flash`.
- Do not revert to `models.generate_content` or `gemini-2.5-flash` for the agent without a deliberate migration decision.
- Keep `google-genai>=2.0.0`.
- The server remains authoritative for menu, pricing, calories, delivery eligibility, and order status.
