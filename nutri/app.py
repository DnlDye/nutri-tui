"""Nutrition tracker TUI: macros, minerals, weight and drinks. All local."""
from __future__ import annotations

import datetime as dt

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import (Button, DataTable, Footer, Header, Input, Label,
                             OptionList, Select, Static, TabbedContent, TabPane)
from textual.widgets.option_list import Option

from . import core, db as dbmod, drinks as drinksmod, foods, portions, theme

FOOD_FIELDS = [
    ("name", "Name"), ("grp", "Group"), ("kcal", "kcal/100g"),
    ("protein", "protein g"), ("carbs", "carbs g"), ("fat", "fat g"),
    ("fiber", "fibre g"), ("vitc", "vit C mg"), ("potassium", "potassium mg"),
    ("sodium", "sodium mg"), ("antiox", "antiox 0-3"), ("notes", "notes"),
]


def M(v, fmt="{:.0f}", state=core.NONE) -> Text:
    if v is None:
        return Text("—", style=theme.state_color(core.NONE))
    return Text(fmt.format(v), style=theme.state_color(state))


def badge(state: str) -> Text:
    return Text(core.SYMBOL[state], style=theme.state_color(state))


class LogTable(DataTable):
    """DataTable que además lleva el cursor a la primera/última fila con Home/End."""

    BINDINGS = [
        Binding("home", "row_first", "First", show=False),
        Binding("end", "row_last", "Last", show=False),
    ]

    def action_row_first(self):
        if self.row_count:
            self.move_cursor(row=0)

    def action_row_last(self):
        if self.row_count:
            self.move_cursor(row=self.row_count - 1)


class HoyPane(VerticalScroll):
    """Today's panel: every metric with its traffic light."""

    def compose(self) -> ComposeResult:
        with Horizontal(id="hoy_top"):
            yield Static("", id="hoy_header")
            yield Static("", id="hoy_peso")
        yield DataTable(id="hoy_table", zebra_stripes=True)
        yield Static("", id="hoy_spark")

    def on_mount(self):
        t = self.query_one("#hoy_table", DataTable)
        t.cursor_type = "row"
        t.add_columns("metric", "consumed", "target", "%", "")

    def reload(self):
        app: NutriApp = self.app
        day = dt.date.today().isoformat()
        d = app.db.day_get(day)
        training = bool(d["training"])
        tot = app.db.totals(day)
        steps = d["steps"]
        metrics = core.evaluate(tot, app.targets, training, False, steps)
        kt = core.kcal_target(app.targets, training)

        hdr = Text()
        hdr.append(day + "  ", style="bold")
        hdr.append("TRAINING" if training else "REST",
                   style=f"bold {theme.THEME['ok']}" if training else f"bold {theme.THEME['warn']}")
        hdr.append(f"  ·  target {kt:.0f} kcal\n", style=theme.THEME["muted"])
        hdr.append(f"{tot.kcal:.0f} kcal", style="bold")
        hdr.append(f"  ·  {tot.items} items", style=theme.THEME["muted"])
        self.query_one("#hoy_header", Static).update(hdr)

        prog = core.progress(app.targets, app.db.weight_latest()[1] if app.db.weight_latest() else None)
        p = Text()
        p.append("WEIGHT\n", style=f"bold {theme.THEME['muted']}")
        if prog["actual"]:
            p.append(f"{prog['actual']:.1f} kg", style="bold")
            p.append(f"  from {prog['inicial']:.1f} → {prog['meta']:.0f}\n", style=theme.THEME["muted"])
            p.append(f"lost {prog['bajado']:.1f} kg · to go {prog['falta']:.1f}\n")
            p.append(f"BMI {prog['imc']:.1f} · progress {prog['pct']:.0%}")
        else:
            p.append("no weight logged", style=theme.state_color(core.NONE))
        self.query_one("#hoy_peso", Static).update(p)

        t = self.query_one("#hoy_table", DataTable)
        keep = t.cursor_row
        t.clear()
        for m in metrics:
            pct = ""
            txt_val = m.value_text()
            row_state = m.state
            if m.key in ("kcal", "protein", "vitc", "potassium"):
                tgt = {"kcal": kt, "protein": app.targets["prot_min"],
                       "vitc": app.targets["vitc"],
                       "potassium": app.targets["potasio_min"]}[m.key]
                if tgt and m.value:
                    pct = f"{m.value / tgt:.0%}"
            elif m.key in ("p_pct", "c_pct", "f_pct"):
                pct = ""
            t.add_row(Text(m.label, style="bold" if m.key == "kcal" else ""),
                      M(m.value, m.fmt, row_state),
                      Text(m.target_text, style=theme.THEME["muted"]),
                      Text(pct, style=theme.THEME["muted"]),
                      badge(row_state), key=m.key)
        if t.row_count:
            t.move_cursor(row=min(keep, t.row_count - 1))

        # kcal sparkline (last 14 days)
        end = dt.date.today()
        start = end - dt.timedelta(days=13)
        series = app.db.day_totals(start.isoformat(), end.isoformat())
        vals = []
        for i in range(14):
            key = (start + dt.timedelta(days=i)).isoformat()
            t_day = series.get(key)
            vals.append(t_day.kcal if t_day else None)
        sp = Text()
        sp.append("kcal 14 days  ", style=f"bold {theme.THEME['muted']}")
        sp.append(core.sparkline(vals, 30) or "no data", style=theme.THEME["accent"])
        wser = app.db.weight_series(30)
        sp.append("\nweight 30 days  ", style=f"bold {theme.THEME['muted']}")
        sp.append(core.sparkline([w for _, w in wser], 28) or "no data", style=theme.THEME["accent2"])
        if len(wser) >= 2:
            delta = wser[-1][1] - wser[0][1]
            sp.append(f"   {delta:+.1f} kg", style=theme.THEME["ok"] if delta <= 0 else theme.THEME["fail"])
        sp.append("\n\n[t] training/rest   [s] steps   [r] reload", style=theme.THEME["dim"])
        self.query_one("#hoy_spark", Static).update(sp)

        # (health markers are general goals: they live in the Health tab)


