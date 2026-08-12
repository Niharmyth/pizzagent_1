# Pizzomania V9 — AI responsiveness fix

This patch is based on V8 Mobile AI/Admin Fix.

## Root causes addressed
- Interaction-scoped `system_instruction` was only supplied on the first Interactions API turn. It is now supplied on every turn.
- After a successful `build_pizza`, the model could continue requesting tools until the round cap. The final response turn now disables custom tools once a valid pizza exists.
- A successful validated pizza is returned instead of a generic "stuck" response if the final natural-language turn cannot complete within the bounded loop.
- The frontend has a 35-second abort guard and can fall back to the deterministic local agent for a quick response.
- Agent rounds reduced to 3 because the normal path is search -> build -> final response.

## Gemini configuration
Use the current Interactions API configuration:

GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.6-flash
FLASK_SECRET_KEY=...

The app continues to use server-side tool execution and authoritative pricing.
