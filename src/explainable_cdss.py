"""
MatriSuraksha - Comprehensive Explainable Continuous CDSS Engine
Incorporates full antenatal & intrapartum variables from the MatriSuraksha Excel dataset:
- Maternal Vitals: BP (Systolic/Diastolic), Pulse, Temperature (°F)
- Vaginal Exam: Cervical Dilatation (cm), Effacement (%), Station, Presentation/Lie
- Membranes & Liquor: ROM status, Liquor Color (Clear, Thin MSL, Thick MSL, Blood-stained)
- Fetal Status: Baseline FHR, Fetal movements, Ultrasound AFI, Placenta location
- Antenatal Risk: Gestational age, Gravida, Parity, Prior LUCS (C-Section), Prior Stillbirth/Loss
- Lab & Comorbidities: Hemoglobin, Urine Albumin (Neg to +++), Blood Sugar (GDM), PIH
Integrated with SHAP (SHapley Additive exPlanations) TreeExplainer.
"""

import os
import sys
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shap_explainer import MatriSurakshaSHAP

shap_engine = MatriSurakshaSHAP()


class ExplainableCDSS:

    def __init__(self):
        self.shap_engine = shap_engine

    def evaluate_vitals(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Parse Input Parameters with safe fallbacks
        sbp = float(data.get("systolic_bp") or data.get("Systolic_BP") or 120)
        dbp = float(data.get("diastolic_bp") or data.get("Diastolic_BP") or 80)
        pulse = float(data.get("pulse") or data.get("Pulse") or 78)
        temp = float(data.get("temp") or data.get("Vitals - Temp") or 98.4)
        hb = float(data.get("hemoglobin") or data.get("Hemoglobin") or 11.0)
        fhr = float(data.get("fetal_heart_rate") or data.get("Fetal_Heart_Rate") or 140)
        ga = float(data.get("gestational_age") or data.get("Gestational_Age") or 39.0)
        age = float(data.get("age") or data.get("Age") or 22)
        
        # Intrapartum Progression
        labor_duration = float(data.get("labor_duration") or data.get("duration_of_labor") or 0)
        cervix = float(data.get("cervical_dilatation") or data.get("cervix") or 3)
        effacement = float(data.get("effacement") or 50)
        station = str(data.get("station") or "0")
        stage_of_labor = str(data.get("stage_of_labor") or "Active Labour")
        presentation = str(data.get("presentation") or data.get("presenting_part") or "Vertex/Cephalic").upper()
        
        # Membranes & Liquor
        has_rom = int(data.get("has_rom") in [1, "1", "Yes", "YES", True])
        liquor_color = str(data.get("liquor_color") or "Clear").upper()
        
        # Antenatal History & Diagnostics
        gravida = int(data.get("gravida") or 1)
        parity_live = int(data.get("parity_live") or 0)
        parity_loss = int(data.get("parity_loss") or 0)
        prev_lucs = int(data.get("prev_lucs") in [1, "1", "Yes", "YES", True])
        prev_loss = int(data.get("has_prev_comp") in [1, "1", "Yes", "YES", True] or (parity_loss > 0))
        urine_albumin = str(data.get("urine_albumin") or "Nil").upper()
        blood_sugar = float(data.get("blood_sugar") or 90)
        usg_afi = str(data.get("usg_afi") or "Adequate").upper()
        usg_placenta = str(data.get("usg_placenta") or "Normal").upper()

        triggers: List[Dict[str, Any]] = []

        # -------------------------------------------------------------
        # Clinical Danger Triggers Evaluation (MoHFW / WHO Guidelines)
        # -------------------------------------------------------------

        # 1. Maternal Pulse Highlight & Shock / Infection
        pulse_highlight = {
            "status": "NORMAL",
            "val": pulse,
            "badge_class": "badge-normal",
            "alert_message": "Maternal pulse is physiological (60-99 bpm)."
        }
        if pulse >= 100:
            pulse_highlight = {
                "status": "TACHYCARDIA_ALERT",
                "val": pulse,
                "badge_class": "badge-danger pulse-animate",
                "alert_message": f"Maternal Tachycardia ({pulse:.0f} bpm) detected! Warning: Screen for dehydration, chorioamnionitis, or concealed intrapartum hemorrhage."
            }
            triggers.append({
                "severity": "YELLOW",
                "title": "Maternal Tachycardia (Pulse >= 100 bpm)",
                "text": f"Maternal pulse {pulse:.0f} bpm indicates cardiovascular stress or intra-amniotic infection.",
                "action": "Hydrate with IV Ringer Lactate, evaluate temperature and blood loss."
            })
        elif pulse < 60:
            pulse_highlight = {
                "status": "BRADYCARDIA_ALERT",
                "val": pulse,
                "badge_class": "badge-warning",
                "alert_message": f"Maternal Bradycardia ({pulse:.0f} bpm) detected."
            }

        # 2. Maternal Pyrexia / Intra-amniotic Infection
        if temp >= 100.4:
            triggers.append({
                "severity": "RED",
                "title": "Maternal Intrapartum Pyrexia (Fever >= 100.4°F)",
                "text": f"Maternal temperature {temp:.1f}°F suggests chorioamnionitis or systemic sepsis.",
                "action": "Start IV Ampicillin + Gentamicin, maternal paracetamol, and immediate transfer to SDH/DH."
            })

        # 3. Hypertensive Disorders of Pregnancy (PIH / Preeclampsia)
        if sbp >= 160 or dbp >= 110 or "+++" in urine_albumin or "++" in urine_albumin and (sbp >= 140 or dbp >= 90):
            triggers.append({
                "severity": "RED",
                "title": "Severe Preeclampsia / Hypertensive Crisis",
                "text": f"BP {sbp:.0f}/{dbp:.0f} mmHg with Urine Albumin [{urine_albumin}]. Extreme eclampsia stroke risk.",
                "action": "Administer Pritchard Loading Dose MgSO4 (4g IV over 10 min + 10g IM) and transfer in 108 ambulance with catheter."
            })
        elif sbp >= 140 or dbp >= 90 or "+" in urine_albumin or "TRACE" in urine_albumin:
            triggers.append({
                "severity": "YELLOW",
                "title": "Gestational Hypertension (Stage 1)",
                "text": f"BP {sbp:.0f}/{dbp:.0f} mmHg indicates preeclampsia risk.",
                "action": "Strict 2-hourly BP charting, urine albumin test, Senior MO review."
            })

        # 4. Fetal Well-being (Distress & Bradycardia/Tachycardia)
        if fhr < 110:
            triggers.append({
                "severity": "RED",
                "title": "Severe Fetal Distress / Bradycardia (< 110 bpm)",
                "text": f"Fetal Heart Rate {fhr:.0f} bpm indicates critical intrauterine hypoxia.",
                "action": "Maternal left lateral tilt, high-flow O2 (8-10 L/min), stop oxytocin immediately, emergency transfer for LSCS."
            })
        elif fhr > 160:
            triggers.append({
                "severity": "RED",
                "title": "Fetal Tachycardia (> 160 bpm)",
                "text": f"Fetal Heart Rate {fhr:.0f} bpm indicates intrauterine distress or maternal fever.",
                "action": "Evaluate maternal temperature, reassess in 15 mins, prepare for emergency transfer if sustained."
            })

        # 5. Malpresentation & Obstetric Mechanics
        if any(m in presentation for m in ["BREECH", "TRANSVERSE", "SHOULDER", "BROW", "FACE"]):
            triggers.append({
                "severity": "RED",
                "title": f"Fetal Malpresentation ({presentation})",
                "text": "Non-cephalic presentation cannot be safely delivered vaginally at primary healthcare unit.",
                "action": "Do NOT augment. Immediate transfer to SDH/DH with 24x7 operative theater capability."
            })

        # 6. Membrane Rupture & Meconium Stained Liquor (MSL)
        if "THICK" in liquor_color or "GRADE 3" in liquor_color or "GRADE 2" in liquor_color:
            triggers.append({
                "severity": "RED",
                "title": "Thick Meconium-Stained Liquor (MSL)",
                "text": "Thick particulate meconium indicates severe fetal hypoxia with extreme meconium aspiration syndrome risk.",
                "action": "Requires delivery in facility with functional SNCU/NICU and pediatric endotracheal suction on standby."
            })
        elif "THIN" in liquor_color or "MECONIUM" in liquor_color:
            triggers.append({
                "severity": "YELLOW",
                "title": "Thin Meconium-Stained Liquor",
                "text": "Light meconium staining warrants continuous electronic fetal surveillance.",
                "action": "Check FHR every 15 minutes. Escalate to RED if FHR decelerates."
            })
        elif has_rom:
            triggers.append({
                "severity": "YELLOW",
                "title": "Rupture of Membranes (PROM)",
                "text": "Membranes ruptured; ascending bacterial infection hazard.",
                "action": "Strict aseptic technique. If leaking > 12h, administer prophylactic antibiotics."
            })

        # 7. Placental & Fluid Pathologies
        if any(p in usg_placenta for p in ["PREVIA", "LOW", "MARGINAL"]):
            triggers.append({
                "severity": "RED",
                "title": "Placenta Previa / Low-Lying Placenta",
                "text": "Extreme hazard of catastrophic, unheralded antepartum hemorrhage during cervical dilation.",
                "action": "Strictly NO digital vaginal examination! Immediate emergency transfer with IV access."
            })

        if "OLIGO" in usg_afi:
            triggers.append({
                "severity": "YELLOW",
                "title": "Oligohydramnios (Reduced Amniotic Fluid)",
                "text": "Low AFI increases risk of cord compression and fetal deceleration during contractions.",
                "action": "Monitor FHR closely after each contraction."
            })

        # 8. Previous Cesarean (Trial of Labor after Cesarean - TOLAC / Scar Rupture)
        if prev_lucs:
            triggers.append({
                "severity": "RED",
                "title": "Previous Caesarean Section (Scarred Uterus)",
                "text": "Risk of uterine rupture during labor. VBAC trials are not authorized at primary PHC units without emergency LSCS back-up.",
                "action": "Planned institutional transfer to SDH/DH."
            })

        # 9. Severe / Moderate Anemia
        if hb < 7.0:
            triggers.append({
                "severity": "RED",
                "title": "Severe Maternal Anemia (Hb < 7.0 g/dL)",
                "text": f"Hemoglobin {hb:.1f} g/dL causes fatal decompensation during physiological intrapartum bleeding.",
                "action": "Arrange cross-matched packed red cells and transfer to hospital with functional blood bank."
            })
        elif hb < 10.0:
            triggers.append({
                "severity": "YELLOW",
                "title": "Moderate Maternal Anemia (7.0 - 9.9 g/dL)",
                "text": f"Hb {hb:.1f} g/dL reduces maternal physical stamina and tolerance to 3rd stage blood loss.",
                "action": "AMTSL with Oxytocin mandatory; have IV cannula secured."
            })

        # 10. Gestational Age & Term Boundaries
        if ga < 36:
            triggers.append({
                "severity": "RED",
                "title": "Preterm Labor (< 36 Weeks)",
                "text": f"Gestation {ga:.0f} weeks carries extreme neonatal respiratory distress and hypothermia hazard.",
                "action": "Dexamethasone 6mg IM loading, KMC preparation, and transfer to facility with SNCU."
            })
        elif ga >= 41:
            triggers.append({
                "severity": "YELLOW",
                "title": "Post-term Pregnancy (>= 41 Weeks)",
                "text": f"Gestation {ga:.0f} weeks elevates postmaturity and meconium aspiration hazards.",
                "action": "Strict partographic plotting; planned referral if labor does not advance."
            })

        # 11. Maternal Age & Obstetric History
        if age <= 18:
            triggers.append({
                "severity": "YELLOW",
                "title": "Adolescent Pregnancy (<= 18 years)",
                "text": f"Age {age:.0f} years has high correlation with cephalopelvic disproportion (CPD).",
                "action": "Close partograph monitoring of cervical progression."
            })
        if prev_loss:
            triggers.append({
                "severity": "YELLOW",
                "title": "History of Prior Obstetric Loss / Complication",
                "text": "Past perinatal loss heightens recurrence risk.",
                "action": "Senior Medical Officer review."
            })

        # 12. Gestational Diabetes (Blood Sugar)
        if blood_sugar >= 140:
            triggers.append({
                "severity": "YELLOW",
                "title": "Elevated Blood Glucose / Gestational Diabetes",
                "text": f"Blood sugar {blood_sugar:.0f} mg/dL elevates risk of fetal macrosomia and shoulder dystocia.",
                "action": "Ensure pediatric resuscitation team is alerted."
            })

        # -------------------------------------------------------------
        # Synthesize Final AI Decision
        # -------------------------------------------------------------
        red_count = sum(1 for t in triggers if t["severity"] == "RED")
        yellow_count = sum(1 for t in triggers if t["severity"] == "YELLOW")

        risk_score = min(100.0, (red_count * 40.0) + (yellow_count * 15.0) + (10 if pulse >= 100 else 0))

        if red_count > 0:
            ai_decision = "REFER IMMEDIATELY (EMERGENCY TRANSFER)"
            ai_decision_code = "REFER"
            triage_level = "RED"
            triage_color = "#dc2626"
            triage_bg = "#fef2f2"
            urgency = "Immediate Emergency (within 30-45 minutes)"
            destination = "Gangarampur SDH or Balurghat DH (Secondary/Tertiary Hospital)"
            refer_flag = True
            stabilization_protocols = [
                "Establish wide-bore (16-18G) intravenous access with Ringer Lactate.",
                "Administer emergency loading dose (MgSO4 for severe HTN, Oxygen for fetal distress).",
                "Accompany patient in 102/108 Ambulance with trained health staff.",
                "Alert referral hospital before departure."
            ]
        elif yellow_count >= 2:
            ai_decision = "REFER (PLANNED TRANSFER AFTER SENIOR REVIEW)"
            ai_decision_code = "REFER"
            triage_level = "YELLOW"
            triage_color = "#d97706"
            triage_bg = "#fffbeb"
            urgency = "Senior MO Review & Planned Transfer"
            destination = "Sub-Divisional Hospital (Gangarampur SDH)"
            refer_flag = True
            stabilization_protocols = [
                "Senior Medical Officer clinical evaluation.",
                "Continuous partograph plotting every 30 minutes.",
                "Secure IV access and alert referral hospital."
            ]
        elif yellow_count == 1:
            ai_decision = "DO NOT REFER YET — SENIOR MO VIGILANCE AT PHC"
            ai_decision_code = "VIGILANCE"
            triage_level = "YELLOW"
            triage_color = "#d97706"
            triage_bg = "#fffbeb"
            urgency = "Close 30-Min Partographic Vigilance"
            destination = "PLHCU Delivery with Contingency Referral Plan"
            refer_flag = False
            stabilization_protocols = [
                "Plot cervical dilatation and fetal heart rate on Partograph.",
                "Re-evaluate in 2 hours. If labor arrests, escalate to RED."
            ]
        else:
            ai_decision = "DO NOT REFER — SAFE FOR NORMAL PLHCU DELIVERY"
            ai_decision_code = "DO_NOT_REFER"
            triage_level = "GREEN"
            triage_color = "#16a34a"
            triage_bg = "#f0fdf4"
            urgency = "Routine Supportive Maternity Care"
            destination = "Primary Health Center / Rural Hospital"
            refer_flag = False
            stabilization_protocols = [
                "Respectful supportive maternity care.",
                "Routine partographic monitoring.",
                "Active management of 3rd stage of labour (AMTSL) with Oxytocin."
            ]

        # -------------------------------------------------------------
        # Run Real SHAP TreeExplainer Calculation
        # -------------------------------------------------------------
        shap_res = self.shap_engine.explain_patient(data)

        return {
            "ai_decision": ai_decision,
            "ai_decision_code": ai_decision_code,
            "referral_recommended": refer_flag,
            "triage_level": triage_level,
            "triage_color": triage_color,
            "triage_bg": triage_bg,
            "urgency": urgency,
            "recommended_destination": destination,
            "risk_score": risk_score,
            "pulse_highlight": pulse_highlight,
            "triggers": triggers,
            "stabilization_protocols": stabilization_protocols,
            "shap": shap_res,
        }


explainable_cdss = ExplainableCDSS()
