"""Local database (SQLite). Everything lives on the user's disk."""
from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
from pathlib import Path

from . import core, foods

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
CREATE TABLE IF NOT EXISTS drinks (
    week TEXT PRIMARY KEY,
    water INTEGER DEFAULT 0, coffee INTEGER DEFAULT 0, tea INTEGER DEFAULT 0,
    coke INTEGER DEFAULT 0, other INTEGER DEFAULT 0, sucralose REAL DEFAULT 0
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

    def weight_previous(self, day: str) -> float | None:
        r = self.con.execute(
            "SELECT kg FROM weights WHERE day < ? ORDER BY day DESC LIMIT 1", (day,)).fetchone()
        return r["kg"] if r else None

    # ---------------------------------------------------------------- drinks
    def drinks_get(self, week: str) -> dict:
        r = self.con.execute("SELECT * FROM drinks WHERE week=?", (week,)).fetchone()
        if r:
            return dict(r)
        return {"week": week, "water": 0, "coffee": 0, "tea": 0, "coke": 0,
                "other": 0, "sucralose": 0.0}

    def drinks_set(self, week: str, **fields):
        cur = self.drinks_get(week)
        cur.update({k: v for k, v in fields.items() if k != "week"})
        self.con.execute(
            "INSERT INTO drinks (week,water,coffee,tea,coke,other,sucralose)"
            " VALUES (?,?,?,?,?,?,?) ON CONFLICT(week) DO UPDATE SET"
            " water=excluded.water, coffee=excluded.coffee, tea=excluded.tea,"
            " coke=excluded.coke, other=excluded.other, sucralose=excluded.sucralose",
            (week, cur["water"], cur["coffee"], cur["tea"], cur["coke"],
             cur["other"], cur["sucralose"]))
        self.con.commit()

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
        r = self.con.execute("SELECT MIN(day) d FROM entries").fetchone()
        return r["d"] or iso(dt.date.today())


def iso(d) -> str:
    return d.isoformat() if isinstance(d, dt.date) else str(d)


def monday_of(d: dt.date) -> dt.date:
    return d - dt.timedelta(days=d.weekday())
