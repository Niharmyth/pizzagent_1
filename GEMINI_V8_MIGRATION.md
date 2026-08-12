# Gemini V8 migration

Pizzomania V8 uses the Google Gemini Interactions API for agent orchestration.

## Configuration

```env
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-3.6-flash
FLASK_SECRET_KEY=your_random_secret
```

The Build My Pizza frontend stores the returned interaction ID for follow-up turns. The backend passes that ID as `previous_interaction_id`, allowing Gemini to retain the conversation state server-side.

Tool calls are still executed by Flask. Prices, calories, menu availability, delivery eligibility, and order status remain authoritative backend facts.

## Health check

Open `/api/ai/status` or the Admin page. It reports the configured model and `Interactions API` without exposing the API key.

If Gemini is unavailable, the deterministic Pizzomania fallback remains available.
