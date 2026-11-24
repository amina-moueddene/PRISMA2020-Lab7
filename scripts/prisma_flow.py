#!/usr/bin/env python3
"""Lab 7 - Construire le diagramme de flux PRISMA 2020 à partir des décisions de la revue.

Revue : Machine learning and remote sensing for disease and stress detection in olive.
Les nombres ne sont pas saisis à la main : ils sont recalculés à partir des sources.

Entrées
  data/identification.csv                     enregistrements identifiés par base (Lab 3)
  data/Screening_ledger_olive_PRISMA2020.csv  une ligne par enregistrement unique, avec la décision et l'étape (Labs 5-6)
  data/rapports_etudes.csv                    rapports qui décrivent la même étude
  data/PRISMA_template_officiel.csv           modèle CSV de l'outil officiel (package R PRISMA2020, licence MIT)

Sorties (output/)
  01_identification.csv           étape 2
  02_records_reports_studies.csv  étape 3
  03_verification.csv             étapes 4 à 11 (tableau de vérification)
  04_exclusions_titre_resume.csv  étape 6 (motifs)
  05_exclusions_texte_integral.csv étape 10 (une ligne par rapport exclu : DOI, motif, commentaire)
  06_controles.csv                étape 11 (contrôles arithmétiques)
  07_PRISMA_officiel.csv          étape 12 : fichier à importer dans l'outil officiel
  08_prisma2020_flow.svg / .png   étape 12 : diagramme au format du modèle officiel
Usage : python scripts/prisma_flow.py
"""
import csv
import io
import re
import subprocess
from collections import Counter, OrderedDict
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
DATA, OUT = ROOT / "data", ROOT / "output"

REASONS = {"E1": "Published before 2013", "E2": "Not olive", "E3": "No disease or stress target",
           "E4": "No aerial or satellite sensing", "E5": "No machine-learning model", "E6": "Review or editorial",
           "E7": "Book, chapter or front matter", "E8": "Language"}
REASONS_FR = {"E1": "Avant 2013", "E2": "Pas l'olivier", "E3": "Ni maladie ni stress",
              "E4": "Pas de télédétection aérienne ou satellitaire", "E5": "Pas de modèle appris",
              "E6": "Revue ou éditorial", "E7": "Livre, chapitre ou présentation d'actes", "E8": "Langue"}
ORDER = list(REASONS)


def read(path):
    return list(csv.DictReader(io.StringIO(Path(path).read_text(encoding="utf-8-sig"))))


def write(path, header, rows):
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def code(s):
    m = re.search(r"\((E\d)\)", s)
    return m.group(1) if m else ""


# ---------------------------------------------------------------- calcul des nombres
def compute(ident, ledger, links):
    sought_stages = {"Full text", "Title/abstract (full text not retrieved)"}
    ta_excl = [r for r in ledger if r["decision_stage"] not in sought_stages]
    sought = [r for r in ledger if r["decision_stage"] in sought_stages]
    not_retr = [r for r in sought if "not retrieved" in r["decision_stage"]]
    assessed = [r for r in sought if r["decision_stage"] == "Full text"]
    ft_excl = [r for r in assessed if r["final_decision"].startswith("Excluded")]
    included = [r for r in assessed if r["final_decision"] == "Included"]
    to_study = {l["record_rapport"]: l["etude"] for l in links}
    studies = sorted({to_study.get(r["record"], r["record"]) for r in included}, key=int)
    n = OrderedDict()
    n["identifies_par_base"] = {r["Base"]: int(r["Nombre"]) for r in ident}
    n["identifies"] = sum(n["identifies_par_base"].values())
    n["doublons"] = n["identifies"] - len(ledger)
    n["examines"] = len(ledger)
    n["exclus_titre_resume"] = len(ta_excl)
    n["exclus_titre_resume_par_motif"] = {k: v for k, v in sorted(Counter(code(r["final_decision"]) for r in ta_excl).items(), key=lambda x: ORDER.index(x[0]))}
    n["recherches"] = len(sought)
    n["non_recuperes"] = len(not_retr)
    n["evalues"] = len(assessed)
    n["exclus_texte_integral"] = len(ft_excl)
    n["exclus_texte_integral_par_motif"] = {k: v for k, v in sorted(Counter(code(r["final_decision"]) for r in ft_excl).items(), key=lambda x: ORDER.index(x[0]))}
    n["rapports_inclus"] = len(included)
    n["etudes_incluses"] = len(studies)
    return n, {"ta_excl": ta_excl, "sought": sought, "not_retr": not_retr, "assessed": assessed,
               "ft_excl": ft_excl, "included": included, "studies": studies, "to_study": to_study}


