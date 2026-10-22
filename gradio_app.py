"""
MatriSuraksha (মাতৃসুরক্ষা) - Official Gradio Clinical Decision Support System
2x2 Grid Layout & White-and-Orange Healthcare Theme

Cards Layout:
- Row 1, Col 1: Card 1 - Patient Vitals & Clinical Observation Entry
- Row 1, Col 2: Card 2 - TRIAGE Continuous Clinical Decision Support
- Row 2, Col 1: Card 3 - Attending Doctor Clinical Evaluation & Final Disposition
- Row 2, Col 2: Card 4 - SHAP Explainable AI Waterfall (TreeExplainer)

Research Project Grant Acknowledgment:
Institute of Health and Family Welfare (IHFW), Department of Health and Family Welfare, Government of West Bengal.
- Principal Investigator (PI): Dr. Dilip Kumar Biswas, Deputy CMOH – III, Dakshin Dinajpur
- Co-PI: Dr. Arkaprabha Sau, Public Health Specialist and Chief AI ML Scientist
- Co-PI: Dr. Ishita Bhakta, Assistant Professor, Department of Information Technology, Techno Main Salt Lake, Kolkata
"""

import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import gradio as gr

# Ensure src and app are in path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
sys.path.insert(0, os.path.join(BASE_DIR, "app"))

from explainable_cdss import explainable_cdss
import db

# Initialize DB tables
db.init_db()


# -------------------------------------------------------------
# Core CDSS & SHAP Evaluation Logic
# -------------------------------------------------------------
def create_empty_shap_figure():
    fig, ax = plt.subplots(figsize=(6.5, 3.2), facecolor="#ffffff")
    ax.set_facecolor("#ffffff")
    ax.text(0.5, 0.5, "Complete Section 1, 2, and 3 in Card 1,\nclick '1. Save Maternal Details',\nthen trigger '2. AI Based CDSS for Referral'\nto visualize SHAP TreeExplainer feature attributions.",
            ha="center", va="center", color="#94a3b8", fontsize=10, fontweight="600")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    plt.tight_layout()
    return fig


initial_triage_html = """
<div style="background: #f8fafc; border: 2px dashed #cbd5e1; border-left: 8px solid #94a3b8; border-radius: 10px; padding: 14px 16px; margin-bottom: 12px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
        <span style="font-size: 11px; font-weight: 800; color: #64748b; text-transform: uppercase;">AI Referral Recommendation</span>
        <span style="background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1; padding: 3px 12px; border-radius: 20px; font-size: 11px; font-weight: 800;">AWAITING INTAKE</span>
    </div>
    <div style="font-size: 16px; font-weight: 900; color: #475569; margin: 4px 0;">
        ⏳ AI DECISION: AWAITING CLINICAL INTAKE & EVALUATION
    </div>
    <div style="font-size: 12px; color: #64748b;">
        Complete Card 1 Intake, save maternal details, and click "2. AI Based CDSS for Referral".
    </div>
</div>

<div style="display: flex; flex-direction: column; gap: 10px; margin: 12px 0;">
    <div style="background: #ffffff; border: 1.5px solid #fed7aa; border-radius: 10px; padding: 12px 16px;">
        <div style="font-size: 11px; font-weight: 800; color: #ea580c; text-transform: uppercase;">⏱ AI Composite Risk Score</div>
        <div style="display: flex; align-items: baseline; gap: 6px;">
            <span style="font-size: 28px; font-weight: 900; color: #94a3b8;">--</span>
            <span style="font-size: 16px; font-weight: 600; color: #94a3b8;">/ 100</span>
            <span style="background: #f1f5f9; color: #64748b; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 800; margin-left: auto;">Pending Intake</span>
        </div>
    </div>
    <div style="background: #ffffff; border: 1.5px solid #fed7aa; border-radius: 10px; padding: 12px 16px;">
        <div style="font-size: 11px; font-weight: 800; color: #ea580c; text-transform: uppercase;">🏥 Care Destination & Facility Protocol</div>
        <div style="font-size: 14px; font-weight: 700; color: #64748b; line-height: 1.45;">
            Pending clinical intake data. Complete all 3 sections in Card 1, save details, and trigger AI CDSS.
        </div>
    </div>
</div>

<div style="background: #fffaf5; border: 1px solid #fed7aa; border-radius: 10px; padding: 12px 14px;">
    <h4 style="margin: 0 0 6px 0; font-size: 12px; color: #c2410c; text-transform: uppercase; font-weight: 800;">📋 Clinical Assessment Findings & Triggers</h4>
    <p style="margin: 0; font-size: 12px; color: #64748b;">Awaiting patient intake execution to trigger evidence-based danger sign alerts.</p>
</div>
"""


def check_sections_readiness(
    name, age, sbp, dbp, pulse, temp, stage,
    fhr, lie, cdil, eff, station, rom, liquor,
    ga, grav, hb, urine, plac, afi
):
    s1 = bool(name and str(name).strip() and age is not None and sbp is not None and dbp is not None and pulse is not None and temp is not None and stage)
    s2 = bool(fhr is not None and lie and cdil is not None and eff is not None and station and rom and liquor)
    s3 = bool(ga is not None and grav is not None and hb is not None and urine and plac and afi)
    count = (1 if s1 else 0) + (1 if s2 else 0) + (1 if s3 else 0)
    
    if count == 3:
        msg = "✅ **All 3 Sections Completed (3/3)**! Click **'1. Save Maternal Details'** to record patient."
        return msg, gr.update(interactive=True)
    else:
        pending = []
        if not s1: pending.append("Section 1 (Demographics & Vitals)")
        if not s2: pending.append("Section 2 (Vaginal Exam & Fetus)")
        if not s3: pending.append("Section 3 (Antenatal & Diagnostics)")
        msg = f"⭕ **Section Progress**: {count} / 3 Completed. Pending: {', '.join(pending)}. Fill all 3 sections to activate **'1. Save Maternal Details'**."
        return msg, gr.update(interactive=False)


