"""
MatriSuraksha - Machine Learning Predictive Modeling & Feature Importance
Trains and evaluates baseline referral risk models using Scikit-Learn:
- Logistic Regression (with Odds Ratios)
- Random Forest Classifier (Feature Importances)
- Decision Tree Classifier (Interpretable Clinical Rules)
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.metrics import (
    roc_auc_score,
    accuracy_score,
    recall_score,
    precision_score,
    f1_score,
    confusion_matrix,
    classification_report,
)
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


def prepare_ml_data(feature_matrix_path):
    df = pd.read_csv(feature_matrix_path)
    
    # Target variable
    y = df["Referred_Target"].values
    
    # Candidate predictor features (clinical & demographic)
    candidate_cols = [
        "Age",
        "Is_Teenage",
        "Is_BPL",
        "Is_ST_SC",
        "Gravida_Num",
        "Is_Primigravida",
        "Parity_Live",
        "Gestational_Age",
        "Is_Preterm",
        "ANC_Visits",
        "Inadequate_ANC",
        "Has_Previous_Complications",
        "Hemoglobin",
        "Has_Anemia",
        "Has_Moderate_Severe_Anemia",
        "Systolic_BP",
        "Diastolic_BP",
        "Is_Hypertensive",
        "Fetal_Heart_Rate",
        "Has_ROM",
    ]
    
    # Keep only columns that exist
    features = [c for c in candidate_cols if c in df.columns]
    X = df[features].copy()
    
    return df, X, y, features


def train_and_evaluate_models(X, y, feature_names, out_dir):
    print("=" * 60)
    print("MATRISURAKSHA: BASELINE ML MODEL TRAINING & EVALUATION")
    print("=" * 60)
    print(f"Total Cohort Size: {len(y)} | Positives (Referred): {sum(y)} ({sum(y)/len(y):.1%})")
    
    # Define Classifiers
    models = {
        "Logistic Regression": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(class_weight="balanced", random_state=42, max_iter=1000)),
        ]),
        "Random Forest": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("clf", RandomForestClassifier(n_estimators=100, class_weight="balanced", max_depth=4, random_state=42)),
        ]),
        "Decision Tree": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("clf", DecisionTreeClassifier(class_weight="balanced", max_depth=3, min_samples_leaf=3, random_state=42)),
        ]),
    }
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scoring = ["roc_auc", "accuracy", "recall", "precision", "f1"]
    
    results = []
    
    for name, pipeline in models.items():
        cv_res = cross_validate(pipeline, X, y, cv=cv, scoring=scoring, return_train_score=False)
        
        # Fit on full data to inspect parameters/features
        pipeline.fit(X, y)
        y_pred = pipeline.predict(X)
        y_prob = pipeline.predict_proba(X)[:, 1] if hasattr(pipeline.named_steps["clf"], "predict_proba") else y_pred
        
        res_row = {
            "Model": name,
            "CV ROC-AUC (Mean)": np.mean(cv_res["test_roc_auc"]),
            "CV ROC-AUC (Std)": np.std(cv_res["test_roc_auc"]),
            "CV Recall (Mean)": np.mean(cv_res["test_recall"]),
            "CV Precision (Mean)": np.mean(cv_res["test_precision"]),
            "CV F1 (Mean)": np.mean(cv_res["test_f1"]),
            "Full Dataset AUC": roc_auc_score(y, y_prob),
            "Full Dataset Recall": recall_score(y, y_pred),
            "Full Dataset Precision": precision_score(y, y_pred, zero_division=0),
        }
        results.append(res_row)
        
        # Save model
        model_file = os.path.join(out_dir, f"{name.lower().replace(' ', '_')}.joblib")
        joblib.dump(pipeline, model_file)
        
    res_df = pd.DataFrame(results)
    print("\n--- Cross-Validation Model Performance (5-Fold CV) ---")
    print(res_df.to_string(index=False))
    
    # Save performance summary
    res_df.to_csv(os.path.join(out_dir, "model_performance_summary.csv"), index=False)
    
    # Feature Importances from Random Forest
    rf_pipeline = models["Random Forest"]
    rf_clf = rf_pipeline.named_steps["clf"]
    importances = pd.DataFrame({
        "Feature": feature_names,
        "Importance": rf_clf.feature_importances_,
    }).sort_values(by="Importance", ascending=False)
    
    print("\n--- Random Forest Feature Importances ---")
    print(importances.head(10).to_string(index=False))
    importances.to_csv(os.path.join(out_dir, "rf_feature_importances.csv"), index=False)
    
    # Logistic Regression Coefficients (Odds Ratios)
    lr_pipeline = models["Logistic Regression"]
    lr_clf = lr_pipeline.named_steps["clf"]
    lr_coeffs = pd.DataFrame({
        "Feature": feature_names,
        "Coefficient": lr_clf.coef_[0],
        "Odds_Ratio": np.exp(lr_clf.coef_[0]),
    }).sort_values(by="Odds_Ratio", ascending=False)
    
    print("\n--- Logistic Regression Top Odds Ratios ---")
    print(lr_coeffs.head(10).to_string(index=False))
    lr_coeffs.to_csv(os.path.join(out_dir, "logistic_odds_ratios.csv"), index=False)
    
    # Decision Tree Rule Export
    dt_pipeline = models["Decision Tree"]
    dt_clf = dt_pipeline.named_steps["clf"]
    tree_rules = export_text(dt_clf, feature_names=feature_names)
    print("\n--- Interpretable Clinical Decision Tree Rules ---")
    print(tree_rules)
    with open(os.path.join(out_dir, "decision_tree_rules.txt"), "w") as f:
        f.write(tree_rules)
        
    return res_df, importances, lr_coeffs


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    feat_path = os.path.join(base_dir, "data", "feature_matrix.csv")
    out_dir = os.path.join(base_dir, "models")
    os.makedirs(out_dir, exist_ok=True)
    
    df, X, y, features = prepare_ml_data(feat_path)
    train_and_evaluate_models(X, y, features, out_dir)
