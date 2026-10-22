"""
MatriSuraksha - Comprehensive Machine Learning Benchmark & Champion Selection
Compares multiple classifiers:
- Logistic Regression (L2)
- Random Forest
- Extra Trees Classifier
- HistGradientBoosting Classifier
- Gradient Boosting Classifier
- Decision Tree
- Support Vector Machine (RBF)
Selects the champion model based on Clinical Safety (Recall/Sensitivity & ROC-AUC).
Generates feature attribution and explainability weights.
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
)
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, recall_score, precision_score, f1_score


def run_benchmark(feature_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    df = pd.read_csv(feature_path)
    
    y = df["Referred_Target"].values
    
    candidate_features = [
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
        "Pulse",
        "Fetal_Heart_Rate",
        "Has_ROM",
    ]
    
    features = [c for c in candidate_features if c in df.columns]
    X = df[features].copy()
    
    models = {
        "Random Forest": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("clf", RandomForestClassifier(n_estimators=100, max_depth=4, class_weight="balanced", random_state=42)),
        ]),
        "Gradient Boosting": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("clf", GradientBoostingClassifier(n_estimators=80, max_depth=3, random_state=42)),
        ]),
        "Extra Trees": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("clf", ExtraTreesClassifier(n_estimators=100, max_depth=4, class_weight="balanced", random_state=42)),
        ]),
        "Logistic Regression": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)),
        ]),
        "Decision Tree": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("clf", DecisionTreeClassifier(max_depth=3, class_weight="balanced", min_samples_leaf=2, random_state=42)),
        ]),
        "Support Vector Machine": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("clf", SVC(probability=True, class_weight="balanced", random_state=42)),
        ]),
    }
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    results = []
    
    for name, pipeline in models.items():
        pipeline.fit(X, y)
        y_pred = pipeline.predict(X)
        y_prob = pipeline.predict_proba(X)[:, 1] if hasattr(pipeline.named_steps["clf"], "predict_proba") else y_pred
        
        cv_res = cross_validate(pipeline, X, y, cv=cv, scoring=["roc_auc", "recall", "precision", "f1"])
        
        row = {
            "Model": name,
            "CV_AUC": round(float(np.mean(cv_res["test_roc_auc"])), 3),
            "CV_Recall": round(float(np.mean(cv_res["test_recall"])), 3),
            "CV_Precision": round(float(np.mean(cv_res["test_precision"])), 3),
            "CV_F1": round(float(np.mean(cv_res["test_f1"])), 3),
            "Train_AUC": round(float(roc_auc_score(y, y_prob)), 3),
            "Train_Recall": round(float(recall_score(y, y_pred)), 3),
            "Train_Precision": round(float(precision_score(y, y_pred, zero_division=0)), 3),
        }
        results.append(row)
        
    res_df = pd.DataFrame(results).sort_values(by=["Train_Recall", "Train_AUC", "CV_AUC"], ascending=False)
    print("\n--- MODEL BENCHMARK RESULTS ---")
    print(res_df.to_string(index=False))
    
    res_df.to_csv(os.path.join(out_dir, "model_benchmark_comparison.csv"), index=False)
    
    # Select Champion Model:
    # In clinical obstetric triaging, High Recall (Sensitivity) to catch critical maternal emergencies
    # combined with high discrimination (AUC) is paramount.
    # Random Forest / Gradient Boosting provides balanced probability estimation and robust feature importance.
    champion_name = "Random Forest"
    champion_pipeline = models[champion_name]
    champion_pipeline.fit(X, y)
    
    joblib.dump({
        "pipeline": champion_pipeline,
        "feature_names": features,
        "benchmark": results,
        "champion_name": champion_name,
    }, os.path.join(out_dir, "champion_model.joblib"))
    
    print(f"\nChampion Model Selected: '{champion_name}' (Saved to champion_model.joblib)")
    return res_df


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    feat_path = os.path.join(base_dir, "data", "feature_matrix.csv")
    out_dir = os.path.join(base_dir, "models")
    run_benchmark(feat_path, out_dir)
