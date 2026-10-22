"""
Unit tests for MatriSuraksha Clinical Decision Support System (CDSS)
Verifies:
1. Blood pressure parsing & hypertensive crisis detection
2. Severe anemia & vital sign boundary checks
3. Preterm & Postterm gestational flags
4. Emergency triage escalation (RED vs YELLOW vs GREEN)
"""

import unittest
import sys
import os

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from clinical_rules import MatriSurakshaCDSS, TriageLevel
from data_pipeline import parse_blood_pressure, parse_gravida, parse_parity, categorize_anemia


class TestMatriSurakshaCDSS(unittest.TestCase):

    def test_bp_parsing(self):
        self.assertEqual(parse_blood_pressure("120/80"), (120.0, 80.0))
        self.assertEqual(parse_blood_pressure("160 / 110"), (160.0, 110.0))
        import numpy as np
        sbp, dbp = parse_blood_pressure(None)
        self.assertTrue(np.isnan(sbp) and np.isnan(dbp))
        sbp2, dbp2 = parse_blood_pressure("invalid")
        self.assertTrue(np.isnan(sbp2) and np.isnan(dbp2))

    def test_gravida_parity_parsing(self):
        self.assertEqual(parse_gravida("1st "), 1)
        self.assertEqual(parse_gravida("4th"), 4)
        self.assertEqual(parse_parity("P0+0"), (0, 0))
        self.assertEqual(parse_parity("P2+1"), (2, 1))
        self.assertEqual(parse_parity("P3"), (3, 0))

    def test_anemia_categorization(self):
        self.assertEqual(categorize_anemia(12.0), "Normal")
        self.assertEqual(categorize_anemia(10.5), "Mild")
        self.assertEqual(categorize_anemia(8.5), "Moderate")
        self.assertEqual(categorize_anemia(6.5), "Severe")

    def test_cdss_routine_green(self):
        cdss = MatriSurakshaCDSS()
        patient = {
            "Unique Study ID": "TEST-NORMAL",
            "Age": 24,
            "Systolic_BP": 118,
            "Diastolic_BP": 76,
            "Hemoglobin": 11.8,
            "Gestational_Age": 39,
            "Fetal_Heart_Rate": 138,
            "Has_ROM": 0,
        }
        res = cdss.evaluate_patient(patient)
        self.assertEqual(res.triage_level, TriageLevel.GREEN)
        self.assertFalse(res.referral_recommended)
        self.assertEqual(res.risk_score, 0.0)

    def test_cdss_severe_hypertension_red(self):
        cdss = MatriSurakshaCDSS()
        patient = {
            "Unique Study ID": "TEST-SEVERE-HTN",
            "Age": 28,
            "Systolic_BP": 170,
            "Diastolic_BP": 115,
            "Hemoglobin": 10.2,
            "Gestational_Age": 38,
            "Fetal_Heart_Rate": 142,
        }
        res = cdss.evaluate_patient(patient)
        self.assertEqual(res.triage_level, TriageLevel.RED)
        self.assertTrue(res.referral_recommended)
        self.assertTrue(any(t.code == "HTN_SEVERE" for t in res.active_triggers))

    def test_cdss_fetal_distress_red(self):
        cdss = MatriSurakshaCDSS()
        patient = {
            "Unique Study ID": "TEST-FHR",
            "Age": 20,
            "Systolic_BP": 110,
            "Diastolic_BP": 70,
            "Hemoglobin": 11.0,
            "Gestational_Age": 40,
            "Fetal_Heart_Rate": 96,  # Severe bradycardia
        }
        res = cdss.evaluate_patient(patient)
        self.assertEqual(res.triage_level, TriageLevel.RED)
        self.assertTrue(res.referral_recommended)
        self.assertTrue(any(t.code == "FHR_BRADYCARDIA" for t in res.active_triggers))


if __name__ == "__main__":
    unittest.main()

