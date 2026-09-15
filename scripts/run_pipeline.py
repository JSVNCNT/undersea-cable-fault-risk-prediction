"""Run all safe development-stage analysis steps.

The final 2025 holdout is summarized but never scored unless an explicit,
separate authorization flag is supplied to a future final-term run.
"""
from __future__ import annotations
import hashlib, json, platform, sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from src import config
from src.data_loading import load_all_raw_data, load_master_data
from src.data_validation import audit_master, add_temporal_label_audit
from src.preprocessing import chronological_split, make_model_frame, split_summary
from src.statistics import categorical_associations, numeric_comparisons
from src.modeling import fit_and_compare, select_model
from src.visualization import make_eda_figures

def sha256(path: Path) -> str:
    h=hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest().upper()

def write_csv(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True); frame.to_csv(path, index=False)

def clean_data(audited: pd.DataFrame) -> pd.DataFrame:
    out = audited[audited["label_temporally_valid"]].copy()
    out["chokepoint"] = out["chokepoint"].astype(str).replace({"": "None"})
    out["fault_next_year"] = out["fault_next_year"].astype(int)
    return out

def build_dictionary(raw, cleaned):
    source_dict = load_all_raw_data()["dictionary"].rename(columns={"column":"variable"})
    rows=[]
    for col in raw.columns:
        s=raw[col]; supplied = source_dict.loc[source_dict.variable==col,"description"]
        note = ""
        role = "identifier" if col=="cable_id" else ("target" if col==config.TARGET_COLUMN else "predictor/audit")
        inclusion = "excluded"; leakage="none identified"
        if col in config.PREDICTORS: inclusion="primary predictor"
        if col in {"design_life_years","is_low_redundancy","rfs_year","vulnerability_index","fault_cause"}: inclusion="excluded"
        if col=="design_life_years": note="Constant at 25; retained for audit, excluded from predictors."
        if col=="is_low_redundancy": note="Verified equivalent to route_redundancy < 40; excluded when continuous feature retained."
        if col=="chokepoint": note='Literal category "None" is valid and not missing.'
        if col=="fault_cause": leakage="May encode contemporaneous fault mechanism; excluded."
        rows.append({"variable":col,"description": supplied.iloc[0] if len(supplied) else "Verified from source audit.","dtype":str(s.dtype),"role":role,"units":"as supplied","allowed_observed_values":str(sorted(s.dropna().astype(str).unique())[:30]),"missing_count":int(s.isna().sum()),"valid_range":f"{s.min()} to {s.max()}" if pd.api.types.is_numeric_dtype(s) else "categorical","source":"undersea_cables_master.csv","derived_status":"derived" if col in {"age_years","route_redundancy","is_low_redundancy"} else "source field","planned_treatment":"retain/audit" if inclusion!="excluded" else "exclude from primary model","predictor_inclusion_status":inclusion,"leakage_concern":leakage,"limitation_note":note})
    return pd.DataFrame(rows)

