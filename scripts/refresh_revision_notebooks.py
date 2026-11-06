"""Mechanically refresh the eight notebook wrappers for the revised evidence.

Each notebook runs read-only stages; complete development fitting is demonstrated
by check_reproduction.py in an isolated working copy, never on the final model.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SETUP="""from pathlib import Path
import sys
root = Path.cwd().resolve()
while not (root / 'src' / 'config.py').exists():
    if root.parent == root:
        raise RuntimeError('Open the notebook from the project or notebooks directory')
    root = root.parent
sys.path.insert(0, str(root))
import pandas as pd
from src import config
from src.data_loading import load_master_data
from src.data_validation import add_temporal_label_audit
revision = root / 'outputs/revisions/2026-11-05'
"""
NOTEBOOKS=[
 ('01_source_and_data_audit','Source and data audit','The accepted source is explicitly synthetic. This executes schema and value audits without writing source files.',"from src.data_validation import audit_master\nraw = load_master_data()\nsummary, gaps, target, variables = audit_master(raw)\ndisplay(summary)\ndisplay(gaps)\ndisplay(pd.DataFrame(raw.attrs['numeric_parsing_audit']))"),
 ('02_data_cleaning','Cleaning and temporal exclusions','This executes cleaning in memory. The original and excluded rows remain auditable; no file is overwritten.',"from scripts.run_pipeline import clean_data\nraw = load_master_data()\ncleaned = clean_data(add_temporal_label_audit(raw))\nassert len(cleaned) == 4821\ndisplay(cleaned.groupby('exclusion_reason', dropna=False).size().rename('rows'))\ndisplay(pd.read_csv(revision / 'record_reconciliation.csv'))"),
 ('03_exploratory_analysis','Development exploratory analysis','These saved summaries describe synthetic cable-years through 2024, not measured global infrastructure or fault rates.',"display(pd.read_csv(root / 'outputs/tables/eda/descriptive_statistics.csv'))\nfor field in ['ocean_route','operator_type','chokepoint']:\n    display(pd.read_csv(root / f'outputs/tables/eda/{field}_summary.csv', keep_default_na=False))\ndisplay(pd.read_csv(revision / 'annual_panel_coverage.csv'))"),
 ('04_statistical_analysis','Development association analysis','Executes the revised 13-test family on eligible development records. Ordinary p-values remain exploratory under repeated observations.',"from src.revision_analysis import association_report, cable_level_sensitivity\nframe = add_temporal_label_audit(load_master_data())\ndevelopment = frame[frame.label_temporally_valid & frame.year.le(2024)]\nnumeric, categorical = association_report(development)\ndisplay(numeric)\ndisplay(categorical)\nids, one_numeric, one_categorical = cable_level_sensitivity(development)\ndisplay(one_numeric)\ndisplay(one_categorical)"),
 ('05_feature_preparation','Training-only feature preparation','Only the preprocessing transformer is fitted here. No classifier, threshold, raw record or final result is changed.',"from src.preprocessing import build_preprocessor\nframe = add_temporal_label_audit(load_master_data())\ntrain = frame[frame.label_temporally_valid & frame.year.isin(config.TRAIN_YEARS)]\ntransformer = build_preprocessor()\nprepared = transformer.fit_transform(train[config.PREDICTORS])\nassert prepared.shape == (2960, 31)\ndisplay(pd.DataFrame({'numeric_input':config.NUMERICAL_PREDICTORS,'training_median':transformer.named_transformers_['numeric'].named_steps['imputer'].statistics_}))\nprint('Prepared training shape:', prepared.shape)"),
 ('06_model_development','Recorded candidate development results','Reads the four saved candidates and their fixed settings. Full development reproduction runs separately in a fresh working copy using scripts/check_reproduction.py.',"import json\ndisplay(pd.read_csv(root / 'outputs/tables/model_comparison_validation.csv'))\ndisplay(pd.read_csv(revision / 'expanding_window_folds.csv'))\nprint(json.loads((root / 'outputs/models/model_metadata.json').read_text())['models'])\ndisplay(pd.read_csv(root / 'outputs/tables/indicator_analysis/indicator_block_validation.csv'))"),
 ('07_model_evaluation','Completed frozen evaluation evidence','The final evaluation was completed once on 2 November 2026 with project-owner authorization. Instructor treatment of that sequence remains consultation. This notebook reads saved evidence and NEVER scores a model.',"import json\nfinal = root / 'outputs/final_evaluation_2026-11-02'\nrecord = json.loads((final / 'evaluation_record.json').read_text())\nassert record['status'] == 'completed_once'\ndisplay(pd.read_csv(final / 'partition_metrics.csv'))\nprint('Saved final confusion counts:', {k:record['final_test'][k] for k in ['TN','FP','FN','TP']})\nprint('No fit, model load, threshold selection or final inference occurred.')"),
 ('08_final_analysis','Revision interpretation and response','Supplementary development diagnostics do not replace the original selection or provide a fresh final test. Records distinguish implementation, group review and instructor decisions.',"import json\nfor name in ['validation_cluster_bootstrap.csv','validation_subgroup_errors.csv','original_predictor_importance.csv','validation_permutation_importance.csv']:\n    display(pd.read_csv(revision / name))\nprint(json.loads((revision / 'clean_copy_reproduction.json').read_text()))\ndisplay(pd.read_csv(root / 'docs/revisions/2026-11-05/compliance_matrix.csv').groupby('status').size())")]


def main():
    for name,title,explanation,code in NOTEBOOKS:
        path=ROOT/'notebooks'/(name+'.ipynb')
        notebook=json.loads(path.read_text(encoding='utf-8-sig'))
        notebook['cells']=[dict(id='stage-description',cell_type='markdown',metadata={},source=[f'# {title}\n',explanation]),
                           dict(id='stage-code',cell_type='code',execution_count=None,metadata={},outputs=[],source=(SETUP+'\n'+code).splitlines(keepends=True))]
        path.write_text(json.dumps(notebook,indent=1,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Refreshed eight read-only research notebooks; no code executed or model evaluated.')


if __name__=='__main__':main()
