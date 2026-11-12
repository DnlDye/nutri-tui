"""Tema: toma la paleta matugen viva del escritorio (la misma que kitty).

Fuente de verdad: ~/.cache/quickshell/matugen.json (apply-theme.sh copia ahí el
quickshell.json del tema y matugen reescribe ese mismo archivo, así que el TUI
se re-tematiza solo cuando cambia la paleta).

Roles usados:
  fondo/panel/superficie  → surface, surface_container, surface_container_high
  texto                   → on_surface
  texto apagado           → outline / outline_variant
  acento                  → primary
  acento 2 (positivo)     → tertiary
  ok / fallo / aviso      → tertiary, error_container, primary_container
"""
from __future__ import annotations

import json
import os
from pathlib import Path

PALETTE_PATHS = [
    Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "quickshell" / "matugen.json",
]

# respaldo si no hay paleta (o el archivo está roto)
FALLBACK = {
    "surface": "#121408", "surface_container": "#282b1d",
    "surface_container_high": "#333627", "on_surface": "#ffffff",
    "outline": "#bdc2a1", "outline_variant": "#999e7e",
    "primary": "#ffdab1", "primary_container": "#d28c27",
    "on_primary_container": "#000000", "tertiary": "#d9e895",
    "error_container": "#ff6b5e", "surface_bright": "#464839",
    "secondary_container": "#c7904a",
}

THEME: dict[str, str] = {}


def _hex(v: str, default: str) -> str:
    v = (v or "").strip()
    if v.startswith("#") and len(v) in (7, 9):
        return v[:7]
    return default


def _pick(pal: dict, key: str, default: str) -> str:
    return _hex(str(pal.get(key, "")), default)


def reload() -> dict[str, str]:
    """Relee la paleta y actualiza THEME en sitio (las referencias siguen válidas)."""
    pal: dict = {}
    for p in PALETTE_PATHS:
        try:
            pal = json.loads(p.read_text())
            if isinstance(pal, dict) and pal.get("primary"):
                break
        except (OSError, ValueError):
            pal = {}

    new = {
        "bg":      _pick(pal, "surface", FALLBACK["surface"]),
        "panel":   _pick(pal, "surface_container_high", FALLBACK["surface_container_high"]),
        "surface": _pick(pal, "surface_container", FALLBACK["surface_container"]),
        "fg":      _pick(pal, "on_surface", FALLBACK["on_surface"]),
        "muted":   _pick(pal, "outline", FALLBACK["outline"]),
        "dim":     _pick(pal, "outline_variant", FALLBACK["outline_variant"]),
        "accent":  _pick(pal, "primary", FALLBACK["primary"]),
        "accent2": _pick(pal, "tertiary", FALLBACK["tertiary"]),
        "ok":      _pick(pal, "tertiary", FALLBACK["tertiary"]),
        "fail":    _pick(pal, "error_container", FALLBACK["error_container"]),
        "warn":    _pick(pal, "primary_container", FALLBACK["primary_container"]),
        "sel_bg":  _pick(pal, "primary_container", FALLBACK["primary_container"]),
        "sel_fg":  _pick(pal, "on_primary_container", FALLBACK["on_primary_container"]),
        "boost":   _pick(pal, "surface_bright", FALLBACK["surface_bright"]),
        "secondary": _pick(pal, "secondary_container", FALLBACK["secondary_container"]),
    }
    THEME.clear()
    THEME.update(new)
    return THEME


def state_color(state: str) -> str:
    """Color de cada semáforo (verde / blanco / rojo / gris)."""
    if not THEME:
        reload()
    return {
        "ok": THEME["ok"],
        "pending": THEME["fg"],
        "fail": THEME["fail"],
        "none": THEME["dim"],
    }.get(state, THEME["dim"])


def textual_theme():
    """Theme de Textual armado con la paleta de matugen."""
    from textual.theme import Theme

    if not THEME:
        reload()
    return Theme(
        name="lucid",
        primary=THEME["accent"],
        secondary=THEME["secondary"],
        accent=THEME["accent2"],
        success=THEME["ok"],
        warning=THEME["warn"],
        error=THEME["fail"],
        foreground=THEME["fg"],
        background=THEME["bg"],
        surface=THEME["surface"],
        panel=THEME["panel"],
        boost=THEME["boost"],
        dark=True,
        variables={
            "nutri-muted": THEME["muted"],
            "nutri-dim": THEME["dim"],
            "nutri-ok": THEME["ok"],
            "nutri-fail": THEME["fail"],
            "nutri-accent2": THEME["accent2"],
        },
    )


reload()
