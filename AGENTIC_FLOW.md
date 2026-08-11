# Pizzomania Live Agentic Flow

The homepage now includes an animated agentic flow that doubles as a product demo and a live status visualization.

## Stages
1. Customer — pizza selected or craving described.
2. Pizza AI — intent is interpreted and a proposal is built.
3. Agent Tools — menu, toppings, size, crust and authoritative price/calories are validated server-side.
4. Order Agent — the approved pizza enters the existing cart/order flow.
5. Kitchen — the preparation sequence moves through dough, sauce, toppings and oven.
6. Delivery — order status and ETA become available.

## Live synchronization
The flow is not only a timed animation. `setAgentFlow()` is called by real app events:
- opening Build My Pizza AI -> Pizza AI
- AI tool/suggestion response -> Agent Tools
- adding an AI suggestion to the cart -> Order Agent
- placing an order -> Order Agent / Agent Tools
- order confirmation -> Kitchen
- preparation countdown -> Kitchen / Delivery

The Play Live Demo button provides a deterministic walkthrough for presentations.