def apply_comments(g):
    """Remplace la raison du tableau de tri par le motif final documenté, quand il est fourni."""
    f = DATA / "commentaires_texte_integral.csv"
    if f.exists():
        over = {r["record"]: r["commentaire"] for r in read(f)}
        for r in g["ft_excl"]:
            if r["record"] in over:
                r["reason"] = over[r["record"]]


def checks(n):
    """Contrôles de cohérence du lab (étape 11) + contrôles des sous-totaux par motif."""
    c = [
        ("Identifiés = somme des bases", n["identifies"], sum(n["identifies_par_base"].values())),
        ("Identifiés = doublons + examinés", n["identifies"], n["doublons"] + n["examines"]),
        ("Recherchés = examinés − exclus titre/résumé", n["recherches"], n["examines"] - n["exclus_titre_resume"]),
        ("Évalués = recherchés − non récupérés", n["evalues"], n["recherches"] - n["non_recuperes"]),
        ("Rapports inclus = évalués − exclus texte intégral", n["rapports_inclus"], n["evalues"] - n["exclus_texte_integral"]),
        ("Exclus titre/résumé = somme des motifs", n["exclus_titre_resume"], sum(n["exclus_titre_resume_par_motif"].values())),
        ("Exclus texte intégral = somme des motifs", n["exclus_texte_integral"], sum(n["exclus_texte_integral_par_motif"].values())),
        ("Études incluses ≤ rapports inclus", True, n["etudes_incluses"] <= n["rapports_inclus"]),
    ]
    return [(name, a, b, a == b) for name, a, b in c]


def check_flow(f, motifs=None):
    """Défi 1 : vérifie un tableau de flux et renvoie les erreurs et les valeurs corrigées.

    f : dict avec identifies, doublons, examines, exclus_titre_resume, recherches, non_recuperes,
        evalues, exclus_texte_integral, inclus (et éventuellement retires_autres).
    motifs : liste des effectifs par motif d'exclusion du texte intégral (facultatif).
    Les valeurs saisies (identifiées, doublons, exclusions, non récupérés, motifs) sont considérées comme
    justes ; chaque valeur dérivée est recalculée à partir d'elles, dans l'ordre du diagramme.
    """
    rules = [("examines", lambda g: g["identifies"] - g["doublons"] - g.get("retires_autres", 0)),
             ("recherches", lambda g: g["examines"] - g["exclus_titre_resume"]),
             ("evalues", lambda g: g["recherches"] - g["non_recuperes"])]
    if motifs is not None:
        rules.append(("exclus_texte_integral", lambda g: sum(motifs)))
    rules.append(("inclus", lambda g: g["evalues"] - g["exclus_texte_integral"]))
    fixed, errors = dict(f), []
    for key, rule in rules:
        expected = rule(fixed)
        if fixed[key] != expected:
            errors.append((key, fixed[key], expected))
            fixed[key] = expected
    return errors, fixed


DEFI1 = dict(identifies=950, doublons=200, examines=800, exclus_titre_resume=500, recherches=300,
             non_recuperes=10, evalues=240, exclus_texte_integral=180, inclus=70)
DEFI1_MOTIFS = [95, 50, 30]  # population hors cible, design non expérimental, langue


def defi2():
    """Défi 2 : 850, 150, 500, 120, 380, 15, 365, 130, 235 -> nombres du diagramme.

    850 − 150 = 700 ≠ 500 : 200 enregistrements retirés avant le screening ne sont pas expliqués.
    Lecture retenue : ils sont déclarés dans la case « retirés pour d'autres raisons », à justifier.
    """
    n = {"identifies": 850, "doublons": 150, "retires_autres": 200, "examines": 500, "exclus_titre_resume": 120,
         "exclus_titre_resume_par_motif": {}, "recherches": 380, "non_recuperes": 15, "evalues": 365,
         "exclus_texte_integral": 130, "exclus_texte_integral_par_motif": {}, "rapports_inclus": 235, "etudes_incluses": 235}
    errors, _ = check_flow({"identifies": 850, "doublons": 150, "retires_autres": 200, "examines": 500, "exclus_titre_resume": 120,
                            "recherches": 380, "non_recuperes": 15, "evalues": 365, "exclus_texte_integral": 130, "inclus": 235})
    return n, errors


