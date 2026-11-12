"""Local database (SQLite). Everything lives on the user's disk."""
from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
from pathlib import Path

from . import core, drinks as drinksmod, foods

SCHEMA = """
CREATE TABLE IF NOT EXISTS foods (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    grp TEXT DEFAULT '',
    kcal REAL DEFAULT 0, protein REAL DEFAULT 0, carbs REAL DEFAULT 0,
    fat REAL DEFAULT 0, fiber REAL DEFAULT 0, vitc REAL DEFAULT 0,
    potassium REAL DEFAULT 0, sodium REAL DEFAULT 0, antiox REAL DEFAULT 0,
    notes TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY,
    day TEXT NOT NULL,
    meal TEXT DEFAULT 'Comida',
    food_id INTEGER NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
    grams REAL NOT NULL,
    note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS days (
    day TEXT PRIMARY KEY,
    training INTEGER DEFAULT 0,
    steps INTEGER,
    skin TEXT DEFAULT '',
    swelling TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS weights (
    day TEXT PRIMARY KEY,
    kg REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS drink_counts (
    week TEXT NOT NULL,
    drink TEXT NOT NULL,
    n INTEGER DEFAULT 0,
    PRIMARY KEY (week, drink)
);
CREATE TABLE IF NOT EXISTS drink_weeks (
    week TEXT PRIMARY KEY,
    sucralose REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS drinks (
    week TEXT PRIMARY KEY,
    water INTEGER DEFAULT 0, coffee INTEGER DEFAULT 0, tea INTEGER DEFAULT 0,
    coke INTEGER DEFAULT 0, other INTEGER DEFAULT 0, sucralose REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS weeks (
    week TEXT PRIMARY KEY,
    days INTEGER DEFAULT 0,
    kcal REAL, protein REAL, carbs REAL, fat REAL,
    vitc REAL, potassium REAL, sodium REAL,
    weight REAL, weight_n INTEGER DEFAULT 0, workouts INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_entries_day ON entries(day);
"""

MEALS = foods.MEALS


def default_path() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "nutricion" / "nutricion.db"


