"""Real tests: logic, database and TUI boot (headless).

Run with:  .venv/bin/python tests/run_tests.py
"""
from __future__ import annotations

import asyncio
import datetime as dt
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nutri import core, db as dbmod, foods, portions  # noqa: E402

FAILS: list[str] = []


def check(name: str, got, exp, tol=1e-6):
    ok = (abs(got - exp) <= tol) if isinstance(exp, (int, float)) and isinstance(got, (int, float)) else (got == exp)
    print(("  ok   " if ok else "  FAIL ") + f"{name}: {got!r}" + ("" if ok else f" != {exp!r}"))
    if not ok:
        FAILS.append(name)


# ---------------------------------------------------------------- lógica
print("== core: totals")
rows = [
    dict(grams=200, kcal=143, protein=12.6, carbs=0.7, fat=9.5, vitc=0, potassium=126, sodium=142, antiox=1),
    dict(grams=150, kcal=165, protein=31.0, carbs=0, fat=3.6, vitc=0, potassium=256, sodium=74, antiox=0),
    dict(grams=300, kcal=87, protein=1.9, carbs=20.1, fat=0.1, vitc=13.0, potassium=379, sodium=5, antiox=2),
    dict(grams=200, kcal=23, protein=2.9, carbs=3.6, fat=0.4, vitc=28.1, potassium=558, sodium=79, antiox=3),
    dict(grams=150, kcal=89, protein=1.1, carbs=22.8, fat=0.3, vitc=8.7, potassium=358, sodium=1, antiox=1),
]
t = core.totals_from_rows(rows)
check("kcal", t.kcal, 974.0, 1e-9)
check("protein", t.protein, 84.85, 1e-9)
check("carbs", t.carbs, 103.1, 1e-9)
check("fat", t.fat, 25.95, 1e-9)
check("vit C", t.vitc, 108.25, 1e-9)
check("potassium", t.potassium, 3426.0, 1e-9)
check("sodium", t.sodium, 569.5, 1e-9)
check("antiox", t.antiox, 15.5, 1e-9)
check("Na:K ratio", round(t.ratio, 4), 0.1662, 1e-4)
check("% protein", round(t.p_pct, 4), 0.3484, 1e-4)
check("% carbs", round(t.c_pct, 4), 0.4234, 1e-4)
check("% fat", round(t.f_pct, 4), 0.2398, 1e-4)

print("== core: traffic lights")
T = core.TARGETS
ms = {m.key: m for m in core.evaluate(t, T, True, False)}
check("kcal 974 in progress -> pending", ms["kcal"].state, core.PENDING)
check("protein 84.9 -> pending", ms["protein"].state, core.PENDING)
check("vitC 108 -> pendiente", ms["vitc"].state, core.PENDING)
check("potassium 3426 -> ok", ms["potassium"].state, core.OK)
check("ratio 0.17 -> ok", ms["ratio"].state, core.OK)

hi = core.totals_from_rows([
    dict(grams=500, kcal=455, protein=24.1, carbs=1.9, fat=38.3, vitc=0, potassium=290, sodium=1235, antiox=0),
])
ms2 = {m.key: m for m in core.evaluate(hi, T, True, True)}
check("kcal 2275 past -> red", ms2["kcal"].state, core.FAIL)
check("high sodium ratio (4.26) -> red", ms2["ratio"].state, core.FAIL)
check("protein 120.5 -> ok", ms2["protein"].state, core.OK)
lo = core.totals_from_rows([
    dict(grams=50, kcal=130, protein=2.7, carbs=28.2, fat=0.3, vitc=0, potassium=35, sodium=1, antiox=0),
])
ms3 = {m.key: m for m in core.evaluate(lo, T, False, True)}
check("past day with 65 kcal -> red", ms3["kcal"].state, core.FAIL)
check("vitC 0 on a past day -> red", ms3["vitc"].state, core.FAIL)
vacio = core.totals_from_rows([])
ms4 = {m.key: m for m in core.evaluate(vacio, T, False, True)}
check("empty day is not red", ms4["kcal"].state, core.NONE)
check("empty day vitC has no data", ms4["vitc"].state, core.NONE)

