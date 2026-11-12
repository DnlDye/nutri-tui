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

from nutri import core, db as dbmod, drinks, foods, portions  # noqa: E402

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
T = dict(core.TARGETS, altura=167, peso_inicial=84.5, peso_meta=70.0,
         musculo=33.0)   # fixed fixture, independent of the shipped defaults
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

# la proteína es sugerencia: pasarse no es fallar
mucho = core.totals_from_rows([
    dict(grams=600, kcal=165, protein=31.0, carbs=0, fat=3.6, vitc=0, potassium=256, sodium=74, antiox=0),
    dict(grams=300, kcal=87, protein=1.9, carbs=20.1, fat=0.1, vitc=13, potassium=379, sodium=5, antiox=2),
])
ms_prot = {m.key: m for m in core.evaluate(mucho, T, True, True)}
check("protein 191 g past day -> still ok (no ceiling)", ms_prot["protein"].state, core.OK)
check("protein target text says suggested", "suggested" in ms_prot["protein"].target_text, True)
poco = core.totals_from_rows([
    dict(grams=100, kcal=130, protein=2.7, carbs=28.2, fat=0.3, vitc=0, potassium=35, sodium=1, antiox=0),
])
ms_poco = {m.key: m for m in core.evaluate(poco, T, False, True)}
check("protein 2.7 g on a past day -> red", ms_poco["protein"].state, core.FAIL)
ms_alto = {m.key: m for m in core.evaluate(mucho, T, True, True)}
check("% protein 43% past day -> ok (suggestion)", ms_alto["p_pct"].state, core.OK)
check("% protein target says suggested", "suggested" in ms_alto["p_pct"].target_text, True)

# condimentos nuevos
nombres = {f[0] for f in foods.SEED}
for c in ("Ketchup", "Mayonnaise", "Light mayonnaise", "Soy sauce",
          "Worcestershire sauce", "Yellow mustard", "Hot sauce", "Sriracha",
          "BBQ sauce", "Balsamic vinegar", "Apple cider vinegar"):
    check(f"condiment {c}", c in nombres, True)

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

# ---------------------------------------------------- stats & body comp
print("== stats / body composition")
st = core.stats([79.6, 79.4, 79.8])
check("stats n", st["n"], 3)
check("stats mean", round(st["mean"], 4), 79.6, 1e-9)
check("stats sample SD", round(st["sd"], 4), 0.2, 1e-9)
check("stats range", (st["min"], st["max"]), (79.4, 79.8))
check("stats single value has no SD", core.stats([80.0])["sd"], None)
check("stats empty", core.stats([])["n"], 0)

bc = core.body_comp(T, 79.8)
check("BMI", round(bc["bmi"], 2), 28.61, 0.01)
check("lean mass from muscle", round(bc["lean"], 2), 63.46, 0.02)
check("fat mass", round(bc["fat"], 2), 16.34, 0.02)
check("fat %", round(bc["fat_pct"], 3), 0.205, 0.002)
check("FFMI", round(bc["ffmi"], 2), 22.76, 0.02)
check("normalised FFMI", round(bc["nffmi"], 2), 23.55, 0.02)
check("FFMI band", bc["band"], "excellent")
check("goal BMI", round(bc["goal_bmi"], 1), 25.1, 0.05)
check("no weight -> no BMI", core.body_comp(T, None)["bmi"], None)
sin_musculo = dict(T, musculo=0)
check("no muscle -> BMI only", core.body_comp(sin_musculo, 79.8)["ffmi"], None)

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
check("seeded foods", len(d.foods()), len(foods.SEED))
check("potato exists", d.food_by_name("Potato (boiled)")["kcal"], 87.0)
check("soy sauce is salty", d.food_by_name("Soy sauce")["sodium"], 5493.0)
check("ketchup kcal", d.food_by_name("Ketchup")["kcal"], 101.0)
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
# --- bebidas: contador por bebida
d.drink_counts_set("2026-11-09", {"Water": 20, "Coffee (drip)": 7, "Black Tea": 2,
                                  "Sugar-soda": 1, "Non-sugar soda": 4})
cnt = d.drink_counts("2026-11-09")
check("drink counter saved", cnt["Sugar-soda"], 1)
check("counter covers the whole catalogue", len(cnt), len(drinks.DRINKS))
# la búsqueda entiende los nombres en español guardados en las notas
check("search finds a food by its Spanish name",
      "Avocado" in [r["name"] for r in d.foods("Aguacate")], True)
