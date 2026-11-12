#!/usr/bin/env python3
"""Genera Nutricion_Tracker.xlsx (importable a Google Sheets)."""
import datetime as dt
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import FormulaRule
from openpyxl.formatting.formatting import ConditionalFormatting
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.chart import LineChart, Reference
from openpyxl.chart.marker import Marker

OUT = "Nutricion_Tracker.xlsx"

# ---------- paleta ----------
DARK   = "FF1F2430"
DARK2  = "FF2E3440"
GREEN  = "FFC6EFCE"
GREEN_F= "FF0F5132"
RED    = "FFFFC7CE"
RED_F  = "FF9C0006"
GREY   = "FFF2F2F2"
ACCENT = "FF8A7FC7"
HDR_FONT = Font(bold=True, color="FFFFFFFF", size=10)
HDR_FILL = PatternFill("solid", start_color=DARK, end_color=DARK)
TITLE_FONT = Font(bold=True, size=14, color=DARK)
SUB_FONT = Font(bold=True, size=10, color="FF555555")
thin = Side(style="thin", color="FFD0D0D0")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)

START   = dt.date(2026, 10, 4)     # hace 38 días
TODAY   = dt.date(2026, 11, 11)
NDAYS   = 120
NLOG    = 1200
NFOOD   = 300

wb = Workbook()

# =====================================================================
# 1. OBJETIVOS
# =====================================================================
ob = wb.active
ob.title = "Objetivos"
ob.sheet_properties.tabColor = ACCENT

def put(ws, ref, val, fmt=None, font=None, fill=None, align=None):
    c = ws[ref]
    c.value = val
    if fmt: c.number_format = fmt
    if font: c.font = font
    if fill: c.fill = fill
    if align: c.alignment = align
    return c

ob["A1"] = "OBJETIVOS Y CONFIGURACIÓN"
ob["A1"].font = TITLE_FONT
ob["A2"] = "Edita solo las celdas de la columna B. Todo lo demás se calcula solo."
ob["A2"].font = Font(italic=True, size=9, color="FF777777")

# --- datos personales ---
ob["A4"] = "DATOS PERSONALES"; ob["A4"].font = SUB_FONT
personal = [
    ("Altura (cm)",            167,        "0"),
    ("Peso inicial (kg)",      84.5,       "0.0"),
    ("Peso actual (kg)",       "=IFERROR(LOOKUP(9.99E+307,Peso!$B$5:$B$500),Objetivos!$B$6)", "0.0"),
    ("Fecha de inicio",        START,      "yyyy-mm-dd"),
    ("Días transcurridos",     "=TODAY()-Objetivos!$B$8", "0"),
    ("Peso objetivo (kg)",     70,         "0.0"),
    ("IMC actual",             "=Objetivos!$B$7/(Objetivos!$B$5/100)^2", "0.0"),
    ("IMC objetivo",           "=Objetivos!$B$10/(Objetivos!$B$5/100)^2", "0.0"),
]
for i, (label, val, fmt) in enumerate(personal):
    r = 5 + i
    put(ob, f"A{r}", label, font=Font(size=10))
    c = put(ob, f"B{r}", val, fmt=fmt, font=Font(bold=True, size=10), fill=PatternFill("solid", start_color=GREY, end_color=GREY))
    c.border = BOX
put(ob, "A13", "Progreso de peso (%)")
put(ob, "B13", "=IFERROR((Objetivos!$B$6-Objetivos!$B$7)/(Objetivos!$B$6-Objetivos!$B$10),\"\")", fmt="0.0%", font=Font(bold=True, size=10), fill=PatternFill("solid", start_color=GREY, end_color=GREY))
put(ob, "A14", "Ritmo (kg/semana)")
put(ob, "B14", "=IFERROR((Objetivos!$B$6-Objetivos!$B$7)/(Objetivos!$B$9/7),\"\")", fmt="0.00", font=Font(bold=True, size=10), fill=PatternFill("solid", start_color=GREY, end_color=GREY))

# --- objetivos diarios ---
ob["A17"] = "OBJETIVO DIARIO"; ob["A17"].font = SUB_FONT
targets = [
    ("kcal día de entreno",              2100, "0"),
    ("kcal día de descanso",             1800, "0"),
    ("Tolerancia kcal (+/-)",             100, "0"),
    ("Proteína mín (g)",                  120, "0"),
    ("Proteína máx (g)",                  140, "0"),
    ("Proteína % mín",                    0.20, "0%"),
    ("Proteína % máx",                    0.30, "0%"),
    ("Carbos % mín",                      0.40, "0%"),
    ("Carbos % máx",                      0.50, "0%"),
    ("Grasa % objetivo (fija)",           0.30, "0%"),
    ("Vitamina C (mg)",                   200, "0"),
    ("Potasio mín (mg)",                 3000, "0"),
    ("Potasio máx (mg)",                 4000, "0"),
    ("Sodio máx (ratio vs potasio)",        1, "0.00"),
    ("Pasos mín",                        3000, "0"),
    ("Pasos máx",                       10000, "0"),
    ("Sucralosa máx (g/día)",              10, "0"),
    ("Coca-Cola: % máx de bebidas/semana", 0.10, "0%"),
    ("Antiox: puntos objetivo/día",         5, "0"),
]
for i, (label, val, fmt) in enumerate(targets):
    r = 18 + i
    put(ob, f"A{r}", label, font=Font(size=10))
    c = put(ob, f"B{r}", val, fmt=fmt, font=Font(bold=True, size=10), fill=PatternFill("solid", start_color=GREY, end_color=GREY))
    c.border = BOX

