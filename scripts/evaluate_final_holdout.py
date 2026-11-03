"""One-time authorized evaluation of the saved, unchanged selected pipeline.

Use --preflight for validation-only checks. The authorization flag reserves an
exclusive run directory before test prediction. Never delete that directory to
rerun an exposed test. This script never calls fit, tunes, or changes a model.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import platform
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import pandas as pd
import sklearn
from src import config
from src.data_loading import load_csv, load_master_data
from src.data_validation import add_temporal_label_audit
from src.evaluation import classification_metrics, final_test_guard

RUN = ROOT / 'outputs/final_evaluation_2026-11-02'
MODEL = config.MODELS_DIR / 'random_forest.joblib'
FRAME = config.MODEL_READY_DIR / 'model_ready_supervised.csv'
SELECTION = config.METRICS_DIR / 'model_selection.json'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def preflight():
    if RUN.exists():
        raise FileExistsError(f'Final evaluation already reserved or completed: {RUN}. Reuse saved results; do not rerun.')
    selection = json.loads(SELECTION.read_text(encoding='utf-8'))
    if selection['selected_model'] != 'random_forest':
        raise ValueError('The authorized selected model must be the recorded random forest.')
    expected_versions = dict(line.strip().split('==', 1) for line in
        (config.REPORTS_DIR/'environment_versions.txt').read_text().splitlines())
    versions = dict(python=platform.python_version(), sklearn=sklearn.__version__,
                    pandas=pd.__version__, numpy=np.__version__, joblib=joblib.__version__)
    if any(expected_versions[key] != versions[key] for key in ['python','sklearn','joblib']):
        raise ValueError(f'Use the original training environment: {versions} != {expected_versions}')
    pipe = joblib.load(MODEL)
    metadata = json.loads((config.MODELS_DIR/'model_metadata.json').read_text())
    assert metadata['predictors'] == config.PREDICTORS == list(pipe.feature_names_in_)
    assert pipe.named_steps['model'].get_params() == metadata['models']['random_forest']
    assert list(pipe.classes_) == [0, 1]
    assert pipe.named_steps['model'].n_features_in_ == 31
    frame = load_csv(FRAME, target_nullable=True)
    audited = add_temporal_label_audit(load_master_data())
    expected = audited.loc[audited.label_temporally_valid, frame.columns].reset_index(drop=True)
    pd.testing.assert_frame_equal(frame.reset_index(drop=True), expected, check_dtype=False)
    assert len(frame)==4315 and not frame.duplicated(['cable_id','year']).any()
    assert not frame[config.PREDICTORS+[config.TARGET_COLUMN]].isna().any().any()
    partitions = {'train':frame[frame.year.isin(config.TRAIN_YEARS)],
                  'validation':frame[frame.year.isin(config.VALIDATION_YEARS)],
                  'final_test':frame[frame.year.eq(config.FINAL_TEST_YEAR)]}
    assert [len(partitions[k]) for k in partitions] == [2960,891,464]
    assert set(partitions['final_test'].year)=={2025}
    numeric = pipe.named_steps['preprocess'].named_transformers_['numeric']
    np.testing.assert_allclose(numeric.named_steps['imputer'].statistics_,
        partitions['train'][config.NUMERICAL_PREDICTORS].median().to_numpy())
    # Verify the frozen pipeline reproduces the recorded validation prediction,
    # never inspecting final-test predictions in preflight.
    val=partitions['validation']
    proba=pipe.predict_proba(val[config.PREDICTORS])
    pred=np.asarray(pipe.classes_)[np.argmax(proba,axis=1)]
    saved=pd.read_csv(config.TABLES_DIR/'validation_error_analysis.csv')
    assert list(saved.cable_id)==list(val.cable_id)
    np.testing.assert_array_equal(pred,saved.predicted.to_numpy())
    np.testing.assert_allclose(proba[:,1],saved.predicted_probability.to_numpy(),atol=1e-14,rtol=1e-12)
    observed=classification_metrics(val[config.TARGET_COLUMN],pred,proba[:,1])
    comparison=pd.read_csv(config.TABLES_DIR/'model_comparison_validation.csv')
    reference=comparison.loc[comparison.model.eq('random_forest')].iloc[0]
    for key,value in observed.items():
        np.testing.assert_allclose(value,float(reference[key]),atol=1e-14,rtol=1e-12)
    protected=[p for directory in ['UnderseaCableRisk','data','outputs/models']
               for p in (ROOT/directory).rglob('*') if p.is_file()]
    protected += [SELECTION,config.TABLES_DIR/'model_comparison_validation.csv',
                  config.TABLES_DIR/'validation_error_analysis.csv',Path(__file__),
                  ROOT/'src/config.py',ROOT/'src/preprocessing.py',ROOT/'src/evaluation.py']
    protocol=dict(selected_model='random_forest',model_path=str(MODEL.relative_to(ROOT)),
        model_sha256=sha(MODEL),predictors=list(config.PREDICTORS),
        parameters=pipe.named_steps['model'].get_params(),
        decision_rule='Saved classes [0,1]; argmax of predict_proba. Ties map to class 0, as in sklearn predict. No threshold adjustment.',
        train_years=config.TRAIN_YEARS,validation_years=config.VALIDATION_YEARS,
        final_test_predictor_year=2025,final_test_target_year=2026,
        metrics=['accuracy','precision','recall','f1','pr_auc','roc_auc','TN','FP','FN','TP'],
        pr_auc_definition='sklearn average_precision_score, not trapezoidal PR area',
        training_refit=False,hyperparameter_tuning=False,post_test_model_selection=False,
        versions=versions,recorded_training_versions=expected_versions,
        version_changes={key:dict(recorded=expected_versions[key],current=value)
                         for key,value in versions.items() if expected_versions[key]!=value},
        validation_reproduction_verified=True,
        protected_sha256={str(p.relative_to(ROOT)):sha(p) for p in protected},
        authorization='User reply: Authorize final evaluation of the frozen model',
        authorization_date_local='2026-11-02',authorization_timezone='Asia/Taipei')
    return pipe,partitions,protocol,observed


def evaluate():
    pipe,partitions,protocol,val_metrics=preflight()
    final_test_guard(allow=True)
    RUN.mkdir()  # Exclusive reservation; intentionally never overwritten/reused.
    (RUN/'frozen').mkdir()
    shutil.copy2(MODEL,RUN/'frozen/random_forest.joblib')
    shutil.copy2(SELECTION,RUN/'frozen/model_selection.json')
    shutil.copy2(config.MODELS_DIR/'model_metadata.json',RUN/'frozen/model_metadata.json')
    assert sha(RUN/'frozen/random_forest.joblib')==protocol['model_sha256']
    protocol['frozen_before_test_utc']=datetime.now(timezone.utc).isoformat()
    protocol['frozen_before_test_local']=datetime.now(timezone(timedelta(hours=8))).isoformat()
    protocol_path=RUN/'protocol.json'
    protocol_path.write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    (RUN/'evaluation_started.json').write_text(json.dumps(dict(
        protocol_sha256=sha(protocol_path),status='Reserved before final-test inference; never delete to rerun'),indent=2),encoding='utf-8')
    # Training diagnostics are not a refit. Validation metrics were verified above.
    train=partitions['train']
    train_prob=pipe.predict_proba(train[config.PREDICTORS])
    train_pred=np.asarray(pipe.classes_)[np.argmax(train_prob,axis=1)]
    train_metrics=classification_metrics(train[config.TARGET_COLUMN],train_pred,train_prob[:,1])
    final=partitions['final_test']
    probabilities=pipe.predict_proba(final[config.PREDICTORS])  # One final inference call.
    predictions=np.asarray(pipe.classes_)[np.argmax(probabilities,axis=1)]
    records=final[['cable_id','year',config.TARGET_COLUMN]].copy()
    records['predicted']=predictions
    records['predicted_probability']=probabilities[:,1]
    records['error_type']=np.select([
        (records.fault_next_year==0)&(predictions==0),
        (records.fault_next_year==0)&(predictions==1),
        (records.fault_next_year==1)&(predictions==0)],['TN','FP','FN'],default='TP')
    # Save exposed outcomes first. Future document builds read these, not the model.
    records.to_csv(RUN/'final_test_predictions.csv',index=False)
    final_metrics=classification_metrics(final[config.TARGET_COLUMN],predictions,probabilities[:,1])
    rows=[]
    for name,metrics in [('train',train_metrics),('validation',val_metrics),('final_test',final_metrics)]:
        part=partitions[name]
        rows.append(dict(partition=name,model='random_forest',rows=len(part),
            predictor_min_year=int(part.year.min()),predictor_max_year=int(part.year.max()),
            positives=int(part.fault_next_year.sum()),prevalence=float(part.fault_next_year.mean()),**metrics))
    pd.DataFrame(rows).to_csv(RUN/'partition_metrics.csv',index=False)
    assert all(sha(ROOT/p)==value for p,value in protocol['protected_sha256'].items())
    summary=dict(completed_at_utc=datetime.now(timezone.utc).isoformat(),
        status='completed_once',model_sha256=protocol['model_sha256'],
        protocol_sha256=sha(protocol_path),final_test=rows[-1],
        source_and_original_model_unchanged=True,refit=False,tuning=False,
        limitation='Publisher-declared computer-generated panel; no verified real-cable or operational claim.',
        artifact_sha256={p.name:sha(p) for p in RUN.glob('*.csv')})
    (RUN/'evaluation_record.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    (config.METRICS_DIR/'final_test_status.txt').write_text(
        'Completed authorized one-time final evaluation of the frozen random_forest pipeline on 2026-11-02.\n'
        'Evidence: outputs/final_evaluation_2026-11-02/evaluation_record.json\n'
        'Do not reselect, refit, retune or rerun this final test. Reuse saved predictions and metrics.\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--preflight',action='store_true')
    mode.add_argument('--authorize-final-evaluation',action='store_true')
    args=parser.parse_args()
    if args.preflight:
        _,_,protocol,_=preflight()
        print(json.dumps(protocol,indent=2))
    else:
        evaluate()
