# Data quality report

The source contains **4,821 rows**, **21 variables**, **500 cables**, and years **2015–2026**. There are 4,321 labeled rows (820 positive; 3,501 negative) and 4,315 temporally eligible supervised rows after excluding six unresolved predecessors.

- Exact duplicate rows: 0; duplicate cable-year keys: 0.
- `chokepoint` literal `None` count: 3,986; these are valid categorical values, not nulls.
- `design_life_years` is constant; `is_low_redundancy` equals `route_redundancy < 40`.
- Unresolved labels are preserved in `data/interim/temporally_unresolved_labels.csv`; see `outputs/tables/temporal_gap_audit.csv`.
- The dataset is synthetic; no result should be interpreted as evidence about real submarine cables.

Reproducible summaries: `outputs/tables/raw_data_quality_summary.csv`, `cleaning_summary.csv`, `raw_vs_cleaned_summary.csv`, `final_data_dictionary.csv`.