# referencias de celda usadas por las demás hojas (deben coincidir con el orden de arriba)
R_KCAL_ENT = "Objetivos!$B$18"
R_KCAL_DES = "Objetivos!$B$19"
R_TOL      = "Objetivos!$B$20"
R_PROT_MIN = "Objetivos!$B$21"
R_PROT_MAX = "Objetivos!$B$22"
R_PPMIN    = "Objetivos!$B$23"
R_PPMAX    = "Objetivos!$B$24"
R_PCMIN    = "Objetivos!$B$25"
R_PCMAX    = "Objetivos!$B$26"
R_PGMIN    = "Objetivos!$B$28"
R_PGMAX    = "Objetivos!$B$30"   # lo usa solo el panel de %
R_FAT      = "Objetivos!$B$27"
R_VITC     = "Objetivos!$B$28"
R_PMIN     = "Objetivos!$B$29"
R_KMIN     = "Objetivos!$B$29"
R_KMAX     = "Objetivos!$B$30"
R_SUCR     = "Objetivos!$B$34"
R_ANTIOX   = "Objetivos!$B$36"

# --- notas ---
ob["A39"] = "NOTAS"; ob["A39"].font = SUB_FONT
notes = [
    "Ventana de calorías: 1800 (descanso) a 2100 (entreno) kcal.",
    "Proteína 120-140 g = 20-30% de las calorías. Grasa fija en 30%.",
    "Carbos 40-50%: salen del resto de calorías, no los fijes a mano.",
    "Sodio: nunca por encima del potasio del día (ratio <= 1). Apunta a 1:1.",
    "Vitamina C 200 mg/día (RDA 90 mg; 200 es el objetivo antioxidante elegido).",
    "Sucralosa <= 10 g/día. Coca-Cola <= 10% de las bebidas de la semana.",
    "Marcadores: piel limpia, sin hinchazón, antiox alto, músculo conservado (proteína + entreno).",
]
for i, n in enumerate(notes):
    ob[f"A{40+i}"] = "• " + n
    ob[f"A{40+i}"].font = Font(size=9, color="FF555555")

for col, w in {"A": 34, "B": 16, "C": 3}.items():
    ob.column_dimensions[col].width = w

# =====================================================================
# 2. ALIMENTOS (base de datos)
# =====================================================================
al = wb.create_sheet("Alimentos")
al.sheet_properties.tabColor = "FF6B8E23"
al["A1"] = "BASE DE DATOS DE ALIMENTOS (valores por 100 g o 100 ml)"
al["A1"].font = TITLE_FONT
al["A2"] = ("Para agregar un alimento: escribe su nombre en la primera fila vacía de la columna A y llena "
            "kcal/proteína/carbos/grasa/vit C/potasio/sodio. Aparecerá solo en el desplegable del registro.")
al["A2"].font = Font(italic=True, size=9, color="FF777777")
HDROW = 4
headers = ["Alimento", "Grupo", "kcal", "Proteína (g)", "Carbos (g)", "Grasa (g)",
           "Fibra (g)", "Vit C (mg)", "Potasio (mg)", "Sodio (mg)", "Antiox (0-3)", "Notas"]
for i, h in enumerate(headers, 1):
    c = al.cell(row=HDROW, column=i, value=h)
    c.font = HDR_FONT; c.fill = HDR_FILL; c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
al.row_dimensions[HDROW].height = 30

