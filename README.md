# pizzagent_1


pip3 install -r requirements.txt
export GEMINI_API_KEY="your-real-key-here"
python3 app.py


(or put that export in ~/.bashrc so it persists across sessions).

## Pizzomania visual update

- Hero copy is real HTML; `hero-pizza.webp` is the clean visual only.
- Product images are served locally from `static/images/pizzas/`.
- `logo-transparent.png` is used in the header.
- Delivery is free for orders of $30 or more; otherwise delivery is $4.99 when serviceable.
- Set `FLASK_SECRET_KEY` in production instead of relying on the development fallback.
