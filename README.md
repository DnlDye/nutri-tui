# Nutrition tracker (TUI)

Local-only terminal tracker for daily macros, minerals and body weight.
No cloud, no account: a single SQLite file on your disk.

```
nutri                # normal use
nutri --tab pane3    # open straight on a tab (1 today … 8 targets)
nutri --db /tmp/x.db # use another database
```

Run from source without the launcher:

```
cd ~/Documents/Tracker-Nutricion
.venv/bin/python -m nutri
```

## Tabs

| # | Tab | What it does |
|---|-----|--------------|
| 1 | Today | the day at a glance: every metric vs its target, colour-coded |
| 2 | Log | add a food (search → grams → Add), delete a row |
| 3 | Foods | food database, 109 entries; add / edit / delete your own |
| 4 | Weight | log weight, 7-day average, trend |
| 5 | Drinks | weekly count: water, coffee, tea, coke, sucralose |
| 6 | History | last 30 logged days, one row per day |
| 7 | Health | general goals (skin, swelling, antioxidants, muscle, weight) — trend only, nothing to tick |
| 8 | Targets | every number the app checks (saved to the local DB) |

## Keys

`1`…`8` switch tabs · `t` training/rest day · `s` steps · `r` reload (also re-reads
the desktop palette) · `q` quit · `n` / `e` / `d` new / edit / delete food in the
Foods tab · `d` delete the selected row in the Log tab.

Single-letter keys are ignored while you are typing in a field, so digits inside
the grams box never jump tabs.

## Colour rules

- **green** — target met.
- **white** — in progress (today) or no data.
- **red** — target failed: over the limit, or a past day that missed it.

Calories: 2100 on training days, 1800 on rest days, ±100 counts as met.
Protein 120-140 g · carbs 40-50% · fat 30% fixed · vitamin C 200 mg ·
potassium 3000-4000 mg · sodium never above potassium (ratio ≤ 1) ·
steps 3000-10000 · sucralose ≤ 10 g/day · coke ≤ 10% of weekly drinks.

## Adding a food

Foods tab → `n`. Values are **per 100 g** (drinks per 100 ml). Only whole
ingredients: the app multiplies by the grams you log. `antiox` is a 0-3
practical scale, not a lab figure.

## Where the data lives

```
~/.local/share/nutricion/nutricion.db
```

Back it up by copying that file. Delete it to start over (the 109 catalogue
foods are re-seeded automatically).

## Theme

The interface reads the live matugen palette at
`~/.cache/quickshell/matugen.json` — the same one kitty and the rest of the
desktop use — so it re-colours itself when you change theme. Press `r` after a
theme change.

## Tests

```
.venv/bin/python tests/run_tests.py
```

Covers the maths (totals, traffic lights, weight progress), the database and a
headless boot of the UI with simulated key presses.

## Layout

```
nutri/core.py    pure logic: targets, totals, traffic lights, sparklines
nutri/db.py      SQLite schema, migrations, queries
nutri/foods.py   the 109-food catalogue (USDA values per 100 g)
nutri/theme.py   matugen palette → Textual theme
nutri/app.py     the Textual UI
tests/           real tests (logic + db + headless TUI)
attic/           the abandoned Google-Sheets/.xlsx version, kept for reference
```
