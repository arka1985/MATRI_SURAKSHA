"""
MatriSuraksha - Database Layer & Seed Engine
Supports SQLite persistent storage for:
1. Primary Hospital Intake & CDSS Triage
2. Referral Destination Tracking & Delivery Outcomes
3. Closed-Loop Clinical Feedback from Receiving Hospitals
4. District CMOH Executive Surveillance Analytics
"""

import sqlite3
import os
import json
import hmac
import hashlib
import time
import struct
import base64
import pandas as pd
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "matrisuraksha.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(seed_from_csv=False):
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Facilities Master Table (User-Entered & Saved Dynamically)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS facilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        facility_name TEXT UNIQUE,
        facility_type TEXT DEFAULT 'PLHCU', -- 'PLHCU' or 'REFERRAL_CENTER'
        block_name TEXT DEFAULT '',
        created_at TEXT
    )
    """)

    # 2. Patients Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        study_id TEXT PRIMARY KEY,
        facility_name TEXT,
        block_name TEXT,
        patient_name TEXT,
        age REAL,
        phone TEXT,
        matrima_id TEXT,
        ses TEXT,
        caste TEXT,
        education TEXT,
        gravida INTEGER,
        parity_live INTEGER,
        parity_loss INTEGER,
        gestational_age REAL,
        anc_visits REAL,
        prev_complications TEXT,
        systolic_bp REAL,
        diastolic_bp REAL,
        hemoglobin REAL,
        fetal_heart_rate REAL,
        has_rom INTEGER,
        cervical_dilatation REAL,
        admission_date TEXT,
        admission_time TEXT,
        cdss_triage_level TEXT,
        cdss_color TEXT,
        cdss_risk_score REAL,
        cdss_urgency TEXT,
        cdss_triggers TEXT,
        is_referred INTEGER DEFAULT 0,
        referral_status TEXT DEFAULT 'ADMITTED', -- 'ADMITTED', 'REFERRED', 'COMPLETED', 'DELIVERED_LOCAL'
        referral_facility TEXT,
        referral_time TEXT,
        referral_reason TEXT,
        referral_timely TEXT,
        delivery_mode TEXT,
        delivery_date TEXT,
        delivery_time TEXT,
        delivery_place TEXT,
        baby_weight REAL,
        baby_sex TEXT,
        baby_status TEXT,
        resuscitation_needed TEXT,
        sncu_referred TEXT,
        created_at TEXT
    )
    """)

    # 2. Closed-Loop Referral Feedback Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS referral_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        study_id TEXT,
        referral_facility TEXT,
        doctor_name TEXT,
        arrival_condition TEXT,
        stabilization_quality TEXT,
        referral_appropriateness TEXT,
        maternal_outcome TEXT,
        neonatal_outcome TEXT,
        feedback_notes TEXT,
        submitted_at TEXT,
        FOREIGN KEY (study_id) REFERENCES patients(study_id)
    )
    """)

    # 3. Security & Users Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        full_name TEXT,
        role TEXT, -- 'DOCTOR', 'NURSE', 'CMOH'
        facility TEXT,
        totp_secret TEXT
    )
    """)

    # 4. Continuous Triage & Doctor Override Timeline Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS triage_assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        study_id TEXT,
        assessment_time TEXT,
        stage_of_labor TEXT,
        systolic_bp REAL,
        diastolic_bp REAL,
        pulse REAL,
        hemoglobin REAL,
        fetal_heart_rate REAL,
        gestational_age REAL,
        has_rom INTEGER,
        cervical_dilatation REAL,
        ai_decision TEXT,
        ai_triage_level TEXT,
        ai_risk_score REAL,
        ai_triggers TEXT,
        doctor_decision TEXT, -- 'AGREE', 'OVERRIDE'
        doctor_action TEXT,   -- 'REFER', 'OBSERVE_AT_PHC', 'DELIVER_AT_PHC', 'REEVALUATE'
        override_reason TEXT,
        doctor_name TEXT,
        reeval_hours REAL,
        next_reeval_time TEXT,
        doctor_final_order TEXT,
        FOREIGN KEY (study_id) REFERENCES patients(study_id)
    )
    """)

    # Safe Schema Migrations for existing tables
    for col, col_type in [
        ("reeval_hours", "REAL"),
        ("next_reeval_time", "TEXT"),
        ("doctor_final_order", "TEXT"),
        ("doctor_decision", "TEXT"),
        ("override_reason", "TEXT"),
    ]:
        try:
            cur.execute(f"ALTER TABLE triage_assessments ADD COLUMN {col} {col_type}")
        except Exception:
            pass
        try:
            cur.execute(f"ALTER TABLE patients ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    try:
        cur.execute("ALTER TABLE users ADD COLUMN totp_secret TEXT")
    except Exception:
        pass

    conn.commit()

    # Pre-seed default authenticated users with individual TOTP secrets (Option A)
    default_users = [
        ("dr.biswas", "matri123", "Dr. Dilip Kumar Biswas (PI & Dy. CMOH III)", "DOCTOR", "Harirampur RH", "JBSWY3DPEHPK3PXP"),
        ("dr.arka", "matri123", "Dr. Arkaprabha Sau (Co-PI & Chief AI/ML Scientist)", "DOCTOR", "District Health HQ", "HXDMVJECJJWSRZ3U"),
        ("dr.bhakta", "matri123", "Dr. Ishita Bhakta (Co-PI & Assistant Professor)", "DOCTOR", "Salt Lake", "KRSXG5CTMVRXEZLU"),
        ("dr.phc", "matri123", "PHC Doctor (Primary Health Unit)", "DOCTOR", "Primary Health Center", "MFRGGZDFMY2TMOBX"),
        ("dr.referral", "matri123", "Doctor at Referred Hospital (Specialist / SDH-DH)", "DOCTOR", "Referred Hospital", "NBSWY3DPEHPK3PZZ"),
        ("cmoh.dd", "matri123", "Chief Medical Officer of Health (Dakshin Dinajpur)", "CMOH", "Balurghat HQ", "OBXXK43VMVRXEZLS"),
    ]
    for u in default_users:
        cur.execute("""
        INSERT INTO users (username, password, full_name, role, facility, totp_secret)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(username) DO UPDATE SET
            password=excluded.password,
            full_name=excluded.full_name,
            role=excluded.role,
            facility=excluded.facility,
            totp_secret=excluded.totp_secret
        """, u)

    # Pre-seed standard Dakshin Dinajpur health facilities if empty
    cur.execute("SELECT COUNT(*) FROM facilities")
    if cur.fetchone()[0] == 0:
        now_ts = datetime.now().isoformat()
        default_facilities = [
            ("Harirampur RH", "PLHCU", "Harirampur", now_ts),
            ("Kushmandi RH", "PLHCU", "Kushmandi", now_ts),
            ("Banshihari RH", "PLHCU", "Banshihari", now_ts),
            ("Tapan RH", "PLHCU", "Tapan", now_ts),
            ("Kumarganj RH", "PLHCU", "Kumarganj", now_ts),
            ("Hili RH", "PLHCU", "Hili", now_ts),
            ("Gangarampur Sub-Divisional Hospital (SDH)", "REFERRAL_CENTER", "Gangarampur", now_ts),
            ("Balurghat District Hospital (DH)", "REFERRAL_CENTER", "Balurghat", now_ts),
            ("Malda Medical College & Hospital (MCH)", "REFERRAL_CENTER", "English Bazar", now_ts),
        ]
        cur.executemany("INSERT OR IGNORE INTO facilities (facility_name, facility_type, block_name, created_at) VALUES (?,?,?,?)", default_facilities)

    conn.commit()

    # Seed data if empty
    cur.execute("SELECT COUNT(*) FROM patients")
    count = cur.fetchone()[0]

    if count == 0 and seed_from_csv:
        csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cleaned_matrisuraksha.csv")
        eval_csv = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports", "cdss_cohort_evaluation.csv")
        
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            eval_map = {}
            if os.path.exists(eval_csv):
                eval_df = pd.read_csv(eval_csv)
                for _, erow in eval_df.iterrows():
                    eval_map[str(erow["Study_ID"]).zfill(4)] = erow

            for _, row in df.iterrows():
                sid = str(row.get("Unique Study ID", "")).zfill(4)
                eval_info = eval_map.get(sid, {})

                is_ref = int(row.get("Referred_Target", 0))
                if is_ref == 1:
                    ref_status = "REFERRED"
                elif pd.notnull(row.get("Mode of Delivery (Final)")):
                    ref_status = "DELIVERED_LOCAL"
                else:
                    ref_status = "ADMITTED"

                cur.execute("""
                INSERT OR REPLACE INTO patients (
                    study_id, facility_name, block_name, patient_name, age, phone, matrima_id,
                    ses, caste, education, gravida, parity_live, parity_loss, gestational_age,
                    anc_visits, prev_complications, systolic_bp, diastolic_bp, hemoglobin,
                    fetal_heart_rate, has_rom, cervical_dilatation, admission_date, admission_time,
                    cdss_triage_level, cdss_color, cdss_risk_score, cdss_urgency, cdss_triggers,
                    is_referred, referral_status, referral_facility, referral_time, referral_reason, referral_timely,
                    delivery_mode, delivery_date, delivery_time, delivery_place,
                    baby_weight, baby_sex, baby_status, resuscitation_needed, sncu_referred, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    sid,
                    str(row.get("Name of Health Facility", "Unknown PHC")),
                    str(row.get("Block Name", "Unknown")),
                    str(row.get("Name of Pregnant Woman", f"Mother {sid}")),
                    float(row.get("Age")) if pd.notnull(row.get("Age")) else None,
                    str(row.get("Phone Number", "")) if pd.notnull(row.get("Phone Number")) else None,
                    str(row.get("Matrima ID Number", "")) if pd.notnull(row.get("Matrima ID Number")) else None,
                    str(row.get("Socioeconomic_Status", "BPL")),
                    str(row.get("Caste", "General")),
                    str(row.get("Education", "Primary")),
                    int(row.get("Gravida_Num")) if pd.notnull(row.get("Gravida_Num")) else 1,
                    int(row.get("Parity_Live")) if pd.notnull(row.get("Parity_Live")) else 0,
                    int(row.get("Parity_Loss")) if pd.notnull(row.get("Parity_Loss")) else 0,
                    float(row.get("Gestational_Age")) if pd.notnull(row.get("Gestational_Age")) else 39.0,
                    float(row.get("ANC_Visits")) if pd.notnull(row.get("ANC_Visits")) else 4.0,
                    "Yes" if row.get("Has_Previous_Complications") == 1 else "No",
                    float(row.get("Systolic_BP")) if pd.notnull(row.get("Systolic_BP")) else 120.0,
                    float(row.get("Diastolic_BP")) if pd.notnull(row.get("Diastolic_BP")) else 80.0,
                    float(row.get("Hemoglobin")) if pd.notnull(row.get("Hemoglobin")) else 10.5,
                    float(row.get("Fetal_Heart_Rate")) if pd.notnull(row.get("Fetal_Heart_Rate")) else 140.0,
                    int(row.get("Has_ROM", 0)),
                    float(row.get("Cervical_Dilatation")) if pd.notnull(row.get("Cervical_Dilatation")) else None,
                    str(row.get("Date of Admission", "01.07.2026")),
                    str(row.get("Onset of Labour - Time", "08:00 AM")),
                    str(eval_info.get("CDSS_Triage_Level", "YELLOW" if is_ref else "GREEN")),
                    str(eval_info.get("CDSS_Color", "#FFB300" if is_ref else "#4CAF50")),
                    float(eval_info.get("CDSS_Risk_Score", 45.0 if is_ref else 0.0)),
                    str(eval_info.get("CDSS_Urgency", "Urgent Referral" if is_ref else "Routine Care")),
                    str(eval_info.get("CDSS_Triggers", "None")),
                    is_ref,
                    ref_status,
                    str(row.get("Name of Referral Facility", "Gangarampur SDH" if is_ref else "")),
                    str(row.get("Time of Referral Decision - Time", "")),
                    str(row.get("Referral Reason 1", "") or row.get("Reason for Referral - Other (specify)", "")),
                    str(row.get("Was Referral Timely?", "Yes" if is_ref else "")),
                    str(row.get("Mode of Delivery (Final)", "")),
                    str(row.get("Date of Final Child Birth", "")),
                    str(row.get("Time of Final Child Birth", "")),
                    str(row.get("Place of Final Childbirth (Name & Address)", "")),
                    float(row.get("Baby_Birth_Weight")) if pd.notnull(row.get("Baby_Birth_Weight")) else None,
                    str(row.get("Sex of Baby", "")),
                    str(row.get("Neonatal Status", "Alive" if pd.notnull(row.get("Baby_Birth_Weight")) else "")),
                    str(row.get("Need for Resuscitation", "No")),
                    str(row.get("Referred to SNCU/NICU", "No")),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

            # Add sample historical feedback from receiving hospital for referred cases
            sample_feedbacks = [
                ("0004", "Gangarampur SDH", "Dr. S. Mukherjee (Consultant Obstetrician)", "Patient brought with BP 150/90 and twitching", "Excellent - IV cannula placed and loading MgSO4 started", "Critical Life-Saving", "Emergency C-Section performed safely. Mother stable in HDU.", "Female baby, 2800g, vigorous, APGAR 8/9", "Timely decision by Harirampur staff saved mother from post-partum eclampsia."),
                ("0005", "Gangarampur SDH", "Dr. A. Das (Senior Resident)", "Active leaking >18 hrs, dry vagina", "Adequate - IV line maintained", "Appropriate & Timely", "Augmented labor, assisted vaginal delivery.", "Male baby, 2750g, kept in observational nursery for 24h.", "Good referral; prolonged PROM at PHC would have risked neonatal sepsis."),
                ("0009", "Balurghat DH", "Dr. P. Sen (G&O Specialist)", "Severe anemia with post-term gestation", "Good - Cross-matching sample accompanied", "Appropriate & Timely", "Vaginal delivery under blood standby. 1 unit PRBC transfused.", "Male baby, 3400g, healthy.", "Properly communicated before dispatch."),
            ]
            for sf in sample_feedbacks:
                cur.execute("""
                INSERT INTO referral_feedback (
                    study_id, referral_facility, doctor_name, arrival_condition,
                    stabilization_quality, referral_appropriateness, maternal_outcome,
                    neonatal_outcome, feedback_notes, submitted_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (*sf, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

            conn.commit()
            print(f"Seeded database with {len(df)} initial patients and clinical feedback records.")

    conn.close()


def get_all_patients(facility=None, status=None):
    conn = get_db_connection()
    query = "SELECT * FROM patients WHERE 1=1"
    params = []
    if facility and facility != "ALL":
        query += " AND facility_name = ?"
        params.append(facility)
    if status and status != "ALL":
        query += " AND referral_status = ?"
        params.append(status)
    query += " ORDER BY study_id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_patient_by_id(study_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM patients WHERE study_id = ?", (study_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_patient(study_id):
    """
    Permanently deletes a test patient record and all associated longitudinal data
    (triage assessments and closed-loop feedback).
    Authorized for test data purge by Dr. Arkaprabha Sau (Chief AI Scientist).
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM referral_feedback WHERE study_id = ?", (study_id,))
    cur.execute("DELETE FROM triage_assessments WHERE study_id = ?", (study_id,))
    cur.execute("DELETE FROM patients WHERE study_id = ?", (study_id,))
    conn.commit()
    conn.close()
    return True


def get_feedback_for_patient(study_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM referral_feedback WHERE study_id = ? ORDER BY id DESC", (study_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_feedbacks():
    conn = get_db_connection()
    rows = conn.execute("""
    SELECT rf.*, p.patient_name, p.facility_name as referring_phc, p.age, p.cdss_triage_level
    FROM referral_feedback rf
    JOIN patients p ON rf.study_id = p.study_id
    ORDER BY rf.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_facilities(facility_type=None):
    """Returns all saved health facilities (Primary Units or Referral Centers)."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS facilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        facility_name TEXT UNIQUE,
        facility_type TEXT DEFAULT 'PLHCU', -- 'PLHCU' or 'REFERRAL_CENTER'
        block_name TEXT DEFAULT '',
        created_at TEXT
    )
    """)
    if facility_type:
        rows = cur.execute("SELECT * FROM facilities WHERE facility_type = ? ORDER BY facility_name ASC", (facility_type,)).fetchall()
    else:
        rows = cur.execute("SELECT * FROM facilities ORDER BY facility_name ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_facility(facility_name, facility_type="PLHCU", block_name=""):
    """Saves a new user-entered Primary Unit or Referral Center so it appears automatically afterward."""
    name = str(facility_name).strip() if facility_name else ""
    if not name or name in ["__ADD_NEW__", "ALL", "None"]:
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS facilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        facility_name TEXT UNIQUE,
        facility_type TEXT DEFAULT 'PLHCU',
        block_name TEXT DEFAULT '',
        created_at TEXT
    )
    """)
    cur.execute("""
    INSERT OR IGNORE INTO facilities (facility_name, facility_type, block_name, created_at)
    VALUES (?, ?, ?, ?)
    """, (name, facility_type, block_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return name


def save_new_patient(patient_data):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Auto-save primary facility if entered by user
    facility_name = patient_data.get("facility_name", "").strip()
    if facility_name and facility_name not in ["__ADD_NEW__", "Primary Health Center", ""]:
        save_facility(facility_name, facility_type="PLHCU", block_name=patient_data.get("block_name", ""))
    else:
        facility_name = "Primary Health Center"
        patient_data["facility_name"] = facility_name
    
    # Auto-generate next study ID starting from 0001
    if not patient_data.get("study_id"):
        cur.execute("SELECT MAX(CAST(study_id AS INTEGER)) FROM patients")
        row = cur.fetchone()
        max_id = row[0] if (row and row[0] is not None) else 0
        patient_data["study_id"] = str(max_id + 1).zfill(4)
        
    cur.execute("""
    INSERT INTO patients (
        study_id, facility_name, block_name, patient_name, age, phone, matrima_id,
        ses, caste, education, gravida, parity_live, parity_loss, gestational_age,
        anc_visits, prev_complications, systolic_bp, diastolic_bp, hemoglobin,
        fetal_heart_rate, has_rom, cervical_dilatation, admission_date, admission_time,
        cdss_triage_level, cdss_color, cdss_risk_score, cdss_urgency, cdss_triggers,
        referral_status, created_at
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        patient_data["study_id"],
        patient_data.get("facility_name", "Primary Health Center"),
        patient_data.get("block_name", "District Block"),
        patient_data.get("patient_name", "Pregnant Mother"),
        patient_data.get("age"),
        patient_data.get("phone"),
        patient_data.get("matrima_id"),
        patient_data.get("ses", "BPL"),
        patient_data.get("caste", "General"),
        patient_data.get("education", "Primary"),
        patient_data.get("gravida", 1),
        patient_data.get("parity_live", 0),
        patient_data.get("parity_loss", 0),
        patient_data.get("gestational_age", 39.0),
        patient_data.get("anc_visits", 4),
        patient_data.get("prev_complications", "No"),
        patient_data.get("systolic_bp", 120.0),
        patient_data.get("diastolic_bp", 80.0),
        patient_data.get("hemoglobin", 10.5),
        patient_data.get("fetal_heart_rate", 140.0),
        patient_data.get("has_rom", 0),
        patient_data.get("cervical_dilatation"),
        patient_data.get("admission_date", datetime.now().strftime("%d-%m-%Y")),
        patient_data.get("admission_time", datetime.now().strftime("%I:%M %p")),
        patient_data.get("cdss_triage_level", "GREEN"),
        patient_data.get("cdss_color", "#4CAF50"),
        patient_data.get("cdss_risk_score", 0.0),
        patient_data.get("cdss_urgency", "Routine Care"),
        patient_data.get("cdss_triggers", "None"),
        "ADMITTED",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()
    return patient_data["study_id"]


def dispatch_referral(study_id, referral_facility, reason, urgency, notes=""):
    ref_name = str(referral_facility).strip() if referral_facility else ""
    if ref_name and ref_name not in ["__ADD_NEW__", "ALL", "None"]:
        save_facility(ref_name, facility_type="REFERRAL_CENTER")
    conn = get_db_connection()
    conn.execute("""
    UPDATE patients SET
        referral_status = 'REFERRED',
        referral_facility = ?,
        referral_time = ?,
        referral_reason = ?,
        referral_timely = 'Yes'
    WHERE study_id = ?
    """, (
        ref_name if ref_name else "Referred Hospital",
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        reason,
        study_id
    ))
    conn.commit()
    conn.close()


def submit_referral_feedback(feedback_data):
    ref_fac = str(feedback_data.get("referral_facility", "")).strip()
    if ref_fac and ref_fac not in ["__ADD_NEW__", "ALL", "None"]:
        save_facility(ref_fac, facility_type="REFERRAL_CENTER")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO referral_feedback (
        study_id, referral_facility, doctor_name, arrival_condition,
        stabilization_quality, referral_appropriateness, maternal_outcome,
        neonatal_outcome, feedback_notes, submitted_at
    ) VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        feedback_data["study_id"],
        feedback_data.get("referral_facility", "Secondary Referral Hospital"),
        feedback_data.get("doctor_name", "Attending Obstetrician"),
        feedback_data.get("arrival_condition", "Stable"),
        feedback_data.get("stabilization_quality", "Adequate"),
        feedback_data.get("referral_appropriateness", "Appropriate & Timely"),
        feedback_data.get("maternal_outcome", "Delivered safely"),
        feedback_data.get("neonatal_outcome", "Healthy"),
        feedback_data.get("feedback_notes", ""),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    # Update patient delivery status
    cur.execute("""
    UPDATE patients SET
        referral_status = 'COMPLETED',
        delivery_mode = ?,
        delivery_date = ?,
        baby_weight = ?,
        baby_status = ?,
        sncu_referred = ?
    WHERE study_id = ?
    """, (
        feedback_data.get("delivery_mode", "Normal"),
        datetime.now().strftime("%d.%m.%Y"),
        feedback_data.get("baby_weight"),
        feedback_data.get("baby_status", "Alive"),
        feedback_data.get("sncu_referred", "No"),
        feedback_data["study_id"]
    ))
    conn.commit()
    conn.close()


def verify_totp(token, secret):
    """
    Standard RFC 6238 Time-based One-Time Password (TOTP) verification.
    Validates dynamic 6-digit codes generated by Google Authenticator / Microsoft Authenticator.
    Works 100% offline without external network requests, SMS, or email dependencies.
    """
    if not token or not secret:
        return False
    t = str(token).strip().replace(" ", "")
    if not t.isdigit() or len(t) != 6:
        return False
    try:
        key = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8), casefold=True)
        now_step = int(time.time() // 30)
        # Check current step and drift of +/- 1 window (30s tolerance)
        for offset in (0, -1, 1):
            c = struct.pack("!Q", now_step + offset)
            h = hmac.new(key, c, hashlib.sha1).digest()
            o = h[19] & 15
            expected = (struct.unpack("!I", h[o:o+4])[0] & 0x7fffffff) % 1000000
            if f"{expected:06d}" == t:
                return True
        return False
    except Exception:
        return False


def generate_totp(secret):
    """
    Generate dynamic 6-digit TOTP for a given secret.
    Standard RFC 6238 implementation for testing and validation.
    """
    key = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8), casefold=True)
    c = struct.pack("!Q", int(time.time() // 30))
    h = hmac.new(key, c, hashlib.sha1).digest()
    o = h[19] & 15
    code = (struct.unpack("!I", h[o:o+4])[0] & 0x7fffffff) % 1000000
    return f"{code:06d}"


def get_user_by_username(username):
    """Retrieve user record by username (case-insensitive)."""
    if not username:
        return None
    conn = get_db_connection()
    user_row = conn.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (str(username).strip(),)).fetchone()
    conn.close()
    return dict(user_row) if user_row else None


def verify_user(username, password, otp=None):
    """
    Option A: True Two-Factor Authentication (2FA).
    Requires BOTH:
    1. Something you KNOW: Correct private password
    2. Something you HAVE: Dynamic 6-digit TOTP from user's configured Authenticator app
    
    Returns:
        tuple: (user_dict, error_message)
        Success: (user_dict, None)
        Failure: (None, error_message_str)
    """
    if not username:
        return None, "Healthcare User ID is required."
        
    conn = get_db_connection()
    user_row = conn.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (str(username).strip(),)).fetchone()
    conn.close()
    if not user_row:
        return None, "Healthcare User ID not recognized."
    
    user = dict(user_row)
    pwd_clean = str(password).strip() if password is not None else ""
    otp_clean = str(otp).strip() if otp is not None else ""
    
    # 1. Factor 1: Verify Password (Knowledge Factor)
    if not pwd_clean or pwd_clean != user.get("password"):
        return None, "Invalid security password. Access denied."
    
    # 2. Factor 2: Verify Dynamic OTP from Authenticator App (Possession Factor)
    user_secret = user.get("totp_secret")
    if not user_secret:
        return None, "Authenticator 2FA secret is not configured for this account."
        
    if not otp_clean:
        return None, "6-Digit Authenticator OTP is required for Two-Factor Authentication."
        
    if not verify_totp(otp_clean, user_secret):
        return None, "Invalid or expired 6-Digit Authenticator OTP. Please re-enter the live code from your phone."
        
    return user, None


def get_all_users():
    conn = get_db_connection()
    rows = conn.execute("SELECT username, full_name, role, facility FROM users").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_triage_assessment(study_id, vitals, ai_eval, doctor_decision="AGREE", doctor_action="ROUTINE", override_reason="", doctor_name="Dr. Dilip Biswas"):
    conn = get_db_connection()
    cur = conn.cursor()
    
    triggers_str = " | ".join([f"[{t['severity']}] {t['title']}" for t in ai_eval.get("triggers", [])]) if ai_eval.get("triggers") else "None"
    
    cur.execute("""
    INSERT INTO triage_assessments (
        study_id, assessment_time, stage_of_labor, systolic_bp, diastolic_bp, pulse,
        hemoglobin, fetal_heart_rate, gestational_age, has_rom, cervical_dilatation,
        ai_decision, ai_triage_level, ai_risk_score, ai_triggers,
        doctor_decision, doctor_action, override_reason, doctor_name
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        study_id,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        vitals.get("stage_of_labor", "Active Labour"),
        vitals.get("systolic_bp"),
        vitals.get("diastolic_bp"),
        vitals.get("pulse"),
        vitals.get("hemoglobin"),
        vitals.get("fetal_heart_rate"),
        vitals.get("gestational_age"),
        vitals.get("has_rom", 0),
        vitals.get("cervical_dilatation"),
        ai_eval.get("ai_decision"),
        ai_eval.get("triage_level"),
        ai_eval.get("risk_score"),
        triggers_str,
        doctor_decision,
        doctor_action,
        override_reason,
        doctor_name
    ))
    
    # Update latest vitals on patient table
    cur.execute("""
    UPDATE patients SET
        systolic_bp = COALESCE(?, systolic_bp),
        diastolic_bp = COALESCE(?, diastolic_bp),
        hemoglobin = COALESCE(?, hemoglobin),
        fetal_heart_rate = COALESCE(?, fetal_heart_rate),
        cdss_triage_level = ?,
        cdss_color = ?,
        cdss_risk_score = ?,
        cdss_urgency = ?,
        cdss_triggers = ?
    WHERE study_id = ?
    """, (
        vitals.get("systolic_bp"),
        vitals.get("diastolic_bp"),
        vitals.get("hemoglobin"),
        vitals.get("fetal_heart_rate"),
        ai_eval.get("triage_level"),
        ai_eval.get("triage_color"),
        ai_eval.get("risk_score"),
        ai_eval.get("urgency"),
        triggers_str,
        study_id
    ))
    
    conn.commit()
    conn.close()


def save_doctor_evaluation_order(study_id, doctor_decision="AGREE", doctor_action="ROUTINE", override_reason="", reeval_hours=None, next_reeval_time=None, doctor_name="Attending Medical Officer"):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Update patient master record
    cur.execute("""
    UPDATE patients SET
        doctor_final_order = ?,
        doctor_decision = ?,
        override_reason = ?,
        reeval_hours = ?,
        next_reeval_time = ?,
        referral_status = CASE 
            WHEN ? = 'REFER' THEN 'REFERRED'
            WHEN ? = 'ROUTINE' THEN 'OBSERVED_PLHCU'
            ELSE 'REEVALUATION_SCHEDULED'
        END,
        is_referred = CASE WHEN ? = 'REFER' THEN 1 ELSE is_referred END
    WHERE study_id = ?
    """, (doctor_action, doctor_decision, override_reason, reeval_hours, next_reeval_time, doctor_action, doctor_action, doctor_action, study_id))
    
    # 2. Append event to triage assessments timeline
    cur.execute("""
    INSERT INTO triage_assessments (
        study_id, assessment_time, stage_of_labor,
        doctor_decision, doctor_action, override_reason, doctor_name,
        reeval_hours, next_reeval_time, doctor_final_order
    ) VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        study_id,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Clinical Evaluation Sign-Off",
        doctor_decision,
        doctor_action,
        override_reason,
        doctor_name,
        reeval_hours,
        next_reeval_time,
        doctor_action
    ))
    
    conn.commit()
    conn.close()


def get_patient_timeline(study_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM triage_assessments WHERE study_id = ? ORDER BY id ASC", (study_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_cmoh_district_analytics():
    conn = get_db_connection()
    cur = conn.cursor()
    
    total_admissions = cur.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    total_referrals = cur.execute("SELECT COUNT(*) FROM patients WHERE is_referred = 1").fetchone()[0]
    total_red = cur.execute("SELECT COUNT(*) FROM patients WHERE cdss_triage_level = 'RED'").fetchone()[0]
    total_yellow = cur.execute("SELECT COUNT(*) FROM patients WHERE cdss_triage_level = 'YELLOW'").fetchone()[0]
    total_green = cur.execute("SELECT COUNT(*) FROM patients WHERE cdss_triage_level = 'GREEN'").fetchone()[0]
    anemia_count = cur.execute("SELECT COUNT(*) FROM patients WHERE hemoglobin < 11.0").fetchone()[0]
    teenage_count = cur.execute("SELECT COUNT(*) FROM patients WHERE age <= 19").fetchone()[0]
    feedbacks_count = cur.execute("SELECT COUNT(*) FROM referral_feedback").fetchone()[0]
    
    # Facility breakdown
    facility_stats = cur.execute("""
    SELECT 
        facility_name,
        COUNT(*) as total_admissions,
        SUM(CASE WHEN is_referred = 1 THEN 1 ELSE 0 END) as referrals,
        SUM(CASE WHEN cdss_triage_level = 'RED' THEN 1 ELSE 0 END) as red_cases,
        ROUND(AVG(hemoglobin), 1) as avg_hb,
        ROUND(AVG(age), 1) as avg_age
    FROM patients
    GROUP BY facility_name
    ORDER BY total_admissions DESC
    """).fetchall()
    
    # Feedback appropriateness breakdown
    appropriateness_stats = cur.execute("""
    SELECT referral_appropriateness, COUNT(*) as count
    FROM referral_feedback
    GROUP BY referral_appropriateness
    """).fetchall()
    
    conn.close()
    
    return {
        "kpi": {
            "total_admissions": total_admissions,
            "total_referrals": total_referrals,
            "referral_rate": round((total_referrals / total_admissions) * 100, 1) if total_admissions else 0,
            "red_count": total_red,
            "yellow_count": total_yellow,
            "green_count": total_green,
            "anemia_rate": round((anemia_count / total_admissions) * 100, 1) if total_admissions else 0,
            "teenage_rate": round((teenage_count / total_admissions) * 100, 1) if total_admissions else 0,
            "feedbacks_count": feedbacks_count,
        },
        "facilities": [dict(r) for r in facility_stats],
        "feedback_summary": [dict(r) for r in appropriateness_stats],
    }


if __name__ == "__main__":
    init_db()
    cmoh = get_cmoh_district_analytics()
    print("CMOH Metrics Summary:", cmoh["kpi"])
