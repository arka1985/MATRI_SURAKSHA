"""
MatriSuraksha - Role-Based Web Application Server & Continuous CDSS
Supports:
1. Module 1: First Admitted Hospital (PLHCU / PHC / Rural Hospital)
2. Module 2: Referred Hospital (SDH / DH) & Closed-Loop Clinical Feedback
3. Module 3: Chief Medical Officer of Health (CMOH) District Executive Dashboard
4. Security Layer: User ID & Password authentication for protected patient data
5. Continuous CDSS Re-Assessment Timeline & Doctor Override Tracking
6. Browser Extension (.zip) Download
"""

import os
import sys
import io
import csv
import zipfile
from functools import wraps
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
    send_file,
    Response,
)

# Add src and app to system path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
sys.path.insert(0, os.path.join(BASE_DIR, "app"))

from explainable_cdss import ExplainableCDSS
import db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "matrisuraksha-secret-wb-health-2026-auth")

explainable_cdss = ExplainableCDSS()

# Ensure database is initialized
db.init_db()


# -------------------------------------------------------------
# Context Processor & Auth Decorator
# -------------------------------------------------------------
@app.context_processor
def inject_user():
    return {
        "current_user": session.get("user")
    }


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


# -------------------------------------------------------------
# Security & Authentication Routes
# -------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()
        user = db.verify_user(username, password)
        if user:
            session["user"] = {
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user["role"],
                "facility": user["facility"]
            }
            next_page = request.form.get("next") or request.args.get("next") or url_for("plhcu_view")
            return redirect(next_page)
        else:
            error = "Invalid healthcare credentials. Please check your User ID and password."
            
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("plhcu_view"))


# -------------------------------------------------------------
# Module 1: First Admitted Hospital (PLHCU)
# -------------------------------------------------------------
@app.route("/")
def index():
    return redirect(url_for("plhcu_view"))


@app.route("/plhcu")
def plhcu_view():
    facility = request.args.get("facility", "ALL")
    patients = db.get_all_patients(facility=facility)
    
    total = len(patients)
    red_count = sum(1 for p in patients if p["cdss_triage_level"] == "RED")
    yellow_count = sum(1 for p in patients if p["cdss_triage_level"] == "YELLOW")
    green_count = sum(1 for p in patients if p["cdss_triage_level"] == "GREEN")
    
    stats = {
        "total": total,
        "red": red_count,
        "yellow": yellow_count,
        "green": green_count,
    }

    primary_units = db.get_facilities(facility_type="PLHCU")
    referral_centers = db.get_facilities(facility_type="REFERRAL_CENTER")
    
    return render_template(
        "plhcu.html",
        active_module="plhcu",
        selected_facility=facility,
        patients=patients,
        stats=stats,
        primary_units=primary_units,
        referral_centers=referral_centers,
    )


# -------------------------------------------------------------
# Protected Individual Patient Detail & Continuous CDSS
# -------------------------------------------------------------
@app.route("/patient/<study_id>")
@login_required
def patient_detail_view(study_id):
    patient = db.get_patient_by_id(study_id)
    if not patient:
        return "Patient not found in district registry", 404
        
    timeline = db.get_patient_timeline(study_id)
    feedbacks = db.get_feedback_for_patient(study_id)
    
    return render_template(
        "patient_detail.html",
        patient=patient,
        timeline=timeline,
        feedbacks=feedbacks,
    )