FOODS = [
    # nombre, grupo, kcal, prot, carb, grasa, fibra, vitC, K, Na, antiox, nota
    ("Papa cocida",            "Verdura",   87, 1.9, 20.1, 0.1, 1.8, 13.0, 379,   5, 2, "con piel"),
    ("Papa cruda",             "Verdura",   77, 2.0, 17.5, 0.1, 2.2, 19.7, 425,   6, 2, ""),
    ("Tomate",                 "Verdura",   18, 0.9,  3.9, 0.2, 1.2, 13.7, 237,   5, 3, "licopeno"),
    ("Ajo",                    "Condimento",149, 6.4, 33.1, 0.5, 2.1, 31.2, 401,  17, 3, "antiox top"),
    ("Cebolla",                "Verdura",   40, 1.1,  9.3, 0.1, 1.7,  7.4, 146,   4, 2, "quercetina"),
    ("Espinaca",               "Verdura",   23, 2.9,  3.6, 0.4, 2.2, 28.1, 558,  79, 3, "alto K"),
    ("Pechuga de pollo cocida","Carne",    165,31.0,  0.0, 3.6, 0.0,  0.0, 256,  74, 0, ""),
    ("Muslo de pollo cocido",  "Carne",    209,26.0,  0.0,10.9, 0.0,  0.0, 250,  88, 0, ""),
    ("Carne de res magra",     "Carne",    250,26.0,  0.0,15.0, 0.0,  0.0, 318,  72, 0, "cocida"),
    ("Jamón de pavo",          "Embutido", 104,17.1,  1.5, 4.3, 0.0,  0.0, 270,1010, 0, "MUCHO sodio"),
    ("Chorizo",                "Embutido", 455,24.1,  1.9,38.3, 0.0,  0.0, 290,1235, 0, "MUCHO sodio"),
    ("Aguacate",               "Grasa",    160, 2.0,  8.5,14.7, 6.7, 10.0, 485,   7, 2, ""),
    ("Lentejas cocidas",       "Legumbre", 116, 9.0, 20.1, 0.4, 7.9,  1.5, 369,   2, 2, ""),
    ("Frijoles negros cocidos","Legumbre", 132, 8.9, 23.7, 0.5, 8.7,  0.0, 355,   1, 2, ""),
    ("Garbanzos cocidos",      "Legumbre", 164, 8.9, 27.4, 2.6, 7.6,  1.3, 291,   7, 1, ""),
    ("Lomo de cerdo cocido",   "Carne",    242,27.0,  0.0,14.0, 0.0,  0.0, 370,  62, 0, ""),
    ("Huevo entero",           "Huevo",    143,12.6,  0.7, 9.5, 0.0,  0.0, 126, 142, 1, ""),
    ("Clara de huevo",         "Huevo",     52,10.9,  0.7, 0.2, 0.0,  0.0, 163, 166, 0, ""),
    ("Arroz blanco cocido",    "Cereal",   130, 2.7, 28.2, 0.3, 0.4,  0.0,  35,   1, 0, ""),
    ("Arroz integral cocido",  "Cereal",   123, 2.7, 25.6, 1.0, 1.6,  0.0,  86,   4, 1, ""),
    ("Avena",                  "Cereal",   389,16.9, 66.3, 6.9,10.6,  0.0, 429,   2, 1, "cruda"),
    ("Pan integral",           "Cereal",   247,13.0, 41.0, 3.4, 6.8,  0.0, 254, 450, 1, ""),
    ("Atún en agua",           "Pescado",  116,25.5,  0.0, 0.8, 0.0,  0.0, 237, 247, 0, ""),
    ("Tilapia cocida",         "Pescado",  128,26.2,  0.0, 2.7, 0.0,  0.0, 380,  56, 0, ""),
    ("Camarón cocido",         "Pescado",   99,24.0,  0.2, 0.3, 0.0,  0.0, 259, 111, 0, ""),
    ("Plátano",                "Fruta",     89, 1.1, 22.8, 0.3, 2.6,  8.7, 358,   1, 1, ""),
    ("Naranja",                "Fruta",     47, 0.9, 11.8, 0.1, 2.4, 53.2, 181,   0, 3, ""),
    ("Limón",                  "Fruta",     29, 1.1,  9.3, 0.3, 2.8, 53.0, 138,   2, 3, ""),
    ("Pimiento rojo",          "Verdura",   31, 1.0,  6.0, 0.3, 2.1,127.7, 211,   4, 3, "vit C top"),
    ("Brócoli",                "Verdura",   34, 2.8,  6.6, 0.4, 2.6, 89.2, 316,  33, 3, ""),
    ("Zanahoria",              "Verdura",   41, 0.9,  9.6, 0.2, 2.8,  5.9, 320,  69, 2, ""),
    ("Pepino",                 "Verdura",   15, 0.7,  3.6, 0.1, 0.5,  2.8, 147,   2, 2, ""),
    ("Repollo",                "Verdura",   25, 1.3,  5.8, 0.1, 2.5, 36.6, 170,  18, 2, ""),
    ("Chile jalapeño",         "Condimento",29, 0.9,  6.5, 0.4, 2.8, 18.9, 248,   3, 2, "capsaicina"),
    ("Tortilla de maíz",       "Cereal",   218, 5.7, 44.6, 2.9, 6.3,  0.0, 186,  45, 1, ""),
    ("Queso fresco",           "Lácteo",   264,17.0,  4.0,20.0, 0.0,  0.0, 104, 364, 0, ""),
    ("Yogur griego natural",   "Lácteo",    59,10.2,  3.6, 0.4, 0.0,  0.0, 141,  36, 0, ""),
    ("Leche entera",           "Lácteo",    61, 3.2,  4.8, 3.3, 0.0,  0.0, 132,  43, 0, ""),
    ("Aceite de oliva",        "Grasa",    884, 0.0,  0.0,100.0,0.0,  0.0,   1,   2, 1, ""),
    ("Almendras",              "Fruto seco",579,21.2, 21.6,49.9,12.5, 0.0, 733,   1, 1, ""),
    ("Nueces",                 "Fruto seco",654,15.2, 13.7,65.2, 6.7,  1.3, 441,   2, 2, "omega-3"),
    ("Salsa de tomate",        "Condimento",24, 1.2,  5.3, 0.2, 1.5,  7.0, 297, 373, 2, ""),
    ("Agua",                   "Bebida",     0, 0.0,  0.0, 0.0, 0.0,  0.0,   0,   0, 0, "por 100 ml"),
    ("Café negro",             "Bebida",     2, 0.3,  0.0, 0.0, 0.0,  0.0, 116,   2, 3, "por 100 ml"),
    ("Té negro",               "Bebida",     1, 0.0,  0.3, 0.0, 0.0,  0.0,  37,   3, 2, "por 100 ml"),
    ("Coca-Cola",              "Bebida",    42, 0.0, 10.6, 0.0, 0.0,  0.0,   2,   4, 0, "por 100 ml"),
    ("Coca-Cola Zero",         "Bebida",   0.3, 0.0,  0.0, 0.0, 0.0,  0.0,   1,   8, 0, "por 100 ml"),
]
first = HDROW + 1
for j, row in enumerate(FOODS):
    for i, v in enumerate(row, 1):
        c = al.cell(row=first + j, column=i, value=v)
        c.font = Font(size=10)
        c.border = BOX
        if 3 <= i <= 11:
            c.number_format = "0.###"
last_food = first + len(FOODS) - 1

for col, w in zip("ABCDEFGHIJKL", [26, 12, 8, 11, 10, 9, 8, 10, 11, 10, 11, 16]):
    al.column_dimensions[col].width = w
al.freeze_panes = f"A{first}"
al.auto_filter.ref = f"A{HDROW}:L{last_food}"

# =====================================================================
# 3. REGISTRO (una fila por alimento consumido)
# =====================================================================
rg = wb.create_sheet("Registro")
rg.sheet_properties.tabColor = "FF4C8BF5"
rg["A1"] = "REGISTRO DE COMIDAS — una fila por alimento"
rg["A1"].font = TITLE_FONT
rg["A2"] = ("Escribe fecha, comida, alimento y gramos. Las columnas grises se llenan solas; "
            "si aparece ¿? el alimento no existe en la hoja Alimentos.")
rg["A2"].font = Font(italic=True, size=9, color="FF777777")
H = 4
cols = ["Fecha", "Comida", "Alimento", "Gramos", "kcal", "Proteína", "Carbos", "Grasa",
        "Vit C", "Potasio", "Sodio", "Antiox", "Notas"]
