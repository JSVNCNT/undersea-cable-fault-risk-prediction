import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, mannwhitneyu

from . import config


def holm_adjust(p_values):
    """Holm family-wise adjustment; preserves order and unavailable p-values."""
    p = np.asarray(p_values, dtype=float)
    adjusted = np.full(p.shape, np.nan)
    valid = np.flatnonzero(np.isfinite(p))
    order = valid[np.argsort(p[valid], kind="stable")]
    if len(order):
        adjusted[order] = np.minimum(1.0, np.maximum.accumulate(p[order] * np.arange(len(order), 0, -1)))
    return adjusted

def cramers_v(table):
    chi2 = chi2_contingency(table, correction=False)[0]; n = table.to_numpy().sum()
    r, k = table.shape; return float(np.sqrt((chi2 / n) / max(1, min(k - 1, r - 1)))) if n else np.nan

def categorical_associations(df):
    rows=[]
    for col in config.CATEGORICAL_PREDICTORS:
        tab = pd.crosstab(df[col], df[config.TARGET_COLUMN]); chi2,p,dof,expected = chi2_contingency(tab)
        rows.append({"variable": col, "test": "chi-square", "statistic": chi2, "df": dof, "p_value": p, "cramers_v": cramers_v(tab), "n": int(tab.to_numpy().sum()),
                     "n_no_fault": int(tab.get(0, pd.Series(dtype=int)).sum()), "n_fault": int(tab.get(1, pd.Series(dtype=int)).sum()),
                     "minimum_expected_count": float(expected.min()), "expected_cells_below_5": int((expected < 5).sum()),
                     "independent_rows_assumed": True, "repeated_cable_caution": True})
    return pd.DataFrame(rows)

def numeric_comparisons(df):
    rows=[]
    for col in config.NUMERICAL_PREDICTORS:
        a=df.loc[df[config.TARGET_COLUMN]==0,col].dropna(); b=df.loc[df[config.TARGET_COLUMN]==1,col].dropna()
        stat,p=mannwhitneyu(a,b,alternative="two-sided")
        rows.append({"variable":col,"test":"Mann-Whitney U","statistic":stat,"p_value":p,"median_no_fault":a.median(),"median_fault":b.median(),"n":len(a)+len(b),
                     "n_no_fault":len(a), "n_fault":len(b),
                     "rank_biserial_fault_higher": float(1 - 2 * stat / (len(a) * len(b))) if len(a) and len(b) else np.nan,
                     "independent_rows_assumed":True, "repeated_cable_caution":True})
    return pd.DataFrame(rows)