@app.route("/patient/<study_id>/reassess", methods=["POST"])
@login_required
def submit_patient_reassessment(study_id):
    patient = db.get_patient_by_id(study_id)
    if not patient:
        return "Patient not found", 404
        
    vitals = {
        "systolic_bp": float(request.form.get("systolic_bp") or 120),
        "diastolic_bp": float(request.form.get("diastolic_bp") or 80),
        "pulse": float(request.form.get("pulse") or 80),
        "hemoglobin": float(request.form.get("hemoglobin") or 10.5),
        "fetal_heart_rate": float(request.form.get("fetal_heart_rate") or 140),
        "gestational_age": float(request.form.get("gestational_age") or 39.0),
        "has_rom": int(request.form.get("has_rom") or 0),
        "cervical_dilatation": float(request.form.get("cervical_dilatation") or 0),
        "stage_of_labor": request.form.get("stage_of_labor", "Active Labour"),
    }
    
    # Run explainable CDSS
    ai_eval = explainable_cdss.evaluate_vitals(vitals)
    
    doctor_decision = request.form.get("doctor_decision", "AGREE")
    doctor_action = request.form.get("doctor_action", "ROUTINE")
    override_reason = request.form.get("override_reason_category", "")
    override_notes = request.form.get("override_notes", "").strip()
    if override_notes:
        override_reason += f" — Notes: {override_notes}"
        
    doctor_name = session.get("user", {}).get("full_name", "Attending Medical Officer")
    
    db.record_triage_assessment(
        study_id=study_id,
        vitals=vitals,
        ai_eval=ai_eval,
        doctor_decision=doctor_decision,
        doctor_action=doctor_action,
        override_reason=override_reason if doctor_decision == "OVERRIDE" else "",
        doctor_name=doctor_name
    )
    
    return redirect(url_for("patient_detail_view", study_id=study_id))


# -------------------------------------------------------------
# Module 2: Referred Hospital (Secondary / Tertiary)
# -------------------------------------------------------------
@app.route("/referral")
def referral_view():
    center = request.args.get("center", "ALL")
    all_patients = db.get_all_patients()
    
    incoming = []
    for p in all_patients:
        if p.get("is_referred") == 1 and p.get("referral_status") == "REFERRED":
            if center == "ALL" or p.get("referral_facility") == center:
                incoming.append(p)
                
    feedbacks = db.get_all_feedbacks()
    if center != "ALL":
        feedbacks = [fb for fb in feedbacks if fb.get("referral_facility") == center]

    # Calculate dynamic Stabilization Quality based on audited feedbacks (true 0 baseline)
    if len(feedbacks) > 0:
        adequate_count = sum(
            1 for fb in feedbacks
            if any(term in str(fb.get("stabilization_quality", "")).lower() for term in ["adequate", "excellent"])
        )
        stabilization_rate = round((adequate_count / len(feedbacks)) * 100, 1)
    else:
        stabilization_rate = 0.0

    # Calculate dynamic Feeder PHC Network from admitted patients & registered PLHCUs
    feeder_units_set = set(p.get("facility_name") for p in all_patients if p.get("facility_name"))
    plhcu_facilities = [f["facility_name"] for f in db.get_facilities(facility_type="PLHCU")]
    all_feeder_units = sorted(list(feeder_units_set.union(plhcu_facilities)))
    feeder_count = len(all_feeder_units)
    feeder_units_list = ", ".join(all_feeder_units) if all_feeder_units else "Awaiting feeder unit admissions"

    referral_centers = db.get_facilities(facility_type="REFERRAL_CENTER")

    return render_template(
        "referral.html",
        active_module="referral",
        selected_center=center,
        incoming_patients=incoming,
        feedbacks=feedbacks,
        stabilization_rate=stabilization_rate,
        feeder_count=feeder_count,
        feeder_units_list=feeder_units_list,
        referral_centers=referral_centers,
    )


# -------------------------------------------------------------
# Module 3: CMOH District Executive Dashboard
# -------------------------------------------------------------
@app.route("/cmoh")
def cmoh_view():
    analytics = db.get_cmoh_district_analytics()
    return render_template(
        "cmoh.html",
        active_module="cmoh",
        analytics=analytics,
    )


# -------------------------------------------------------------
# REST APIs for Real-Time CDSS & Interactions
# -------------------------------------------------------------
@app.route("/api/cdss/evaluate", methods=["POST"])
def api_evaluate_cdss():
    data = request.get_json() or {}
    assessment = explainable_cdss.evaluate_vitals(data)
    return jsonify(assessment)