for i, h in enumerate(cols, 1):
    c = rg.cell(row=H, column=i, value=h)
    c.font = HDR_FONT; c.fill = HDR_FILL
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
rg.row_dimensions[H].height = 28

# alimento -> columna en Alimentos
MAP = {"E": "C", "F": "D", "G": "E", "H": "F", "I": "H", "J": "I", "K": "J", "L": "K"}
for r in range(H + 1, H + 1 + NLOG):
    for col, src in MAP.items():
        rg[f"{col}{r}"] = (f'=IF(OR($C{r}="",$D{r}=""),"",IFERROR($D{r}*'
                           f'INDEX(Alimentos!${src}$5:${src}${first+NFOOD},'
                           f'MATCH($C{r},Alimentos!$A$5:$A${first+NFOOD},0))/100,"¿?"))')
    rg[f"A{r}"].number_format = "yyyy-mm-dd"
    rg[f"D{r}"].number_format = "0.#"
    for col in "EFGHIJKL":
        rg[f"{col}{r}"].number_format = "0.##"
        rg[f"{col}{r}"].fill = PatternFill("solid", start_color=GREY, end_color=GREY)
    for col in "ABCM":
        rg[f"{col}{r}"].fill = PatternFill("solid", start_color="FFFFFFFF", end_color="FFFFFFFF")

for col, w in zip("ABCDEFGHIJKLM", [11, 11, 26, 9, 8, 9, 8, 8, 8, 9, 8, 8, 22]):
    rg.column_dimensions[col].width = w
rg.freeze_panes = f"A{H+1}"

dv_food = DataValidation(type="list", formula1=f"Alimentos!$A$5:$A${first+NFOOD}", allow_blank=True)
dv_food.showDropDown = False   # False = muestra la flecha
dv_meal = DataValidation(type="list", formula1='"Desayuno,Almuerzo,Cena,Snack"', allow_blank=True)
dv_num = DataValidation(type="decimal", operator="greaterThan", formula1="0", allow_blank=True)
for dv in (dv_food, dv_meal, dv_num):
    rg.add_data_validation(dv)
dv_food.add(f"C{H+1}:C{H+NLOG}")
dv_meal.add(f"B{H+1}:B{H+NLOG}")
dv_num.add(f"D{H+1}:D{H+NLOG}")

# =====================================================================
# 4. RESUMEN (un renglón por día + semáforos + gráficas)
# =====================================================================
rs = wb.create_sheet("Resumen")
rs.sheet_properties.tabColor = "FFE0A458"
rs["A1"] = "RESUMEN DIARIO — totales, objetivos y estado"
rs["A1"].font = TITLE_FONT
rs["A2"] = "Verde = objetivo cumplido · Blanco = en curso / sin datos · Rojo = objetivo fallado o límite pasado."
rs["A2"].font = Font(italic=True, size=9, color="FF777777")
H = 4
cols = ["Fecha", "Entreno", "kcal", "Proteína", "Carbos", "Grasa", "Vit C", "Potasio",
        "Sodio", "Na:K", "% Prot", "% Carb", "% Grasa", "Pasos", "Piel OK", "Hinchazón",
        "Antiox", "Peso", "kcal objetivo", "Estado"]
for i, h in enumerate(cols, 1):
    c = rs.cell(row=H, column=i, value=h)
    c.font = HDR_FONT; c.fill = HDR_FILL
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
rs.row_dimensions[H].height = 30

FIRST = H + 1
LAST = FIRST + NDAYS - 1
for k in range(NDAYS):
    r = FIRST + k
    rs[f"A{r}"] = START + dt.timedelta(days=k)
    rs[f"A{r}"].number_format = "yyyy-mm-dd"
    for col_dst, col_src in (("C", "E"), ("D", "F"), ("E", "G"), ("F", "H"),
                             ("G", "I"), ("H", "J"), ("I", "K")):
        rs[f"{col_dst}{r}"] = (f'=SUMIFS(Registro!${col_src}${H+1}:${col_src}${H+NLOG},'
                               f'Registro!$A${H+1}:$A${H+NLOG},$A{r})')
    rs[f"J{r}"] = f'=IF($H{r}>0,$I{r}/$H{r},"")'
    rs[f"K{r}"] = f'=IF($C{r}>0,$D{r}*4/$C{r},"")'
    rs[f"L{r}"] = f'=IF($C{r}>0,$E{r}*4/$C{r},"")'
    rs[f"M{r}"] = f'=IF($C{r}>0,$F{r}*9/$C{r},"")'
    rs[f"Q{r}"] = (f'=SUMIFS(Registro!$L${H+1}:$L${H+NLOG},'
                   f'Registro!$A${H+1}:$A${H+NLOG},$A{r})')
    rs[f"R{r}"] = f'=IFERROR(LOOKUP($A{r},Peso!$A$5:$A$500,Peso!$B$5:$B$500),"")'
    rs[f"S{r}"] = f'=IF($B{r}="Entreno",{R_KCAL_ENT},IF($B{r}="Descanso",{R_KCAL_DES},""))'
    rs[f"T{r}"] = (f'=IF($C{r}=0,"",IF(AND(ISNUMBER($S{r}),ABS($C{r}-$S{r})<={R_TOL},'
                   f'$D{r}>={R_PROT_MIN},$D{r}<={R_PROT_MAX},$G{r}>={R_VITC},'
                   f'$H{r}>={R_PMIN},OR($J{r}="",$J{r}<=1)),"✔",'
                   f'IF($A{r}<TODAY(),"✘","…")))')
    rs[f"A{r}"].number_format = "yyyy-mm-dd"
    for col in "CDEFGHIJKLMNOPQRS":
        rs[f"{col}{r}"].number_format = "0.##"
    for col in "KLM":
        rs[f"{col}{r}"].number_format = "0.0%"
    rs[f"J{r}"].number_format = "0.00"
    rs[f"R{r}"].number_format = "0.0"
    rs[f"S{r}"].number_format = "0"

