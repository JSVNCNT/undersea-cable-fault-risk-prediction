# Predicting Next-Year Fault Occurrence in Global Undersea Cable Systems

**Introduction to Data Science — COPE0683X**  
**Section:** K44

## Project Overview

This repository contains the code, notebooks, documentation, and reproducible analytical workflow for the research project:

> **Predicting Next-Year Fault Occurrence in Global Undersea Cable Systems Using Infrastructure and Operational Indicators**

The project investigates whether infrastructure and operational information available at the end of an observation year can distinguish cable-year records that experience a fault in the following year from those that do not.

The study is designed as a data-science classification project, not an engineering-diagnosis or operational warning system.

## Dataset Source

The working dataset is **Undersea Cables and Global Digital Infrastructure**, obtained from Kaggle:

- **Kaggle dataset:**  
  https://www.kaggle.com/datasets/sergionefedov/undersea-cables-and-global-digital-infrastructure
- **Dataset page account/handle:** `sergionefedov`

### Supplied Files

- `undersea_cables_master.csv`
- `cables_reference.csv`
- `data_dictionary.csv`

### Dataset Summary

- Observation period: 2015–2026
- Unit of analysis: one cable-year observation
- Master-file observations: 4,821
- Unique cable identifiers: 500
- Variables: 21
- Initially labeled observations: 4,321
- Positive next-year fault labels: 820
- Negative next-year fault labels: 3,501
- Target variable: `fault_next_year`

`fault_next_year = 1` indicates that a fault occurs in the following observed cable-year, while `0` indicates no following-year fault.

The final observation for each cable has no forward label and is excluded from supervised model training and evaluation while being preserved separately.

## Important Source-Verification Note

The supplied data dictionary describes `cable_id` as a **synthetic cable system ID**.

The supplied files do not identify a separate upstream empirical owner or custodian. Before the dataset is presented as real-world evidence, the group must verify whether only the identifiers are pseudonymized or whether the observations themselves are simulated.

The exact Kaggle license/permitted-use statement and upstream provenance must also be recorded before making real-world claims.

Because this repository is public, raw dataset files should only be committed if the dataset license permits redistribution.

## Research Questions

1. What are the distributions and operational characteristics of the cable-year observations?
2. Which selected infrastructure and operational variables are statistically associated with `fault_next_year` without interpreting those associations as causal effects?
3. How well do a majority-class baseline, logistic regression, decision tree, and random forest predict next-year fault occurrence using only information available before the held-out prediction year?
4. Which candidate model provides the most appropriate balance of predictive performance, stability, interpretability, and fault-class detection?

## Planned Analytical Workflow

1. Preserve and document the original source files.
2. Audit data types, ranges, duplicates, missing values, and data quality.
3. Verify the forward target and prediction timing.
4. Audit derived variables for possible data leakage.
5. Perform exploratory data analysis and statistical association testing.
6. Prepare categorical and numeric predictors using reproducible preprocessing pipelines.
7. Train a majority-class baseline.
8. Train and tune candidate classification models.
9. Evaluate all models on chronologically held-out data.
10. Interpret results, errors, uncertainty, limitations, and responsible-use boundaries.

## Planned Models

### Majority-Class Baseline

A `DummyClassifier` will provide the minimum benchmark by predicting the most common class.

### Logistic Regression

Used as an interpretable binary classifier and probability model.

### Decision Tree Classifier

Used to capture nonlinear thresholds and rule-like interactions while remaining relatively easy to interpret.

### Random Forest Classifier

Used as a more flexible ensemble model that can capture nonlinear relationships and interactions.

No model is assumed to be the best in advance.

## Validation Strategy

The project uses **chronological validation** rather than random splitting.

Planned starting split:

- Training: 2015–2022
- Validation/model selection: 2023–2024
- Final test: 2025 observations predicting 2026 fault occurrence

All preprocessing, including encoding, scaling, imputation, and any class-imbalance treatment, must be fitted only on the training portion.

## Evaluation Metrics

The project will report:

- Precision
- Recall
- F1-score
- Confusion matrix
- ROC-AUC
- PR-AUC
- Accuracy as a secondary metric

Accuracy will not be used alone because the target is imbalanced.

## Main Variables Under Review

Important proposed predictors include:

- `ocean_route`
- `operator_type`
- `age_years`
- `fiber_pairs`
- `length_km`
- `n_landing_countries`
- `chokepoint`
- `design_capacity_tbps`
- `lit_capacity_tbps`
- `utilization_pct`
- `protected_burial`
- `route_redundancy`
- `is_low_redundancy`
- `vulnerability_index`
- `fault_this_year`

Derived or redundant variables will be audited before modeling.

## Repository Structure

```text
undersea-cable-fault-risk-prediction/
├── data/
│   ├── raw/
│   └── processed/
├── notebooks/
├── src/
├── outputs/
│   ├── figures/
│   ├── tables/
│   └── models/
├── docs/
├── requirements.txt
├── .gitignore
└── README.md