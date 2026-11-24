"""Étapes 4 à 11 et 13 : le classeur Excel contient de vraies formules, et leurs valeurs sont cohérentes."""
import unittest

from openpyxl import load_workbook

from tests.helpers import ROOT

XLSX = ROOT / "output" / "09_verification_prisma.xlsx"


class TestClasseur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = load_workbook(XLSX)                   # formules
        cls.v = load_workbook(XLSX, data_only=True)   # valeurs enregistrées

    def test_feuilles(self):
        self.assertEqual(self.f.sheetnames, ["Identification", "Vérification", "Records_Reports_Studies", "Tri", "Exclusions",
                                             "Liens_rapports_études", "Motifs", "Exemple_énoncé", "Défis"])

    def test_formules_du_lab(self):
        ws = self.f["Vérification"]
        self.assertTrue(str(self.f["Identification"]["B4"].value).upper().startswith("=SUM("))
        self.assertEqual(ws["B4"].value, "=B2-B3")
        self.assertEqual(ws["B6"].value, "=B4-B5")
        self.assertEqual(ws["B8"].value, "=B6-B7")
        self.assertEqual(ws["B10"].value, "=B8-B9")
        self.assertIn("COUNTA", str(self.f["Exclusions"]["B18"].value).upper())
        self.assertIn("IFERROR", str(ws["F2"].value).upper())

    def test_valeurs_et_controles(self):
        ws = self.v["Vérification"]
        self.assertEqual([ws.cell(r, 2).value for r in range(2, 12)], [215, 72, 143, 90, 53, 15, 38, 15, 23, 22])
        self.assertEqual([ws.cell(r, 4).value for r in range(2, 12)], [215, 72, 143, 90, 53, 15, 38, 15, 23, 22])
        self.assertTrue(all(ws.cell(r, 6).value == "OK" for r in list(range(2, 12)) + list(range(16, 21))))
        self.assertEqual(ws["B13"].value, "Tout est cohérent")

    def test_exemple_de_l_enonce(self):
        ws = self.v["Exemple_énoncé"]
        self.assertEqual([ws.cell(r, 2).value for r in (6, 8, 10, 12, 14)], [1000, 780, 230, 220, 60])
        self.assertTrue(all(ws.cell(r, 5).value == "OK" for r in range(2, 15)))

    def test_defis(self):
        ws = self.v["Défis"]
        self.assertEqual(ws["B4"].value, 900)
        self.assertEqual(ws["B9"].value, 230)
        corrections = [ws.cell(r, 6).value for r in range(13, 22) if ws.cell(r, 6).value]
        self.assertEqual(corrections, ["Remplacer 800 par 750", "Remplacer 300 par 250", "Remplacer 180 par 175", "Remplacer 70 par 65"])


if __name__ == "__main__":
    unittest.main()
