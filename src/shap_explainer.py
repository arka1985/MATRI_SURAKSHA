"""
MatriSuraksha - SHAP (SHapley Additive exPlanations) Engine
Calculates true TreeExplainer Shapley values for patient referral risk prediction.
Generates waterfall attributions explaining why the model predicted referral vs local care.
"""

import os
import joblib
import numpy as np
import pandas as pd
import shap

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "champion_model.joblib")


class MatriSurakshaSHAP:

    def __init__(self):
        self.bundle = None
        self.explainer = None
        self.pipeline = None
        self.features = []
        self.base_value = 0.5
        self._init_explainer()

    def _init_explainer(self):
        if not os.path.exists(MODEL_PATH):
            return
        try:
            self.bundle = joblib.load(MODEL_PATH)
            self.pipeline = self.bundle["pipeline"]
            self.features = self.bundle["feature_names"]
            clf = self.pipeline.named_steps["clf"]
            self.explainer = shap.TreeExplainer(clf)
            
            # Base expected value for class 1 (Referral)
            if hasattr(self.explainer.expected_value, "__len__"):
                self.base_value = float(self.explainer.expected_value[1])
            else:
                self.base_value = float(self.explainer.expected_value)
        except Exception as e:
            print(f"Error initializing SHAP TreeExplainer: {e}")

    def explain_patient(self, patient_dict: dict) -> dict:
        """
        Computes patient-specific SHAP feature contributions.
        """
        if self.explainer is None:
            return {
                "base_value": 0.49,
                "prediction_prob": 0.5,
                "shap_contributions": [],
                "error": "Model not loaded"
            }

        # Build feature vector matching training schema
        age = float(patient_dict.get("age") or patient_dict.get("Age") or 22)
        sbp = float(patient_dict.get("systolic_bp") or patient_dict.get("Systolic_BP") or 120)
        dbp = float(patient_dict.get("diastolic_bp") or patient_dict.get("Diastolic_BP") or 80)
        hb = float(patient_dict.get("hemoglobin") or patient_dict.get("Hemoglobin") or 11.0)
        pulse = float(patient_dict.get("pulse") or patient_dict.get("Pulse") or 78)
        fhr = float(patient_dict.get("fetal_heart_rate") or patient_dict.get("Fetal_Heart_Rate") or 140)
        ga = float(patient_dict.get("gestational_age") or patient_dict.get("Gestational_Age") or 39.0)
        gravida = int(patient_dict.get("gravida") or patient_dict.get("Gravida_Num") or 1)
        parity_live = int(patient_dict.get("parity_live") or patient_dict.get("Parity_Live") or 0)
        anc = float(patient_dict.get("anc_visits") or patient_dict.get("ANC_Visits") or 4)
        has_rom = int(patient_dict.get("has_rom") or patient_dict.get("Has_ROM") or 0)
        prev_comp = int(patient_dict.get("has_prev_comp") in [1, "Yes", "YES", True] or patient_dict.get("prev_lucs") in [1, "Yes", "YES", True])

        row_dict = {
            "Age": age,
            "Is_Teenage": 1 if age <= 19 else 0,
            "Is_BPL": 1 if patient_dict.get("ses", "BPL") == "BPL" else 0,
            "Is_ST_SC": 1 if patient_dict.get("caste", "") in ["ST", "SC"] else 0,
            "Gravida_Num": gravida,
            "Is_Primigravida": 1 if gravida == 1 else 0,
            "Parity_Live": parity_live,
            "Gestational_Age": ga,
            "Is_Preterm": 1 if ga < 37 else 0,
            "ANC_Visits": anc,
            "Inadequate_ANC": 1 if anc < 4 else 0,
            "Has_Previous_Complications": prev_comp,
            "Hemoglobin": hb,
            "Has_Anemia": 1 if hb < 11.0 else 0,
            "Has_Moderate_Severe_Anemia": 1 if hb < 10.0 else 0,
            "Systolic_BP": sbp,
            "Diastolic_BP": dbp,
            "Is_Hypertensive": 1 if (sbp >= 140 or dbp >= 90) else 0,
            "Pulse": pulse,
            "Fetal_Heart_Rate": fhr,
            "Has_ROM": has_rom,
        }

        # Align to expected features
        X_df = pd.DataFrame([row_dict])[self.features]
        imputer = self.pipeline.named_steps["imputer"]
        X_imputed = imputer.transform(X_df)

        # Get Random Forest prediction probability for class 1
        clf = self.pipeline.named_steps["clf"]
        pred_prob = float(clf.predict_proba(X_imputed)[0, 1])

        # Compute SHAP values
        raw_shap = self.explainer.shap_values(X_imputed)
        if isinstance(raw_shap, list):
            sv = raw_shap[1][0]
        elif len(raw_shap.shape) == 3:
            sv = raw_shap[0, :, 1]
        else:
            sv = raw_shap[0]

        # Clinical display mapping & guideline annotations
        clinical_map = {
            "Systolic_BP": (f"{sbp:.0f} mmHg", "MoHFW Protocol: Target SBP < 140; SBP >= 160 indicates hypertensive emergency."),
            "Diastolic_BP": (f"{dbp:.0f} mmHg", "WHO Preeclampsia: DBP >= 90 requires evaluation; DBP >= 110 demands immediate MgSO4."),
            "Is_Hypertensive": ("Yes" if (sbp >= 140 or dbp >= 90) else "No", "Direct diagnostic indicator for preeclampsia triage."),
            "Hemoglobin": (f"{hb:.1f} g/dL", "Anemia Mukt Bharat: Hb < 11 g/dL limits blood loss tolerance; Hb < 7 requires blood standby."),
            "Has_Moderate_Severe_Anemia": ("Yes" if hb < 10.0 else "No", "Severe risk factor for intrapartum exhaustion & PPH."),
            "Pulse": (f"{pulse:.0f} bpm", "MoHFW Intrapartum: Pulse >= 100 flags dehydration, intra-amniotic infection, or shock."),
            "Fetal_Heart_Rate": (f"{fhr:.0f} bpm", "FIGO Intrapartum: Normal baseline is 110-160 bpm; extremes signify acute fetal hypoxia."),
            "Gestational_Age": (f"{ga:.1f} wks", "WHO Recommendations: < 37 wks requires SNCU/NICU capability; >= 41 wks risks placental failure."),
            "Is_Preterm": ("Yes" if ga < 37 else "No", "Major driver for secondary neonatal hospital referral."),
            "Has_ROM": ("Ruptured" if has_rom == 1 else "Intact", "Membrane rupture > 12h increases neonatal sepsis and cord prolapse hazard."),
            "Has_Previous_Complications": ("Yes" if prev_comp else "No", "History of stillbirth/LUCS elevates repeat operative risk."),
            "Age": (f"{age:.0f} yrs", "Adolescent (<= 19) pelvis heightens risk of obstructed labor & CPD."),
            "Is_Teenage": ("Yes" if age <= 19 else "No", "Vulnerable age bracket for obstetric emergencies."),
            "Gravida_Num": (f"G{gravida}", "Parity & labor duration dynamics."),
            "ANC_Visits": (f"{anc:.0f} visits", "Quality antenatal surveillance index."),
        }

        contributions = []
        for feat_name, shap_val in zip(self.features, sv):
            val_display, guideline = clinical_map.get(feat_name, (str(row_dict.get(feat_name, "")), "Biomedical feature weight."))
            val_float = float(shap_val)
            if abs(val_float) > 0.0001:
                contributions.append({
                    "feature": feat_name.replace("_", " "),
                    "display_value": val_display,
                    "shap_value": round(val_float, 4),
                    "impact": "INCREASES_RISK" if val_float > 0 else "PROTECTIVE_FACTOR",
                    "guideline": guideline,
                })

        # Sort contributions by absolute impact
        contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

        return {
            "base_value": round(self.base_value, 4),
            "prediction_prob": round(pred_prob, 4),
            "shap_contributions": contributions,
            "top_drivers": [c for c in contributions if c["impact"] == "INCREASES_RISK"][:5],
            "top_protective": [c for c in contributions if c["impact"] == "PROTECTIVE_FACTOR"][:5],
        }


if __name__ == "__main__":
    shap_engine = MatriSurakshaSHAP()
    test_pt = {
        "Age": 17,
        "Systolic_BP": 165,
        "Diastolic_BP": 110,
        "Pulse": 115,
        "Hemoglobin": 8.5,
        "Fetal_Heart_Rate": 162,
        "Gestational_Age": 38,
        "Has_ROM": 1
    }
    res = shap_engine.explain_patient(test_pt)
    print("Base Value:", res["base_value"])
    print("Prediction Prob:", res["prediction_prob"])
    print("\nTop SHAP Risk Pushers:")
    for d in res["top_drivers"]:
        print(f"  + {d['feature']} = {d['display_value']} (SHAP: +{d['shap_value']}) -> {d['guideline']}")
