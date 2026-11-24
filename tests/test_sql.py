"""Vérification du script SQL PRISMA 2020 (sql/prisma_verification.sql) via sqlite3."""
import re
import sqlite3
import unittest

from tests.helpers import ROOT, rows


class TestSqlPrisma(unittest.TestCase):
    def test_sql_pipeline_and_checks(self):
        sql_script = (ROOT / "sql" / "prisma_verification.sql").read_text(encoding="utf-8")
        conn = sqlite3.connect(":memory:")
        conn.executescript(sql_script)

        # Charger le registre de tri réel (143 notices)
        ledger = rows(ROOT / "data" / "Screening_ledger_olive_PRISMA2020.csv")
        for r in ledger:
            m = re.search(r"\((E\d)\)", r["final_decision"])
            code_motif = m.group(1) if m else None
            conn.execute(
                "INSERT INTO screening_ledger VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (int(r["record"]), r["first_author"], int(r["year"]), r["doi"],
                 r["decision_stage"], r["final_decision"], code_motif, r["reason"]),
            )

        # Charger les 15 exclusions texte intégral
        exclusions = rows(ROOT / "output" / "05_exclusions_texte_integral.csv")
        for e in exclusions:
            conn.execute(
                "INSERT INTO exclusions_texte_integral VALUES (?, ?, ?, ?, ?, ?, ?)",
                (int(e["Record_SLR"]), e["DOI"], e["Premier_auteur"], int(e["Annee"]),
                 e["Code"], e["Motif"], e["Commentaire"]),
            )

        row = conn.execute("SELECT * FROM v_verification_prisma").fetchone()
        self.assertEqual(row, (215, 72, 143, 90, 53, 15, 38, 15, 23, 22))

        ctrls = conn.execute("SELECT * FROM v_controles_coherence").fetchone()
        self.assertEqual(ctrls, ("OK", "OK", "OK", "OK", "OK"))
        conn.close()


if __name__ == "__main__":
    unittest.main()
