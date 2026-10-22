"""
MatriSuraksha - Visualizations & Clinical Analytics Figures Generator
Produces publication-ready charts summarizing cohort risk factors and CDSS performance.
"""

import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Set style
sns.set_theme(style="whitegrid", font="sans-serif")
plt.rcParams.update({"font.size": 11, "figure.autolayout": True})


def generate_visual_reports(data_path, eval_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    df = pd.read_csv(data_path)
    eval_df = pd.read_csv(eval_path)

    # -------------------------------------------------------------
    # Figure 1: Comprehensive Maternal Risk Profile
    # -------------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1A: Maternal Age Distribution & High-Risk Brackets
    sns.histplot(
        df["Age"].dropna(),
        bins=15,
        kde=True,
        color="#1976D2",
        ax=axes[0, 0],
    )
    axes[0, 0].axvline(19.5, color="#D32F2F", linestyle="--", linewidth=2, label="Teenage Threshold (<=19y)")
    axes[0, 0].set_title("A. Maternal Age Distribution (Cohort Mean: 22.2 yrs)", fontsize=13, weight="bold")
    axes[0, 0].set_xlabel("Age in Years")
    axes[0, 0].set_ylabel("Count of Mothers")
    axes[0, 0].legend(loc="upper right")

    # 1B: Hemoglobin Levels & Anemia Burden
    hb_clean = df["Hemoglobin"].dropna()
    sns.kdeplot(hb_clean, color="#C2185B", fill=True, alpha=0.3, ax=axes[0, 1])
    axes[0, 1].axvline(11.0, color="#FF9800", linestyle="--", linewidth=1.8, label="Anemia Cutoff (<11.0 g/dL)")
    axes[0, 1].axvline(10.0, color="#E64A19", linestyle="--", linewidth=1.8, label="Moderate Anemia (<10.0 g/dL)")
    axes[0, 1].axvline(7.0, color="#B71C1C", linestyle="--", linewidth=2.0, label="Severe Anemia (<7.0 g/dL)")
    axes[0, 1].set_title("B. Hemoglobin Profile (70.2% Anemia Prevalence)", fontsize=13, weight="bold")
    axes[0, 1].set_xlabel("Hemoglobin (g/dL)")
    axes[0, 1].set_ylabel("Density")
    axes[0, 1].legend(loc="upper left")

    # 1C: Blood Pressure Scatter & Hypertensive Crisis Thresholds
    sns.scatterplot(
        data=df,
        x="Systolic_BP",
        y="Diastolic_BP",
        hue="Referred_Target",
        palette={0: "#2E7D32", 1: "#D32F2F"},
        s=85,
        ax=axes[1, 0],
    )
    axes[1, 0].axvline(140, color="gray", linestyle=":", label="Stage 1 HTN (140/90)")
    axes[1, 0].axhline(90, color="gray", linestyle=":")
    axes[1, 0].axvline(160, color="#C62828", linestyle="--", label="Severe Crisis (160/110)")
    axes[1, 0].axhline(110, color="#C62828", linestyle="--")
    axes[1, 0].set_title("C. Intrapartum/ANC Blood Pressure Risk Space", fontsize=13, weight="bold")
    axes[1, 0].set_xlabel("Systolic BP (mmHg)")
    axes[1, 0].set_ylabel("Diastolic BP (mmHg)")
    axes[1, 0].legend(title="Referred", labels=["Normal Care", "Referred Case", "Stage 1 HTN", "Severe Crisis"], loc="lower right")

    # 1D: Referral Triggers & Danger Signs
    danger_counts = {
        "Amniotic Fluid Leak / PROM": df["Reason_PROM_Dribbling"].sum(),
        "PIH / Eclampsia": df["Reason_PIH_Eclampsia"].sum(),
        "Obstetric Hemorrhage": df["Reason_Hemorrhage"].sum(),
        "Fetal Distress / Cord": df["Reason_Fetal_Distress"].sum(),
        "Postterm / Macrosomia": df["Reason_Postterm_Macrosomia"].sum(),
    }
    danger_df = pd.DataFrame(list(danger_counts.items()), columns=["Trigger", "Count"]).sort_values("Count", ascending=True)
    sns.barplot(data=danger_df, x="Count", y="Trigger", palette="rocket", ax=axes[1, 1])
    axes[1, 1].set_title("D. Leading Documented Drivers of Higher Referral", fontsize=13, weight="bold")
    axes[1, 1].set_xlabel("Number of Cases")
    axes[1, 1].set_ylabel("")

    plt.tight_layout()
    fig1_path = os.path.join(out_dir, "maternal_risk_landscape.png")
    plt.savefig(fig1_path, dpi=300)
    plt.close()
    print(f"Generated Figure 1: {fig1_path}")

    # -------------------------------------------------------------
    # Figure 2: CDSS Decision Engine Performance & Triage Breakdown
    # -------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    # 2A: CDSS Triage Distribution
    triage_counts = eval_df["CDSS_Triage_Level"].value_counts()
    colors = {"GREEN": "#4CAF50", "YELLOW": "#FFB300", "RED": "#E53935"}
    ordered_levels = [lvl for lvl in ["GREEN", "YELLOW", "RED"] if lvl in triage_counts]
    axes[0].pie(
        [triage_counts[lvl] for lvl in ordered_levels],
        labels=[f"{lvl}\n({triage_counts[lvl]} pts, {triage_counts[lvl]/len(eval_df):.1%})" for lvl in ordered_levels],
        colors=[colors[lvl] for lvl in ordered_levels],
        autopct="%1.0f%%",
        startangle=140,
        wedgeprops=dict(width=0.45, edgecolor="white", linewidth=2),
    )
    axes[0].set_title("A. CDSS Rule Engine Risk Stratification (n=57)", fontsize=13, weight="bold")

    # 2B: Referral Concordance Confusion Matrix
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(eval_df["Actual_Referred"], eval_df["CDSS_Refer_Recommended"])
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        cbar=False,
        ax=axes[1],
        xticklabels=["CDSS Routine (Green)", "CDSS Refer (Yellow/Red)"],
        yticklabels=["Actual Local Delivery", "Actual Referred Out"],
    )
    axes[1].set_title("B. Clinical Referral Decision Concordance", fontsize=13, weight="bold")
    axes[1].set_ylabel("Actual Facility Event")
    axes[1].set_xlabel("CDSS Recommendation")

    plt.tight_layout()
    fig2_path = os.path.join(out_dir, "cdss_triage_flow.png")
    plt.savefig(fig2_path, dpi=300)
    plt.close()
    print(f"Generated Figure 2: {fig2_path}")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_dir, "data", "cleaned_matrisuraksha.csv")
    eval_path = os.path.join(base_dir, "reports", "cdss_cohort_evaluation.csv")
    out_dir = os.path.join(base_dir, "reports", "figures")
    generate_visual_reports(data_path, eval_path, out_dir)
