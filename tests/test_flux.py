"""Étapes 2 à 12 : nombres recalculés depuis les sources, contrôles, fichier pour l'outil officiel, diagramme."""
import unittest

from tests.helpers import ROOT, load, rows

pf = load("prisma_flow")
D = ROOT / "data"


class TestNombres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n, cls.g = pf.compute(rows(D / "identification.csv"), rows(D / "Screening_ledger_olive_PRISMA2020.csv"), rows(D / "rapports_etudes.csv"))

    def test_identification(self):
        self.assertEqual(self.n["identifies_par_base"], {"Scopus": 118, "Web of Science Core Collection": 97})
        self.assertEqual(self.n["identifies"], 215)

    def test_chaine_complete(self):
        n = self.n
        self.assertEqual((n["doublons"], n["examines"], n["exclus_titre_resume"], n["recherches"], n["non_recuperes"],
                          n["evalues"], n["exclus_texte_integral"], n["rapports_inclus"], n["etudes_incluses"]),
                         (72, 143, 90, 53, 15, 38, 15, 23, 22))

    def test_motifs(self):
        self.assertEqual(self.n["exclus_titre_resume_par_motif"], {"E2": 36, "E3": 17, "E4": 12, "E6": 11, "E7": 14})
        self.assertEqual(self.n["exclus_texte_integral_par_motif"], {"E3": 5, "E4": 5, "E5": 5})

    def test_tous_les_controles_passent(self):
        res = pf.checks(self.n)
        self.assertEqual(len(res), 8)
        self.assertTrue(all(ok for *_, ok in res), [r for r in res if not r[3]])

    def test_records_reports_studies(self):
        # 23 rapports, 22 études : Makhloufi 2022 (35) est rattaché à l'étude Kallel 2022 (109)
        self.assertEqual(len(self.g["included"]), 23)
        self.assertEqual(len(self.g["studies"]), 22)
        self.assertNotIn("35", self.g["studies"])
        self.assertIn("109", self.g["studies"])

    def test_un_controle_detecte_une_erreur(self):
        n = dict(self.n, evalues=39)
        self.assertFalse(all(ok for *_, ok in pf.checks(n)))


class TestSorties(unittest.TestCase):
    def test_csv_outil_officiel(self):
        v = {r["data"]: r["n"] for r in rows(ROOT / "output" / "07_PRISMA_officiel.csv")}
        expected = {"database_results": "215", "duplicates": "72", "records_screened": "143", "records_excluded": "90",
                    "dbr_sought_reports": "53", "dbr_notretrieved_reports": "15", "dbr_assessed": "38",
                    "new_studies": "22", "new_reports": "23", "register_results": "0", "excluded_other": "0"}
        for k, val in expected.items():
            self.assertEqual(v[k], val, k)
        self.assertEqual(v["dbr_excluded"], "No disease or stress target (E3), 5; No aerial or satellite sensing (E4), 5; No machine-learning model (E5), 5")
        self.assertNotIn("xxx", " ".join(v.values()))

    def test_meme_structure_que_le_modele_officiel(self):
        self.assertEqual([r["data"] for r in rows(ROOT / "output" / "07_PRISMA_officiel.csv")],
                         [r["data"] for r in rows(ROOT / "data" / "PRISMA_template_officiel.csv")])

    def test_diagramme_svg(self):
        svg = (ROOT / "output" / "08_prisma2020_flow.svg").read_text(encoding="utf-8")
        for txt in ("Databases (n = 215)", "Duplicate records removed (n = 72)", "Records screened", "(n = 143)",
                    "Records excluded (n = 90)", "(n = 53)", "(n = 15)", "(n = 38)", "Studies included in review (n = 22)",
                    "Reports of included studies (n = 23)", "Identification", "Screening", "Included"):
            self.assertIn(txt, svg)

    def test_quinze_exclusions_documentees(self):
        ex = rows(ROOT / "output" / "05_exclusions_texte_integral.csv")
        self.assertEqual(len(ex), 15)
        self.assertTrue(all(r["DOI"] and r["Code"] and r["Commentaire"] for r in ex))
        self.assertIn("irrigation", [r for r in ex if r["Record_SLR"] == "23"][0]["Commentaire"])


class TestDefis(unittest.TestCase):
    def test_questions(self):
        self.assertEqual(1200 - 300, 900)
        errors, fixed = pf.check_flow(dict(identifies=1200, doublons=300, examines=900, exclus_titre_resume=400, recherches=500,
                                           non_recuperes=20, evalues=480, exclus_texte_integral=0, inclus=480))
        self.assertEqual(errors, [])

    def test_defi1_corrections(self):
        errors, fixed = pf.check_flow(pf.DEFI1, pf.DEFI1_MOTIFS)
        self.assertEqual(errors, [("examines", 800, 750), ("recherches", 300, 250), ("exclus_texte_integral", 180, 175), ("inclus", 70, 65)])
        self.assertEqual(pf.check_flow(fixed, pf.DEFI1_MOTIFS)[0], [])

    def test_defi2(self):
        n, errors = pf.defi2()
        self.assertEqual(errors, [])
        self.assertEqual(n["identifies"] - n["doublons"] - n["retires_autres"], n["examines"])
        self.assertEqual(n["examines"] - n["exclus_titre_resume"], 380)
        self.assertEqual(380 - 15, 365)
        self.assertEqual(365 - 130, 235)
        self.assertEqual(n["identifies"] - n["doublons"], 700)  # ≠ 500 : l'écart de 200 doit être justifié


if __name__ == "__main__":
    unittest.main()