# ---------------------------------------------------------------- outil officiel
def official_csv(n, template_path, out_path):
    """Remplit le modèle CSV de l'outil officiel (Shiny app / package R PRISMA2020)."""
    rows = read(template_path)
    tr = "; ".join(f"{REASONS[k]} ({k}), {v}" for k, v in n["exclus_titre_resume_par_motif"].items())
    fr = "; ".join(f"{REASONS[k]} ({k}), {v}" for k, v in n["exclus_texte_integral_par_motif"].items())
    values = {
        "database_results": n["identifies"],
        "database_specific_results": "; ".join(f"{k}, {v}" for k, v in n["identifies_par_base"].items()),
        "register_results": 0, "register_specific_results": 0, "other_excluded": 0, "website_results": 0, "organisation_results": 0, "citations_results": 0,
        "duplicates": n["doublons"], "excluded_automatic": 0, "excluded_other": 0,
        "records_screened": n["examines"], "records_excluded": n["exclus_titre_resume"],
        "dbr_sought_reports": n["recherches"], "dbr_notretrieved_reports": n["non_recuperes"],
        "dbr_assessed": n["evalues"], "dbr_excluded": fr,
        "new_studies": n["etudes_incluses"], "new_reports": n["rapports_inclus"],
        "total_studies": n["etudes_incluses"], "total_reports": n["rapports_inclus"],
    }
    for r in rows:
        if r["data"] in values:
            r["n"] = values[r["data"]]
    with Path(out_path).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return tr