check("search by English still works", len(d.foods("Tomato")) >= 3, True)
check("untouched drink is zero", cnt["Latte"], 0)
check("drinks total", sum(cnt.values()), 34)
sm = d.drink_week_summary("2026-11-09", T)
check("sugar share", round(sm["sugar_pct"], 3), round(1 / 34, 3))
check("non-sugar soda counted apart", sm["non_sugar"], 4)
check("week under the sugar rule", sm["ok"], True)
d.sucralose_set("2026-11-09", 84)          # 12 g/day, over the 10 g limit
check("sucralose stored", d.sucralose_get("2026-11-09"), 84.0)
check("sucralose over the limit fails the week",
      d.drink_week_summary("2026-11-09", T)["ok"], False)
d.sucralose_set("2026-11-09", 0)
check("sugar-soda over 10% fails the week",
      d.drink_week_summary("2026-11-09", dict(T, coca_pct_max=0.0))["ok"], False)
# migración de las columnas fijas de la primera versión
tmp_legacy = Path(tempfile.mkdtemp()) / "legacy.db"
dl = dbmod.DB(tmp_legacy)
dl.con.execute("INSERT INTO drinks (week,water,coffee,tea,coke,other,sucralose)"
               " VALUES ('2026-11-02',20,7,2,1,0,6)")
dl.con.commit(); dl.close()
dl2 = dbmod.DB(tmp_legacy)
leg = dl2.drink_counts("2026-11-02")
check("legacy water migrated", leg["Water"], 20)
check("legacy coke became sugar-soda", leg["Sugar-soda"], 1)
check("legacy sucralose migrated", dl2.sucralose_get("2026-11-02"), 6.0)
dl2.close()
d.targets_save({**T, "prot_max": 150})
check("target saved", d.targets()["prot_max"], 150.0)
check("untouched target", d.targets()["prot_min"], 120.0)
d.food_add("Instant oats", "Grain", 380, 13.0, 60.0, 6.0, 10.0, 0, 350, 3, 1, "")
check("new food", d.food_by_name("Instant oats")["kcal"], 380.0)
d.food_delete(d.food_by_name("Instant oats")["id"])
check("food deleted", d.food_by_name("Instant oats"), None)
check("days with entries", d.logged_days(), ["2026-11-11"])

# ---------------------------------------------------------------- TUI
print("== TUI (headless)")


