"""Drink catalogue for the weekly counter.

One row per drink, grouped so the list reads like a menu. Nothing here stores
nutrition — the counter is just "how many this week"; the food database already
has the per-100 ml values if you want to log a drink as food.
"""
from __future__ import annotations

# name, group — order matters: it is the order on screen
DRINKS: list[tuple[str, str]] = [
    # --- coffee
    ("Espresso", "Coffee"),
    ("Americano", "Coffee"),
    ("Coffee (drip)", "Coffee"),
    ("Latte", "Coffee"),
    ("Iced Latte", "Coffee"),
    ("Cappuccino", "Coffee"),
    ("Macchiato", "Coffee"),
    ("Flat White", "Coffee"),
    ("Mocha", "Coffee"),
    ("Cortado", "Coffee"),
    ("Cold Brew", "Coffee"),
    ("Frappé", "Coffee"),
    # --- tea
    ("Black Tea", "Tea"),
    ("Green Tea", "Tea"),
    ("White Tea", "Tea"),
    ("Herbal Tea", "Tea"),
    ("Chai Latte", "Tea"),
    ("Iced Tea", "Tea"),
    # --- water
    ("Water", "Water"),
    ("Sparkling Water", "Water"),
    # --- soda
    ("Sugar-soda", "Soda"),
    ("Non-sugar soda", "Soda"),
    ("Energy drink", "Soda"),
    # --- juice
    ("Orange juice", "Juice"),
    ("Apple juice", "Juice"),
    ("Pineapple juice", "Juice"),
    ("Grape juice", "Juice"),
    ("Cranberry juice", "Juice"),
    ("Lemonade", "Juice"),
    # --- smoothies
    ("Fruit smoothie", "Smoothie"),
    ("Green smoothie", "Smoothie"),
    ("Berry smoothie", "Smoothie"),
    ("Banana smoothie", "Smoothie"),
    ("Protein shake", "Smoothie"),
    # --- other
    ("Hot chocolate", "Other"),
]

GROUPS = ["Coffee", "Tea", "Water", "Soda", "Juice", "Smoothie", "Other"]

SUGAR_SODA = "Sugar-soda"
NON_SUGAR_SODA = "Non-sugar soda"

# left column / right column, so the whole menu fits without scrolling
LEFT_GROUPS = ("Coffee", "Tea")
RIGHT_GROUPS = ("Water", "Soda", "Juice", "Smoothie", "Other")

# old fixed columns (first version) -> drink names, used once when migrating
LEGACY_MAP = {"water": "Water", "coffee": "Coffee (drip)", "tea": "Black Tea",
              "coke": SUGAR_SODA}


def names() -> list[str]:
    return [n for n, _ in DRINKS]


def by_group(group: str) -> list[str]:
    return [n for n, g in DRINKS if g == group]