def save_maternal_intake(
    name, age, matrima_id, sbp, dbp, pulse, temp, stage, dur,
    fhr, lie, cdil, eff, station, rom, liquor,
    ga, grav, plive, ploss, hb, urine, bsugar, plac, afi, prev_lucs, prev_comp
):
    try:
        age_f = float(age) if age is not None else 24.0
        sbp_f = float(sbp) if sbp is not None else 120.0
        dbp_f = float(dbp) if dbp is not None else 80.0
        pulse_f = float(pulse) if pulse is not None else 78.0
        temp_f = float(temp) if temp is not None else 98.4
        fhr_f = float(fhr) if fhr is not None else 140.0
        cdil_f = float(cdil) if cdil is not None else 4.0
        eff_f = float(eff) if eff is not None else 50.0
        ga_f = float(ga) if ga is not None else 39.0
        grav_i = int(grav) if grav is not None else 1
        hb_f = float(hb) if hb is not None else 11.0
        dur_f = float(dur) if dur is not None else 4.0
        plive_i = int(plive) if plive is not None else 0
        ploss_i = int(ploss) if ploss is not None else 0
        bsugar_f = float(bsugar) if bsugar is not None else 95.0
    except Exception as ex:
        return f"❌ Input parsing error: {ex}", gr.update(interactive=True), gr.update(interactive=False), "NEW"

    payload = {
        "patient_name": name or "Mother",
        "age": age_f,
        "matrima_id": matrima_id or "",
        "systolic_bp": sbp_f,
        "diastolic_bp": dbp_f,
        "pulse": pulse_f,
        "temp": temp_f,
        "stage_of_labor": stage or "Active Labour (First Stage)",
        "labor_duration": dur_f,
        "fetal_heart_rate": fhr_f,
        "presentation": lie or "Vertex/Cephalic",
        "cervical_dilatation": cdil_f,
        "effacement": eff_f,
        "station": station or "0",
        "has_rom": 1 if (rom and "Ruptured" in str(rom)) else 0,
        "liquor_color": liquor or "Clear",
        "gestational_age": ga_f,
        "gravida": grav_i,
        "parity_live": plive_i,
        "parity_loss": ploss_i,
        "hemoglobin": hb_f,
        "urine_albumin": urine or "Nil",
        "blood_sugar": bsugar_f,
        "usg_placenta": plac or "Normal",
        "usg_afi": afi or "Adequate",
        "prev_lucs": 1 if prev_lucs else 0,
        "has_prev_comp": 1 if prev_comp else 0
    }
    
    assessment = explainable_cdss.evaluate_vitals(payload)
    trigger_titles = [f"[{t['severity']}] {t['title']}" for t in assessment.get("triggers", [])]
    triggers_str = " | ".join(trigger_titles) if trigger_titles else "None"

    patient_record = {
        **payload,
        "cdss_triage_level": assessment["triage_level"],
        "cdss_color": assessment["triage_color"],
        "cdss_risk_score": assessment["risk_score"],
        "cdss_urgency": assessment["urgency"],
        "cdss_triggers": triggers_str,
    }
    study_id = db.save_new_patient(patient_record)

    status_msg = f"✅ **Patient #{study_id} Intake Recorded in Clinical Registry**! Now click **'2. AI Based CDSS for Referral'** to run continuous CDSS triage."
    btn1_upd = gr.update(value=f"✓ 1. Saved (Patient #{study_id})", interactive=False)
    btn2_upd = gr.update(interactive=True)
    return status_msg, btn1_upd, btn2_upd, study_id


