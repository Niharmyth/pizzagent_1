"""Expanded cross-category catalog for Pizzomania V12.

The existing PIZZAS list remains authoritative for pizza pricing/configuration.
This module adds non-pizza products and bundle definitions so the menu and AI
can reason across the full food-and-drink catalog without changing pizza logic.
"""

MENU_EXTRAS = [
    # Drinks
    {"id": "d_coke", "category": "drinks", "name": "Coca-Cola", "description": "Classic chilled Coca-Cola.", "price": 3.50, "calories": 139, "tags": ["Drink", "Popular"], "dietary": [], "image": "/static/images/menu/coke.webp"},
    {"id": "d_coke_zero", "category": "drinks", "name": "Coke Zero", "description": "Zero-sugar Coca-Cola.", "price": 3.50, "calories": 1, "tags": ["Drink", "Zero Sugar"], "dietary": ["Vegetarian", "Vegan"], "image": "/static/images/menu/coke-zero.webp"},
    {"id": "d_sprite", "category": "drinks", "name": "Sprite", "description": "Crisp lemon-lime soft drink.", "price": 3.50, "calories": 140, "tags": ["Drink"], "dietary": ["Vegetarian", "Vegan"], "image": "/static/images/menu/sprite.webp"},
    {"id": "d_water", "category": "drinks", "name": "Still Water", "description": "Chilled bottled water.", "price": 2.50, "calories": 0, "tags": ["Drink", "Light"], "dietary": ["Vegetarian", "Vegan"], "image": "/static/images/menu/water.webp"},

    # Sides
    {"id": "s_garlic", "category": "sides", "name": "Garlic Bread", "description": "Warm toasted garlic bread with herbs.", "price": 6.90, "calories": 420, "tags": ["Side", "Popular"], "dietary": ["Vegetarian"], "image": "/static/images/menu/garlic-bread.webp"},
    {"id": "s_cheesy_garlic", "category": "sides", "name": "Cheesy Garlic Bread", "description": "Garlic bread finished with melted mozzarella.", "price": 8.90, "calories": 560, "tags": ["Side", "Cheesy"], "dietary": ["Vegetarian"], "image": "/static/images/menu/cheesy-garlic-bread.webp"},
    {"id": "s_wedges", "category": "sides", "name": "Loaded Potato Wedges", "description": "Crispy potato wedges with smoky seasoning and dipping sauce.", "price": 8.90, "calories": 520, "tags": ["Side", "Movie Night"], "dietary": ["Vegetarian"], "image": "/static/images/menu/wedges.webp"},
    {"id": "s_wings", "category": "sides", "name": "Spicy Chicken Bites", "description": "Crispy chicken bites with a fiery glaze.", "price": 10.90, "calories": 610, "tags": ["Side", "Spicy", "Protein"], "dietary": [], "image": "/static/images/menu/chicken-bites.webp"},

    # Dips
    {"id": "dip_garlic", "category": "dips", "name": "Garlic Aioli", "description": "Creamy garlic dipping sauce.", "price": 1.50, "calories": 130, "tags": ["Dip"], "dietary": ["Vegetarian"], "image": "/static/images/menu/garlic-aioli.webp"},
    {"id": "dip_bbq", "category": "dips", "name": "Smoky BBQ Dip", "description": "Sweet and smoky barbecue dip.", "price": 1.50, "calories": 80, "tags": ["Dip", "BBQ"], "dietary": ["Vegetarian", "Vegan"], "image": "/static/images/menu/bbq-dip.webp"},
    {"id": "dip_chili", "category": "dips", "name": "Spicy Chili Dip", "description": "Hot chili dipping sauce for heat seekers.", "price": 1.50, "calories": 45, "tags": ["Dip", "Spicy"], "dietary": ["Vegetarian", "Vegan"], "image": "/static/images/menu/chili-dip.webp"},

    # Desserts
    {"id": "x_brownie", "category": "desserts", "name": "Chocolate Brownie", "description": "Rich chocolate brownie served warm.", "price": 6.50, "calories": 390, "tags": ["Dessert", "Chocolate"], "dietary": ["Vegetarian"], "image": "/static/images/menu/brownie.webp"},
    {"id": "x_churros", "category": "desserts", "name": "Cinnamon Churros", "description": "Crisp churros with cinnamon sugar and chocolate dip.", "price": 6.90, "calories": 410, "tags": ["Dessert", "Shareable"], "dietary": ["Vegetarian"], "image": "/static/images/menu/churros.webp"},
    {"id": "x_lava", "category": "desserts", "name": "Chocolate Lava Cake", "description": "Warm chocolate cake with a gooey centre.", "price": 7.50, "calories": 450, "tags": ["Dessert", "Chocolate"], "dietary": ["Vegetarian"], "image": "/static/images/menu/lava-cake.webp"},
]

MENU_BUNDLES = [
    {"id": "b_family_feast", "name": "Family Feast", "description": "A family pizza night with a side, drinks and dessert.", "categories": ["family", "sides", "drinks", "desserts"], "tags": ["Family", "Value"], "serves": "4-6"},
    {"id": "b_date_night", "name": "Date Night", "description": "Two pizzas, two drinks and a dessert to share.", "categories": ["single", "drinks", "desserts"], "tags": ["Date Night", "Value"], "serves": "2"},
    {"id": "b_kids_mania", "name": "Kids Mania", "description": "Two kids pizzas, two drinks and garlic bread.", "categories": ["kids", "drinks", "sides"], "tags": ["Kids", "Family"], "serves": "2-3"},
    {"id": "b_movie_night", "name": "Movie Night", "description": "Pizza, wedges, spicy bites and drinks for a movie marathon.", "categories": ["single", "family", "sides", "drinks"], "tags": ["Movie Night", "Shareable"], "serves": "3-5"},
]

MENU_CATEGORIES = [
    {"id": "all", "name": "All", "icon": "✦"},
    {"id": "single", "name": "Pizza", "icon": "🍕"},
    {"id": "family", "name": "Family", "icon": "👨‍👩‍👧‍👦"},
    {"id": "kids", "name": "Kids", "icon": "🧒"},
    {"id": "drinks", "name": "Drinks", "icon": "🥤"},
    {"id": "sides", "name": "Sides", "icon": "🍟"},
    {"id": "dips", "name": "Dips", "icon": "🧄"},
    {"id": "desserts", "name": "Desserts", "icon": "🍰"},
]


def extras_by_category(category=None):
    if not category or category == "all":
        return list(MENU_EXTRAS)
    return [item for item in MENU_EXTRAS if item["category"] == category]


def menu_search(query="", category="all", max_price=None, dietary=None):
    """Small deterministic cross-category search for non-pizza menu items."""
    text = str(query or "").lower().strip()
    dietary = {str(x).lower() for x in (dietary or [])}
    items = extras_by_category(category)
    if max_price is not None:
        items = [x for x in items if x["price"] <= float(max_price)]
    if dietary:
        items = [x for x in items if dietary.issubset({d.lower() for d in x["dietary"]})]
    if not text:
        return items
    tokens = [t for t in text.split() if len(t) > 2]
    ranked = []
    for item in items:
        hay = " ".join([item["name"], item["description"], *item["tags"], *item["dietary"]]).lower()
        score = sum(2 if token in hay else 0 for token in tokens)
        if score:
            ranked.append((score, item))
    return [item for _, item in sorted(ranked, key=lambda pair: (-pair[0], pair[1]["price"]))]