# ---------------------------------------------------------------- diagramme (structure du modèle officiel)
def svg_flow(n, lang="en", title=None):
    T = {
        "en": dict(head="Identification of studies via databases and registers", ident="Identification", scr="Screening", inc="Included",
                   rec="Records identified from:", dbs="Databases", regs="Registers", rem="Records removed before screening:",
                   dup="Duplicate records removed", auto="Records marked as ineligible by automation tools", oth="Records removed for other reasons",
                   scrd="Records screened", excl="Records excluded", sought="Reports sought for retrieval", notr="Reports not retrieved",
                   ass="Reports assessed for eligibility", rexc="Reports excluded", stud="Studies included in review",
                   reps="Reports of included studies", R=REASONS),
        "fr": dict(head="Identification des études via les bases de données et registres", ident="Identification", scr="Sélection", inc="Inclusion",
                   rec="Enregistrements identifiés :", dbs="Bases de données", regs="Registres", rem="Enregistrements retirés avant la sélection :",
                   dup="Doublons retirés", auto="Marqués inéligibles par un outil automatique", oth="Retirés pour d'autres raisons",
                   scrd="Enregistrements examinés", excl="Enregistrements exclus", sought="Rapports recherchés", notr="Rapports non récupérés",
                   ass="Rapports évalués pour l'éligibilité", rexc="Rapports exclus", stud="Études incluses dans la revue",
                   reps="Rapports des études incluses", R=REASONS_FR),
    }[lang]
    W, H = 900, 900
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Arial, Helvetica, sans-serif">',
           '<defs><marker id="a" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="#000"/></marker></defs>',
           f'<rect width="{W}" height="{H}" fill="#fff"/>']
    if title:
        out.append(f'<text x="{W / 2}" y="22" text-anchor="middle" font-size="15" font-weight="bold">{escape(title)}</text>')
    y0 = 40 if title else 30

    def box(x, y, w, h, lines, fill="#fff", bold_first=False, size=13):
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="#000" stroke-width="1.2"/>')
        ty = y + (h - 17 * len(lines)) / 2 + 13
        for i, ln in enumerate(lines):
            anchor, tx = ("middle", x + w / 2) if not ln.startswith("  ") else ("start", x + 14)
            weight = ' font-weight="bold"' if bold_first and i == 0 else ""
            out.append(f'<text x="{tx}" y="{ty + 17 * i}" text-anchor="{anchor}" font-size="{size}"{weight}>{escape(ln.strip() if anchor == "middle" else ln.strip())}</text>')

    def arrow(x1, y1, x2, y2):
        out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#000" stroke-width="1.2" marker-end="url(#a)"/>')

    def phase(y, h, label):
        out.append(f'<rect x="20" y="{y}" width="34" height="{h}" rx="6" fill="#9dc3e6" stroke="#5b9bd5"/>')
        out.append(f'<text transform="translate(42,{y + h / 2}) rotate(-90)" text-anchor="middle" font-size="14" font-weight="bold">{escape(label)}</text>')

    # en-tête jaune
    box(70, y0, 810, 40, [T["head"]], "#ffd966", True, 14)
    LX, LW, RX, RW = 70, 370, 500, 380
    # identification
    yi = y0 + 60
    phase(yi, 150, T["ident"])
    dbl = "; ".join(f"{k.replace(' Core Collection', '')} n = {v}" for k, v in n.get("identifies_par_base", {}).items())
    box(LX, yi, LW, 150, [T["rec"], f"{T['dbs']} (n = {n['identifies']})"] + ([f"({dbl})"] if dbl else []) + [f"{T['regs']} (n = 0)"])
    box(RX, yi, RW, 150, [T["rem"], f"{T['dup']} (n = {n['doublons']})", f"{T['auto']} (n = {n.get('retires_auto', 0)})",
                          f"{T['oth']} (n = {n.get('retires_autres', 0)})"], size=12)
    arrow(LX + LW, yi + 75, RX, yi + 75)
    # screening
    ys = yi + 180
    phase(ys, 420, T["scr"])
    tr = n["exclus_titre_resume_par_motif"]
    rows = [(f"{T['scrd']}", f"(n = {n['examines']})"), (f"{T['sought']}", f"(n = {n['recherches']})"),
            (f"{T['ass']}", f"(n = {n['evalues']})")]
    rights = [[f"{T['excl']} (n = {n['exclus_titre_resume']})"] + [f"  {T['R'][k]} ({k}): {v}" for k, v in tr.items()],
              [f"{T['notr']}", f"(n = {n['non_recuperes']})"],
              [f"{T['rexc']} (n = {n['exclus_texte_integral']})"] + [f"  {T['R'][k]} ({k}): {v}" for k, v in n["exclus_texte_integral_par_motif"].items()]]
    heights = [125, 80, 110]
    yy = ys
    for (a, b), right, h in zip(rows, rights, heights):
        box(LX, yy + (h - 60) / 2, LW, 60, [a, b])
        box(RX, yy, RW, h, right, size=12)
        arrow(LX + LW, yy + h / 2, RX, yy + h / 2)
        yy += h + 52
    # flèches verticales
    arrow(LX + LW / 2, yi + 150, LX + LW / 2, ys + (125 - 60) / 2)
    arrow(LX + LW / 2, ys + (125 + 60) / 2, LX + LW / 2, ys + 125 + 52 + 10)
    arrow(LX + LW / 2, ys + 125 + 52 + 70, LX + LW / 2, ys + 125 + 52 + 80 + 52 + 25)
    # inclusion
    yinc = ys + 440
    phase(yinc, 90, T["inc"])
    arrow(LX + LW / 2, ys + 125 + 52 + 80 + 52 + 85, LX + LW / 2, yinc + 5)
    box(LX, yinc + 5, LW, 80, [f"{T['stud']} (n = {n['etudes_incluses']})", f"{T['reps']} (n = {n['rapports_inclus']})"], "#fff", True)
    out.append("</svg>")
    return "\n".join(out).replace(f'height="{H}" viewBox="0 0 {W} {H}"', f'height="{yinc + 120}" viewBox="0 0 {W} {yinc + 120}"').replace(
        f'<rect width="{W}" height="{H}" fill="#fff"/>', f'<rect width="{W}" height="{yinc + 120}" fill="#fff"/>')


def to_png(svg_path):
    png = svg_path.with_suffix(".png")
    try:
        subprocess.run(["rsvg-convert", "-z", "1.6", "-o", str(png), str(svg_path)], check=True, capture_output=True)
        return png
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


