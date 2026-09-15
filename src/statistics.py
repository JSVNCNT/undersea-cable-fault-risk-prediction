import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, mannwhitneyu

from . import config

def cramers_v(table):
    chi2 = chi2_contingency(table, correction=False)[0]; n = table.to_numpy().sum()
    r, k = table.shape; return float(np.sqrt((chi2 / n) / max(1, min(k - 1, r - 1)))) if n else np.nan

def categorical_associations(df):
    rows=[]
    for col in config.CATEGORICAL_PREDICTORS:
        tab = pd.crosstab(df[col], df[config.TARGET_COLUMN]); chi2,p,dof,_ = chi2_contingency(tab)
        rows.append({"variable": col, "test": "chi-square", "statistic": chi2, "df": dof, "p_value": p, "cramers_v": cramers_v(tab), "n": int(tab.to_numpy().sum())})
    return pd.DataFrame(rows)

def numeric_comparisons(df):
    rows=[]
    for col in config.NUMERICAL_PREDICTORS:
        a=df.loc[df[config.TARGET_COLUMN]==0,col].dropna(); b=df.loc[df[config.TARGET_COLUMN]==1,col].dropna()
        stat,p=mannwhitneyu(a,b,alternative="two-sided")
        rows.append({"variable":col,"test":"Mann-Whitney U","statistic":stat,"p_value":p,"median_no_fault":a.median(),"median_fault":b.median(),"n":len(a)+len(b)})
    return pd.DataFrame(rows)