check("sparkline length", len(core.sparkline([1, 2, 3, 4, 5], 10)), 5)
check("empty sparkline", core.sparkline([], 10), "")
p = core.progress(T, 79.8)
check("lost kg", round(p["bajado"], 1), 4.7)
check("to go kg", round(p["falta"], 1), 9.8)
check("BMI", round(p["imc"], 2), 28.61, 0.01)
check("progress", round(p["pct"], 3), 0.324, 0.001)

# ------------------------------------------------------------- portions
print("== portions")
check("tomato medium", portions.for_food("Tomato", "Vegetable")[1], ("medium", 130))
check("potato large", portions.for_food("Potato (boiled)", "Vegetable")[2], ("large", 250))
check("chicken 100/200/400",
      [g for _, g in portions.for_food("Chicken breast (cooked)", "Meat")], [100, 200, 400])
check("salmon 100/200/400",
      [g for _, g in portions.for_food("Salmon (cooked)", "Fish")], [100, 200, 400])
check("salt is a pinch", portions.for_food("Salt", "Spice")[0], ("pinch", 1))
check("unknown food has no suggestion", portions.for_food("Nothing", "Nope"), [])
check("default index is the middle", portions.default_index(portions.for_food("Apple", "")), 1)
# toda porción por item debe apuntar a un alimento real del catálogo
cat = {f[0] for f in foods.SEED}
check("item portions match the catalogue", sorted(set(portions.ITEM) - cat), [])
# y ningún grupo inventado
grupos = {f[1] for f in foods.SEED}
check("group portions match real groups", sorted(set(portions.GROUP) - grupos - {"Egg"}), [])

# ---------------------------------------------------------------- base
print("== db")
tmp = Path(tempfile.mkdtemp()) / "t.db"
d = dbmod.DB(tmp)
check("seeded foods", len(d.foods()), 109)
check("potato exists", d.food_by_name("Potato (boiled)")["kcal"], 87.0)
d.entry_add("2026-11-11", "Lunch", "Potato (boiled)", 300)
d.entry_add("2026-11-11", "Dinner", "Whole egg", 200)
tot = d.totals("2026-11-11")
check("day kcal in db", round(tot.kcal, 1), 547.0, 0.05)
check("items", tot.items, 2)
d.day_set("2026-11-11", training=1, steps=4200, skin="Sí", swelling="No")
day = d.day_get("2026-11-11")
check("training saved", day["training"], 1)
check("steps saved", day["steps"], 4200)
d.toggle_training("2026-11-11")
check("toggle training", d.day_get("2026-11-11")["training"], 0)
d.weight_put("2026-10-04", 84.5)
d.weight_put("2026-11-11", 79.8)
check("latest weight", d.weight_latest()[1], 79.8)
check("weight series", len(d.weight_series()), 2)
d.drinks_set("2026-11-09", water=20, coffee=7, tea=2, coke=1, other=0, sucralose=0)
check("drinks saved", d.drinks_get("2026-11-09")["coke"], 1)
val = d.drinks_get("2026-11-09")
total_beb = sum(val[k] for k in ("water", "coffee", "tea", "coke", "other"))
check("drinks total", total_beb, 30)
check("% coca", round(val["coke"] / total_beb, 3), 0.033)
d.targets_save({**T, "prot_max": 150})
check("target saved", d.targets()["prot_max"], 150.0)
check("untouched target", d.targets()["prot_min"], 120.0)
d.food_add("Avena instantánea", "Cereal", 380, 13.0, 60.0, 6.0, 10.0, 0, 350, 3, 1, "")
check("new food", d.food_by_name("Avena instantánea")["kcal"], 380.0)
d.food_delete(d.food_by_name("Avena instantánea")["id"])
check("food deleted", d.food_by_name("Avena instantánea"), None)
check("days with entries", d.logged_days(), ["2026-11-11"])

# ---------------------------------------------------------------- TUI
print("== TUI (headless)")