for col, w in zip("ABCDEFGHIJKLMNOPQRST", [11,9,8,9,9,8,8,9,8,7,8,8,8,8,8,9,8,8,10,7]):
    rs.column_dimensions[col].width = w
rs.freeze_panes = f"A{FIRST}"

dv_ent = DataValidation(type="list", formula1='"Entreno,Descanso"', allow_blank=True)
dv_sn  = DataValidation(type="list", formula1='"Sí,No"', allow_blank=True)
for dv in (dv_ent, dv_sn):
    rs.add_data_validation(dv)
dv_ent.add(f"B{FIRST}:B{LAST}")
dv_sn.add(f"O{FIRST}:O{LAST}")
dv_sn.add(f"P{FIRST}:P{LAST}")


def cf_range(ws, sqref, rules):
    """Varias reglas (formula, color) dentro de un solo bloque condicional."""
    for formula, color in rules:
        ws.conditional_formatting.add(sqref, FormulaRule(
            formula=[formula],
            fill=PatternFill("solid", start_color=color, end_color=color),
            stopIfTrue=True))


REF = f"{FIRST}"
def R(col): return f"${col}{REF}"

# --- semáforos de Resumen ---
cf_range(rs, f"C{FIRST}:C{LAST}", [
    (f'AND($C{FIRST}>0,ISNUMBER($S{FIRST}),ABS($C{FIRST}-$S{FIRST})<={R_TOL})', GREEN),
    (f'AND($C{FIRST}>0,ISNUMBER($S{FIRST}),OR($C{FIRST}>$S{FIRST}+2*{R_TOL},'
     f'AND($A{FIRST}<TODAY(),$C{FIRST}<$S{FIRST}-3*{R_TOL})))', RED),
])
cf_range(rs, f"D{FIRST}:D{LAST}", [
    (f'AND($D{FIRST}>0,$D{FIRST}>={R_PROT_MIN},$D{FIRST}<={R_PROT_MAX})', GREEN),
    (f'AND($D{FIRST}>0,OR($D{FIRST}>{R_PROT_MAX}+20,'
     f'AND($A{FIRST}<TODAY(),$D{FIRST}<{R_PROT_MIN}-20)))', RED),
])
cf_range(rs, f"K{FIRST}:K{LAST}", [
    (f'AND($C{FIRST}>0,$K{FIRST}>={R_PPMIN},$K{FIRST}<={R_PPMAX})', GREEN),
    (f'AND($C{FIRST}>0,OR($K{FIRST}>{R_PPMAX}+0.05,'
     f'AND($A{FIRST}<TODAY(),$K{FIRST}<{R_PPMIN}-0.05)))', RED),
])
cf_range(rs, f"L{FIRST}:L{LAST}", [
    (f'AND($C{FIRST}>0,$L{FIRST}>={R_PCMIN},$L{FIRST}<={R_PCMAX})', GREEN),
    (f'AND($C{FIRST}>0,OR($L{FIRST}>{R_PCMAX}+0.05,'
     f'AND($A{FIRST}<TODAY(),$L{FIRST}<{R_PCMIN}-0.05)))', RED),
])
cf_range(rs, f"M{FIRST}:M{LAST}", [
    (f'AND($C{FIRST}>0,ABS($M{FIRST}-{R_FAT})<=0.03)', GREEN),
    (f'AND($C{FIRST}>0,ABS($M{FIRST}-{R_FAT})>0.06)', RED),
])
cf_range(rs, f"G{FIRST}:G{LAST}", [
    (f'AND($G{FIRST}>0,$G{FIRST}>={R_VITC})', GREEN),
    (f'AND($A{FIRST}<TODAY(),$G{FIRST}<{R_VITC}*0.5)', RED),
])
cf_range(rs, f"H{FIRST}:H{LAST}", [
    (f'AND($H{FIRST}>0,$H{FIRST}>={R_KMIN},$H{FIRST}<={R_KMAX})', GREEN),
    (f'AND($H{FIRST}>0,OR($H{FIRST}>{R_KMAX}+500,'
     f'AND($A{FIRST}<TODAY(),$H{FIRST}<{R_KMIN}-500)))', RED),
])
cf_range(rs, f"I{FIRST}:J{LAST}", [
    (f'AND($H{FIRST}>0,$I{FIRST}>0,$I{FIRST}<=$H{FIRST})', GREEN),
    (f'AND($I{FIRST}>0,OR($H{FIRST}=0,$I{FIRST}>$H{FIRST}*1.15))', RED),
])
cf_range(rs, f"N{FIRST}:N{LAST}", [
    (f'AND($N{FIRST}>=Objetivos!$B$32,$N{FIRST}<=Objetivos!$B$33)', GREEN),
    (f'AND($N{FIRST}>0,$N{FIRST}<Objetivos!$B$32)', RED),
])
cf_range(rs, f"O{FIRST}:O{LAST}", [
    (f'$O{FIRST}="Sí"', GREEN), (f'$O{FIRST}="No"', RED),
])
cf_range(rs, f"P{FIRST}:P{LAST}", [
    (f'$P{FIRST}="No"', GREEN), (f'$P{FIRST}="Sí"', RED),
])
cf_range(rs, f"Q{FIRST}:Q{LAST}", [
    (f'$Q{FIRST}>={R_ANTIOX}', GREEN),
    (f'AND($A{FIRST}<TODAY(),$C{FIRST}>0,$Q{FIRST}<{R_ANTIOX}/2)', RED),
])
cf_range(rs, f"T{FIRST}:T{LAST}", [
    (f'$T{FIRST}="✔"', GREEN), (f'$T{FIRST}="✘"', RED),
])

# --- gráficas ---
cats = Reference(rs, min_col=1, min_row=FIRST, max_row=LAST)

