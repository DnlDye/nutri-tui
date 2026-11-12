#!/usr/bin/env python3
"""Verificación real del libro: mete datos de prueba, evalúa las fórmulas con
la librería `formulas` y compara contra el cálculo hecho en Python."""
import datetime as dt, shutil, sys, os
from openpyxl import load_workbook

SRC = "Nutricion_Tracker.xlsx"
TST = "/tmp/verif_tracker.xlsx"

wb = load_workbook(SRC)
rg, rs, pe, al = wb["Registro"], wb["Resumen"], wb["Peso"], wb["Alimentos"]

D = dt.datetime(2026, 11, 11)
Y = dt.datetime(2026, 11, 10)
log = [
    (D, "Desayuno", "Huevo entero", 200),
    (D, "Almuerzo", "Pechuga de pollo cocida", 150),
    (D, "Almuerzo", "Papa cocida", 300),
    (D, "Cena", "Espinaca", 200),
    (D, "Snack", "Plátano", 150),
    (Y, "Cena", "Chorizo", 100),
]
for i, (d, meal, food, g) in enumerate(log):
    r = 5 + i
    rg[f"A{r}"] = d
    rg[f"B{r}"] = meal
    rg[f"C{r}"] = food
    rg[f"D{r}"] = g

# tipo de día
for r in range(5, 125):
    if rs[f"A{r}"].value and rs[f"A{r}"].value.date() == D.date():
        rs[f"B{r}"] = "Entreno"
        rs[f"N{r}"] = 4200
        rs[f"O{r}"] = "Sí"
        rs[f"P{r}"] = "No"

# peso
pe["A7"] = dt.datetime(2026, 11, 12); pe["B7"] = 79.4

# --- recorta filas para que la evaluación sea rápida ---
rg.delete_rows(11, 1204 - 10)
rs.delete_rows(11, 124 - 10)
pe.delete_rows(13, 304 - 12)
wb.save(TST)
print("test escrito:", TST)

# --- valores esperados calculados en Python desde la hoja Alimentos ---
db = {}
for r in range(5, 52):
    n = al[f"A{r}"].value
    if n:
        db[n] = dict(kcal=al[f"C{r}"].value, p=al[f"D{r}"].value, c=al[f"E{r}"].value,
                     f=al[f"F{r}"].value, vitc=al[f"H{r}"].value, k=al[f"I{r}"].value,
                     na=al[f"J{r}"].value, ant=al[f"K{r}"].value)
exp = dict(kcal=0, p=0, c=0, f=0, vitc=0, k=0, na=0, ant=0)
for d, meal, food, g in log:
    if d != D:
        continue
    for key in exp:
        exp[key] += db[food][key] * g / 100

print("esperado:", {k: round(v, 3) for k, v in exp.items()})
print("esperado J (Na:K):", round(exp["na"] / exp["k"], 4))
print("esperado K (%prot):", round(exp["p"] * 4 / exp["kcal"], 4))
print("esperado L (%carb):", round(exp["c"] * 4 / exp["kcal"], 4))
print("esperado M (%grasa):", round(exp["f"] * 9 / exp["kcal"], 4))

# --- evaluar ---
try:
    import formulas
except ImportError:
    sys.exit("falta la librería formulas")

xl = formulas.ExcelModel().loads(TST).finish()
sol = xl.calculate()

def get(sheet, ref):
    key = [k for k in sol if f"{sheet.upper()}'!{ref}".upper() in k.upper()]
    if not key:
        return "MISSING"
    v = sol[key[0]].value[0][0]
    return v

def num(v):
    try:
        return float(v)
    except Exception:
        return v

rows = {}
for r in range(5, 11):
    rows[r] = dict(
        date=get("Resumen", f"A{r}"),
        kcal=num(get("Resumen", f"C{r}")), p=num(get("Resumen", f"D{r}")),
        c=num(get("Resumen", f"E{r}")), f=num(get("Resumen", f"F{r}")),
        vitc=num(get("Resumen", f"G{r}")), k=num(get("Resumen", f"H{r}")),
        na=num(get("Resumen", f"I{r}")), ratio=num(get("Resumen", f"J{r}")),
        pp=num(get("Resumen", f"K{r}")), pc=num(get("Resumen", f"L{r}")),
        pg=num(get("Resumen", f"M{r}")), peso=num(get("Resumen", f"R{r}")),
        tgt=num(get("Resumen", f"S{r}")), estado=get("Resumen", f"T{r}"),
    )
for r, v in rows.items():
    print(r, v)

print("\nRegistro E5..E10:", [num(get("Registro", f"E{r}")) for r in range(5, 11)])
print("Registro J5 (K de 200g huevo, esperado 252):", num(get("Registro", "J5")))
print("Objetivos B7 (último peso, esperado 79.4):", num(get("Objetivos", "B7")))
print("Objetivos B11 IMC (esperado %.2f):" % (79.4 / 1.67**2), num(get("Objetivos", "B11")))
print("Objetivos B14 ritmo kg/sem (esperado %.3f):" % ((84.5 - 79.4) / (38 / 7)),
      num(get("Objetivos", "B14")))
print("Hoy B6 kcal de hoy (esperado %.1f):" % exp["kcal"], num(get("Hoy", "B6")))
print("Hoy E6 estado kcal:", get("Hoy", "E6"))
print("Hoy B13 ratio Na:K (esperado %.3f):" % (exp["na"] / exp["k"]), num(get("Hoy", "B13")))
print("Bebidas K5 con datos vacíos:", get("Bebidas", "K5"))