def run_triage_evaluation(
    patient_name, age, sbp, dbp, pulse, hb, fhr, ga, gravida, parity_live, parity_loss,
    cervical_dil, effacement, station, lie, rom, liquor, urine_alb, blood_sugar, usg_afi, prev_lucs, prev_comp,
    stage_of_labor="Active Labour (First Stage)", labor_duration=4, usg_placenta="Normal"
):
    payload = {
        "patient_name": patient_name or "Admitted Mother",
        "age": float(age or 24),
        "systolic_bp": float(sbp or 120),
        "diastolic_bp": float(dbp or 80),
        "maternal_pulse": float(pulse or 78),
        "pulse": float(pulse or 78),
        "hemoglobin": float(hb or 11.0),
        "fetal_heart_rate": float(fhr or 140),
        "gestational_age": float(ga or 39.0),
        "gravida": int(gravida or 1),
        "parity_live": int(parity_live or 0),
        "parity_loss": int(parity_loss or 0),
        "cervical_dilatation": float(cervical_dil or 4.0),
        "effacement": float(effacement or 50),
        "station": station or "0",
        "presentation_lie": lie or "Vertex/Cephalic",
        "presentation": lie or "Vertex/Cephalic",
        "has_rom": 1 if (rom == "Yes" or (rom and "Ruptured" in str(rom))) else 0,
        "liquor_color": liquor or "Clear",
        "urine_albumin": urine_alb or "Nil",
        "blood_sugar": float(blood_sugar or 95) if isinstance(blood_sugar, (int, float)) else 95,
        "usg_placenta": usg_placenta or "Normal",
        "usg_afi": usg_afi or "Adequate",
        "stage_of_labor": stage_of_labor or "Active Labour (First Stage)",
        "labor_duration": float(labor_duration or 4),
        "prev_lucs": 1 if prev_lucs else 0,
        "has_prev_comp": 1 if prev_comp else 0,
    }

    # Evaluate using clinical AI engine
    result = explainable_cdss.evaluate_vitals(payload)
    triage = result["triage_level"]

    # 1. Format AI Decision Banner
    if triage == "RED":
        badge_color = "#dc2626"
        bg_color = "#fef2f2"
        border_color = "#fca5a5"
        icon = "🚨"
    elif triage == "YELLOW":
        badge_color = "#d97706"
        bg_color = "#fffbeb"
        border_color = "#fcd34d"
        icon = "⚠️"
    else:
        badge_color = "#15803d"
        bg_color = "#f0fdf4"
        border_color = "#86efac"
        icon = "🛡️"

    decision_banner = f"""
    <div style="background: {bg_color}; border: 2px solid {border_color}; border-left: 8px solid {badge_color}; border-radius: 10px; padding: 14px 16px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-size: 11px; font-weight: 800; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">AI Referral Recommendation</span>
            <span style="background: {badge_color}; color: white; padding: 3px 12px; border-radius: 20px; font-size: 11px; font-weight: 800;">{triage} TRIAGE</span>
        </div>
        <div style="font-size: 17px; font-weight: 900; color: {badge_color}; margin: 4px 0; display: flex; align-items: center; gap: 8px;">
            <span>{icon}</span> <span>AI DECISION: {result['ai_decision']}</span>
        </div>
        <div style="font-size: 12px; color: #334155;">
            <strong>Clinical Urgency:</strong> {result['urgency']}
        </div>
    </div>
    """

    # Pulse Alert Box
    pulse_info = result.get("pulse_highlight", {})
    if pulse_info.get("status") != "NORMAL":
        pulse_alert = f"""
        <div style="background: #fee2e2; border: 1.5px solid #f87171; color: #991b1b; padding: 10px 14px; border-radius: 8px; font-weight: 700; margin-bottom: 12px; font-size: 13px;">
            💓 <strong>MATERNAL PULSE ALERT:</strong> {pulse_info.get('alert_message')}
        </div>
        """
    else:
        pulse_alert = ""

    # 2. Formatted Risk Score & Care Destination (Zero Overflow, Full Wrapping)
    risk_score_val = result["risk_score"]
    dest_val = result["recommended_destination"]
    score_tag_text = "Physiological Status" if triage == "GREEN" else ("Moderate Vigilance" if triage == "YELLOW" else "Critical Emergency")

    summary_cards = f"""
    <div style="display: flex; flex-direction: column; gap: 10px; margin: 12px 0;">
        <div style="background: #ffffff; border: 1.5px solid #fed7aa; border-radius: 10px; padding: 12px 16px; box-shadow: 0 1px 4px rgba(234,88,12,0.05);">
            <div style="font-size: 11px; font-weight: 800; color: #ea580c; text-transform: uppercase; margin-bottom: 4px;">⏱ AI Composite Risk Score</div>
            <div style="display: flex; align-items: baseline; gap: 6px;">
                <span style="font-size: 28px; font-weight: 900; color: #0f172a;">{risk_score_val:.0f}</span>
                <span style="font-size: 16px; font-weight: 600; color: #64748b;">/ 100</span>
                <span style="background: {badge_color}; color: white; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 800; margin-left: auto;">{score_tag_text}</span>
            </div>
        </div>

        <div style="background: #ffffff; border: 1.5px solid #fed7aa; border-radius: 10px; padding: 12px 16px; box-shadow: 0 1px 4px rgba(234,88,12,0.05);">
            <div style="font-size: 11px; font-weight: 800; color: #ea580c; text-transform: uppercase; margin-bottom: 4px;">🏥 Care Destination & Facility Protocol</div>
            <div style="font-size: 15px; font-weight: 800; color: #0f172a; line-height: 1.45; word-wrap: break-word; overflow-wrap: break-word; white-space: normal;">
                {dest_val}
            </div>
        </div>
    </div>
    """

    # 3. Clinical Danger Signs & Guideline Protocols
    triggers_items = "".join([f"<li style='margin-bottom: 5px;'><strong>[{t['severity']}] {t['title']}:</strong> {t.get('action') or t.get('text')}</li>" for t in result.get("triggers", [])])
    if not triggers_items:
        triggers_items = "<li style='color: #166534;'>✅ All initial vital parameters, maternal pulse rhythm, and fetal heart rate are physiological. Safe for PLHCU delivery.</li>"

    protocols_items = "".join([f"<li style='margin-bottom: 4px;'>✓ {p}</li>" for p in result.get("stabilization_protocols", [])])

    details_html = f"""
    <div style="background: #fffaf5; border: 1px solid #fed7aa; border-radius: 10px; padding: 12px 14px; margin-top: 8px;">
        <h4 style="margin: 0 0 6px 0; font-size: 12px; color: #c2410c; text-transform: uppercase; font-weight: 800;">📋 Clinical Assessment Findings & Triggers</h4>
        <ul style="margin: 0 0 10px 0; padding-left: 18px; font-size: 12px; color: #334155; line-height: 1.4;">{triggers_items}</ul>
        
        <h4 style="margin: 8px 0 4px 0; font-size: 12px; color: #15803d; text-transform: uppercase; font-weight: 800;">🛡️ Standard Clinical Protocols (MoHFW Guidelines)</h4>
        <ul style="margin: 0; padding-left: 18px; font-size: 12px; color: #15803d; line-height: 1.4;">{protocols_items}</ul>
    </div>
    """

    # 4. Generate SHAP TreeExplainer Waterfall Plot (Card 4)
    shap_data = result.get("shap", {})
    contribs = shap_data.get("contributions", [])[:8]

    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=100)
    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#fffaf5')

    if contribs:
        y_pos = range(len(contribs))
        features = [f"{c['feature']} ({c['display_value']})" for c in contribs]
        values = [c["shap_value"] for c in contribs]
        colors = ["#dc2626" if v > 0 else "#ea580c" for v in values]

        bars = ax.barh(y_pos, values, color=colors, height=0.55, edgecolor="none")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(features, fontsize=9, color="#0f172a", fontweight="600")
        ax.invert_yaxis()
        ax.axvline(0, color="#64748b", linestyle="--", linewidth=0.9)
        ax.set_xlabel("SHAP Feature Attribution Value (ϕᵢ)", fontsize=9, fontweight="bold", color="#334155")
        ax.set_title(
            f"Model Referral Risk: {shap_data.get('prediction_prob', 0.4)*100:.1f}%  |  Base Value E[f(X)]: {shap_data.get('base_value', 0.493)*100:.1f}%",
            fontsize=10,
            fontweight="bold",
            color="#0f172a",
            pad=10
        )
        for bar in bars:
            width = bar.get_width()
            align = "left" if width >= 0 else "right"
            offset = 0.005 if width >= 0 else -0.005
            ax.text(width + offset, bar.get_y() + bar.get_height()/2, f"{width:+.3f}", va="center", ha=align, fontsize=8, color="#0f172a", fontweight="bold")
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#fed7aa')
        ax.spines['bottom'].set_color('#fed7aa')
        plt.tight_layout()
    else:
        ax.text(0.5, 0.5, "No SHAP feature contributions available", ha="center", va="center")

    combined_triage_html = decision_banner + pulse_alert + summary_cards + details_html
    return combined_triage_html, fig


