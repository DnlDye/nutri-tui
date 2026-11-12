"""Pure logic: targets, daily totals and traffic lights.

None of this touches the database or the screen, so it can be tested alone.
Rules:

  green  = target met
  white  = in progress / no data
  red    = target failed or limit exceeded
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ------------------------------------------------------------------ targets
TARGETS: dict[str, float] = {
    # energy
    "kcal_entreno": 2100,
    "kcal_descanso": 1800,
    "tol_kcal": 100,
    # macros
    "prot_min": 120,
    "prot_max": 140,
    "pct_prot_min": 0.20,
    "pct_prot_max": 0.30,
    "pct_carb_min": 0.40,
    "pct_carb_max": 0.50,
    "pct_fat": 0.30,
    # minerals and vitamins
    "vitc": 200,
    "potasio_min": 3000,
    "potasio_max": 4000,
    "ratio_max": 1.0,        # sodio : potasio
    "antiox_min": 5.0,
    # activity
    "pasos_min": 3000,
    "pasos_max": 10000,
    # drinks
    "sucralosa_max": 10.0,
    "coca_pct_max": 0.10,
    # body
    "peso_inicial": 84.5,
    "peso_meta": 70.0,
    "altura": 167,
}

TARGET_LABELS = {
    "kcal_entreno": "kcal on training days",
    "kcal_descanso": "kcal on rest days",
    "tol_kcal": "kcal tolerance (+/-)",
    "prot_min": "protein min (g)",
    "prot_max": "protein max (g)",
    "pct_prot_min": "protein % min",
    "pct_prot_max": "protein % max",
    "pct_carb_min": "carbs % min",
    "pct_carb_max": "carbs % max",
    "pct_fat": "fat % (fixed)",
    "vitc": "vitamin C (mg)",
    "potasio_min": "potassium min (mg)",
    "potasio_max": "potassium max (mg)",
    "ratio_max": "sodium : potassium max",
    "antiox_min": "antiox (points/day)",
    "pasos_min": "steps min",
    "pasos_max": "steps max",
    "sucralosa_max": "sucralose max (g/day)",
    "coca_pct_max": "coca-cola % max weekly",
    "peso_inicial": "starting weight (kg)",
    "peso_meta": "goal weight (kg)",
    "altura": "height (cm)",
}

PCT_KEYS = {"pct_prot_min", "pct_prot_max", "pct_carb_min", "pct_carb_max",
            "pct_fat", "coca_pct_max"}


# -------------------------------------------------------------------- totals
@dataclass
class Totals:
    kcal: float = 0.0
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0
    vitc: float = 0.0
    potassium: float = 0.0
    sodium: float = 0.0
    antiox: float = 0.0
    items: int = 0

    @property
    def ratio(self) -> float | None:
        return self.sodium / self.potassium if self.potassium > 0 else None

    @property
    def p_pct(self) -> float | None:
        return self.protein * 4 / self.kcal if self.kcal > 0 else None

    @property
    def c_pct(self) -> float | None:
        return self.carbs * 4 / self.kcal if self.kcal > 0 else None

    @property
    def f_pct(self) -> float | None:
        return self.fat * 9 / self.kcal if self.kcal > 0 else None


def totals_from_rows(rows) -> Totals:
    """rows: iterable of dicts with grams + the food values per 100 g."""
    t = Totals()
    for r in rows:
        g = float(r["grams"] or 0) / 100.0
        t.kcal += float(r["kcal"] or 0) * g
        t.protein += float(r["protein"] or 0) * g
        t.carbs += float(r["carbs"] or 0) * g
        t.fat += float(r["fat"] or 0) * g
        t.vitc += float(r["vitc"] or 0) * g
        t.potassium += float(r["potassium"] or 0) * g
        t.sodium += float(r["sodium"] or 0) * g
        t.antiox += float(r["antiox"] or 0) * g
        t.items += 1
    return t


# --------------------------------------------------------------- traffic light
OK, PENDING, FAIL, NONE = "ok", "pending", "fail", "none"


def _num(v) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def st_band(value, lo, hi, past: bool, low_slack=0.25, high_slack=0.25,
            hard_high=None, hard_low=None):
    """Inside [lo, hi] = ok. Outside but close = pending. Far = fail.

    `value is None` means "no data"; a real 0 is still evaluated.
    """
    if value is None:
        return NONE
    span = (hi - lo) or (abs(hi) or 1)
    if lo <= value <= hi:
        return OK
    if value > hi:
        if hard_high is not None:
            return FAIL if value > hard_high else PENDING
        return FAIL if value > hi + span * high_slack else PENDING
    # below the minimum
    if past and value < lo - span * low_slack:
        return FAIL
    if hard_low is not None and value < hard_low:
        return FAIL
    return PENDING


def st_min(value, target, past: bool, half=False):
    """Only reaching the minimum matters. 0 counts as zero, not as "no data"."""
    if value is None:
        return NONE
    if value >= target:
        return OK
    if past and value < target * (0.5 if half else 0.75):
        return FAIL
    return PENDING


@dataclass
class Metric:
    key: str
    label: str
    value: float | None
    target_text: str
    state: str
    fmt: str = "{:.0f}"
    hint: str = ""

    def value_text(self) -> str:
        v = self.value
        if v is None:
            return "—"
        return self.fmt.format(v)


def kcal_target(t: dict, training: bool) -> float:
    return t["kcal_entreno"] if training else t["kcal_descanso"]


def evaluate(tot: Totals, t: dict, training: bool, past: bool,
             steps: int | None = None) -> list[Metric]:
    """Return the day's metrics with their state (green/white/red)."""
    kt = kcal_target(t, training)
    tol = t["tol_kcal"]
    out: list[Metric] = []

    # a day with no food at all stays "no data" (white), not red
    nodata = tot.items == 0

    def V(x):
        return None if nodata else x

    out.append(Metric("kcal", "kcal", V(tot.kcal), f"{kt:.0f}±{tol:.0f}",
                      st_band(V(tot.kcal), kt - tol, kt + tol, past,
                              low_slack=2.0, high_slack=0.0), "{:.0f}"))
    out.append(Metric("protein", "protein (g)", V(tot.protein),
                      f"{t['prot_min']:.0f}-{t['prot_max']:.0f}",
                      st_band(V(tot.protein), t["prot_min"], t["prot_max"], past,
                              low_slack=0.15, high_slack=1.0,
                              hard_high=t["prot_max"] + 30), "{:.1f}"))

    p, c, f = V(tot.p_pct), V(tot.c_pct), V(tot.f_pct)
    out.append(Metric("p_pct", "% protein", p, f"{t['pct_prot_min']:.0%}-{t['pct_prot_max']:.0%}",
                      st_band(p, t["pct_prot_min"], t["pct_prot_max"], past,
                              low_slack=0.25, high_slack=0.15), "{:.0%}"))
    out.append(Metric("c_pct", "% carbs", c, f"{t['pct_carb_min']:.0%}-{t['pct_carb_max']:.0%}",
                      st_band(c, t["pct_carb_min"], t["pct_carb_max"], past,
                              low_slack=0.25, high_slack=0.10), "{:.0%}"))
    out.append(Metric("f_pct", "% fat", f, f"{t['pct_fat']:.0%} ±3",
                      st_band(f, t["pct_fat"] - 0.03, t["pct_fat"] + 0.03, past,
                              low_slack=0.0, high_slack=1.0), "{:.0%}"))

    out.append(Metric("vitc", "vitamin C (mg)", V(tot.vitc), f"{t['vitc']:.0f}",
                      st_min(V(tot.vitc), t["vitc"], past, half=True), "{:.0f}"))
    out.append(Metric("potassium", "potassium (mg)", V(tot.potassium),
                      f"{t['potasio_min']:.0f}-{t['potasio_max']:.0f}",
                      st_band(V(tot.potassium), t["potasio_min"], t["potasio_max"], past,
                              low_slack=0.20, high_slack=0.20,
                              hard_high=t["potasio_max"] + 500), "{:.0f}"))
    out.append(Metric("sodium", "sodium (mg)", V(tot.sodium),
                      f"≤ potassium", NONE if nodata else _st_ratio(tot, t, past), "{:.0f}"))
    out.append(Metric("ratio", "sodium : potassium", V(tot.ratio), f"≤ {t['ratio_max']:.2f}",
                      NONE if nodata else _st_ratio(tot, t, past), "{:.2f}"))
    # antiox is no longer a daily target: reported, not graded
    out.append(Metric("antiox", "antiox (pts)", V(tot.antiox), "info", NONE, "{:.1f}"))
    if steps is not None:
        out.append(Metric("steps", "steps", steps or None,
                          f"{t['pasos_min']:.0f}-{t['pasos_max']:.0f}",
                          st_band(steps, t["pasos_min"], t["pasos_max"], False,
                                  low_slack=1.0, high_slack=100), "{:.0f}"))
    return out