class RegistrarPane(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Static("LOG FOOD", classes="title")
        with Horizontal(classes="formrow"):
            yield Input(value=dt.date.today().isoformat(), id="rg_date", classes="f_date")
            yield Select([(m, m) for m in dbmod.MEALS], value=dbmod.MEALS[0], id="rg_meal",
                         allow_blank=False, classes="f_meal")
        yield Input(placeholder="search food… (enter to pick)", id="rg_search")
        yield OptionList(id="rg_foods")
        with Horizontal(classes="formrow"):
            yield Select([("custom", "custom")], id="rg_portion", allow_blank=False,
                         classes="f_portion")
            yield Input(placeholder="grams", id="rg_grams", classes="f_grams")
            yield Button("Add", id="rg_add", variant="success")
            yield Button("Delete row", id="rg_del", variant="error")
        yield Static("", id="rg_sel")
        yield LogTable(id="rg_table", zebra_stripes=True)
        yield Static("↑↓ scroll the log · Esc back to search · d deletes the selected row",
                     id="rg_hint", classes="hint")

    def on_mount(self):
        self._sel: str | None = None
        self._rows: list = []
        t = self.query_one("#rg_table", DataTable)
        t.cursor_type = "row"
        t.add_columns("meal", "food", "g", "kcal", "P", "C", "F", "vitC", "K", "Na", "antiox")
        self.fill_foods("")
        self.reload()

    # --- lista de alimentos
    def fill_foods(self, search: str):
        ol = self.query_one("#rg_foods", OptionList)
        ol.clear_options()
        self._rows = list(self.app.db.foods(search))[:40]
        self._matches = [r["name"] for r in self._rows]
        for n in self._matches:
            ol.add_option(Option(n))
        if self._matches:
            ol.highlighted = 0

    def on_input_changed(self, ev: Input.Changed):
        if ev.input.id == "rg_search":
            self.fill_foods(ev.value)

    def on_input_submitted(self, ev: Input.Submitted):
        if ev.input.id in ("rg_search",):
            self.query_one("#rg_foods", OptionList).focus()
        elif ev.input.id == "rg_grams":
            self.add_entry()

    # --- porciones sugeridas
    def load_portions(self, name: str):
        row = next((r for r in self._rows if r["name"] == name), None)
        group = (row["grp"] if row else "") or ""
        opts = portions.for_food(name, group)
        sel = self.query_one("#rg_portion", Select)
        if not opts:
            sel.set_options([("custom", "custom")])
            sel.value = "custom"
            self.query_one("#rg_grams", Input).value = ""
            return
        sel.set_options([(f"{label} · {g:g} g", str(g)) for label, g in opts]
                        + [("custom", "custom")])
        idx = portions.default_index(opts)
        sel.value = str(opts[idx][1])
        self.query_one("#rg_grams", Input).value = f"{opts[idx][1]:g}"

    def on_option_list_option_selected(self, ev: OptionList.OptionSelected):
        self._sel = str(ev.option.prompt)
        self.query_one("#rg_sel", Static).update(
            Text(f"food: {self._sel}", style=f"bold {theme.THEME['accent']}"))
        self.load_portions(self._sel)
        self.query_one("#rg_grams", Input).focus()

    def on_select_changed(self, ev: Select.Changed):
        if ev.select.id != "rg_portion":
            return
        val = ev.value
        if val in (None, Select.BLANK, "custom"):
            # el Select postea Changed al montarse; sólo movemos el foco si es el usuario
            if ev.select.has_focus:
                self.query_one("#rg_grams", Input).focus()
            return
        try:
            self.query_one("#rg_grams", Input).value = f"{float(val):g}"
        except (TypeError, ValueError):
            pass

    # --- navegación con flechas: buscar → lista → registro
    def focus_log(self):
        t = self.query_one("#rg_table", DataTable)
        if not t.row_count:
            return
        t.focus()
        t.move_cursor(row=t.row_count - 1)

    def on_key(self, event):
        focused = self.app.focused
        if focused is None:
            return
        if focused.id == "rg_search":
            if event.key == "down":
                self.query_one("#rg_foods", OptionList).focus()
                event.stop()
            elif event.key == "up":
                self.focus_log()
                event.stop()
        elif focused.id == "rg_table":
            if event.key == "escape":
                self.query_one("#rg_search", Input).focus()
                event.stop()

    def on_button_pressed(self, ev: Button.Pressed):
        if ev.button.id == "rg_add":
            self.add_entry()
        elif ev.button.id == "rg_del":
            self.delete_selected()

    def add_entry(self):
        day = self.query_one("#rg_date", Input).value.strip()
        meal = self.query_one("#rg_meal", Select).value
        grams = self.query_one("#rg_grams", Input).value.strip().replace(",", ".")
        try:
            dt.date.fromisoformat(day)
        except ValueError:
            self.app.notify("invalid date (use YYYY-MM-DD)", severity="error")
            return
        if not self._sel:
            self.app.notify("pick a food from the list", severity="error")
            return
        try:
            g = float(grams)
        except ValueError:
            self.app.notify("invalid grams", severity="error")
            return
        self.app.db.entry_add(day, str(meal), self._sel, g)
        self.query_one("#rg_grams", Input).value = ""
        self.query_one("#rg_portion", Select).set_options([("custom", "custom")])
        self.query_one("#rg_portion", Select).value = "custom"
        self.query_one("#rg_search", Input).focus()
        self.app.notify(f"+{self._sel} {g:g} g")
        self.app.reload_all()

    def delete_selected(self):
        t = self.query_one("#rg_table", DataTable)
        if not t.row_count:
            return
        row_key = t.coordinate_to_cell_key((t.cursor_row, 0)).row_key
        try:
            self.app.db.entry_delete(int(row_key.value))
        except (TypeError, ValueError):
            return
        self.app.reload_all()

    def reload(self):
        t = self.query_one("#rg_table", DataTable)
        day = dt.date.today().isoformat()
        t.clear()
        rows = self.app.db.entries(day)
        tgt = self.app.targets
        for r in rows:
            g = r["grams"] / 100
            k = core.Metric("x", "x", r["kcal"] * g, "", core.NONE)
            t.add_row(
                r["meal"], r["name"], M(r["grams"], "{:.0f}"),
                M(r["kcal"] * g), M(r["protein"] * g, "{:.1f}"),
                M(r["carbs"] * g, "{:.1f}"), M(r["fat"] * g, "{:.1f}"),
                M(r["vitc"] * g, "{:.0f}",
                  core.st_min(r["vitc"] * g, 1, False)),
                M(r["potassium"] * g), M(r["sodium"] * g), M(r["antiox"] * g, "{:.1f}"),
                key=str(r["id"]))
        tot = self.app.db.totals(day)
        if rows:
            t.add_row("", Text("TOTAL", style="bold"), "",
                      Text(f"{tot.kcal:.0f}", style="bold"),
                      Text(f"{tot.protein:.1f}", style="bold"),
                      Text(f"{tot.carbs:.1f}", style="bold"),
                      Text(f"{tot.fat:.1f}", style="bold"),
                      Text(f"{tot.vitc:.0f}", style="bold"),
                      Text(f"{tot.potassium:.0f}", style="bold"),
                      Text(f"{tot.sodium:.0f}", style="bold"),
                      Text(f"{tot.antiox:.1f}", style="bold"), key="total")


class AlimentosPane(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Static("FOOD DATABASE (per 100 g / 100 ml)", classes="title")
        yield Static("values are per 100 g · add your own with [n]", classes="hint")
        yield Input(placeholder="filter…", id="al_search")
        yield DataTable(id="al_table", zebra_stripes=True)
        with Horizontal(classes="formrow"):
            yield Button("New [n]", id="al_new", variant="success")
            yield Button("Edit [e]", id="al_edit")
            yield Button("Delete [d]", id="al_del", variant="error")

    def on_mount(self):
        t = self.query_one("#al_table", DataTable)
        t.cursor_type = "row"
        t.add_columns("food", "group", "kcal", "P", "C", "F", "fibre", "vitC", "K", "Na", "antiox")
        self.reload()

    def on_input_changed(self, ev: Input.Changed):
        if ev.input.id == "al_search":
            self.reload(ev.value)

    def reload(self, search: str = ""):
        t = self.query_one("#al_table", DataTable)
        t.clear()
        rows = self.app.db.foods(search)
        self._rows = rows
        for r in rows:
            na_state = core.FAIL if (r["sodium"] or 0) > 600 else core.NONE
            t.add_row(r["name"], r["grp"] or "", M(r["kcal"]),
                      M(r["protein"], "{:.1f}"), M(r["carbs"], "{:.1f}"),
                      M(r["fat"], "{:.1f}"), M(r["fiber"], "{:.1f}"),
                      M(r["vitc"], "{:.0f}"), M(r["potassium"]), M(r["sodium"], "{:.0f}", na_state),
                      M(r["antiox"], "{:.0f}"), key=str(r["id"]))

    def selected_row(self):
        t = self.query_one("#al_table", DataTable)
        if not t.row_count:
            return None
        key = t.coordinate_to_cell_key((t.cursor_row, 0)).row_key
        for r in self._rows:
            if str(r["id"]) == str(key.value):
                return r
        return None

    def on_button_pressed(self, ev: Button.Pressed):
        if ev.button.id == "al_new":
            self.new_food()
        elif ev.button.id == "al_edit":
            self.edit_food()
        elif ev.button.id == "al_del":
            self.del_food()

    def new_food(self):
        def done(result):
            if not result:
                return
            try:
                self.app.db.food_add(**result)
            except Exception as exc:                      # nombre repetido
                self.app.notify(f"could not save: {exc}", severity="error")
                return
            self.app.notify(f"added: {result['name']}")
            self.app.reload_all()
        self.app.push_screen(FoodModal(), done)

    def edit_food(self):
        r = self.selected_row()
        if r is None:
            return

        def done(result):
            if not result:
                return
            name = result.pop("name")
            self.app.db.food_update(r["id"], name=name, **result)
            self.app.notify(f"updated: {name}")
            self.app.reload_all()
        self.app.push_screen(FoodModal(dict(r)), done)

    def del_food(self):
        r = self.selected_row()
        if r is None:
            return
        self.app.db.food_delete(r["id"])
        self.app.notify(f"deleted: {r['name']}")
        self.app.reload_all()


class PesosPane(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Static("BODY WEIGHT", classes="title")
        yield Static("log it fasted, same time of day · goal lives in the Targets tab",
                     classes="hint")
        with Horizontal(classes="formrow"):
            yield Input(value=dt.date.today().isoformat(), id="pe_date", classes="f_date")
            yield Input(placeholder="kg", id="pe_kg", classes="f_grams")
            yield Button("Log", id="pe_add", variant="success")
        yield Static("", id="pe_stats")
        yield Static("", id="pe_spark")
        yield DataTable(id="pe_table", zebra_stripes=True)

    def on_mount(self):
        t = self.query_one("#pe_table", DataTable)
        t.cursor_type = "row"
        t.add_columns("date", "kg", "7d avg", "Δ vs previous")
        self.reload()

    def on_button_pressed(self, ev: Button.Pressed):
        if ev.button.id != "pe_add":
            return
        day = self.query_one("#pe_date", Input).value.strip()
        kg = self.query_one("#pe_kg", Input).value.strip().replace(",", ".")
        try:
            dt.date.fromisoformat(day)
            k = float(kg)
        except ValueError:
            self.app.notify("invalid date or kg", severity="error")
            return
        self.app.db.weight_put(day, k)
        self.query_one("#pe_kg", Input).value = ""
        self.app.notify(f"{k:.1f} kg logged")
        self.app.reload_all()

    def on_input_submitted(self, ev: Input.Submitted):
        if ev.input.id == "pe_kg":
            self.query_one("#pe_add", Button).press()

    def reload(self):
        t = self.query_one("#pe_table", DataTable)
        t.clear()
        serie = self.app.db.weight_series(200)
        self._serie = serie
        for i, (day, kg) in enumerate(reversed(serie)):
            last7 = [v for _, v in serie[max(0, len(serie) - 1 - i - 6): len(serie) - i]]
            avg = sum(last7) / len(last7)
            prev = serie[len(serie) - 1 - i - 1][1] if i + 1 < len(serie) else None
            delta = Text("—", style=theme.state_color(core.NONE))
            if prev is not None:
                d = kg - prev
                delta = Text(f"{d:+.1f}", style=theme.THEME["ok"] if d <= 0 else theme.THEME["fail"])
            t.add_row(day, Text(f"{kg:.1f}", style="bold"),
                      Text(f"{avg:.2f}", style=theme.THEME["muted"]), delta, key=day)

        prog = core.progress(self.app.targets, serie[-1][1] if serie else None)
        s = Text()
        if prog["actual"]:
            s.append(f"{prog['actual']:.1f} kg  ", style="bold")
            s.append(f"start {prog['inicial']:.1f} · goal {prog['meta']:.0f} · ", style=theme.THEME["muted"])
            s.append(f"lost {prog['bajado']:.1f} · to go {prog['falta']:.1f} · ", style=theme.THEME["ok"])
            s.append(f"progress {prog['pct']:.0%} · BMI {prog['imc']:.1f}", style="")
            if prog.get("ffmi"):
                s.append(f" · FFMI {prog['ffmi']:.1f} (norm {prog['nffmi']:.1f}, "
                         f"{prog['band']})", style=theme.THEME["muted"])
                s.append(f" · fat {prog['fat']:.1f} kg ({prog['fat_pct']:.0%})", style="")
            if len(serie) >= 2:
                d0 = dt.date.fromisoformat(serie[0][0])
                d1 = dt.date.fromisoformat(serie[-1][0])
                days = max(1, (d1 - d0).days)
                rate = (serie[0][1] - serie[-1][1]) / days * 7
                s.append(f"  ·  rate {rate:+.2f} kg/week",
                         style=theme.THEME["ok"] if rate >= 0 else theme.THEME["fail"])
        else:
            s.append("sin peso registrado", style=theme.state_color(core.NONE))
        self.query_one("#pe_stats", Static).update(s)

        sp = Text("last 30 entries  ", style=f"bold {theme.THEME['muted']}")
        sp.append(core.sparkline([v for _, v in serie], 60) or "no data", style=theme.THEME["accent2"])
        self.query_one("#pe_spark", Static).update(sp)


class BebidasPane(VerticalScroll):
    """Weekly drink counter: one row per drink, type the number, save."""

    def compose(self) -> ComposeResult:
        yield Static("DRINKS — weekly counter", classes="title")
        yield Static("count what you actually drank · sugar-soda ≤ 10% of the week · "
                     "sucralose ≤ 10 g/day", classes="hint")
        with Horizontal(classes="formrow"):
            yield Select([("", "")], id="be_week", allow_blank=True, classes="f_week")
            yield Button("Save week", id="be_save", variant="success")
            yield Label("sucralose g", classes="drlabel")
            yield Input(placeholder="0", id="be_sucralose", compact=True,
                        classes="drinput")
        yield Static("", id="be_status")
        with Horizontal(id="be_cols"):
            yield Vertical(id="be_col_left", classes="drcol")
            yield Vertical(id="be_col_right", classes="drcol")
        yield Static("RECENT WEEKS", classes="section")
        yield DataTable(id="be_table", zebra_stripes=True)

    def on_mount(self):
        weeks = []
        today = dt.date.today()
        for i in range(12):
            w = dbmod.monday_of(today) - dt.timedelta(days=7 * i)
            weeks.append((w.isoformat(), w.isoformat()))
        sel = self.query_one("#be_week", Select)
        sel.set_options(weeks)
        sel.value = weeks[0][0]

        self._inputs: dict[str, Input] = {}
        for col_id, groups in (("#be_col_left", drinksmod.LEFT_GROUPS),
                               ("#be_col_right", drinksmod.RIGHT_GROUPS)):
            col = self.query_one(col_id, Vertical)
            for group in groups:
                col.mount(Static(group, classes="drgroup"))
                for name in drinksmod.by_group(group):
                    row = Horizontal(classes="drrow")
                    col.mount(row)
                    row.mount(Label(name, classes="drlabel"))
                    inp = Input(compact=True, classes="drinput",
                                id=f"dr_{len(self._inputs)}")
                    row.mount(inp)
                    self._inputs[name] = inp

        t = self.query_one("#be_table", DataTable)
        t.cursor_type = "row"
        t.add_columns("week", "total", "sugar-soda", "% sugar", "sucralose/day", "status")
        self.reload()

    def current_week(self) -> str | None:
        v = self.query_one("#be_week", Select).value
        return None if v in (None, Select.BLANK) else str(v)

    def on_select_changed(self, ev: Select.Changed):
        if ev.select.id == "be_week" and ev.value not in (None, Select.BLANK):
            self.reload()

    def reload(self):
        week = self.current_week()
        if week is None:
            return
        counts = self.app.db.drink_counts(week)
        typing = any(i.has_focus for i in self._inputs.values()) or \
            self.query_one("#be_sucralose", Input).has_focus
        if not typing:                      # no pisar lo que está escribiendo
            for name, inp in self._inputs.items():
                n = counts.get(name, 0)
                inp.value = str(n) if n else ""
            suc = self.app.db.sucralose_get(week)
            self.query_one("#be_sucralose", Input).value = f"{suc:g}" if suc else ""

        s = self.app.db.drink_week_summary(week, self.app.targets)
        line = Text()
        line.append(f"{s['total']} drinks", style="bold")
        line.append(f"  ·  sugar-soda {s['sugar']}", style="")
        if s["sugar_pct"] is not None:
            line.append(f" ({s['sugar_pct']:.0%})",
                        style=theme.state_color(core.OK if s["sugar_pct"] <=
                                               self.app.targets["coca_pct_max"] else core.FAIL))
        line.append(f"  ·  non-sugar {s['non_sugar']}", style=theme.THEME["muted"])
        line.append(f"  ·  sucralose {s['sucralose_day']:.1f} g/day",
                    style=theme.state_color(core.OK if s["sucralose_day"] <=
                                            self.app.targets["sucralosa_max"] else core.FAIL))
        if s["total"]:
            line.append("   " + core.SYMBOL[core.OK if s["ok"] else core.FAIL],
                        style=theme.state_color(core.OK if s["ok"] else core.FAIL))
        self.query_one("#be_status", Static).update(line)

        t = self.query_one("#be_table", DataTable)
        t.clear()
        base = dt.date.fromisoformat(week)
        for i in range(8):
            w = (base - dt.timedelta(days=7 * i)).isoformat()
            r = self.app.db.drink_week_summary(w, self.app.targets)
            if not r["total"] and not r["sucralose"]:
                continue
            state = core.OK if r["ok"] else core.FAIL
            t.add_row(
                w, str(r["total"]), str(r["sugar"]),
                Text(f"{r['sugar_pct']:.0%}" if r["sugar_pct"] is not None else "—",
                     style=theme.state_color(state)),
                Text(f"{r['sucralose_day']:.1f}", style=theme.state_color(state)),
                badge(state), key=w)

    def on_button_pressed(self, ev: Button.Pressed):
        if ev.button.id != "be_save":
            return
        week = self.current_week()
        if week is None:
            return
        counts = {}
        for name, inp in self._inputs.items():
            raw = inp.value.strip().replace(",", ".")
            if not raw:
                counts[name] = 0
                continue
            try:
                counts[name] = int(float(raw))
            except ValueError:
                self.app.notify(f"{name}: numbers only", severity="error")
                return
        raw = self.query_one("#be_sucralose", Input).value.strip().replace(",", ".")
        try:
            suc = float(raw) if raw else 0.0
        except ValueError:
            self.app.notify("sucralose: invalid number", severity="error")
            return
        self.app.db.drink_counts_set(week, counts)
        self.app.db.sucralose_set(week, suc)
        self.app.notify(f"week {week} saved")
        self.app.reload_all()


class HistorialPane(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Static("DAILY HISTORY", classes="title")
        yield Static("last 30 days with entries · green met, red failed",
                     classes="hint")
        yield DataTable(id="hi_table", zebra_stripes=True)

    def on_mount(self):
        t = self.query_one("#hi_table", DataTable)
        t.cursor_type = "row"
        t.add_columns("date", "type", "kcal", "protein", "%P", "%C", "%F", "vitC", "K",
                      "Na", "Na:K", "steps", "status")
        self.reload()

    def reload(self):
        t = self.query_one("#hi_table", DataTable)
        t.clear()
        today = dt.date.today()
        start = today - dt.timedelta(days=29)
        series = self.app.db.day_totals(start.isoformat(), today.isoformat())
        days = self.app.db.logged_days(30)
        tg = self.app.targets
        for day in sorted(series.keys(), reverse=True)[:30]:
            tot = series[day]
            d = self.app.db.day_get(day)
            training = bool(d["training"])
            past = day < today.isoformat()
            ms = {m.key: m for m in core.evaluate(tot, tg, training, past, d["steps"])}
            st = core.day_state(list(ms.values()), past)
            kt = core.kcal_target(tg, training)
            t.add_row(
                day,
                Text("training" if training else "rest",
                     style=theme.THEME["ok"] if training else theme.THEME["muted"]),
                M(tot.kcal, "{:.0f}", ms["kcal"].state),
                M(tot.protein, "{:.1f}", ms["protein"].state),
                M(tot.p_pct, "{:.0%}", ms["p_pct"].state),
                M(tot.c_pct, "{:.0%}", ms["c_pct"].state),
                M(tot.f_pct, "{:.0%}", ms["f_pct"].state),
                M(tot.vitc, "{:.0f}", ms["vitc"].state),
                M(tot.potassium, "{:.0f}", ms["potassium"].state),
                M(tot.sodium, "{:.0f}", ms["sodium"].state),
                M(tot.ratio, "{:.2f}", ms["ratio"].state),
                M(d["steps"], "{:.0f}", ms["steps"].state if d["steps"] else core.NONE),
                badge(st), key=day)


class ObjetivosPane(VerticalScroll):
    """Targets, body composition and the week/month rollups."""

    BODY_KEYS = ("altura", "peso_inicial", "peso_meta", "musculo")

    def compose(self) -> ComposeResult:
        yield Static("TARGETS", classes="title")
        yield Static("changes are saved to the local database · % written as 0-100",
                     classes="hint")
        yield Static("BODY", classes="section")
        yield Vertical(id="ob_body_fields")
        yield Static("", id="ob_body_stats")
        yield Static("DAILY TARGETS", classes="section")
        yield Vertical(id="ob_daily_fields")
        with Horizontal(classes="formrow"):
            yield Button("Save", id="ob_save", variant="success")
            yield Button("Reset defaults", id="ob_reset")
        yield Static("THIS WEEK — live averages", classes="section")
        yield DataTable(id="ob_week", zebra_stripes=True)
        yield Static("STORED WEEKS — frozen when the week closes", classes="section")
        yield DataTable(id="ob_weeks", zebra_stripes=True)
        yield Static("MONTHLY WEIGHT — mean ± SD", classes="section")
        yield DataTable(id="ob_months", zebra_stripes=True)

    def on_mount(self):
        self._inputs: dict[str, Input] = {}
        for box_id, keys in (("#ob_body_fields", self.BODY_KEYS),
                             ("#ob_daily_fields",
                              [k for k in core.TARGET_LABELS if k not in self.BODY_KEYS])):
            box = self.query_one(box_id, Vertical)
            for key in keys:
                row = Horizontal(classes="obrow")
                box.mount(row)
                row.mount(Label(core.TARGET_LABELS[key], classes="oblabel"))
                inp = Input(id=f"ob_{key}", classes="obinput", compact=True)
                row.mount(inp)
                self._inputs[key] = inp
        wk = self.query_one("#ob_week", DataTable)
        wk.add_columns("metric", "average")
        ws = self.query_one("#ob_weeks", DataTable)
        ws.add_columns("week", "days", "kcal", "protein", "weight", "workouts")
        mo = self.query_one("#ob_months", DataTable)
        mo.add_columns("month", "weigh-ins", "mean kg", "SD", "min", "max", "mean ± SD")
        self.reload()

    def reload(self):
        t = self.app.targets
        for key, inp in self._inputs.items():
            v = t.get(key)
            if key in core.PCT_KEYS:
                inp.value = f"{v * 100:.1f}"
            else:
                inp.value = f"{v:g}"

        # --- composición corporal
        weight = self.app.db.weight_latest()
        bc = core.body_comp(t, weight[1] if weight else None)
        line = Text()
        if bc["bmi"]:
            line.append(f"BMI {bc['bmi']:.1f}", style="bold")
            if bc["goal_bmi"]:
                line.append(f"  ·  at goal {bc['goal_bmi']:.1f}", style=theme.THEME["muted"])
            if bc["ffmi"]:
                line.append(f"  ·  FFMI {bc['ffmi']:.1f}", style="bold")
                line.append(f" (normalised {bc['nffmi']:.1f}, {bc['band']})",
                            style=theme.THEME["muted"])
                line.append(f"\nlean {bc['lean']:.1f} kg  ·  fat {bc['fat']:.1f} kg "
                            f"({bc['fat_pct']:.0%})", style="")
            line.append(f"\nmuscle → lean uses {core.MUSCLE_TO_LEAN:.0%}; edit the muscle "
                        f"figure above to match reality.", style=theme.THEME["dim"])
        else:
            line.append("log a weight and set height + muscle mass to see BMI/FFMI",
                        style=theme.THEME["dim"])
        self.query_one("#ob_body_stats", Static).update(line)

        # --- semana en curso
        monday = dbmod.monday_of(dt.date.today()).isoformat()
        r = self.app.db.week_rollup(monday)
        wk = self.query_one("#ob_week", DataTable)
        wk.clear()
        filas = [("days logged", f"{r['days']:d}"), ("workouts", f"{r['workouts']:d}")]
        for label, key, fmt in (("kcal", "kcal", "{:.0f}"), ("protein (g)", "protein", "{:.1f}"),
                                ("carbs (g)", "carbs", "{:.1f}"), ("fat (g)", "fat", "{:.1f}"),
                                ("vitamin C (mg)", "vitc", "{:.0f}"),
                                ("potassium (mg)", "potassium", "{:.0f}"),
                                ("sodium (mg)", "sodium", "{:.0f}")):
            v = r[key]
            filas.append((label, fmt.format(v) if v is not None else "—"))
        wv = r["weight"]
        filas.append(("weight (kg)", f"{wv:.2f} ({r['weight_n']})" if wv else "—"))
        for label, value in filas:
            wk.add_row(label, Text(value, style="bold"))
        wk.add_row("week starts", Text(monday, style=theme.THEME["muted"]))

        # --- semanas guardadas
        ws = self.query_one("#ob_weeks", DataTable)
        ws.clear()
        for w in self.app.db.weeks_list(12):
            ws.add_row(
                w["week"], str(w["days"] or 0),
                Text(f"{w['kcal']:.0f}" if w["kcal"] is not None else "—", style=""),
                Text(f"{w['protein']:.1f}" if w["protein"] is not None else "—", style=""),
                Text(f"{w['weight']:.2f}" if w["weight"] else "—", style="bold"),
                str(w["workouts"] or 0))

        # --- meses con ± desviación estándar
        mo = self.query_one("#ob_months", DataTable)
        mo.clear()
        for m in self.app.db.weight_monthly():
            sd = m["sd"]
            rango = (f"{m['mean'] - sd:.1f} – {m['mean'] + sd:.1f}" if sd else "—")
            mo.add_row(
                m["month"], str(m["n"]),
                Text(f"{m['mean']:.2f}", style="bold"),
                Text(f"± {sd:.2f}" if sd else "—", style=theme.THEME["muted"]),
                Text(f"{m['min']:.1f}", style=""),
                Text(f"{m['max']:.1f}", ""),
                Text(rango, style=theme.THEME["muted"]))

    def on_button_pressed(self, ev: Button.Pressed):
        if ev.button.id == "ob_save":
            vals = {}
            for key, inp in self._inputs.items():
                raw = inp.value.strip().replace(",", ".")
                if not raw:
                    continue
                try:
                    v = float(raw)
                except ValueError:
                    self.app.notify(f"{core.TARGET_LABELS[key]}: invalid number",
                                    severity="error")
                    return
                vals[key] = v / 100 if key in core.PCT_KEYS else v
            self.app.db.targets_save(vals)
            self.app.notify("targets saved")
            self.app.reload_all()
        elif ev.button.id == "ob_reset":
            self.app.db.targets_save(core.TARGETS)
            self.app.notify("targets reset")
            self.app.reload_all()


class SaludPane(VerticalScroll):
    """General health goals: not tracked daily, judged over weeks."""

    def compose(self) -> ComposeResult:
        yield Static("GENERAL HEALTH GOALS", classes="title")
        yield Static("not daily checkboxes: judged on weekly trends", classes="hint")
        yield Static("", id="sa_body")

    def reload(self):
        app: NutriApp = self.app
        tg = app.targets
        hoy = dt.date.today()
        ini = hoy - dt.timedelta(days=27)
        series = app.db.day_totals(ini.isoformat(), hoy.isoformat())
        dias = list(series.values())
        n = max(1, len(dias))
        prom_prot = sum(d.protein for d in dias) / n
        prom_vitc = sum(d.vitc for d in dias) / n
        prom_k = sum(d.potassium for d in dias) / n
        prom_na = sum(d.sodium for d in dias) / n
        prom_ant = sum(d.antiox for d in dias) / n
        entrenos = sum(1 for i in range(28)
                       if app.db.day_get((hoy - dt.timedelta(days=i)).isoformat())["training"])
        p = core.progress(tg, app.db.weight_latest()[1] if app.db.weight_latest() else None)

        def linea(nombre: str, estado: str, detalle: str):
            t = Text()
            t.append(f"{nombre:<28}", style="bold")
            t.append(f"{core.SYMBOL[estado]}  ", style=theme.state_color(estado))
            t.append(detalle, style=theme.THEME["muted"])
            return t

        cuerpo = Text()
        cuerpo.append(f"last 28 days · {len(dias)} days logged · "
                      f"{entrenos} workouts\n\n", style=theme.THEME["dim"])

        piel = core.OK if prom_vitc >= tg["vitc"] and prom_na <= prom_k else core.PENDING
        cuerpo.append_text(linea("Clear skin", piel,
                                 f"vit C {prom_vitc:.0f} mg/day · Na {prom_na:.0f} vs K {prom_k:.0f}"))
        cuerpo.append("\n")
        hinch = core.OK if prom_na <= prom_k * 0.9 else (core.PENDING if prom_na <= prom_k else core.FAIL)
        cuerpo.append_text(linea("No bloating / swelling", hinch,
                                 f"average Na:K {prom_na / prom_k if prom_k else 0:.2f} · "
                                 f"target ≤ {tg['ratio_max']:.2f}"))
        cuerpo.append("\n")
        anti = core.OK if prom_ant >= tg["antiox_min"] else core.PENDING
        cuerpo.append_text(linea("Antioxidant load", anti,
                                 f"{prom_ant:.1f} pts/day (veg, garlic, onion, tomato, coffee)"))
        cuerpo.append("\n")
        mus = core.OK if prom_prot >= tg["prot_min"] and entrenos >= 4 else core.PENDING
        cuerpo.append_text(linea("Muscle kept", mus,
                                 f"protein {prom_prot:.0f} g/day · {entrenos} workouts/28d · 0-2 RIR"))
        cuerpo.append("\n")
        peso_estado = core.NONE
        if p["actual"]:
            peso_estado = core.OK if p["pct"] >= 0.25 else core.PENDING
        cuerpo.append_text(linea("Road to 70 kg", peso_estado,
                                 (f"{p['actual']:.1f} kg · {p['pct']:.0%} of the way · "
                                  f"{p['falta']:.1f} kg to go") if p["actual"] else "no weight logged"))
        cuerpo.append("\n\n")
        cuerpo.append("How to read it: green = the trend already meets it; grey = not enough data "
                      "yet; red = the trend is going against it.\n", style=theme.THEME["dim"])
        cuerpo.append("No checkboxes: missing one day means nothing. The average is what counts.",
                      style=theme.THEME["dim"])
        self.query_one("#sa_body", Static).update(cuerpo)


class FoodModal(ModalScreen):
    """Create or edit a food."""

    BINDINGS = [Binding("escape", "dismiss_modal", "cancelar")]

    def __init__(self, food: dict | None = None):
        super().__init__()
        self.food = food or {}

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal"):
            yield Static("NEW FOOD" if not self.food else "EDIT FOOD",
                         classes="title")
            yield Static("values per 100 g (drinks: per 100 ml)", classes="hint")
            with VerticalScroll(id="fm_fields"):
                for key, label in FOOD_FIELDS:
                    with Horizontal(classes="obrow obsrow" if key == "grp" else "obrow"):
                        yield Label(label, classes="oblabel")
                        if key == "grp":
                            actual = str(self.food.get("grp") or foods.GROUPS[0])
                            if actual not in foods.GROUPS:
                                actual = foods.GROUPS[0]
                            yield Select([(g, g) for g in foods.GROUPS], value=actual,
                                         allow_blank=False, id="fm_grp",
                                         classes="obinput")
                        else:
                            yield Input(value=str(self.food.get(key, "") or ""),
                                        id=f"fm_{key}", classes="obinput", compact=True)
            with Horizontal(classes="formrow"):
                yield Button("Save", id="fm_save", variant="success")
                yield Button("Cancel", id="fm_cancel")

    def on_button_pressed(self, ev: Button.Pressed):
        if ev.button.id == "fm_cancel":
            self.dismiss(None)
            return
        out = {"grp": str(self.query_one("#fm_grp", Select).value)}
        for key, _ in FOOD_FIELDS:
            if key == "grp":
                continue
            raw = self.query_one(f"#fm_{key}", Input).value.strip()
            if key in ("name", "notes"):
                out[key] = raw
            else:
                raw = raw.replace(",", ".")
                if not raw:
                    out[key] = 0.0
                    continue
                try:
                    out[key] = float(raw)
                except ValueError:
                    self.app.notify(f"{key}: invalid number", severity="error")
                    return
        if not out["name"]:
            self.app.notify("name is required", severity="error")
            return
        if out["grp"] not in foods.GROUPS:            # el Select no debería permitirlo
            self.app.notify(f"unknown group: {out['grp']}", severity="error")
            return
        self.dismiss(out)

    def action_dismiss_modal(self):
        self.dismiss(None)


class NutriApp(App):
    CSS = """
    Screen { background: $background; }
    .title { text-style: bold; color: $accent; padding: 1 0 0 0; }
    .section { text-style: bold; color: $nutri-accent2; padding: 1 0 0 0; }
    .hint { color: $nutri-muted; padding: 0 0 1 0; }
    .formrow { height: auto; padding: 1 0; }
    .field { width: 14; height: auto; margin: 0 1 0 0; }
    .f_date { width: 16; }
    .f_week { width: 24; }
    .f_meal { width: 18; }
    .f_grams { width: 12; }
    .f_portion { width: 22; }
    .obrow { height: 1; }
    #ob_body_fields, #ob_daily_fields { height: auto; }
    .oblabel { width: 34; content-align: left middle; color: $nutri-muted; }
    .obinput { width: 20; background: $surface; color: $accent; border: none; }
    .obsrow { height: 3; }
    .modal .obrow { margin-bottom: 1; }
    .modal Input.obinput { background: $nutri-boost; }
    Input.obinput { background: $surface; }
    .obinput:focus { background: $primary; color: $background; text-style: bold; }
    #hoy_top { height: 4; }
    #hoy_header { width: 1fr; padding-right: 2; }
    #hoy_peso { width: 34; }
    #hoy_table { height: auto; }
    #hoy_spark { padding: 1 0 0 0; }
    #rg_foods { height: 8; border: tall $primary; }
    #rg_table { height: 14; }
    #al_table { height: 18; }
    #pe_table { height: 14; }
    #be_table { height: 8; }
    #hi_table { height: 20; }
    #be_cols { height: auto; }
    .drcol { width: 1fr; height: auto; }
    .drgroup { height: 2; text-style: bold; color: $nutri-accent2; padding: 1 0 0 0; }
    .drrow { height: 1; }
    .drlabel { width: 22; color: $nutri-muted; }
    .drinput { width: 8; background: $surface; color: $accent; border: none; }
    .drinput:focus { background: $primary; color: $background; text-style: bold; }
    #ob_week { height: 12; }
    #ob_weeks { height: 10; }
    #ob_months { height: 10; }
    #fm_fields { height: 28; }
    .modal {
        width: 74; height: auto; max-height: 40; padding: 1 2;
        border: thick $primary; background: $panel;
    }
    ModalScreen { align: center middle; }
    DataTable > .datatable--header { background: $panel; color: $accent; text-style: bold; }
    DataTable > .datatable--cursor { background: $primary; color: $background; }
    Tabs { background: $panel; }
    Tab.-active { color: $background; text-style: bold; }
    """

    BINDINGS = [
        Binding("q", "quit", "quit"),
        Binding("r", "reload", "reload"),
        Binding("1", "tab('pane1')", "today"),
        Binding("2", "tab('pane2')", "log"),
        Binding("3", "tab('pane3')", "foods"),
        Binding("4", "tab('pane4')", "weight"),
        Binding("5", "tab('pane5')", "drinks"),
        Binding("6", "tab('pane6')", "history"),
        Binding("7", "tab('pane7')", "health"),
        Binding("8", "tab('pane8')", "targets"),
        Binding("t", "toggle_training", "training/rest"),
    ]

    def __init__(self, db_path: str | None = None, tab: str | None = None):
        super().__init__()
        self._start_tab = tab
        theme.reload()
        self.register_theme(theme.textual_theme())
        self.theme = "lucid"
        self.db = dbmod.DB(db_path)
        self.targets = self.db.targets()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="pane1"):
            with TabPane("Today", id="pane1"):
                yield HoyPane(id="hoy")
            with TabPane("Log", id="pane2"):
                yield RegistrarPane(id="reg")
            with TabPane("Foods", id="pane3"):
                yield AlimentosPane(id="ali")
            with TabPane("Weight", id="pane4"):
                yield PesosPane(id="pes")
            with TabPane("Drinks", id="pane5"):
                yield BebidasPane(id="beb")
            with TabPane("History", id="pane6"):
                yield HistorialPane(id="his")
            with TabPane("Health", id="pane7"):
                yield SaludPane(id="sal")
            with TabPane("Targets", id="pane8"):
                yield ObjetivosPane(id="obj")
        yield Footer()

    def on_mount(self):
        self.title = "Nutrition"
        self.sub_title = str(self.db.path)
        self.reload_all()
        if self._start_tab:
            self.call_after_refresh(self._apply_start_tab)
        self.set_interval(120, self.reload_all)

    # ------------------------------------------------------------- acciones
    def reload_all(self):
        self.targets = self.db.targets()
        try:
            self.db.weeks_store()
        except Exception:
            pass
        for pane in (HoyPane, RegistrarPane, AlimentosPane, PesosPane,
                     BebidasPane, HistorialPane, SaludPane, ObjetivosPane):
            try:
                self.query_one(pane).reload()
            except Exception:
                pass
        self.refresh_subtitle()

    def _apply_start_tab(self):
        try:
            self.query_one(TabbedContent).active = self._start_tab
        except Exception:
            pass

    def refresh_subtitle(self):
        day = dt.date.today().isoformat()
        tot = self.db.totals(day)
        d = self.db.day_get(day)
        kt = core.kcal_target(self.targets, bool(d["training"]))
        self.sub_title = (f"{day} · {'training' if d['training'] else 'rest'} · "
                          f"{tot.kcal:.0f}/{kt:.0f} kcal · {self.db.path}")

    def action_reload(self):
        theme.reload()
        self.register_theme(theme.textual_theme())
        self.theme = "lucid"
        self.reload_all()
        self.notify("reloaded (palette re-read)")

    def action_tab(self, pane: str):
        self.query_one(TabbedContent).active = pane

    def action_toggle_training(self):
        day = dt.date.today().isoformat()
        new = self.db.toggle_training(day)
        self.notify("TRAINING day" if new else "REST day")
        self.reload_all()

    def on_key(self, event):
        # tab shortcuts
        focused = self.focused
        if isinstance(focused, Input):
            return
        pane = None
        try:
            pane = self.query_one(TabbedContent).active
        except Exception:
            return
        if event.key == "n" and pane == "pane3":
            self.query_one(AlimentosPane).new_food()
            event.stop()
        elif event.key == "e" and pane == "pane3":
            self.query_one(AlimentosPane).edit_food()
            event.stop()
        elif event.key == "d" and pane == "pane3":
            self.query_one(AlimentosPane).del_food()
            event.stop()
        elif event.key == "d" and pane == "pane2":
            self.query_one(RegistrarPane).delete_selected()
            event.stop()
        elif event.key == "s" and pane == "pane1":
            self._ask_steps()
            event.stop()

    def _ask_steps(self):
        self.push_screen(StepsModal(self.db.day_get(dt.date.today().isoformat())),
                         self._set_steps)

    def _set_steps(self, value):
        if value is None:
            return
        self.db.day_set(dt.date.today().isoformat(), steps=value)
        self.reload_all()


class StepsModal(ModalScreen):
    BINDINGS = [Binding("escape", "cancel", "cancelar")]

    def __init__(self, day: dict):
        super().__init__()
        self.day = day

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal"):
            yield Static("STEPS TODAY", classes="title")
            yield Input(value=str(self.day.get("steps") or ""), placeholder="steps",
                        id="st_steps", classes="f_grams")
            with Horizontal(classes="formrow"):
                yield Button("Save", id="st_save", variant="success")
                yield Button("Cancel", id="st_cancel")

    def on_button_pressed(self, ev: Button.Pressed):
        if ev.button.id == "st_cancel":
            self.dismiss(None)
            return
        raw = self.query_one("#st_steps", Input).value.strip()
        try:
            self.dismiss(int(float(raw)) if raw else 0)
        except ValueError:
            self.app.notify("invalid number", severity="error")

    def action_cancel(self):
        self.dismiss(None)


def main(argv: list[str] | None = None):
    import argparse
    ap = argparse.ArgumentParser(prog="nutri", description="Terminal nutrition tracker")
    ap.add_argument("--db", help="sqlite database path (default: ~/.local/share/nutricion)")
    ap.add_argument("--tab", choices=["pane1", "pane2", "pane3", "pane4", "pane5",
                                      "pane6", "pane7", "pane8"],
                    help="starting tab (1 today ... 8 targets)")
    args = ap.parse_args(argv)
    NutriApp(args.db, args.tab).run()


if __name__ == "__main__":
    main()
