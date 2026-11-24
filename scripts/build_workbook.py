#!/usr/bin/env python3
"""Lab 7 - Classeur Excel de vérification PRISMA (étapes 2 à 11 et 13), avec de vraies formules.

Feuilles
  Identification      étape 2 : nombres par base, total =SUM()
  Tri                 une ligne par enregistrement unique (143), avec son statut PRISMA et son étude
  Vérification        étapes 4 à 11 : chaque nombre calculé par formule, contrôlé par un comptage indépendant (=COUNTIF)
  Records_Reports_Studies  étape 3
  Motifs              étapes 6 et 10 : exclusions par motif (=COUNTIFS) et contrôle des sous-totaux
  Exclusions          étape 10 : un rapport exclu par ligne (DOI, motif, commentaire), =COUNTA()
  Exemple_énoncé      les nombres de l'énoncé (1000, 220, 550, 10, 160) recalculés par les mêmes formules
  Défis               questions 1-2, défi 1 (tableau à corriger), défi 2 (nombres bruts)

Le fichier est recalculé par LibreOffice (si disponible) pour que les valeurs soient enregistrées.
Usage : python scripts/build_workbook.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prisma_flow as pf  # noqa: E402

ROOT = pf.ROOT
OUTFILE = ROOT / "output" / "09_verification_prisma.xlsx"
BOLD = Font(bold=True)
HEAD = PatternFill("solid", fgColor="D9E1F2")
RED = PatternFill("solid", fgColor="F8CBAD")
GREEN = PatternFill("solid", fgColor="C6EFCE")


def header(ws, cols, widths):
    ws.append(cols)
    for i, w in enumerate(widths, 1):
        ws.cell(1, i).font = BOLD
        ws.cell(1, i).fill = HEAD
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"


def flag(ws, rng):
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"ERREUR"'], fill=RED))
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"OK"'], fill=GREEN))


def status(r):
    st = r["decision_stage"]
    if st not in ("Full text", "Title/abstract (full text not retrieved)"):
        return "Exclu titre/résumé"
    if "not retrieved" in st:
        return "Non récupéré"
    return "Inclus" if r["final_decision"] == "Included" else "Exclu texte intégral"


def build():
    ident = pf.read(pf.DATA / "identification.csv")
    ledger = pf.read(pf.DATA / "Screening_ledger_olive_PRISMA2020.csv")
    links = pf.read(pf.DATA / "rapports_etudes.csv")
    n, g = pf.compute(ident, ledger, links)
    pf.apply_comments(g)
    wb = Workbook()

    # ---- Identification (étape 2)
    ws = wb.active
    ws.title = "Identification"
    header(ws, ["Base", "Nombre", "Unité", "Date", "Champ"], [32, 10, 10, 12, 16])
    for r in ident:
        ws.append([r["Base"], int(r["Nombre"]), "records", r["Date"], r["Champ"]])
    last = ws.max_row
    ws.append(["Total", f"=SUM(B2:B{last})", "records"])
    ws.cell(ws.max_row, 1).font = BOLD
    tot_row = ws.max_row

    # ---- Tri (source des comptages indépendants)
    tri = wb.create_sheet("Tri")
    header(tri, ["Record", "Premier auteur", "Année", "DOI", "Étape de la décision", "Statut PRISMA", "Étude", "Code"], [8, 18, 7, 34, 38, 22, 7, 6])
    for r in ledger:
        tri.append([int(r["record"]), r["first_author"], int(r["year"]), r["doi"].replace("https://doi.org/", ""), r["decision_stage"],
                    status(r), int(g["to_study"].get(r["record"], r["record"])), pf.code(r["final_decision"])])
    N = tri.max_row
    S = f"Tri!$F$2:$F${N}"

    # ---- Exclusions (étape 10)
    ex = wb.create_sheet("Exclusions")
    header(ex, ["DOI", "Record", "Premier auteur", "Code", "Motif", "Commentaire"], [34, 8, 16, 6, 40, 80])
    for r in g["ft_excl"]:
        c = pf.code(r["final_decision"])
        ex.append([r["doi"].replace("https://doi.org/", "") or "sans DOI", int(r["record"]), r["first_author"], c, pf.REASONS_FR[c], r["reason"]])
    ex_last = ex.max_row
    ex.append([])
    # COUNTA sur la colonne Record (toujours remplie) : un rapport exclu n'a pas de DOI
    ex.append(["Nombre d'exclusions", f"=COUNTA(B2:B{ex_last})"])
    ex_count = f"Exclusions!B{ex.max_row}"
    ex.cell(ex.max_row, 1).font = BOLD

    # ---- Liens rapports -> études
    li = wb.create_sheet("Liens_rapports_études")
    header(li, ["Rapport (record)", "Étude (record)", "Commentaire"], [16, 14, 90])
    for l in links:
        li.append([int(l["record_rapport"]), int(l["etude"]), l["commentaire"]])
    li_last = li.max_row

    # ---- Vérification (étapes 4 à 11)
    v = wb.create_sheet("Vérification", 1)
    header(v, ["Étape", "Nombre", "Calcul (formule de la colonne B)", "Contrôle indépendant", "Source du contrôle", "Contrôle"],
           [36, 10, 44, 20, 46, 10])
    rows = [
        ("Références identifiées", f"=Identification!B{tot_row}", "somme des bases", f"=COUNTA({S})+B3", "uniques (Tri) + doublons"),
        ("Doublons supprimés", n["doublons"], "saisi : journal de déduplication (Lab 5)", f"=B2-COUNTA({S})", "identifiées − uniques (Tri)"),
        ("Références examinées", "=B2-B3", "identifiées − doublons", f"=COUNTA({S})", "lignes de Tri"),
        ("Références exclues (titre/résumé)", f'=COUNTIF({S},"Exclu titre/résumé")', "décisions de Tri", "=SUM(Motifs!B2:B9)", "somme des motifs (Motifs)"),
        ("Textes intégraux recherchés", "=B4-B5", "examinées − exclues", f'=COUNTIF({S},"Non récupéré")+COUNTIF({S},"Exclu texte intégral")+COUNTIF({S},"Inclus")', "statuts après titre/résumé (Tri)"),
        ("Textes non récupérés", f'=COUNTIF({S},"Non récupéré")', "décisions de Tri", f'=COUNTIF(Tri!$E$2:$E${N},"*not retrieved*")', "étape de la décision (Tri)"),
        ("Textes intégraux évalués", "=B6-B7", "recherchés − non récupérés", f'=COUNTIF(Tri!$E$2:$E${N},"Full text")', "étape de la décision (Tri)"),
        ("Exclusions avec motifs", f"={ex_count}", "lignes de la feuille Exclusions", f'=COUNTIF({S},"Exclu texte intégral")', "statuts (Tri)"),
        ("Rapports inclus", "=B8-B9", "évalués − exclus", f'=COUNTIF({S},"Inclus")', "statuts (Tri)"),
        ("Études incluses", f"=B10-COUNTA('Liens_rapports_études'!A2:A{li_last})", "rapports − rapports d'une même étude",
         f'=SUMPRODUCT(({S}="Inclus")/(COUNTIFS(Tri!$G$2:$G${N},Tri!$G$2:$G${N},{S},"Inclus")+({S}<>"Inclus")))', "études distinctes parmi les inclus (Tri)"),
    ]
    for i, (a, b, c, d, e) in enumerate(rows, start=2):
        v.append([a, b, c, d, e, f'=IFERROR(IF(B{i}=D{i},"OK","ERREUR"),"ERREUR")'])
    v.append([])
    v.append(["Statut global", '=IF(COUNTIF(F2:F11,"ERREUR")=0,"Tout est cohérent","Incohérence : voir colonne F")'])
    v.cell(v.max_row, 1).font = BOLD
    v.append([])
    v.append(["Checklist de cohérence du lab", "", "", "", "", ""])
    v.cell(v.max_row, 1).font = BOLD
    checks = [("Identifiées = doublons + examinées", "=IF(B2=B3+B4,\"OK\",\"ERREUR\")"),
              ("Recherchés = examinées − exclues titre/résumé", "=IF(B6=B4-B5,\"OK\",\"ERREUR\")"),
              ("Évalués = recherchés − non récupérés", "=IF(B8=B6-B7,\"OK\",\"ERREUR\")"),
              ("Rapports inclus = évalués − exclusions", "=IF(B10=B8-B9,\"OK\",\"ERREUR\")"),
              ("Exclusions = nombre de lignes de la feuille Exclusions", f"=IF(B9={ex_count},\"OK\",\"ERREUR\")")]
    for a, f in checks:
        v.append([a, "", "", "", "", f])
    flag(v, f"F2:F{v.max_row}")

    # ---- Records / reports / studies (étape 3)
    rr = wb.create_sheet("Records_Reports_Studies", 2)
    header(rr, ["Étape", "Unité", "Nombre", "Définition"], [30, 10, 10, 80])
    for etape, unite, ref, d in [
        ("Identification", "records", "=Vérification!B2", "notices brutes exportées (une par base où l'article est indexé)"),
        ("Après déduplication", "records", "=Vérification!B4", "notices uniques soumises au tri titre/résumé"),
        ("Recherche du texte intégral", "reports", "=Vérification!B6", "documents complets recherchés (ici 1 notice = 1 rapport)"),
        ("Évaluation de l'éligibilité", "reports", "=Vérification!B8", "documents complets lus"),
        ("Inclusion", "reports", "=Vérification!B10", "documents complets retenus"),
        ("Inclusion", "studies", "=Vérification!B11", "études distinctes : Kallel 2022 et Makhloufi 2022 décrivent la même étude")]:
        rr.append([etape, unite, ref, d])

    # ---- Motifs (étapes 6 et 10)
    mo = wb.create_sheet("Motifs")
    header(mo, ["Code", "Exclus titre/résumé", "Exclus texte intégral", "Motif"], [8, 18, 20, 50])
    for k in pf.ORDER:
        r = mo.max_row + 1
        mo.append([k, f'=COUNTIFS({S},"Exclu titre/résumé",Tri!$H$2:$H${N},A{r})',
                   f'=COUNTIFS({S},"Exclu texte intégral",Tri!$H$2:$H${N},A{r})', pf.REASONS_FR[k]])
    mo.append(["Total", "=SUM(B2:B9)", "=SUM(C2:C9)"])
    mo.append(["Contrôle", '=IF(B10=Vérification!B5,"OK","ERREUR")', '=IF(C10=Vérification!B9,"OK","ERREUR")'])
    flag(mo, "B11:C11")

    # ---- Exemple de l'énoncé
    ee = wb.create_sheet("Exemple_énoncé")
    header(ee, ["Étape", "Nombre", "Formule", "Attendu (énoncé)", "Contrôle"], [34, 10, 26, 16, 10])
    ex_rows = [("Scopus", 420, "saisi", 420), ("Web of Science", 310, "saisi", 310), ("IEEE Xplore", 180, "saisi", 180), ("ACM DL", 90, "saisi", 90),
               ("Références identifiées", "=SUM(B2:B5)", "=SUM(B2:B5)", 1000), ("Doublons supprimés", 220, "saisi", 220),
               ("Références examinées", "=B6-B7", "=B6-B7", 780), ("Exclues titre/résumé", 550, "saisi", 550),
               ("Textes intégraux recherchés", "=B8-B9", "=B8-B9", 230), ("Textes non récupérés", 10, "saisi", 10),
               ("Textes intégraux évalués", "=B10-B11", "=B10-B11", 220), ("Exclusions avec motifs", 160, "saisi", 160),
               ("Études incluses", "=B12-B13", "=B12-B13", 60)]
    for i, (a, b, c, d) in enumerate(ex_rows, start=2):
        ee.append([a, b, c, d, f'=IF(B{i}=D{i},"OK","ERREUR")'])
    flag(ee, "E2:E14")

    # ---- Défis (étape 13)
    de = wb.create_sheet("Défis")
    for col, w in zip("ABCDEF", [44, 12, 14, 30, 12, 60]):
        de.column_dimensions[col].width = w
    de.append(["Question 1 : 1200 identifiées, 300 doublons"])
    de.cell(1, 1).font = BOLD
    de.append(["Identifiées", 1200])
    de.append(["Doublons", 300])
    de.append(["Examinées = identifiées − doublons", "=B2-B3"])
    de.append([])
    de.append(["Question 2 : 250 recherchés, dont 20 non récupérés"])
    de.cell(6, 1).font = BOLD
    de.append(["Textes intégraux recherchés", 250])
    de.append(["Non récupérés", 20])
    de.append(["Évalués = recherchés − non récupérés", "=B7-B8"])
    de.append(["(Les 400 exclus au screening ne changent rien : ils sont déjà déduits des 250 recherchés.)"])
    de.append([])
    de.append(["Défi 1 : tableau avec incohérences", "Saisi", "Recalculé", "Formule", "Contrôle", "Correction"])
    for c in range(1, 7):
        de.cell(12, c).font = BOLD
        de.cell(12, c).fill = HEAD
    d1 = [("Références identifiées", 950, "=B13", "saisi"),
          ("Doublons supprimés", 200, "=B14", "saisi"),
          ("Références examinées", 800, "=C13-C14", "identifiées − doublons"),
          ("Exclues titre/résumé", 500, "=B16", "saisi"),
          ("Textes intégraux recherchés", 300, "=C15-C16", "examinées − exclues"),
          ("Textes non récupérés", 10, "=B18", "saisi"),
          ("Textes intégraux évalués", 240, "=C17-C18", "recherchés − non récupérés"),
          ("Exclusions avec motifs", 180, "=SUM(B23:B25)", "somme des motifs ci-dessous"),
          ("Études incluses", 70, "=C19-C20", "évalués − exclusions")]
    for i, (a, b, c, d) in enumerate(d1, start=13):
        de.append([a, b, c, d, f'=IF(B{i}=C{i},"OK","ERREUR")',
                   f'=IF(B{i}=C{i},"",CONCATENATE("Remplacer ",B{i}," par ",C{i}))'])
    de.append(["  dont motifs détaillés :"])
    for a, b in (("  Population hors cible", 95), ("  Design non expérimental", 50), ("  Langue", 30)):
        de.append([a, b])
    flag(de, "E13:E21")
    de.append([])
    de.append(["Défi 2 : nombres bruts 850, 150, 500, 120, 380, 15, 365, 130, 235", "Valeur", "Recalculé", "Formule", "Contrôle", "Lecture"])
    r0 = de.max_row
    for c in range(1, 7):
        de.cell(r0, c).font = BOLD
        de.cell(r0, c).fill = HEAD
    d2 = [("Références identifiées", 850, None, "saisi", ""),
          ("Doublons supprimés", 150, None, "saisi", ""),
          ("Retirés pour une autre raison avant le screening", None, f"=B{r0 + 1}-B{r0 + 2}-B{r0 + 4}", "identifiées − doublons − examinées",
           "850 − 150 = 700 ≠ 500 : 200 enregistrements doivent être justifiés (case « autres raisons ») ou les doublons sont faux"),
          ("Références examinées", 500, None, "saisi", ""),
          ("Exclues titre/résumé", 120, None, "saisi", ""),
          ("Textes intégraux recherchés", 380, f"=B{r0 + 4}-B{r0 + 5}", "examinées − exclues", ""),
          ("Textes non récupérés", 15, None, "saisi", ""),
          ("Textes intégraux évalués", 365, f"=B{r0 + 6}-B{r0 + 7}", "recherchés − non récupérés", ""),
          ("Exclusions avec motifs", 130, None, "saisi", ""),
          ("Études incluses", 235, f"=B{r0 + 8}-B{r0 + 9}", "évalués − exclusions", "")]
    for i, (a, b, c, d, e) in enumerate(d2, start=r0 + 1):
        ctrl = f'=IF(B{i}=C{i},"OK","ERREUR")' if c and b is not None else ""
        de.append([a, b, c, d, ctrl, e])
    flag(de, f"E{r0 + 1}:E{de.max_row}")

    for w in wb.worksheets:
        for row in w.iter_rows():
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=cell.column_letter in ("F",) and w.title in ("Exclusions", "Défis"))
    OUTFILE.parent.mkdir(exist_ok=True)
    wb.save(OUTFILE)
    recalc(OUTFILE)
    return OUTFILE


def recalc(path):
    """Recalcule le classeur avec LibreOffice pour enregistrer les valeurs des formules (sinon Excel le fera à l'ouverture)."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print("LibreOffice absent : les formules seront calculées à l'ouverture dans Excel.")
        return
    with tempfile.TemporaryDirectory() as t:
        subprocess.run([soffice, "--headless", "--calc", "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", t, str(path)],
                       check=True, capture_output=True)
        shutil.copy(Path(t) / path.name, path)


if __name__ == "__main__":
    p = build()
    from openpyxl import load_workbook
    wb = load_workbook(p, data_only=True)
    v = wb["Vérification"]
    for r in range(2, 12):
        print(f"{v.cell(r, 1).value:<36} {v.cell(r, 2).value!s:>5}  contrôle {v.cell(r, 4).value!s:>5}  {v.cell(r, 6).value}")
    print(v.cell(13, 2).value)
