# Pizzomania update

## Changed

- Rebuilt the hero as real responsive HTML + a clean pizza-only visual.
- Added `static/images/hero-pizza.webp`.
- Switched navbar to `logo-transparent.png`.
- Replaced all external/Wikimedia pizza image URLs with local assets.
- Cleaned the six product images by removing the baked-in product-name ribbons.
- Reduced background-pattern intensity and increased pattern scale.
- Added responsive hero behavior for mobile.
- Removed the legacy self-contained hero implementation and unused legacy hero/logo files.
- Changed delivery pricing so delivery is free at `$30+`, otherwise `$4.99` when serviceable.
- Moved Flask secret to `FLASK_SECRET_KEY` with a development fallback.
- Updated the deals disclaimer to distinguish demo promo codes from the implemented free-delivery threshold.

## Files changed

- `app.py`
- `templates/index.html`
- `static/style.css`
- `README.md`

## New/updated assets

- `static/images/hero-pizza.webp`
- `static/images/logo-transparent.png`
- `static/images/pizzas/*.webp`

## Deliberately preserved

- Flask API structure
- cart/session logic
- pizza customization and server-side price calculation
- search and filters
- pickup/delivery flow
- order processing
- loading animation
- order tracker
- deals carousel
- account/loyalty demo
- mobile bottom navigation

## Note

The current repository did not contain individually generated clean photography for every unique menu item. The remaining family/kids items therefore reuse the closest local Pizzomania image rather than pulling external Wikimedia photos. For a final production-quality menu, create dedicated photography for each distinct pizza.

## Dedicated pizza photography pass
- Added clean, text-free 4:3 pizza photography for the remaining single/family/kids products.
- Added a dedicated Mediterranean Falafel image.
- Updated `app.py` so every pizza product uses a local image asset; no pizza product falls back to Wikimedia.
- Kept the existing Pizzomania visual language: warm neutral surface, overhead food photography, consistent framing.
