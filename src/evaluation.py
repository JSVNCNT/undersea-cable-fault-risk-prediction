from typing import Any, Dict
import numpy as np
from sklearn.metrics import (accuracy_score, average_precision_score, confusion_matrix,
                             f1_score, precision_score, recall_score, roc_auc_score)

def classification_metrics(y_true, y_pred, y_prob=None) -> Dict[str, Any]:
    y_true = np.asarray(y_true).astype(int); y_pred = np.asarray(y_pred).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    result = {"accuracy": float(accuracy_score(y_true, y_pred)),
              "precision": float(precision_score(y_true, y_pred, zero_division=0)),
              "recall": float(recall_score(y_true, y_pred, zero_division=0)),
              "f1": float(f1_score(y_true, y_pred, zero_division=0)),
              "TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp)}
    if y_prob is None:
        result.update({"roc_auc": np.nan, "pr_auc": np.nan})
    else:
        try: result["roc_auc"] = float(roc_auc_score(y_true, y_prob))
        except ValueError: result["roc_auc"] = np.nan
        try: result["pr_auc"] = float(average_precision_score(y_true, y_prob))
        except ValueError: result["pr_auc"] = np.nan
    return result

def evaluate_pipeline(model, X, y) -> Dict[str, Any]:
    pred = model.predict(X)
    prob = model.predict_proba(X)[:, 1] if hasattr(model, "predict_proba") else None
    return classification_metrics(y, pred, prob)

def final_test_guard(allow: bool = False) -> None:
    if not allow:
        raise PermissionError("Final test evaluation is locked. Enable only for authorized Final-Term evaluation after model selection is frozen.")

