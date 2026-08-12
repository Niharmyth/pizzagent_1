# Pizzomania V8 — Gemini Interactions API

- Migrated agent orchestration from `models.generate_content` to Google's Interactions API.
- Updated default model to `gemini-3.6-flash`.
- Migrated delivery messaging to the Interactions API.
- Preserved server-side tool execution and authoritative pizza pricing/calorie validation.
- Added stateful interaction IDs to the Build My Pizza frontend so follow-up requests retain Gemini conversation state.
- Added Interactions API metadata to AI health/admin status.
- Updated `google-genai` minimum version to 2.0.0.
- Updated `.env.example` with the new default model.

## Why

The previous `gemini-2.5-flash` + `generate_content` path can return `404 NOT_FOUND` for new users. The current Google guidance recommends the Interactions API for new agentic applications and documents `gemini-3.6-flash` with custom function calling.