# -------------------------------------------------------------
# Doctor Decision & Re-evaluation Scheduler
# -------------------------------------------------------------
def calculate_due_time(hours_option, custom_hours):
    try:
        hours = float(custom_hours) if hours_option == "Custom" else float(hours_option)
    except Exception:
        hours = 1.0
    due = datetime.now() + timedelta(hours=hours)
    return due.strftime("%H:%M (%d %b)")


def save_doctor_clinical_order(
    study_id, doctor_alignment, override_reason_cat, override_notes,
    disposition_order, reeval_hours_choice, custom_reeval_input
):
    try:
        hours = float(custom_reeval_input) if reeval_hours_choice == "Custom" else float(reeval_hours_choice)
    except Exception:
        hours = 1.0

    due_time_str = (datetime.now() + timedelta(hours=hours)).strftime("%H:%M (%d %b)")
    override_reason_final = f"{override_reason_cat}: {override_notes}" if doctor_alignment == "OVERRIDE" else ""

    # Save to database
    db.save_doctor_evaluation_order(
        study_id=study_id or "0004",
        doctor_decision=doctor_alignment,
        doctor_action=disposition_order,
        override_reason=override_reason_final,
        reeval_hours=hours if disposition_order == "REEVALUATE" else None,
        next_reeval_time=due_time_str if disposition_order == "REEVALUATE" else None,
        doctor_name="Attending Medical Officer"
    )

    return f"✅ Doctor's Order Confirmed & Signed for #{study_id}!\n• Disposition: {disposition_order}\n• AI Alignment: {doctor_alignment}\n• Scheduled Re-evaluation: {due_time_str if disposition_order == 'REEVALUATE' else 'N/A'}\n• Audit Record Logged to District Registry."


# -------------------------------------------------------------
# Generate Official Emergency Referral Transfer Slip
# -------------------------------------------------------------
def generate_referral_slip(study_id, destination_hospital, transport_mode, reason, iv_line, mgso4, oxygen):
    slip_md = f"""
# GOVERNMENT OF WEST BENGAL • DEPARTMENT OF HEALTH & FAMILY WELFARE
## MATRISURAKSHA EMERGENCY OBSTETRIC REFERRAL DOSSIER
**Dakshin Dinajpur District AI-Assisted Clinical Transfer Slip • মাতৃসুরক্ষা**

---

### 1. Referring Facility & Patient Demographics
- **Patient Study ID:** `#{study_id}`
- **Referring Center:** Harirampur Rural Hospital (PLHCU)
- **Transfer Timestamp:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
- **Designated Referral Center:** **{destination_hospital}**
- **Mode of Transport:** **{transport_mode}**

### 2. Clinical Reason for Inter-Hospital Transfer
> **Primary Danger Signs & Indications:**  
> {reason}

### 3. Mandatory Pre-Departure Stabilization Checklist (MoHFW Verified)
- [{'X' if iv_line else ' '}] **IV Cannula (16-18G) placed in situ** with Ringer Lactate continuous infusion.
- [{'X' if mgso4 else ' '}] **MgSO4 Loading Dose administered** (4g IV + 10g IM) for severe hypertension/pre-eclampsia.
- [{'X' if oxygen else ' '}] **Left lateral maternal positioning maintained** with high-flow oxygen.
- [X] **Higher Facility Notified** via telephone prior to ambulance departure.

---
*Signed by Attending Medical Officer & On-Duty Staff Nurse*  
*Government of West Bengal Health Research Grant • PI: Dr. Dilip Kumar Biswas (Dy. CMOH III)*
    """
    return slip_md


# -------------------------------------------------------------
# Secure Registry & Analytics (Password Protected)
# -------------------------------------------------------------
def unlock_registry(username, password):
    user = db.verify_user(username, password)
    if not user:
        return "❌ Access Denied: Invalid Healthcare User ID or Password.", None
    
    patients = db.get_all_patients()
    df = pd.DataFrame(patients)
    cols = ["study_id", "patient_name", "age", "gestational_age", "systolic_bp", "diastolic_bp", "hemoglobin", "cdss_triage_level", "referral_status", "referral_facility"]
    df_filtered = df[[c for c in cols if c in df.columns]]
    
    total = len(df)
    referred = sum(1 for p in patients if p.get("is_referred") == 1 or p.get("referral_status") == "REFERRED")
    ref_rate = (referred / total * 100) if total > 0 else 0.0

    stats_msg = f"✅ Authenticated: {user['full_name']} ({user['role']}) | Total Registered: {total} | Transfers: {referred} ({ref_rate:.1f}%)"
    return stats_msg, df_filtered


