"""Portion sizes (average weights) — a separate layer from the food database.

Nothing here is stored in `foods`: the catalogue keeps the per-100 g values and
this module answers "what is a normal amount of this?" when you log it.

Lookup order for a food:
  1. ITEM[name]   — item-specific weights (a tomato is not a watermelon)
  2. GROUP[group] — a sensible default for the whole group
  3. []           — no suggestion, type the grams yourself

Weights are edible-portion averages, in grams (ml for drinks).
"""
from __future__ import annotations

# ---------------------------------------------------------------- per item
ITEM: dict[str, list[tuple[str, float]]] = {
    # vegetables
    "Potato (boiled)": [("small", 120), ("medium", 170), ("large", 250)],
    "Potato (raw)": [("small", 120), ("medium", 170), ("large", 250)],
    "Sweet potato": [("small", 100), ("medium", 150), ("large", 250)],
    "Tomato": [("small", 90), ("medium", 130), ("large", 180)],
    "Cucumber": [("small", 100), ("medium", 200), ("large", 300)],
    "Zucchini": [("small", 120), ("medium", 200), ("large", 300)],
    "Eggplant": [("small", 150), ("medium", 250), ("large", 400)],
    "Red bell pepper": [("small", 90), ("medium", 120), ("large", 180)],
    "Carrot": [("small", 50), ("medium", 70), ("large", 100)],
    "Onion": [("small", 70), ("medium", 110), ("large", 170)],
    "Garlic": [("1 clove", 3), ("2 cloves", 6), ("3 cloves", 9)],
    "Spinach": [("small", 30), ("medium", 60), ("large", 100)],
    "Kale": [("small", 30), ("medium", 60), ("large", 100)],
    "Swiss chard": [("small", 30), ("medium", 60), ("large", 100)],
    "Bok choy": [("small", 100), ("medium", 170), ("large", 250)],
    "Brussels sprouts": [("small", 15), ("medium", 20), ("large", 30)],
    "Lettuce": [("small", 30), ("medium", 60), ("large", 100)],
    "Broccoli": [("small", 100), ("medium", 150), ("large", 250)],
    "Cauliflower": [("small", 150), ("medium", 300), ("large", 500)],
    "Asparagus": [("small", 15), ("medium", 20), ("large", 30)],
    "Mushrooms": [("small", 10), ("medium", 18), ("large", 30)],
    "Cabbage": [("small", 100), ("medium", 200), ("large", 300)],
    "Jalapeño": [("small", 10), ("medium", 15), ("large", 25)],
    # fruit
    "Apple": [("small", 150), ("medium", 180), ("large", 220)],
    "Orange": [("small", 130), ("medium", 180), ("large", 230)],
    "Grapefruit": [("small", 200), ("medium", 250), ("large", 300)],
    "Pomegranate": [("small", 200), ("medium", 280), ("large", 350)],
    "Banana": [("small", 100), ("medium", 120), ("large", 150)],
    "Watermelon": [("small", 150), ("medium", 300), ("large", 500)],
    "Melon": [("small", 150), ("medium", 300), ("large", 500)],
    "Pear": [("small", 150), ("medium", 180), ("large", 220)],
    "Peach": [("small", 130), ("medium", 150), ("large", 180)],
    "Strawberries": [("1 berry", 12), ("handful", 80), ("bowl", 150)],
    "Mango": [("small", 150), ("medium", 200), ("large", 300)],
    "Pineapple": [("small", 100), ("medium", 200), ("large", 300)],
    "Kiwi": [("small", 60), ("medium", 75), ("large", 100)],
    "Raspberries": [("handful", 60), ("bowl", 120), ("large bowl", 200)],
    "Blueberries": [("handful", 70), ("bowl", 150), ("large bowl", 250)],
    "Cherries": [("handful", 80), ("bowl", 150), ("large bowl", 250)],
    "Lemon": [("small", 60), ("medium", 90), ("large", 120)],
    # eggs (counted, not sized)
    "Whole egg": [("1 egg", 50), ("2 eggs", 100), ("3 eggs", 150)],
    "Egg white": [("1 white", 33), ("2 whites", 66), ("3 whites", 99)],
    # grains: dry weight, then cooked
    "Oats (dry)": [("small", 40), ("medium", 80), ("large", 150)],
    "Wholegrain rice (dry)": [("small", 50), ("medium", 100), ("large", 200)],
    "Wheat berries (dry)": [("small", 50), ("medium", 100), ("large", 200)],
    "Quinoa (dry)": [("small", 50), ("medium", 100), ("large", 200)],
    "Farro (dry)": [("small", 50), ("medium", 100), ("large", 200)],
    "Bulgur (dry)": [("small", 50), ("medium", 100), ("large", 200)],
    "Barley (pearled, dry)": [("small", 50), ("medium", 100), ("large", 200)],
    "Brown rice (cooked)": [("small", 150), ("medium", 250), ("large", 400)],
    "White rice (cooked)": [("small", 150), ("medium", 250), ("large", 400)],
    "Wholegrain bread": [("1 slice", 35), ("2 slices", 70), ("3 slices", 105)],
    "Corn tortilla": [("1 tortilla", 25), ("2 tortillas", 50), ("3 tortillas", 75)],
    # dairy
    "Whole milk": [("glass", 200), ("mug", 250), ("large glass", 400)],
    "Yogurt (plain)": [("small", 100), ("medium", 150), ("large", 250)],
    "Greek yogurt": [("small", 100), ("medium", 170), ("large", 250)],
    "Fresh cheese": [("small", 30), ("medium", 60), ("large", 120)],
}

# --------------------------------------------------------------- per group
GROUP: dict[str, list[tuple[str, float]]] = {
    "Meat": [("100 g", 100), ("200 g", 200), ("400 g", 400)],
    "Fish": [("100 g", 100), ("200 g", 200), ("400 g", 400)],
    "Legume": [("100 g", 100), ("200 g", 200), ("300 g", 300)],
    "Grain": [("50 g", 50), ("100 g", 100), ("200 g", 200)],
    "Nut/Seed": [("15 g", 15), ("30 g", 30), ("60 g", 60)],
    "Fat": [("1 tsp", 5), ("1 tbsp", 15), ("2 tbsp", 30)],
    "Spice": [("pinch", 1), ("1 tsp", 2), ("1 tbsp", 5)],
    "Condiment": [("1 tbsp", 15), ("2 tbsp", 30), ("4 tbsp", 60)],
    "Dairy": [("100 g", 100), ("200 g", 200), ("300 g", 300)],
    "Drink": [("glass", 200), ("mug", 350), ("bottle", 500)],
    "Vegetable": [("small", 80), ("medium", 150), ("large", 250)],
    "Fruit": [("small", 100), ("medium", 150), ("large", 200)],
    "Egg": [("1 egg", 50), ("2 eggs", 100), ("3 eggs", 150)],
}


def for_food(name: str, group: str = "") -> list[tuple[str, float]]:
    """Suggested portions for a food: per item first, then by group."""
    if name in ITEM:
        return list(ITEM[name])
    return list(GROUP.get(group or "", []))


def default_index(options: list[tuple[str, float]]) -> int:
    """Which suggestion to preselect (the middle one, like a medium tomato)."""
    if not options:
        return -1
    return 1 if len(options) > 1 else 0
