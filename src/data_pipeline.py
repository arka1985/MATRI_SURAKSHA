"""
MatriSuraksha - Data Cleaning, Harmonization and Feature Engineering Pipeline
Project: MatriSuraksha (AI-Driven Referral Decision Support System)
"""

import os
import re
import numpy as np
import pandas as pd
import openpyxl


def parse_blood_pressure(bp_val):
    """
    Parses blood pressure string (e.g., '120/80', '150/90') into (systolic, diastolic).
    Returns (np.nan, np.nan) if invalid or missing.
    """
    if pd.isna(bp_val):
        return np.nan, np.nan
    bp_str = str(bp_val).strip()
    match = re.search(r"(\d{2,3})\s*/\s*(\d{2,3})", bp_str)
    if match:
        try:
            return float(match.group(1)), float(match.group(2))
        except ValueError:
            return np.nan, np.nan
    return np.nan, np.nan


def parse_gravida(gravida_val):
    """
    Normalizes gravida representation (e.g., '1st ', '2nd', '3rd', '4th') to integer.
    """
    if pd.isna(gravida_val):
        return np.nan
    s = str(gravida_val).strip().lower()
    match = re.search(r"\d+", s)
    if match:
        return int(match.group(0))
    return np.nan


def parse_parity(parity_val):
    """
    Parses parity string (e.g., 'P0+0', 'P1+0', 'P1+1', 'P2+1', 'P1')
    Returns (live_births, pregnancy_losses).
    """
    if pd.isna(parity_val):
        return np.nan, np.nan
    s = str(parity_val).strip().upper()
    match = re.search(r"P(\d+)(?:\+(\d+))?", s)
    if match:
        live = int(match.group(1))
        loss = int(match.group(2)) if match.group(2) is not None else 0
        return live, loss
    return np.nan, np.nan


def categorize_anemia(hb):
    """
    Categorizes hemoglobin level (g/dL) as per WHO/MoHFW India guidelines:
    - Normal: >= 11.0
    - Mild: 10.0 - 10.9
    - Moderate: 7.0 - 9.9
    - Severe: < 7.0
    """
    if pd.isna(hb):
        return "Unknown"
    if hb >= 11.0:
        return "Normal"
    elif hb >= 10.0:
        return "Mild"
    elif hb >= 7.0:
        return "Moderate"
    else:
        return "Severe"