# -------------------------------------------------------------
# GRADIO APPLICATION UI (4-CARD 2x2 GRID • WHITE & ORANGE THEME)
# -------------------------------------------------------------
custom_orange_css = """
body, .gradio-container {
    background-color: #fafaf9 !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}

/* Header Box */
.header-box {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    color: white;
    padding: 16px 22px;
    border-radius: 12px;
    margin-bottom: 20px;
    border-bottom: 3.5px solid #ea580c;
    box-shadow: 0 4px 14px rgba(0,0,0,0.12);
}
.header-box h1 { margin: 0; font-size: 22px; font-weight: 800; }
.header-box h1 span { color: #fdba74; font-size: 17px; }
.header-box p { margin: 4px 0 0 0; color: #cbd5e1; font-size: 13px; }

/* 4-Card Clinical Grid Styling */
.card-header-bar {
    background: #fffaf5;
    border: 1.5px solid #fed7aa;
    border-top: 4px solid #ea580c;
    border-radius: 10px 10px 0 0;
    padding: 10px 14px;
    font-weight: 800;
    font-size: 14px;
    color: #0f172a;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.clinical-card-container {
    background: #ffffff;
    border: 1.5px solid #fed7aa;
    border-top: none;
    border-radius: 0 0 10px 10px;
    padding: 14px;
    box-shadow: 0 4px 12px rgba(234, 88, 12, 0.05);
    margin-bottom: 16px;
}

/* Primary Button in Orange */
button.primary-orange-btn {
    background: linear-gradient(135deg, #ea580c 0%, #f97316 100%) !important;
    color: white !important;
    font-weight: 800 !important;
    border: none !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 8px rgba(234, 88, 12, 0.3) !important;
}

/* Institutional Footer */
.grant-footer-box {
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-top: 3px solid #ea580c;
    border-radius: 10px;
    padding: 16px 20px;
    margin-top: 24px;
    font-size: 13px;
    color: #475569;
}
"""