class DB:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.path)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys = ON")
        self.con.executescript(SCHEMA)
        self._migrate()
        self._migrate_drinks()
        self._seed()
        self.con.commit()

    # ----------------------------------------------------------------- private
    def _seed(self):
        """Insert catalogue foods that are missing (never touches the user's own)."""
        self.con.executemany(
            "INSERT OR IGNORE INTO foods (name,grp,kcal,protein,carbs,fat,fiber,vitc,"
            "potassium,sodium,antiox,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", foods.SEED)

    def _migrate(self):
        """Rename first-version (Spanish) foods, keeping the id and its log entries."""
        for old, new in foods.RENAMES.items():
            have_old = self.con.execute("SELECT id FROM foods WHERE name=?", (old,)).fetchone()
            have_new = self.con.execute("SELECT id FROM foods WHERE name=?", (new,)).fetchone()
            if have_old and not have_new:
                self.con.execute("UPDATE foods SET name=? WHERE id=?", (new, have_old["id"]))

    def close(self):
        self.con.close()

    # ------------------------------------------------------------------- food
    def foods(self, search: str = "") -> list[sqlite3.Row]:
        q = "SELECT * FROM foods"
        args: list = []
        if search:
            q += " WHERE name LIKE ?"
            args.append(f"%{search}%")
        q += " ORDER BY name COLLATE NOCASE"
        return self.con.execute(q, args).fetchall()

    def food_by_name(self, name: str) -> sqlite3.Row | None:
        return self.con.execute("SELECT * FROM foods WHERE name = ?", (name,)).fetchone()

    def food_add(self, name, grp="", kcal=0, protein=0, carbs=0, fat=0, fiber=0,
                 vitc=0, potassium=0, sodium=0, antiox=0, notes="") -> int:
        cur = self.con.execute(
            "INSERT INTO foods (name,grp,kcal,protein,carbs,fat,fiber,vitc,potassium,"
            "sodium,antiox,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (name.strip(), grp, kcal, protein, carbs, fat, fiber, vitc,
             potassium, sodium, antiox, notes))
        self.con.commit()
        return cur.lastrowid

    def food_update(self, fid: int, **fields):
        if not fields:
            return
        sets = ", ".join(f"{k}=?" for k in fields)
        self.con.execute(f"UPDATE foods SET {sets} WHERE id=?", (*fields.values(), fid))
        self.con.commit()

    def food_delete(self, fid: int):
        self.con.execute("DELETE FROM foods WHERE id=?", (fid,))
        self.con.commit()

    # -------------------------------------------------------------------- log
    def entry_add(self, day: str, meal: str, food_name: str, grams: float, note="") -> int:
        f = self.food_by_name(food_name)
        if f is None:
            raise KeyError(f"alimento no existe: {food_name}")
        cur = self.con.execute(
            "INSERT INTO entries (day,meal,food_id,grams,note) VALUES (?,?,?,?,?)",
            (day, meal, f["id"], float(grams), note))
        self.con.commit()
        return cur.lastrowid

    def entries(self, day: str) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT e.id, e.meal, e.grams, e.note, f.name, f.kcal, f.protein, f.carbs,"
            " f.fat, f.vitc, f.potassium, f.sodium, f.antiox"
            " FROM entries e JOIN foods f ON f.id = e.food_id"
            " WHERE e.day = ? ORDER BY e.id", (day,)).fetchall()

    def entry_delete(self, eid: int):
        self.con.execute("DELETE FROM entries WHERE id=?", (eid,))
        self.con.commit()

    def totals(self, day: str) -> core.Totals:
        return core.totals_from_rows(self.entries(day))

    def day_totals(self, start: str, end: str) -> dict[str, core.Totals]:
        rows = self.con.execute(
            "SELECT e.day, e.grams, f.kcal, f.protein, f.carbs, f.fat, f.vitc,"
            " f.potassium, f.sodium, f.antiox"
            " FROM entries e JOIN foods f ON f.id = e.food_id"
            " WHERE e.day BETWEEN ? AND ? ORDER BY e.day", (start, end)).fetchall()
        out: dict[str, list] = {}
        for r in rows:
            out.setdefault(r["day"], []).append(r)
        return {d: core.totals_from_rows(rs) for d, rs in out.items()}

    def logged_days(self, limit: int = 400) -> list[str]:
        rows = self.con.execute(
            "SELECT DISTINCT day FROM entries ORDER BY day DESC LIMIT ?", (limit,))
        return [r["day"] for r in rows]

    # ------------------------------------------------------------------ days
    def day_get(self, day: str) -> dict:
        r = self.con.execute("SELECT * FROM days WHERE day=?", (day,)).fetchone()
        if r:
            return dict(r)
        return {"day": day, "training": 0, "steps": None, "skin": "", "swelling": ""}

    def day_set(self, day: str, **fields):
        cur = self.day_get(day)
        cur.update({k: v for k, v in fields.items() if k != "day"})
        self.con.execute(
            "INSERT INTO days (day,training,steps,skin,swelling) VALUES (?,?,?,?,?)"
            " ON CONFLICT(day) DO UPDATE SET training=excluded.training,"
            " steps=excluded.steps, skin=excluded.skin, swelling=excluded.swelling",
            (day, cur["training"], cur["steps"], cur["skin"], cur["swelling"]))
        self.con.commit()

    def toggle_training(self, day: str) -> int:
        d = self.day_get(day)
        new = 0 if d["training"] else 1
        self.day_set(day, training=new)
        return new

    # ---------------------------------------------------------------- weight
    def weight_put(self, day: str, kg: float):
        self.con.execute(
            "INSERT INTO weights (day,kg) VALUES (?,?) ON CONFLICT(day) DO UPDATE SET kg=excluded.kg",
            (day, float(kg)))
        self.con.commit()

    def weight_get(self, day: str) -> float | None:
        r = self.con.execute("SELECT kg FROM weights WHERE day=?", (day,)).fetchone()
        return r["kg"] if r else None

    def weight_latest(self) -> tuple[str, float] | None:
        r = self.con.execute("SELECT day, kg FROM weights ORDER BY day DESC LIMIT 1").fetchone()
        return (r["day"], r["kg"]) if r else None

    def weight_series(self, limit: int = 60) -> list[tuple[str, float]]:
        rows = self.con.execute(
            "SELECT day, kg FROM weights ORDER BY day DESC LIMIT ?", (limit,)).fetchall()
        return [(r["day"], r["kg"]) for r in reversed(rows)]

    def weights_between(self, start: str, end: str) -> list[tuple[str, float]]:
        rows = self.con.execute(
            "SELECT day, kg FROM weights WHERE day BETWEEN ? AND ? ORDER BY day",
            (start, end)).fetchall()
        return [(r["day"], r["kg"]) for r in rows]

    def weight_previous(self, day: str) -> float | None:
        r = self.con.execute(
            "SELECT kg FROM weights WHERE day < ? ORDER BY day DESC LIMIT 1", (day,)).fetchone()
        return r["kg"] if r else None

    # ----------------------------------------------------------- weeks/months
    def week_rollup(self, monday: str) -> dict:
        """Averages for one Mon-Sun week (live; nothing is stored here)."""
        start = dt.date.fromisoformat(monday)
        end = (start + dt.timedelta(days=6)).isoformat()
        days = self.day_totals(monday, end)
        n = len(days)
        weights = [kg for _, kg in self.weights_between(monday, end)]
        workouts = self.con.execute(
            "SELECT COUNT(*) c FROM days WHERE day BETWEEN ? AND ? AND training=1",
            (monday, end)).fetchone()["c"]

        def avg(field):
            return sum(getattr(t, field) for t in days.values()) / n if n else None

        wstats = core.stats(weights)
        return {
            "week": monday, "days": n, "workouts": workouts,
            "kcal": avg("kcal"), "protein": avg("protein"), "carbs": avg("carbs"),
            "fat": avg("fat"), "vitc": avg("vitc"), "potassium": avg("potassium"),
            "sodium": avg("sodium"),
            "weight": wstats["mean"], "weight_n": wstats["n"],
        }

    def weeks_store(self, today: dt.date | None = None) -> int:
        """Freeze every closed week into the weeks table (idempotent)."""
        today = today or dt.date.today()
        current = monday_of(today)
        first = self.start_day()
        if not first:
            return 0
        week = monday_of(dt.date.fromisoformat(first))
        stored = 0
        while week < current:
            r = self.week_rollup(week.isoformat())
            if r["days"] or r["weight_n"]:
                self.con.execute(
                    "INSERT INTO weeks (week,days,kcal,protein,carbs,fat,vitc,potassium,"
                    "sodium,weight,weight_n,workouts) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
                    " ON CONFLICT(week) DO UPDATE SET days=excluded.days,"
                    " kcal=excluded.kcal, protein=excluded.protein, carbs=excluded.carbs,"
                    " fat=excluded.fat, vitc=excluded.vitc, potassium=excluded.potassium,"
                    " sodium=excluded.sodium, weight=excluded.weight,"
                    " weight_n=excluded.weight_n, workouts=excluded.workouts",
                    (r["week"], r["days"], r["kcal"], r["protein"], r["carbs"], r["fat"],
                     r["vitc"], r["potassium"], r["sodium"], r["weight"],
                     r["weight_n"], r["workouts"]))
                stored += 1
            week += dt.timedelta(days=7)
        self.con.commit()
        return stored

    def weeks_list(self, limit: int = 12) -> list[dict]:
        rows = self.con.execute(
            "SELECT * FROM weeks ORDER BY week DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def weight_monthly(self) -> list[dict]:
        """Per calendar month: weigh-ins, mean, sample SD, range."""
        rows = self.con.execute(
            "SELECT day, kg FROM weights ORDER BY day").fetchall()
        buckets: dict[str, list[float]] = {}
        for r in rows:
            buckets.setdefault(r["day"][:7], []).append(r["kg"])
        out = []
        for month in sorted(buckets, reverse=True):
            st = core.stats(buckets[month])
            st["month"] = month
            out.append(st)
        return out

    # ---------------------------------------------------------------- drinks
    def drink_counts(self, week: str) -> dict[str, int]:
        """Counts for every drink in the catalogue (0 when untouched)."""
        rows = self.con.execute(
            "SELECT drink, n FROM drink_counts WHERE week=?", (week,)).fetchall()
        have = {r["drink"]: r["n"] for r in rows}
        return {name: int(have.get(name, 0)) for name in drinksmod.names()}

    def drink_counts_set(self, week: str, counts: dict[str, int]):
        for name, n in counts.items():
            n = int(n or 0)
            if n <= 0:
                self.con.execute(
                    "DELETE FROM drink_counts WHERE week=? AND drink=?", (week, name))
            else:
                self.con.execute(
                    "INSERT INTO drink_counts (week,drink,n) VALUES (?,?,?)"
                    " ON CONFLICT(week,drink) DO UPDATE SET n=excluded.n",
                    (week, name, n))
        self.con.commit()

    def sucralose_get(self, week: str) -> float:
        r = self.con.execute(
            "SELECT sucralose FROM drink_weeks WHERE week=?", (week,)).fetchone()
        return float(r["sucralose"] or 0) if r else 0.0

    def sucralose_set(self, week: str, grams: float):
        self.con.execute(
            "INSERT INTO drink_weeks (week,sucralose) VALUES (?,?)"
            " ON CONFLICT(week) DO UPDATE SET sucralose=excluded.sucralose",
            (week, float(grams or 0)))
        self.con.commit()

    def drink_week_summary(self, week: str, targets: dict) -> dict:
        counts = self.drink_counts(week)
        total = sum(counts.values())
        sugar = counts.get(drinksmod.SUGAR_SODA, 0)
        non_sugar = counts.get(drinksmod.NON_SUGAR_SODA, 0)
        suc = self.sucralose_get(week)
        pct = (sugar / total) if total else None
        per_day = suc / 7 if suc else 0.0
        ok = (total > 0 and pct is not None and pct <= targets["coca_pct_max"]
              and per_day <= targets["sucralosa_max"])
        return {"week": week, "counts": counts, "total": total, "sugar": sugar,
                "non_sugar": non_sugar, "sugar_pct": pct, "sucralose": suc,
                "sucralose_day": per_day, "ok": ok}

    def drink_weeks_history(self, week: str, n: int = 8) -> list[dict]:
        base = dt.date.fromisoformat(week)
        return [self.drink_week_summary((base - dt.timedelta(days=7 * i)).isoformat(), {})
                for i in range(n)]

    def _migrate_drinks(self):
        """First version had fixed columns; move them into the counter once."""
        if self.con.execute("SELECT 1 FROM drink_counts LIMIT 1").fetchone():
            return
        for r in self.con.execute("SELECT * FROM drinks").fetchall():
            for col, name in drinksmod.LEGACY_MAP.items():
                if r[col]:
                    self.con.execute(
                        "INSERT INTO drink_counts (week,drink,n) VALUES (?,?,?)"
                        " ON CONFLICT(week,drink) DO UPDATE SET n=excluded.n",
                        (r["week"], name, r[col]))
            if r["sucralose"]:
                self.con.execute(
                    "INSERT INTO drink_weeks (week,sucralose) VALUES (?,?)"
                    " ON CONFLICT(week) DO UPDATE SET sucralose=excluded.sucralose",
                    (r["week"], r["sucralose"]))

    # ---------------------------------------------------------------- targets
    def targets(self) -> dict:
        t = dict(core.TARGETS)
        r = self.con.execute("SELECT value FROM settings WHERE key='targets'").fetchone()
        if r:
            try:
                t.update({k: v for k, v in json.loads(r["value"]).items() if k in t})
            except (ValueError, TypeError):
                pass
        return t

    def targets_save(self, values: dict):
        t = {k: float(v) for k, v in values.items() if k in core.TARGETS}
        self.con.execute(
            "INSERT INTO settings (key,value) VALUES ('targets',?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (json.dumps(t),))
        self.con.commit()

    # --------------------------------------------------------------- utils
    def start_day(self) -> str:
        """First day with entries; today if there is none."""
        r = self.con.execute(
            "SELECT MIN(d) FROM (SELECT day AS d FROM entries"
            " UNION ALL SELECT day FROM weights UNION ALL SELECT day FROM days)"
        ).fetchone()
        return (r[0] if r and r[0] else None) or iso(dt.date.today())


def iso(d) -> str:
    return d.isoformat() if isinstance(d, dt.date) else str(d)


def monday_of(d: dt.date) -> dt.date:
    return d - dt.timedelta(days=d.weekday())