def clean_matrisuraksha_data(file_path):
    """
    Loads, harmonizes, and enriches raw Excel data from MatriSuraksha workbook.
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb["DKB"]
    raw_data = list(ws.iter_rows(values_only=True))
    
    # Row index 2 (row 3 in Excel) contains header names
    headers = [str(c).strip() if c is not None else f"col_{i}" for i, c in enumerate(raw_data[2])]
    
    # Rows with data start at index 3
    data_rows = []
    for r in raw_data[3:]:
        # Keep row if it has at least a Study ID or substantive data
        if r[0] is not None and str(r[0]).strip() != "":
            data_rows.append(r)
            
    df = pd.DataFrame(data_rows, columns=headers)
    print(f"Loaded {len(df)} active patient records from {file_path}")
    
    # 1. Clean Identifiers & Facility
    df["Unique Study ID"] = df["Unique Study ID"].astype(str).str.strip().str.zfill(4)
    df["Name of Health Facility"] = df["Name of Health Facility"].astype(str).str.strip()
    df["Block Name"] = df["Block Name"].astype(str).str.strip()
    
    # 2. Demographic Features
    df["Age"] = pd.to_numeric(df["Age (years)"], errors="coerce")
    df["Is_Teenage"] = (df["Age"] <= 19).astype(int)
    df["Is_Advanced_Age"] = (df["Age"] >= 35).astype(int)
    
    df["Socioeconomic_Status"] = df["Socioeconomic Status"].astype(str).str.strip().str.upper()
    df["Is_BPL"] = (df["Socioeconomic_Status"] == "BPL").astype(int)
    
    df["Caste"] = df["Caste Category"].astype(str).str.strip()
    df["Is_ST_SC"] = df["Caste"].isin(["ST", "SC"]).astype(int)
    
    df["Education"] = df["Education Level"].astype(str).str.strip()
    
    # 3. Obstetric History
    df["Gravida_Num"] = df["Gravida"].apply(parse_gravida)
    df["Is_Primigravida"] = (df["Gravida_Num"] == 1).astype(int)
    
    parity_parsed = df["Parity"].apply(parse_parity)
    df["Parity_Live"] = [p[0] for p in parity_parsed]
    df["Parity_Loss"] = [p[1] for p in parity_parsed]
    
    df["Gestational_Age_ANC"] = pd.to_numeric(df["Weeks of Gestation (ANC)"], errors="coerce")
    df["Gestational_Age_Intrapartum"] = pd.to_numeric(df["Weeks of Gestation (Intrapartum)"], errors="coerce")
    df["Gestational_Age"] = df["Gestational_Age_Intrapartum"].combine_first(df["Gestational_Age_ANC"])
    
    df["Is_Preterm"] = (df["Gestational_Age"] < 37).astype(int)
    df["Is_Postterm"] = (df["Gestational_Age"] >= 41).astype(int)
    
    df["ANC_Visits"] = pd.to_numeric(df["No. of ANC Visits till onset of Labour"], errors="coerce")
    df["Inadequate_ANC"] = (df["ANC_Visits"] < 4).astype(int)
    
    prev_comp_str = df["History of Previous Complications"].astype(str).str.strip().str.upper()
    df["Has_Previous_Complications"] = prev_comp_str.isin(["YES", "Y"]).astype(int)
    
    # 4. Clinical Measurements & Vitals
    df["Hemoglobin"] = pd.to_numeric(df["Hemoglobin Hb (g/dL)"], errors="coerce")
    df["Anemia_Category"] = df["Hemoglobin"].apply(categorize_anemia)
    df["Has_Anemia"] = (df["Hemoglobin"] < 11.0).astype(int)
    df["Has_Moderate_Severe_Anemia"] = (df["Hemoglobin"] < 10.0).astype(int)
    
    # Parse ANC and Intrapartum Blood Pressure
    anc_bp = df["Blood Pressure (mmHg)"].apply(parse_blood_pressure)
    df["ANC_Systolic_BP"] = [b[0] for b in anc_bp]
    df["ANC_Diastolic_BP"] = [b[1] for b in anc_bp]
    
    intra_bp = df["Vitals - BP"].apply(parse_blood_pressure)
    df["Intra_Systolic_BP"] = [b[0] for b in intra_bp]
    df["Intra_Diastolic_BP"] = [b[1] for b in intra_bp]
    
    df["Systolic_BP"] = df["Intra_Systolic_BP"].combine_first(df["ANC_Systolic_BP"])
    df["Diastolic_BP"] = df["Intra_Diastolic_BP"].combine_first(df["ANC_Diastolic_BP"])
    
    # Clinical Hypertension Criteria
    df["Is_Hypertensive"] = ((df["Systolic_BP"] >= 140) | (df["Diastolic_BP"] >= 90)).astype(int)
    df["Is_Severe_Hypertension"] = ((df["Systolic_BP"] >= 160) | (df["Diastolic_BP"] >= 110)).astype(int)
    
    # Vitals
    df["Pulse"] = pd.to_numeric(df["Vitals - Pulse"], errors="coerce")
    df["Fetal_Heart_Rate"] = pd.to_numeric(df["Fetal Heart Rate (Intrapartum)"], errors="coerce")
    df["Fetal_Heart_Rate"] = df["Fetal_Heart_Rate"].combine_first(
        pd.to_numeric(df["Fetal Heart Rate FHR (ANC)"], errors="coerce")
    )
    df["Fetal_Distress_FHR"] = ((df["Fetal_Heart_Rate"] < 110) | (df["Fetal_Heart_Rate"] > 160)).astype(int)
    
    # 5. Labor & Membrane Rupture
    rom_str = df["Rupture of Membranes (ROM)"].astype(str).str.strip().str.upper()
    df["Has_ROM"] = rom_str.isin(["YES", "Y"]).astype(int)
    
    df["Cervical_Dilatation"] = pd.to_numeric(df["VE - Cervical Dilatation (cm)"], errors="coerce")
    
    # 6. Referral Outcome Harmonization (Target Variable)
    ref_col = df["Referred to Higher Center"].astype(str).str.strip().str.upper()
    ref_facility = df["Name of Referral Facility"].notnull()
    ref_reason_1 = df["Referral Reason 1"].notnull()
    ref_reason_other = df["Reason for Referral - Other (specify)"].notnull()
    
    # Patient is marked Referred if explicit Yes OR referral facility/reason exists
    df["Referred_Target"] = (
        ref_col.isin(["YES", "Y"]) | ref_facility | ref_reason_1 | ref_reason_other
    ).astype(int)
    
    # Identify Reason Flags
    reasons_text = (
        df["Referral Reason 1"].fillna("").astype(str)
        + " "
        + df["Reason for Referral - Other (specify)"].fillna("").astype(str)
    ).str.upper()
    
    df["Reason_PIH_Eclampsia"] = reasons_text.apply(
        lambda s: 1 if any(k in s for k in ["PIH", "ECLAMPSIA", "PREECLAMPSIA", "BP"]) else 0
    )
    df["Reason_Hemorrhage"] = reasons_text.apply(
        lambda s: 1 if any(k in s for k in ["APH", "PPH", "BLEEDING", "HEMORRHAGE"]) else 0
    )
    df["Reason_PROM_Dribbling"] = reasons_text.apply(
        lambda s: 1 if any(k in s for k in ["PROM", "DRIBBLING", "DRIBBLEING", "LEAK"]) else 0
    )
    df["Reason_Fetal_Distress"] = reasons_text.apply(
        lambda s: 1 if any(k in s for k in ["FETAL DISTRESS", "CORD", "ASPHYXIA"]) else 0
    )
    df["Reason_Postterm_Macrosomia"] = reasons_text.apply(
        lambda s: 1 if any(k in s for k in ["POST TERM", "OVERWEIGHT", "MACROSOMIA"]) else 0
    )
    
    # Delivery Outcome Harmonization
    df["Delivered_Locally"] = df["Place of Final Childbirth (Name & Address)"].notnull().astype(int)
    df["Baby_Birth_Weight"] = pd.to_numeric(df["Birth Weight (grams)"], errors="coerce")
    df["Is_Low_Birth_Weight"] = (df["Baby_Birth_Weight"] < 2500).astype(int)
    
    return df


def generate_feature_matrix(df):
    """
    Selects and pre-formats analytical feature columns for predictive modeling and risk profiling.
    """
    feature_cols = [
        "Unique Study ID",
        "Name of Health Facility",
        "Age",
        "Is_Teenage",
        "Is_Advanced_Age",
        "Is_BPL",
        "Is_ST_SC",
        "Gravida_Num",
        "Is_Primigravida",
        "Parity_Live",
        "Parity_Loss",
        "Gestational_Age",
        "Is_Preterm",
        "Is_Postterm",
        "ANC_Visits",
        "Inadequate_ANC",
        "Has_Previous_Complications",
        "Hemoglobin",
        "Has_Anemia",
        "Has_Moderate_Severe_Anemia",
        "Systolic_BP",
        "Diastolic_BP",
        "Is_Hypertensive",
        "Is_Severe_Hypertension",
        "Pulse",
        "Fetal_Heart_Rate",
        "Fetal_Distress_FHR",
        "Has_ROM",
        "Cervical_Dilatation",
        # Target
        "Referred_Target",
    ]
    
    return df[feature_cols].copy()


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    excel_path = os.path.join(base_dir, "MatriSuraksha Dataset Final Version.xlsx")
    out_dir = os.path.join(base_dir, "data")
    os.makedirs(out_dir, exist_ok=True)
    
    cleaned_df = clean_matrisuraksha_data(excel_path)
    csv_path = os.path.join(out_dir, "cleaned_matrisuraksha.csv")
    cleaned_df.to_csv(csv_path, index=False)
    print(f"Exported cleaned dataset ({len(cleaned_df)} rows, {cleaned_df.shape[1]} columns) to {csv_path}")
    
    feature_df = generate_feature_matrix(cleaned_df)
    feat_path = os.path.join(out_dir, "feature_matrix.csv")
    feature_df.to_csv(feat_path, index=False)
    print(f"Exported feature matrix ({feature_df.shape}) to {feat_path}")
    
    print("\nSummary Stats of Key Processed Features:")
    print("Referral Rate:", feature_df["Referred_Target"].mean())
    print("Teenage Rate:", feature_df["Is_Teenage"].mean())
    print("Hypertension Rate:", feature_df["Is_Hypertensive"].mean())
    print("Anemia Rate (<11 g/dL):", feature_df["Has_Anemia"].mean())
    print("Moderate/Severe Anemia (<10 g/dL):", feature_df["Has_Moderate_Severe_Anemia"].mean())