@app.route("/api/patient/admit", methods=["POST"])
def api_admit_patient():
    data = request.get_json() or {}
    
    # Calculate explainable CDSS
    assessment = explainable_cdss.evaluate_vitals(data)
    
    trigger_titles = [f"[{t['severity']}] {t['title']}" for t in assessment.get("triggers", [])]
    triggers_str = " | ".join(trigger_titles) if trigger_titles else "None"
    
    patient_record = {
        **data,
        "cdss_triage_level": assessment["triage_level"],
        "cdss_color": assessment["triage_color"],
        "cdss_risk_score": assessment["risk_score"],
        "cdss_urgency": assessment["urgency"],
        "cdss_triggers": triggers_str,
    }
    
    study_id = db.save_new_patient(patient_record)
    
    # Record initial baseline assessment in timeline
    db.record_triage_assessment(
        study_id=study_id,
        vitals=data,
        ai_eval=assessment,
        doctor_decision="AGREE",
        doctor_action="ADMITTED",
        override_reason="",
        doctor_name=session.get("user", {}).get("full_name", "Intake Healthcare Staff")
    )
    
    return jsonify({
        "success": True,
        "study_id": study_id,
        "triage_level": assessment["triage_level"],
        "ai_decision": assessment["ai_decision"],
        "referral_recommended": assessment["referral_recommended"],
    })


@app.route("/api/patient/refer", methods=["POST"])
def api_refer_patient():
    data = request.get_json() or {}
    study_id = data.get("study_id")
    facility = (data.get("referral_facility") or "").strip()
    if not facility or facility in ["__ADD_NEW__", "None"]:
        facility = "Designated Referral Hospital"
    reason = data.get("reason", "Intrapartum danger signs")
    
    if not study_id:
        return jsonify({"success": False, "error": "Missing study_id"}), 400
        
    db.dispatch_referral(study_id, facility, reason, "Emergency")
    return jsonify({"success": True, "study_id": study_id, "referral_facility": facility})


@app.route("/api/doctor/evaluation", methods=["POST"])
def api_save_doctor_evaluation():
    data = request.get_json() or {}
    study_id = data.get("study_id")
    if not study_id:
        return jsonify({"success": False, "error": "Missing study_id"}), 400
        
    doctor_decision = data.get("doctor_decision", "AGREE")
    doctor_action = data.get("doctor_action", "ROUTINE")
    override_reason = data.get("override_reason", "")
    reeval_hours = data.get("reeval_hours")
    next_reeval_time = data.get("next_reeval_time")
    doctor_name = session.get("user", {}).get("full_name", "Attending Medical Officer")
    
    db.save_doctor_evaluation_order(
        study_id=study_id,
        doctor_decision=doctor_decision,
        doctor_action=doctor_action,
        override_reason=override_reason,
        reeval_hours=reeval_hours,
        next_reeval_time=next_reeval_time,
        doctor_name=doctor_name
    )
    
    return jsonify({
        "success": True,
        "study_id": study_id,
        "doctor_action": doctor_action,
        "next_reeval_time": next_reeval_time
    })


@app.route("/api/referral/feedback", methods=["POST"])
def api_submit_feedback():
    data = request.get_json() or {}
    study_id = data.get("study_id")
    
    if not study_id:
        return jsonify({"success": False, "error": "Missing study_id"}), 400
        
    db.submit_referral_feedback(data)
    return jsonify({"success": True, "study_id": study_id})


@app.route("/api/export/csv")
def api_export_csv():
    patients = db.get_all_patients()
    if not patients:
        return "No data available", 404
        
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(patients[0].keys()))
    writer.writeheader()
    writer.writerows(patients)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=matrisuraksha_district_registry.csv"}
    )


# -------------------------------------------------------------
# Browser Extension Download Route
# -------------------------------------------------------------
@app.route("/download/extension.zip")
def download_extension():
    ext_dir = os.path.join(BASE_DIR, "extension")
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ext_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, ext_dir)
                zf.write(file_path, arcname)
    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype="application/zip",
        as_attachment=True,
        download_name="MatriSuraksha_Browser_Extension.zip"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"Starting MatriSuraksha Web Application on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
