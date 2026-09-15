from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

def make_eda_figures(df: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    yearly = df.groupby("year").agg(records=("cable_id", "size"), prevalence=("fault_next_year", "mean"))
    fig, ax1 = plt.subplots(figsize=(8, 4)); yearly.records.plot(ax=ax1, marker="o", color="tab:blue"); ax1.set(xlabel="Observation year", ylabel="Records", title="Figure 1. Annual cable-year records")
    fig.tight_layout(); fig.savefig(out_dir / "figure_01_annual_records.png", dpi=150); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4)); yearly.prevalence.plot(ax=ax, marker="o", color="tab:red"); ax.set(xlabel="Observation year", ylabel="Next-year fault prevalence", title="Figure 2. Annual next-year fault prevalence"); fig.tight_layout(); fig.savefig(out_dir / "figure_02_annual_prevalence.png", dpi=150); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4)); df["route_redundancy"].plot(kind="hist", bins=25, ax=ax, color="tab:green"); ax.set(xlabel="Route redundancy (count)", title="Figure 3. Route-redundancy distribution"); fig.tight_layout(); fig.savefig(out_dir / "figure_03_route_redundancy.png", dpi=150); plt.close(fig)

