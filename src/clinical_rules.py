"""
MatriSuraksha - Clinical Decision Support System (CDSS) Rule Engine
Evidence-based intrapartum and antenatal referral triage for Primary Health Care (PHC/RH) units.
Aligned with MoHFW (India) Guidelines, Dakshin Dinajpur Protocols, and WHO Intrapartum Recommendations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class TriageLevel(Enum):
    GREEN = "Low Risk (Safe for PLHCU Delivery)"
    YELLOW = "Moderate Risk (Senior MO Review / Alert SDH)"
    RED = "High Risk (Immediate Emergency Referral to SDH/DH)"


@dataclass
class ClinicalTrigger:
    code: str
    category: str
    severity: str  # "RED" or "YELLOW"
    title: str
    clinical_rationale: str
    action_required: str


@dataclass
class CDSSAssessment:
    study_id: str
    triage_level: TriageLevel
    triage_color: str
    referral_recommended: bool
    urgency: str  # "Immediate", "Urgent Review", "Routine"
    recommended_destination: str
    stabilization_protocols: List[str]
    active_triggers: List[ClinicalTrigger] = field(default_factory=list)
    risk_score: float = 0.0  # 0 to 100 composite risk index


class MatriSurakshaCDSS:
    """
    Clinical Decision Support System engine for MatriSuraksha.
    Evaluates antenatal, intrapartum, and labor progression data.
    """

    def __init__(self):
        pass

    def evaluate_patient(self, patient: Dict[str, Any]) -> CDSSAssessment:
        study_id = str(patient.get("Unique Study ID", "UNKNOWN"))
        triggers: List[ClinicalTrigger] = []

        # 1. Blood Pressure & Hypertensive Disorders of Pregnancy
        sbp = patient.get("Systolic_BP")
        dbp = patient.get("Diastolic_BP")
        
        if sbp is not None and dbp is not None:
            if sbp >= 160 or dbp >= 110:
                triggers.append(
                    ClinicalTrigger(
                        code="HTN_SEVERE",
                        category="Hypertension / Preeclampsia",
                        severity="RED",
                        title="Severe Gestational Hypertension / Impending Eclampsia",
                        clinical_rationale=f"Blood pressure {sbp:.0f}/{dbp:.0f} mmHg reaches severe pre-eclampsia thresholds with high stroke/convulsion risk.",
                        action_required="Administer loading dose of MgSO4 (Pritchard regimen) and immediate referral to SDH/DH in ambulance with IV line in situ.",
                    )
                )
            elif sbp >= 140 or dbp >= 90:
                triggers.append(
                    ClinicalTrigger(
                        code="HTN_MODERATE",
                        category="Hypertension / Preeclampsia",
                        severity="YELLOW",
                        title="Gestational Hypertension / Mild Pre-eclampsia",
                        clinical_rationale=f"Blood pressure {sbp:.0f}/{dbp:.0f} mmHg requires strict 4-hourly monitoring, urine albumin screening, and MO evaluation.",
                        action_required="Perform urine albumin test. If albumin >= ++ or epigastric symptoms appear, escalate immediately to RED referral.",
                    )
                )

        # 2. Hemoglobin & Anemia
        hb = patient.get("Hemoglobin")
        if hb is not None:
            if hb < 7.0:
                triggers.append(
                    ClinicalTrigger(
                        code="ANEMIA_SEVERE",
                        category="Hematological",
                        severity="RED",
                        title="Severe Maternal Anemia (< 7.0 g/dL)",
                        clinical_rationale=f"Hb of {hb:.1f} g/dL severely impairs oxygen delivery during labor and substantially elevates postpartum hemorrhage mortality.",
                        action_required="Pre-arrange packed red blood cells (PRBC) and refer to facility with 24x7 blood bank (SDH/DH).",
                    )
                )
            elif hb < 10.0:
                triggers.append(
                    ClinicalTrigger(
                        code="ANEMIA_MODERATE",
                        category="Hematological",
                        severity="YELLOW",
                        title="Moderate Maternal Anemia (7.0 - 9.9 g/dL)",
                        clinical_rationale=f"Hb of {hb:.1f} g/dL increases susceptibility to fatigue, infection, and low tolerance to intrapartum blood loss.",
                        action_required="Active management of 3rd stage of labour (AMTSL) mandatory; ensure oxytocin ready at delivery.",
                    )
                )

        # 3. Fetal Well-being & Heart Rate
        fhr = patient.get("Fetal_Heart_Rate")
        if fhr is not None:
            if fhr < 110:
                triggers.append(
                    ClinicalTrigger(
                        code="FHR_BRADYCARDIA",
                        category="Fetal Well-being",
                        severity="RED",
                        title="Fetal Bradycardia (FHR < 110 bpm)",
                        clinical_rationale=f"Baseline fetal heart rate {fhr:.0f} bpm indicates acute fetal hypoxia/distress requiring immediate intervention.",
                        action_required="Administer maternal oxygen, left lateral position, stop oxytocics if running, and transfer urgently for emergency C-section.",
                    )
                )
            elif fhr > 160:
                triggers.append(
                    ClinicalTrigger(
                        code="FHR_TACHYCARDIA",
                        category="Fetal Well-being",
                        severity="RED",
                        title="Fetal Tachycardia (FHR > 160 bpm)",
                        clinical_rationale=f"Fetal heart rate {fhr:.0f} bpm indicates intrauterine distress or intra-amniotic infection.",
                        action_required="Assess maternal temperature, recheck FHR in 15 mins. If sustained, refer for electronic fetal monitoring / operative delivery.",
                    )
                )

        # 4. Gestational Age & Term Status
        ga = patient.get("Gestational_Age")
        if ga is not None:
            if ga < 36:
                triggers.append(
                    ClinicalTrigger(
                        code="PRETERM_LABOR",
                        category="Gestational Age",
                        severity="RED",
                        title="Preterm Labor (< 36 Weeks)",
                        clinical_rationale=f"Gestational age {ga:.0f} weeks carries significant risk of neonatal respiratory distress syndrome and prematurity complications.",
                        action_required="Administer antenatal corticosteroids (Dexamethasone) for lung maturity and transfer to facility with functional SNCU/NICU.",
                    )
                )
            elif ga >= 41:
                triggers.append(
                    ClinicalTrigger(
                        code="POSTTERM_PREGNANCY",
                        category="Gestational Age",
                        severity="YELLOW",
                        title="Post-term Pregnancy (>= 41 Weeks)",
                        clinical_rationale=f"Gestational age {ga:.0f} weeks increases risk of placental insufficiency, oligohydramnios, and meconium aspiration.",
                        action_required="Evaluate AFI and non-stress test; arrange planned referral if labor does not progress smoothly.",
                    )
                )

        # 5. Membrane Rupture & Sepsis Risk
        has_rom = patient.get("Has_ROM")
        rom_time = patient.get("ROM - Date & Time")
        if has_rom == 1 or patient.get("Reason_PROM_Dribbling") == 1:
            triggers.append(
                ClinicalTrigger(
                    code="PROM_LEAKING",
                    category="Intrapartum Progression",
                    severity="YELLOW",
                    title="Rupture of Membranes / Amniotic Fluid Dribbling",
                    clinical_rationale="Membrane rupture increases the hazard of ascending chorioamnionitis and cord prolapse.",
                    action_required="Check liquor color (clear vs meconium). If >12 hours or meconium stained, escalate to RED for antibiotic coverage and referral.",
                )
            )

        # 6. Obstetric History & Extreme Maternal Age
        age = patient.get("Age")
        if age is not None:
            if age <= 18:
                triggers.append(
                    ClinicalTrigger(
                        code="AGE_TEENAGE",
                        category="Obstetric Risk",
                        severity="YELLOW",
                        title="Adolescent Pregnancy (<= 18 years)",
                        clinical_rationale=f"Maternal age {age:.0f} is associated with cephalopelvic disproportion (CPD), prolonged labor, and hypertensive risk.",
                        action_required="Close partographic monitoring of cervical dilatation and station descent.",
                    )
                )
            elif age >= 35:
                triggers.append(
                    ClinicalTrigger(
                        code="AGE_ADVANCED",
                        category="Obstetric Risk",
                        severity="YELLOW",
                        title="Advanced Maternal Age (>= 35 years)",
                        clinical_rationale=f"Age {age:.0f} is associated with elevated rates of intrapartum complications and uterine atony.",
                        action_required="Careful intrapartum surveillance and anticipation of 3rd stage management.",
                    )
                )

        if patient.get("Has_Previous_Complications") == 1:
            triggers.append(
                ClinicalTrigger(
                    code="PREV_COMPLICATION",
                    category="Obstetric History",
                    severity="YELLOW",
                    title="History of Prior Pregnancy Complications",
                    clinical_rationale="Prior adverse outcomes (stillbirth, recurrent miscarriage) heighten recurring perinatal risk.",
                    action_required="Consult Senior Medical Officer for dedicated intrapartum delivery plan.",
                )
            )

        # 7. Check direct clinical reason flags if provided in record
        if patient.get("Reason_PIH_Eclampsia") == 1:
            if not any(t.code == "HTN_SEVERE" for t in triggers):
                triggers.append(
                    ClinicalTrigger(
                        code="DX_ECLAMPSIA",
                        category="Direct Clinical Diagnosis",
                        severity="RED",
                        title="Clinically Diagnosed Eclampsia / Pre-eclampsia",
                        clinical_rationale="Emergency condition with maternal mortality risk.",
                        action_required="Immediate MgSO4 and emergency transport to SDH/DH.",
                    )
                )

        if patient.get("Reason_Hemorrhage") == 1:
            triggers.append(
                ClinicalTrigger(
                    code="DX_HEMORRHAGE",
                    category="Direct Clinical Diagnosis",
                    severity="RED",
                    title="Obstetric Hemorrhage (APH / PPH)",
                    clinical_rationale="Severe blood loss requires immediate surgical and blood transfusion capability.",
                    action_required="Start two large-bore IV lines (16G), fluid resuscitation, and emergency transfer.",
                )
            )

        # Calculate Triage Level & Composite Risk Score
        red_count = sum(1 for t in triggers if t.severity == "RED")
        yellow_count = sum(1 for t in triggers if t.severity == "YELLOW")

        # Base scoring
        risk_score = min(100.0, (red_count * 40.0) + (yellow_count * 15.0))

        if red_count > 0:
            triage_level = TriageLevel.RED
            triage_color = "#D32F2F"  # Red
            referral_recommended = True
            urgency = "Immediate Emergency (within 30-45 minutes)"
            destination = "Sub-Divisional Hospital (Gangarampur SDH) or District Hospital (Balurghat DH)"
            stabilization = [
                "Establish wide-bore (16-18G) intravenous access.",
                "Maintain left lateral tilt position.",
                "Administer emergency loading medications (MgSO4 for eclampsia, Oxygen for fetal distress).",
                "Accompany in 102/108 Ambulance with trained health staff.",
            ]
        elif yellow_count >= 2:
            triage_level = TriageLevel.YELLOW
            triage_color = "#F57C00"  # Amber
            referral_recommended = True
            urgency = "Urgent Senior MO Review & Planned Transfer"
            destination = "Gangarampur SDH (Planned referral if no active progression)"
            stabilization = [
                "Senior Medical Officer examination.",
                "Continuous partographic recording every 30 minutes.",
                "Alert referral hospital before departure.",
            ]
        elif yellow_count == 1:
            triage_level = TriageLevel.YELLOW
            triage_color = "#FBC02D"  # Yellow
            referral_recommended = False
            urgency = "Close Vigilance at PLHCU"
            destination = "PLHCU Delivery with Contingency Referral Plan"
            stabilization = [
                "Monitor vitals and fetal heart rate every 30 minutes.",
                "Plot on Partograph.",
                "Re-evaluate in 2 hours.",
            ]
        else:
            triage_level = TriageLevel.GREEN
            triage_color = "#388E3C"  # Green
            referral_recommended = False
            urgency = "Routine Care"
            destination = "PLHCU Delivery (Local Rural Hospital / Primary Health Center)"
            stabilization = [
                "Supportive respectful maternity care.",
                "Standard partograph monitoring.",
                "Active management of third stage of labour (AMTSL) with Oxytocin.",
            ]

        return CDSSAssessment(
            study_id=study_id,
            triage_level=triage_level,
            triage_color=triage_color,
            referral_recommended=referral_recommended,
            urgency=urgency,
            recommended_destination=destination,
            stabilization_protocols=stabilization,
            active_triggers=triggers,
            risk_score=risk_score,
        )


if __name__ == "__main__":
    # Test sample patient cases
    cdss = MatriSurakshaCDSS()

    # Case 1: Healthy primigravida
    p1 = {
        "Unique Study ID": "TEST-01",
        "Age": 22,
        "Systolic_BP": 110,
        "Diastolic_BP": 70,
        "Hemoglobin": 11.5,
        "Fetal_Heart_Rate": 136,
        "Gestational_Age": 39,
    }
    r1 = cdss.evaluate_patient(p1)
    print(f"Case 1: {r1.triage_level.name} | Referral={r1.referral_recommended} | Score={r1.risk_score}")

    # Case 2: Severe Hypertension in teenage pregnancy
    p2 = {
        "Unique Study ID": "TEST-02",
        "Age": 17,
        "Systolic_BP": 165,
        "Diastolic_BP": 112,
        "Hemoglobin": 9.2,
        "Fetal_Heart_Rate": 140,
        "Gestational_Age": 38,
    }
    r2 = cdss.evaluate_patient(p2)
    print(f"Case 2: {r2.triage_level.name} | Referral={r2.referral_recommended} | Score={r2.risk_score}")
    for t in r2.active_triggers:
        print(f"  - [{t.severity}] {t.title}: {t.action_required}")