async def tui():
    from nutri.app import NutriApp, FoodModal
    app = NutriApp(str(tmp))
    async with app.run_test(size=(140, 42)) as pilot:
        await pilot.pause()
        from textual.widgets import DataTable, Input, Select, Static, TabbedContent
        # regresión: la app abre en Today (un Changed del Select robaba el foco
        # en una pestaña oculta y TabbedContent saltaba a Log)
        check("app opens on Today", app.query_one(TabbedContent).active, "pane1")
        # el panel de hoy depende del día real: fijamos los pasos de hoy
        app.db.day_set(dt.date.today().isoformat(), steps=4200)
        app.reload_all()
        await pilot.pause()
        hoy = app.query_one("#hoy_table", DataTable)
        check("today panel rows (10 metrics + steps)", hoy.row_count, 11)
        ali = app.query_one("#al_table", DataTable)
        check("food table rows", ali.row_count, len(foods.SEED))
        hi = app.query_one("#hi_table", DataTable)
        await pilot.pause()
        check("history has the test day", hi.row_count, 1)
        # cambiar de pestaña
        await pilot.press("2")
        await pilot.pause()
        check("log tab active",
              app.query_one(TabbedContent).active, "pane2")
        # alta de una entrada por la propia UI
        app.query_one("#rg_search").value = "Potato (boiled)"
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
        grp_sel = app.screen.query_one("#fm_grp", Select)
        check("group is a fixed picker", len(grp_sel._options), len(foods.GROUPS))
        check("no free-text group field",
              [i.id for i in app.screen.query("Input") if i.id == "fm_grp"], [])
        app.screen.query_one("#fm_name", Input).value = "Pumpkin"
        grp_sel.value = "Vegetable"
        app.screen.query_one("#fm_kcal", Input).value = "26"
        app.screen.query_one("#fm_protein", Input).value = "1"
        app.screen.query_one("#fm_save").press()
        await pilot.pause()
        nuevo = app.db.food_by_name("Pumpkin")
        check("food saved from the modal", nuevo is not None, True)
        check("food saved with the picked group", nuevo["grp"], "Vegetable")
        app.db.food_delete(nuevo["id"])
        await pilot.press("escape")
        await pilot.pause()
        check("modal closed", isinstance(app.screen, FoodModal), False)
        # objetivos
        await pilot.press("8")
        await pilot.pause()
        check("targets tab opens", app.query_one(TabbedContent).active, "pane8")
        app.query_one("#ob_vitc").value = "250"
        app.query_one("#ob_save").press()
        await pilot.pause()
        check("target edited in the UI", app.db.targets()["vitc"], 250.0)
        # regresión: un Vertical dentro de VerticalScroll colapsa a 1 fila si no
        # lleva height: auto, y los inputs quedan invisibles (query_one los ve igual)
        for bid in ("#ob_body_fields", "#ob_daily_fields"):
            box = app.query_one(bid)
            rows = list(box.query(".obrow"))
            check(f"{bid} is tall enough for its rows", box.size.height, len(rows))
            check(f"{bid} rows are laid out in order", len({r.region.y for r in rows}), len(rows))
        check("weekly table has rows", app.query_one("#ob_week").row_count > 5, True)
        check("monthly table lists both months", app.query_one("#ob_months").row_count, 2)
        cuerpo = str(app.query_one("#ob_body_stats", Static).content)
        check("body panel shows FFMI", "FFMI" in cuerpo, True)
        # el campo de músculo entra en la composición al guardar
        app.query_one("#ob_musculo").value = "36"
        app.query_one("#ob_save").press()
        await pilot.pause()
        check("muscle saved", app.db.targets()["musculo"], 36.0)
        nuevo = str(app.query_one("#ob_body_stats", Static).content)
        check("composition follows the muscle figure", nuevo != cuerpo, True)
        hdr = app.query_one("#hoy_header", Static).content
        check("today panel shows the date", dt.date.today().isoformat() in str(hdr), True)
        check("today panel shows kcal", "kcal" in str(hdr), True)
        print("  header:", str(hdr).strip()[:90])

        # bebidas: contador por bebida
        await pilot.press("5")
        await pilot.pause()
        check("drinks tab opens", app.query_one(TabbedContent).active, "pane5")
        from nutri.app import BebidasPane
        pane = app.query_one(BebidasPane)
        check("one input per drink", len(pane._inputs), len(drinks.DRINKS))
        for bid in ("#be_col_left", "#be_col_right"):
            col = app.query_one(bid)
            rows = list(col.query(".drrow"))
            heads = list(col.query(".drgroup"))
            check(f"{bid} is laid out", col.size.height, len(rows) + len(heads) * 2)
        for inp in pane._inputs.values():      # empezar de cero
            inp.value = ""
        pane._inputs["Sugar-soda"].value = "2"
        pane._inputs["Coffee (drip)"].value = "7"
        pane._inputs["Latte"].value = "3"
        pane._inputs["Water"].value = "20"
        app.query_one("#be_sucralose").value = "5"
        app.query_one("#be_save").press()
        await pilot.pause()
        semana = pane.current_week()
        cnt_ui = app.db.drink_counts(semana)
        check("drink saved from the UI", cnt_ui["Sugar-soda"], 2)
        check("all drinks saved", sum(cnt_ui.values()), 32)
        check("sucralose saved from the UI", app.db.sucralose_get(semana), 5.0)
        sm_ui = app.db.drink_week_summary(semana, app.targets)
        check("sugar share of the week", round(sm_ui["sugar_pct"], 3), round(2 / 32, 3))
        check("week status ok", sm_ui["ok"], True)

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

        # log table: flechas para desplazarse, Esc para volver a buscar
        for _ in range(25):
            app.db.entry_add(dt.date.today().isoformat(), "Lunch", "Tomato", 100)
        app.reload_all()
        await pilot.pause()
        await pilot.press("2")
        await pilot.pause()
        app.query_one("#rg_search").focus()
        await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        check("down from the search box goes to the food list", app.focused.id, "rg_foods")
        app.query_one("#rg_search").focus()
        await pilot.pause()
        await pilot.press("up")
        await pilot.pause()
        check("up from the search box jumps into the log", app.focused.id, "rg_table")
        tbl = app.query_one("#rg_table")
        check("log cursor starts on the newest row", tbl.cursor_row, tbl.row_count - 1)
        check("log is scrolled to the bottom", tbl.scroll_y > 0, True)
        top = tbl.scroll_y
        for _ in range(15):
            await pilot.press("up")
        await pilot.pause()
        check("arrow up moves the log cursor", tbl.cursor_row, tbl.row_count - 1 - 15)
        check("the view follows the cursor", tbl.scroll_y <= top, True)
        await pilot.press("home")
        await pilot.pause()
        check("home goes to the first row", tbl.cursor_row, 0)
        check("first row means no scroll", tbl.scroll_y, 0)
        await pilot.press("escape")
        await pilot.pause()
        check("escape returns to the search box", app.focused.id, "rg_search")


asyncio.run(tui())

print()
if FAILS:
    print(f"FAILED {len(FAILS)}: {FAILS}")
    sys.exit(1)
print("ALL OK")