ch1 = LineChart()
ch1.title = "Calorías vs objetivo"
ch1.height, ch1.width = 8, 22
ch1.y_axis.title = "kcal"
ch1.x_axis.title = "fecha"
ch1.add_data(Reference(rs, min_col=3, min_row=H, max_row=LAST), titles_from_data=True)
ch1.add_data(Reference(rs, min_col=19, min_row=H, max_row=LAST), titles_from_data=True)
ch1.set_categories(cats)
ch1.series[0].graphicalProperties.line.width = 22000
ch1.series[1].graphicalProperties.line.dashStyle = "dash"
for s in ch1.series:
    s.marker = Marker(symbol="none")
rs.add_chart(ch1, "V4")

ch2 = LineChart()
ch2.title = "Reparto de macros (%)"
ch2.height, ch2.width = 8, 22
ch2.y_axis.title = "% de kcal"
ch2.add_data(Reference(rs, min_col=11, max_col=13, min_row=H, max_row=LAST), titles_from_data=True)
ch2.set_categories(cats)
for s in ch2.series:
    s.marker = Marker(symbol="none")
rs.add_chart(ch2, "V26")

ch3 = LineChart()
ch3.title = "Vitamina C y potasio"
ch3.height, ch3.width = 8, 22
ch3.add_data(Reference(rs, min_col=7, min_row=H, max_row=LAST), titles_from_data=True)
ch3.add_data(Reference(rs, min_col=8, min_row=H, max_row=LAST), titles_from_data=True)
ch3.set_categories(cats)
for s in ch3.series:
    s.marker = Marker(symbol="none")
rs.add_chart(ch3, "V48")

# =====================================================================
# 5. PESO
# =====================================================================
pe = wb.create_sheet("Peso")
pe.sheet_properties.tabColor = "FF9CC5A1"
pe["A1"] = "PESO CORPORAL"
pe["A1"].font = TITLE_FONT
pe["A2"] = "Anota fecha y peso (en ayunas, misma hora). La meta está en Objetivos → peso objetivo."
pe["A2"].font = Font(italic=True, size=9, color="FF777777")
H = 4
for i, h in enumerate(["Fecha", "Peso (kg)", "Media 7 días", "Objetivo"], 1):
    c = pe.cell(row=H, column=i, value=h)
    c.font = HDR_FONT; c.fill = HDR_FILL
    c.alignment = Alignment(horizontal="center", wrap_text=True)

pe_rows = 300
first_w = H + 1
for k in range(pe_rows):
    r = first_w + k
    pe[f"A{r}"].number_format = "yyyy-mm-dd"
    pe[f"B{r}"].number_format = "0.0"
    pe[f"C{r}"].number_format = "0.00"
    pe[f"D{r}"].number_format = "0.0"
    if r <= first_w + 6:
        pe[f"C{r}"] = f'=IF($B{r}="","",AVERAGE($B${first_w}:$B{r}))'
    else:
        pe[f"C{r}"] = f'=IF($B{r}="","",IFERROR(AVERAGE($B{r-6}:$B{r}),""))'
    pe[f"D{r}"] = "=Objetivos!$B$10"
pe[f"A{first_w}"] = START
pe[f"B{first_w}"] = 84.5
pe[f"A{first_w+1}"] = TODAY
pe[f"B{first_w+1}"] = 79.8
for col, w in zip("ABCD", [12, 11, 14, 10]):
    pe.column_dimensions[col].width = w
pe.freeze_panes = f"A{first_w}"

chw = LineChart()
chw.title = "Peso vs objetivo (70 kg)"
chw.height, chw.width = 9, 24
chw.y_axis.title = "kg"
chw.add_data(Reference(pe, min_col=2, max_col=3, min_row=H, max_row=first_w+pe_rows-1), titles_from_data=True)
chw.add_data(Reference(pe, min_col=4, min_row=H, max_row=first_w+pe_rows-1), titles_from_data=True)
chw.set_categories(Reference(pe, min_col=1, min_row=first_w, max_row=first_w+pe_rows-1))
for s in chw.series:
    s.marker = Marker(symbol="circle", size=4)
pe.add_chart(chw, "F4")

# =====================================================================
# 6. BEBIDAS (semanal)
# =====================================================================
be = wb.create_sheet("Bebidas")
be.sheet_properties.tabColor = "FF7FB2C7"
be["A1"] = "BEBIDAS — control semanal"
be["A1"].font = TITLE_FONT
be["A2"] = ("Cuenta por semana en vasos/tazas. Reglas: Coca-Cola <= 10% de las bebidas de la semana, "
            "sucralosa <= 10 g/día (promedio).")
be["A2"].font = Font(italic=True, size=9, color="FF777777")
H = 4
bcols = ["Semana inicia", "Agua (vasos)", "Café (tazas)", "Té negro (tazas)",
         "Coca-Cola (vasos)", "Otras (vasos)", "Total bebidas", "% Coca-Cola",
         "Sucralosa total (g)", "Sucralosa /día", "Estado"]
for i, h in enumerate(bcols, 1):
    c = be.cell(row=H, column=i, value=h)
    c.font = HDR_FONT; c.fill = HDR_FILL
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
be.row_dimensions[H].height = 30
NW = 26
for k in range(NW):
    r = H + 1 + k
    be[f"A{r}"] = START + dt.timedelta(days=7 * k)
    be[f"A{r}"].number_format = "yyyy-mm-dd"
    be[f"G{r}"] = f'=SUM($B{r}:$F{r})'
    be[f"H{r}"] = f'=IF($G{r}=0,"",$E{r}/$G{r})'
    be[f"J{r}"] = f'=IF($I{r}="","",$I{r}/7)'
    be[f"K{r}"] = (f'=IF($G{r}=0,"",IF(AND($H{r}<=Objetivos!$B$35,$J{r}<=Objetivos!$B$34),'
                   f'"✔","✘"))')
    for col in "BEFGI":
        be[f"{col}{r}"].number_format = "0.##"
    be[f"H{r}"].number_format = "0.0%"
    be[f"J{r}"].number_format = "0.0"
