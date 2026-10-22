"""
MatriSuraksha - Cohort Evaluation of CDSS Referral Decisions
Evaluates the Rule-Based Clinical Decision Support System against all 57 cohort patients.
Calculates Sensitivity, Specificity, Concordance, and detailed case-by-case audit.
"""

import os
import pandas as pd
from clinical_rules import MatriSurakshaCDSS, TriageLevel


def run_cdss_cohort_evaluation(data_path, out_dir):
    df = pd.read_csv(data_path)
    cdss = MatriSurakshaCDSS()
    
    results = []
    
    for idx, row in df.iterrows():
        patient_dict = row.to_dict()
        assessment = cdss.evaluate_patient(patient_dict)
        
        # Extract triggers summary
        trigger_titles = [f"[{t.severity}] {t.title}" for t in assessment.active_triggers]
        trigger_str = " | ".join(trigger_titles) if trigger_titles else "None"
        
        results.append({
            "Study_ID": assessment.study_id,
            "Facility": row.get("Name of Health Facility"),
            "Age": row.get("Age"),
            "Gestational_Age": row.get("Gestational_Age"),
            "Hemoglobin": row.get("Hemoglobin"),
            "BP": f"{row.get('Systolic_BP', '')}/{row.get('Diastolic_BP', '')}",
            "Actual_Referred": int(row.get("Referred_Target", 0)),
            "CDSS_Triage_Level": assessment.triage_level.name,
            "CDSS_Color": assessment.triage_color,
            "CDSS_Refer_Recommended": int(assessment.referral_recommended),
            "CDSS_Risk_Score": assessment.risk_score,
            "CDSS_Urgency": assessment.urgency,
            "CDSS_Triggers": trigger_str,
            "Triggers_Count": len(assessment.active_triggers),
        })
        
    eval_df = pd.DataFrame(results)
    
    # Save detailed evaluation
    eval_csv = os.path.join(out_dir, "cdss_cohort_evaluation.csv")
    eval_df.to_csv(eval_csv, index=False)
    print(f"Exported CDSS evaluation for all {len(eval_df)} patients to {eval_csv}")
    
    # Concordance & Diagnostic Performance Metrics
    actual_pos = eval_df["Actual_Referred"] == 1
    actual_neg = eval_df["Actual_Referred"] == 0
    cdss_pos = eval_df["CDSS_Refer_Recommended"] == 1
    cdss_neg = eval_df["CDSS_Refer_Recommended"] == 0
    
    tp = (actual_pos & cdss_pos).sum()
    fn = (actual_pos & cdss_neg).sum()
    tn = (actual_neg & cdss_neg).sum()
    fp = (actual_neg & cdss_pos).sum()
    
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    ppv = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    npv = tn / (tn + fn) if (tn + fn) > 0 else 0.0
    accuracy = (tp + tn) / len(eval_df)
    
    print("\n" + "=" * 60)
    print("MATRISURAKSHA CDSS CLINICAL TRIAGE PERFORMANCE")
    print("=" * 60)
    print(f"Total Enrolled Patients:      {len(eval_df)}")
    print(f"Actual Clinical Referrals:    {actual_pos.sum()}")
    print(f"CDSS Recommended Referrals:   {cdss_pos.sum()}")
    print(f"\nConfusion Matrix (Referral Flag):")
    print(f"  True Positives  (TP): {tp} (Referred & Flagged)")
    print(f"  False Negatives (FN): {fn} (Referred but Missed)")
    print(f"  True Negatives  (TN): {tn} (Delivered Locally & Cleared)")
    print(f"  False Positives (FP): {fp} (Flagged for Higher Vigilance/Transfer)")
    print(f"\nDiagnostic Statistics:")
    print(f"  Sensitivity (Recall):       {sensitivity:.1%}")
    print(f"  Specificity:                {specificity:.1%}")
    print(f"  Positive Predictive Value:  {ppv:.1%}")
    print(f"  Negative Predictive Value:  {npv:.1%}")
    print(f"  Overall Concordance:        {accuracy:.1%}")
    
    print("\n--- Distribution of CDSS Triage Levels across Cohort ---")
    print(eval_df["CDSS_Triage_Level"].value_counts().to_string())
    
    print("\n--- Audit of Actual Referred Cases (All 9 patients) ---")
    referred_cases = eval_df[eval_df["Actual_Referred"] == 1][
        ["Study_ID", "Facility", "CDSS_Triage_Level", "CDSS_Refer_Recommended", "CDSS_Risk_Score", "CDSS_Triggers"]
    ]
    print(referred_cases.to_string(index=False))
    
    return eval_df


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_dir, "data", "cleaned_matrisuraksha.csv")
    out_dir = os.path.join(base_dir, "reports")
    os.makedirs(out_dir, exist_ok=True)
    
    run_cdss_cohort_evaluation(data_path, out_dir)