# ---------------------------------------------------------------- programme principal
def main():
    OUT.mkdir(exist_ok=True)
    ident, ledger, links = read(DATA / "identification.csv"), read(DATA / "Screening_ledger_olive_PRISMA2020.csv"), read(DATA / "rapports_etudes.csv")
    n, g = compute(ident, ledger, links)
    apply_comments(g)

    write(OUT / "01_identification.csv", ["Base", "Nombre"], [[k, v] for k, v in n["identifies_par_base"].items()] + [["Total", n["identifies"]]])
    write(OUT / "02_records_reports_studies.csv", ["Etape", "Unite", "Nombre", "Definition"], [
        ["Identification", "records", n["identifies"], "notices brutes exportées des bases (une par base)"],
        ["Après déduplication", "records", n["examines"], "notices uniques soumises au tri titre/résumé"],
        ["Recherche du texte intégral", "reports", n["recherches"], "documents complets recherchés (1 notice = 1 rapport ici)"],
        ["Évaluation de l'éligibilité", "reports", n["evalues"], "documents complets lus"],
        ["Inclusion", "reports", n["rapports_inclus"], "documents complets retenus"],
        ["Inclusion", "studies", n["etudes_incluses"], "études distinctes (Kallel 2022 et Makhloufi 2022 = une étude)"]])
    ver = [("Références identifiées", n["identifies"], "somme des bases"),
           ("Doublons supprimés", n["doublons"], "identifiées − examinées"),
           ("Références examinées", n["examines"], "notices uniques"),
           ("Références exclues (titre/résumé)", n["exclus_titre_resume"], "décision au tri titre/résumé"),
           ("Textes intégraux recherchés", n["recherches"], "examinées − exclues"),
           ("Textes non récupérés", n["non_recuperes"], "recherchés sans texte intégral"),
           ("Textes intégraux évalués", n["evalues"], "recherchés − non récupérés"),
           ("Exclusions avec motifs", n["exclus_texte_integral"], "décision sur texte intégral"),
           ("Rapports inclus", n["rapports_inclus"], "évalués − exclus"),
           ("Études incluses", n["etudes_incluses"], "rapports regroupés par étude")]
    write(OUT / "03_verification.csv", ["Etape", "Nombre", "Calcul"], ver)
    write(OUT / "04_exclusions_titre_resume.csv", ["Code", "Motif", "Nombre"],
          [[k, REASONS_FR[k], v] for k, v in n["exclus_titre_resume_par_motif"].items()] + [["Total", "", n["exclus_titre_resume"]]])
    write(OUT / "05_exclusions_texte_integral.csv", ["Record_SLR", "DOI", "Premier_auteur", "Annee", "Code", "Motif", "Commentaire"],
          [[r["record"], r["doi"].replace("https://doi.org/", "") or "sans DOI", r["first_author"], r["year"], code(r["final_decision"]),
            REASONS_FR[code(r["final_decision"])], r["reason"]] for r in g["ft_excl"]])
    res = checks(n)
    write(OUT / "06_controles.csv", ["Controle", "Valeur", "Attendu", "OK"], [[a, b, c, "OK" if d else "ERREUR"] for a, b, c, d in res])
    official_csv(n, DATA / "PRISMA_template_officiel.csv", OUT / "07_PRISMA_officiel.csv")
    for lang, name in (("en", "08_prisma2020_flow.svg"), ("fr", "08_prisma2020_flow_fr.svg")):
        p = OUT / name
        p.write_text(svg_flow(n, lang), encoding="utf-8")
        to_png(p)
    import json
    errs, fixed = check_flow(DEFI1, DEFI1_MOTIFS)
    write(OUT / "10_defi1_corrections.csv", ["Ligne", "Saisi", "Corrigé"], errs)
    n2, e2 = defi2()
    p = OUT / "11_defi2_prisma.svg"
    p.write_text(svg_flow(n2, "fr", "Défi 2 (nombres de l'énoncé ; 200 retraits à justifier)"), encoding="utf-8")
    to_png(p)
    (OUT / "00_nombres.json").write_text(json.dumps(n, ensure_ascii=False, indent=1), encoding="utf-8")
    for a, b, c, d in res:
        print(f"{'OK ' if d else 'ERREUR'} {a} : {b} / {c}")
    if not all(d for *_, d in res):
        raise SystemExit("Incohérence dans le diagramme")
    print(json.dumps(n, ensure_ascii=False))


if __name__ == "__main__":
    main()