async def tui():
    from nutri.app import NutriApp, FoodModal
    app = NutriApp(str(tmp))
    async with app.run_test(size=(140, 42)) as pilot:
        await pilot.pause()
        from textual.widgets import DataTable, Static, TabbedContent
        hoy = app.query_one("#hoy_table", DataTable)
        check("today panel rows (10 metrics + steps)", hoy.row_count, 11)
        ali = app.query_one("#al_table", DataTable)
        check("food table rows", ali.row_count, 109)
        hi = app.query_one("#hi_table", DataTable)
        await pilot.pause()
        check("history has the test day", hi.row_count, 1)
        # cambiar de pestaña
        await pilot.press("2")
        await pilot.pause()
        check("log tab active",
              app.query_one(TabbedContent).active, "pane2")
        # alta de una entrada por la propia UI
        app.query_one("#rg_search").value = "Potato"
        await pilot.pause()
        reg = app.query_one("#rg_foods")
        check("search filters", reg.option_count >= 1, True)
        reg.action_select()
        await pilot.pause()
        # porciones: el selector trae las sugerencias y rellena los gramos
        por = app.query_one("#rg_portion")
        check("portion options (3 + custom)", len(por._options), 4)
        check("medium preselected in grams", app.query_one("#rg_grams").value, "170")
        por.value = "250"
        await pilot.pause()
        check("large portion fills grams", app.query_one("#rg_grams").value, "250")
        antes = app.db.totals(dt.date.today().isoformat()).kcal
        app.query_one("#rg_grams").value = "250"
        app.query_one("#rg_add").press()
        await pilot.pause()
        tot_ui = app.db.totals(dt.date.today().isoformat())
        check("entry added from the UI (+250 g potato)", round(tot_ui.kcal - antes, 1), 217.5, 0.01)
        # registrar peso
        await pilot.press("4")
        await pilot.pause()
        app.query_one("#pe_kg").value = "79.2"
        app.query_one("#pe_add").press()
        await pilot.pause()
        check("weight from the UI", app.db.weight_latest()[1], 79.2)
        # toggle entreno (los atajos de letra no disparan mientras un Input tiene el foco,
        # así que primero devolvemos el foco a las pestañas)
        await pilot.press("1")
        await pilot.pause()
        app.set_focus(None)
        await pilot.pause()
        before = app.db.day_get(dt.date.today().isoformat())["training"]
        await pilot.press("t")
        await pilot.pause()
        check("training shortcut flips the day type",
              app.db.day_get(dt.date.today().isoformat())["training"], 0 if before else 1)
        # modal de alimento nuevo
        await pilot.press("3")
        await pilot.pause()
        app.query_one("#al_new").press()
        await pilot.pause()
        check("modal opened", isinstance(app.screen, FoodModal), True)
        await pilot.press("escape")
        await pilot.pause()
        check("modal closed", isinstance(app.screen, FoodModal), False)
        # objetivos
        await pilot.press("7")
        await pilot.pause()
        app.query_one("#ob_vitc").value = "250"
        app.query_one("#ob_save").press()
        await pilot.pause()
        check("target edited in the UI", app.db.targets()["vitc"], 250.0)
        hdr = app.query_one("#hoy_header", Static).content
        check("today panel shows the date", dt.date.today().isoformat() in str(hdr), True)
        check("today panel shows kcal", "kcal" in str(hdr), True)
        print("  header:", str(hdr).strip()[:90])

        # bebidas: guardar semana y ver el estado
        await pilot.press("5")
        await pilot.pause()
        app.query_one("#be_water").value = "20"
        app.query_one("#be_coke").value = "1"
        app.query_one("#be_save").press()
        await pilot.pause()
        sem = app.db.drinks_get(str(app.query_one("#be_week").value))
        check("drinks saved from the UI", sem["water"], 20)
        check("week coke count", sem["coke"], 1)

        # pasos por el modal
        await pilot.press("1")
        await pilot.pause()
        app.set_focus(None)
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause()
        app.screen.query_one("#st_steps").value = "5200"
        app.screen.query_one("#st_save").press()
        await pilot.pause()
        check("steps via the modal", app.db.day_get(dt.date.today().isoformat())["steps"], 5200)


asyncio.run(tui())

print()
if FAILS:
    print(f"FAILED {len(FAILS)}: {FAILS}")
    sys.exit(1)
print("ALL OK")