with gr.Blocks(title="MatriSuraksha - 4-Card 2x2 CDSS") as demo:

    # Header Lockup
    gr.HTML("""
    <div class="header-box">
        <h1>MatriSuraksha <span>মাতৃসুরক্ষা</span> &bull; Continuous AI Maternity CDSS</h1>
        <p>Dakshin Dinajpur District AI-Assisted Clinical Referral Decision Support System &bull; Govt. of West Bengal</p>
    </div>
    """)

    # =============================================================
    # ROW 1 (TOP): CARD 1 & CARD 2
    # =============================================================
    with gr.Row():
        # ---------------------------------------------------------
        # ROW 1, COL 1: CARD 1 - Patient Vitals & Clinical Observation Entry
        # ---------------------------------------------------------
        with gr.Column(scale=1):
            gr.HTML("""
            <div class="card-header-bar">
                <span>📋 Card 1: Patient Vitals & Clinical Observation Entry</span>
                <span style="background: #ffedd5; color: #c2410c; padding: 2px 8px; border-radius: 12px; font-size: 11px;">Intake Workspace</span>
            </div>
            """)
            with gr.Group(elem_classes="clinical-card-container"):
                # Dynamic Section Completion Progress Header
                section_status_md = gr.Markdown("⭕ **Section Progress: 0 / 3 Complete**. Fill Section 1, 2, and 3 below to activate **'1. Save Maternal Details'**.")

                with gr.Accordion("1️⃣ Section 1: Demographics & Acute Maternal Vitals", open=True):
                    patient_name = gr.Textbox(label="Mother's Full Name *", placeholder="e.g. Ananya Das", value="")
                    with gr.Row():
                        age = gr.Number(label="Age (Years) *", placeholder="e.g. 24", value=None)
                        matrima_id = gr.Textbox(label="Matrima / ANC ID", placeholder="e.g. 1904523891", value="")
                    with gr.Row():
                        sbp = gr.Number(label="Systolic BP (mmHg) *", placeholder="e.g. 120", value=None)
                        dbp = gr.Number(label="Diastolic BP (mmHg) *", placeholder="e.g. 80", value=None)
                        pulse = gr.Number(label="Maternal Pulse (bpm) *", placeholder="e.g. 78", value=None)
                    with gr.Row():
                        temp = gr.Number(label="Temperature (°F) *", placeholder="e.g. 98.4", value=None)
                        stage_of_labor = gr.Dropdown(
                            ["Active Labour (First Stage)", "Second Stage (Full Dilatation / Crowning)", "Latent Phase", "Third Stage / Postpartum"],
                            label="Stage of Labour *", value=None
                        )
                        labor_duration = gr.Number(label="Duration of Labour (hrs)", placeholder="e.g. 4", value=None)

                with gr.Accordion("2️⃣ Section 2: Vaginal Examination & Fetus", open=False):
                    with gr.Row():
                        fhr = gr.Number(label="Fetal Heart Rate (bpm) *", placeholder="e.g. 140", value=None)
                        lie = gr.Dropdown(
                            ["Vertex / Cephalic (Normal)", "Breech (Frank / Complete)", "Transverse / Shoulder Lie", "Brow / Face Presentation"],
                            label="Presentation / Lie *", value=None
                        )
                    with gr.Row():
                        cervical_dil = gr.Number(label="Cervical Dilat. (cm) *", placeholder="e.g. 4.0", value=None)
                        effacement = gr.Number(label="Cervical Effacement (%) *", placeholder="e.g. 60", value=None)
                    with gr.Row():
                        station = gr.Dropdown(["High (-3)", "-2", "-1", "Engaged (0)", "+1", "+2 (Deep pelvic)", "Crowning (+3)"], label="Station of Head *", value=None)
                        rom = gr.Dropdown(["Intact Membranes", "Ruptured Membranes (Active PROM / Dribbling)"], label="Membrane Status *", value=None)
                    liquor = gr.Dropdown(["Clear / Physiological", "Thin Meconium (Grade 1)", "Thick Meconium (Grade 2/3 - Critical)", "Blood-Stained"], label="Liquor / Amniotic Color *", value=None)

                with gr.Accordion("3️⃣ Section 3: Antenatal Profile & Diagnostics", open=False):
                    with gr.Row():
                        ga = gr.Number(label="Gestational Age (weeks) *", placeholder="e.g. 39.0", value=None)
                        gravida = gr.Number(label="Gravida (G) *", placeholder="e.g. 1", value=None)
                        p_live = gr.Number(label="Parity Live (P)", placeholder="e.g. 0", value=None)
                        p_loss = gr.Number(label="Parity Loss (L)", placeholder="e.g. 0", value=None)
                    with gr.Row():
                        hb = gr.Number(label="Hemoglobin (g/dL) *", placeholder="e.g. 11.2", value=None)
                        urine_alb = gr.Dropdown(["Nil / Negative", "Trace", "+", "++ (Pre-eclampsia Alert)", "+++ (Severe Pre-eclampsia)"], label="Urine Albumin *", value=None)
                        blood_sugar = gr.Number(label="Blood Sugar (mg/dL)", placeholder="e.g. 95", value=None)
                    with gr.Row():
                        usg_placenta = gr.Dropdown(["Normal Fundal/Anterior/Posterior", "Low-lying Placenta", "Placenta Previa (Critical Hemorrhage)"], label="USG Placenta Position *", value=None)
                        usg_afi = gr.Dropdown(["Adequate AFI", "Oligohydramnios (Reduced Fluid)", "Polyhydramnios (Excess Fluid)"], label="USG AFI (Liquor Volume) *", value=None)
                    with gr.Row():
                        prev_lucs = gr.Checkbox(label="Previous Caesarean Section (LUCS Scar)", value=False)
                        prev_comp = gr.Checkbox(label="Prior Stillbirth / Miscarriages", value=False)

                # Two-Stage Sequential Action Buttons
                with gr.Row():
                    btn_save_maternal = gr.Button("💾 1. Save Maternal Details", interactive=False, elem_classes="primary-orange-btn")
                    btn_run_cdss = gr.Button("⚡ 2. AI Based CDSS for Referral", interactive=False, elem_classes="primary-orange-btn")
                
                active_study_id = gr.Textbox(value="NEW-ADMISSION", visible=False)

        # ---------------------------------------------------------
        # ROW 1, COL 2: CARD 2 - TRIAGE Continuous Clinical Decision Support
        # ---------------------------------------------------------
        with gr.Column(scale=1):
            gr.HTML("""
            <div class="card-header-bar">
                <span>🛡️ Card 2: TRIAGE Continuous Clinical Decision Support</span>
                <span style="background: #ffedd5; color: #c2410c; padding: 2px 8px; border-radius: 12px; font-size: 11px;">Real-Time AI Decision</span>
            </div>
            """)
            with gr.Group(elem_classes="clinical-card-container"):
                triage_output_html = gr.HTML(value=initial_triage_html)

    # =============================================================
    # ROW 2 (BOTTOM): CARD 3 & CARD 4
    # =============================================================
    with gr.Row():
        # ---------------------------------------------------------
        # ROW 2, COL 1: CARD 3 - Attending Doctor Clinical Evaluation & Final Disposition
        # ---------------------------------------------------------
        with gr.Column(scale=1):
            gr.HTML("""
            <div class="card-header-bar">
                <span>👨‍⚕️ Card 3: Attending Doctor Clinical Evaluation & Final Disposition</span>
                <span style="background: #ffedd5; color: #c2410c; padding: 2px 8px; border-radius: 12px; font-size: 11px;">Mandatory Clinician Sign-Off</span>
            </div>
            """)
            with gr.Group(elem_classes="clinical-card-container"):
                doctor_alignment = gr.Radio(
                    choices=[("Agree with AI Triage Decision", "AGREE"), ("Override / Contradict AI Decision", "OVERRIDE")],
                    value="AGREE",
                    label="1. Clinician AI Alignment"
                )

                override_reason_cat = gr.Dropdown(
                    [
                        "Rapid Labor Progression (Crowning, unsafe to transfer in ambulance)",
                        "Maternal Vitals Stabilized after initial medical therapy",
                        "Clinical internal exam confirms adequate pelvis & descent",
                        "Patient / Family refused inter-hospital referral despite counseling",
                        "Bedside clinical emergency demands immediate transfer (AI too conservative)",
                        "Logistical emergency (102 Ambulance delay / Road block)",
                        "Other Specialist Clinical Judgment"
                    ],
                    value="Rapid Labor Progression (Crowning, unsafe to transfer in ambulance)",
                    label="Primary Clinical Reason for Contradicting AI"
                )
                override_notes = gr.Textbox(placeholder="Detail clinical rationale for audit trail and CMOH district review...", label="Doctor's Rationale Notes")

                gr.Markdown("**2. Doctor's Final Management Order & Care Plan:**")
                disposition_order = gr.Radio(
                    choices=[
                        ("Re-evaluate after Set Hours", "REEVALUATE"),
                        ("Decision to Refer to Higher Centre (SDH / DH)", "REFER"),
                        ("Proceed with Normal Delivery at PLHCU", "ROUTINE")
                    ],
                    value="REEVALUATE",
                    label="Clinical Disposition Choice"
                )

                with gr.Row():
                    reeval_hours_choice = gr.Dropdown(
                        choices=[("30 Minutes (High Vigilance)", "0.5"), ("1 Hour (Active Phase)", "1.0"), ("2 Hours (Latent Phase)", "2.0"), ("4 Hours (Routine Partograph)", "4.0"), ("Custom Hours...", "Custom")],
                        value="1.0",
                        label="Schedule Re-evaluation In"
                    )
                    custom_reeval_input = gr.Number(value=1.0, label="Custom Hours (if selected)")
                    due_time_display = gr.Textbox(label="Calculated Next Re-evaluation Due Timestamp", value=calculate_due_time("1.0", 1.0), interactive=False)

                reeval_hours_choice.change(fn=calculate_due_time, inputs=[reeval_hours_choice, custom_reeval_input], outputs=due_time_display)
                custom_reeval_input.change(fn=calculate_due_time, inputs=[reeval_hours_choice, custom_reeval_input], outputs=due_time_display)

                btn_save_order = gr.Button("🖋️ Sign & Finalize Attending Doctor Clinical Order", variant="primary", elem_classes="primary-orange-btn")
                order_status_msg = gr.Textbox(label="Doctor Order Audit Confirmation", interactive=False)
                btn_save_order.click(
                    fn=save_doctor_clinical_order,
                    inputs=[active_study_id, doctor_alignment, override_reason_cat, override_notes, disposition_order, reeval_hours_choice, custom_reeval_input],
                    outputs=order_status_msg
                )

        # ---------------------------------------------------------
        # ROW 2, COL 2: CARD 4 - SHAP Explainable AI Waterfall (TreeExplainer)
        # ---------------------------------------------------------
        with gr.Column(scale=1):
            gr.HTML("""
            <div class="card-header-bar">
                <span>🧠 Card 4: SHAP Explainable AI Waterfall (TreeExplainer)</span>
                <span style="background: #ffedd5; color: #c2410c; padding: 2px 8px; border-radius: 12px; font-size: 11px;">Feature Attribution (ϕᵢ)</span>
            </div>
            """)
            with gr.Group(elem_classes="clinical-card-container"):
                gr.Markdown("*Exact Shapley values (ϕᵢ) for individual patient parameters relative to Base Expected Value E[f(X)] = 0.493:*")
                shap_plot_output = gr.Plot(value=create_empty_shap_figure(), label="SHAP Feature Attribution Waterfall")

    # Wire Real-Time Completion Checking across inputs
    key_inputs = [
        patient_name, age, sbp, dbp, pulse, temp, stage_of_labor,
        fhr, lie, cervical_dil, effacement, station, rom, liquor,
        ga, gravida, hb, urine_alb, usg_placenta, usg_afi
    ]
    for inp in key_inputs:
        inp.change(
            fn=check_sections_readiness,
            inputs=key_inputs,
            outputs=[section_status_md, btn_save_maternal]
        )

    # Save Maternal Details handler
    save_all_inputs = [
        patient_name, age, matrima_id, sbp, dbp, pulse, temp, stage_of_labor, labor_duration,
        fhr, lie, cervical_dil, effacement, station, rom, liquor,
        ga, gravida, p_live, p_loss, hb, urine_alb, blood_sugar, usg_placenta, usg_afi, prev_lucs, prev_comp
    ]
    btn_save_maternal.click(
        fn=save_maternal_intake,
        inputs=save_all_inputs,
        outputs=[section_status_md, btn_save_maternal, btn_run_cdss, active_study_id]
    )

    # Run AI CDSS handler
    def run_ai_eval_bridge(
        name, age, matrima_id, sbp, dbp, pulse, temp, stage, dur,
        fhr, lie, cdil, eff, station, rom, liquor,
        ga, grav, plive, ploss, hb, urine, bsugar, plac, afi, prev_lucs, prev_comp,
        study_id
    ):
        t_html, s_fig = run_triage_evaluation(
            patient_name=name,
            age=age,
            sbp=sbp,
            dbp=dbp,
            pulse=pulse,
            hb=hb,
            fhr=fhr,
            ga=ga,
            gravida=grav,
            parity_live=plive,
            parity_loss=ploss,
            cervical_dil=cdil,
            effacement=eff,
            station=station,
            lie=lie,
            rom=rom,
            liquor=liquor,
            urine_alb=urine,
            blood_sugar=bsugar,
            usg_afi=afi,
            prev_lucs=prev_lucs,
            prev_comp=prev_comp,
            stage_of_labor=stage,
            labor_duration=dur,
            usg_placenta=plac
        )
        return t_html, s_fig

    btn_run_cdss.click(
        fn=run_ai_eval_bridge,
        inputs=save_all_inputs + [active_study_id],
        outputs=[triage_output_html, shap_plot_output]
    )

    # =============================================================
    # SECONDARY ACCORDIONS: TRANSFER DOSSIER, FEEDBACK & PROTECTED MIS
    # =============================================================
    with gr.Accordion("📄 Digital Emergency Referral Transfer Voucher", open=False):
        with gr.Row():
            ref_study_id = gr.Textbox(label="Patient Study ID", value="0004")
            ref_dest = gr.Dropdown(["Gangarampur Sub-Divisional Hospital (SDH)", "Balurghat District Hospital (DH)", "Malda Medical College & Hospital"], value="Gangarampur Sub-Divisional Hospital (SDH)", label="Designated Higher Referral Center")
            ref_trans = gr.Dropdown(["102 Government Ambulance (Dialed)", "108 Emergency ALS Ambulance", "Private / Hired Transport"], value="102 Government Ambulance (Dialed)", label="Mode of Transport")

        ref_reason = gr.Textbox(label="Primary Danger Signs & Indications for Transfer", value="Severe pre-eclampsia (BP 165/105 mmHg), Oligohydramnios (AFI < 5cm)")
        
        with gr.Row():
            chk_iv = gr.Checkbox(label="IV Cannula (16-18G) placed with Ringer Lactate drip", value=True)
            chk_mg = gr.Checkbox(label="MgSO4 Loading Dose Administered (if SBP >= 160 or DBP >= 110)", value=True)
            chk_o2 = gr.Checkbox(label="Left lateral positioning & maternal oxygen given", value=True)

        btn_gen_slip = gr.Button("🖨️ Generate Official Government of West Bengal Referral Slip", variant="primary", elem_classes="primary-orange-btn")
        slip_output = gr.Markdown()

        btn_gen_slip.click(
            fn=generate_referral_slip,
            inputs=[ref_study_id, ref_dest, ref_trans, ref_reason, chk_iv, chk_mg, chk_o2],
            outputs=slip_output
        )

    with gr.Accordion("🔄 Closed-Loop Referral Feedback (Secondary Hospital)", open=False):
        with gr.Row():
            fb_study_id = gr.Textbox(label="Patient Study ID", value="0004")
            fb_hosp = gr.Dropdown(["Gangarampur SDH", "Balurghat DH", "Malda Medical College"], value="Gangarampur SDH", label="Reporting Referral Hospital")
            fb_doctor = gr.Textbox(label="Attending Specialist Obstetrician", value="Dr. S. Mukherjee, MD (OBGYN)")

        with gr.Row():
            fb_arrival = gr.Dropdown(["Stable", "Critical / In Shock", "Active Second Stage", "Expired in Transit"], value="Stable", label="Maternal Condition on Arrival")
            fb_stab = gr.Dropdown(["Adequate & Exemplary", "Partial / Incomplete", "No Pre-Departure Care"], value="Adequate & Exemplary", label="Pre-Departure Stabilization Quality")
            fb_appr = gr.Dropdown(["Appropriate & Timely", "Delayed Referral", "Unnecessary Transfer"], value="Appropriate & Timely", label="Referral Appropriateness")

        with gr.Row():
            fb_mat_out = gr.Dropdown(["Delivered safely via Normal Delivery", "Delivered via Emergency Caesarean Section", "Still undergoing active management", "Maternal ICU admission"], value="Delivered via Emergency Caesarean Section", label="Maternal Outcome")
            fb_neo_out = gr.Dropdown(["Healthy Baby (Apgar >= 8)", "Mild Asphyxia / Resuscitated", "SNCU Admission Required", "Stillbirth / Fresh Loss"], value="Healthy Baby (Apgar >= 8)", label="Neonatal Outcome")

        fb_notes = gr.Textbox(label="Feedback Notes to Referring PHC Nurse/Doctor", value="Timely referral and MgSO4 loading dose prevented intrapartum eclampsia convulsions. Mother and baby healthy.")
        btn_submit_fb = gr.Button("💾 Submit Closed-Loop Feedback to District Health System", variant="primary", elem_classes="primary-orange-btn")
        fb_confirm = gr.Textbox(label="Submission Status", interactive=False)

        def submit_fb_wrapper(sid, hosp, doc, arr, stab, appr, mout, nout, notes):
            db.submit_referral_feedback({
                "study_id": sid,
                "referral_facility": hosp,
                "doctor_name": doc,
                "arrival_condition": arr,
                "stabilization_quality": stab,
                "referral_appropriateness": appr,
                "maternal_outcome": mout,
                "neonatal_outcome": nout,
                "feedback_notes": notes,
                "delivery_mode": mout,
                "baby_weight": 2.85,
                "baby_status": "Alive",
                "sncu_referred": "No"
            })
            return f"✅ Closed-Loop Feedback recorded successfully for #{sid} at {hosp}!"

        btn_submit_fb.click(
            fn=submit_fb_wrapper,
            inputs=[fb_study_id, fb_hosp, fb_doctor, fb_arrival, fb_stab, fb_appr, fb_mat_out, fb_neo_out, fb_notes],
            outputs=fb_confirm
        )

    with gr.Accordion("🔒 Secure Facility Maternity Registry (MIS - Password Protected)", open=False):
        gr.Markdown("*Mandatory User ID & Security Password required under West Bengal Public Health Clinical Data Protection Protocols.*")

        with gr.Row():
            auth_user = gr.Textbox(label="Healthcare User ID (e.g. dr.biswas or nurse.anm)", value="dr.biswas")
            auth_pass = gr.Textbox(label="Security Password", type="password", value="matri123")
            btn_unlock = gr.Button("🔓 Authenticate & Unlock Registry", variant="primary", elem_classes="primary-orange-btn")

        auth_status = gr.Markdown()
        registry_table = gr.DataFrame(label="Patient Records Archive", interactive=False)

        btn_unlock.click(
            fn=unlock_registry,
            inputs=[auth_user, auth_pass],
            outputs=[auth_status, registry_table]
        )

    # Institutional Grant Footer
    gr.HTML("""
    <div class="grant-footer-box">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
            <strong style="font-size: 14px; color: #0f172a;">🏆 Research Project Grant Acknowledgment:</strong>
        </div>
        <p style="margin: 0 0 10px 0; line-height: 1.5;">
            This Research Project Received the financial Grant from <strong>Institute of Health and Family Welfare (IHFW), Department of Health and Family Welfare, Government of West Bengal</strong>.
        </p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; margin-top: 10px;">
            <div style="background: white; padding: 10px 14px; border-radius: 8px; border: 1.5px solid #fed7aa;">
                <span style="font-size: 11px; font-weight: 800; color: #ea580c; text-transform: uppercase;">Principal Investigator (PI)</span>
                <div style="font-weight: 800; color: #0f172a;">Dr. Dilip Kumar Biswas</div>
                <div style="font-size: 12px; color: #64748b;">Deputy CMOH – III, Dakshin Dinajpur</div>
            </div>
            <div style="background: white; padding: 10px 14px; border-radius: 8px; border: 1.5px solid #fed7aa;">
                <span style="font-size: 11px; font-weight: 800; color: #ea580c; text-transform: uppercase;">Co-Principal Investigator</span>
                <div style="font-weight: 800; color: #0f172a;">Dr. Arkaprabha Sau</div>
                <div style="font-size: 12px; color: #64748b;">Public Health Specialist & Chief AI ML Scientist</div>
            </div>
            <div style="background: white; padding: 10px 14px; border-radius: 8px; border: 1.5px solid #fed7aa;">
                <span style="font-size: 11px; font-weight: 800; color: #ea580c; text-transform: uppercase;">Co-Principal Investigator</span>
                <div style="font-weight: 800; color: #0f172a;">Dr. Ishita Bhakta</div>
                <div style="font-size: 12px; color: #64748b;">Assistant Professor, Department of IT, Techno Main Salt Lake</div>
            </div>
        </div>
    </div>
    """)


if __name__ == "__main__":
    port = int(os.environ.get("GRADIO_SERVER_PORT", 7860))
    print(f"Starting MatriSuraksha Gradio 2x2 Grid on http://127.0.0.1:{port}")
    demo.launch(server_name="127.0.0.1", server_port=port, share=False, theme=gr.themes.Soft(primary_hue="orange", secondary_hue="amber", neutral_hue="slate"), css=custom_orange_css)