def main():
    config.ensure_directories()
    raw = load_all_raw_data(); master = raw["master"]
    summary, gaps, target_dist, variable = audit_master(master)
    audited = add_temporal_label_audit(master)
    write_csv(summary, config.TABLES_DIR/"raw_data_quality_summary.csv")
    write_csv(gaps, config.TABLES_DIR/"temporal_gap_audit.csv")
    write_csv(target_dist, config.TABLES_DIR/"target_distribution_raw.csv")
    write_csv(variable, config.TABLES_DIR/"variable_audit.csv")
    unresolved = audited[audited[config.TARGET_COLUMN].notna() & ~audited["label_temporally_valid"]]
    write_csv(unresolved, config.INTERIM_DIR/"temporally_unresolved_labels.csv")
    clean = clean_data(audited)
    write_csv(clean.drop(columns=["next_observed_year","has_consecutive_next_year","label_temporally_valid"]), config.PROCESSED_DIR/"undersea_cables_cleaned.csv")
    write_csv(pd.DataFrame([{"action":"Excluded six temporally unresolved labeled predecessors; preserved in data/interim/temporally_unresolved_labels.csv","rows_before":len(master),"rows_after":len(clean),"literal_None_preserved":int((clean.chokepoint=='None').sum())}]), config.TABLES_DIR/"cleaning_summary.csv")
    write_csv(pd.DataFrame([{"raw_rows":len(master),"cleaned_rows":len(clean),"raw_columns":len(master.columns),"cleaned_columns":len(master.columns)}]), config.TABLES_DIR/"raw_vs_cleaned_summary.csv")
    write_csv(pd.DataFrame([{"variable":"cable_id","reason":"identifier/grouping only"},{"variable":"design_life_years","reason":"constant"},{"variable":"is_low_redundancy","reason":"deterministic duplicate of route_redundancy"},{"variable":"rfs_year","reason":"redundant with year and age_years"},{"variable":"vulnerability_index","reason":"construction not verifiable; sensitivity only"},{"variable":"fault_cause","reason":"potential contemporaneous leakage"}]), config.TABLES_DIR/"excluded_predictors.csv")
    write_csv(build_dictionary(master, clean), config.TABLES_DIR/"final_data_dictionary.csv")
    # EDA artifacts
    eda = clean.copy(); write_csv(eda.describe(include="all").transpose().reset_index().rename(columns={"index":"variable"}), config.TABLES_DIR/"eda"/"descriptive_statistics.csv")
    for col in ["ocean_route","operator_type","chokepoint"]:
        counts=eda[col].value_counts(dropna=False).rename_axis(col).reset_index(name="count"); counts["proportion"]=counts["count"]/len(eda); write_csv(counts, config.TABLES_DIR/"eda"/(f"{col}_summary.csv"))
    make_eda_figures(eda, config.FIGURES_DIR/"eda")
    # statistics
    write_csv(categorical_associations(clean), config.TABLES_DIR/"statistics"/"categorical_associations.csv")
    write_csv(numeric_comparisons(clean), config.TABLES_DIR/"statistics"/"numeric_comparisons.csv")
    write_csv(pd.DataFrame([{"check":"All inferential tests are non-causal; repeated observations noted as limitation","status":"documented"}]), config.TABLES_DIR/"statistics"/"assumption_checks.csv")
    try:
        import statsmodels.formula.api as smf
        formula = "fault_next_year ~ C(ocean_route) + C(operator_type) + age_years + fiber_pairs + length_km + n_landing_countries + C(chokepoint) + design_capacity_tbps + lit_capacity_tbps + utilization_pct + protected_burial + route_redundancy + fault_this_year"
        fit = smf.logit(formula, data=clean).fit(disp=False, cov_type="cluster", cov_kwds={"groups": clean[config.ID_COLUMN]})
        ci = fit.conf_int(); assoc = pd.DataFrame({"term":fit.params.index,"coefficient":fit.params.values,"standard_error":fit.bse.values,"odds_ratio":__import__("numpy").exp(fit.params.values),"ci_low":__import__("numpy").exp(ci[0].values),"ci_high":__import__("numpy").exp(ci[1].values),"p_value":fit.pvalues.values})
    except Exception as exc:
        assoc = pd.DataFrame([{"term":"model_fit","coefficient":None,"standard_error":None,"odds_ratio":None,"ci_low":None,"ci_high":None,"p_value":None,"note":f"Association model unavailable: {exc}"}])
    write_csv(assoc, config.TABLES_DIR/"statistics"/"logistic_association_results.csv")
    # model data and partitions
    model = make_model_frame(clean); write_csv(model, config.MODEL_READY_DIR/"model_ready_supervised.csv")
    write_csv(pd.DataFrame([{"feature":f,"role":"predictor","type":"categorical" if f in config.CATEGORICAL_PREDICTORS else "numeric","included":True} for f in config.PREDICTORS]), config.TABLES_DIR/"predictor_manifest.csv")
    splits=chronological_split(model); write_csv(split_summary(splits), config.TABLES_DIR/"data_split_summary.csv")
    comparison, fitted = fit_and_compare(splits["train"], splits["validation"])
    write_csv(comparison, config.TABLES_DIR/"model_comparison_validation.csv")
    selected=select_model(comparison)
    selection={"selected_model":selected,"selection_date":datetime.now(timezone.utc).isoformat(),"development_partitions":"train 2015-2022; validation 2023-2024","primary_metric":"PR-AUC / average precision due to 18.98% positive prevalence","supporting_metrics":["recall","precision","F1","ROC-AUC","confusion matrix"],"interpretability_consideration":"Prefer simpler model for ties; compare coefficient/tree/importance artifacts.","overfitting_consideration":"Final test not accessed; validation-only comparison.","limitations":"Results describe the supplied synthetic dataset and are not real-world cable evidence."}
    (config.METRICS_DIR).mkdir(exist_ok=True); (config.METRICS_DIR/"model_selection.json").write_text(json.dumps(selection,indent=2),encoding="utf-8")
    (config.MODELS_DIR/"model_metadata.json").write_text(json.dumps({"random_seed": config.RANDOM_SEED, "predictors": config.PREDICTORS, "categorical_predictors": config.CATEGORICAL_PREDICTORS, "numeric_predictors": config.NUMERICAL_PREDICTORS, "models": {n: fitted[n].named_steps["model"].get_params() for n in fitted}}, indent=2, default=str), encoding="utf-8")
    # validation error analysis for selected model
    val=splits["validation"]; pipe=fitted[selected]; pred=pipe.predict(val[config.PREDICTORS]); prob=pipe.predict_proba(val[config.PREDICTORS])[:,1]
    errors=val[[config.ID_COLUMN,config.YEAR_COLUMN,config.TARGET_COLUMN]].copy(); errors["predicted"]=pred; errors["predicted_probability"]=prob; errors["error_type"]=errors.apply(lambda r: "TN" if r[config.TARGET_COLUMN]==0 and r.predicted==0 else "FP" if r[config.TARGET_COLUMN]==0 else "FN" if r.predicted==0 else "TP",axis=1); write_csv(errors, config.TABLES_DIR/"validation_error_analysis.csv")
    interp_dir = config.TABLES_DIR / "model_interpretation"
    # Save transparent, model-specific interpretation artifacts.
    try:
        feature_names = fitted["logistic_regression"].named_steps["preprocess"].get_feature_names_out()
        coef = fitted["logistic_regression"].named_steps["model"].coef_[0]
        write_csv(pd.DataFrame({"feature": feature_names, "coefficient": coef, "odds_ratio": __import__("numpy").exp(coef), "direction": ["positive" if x > 0 else "negative" for x in coef]}).sort_values("coefficient", key=lambda s: s.abs(), ascending=False), interp_dir/"logistic_coefficients.csv")
    except Exception:
        pass
    for model_name in ["decision_tree", "random_forest"]:
        est = fitted[model_name].named_steps["model"]
        names = fitted[model_name].named_steps["preprocess"].get_feature_names_out()
        write_csv(pd.DataFrame({"feature": names, "importance": est.feature_importances_}).sort_values("importance", ascending=False), interp_dir/f"{model_name}_feature_importance.csv")
    write_csv(errors.groupby(["year", "error_type"]).size().rename("count").reset_index(), config.TABLES_DIR/"robustness_by_validation_year.csv")
    (config.METRICS_DIR/"final_test_status.txt").write_text("Final test evaluation is locked. Enable only for authorized Final-Term evaluation after model selection is frozen.\n", encoding="utf-8")
    # metadata and governance outputs
    versions=[]
    for pkg in ["pandas","numpy","scipy","sklearn","statsmodels","matplotlib","joblib"]:
        try:
            mod=__import__(pkg); versions.append(f"{pkg}=={getattr(mod,'__version__','unknown')}")
        except Exception: pass
    versions.insert(0,f"python=={platform.python_version()}"); (config.REPORTS_DIR/"environment_versions.txt").write_text("\n".join(versions)+"\n",encoding="utf-8")
    source=(ROOT/"docs/source_record/dataset_source_record.md"); source.parent.mkdir(parents=True,exist_ok=True); source.write_text(f"""# Dataset source record\n\n- Title: Undersea Cables and Global Digital Infrastructure\n- Kaggle: https://www.kaggle.com/datasets/sergionefedov/undersea-cables-and-global-digital-infrastructure\n- Handle: sergionefedov\n- Access date: 2026-09-16\n- License: CC0 (Public Domain)\n- Status: 100% synthetic, procedurally generated with a fixed seed; not authenticated real cable measurements.\n- Files: undersea_cables_master.csv, cables_reference.csv, data_dictionary.csv\n- Unit: one cable-year observation; coverage 2015-2026; master rows {len(master)}.\n- SHA-256 master: {sha256(config.MASTER_PATH)}\n- SHA-256 reference: {sha256(config.REFERENCE_PATH)}\n- SHA-256 dictionary: {sha256(config.DICTIONARY_PATH)}\n- Synthetic dataset instructor status: PENDING EXPLICIT CONFIRMATION\n- Redistribution note: CC0 permits reuse; retain accurate attribution and do not imply endorsement.\n- Limitations: six temporally unresolved labels are excluded from supervised analysis; external empirical validation is required before any operational use.\n""",encoding="utf-8")
    dq=ROOT/"docs/data_quality/data_quality_report.md"; dq.parent.mkdir(parents=True,exist_ok=True); dq.write_text(f"""# Data quality report\n\nThe source contains **{len(master):,} rows**, **{len(master.columns)} variables**, **{master.cable_id.nunique()} cables**, and years **{master.year.min()}–{master.year.max()}**. There are {master.fault_next_year.notna().sum():,} labeled rows ({(master.fault_next_year==1).sum():,} positive; {(master.fault_next_year==0).sum():,} negative) and {len(clean):,} temporally eligible supervised rows after excluding six unresolved predecessors.\n\n- Exact duplicate rows: {master.duplicated().sum()}; duplicate cable-year keys: {master.duplicated(['cable_id','year']).sum()}.\n- `chokepoint` literal `None` count: {(master.chokepoint=='None').sum():,}; these are valid categorical values, not nulls.\n- `design_life_years` is constant; `is_low_redundancy` equals `route_redundancy < 40`.\n- Unresolved labels are preserved in `data/interim/temporally_unresolved_labels.csv`; see `outputs/tables/temporal_gap_audit.csv`.\n- The dataset is synthetic; no result should be interpreted as evidence about real submarine cables.\n\nReproducible summaries: `outputs/tables/raw_data_quality_summary.csv`, `cleaning_summary.csv`, `raw_vs_cleaned_summary.csv`, `final_data_dictionary.csv`.\n""",encoding="utf-8")
    trace=pd.DataFrame([{"research_question":"RQ1","evidence":"EDA descriptive_statistics.csv and outputs/figures/eda","artifacts":"03_exploratory_analysis.ipynb"},{"research_question":"RQ2","evidence":"statistics/categorical_associations.csv; numeric_comparisons.csv","artifacts":"04_statistical_analysis.ipynb"},{"research_question":"RQ3","evidence":"model_comparison_validation.csv","artifacts":"06_model_development.ipynb"},{"research_question":"RQ4","evidence":"model_selection.json; validation_error_analysis.csv","artifacts":"07_model_evaluation.ipynb"}]); write_csv(trace,config.TABLES_DIR/"research_question_traceability.csv")
    manifest=[]
    for p in [config.TABLES_DIR/"raw_data_quality_summary.csv",config.TABLES_DIR/"model_comparison_validation.csv",config.METRICS_DIR/"model_selection.json",config.PROCESSED_DIR/"undersea_cables_cleaned.csv"]:
        manifest.append({"artifact":str(p.relative_to(ROOT)),"type":p.suffix.lstrip('.'),"stage":"development","source_notebook_or_script":"scripts/run_pipeline.py","research_question":"RQ1-RQ4","description":"Generated reproducible artifact","generated_at":datetime.now(timezone.utc).isoformat(),"status":"generated"})
    write_csv(pd.DataFrame(manifest),config.REPORTS_DIR/"artifact_manifest.csv")
    print(f"Safe pipeline complete. Cleaned rows: {len(clean)}; selected model: {selected}. Final test evaluation is locked. Unresolved labels: {len(unresolved)}.")

if __name__ == "__main__": main()
