from pathlib import Path
import re, sys

ROOT = Path(__file__).resolve().parents[1]
app = (ROOT / 'app.py').read_text()
index = (ROOT / 'templates/index.html').read_text()
css = (ROOT / 'static/style.css').read_text()
js = (ROOT / 'static/app.js').read_text()
errors=[]

def need(text, needle, label):
    if needle not in text: errors.append(f'Missing {label}: {needle}')

def forbid(text, pattern, label):
    if re.search(pattern, text, re.I): errors.append(f'Forbidden {label}: {pattern}')

need(app, 'HERO_IMAGE = "/static/images/hero-pizza.webp"', 'clean hero')
need(index, 'images/logo-transparent.png', 'transparent logo')
need(index, 'id="aiOpenBtn"', 'Build My Pizza AI entry point')
need(index, 'id="playAiFlowBtn"', 'agent flow demo')
need(js, '/api/order/status?order_number=', 'canonical order status client')
need(app, '@app.route("/api/order/status", methods=["GET"])', 'canonical order status endpoint')
need(app, 'order.get("owner_id") != owner', 'session-scoped order lookup')
need(app, 'delivery_fee = 0.0 if fulfilment == "pickup" else (0.0 if subtotal >= 30', '$30 free delivery logic')
need(app, 'build_pizza', 'AI pizza validation tool')
forbid(app, r'wiki_img|Wikimedia Commons|Special:FilePath', 'external pizza image dependency')
forbid(index, r'codes aren.?t applied at checkout yet', 'stale deal copy')

required_images = ['hero-pizza.webp','logo-transparent.png','background-pattern.png']
for name in required_images:
    if not (ROOT/'static/images'/name).exists(): errors.append(f'Missing asset: static/images/{name}')

pizza_dir=ROOT/'static/images/pizzas'
if len(list(pizza_dir.glob('*.webp'))) < 15: errors.append('Expected at least 15 local pizza images')

if errors:
    print('Pizzomania consistency check FAILED')
    for e in errors: print(' -',e)
    sys.exit(1)
print('Pizzomania consistency check PASSED')