for col, w in zip("ABCDEFGHIJK", [14,11,11,12,13,11,11,11,15,13,8]):
    be.column_dimensions[col].width = w
be.freeze_panes = f"A{H+1}"

cf_range(be, f"H{H+1}:J{H+NW}", [
    (f'AND($G{H+1}>0,$H{H+1}<=Objetivos!$B$35,$J{H+1}<=Objetivos!$B$34)', GREEN),
    (f'AND($G{H+1}>0,OR($H{H+1}>Objetivos!$B$35,$J{H+1}>Objetivos!$B$34))', RED),
])
cf_range(be, f"K{H+1}:K{H+NW}", [
    (f'$K{H+1}="✔"', GREEN), (f'$K{H+1}="✘"', RED),
])

# =====================================================================
# 7. HOY (panel)
# =====================================================================
ho = wb.create_sheet("Hoy", 0)
ho.sheet_properties.tabColor = DARK
ho["A1"] = "PANEL DE HOY"
ho["A1"].font = TITLE_FONT
ho["A2"] = "=TEXT(TODAY(),\"dddd dd/mm/yyyy\")"
ho["A2"].font = Font(bold=True, size=11, color="FF555555")
ho["A3"] = "Tipo de día (se toma de Resumen):"
ho["A3"].font = Font(size=9, color="FF777777")
ho["C3"] = '=IFERROR(INDEX(Resumen!$B:$B,MATCH(TODAY(),Resumen!$A:$A,0)),"Sin fila en Resumen")'
ho["C3"].font = Font(bold=True, size=10)

hdr = ["Métrica", "Consumido", "Objetivo", "%", "Estado"]
for i, h in enumerate(hdr, 1):
    c = ho.cell(row=5, column=i, value=h)
    c.font = HDR_FONT; c.fill = HDR_FILL
    c.alignment = Alignment(horizontal="center")

LOG0, LOG1 = 5, 4 + NLOG
def sumif(col):
    return (f'=SUMIFS(Registro!${col}${LOG0}:${col}${LOG1},'
            f'Registro!$A${LOG0}:$A${LOG1},TODAY())')

rows = [
    ("kcal",            sumif("E"), f'=IFERROR(INDEX(Resumen!$S:$S,MATCH(TODAY(),Resumen!$A:$A,0)),"")', "0", "kcal"),
    ("Proteína (g)",    sumif("F"), "=Objetivos!$B$22", "0.0", "prot"),
    ("Carbos (g)",      sumif("G"), '=IFERROR(IF($C$6>0,$C$6*Objetivos!$B$25/4,""),"")', "0.0", "carb"),
    ("Grasa (g)",       sumif("H"), '=IFERROR(IF($C$6>0,$C$6*Objetivos!$B$27/9,""),"")', "0.0", "fat"),
    ("Vit C (mg)",      sumif("I"), "=Objetivos!$B$28", "0", "vitc"),
    ("Potasio (mg)",    sumif("J"), "=Objetivos!$B$29", "0", "k"),
    ("Sodio (mg)",      sumif("K"), sumif("J"), "0", "na"),
    ("Na : K",          '=IFERROR(SUMIFS(Registro!$K$5:$K$1204,Registro!$A$5:$A$1204,TODAY())/SUMIFS(Registro!$J$5:$J$1204,Registro!$A$5:$A$1204,TODAY()),"")',
                        "=Objetivos!$B$31", "0.00", "ratio"),
    ("Antiox (pts)",    sumif("L"), "=Objetivos!$B$36", "0.0", "antiox"),
]
r = 6
for label, val, tgt, fmt, kind in rows:
    ho[f"A{r}"] = label
    ho[f"A{r}"].font = Font(size=10)
    ho[f"B{r}"] = val
    ho[f"C{r}"] = tgt
    ho[f"B{r}"].number_format = fmt
    ho[f"C{r}"].number_format = fmt
    ho[f"B{r}"].font = Font(bold=True, size=11)
    ho[f"D{r}"] = f'=IFERROR(IF($C{r}>0,$B{r}/$C{r},""),"")'
    ho[f"D{r}"].number_format = "0%"
    if kind == "ratio":
        ho[f"E{r}"] = f'=IF($B{r}=0,"",IF($B{r}<=Objetivos!$B$31,"✔",IF($B{r}<=Objetivos!$B$31*1.15,"…","✘")))'
    elif kind == "na":
        ho[f"E{r}"] = f'=IF($B{r}=0,"",IF($B$11=0,"…",IF($B{r}<=$B$11,"✔",IF($B{r}<=$B$11*1.15,"…","✘"))))'
    elif kind == "kcal":
        ho[f"E{r}"] = (f'=IF($B{r}=0,"",IF(ABS($B{r}-$C{r})<={R_TOL},"✔",'
                       f'IF($B{r}>$C{r}+2*{R_TOL},"✘","…")))')
    elif kind == "fat":
        ho[f"E{r}"] = (f'=IF($B{r}=0,"",IF($B$6=0,"…",IF(ABS($B{r}*9/$B$6-Objetivos!$B$27)<=0.04,"✔","…")))')
    elif kind == "prot":
        ho[f"E{r}"] = (f'=IF($B{r}=0,"",IF(AND($B{r}>={R_PROT_MIN},$B{r}<={R_PROT_MAX}),"✔",'
                       f'IF($B{r}>{R_PROT_MAX},"✘","…")))')
    else:
        ho[f"E{r}"] = f'=IF($B{r}=0,"",IF($B{r}>=$C{r},"✔","…"))'
    ho[f"E{r}"].alignment = Alignment(horizontal="center")
    for col in "ABCDE":
        ho[f"{col}{r}"].border = BOX
    r += 1