def _st_ratio(tot: Totals, t: dict, past: bool) -> str:
    r = tot.ratio
    if r is None:
        return NONE if tot.sodium <= 0 else FAIL   # sodio sin potasio = rojo
    if r <= t["ratio_max"]:
        return OK
    if r <= t["ratio_max"] * 1.15:
        return PENDING
    return FAIL


def day_state(metrics: list[Metric], past: bool) -> str:
    """Overall state of the day."""
    core = [m for m in metrics if m.key in
            ("kcal", "protein", "vitc", "potassium", "ratio")]
    if all(m.state == NONE for m in core):
        return NONE
    if any(m.state == FAIL for m in core):
        return FAIL
    if past and any(m.state == PENDING for m in core):
        return FAIL
    if all(m.state == OK for m in core):
        return OK
    return PENDING


# ------------------------------------------------------------ text / graphics
SYMBOL = {OK: "✔", PENDING: "…", FAIL: "✘", NONE: "·"}
COLOR = {OK: "#3fb950", PENDING: "#d0d0d0", FAIL: "#f85149", NONE: "#6e7681"}

SPARK = "▁▂▃▄▅▆▇█"


def sparkline(values: list[float | None], width: int = 40) -> str:
    """One-line bar chart. Gaps (None) are kept as blank space."""
    vals = list(values)[-width:]
    nums = [v for v in vals if v is not None]
    if not nums:
        return ""
    lo, hi = min(nums), max(nums)
    out = []
    for v in vals:
        if v is None:
            out.append(" ")
            continue
        idx = 3 if hi == lo else int((v - lo) / (hi - lo) * (len(SPARK) - 1))
        out.append(SPARK[idx])
    return "".join(out)


def progress(t: dict, current_weight: float | None) -> dict:
    start, goal = t["peso_inicial"], t["peso_meta"]
    cur = current_weight
    d = {"actual": cur, "inicial": start, "meta": goal, "bajado": None,
         "falta": None, "pct": None, "imc": None}
    if cur:
        d["bajado"] = start - cur
        d["falta"] = max(0.0, cur - goal)
        d["pct"] = (start - cur) / (start - goal) if start != goal else 0.0
        h = t["altura"] / 100.0
        d["imc"] = cur / (h * h)
    return d