# pasos y marcadores
ho["A17"] = "Pasos de hoy"
ho["B17"] = '=IFERROR(INDEX(Resumen!$N:$N,MATCH(TODAY(),Resumen!$A:$A,0)),"")'
ho["C17"] = "=Objetivos!$B$33"
ho["B17"].number_format = "0"; ho["C17"].number_format = "0"
ho["E17"] = '=IF($B17=0,"",IF(AND($B17>=Objetivos!$B$32,$B17<=Objetivos!$B$33),"✔","…"))'
ho["E17"].alignment = Alignment(horizontal="center")

ho["G5"] = "PESO"; ho["G5"].font = SUB_FONT
peso_rows = [
    ("Actual (kg)",  "=Objetivos!$B$7",  "0.0"),
    ("Inicial (kg)", "=Objetivos!$B$6",  "0.0"),
    ("Bajado (kg)",  "=Objetivos!$B$6-Objetivos!$B$7", "0.0"),
    ("Falta (kg)",   "=Objetivos!$B$7-Objetivos!$B$10", "0.0"),
    ("Meta (kg)",    "=Objetivos!$B$10", "0.0"),
    ("Progreso",     "=Objetivos!$B$13", "0.0%"),
    ("kg/semana",    "=Objetivos!$B$14", "0.00"),
    ("Días",         "=Objetivos!$B$9",  "0"),
    ("IMC",          "=Objetivos!$B$11", "0.0"),
]
for i, (lbl, val, fmt) in enumerate(peso_rows):
    ho[f"G{6+i}"] = lbl
    ho[f"G{6+i}"].font = Font(size=10)
    ho[f"H{6+i}"] = val
    ho[f"H{6+i}"].number_format = fmt
    ho[f"H{6+i}"].font = Font(bold=True, size=11)

ho["A19"] = "MARCADORES DE SALUD (se llenan en Resumen)"
ho["A19"].font = SUB_FONT
mk = [
    ("Piel limpia (dermatológico)", '=IFERROR(INDEX(Resumen!$O:$O,MATCH(TODAY(),Resumen!$A:$A,0)),"")'),
    ("Sin hinchazón (antiswelling)", '=IFERROR(INDEX(Resumen!$P:$P,MATCH(TODAY(),Resumen!$A:$A,0)),"")'),
    ("Antioxidantes del día",        '=IFERROR(INDEX(Resumen!$Q:$Q,MATCH(TODAY(),Resumen!$A:$A,0)),"")'),
    ("Músculo: proteína + entreno",  '=IF(AND($B$7>=Objetivos!$B$21,INDEX(Resumen!$B:$B,MATCH(TODAY(),Resumen!$A:$A,0))="Entreno"),"Sí","Aún no")'),
]
for i, (lbl, val) in enumerate(mk):
    ho[f"A{20+i}"] = lbl
    ho[f"A{20+i}"].font = Font(size=10)
    ho[f"C{20+i}"] = val
    ho[f"C{20+i}"].font = Font(bold=True, size=10)

ho.column_dimensions["A"].width = 32
ho.column_dimensions["B"].width = 13
ho.column_dimensions["C"].width = 13
ho.column_dimensions["D"].width = 9
ho.column_dimensions["E"].width = 9
ho.column_dimensions["F"].width = 3
ho.column_dimensions["G"].width = 20
ho.column_dimensions["H"].width = 12

cf_range(ho, "A6:E17", [
    ('$E6="✔"', GREEN),
    ('$E6="✘"', RED),
])

# =====================================================================
# 8. LÉEME
# =====================================================================
le = wb.create_sheet("Léeme")
le.sheet_properties.tabColor = "FFFFFFFF"
le["A1"] = "CÓMO SE USA"
le["A1"].font = TITLE_FONT
texto = [
 ("", ""),
 ("1. Registrar comida", "Hoja Registro. Una fila por alimento: fecha, comida, alimento (desplegable), gramos. El resto se calcula."),
 ("2. Agregar un alimento nuevo", "Hoja Alimentos: escribe el nombre en la primera fila vacía de la columna A y llena kcal/proteína/carbos/grasa/vitC/potasio/sodio (por 100 g). Aparece solo en el desplegable."),
 ("3. Marcar el día", "Hoja Resumen: elige Entreno o Descanso en la columna B (eso cambia el objetivo de kcal), pon los pasos y marca Piel OK / Hinchazón."),
 ("4. Peso", "Hoja Peso: fecha y peso en ayunas. La gráfica y el ritmo se actualizan solos."),
 ("5. Bebidas", "Hoja Bebidas: cuenta por semana. Coca-Cola <= 10% del total, sucralosa <= 10 g/día."),
 ("", ""),
 ("Colores", "Verde = objetivo cumplido. Blanco = en curso o sin datos. Rojo = objetivo fallado o límite pasado."),
 ("Filas", "Resumen tiene 120 días (hasta 2027-01-31). Registro tiene 1200 filas: cuando se acaben, selecciona la última fila y arrastra hacia abajo."),
 ("Objetivos", "Todos los números (kcal, proteína, vit C, potasio, sodio, pasos, sucralosa) viven en la hoja Objetivos, columna B. Cámbialos ahí, no en las fórmulas."),
 ("Datos", "Valores por 100 g tomados de tablas USDA. La columna Antiox (0-3) es una escala práctica (0 nada, 3 alto), no un número de laboratorio."),
]
r = 3
for a, b in texto:
    le[f"A{r}"] = a
    le[f"A{r}"].font = Font(bold=True, size=10)
    le[f"B{r}"] = b
    le[f"B{r}"].font = Font(size=10)
    le[f"B{r}"].alignment = Alignment(wrap_text=True, vertical="top")
    le.row_dimensions[r].height = 30 if b else 8
    r += 1
le.column_dimensions["A"].width = 34
le.column_dimensions["B"].width = 110

# =====================================================================
wb.calculation.fullCalcOnLoad = True
wb.save(OUT)
print("ok ->", OUT)
