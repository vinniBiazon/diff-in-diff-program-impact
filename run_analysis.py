"""Run the difference-in-differences case study end to end.

    python data/generate.py     # once, creates data/raw/
    python run_analysis.py      # runs sql/00..05 in DuckDB, adds bootstrap intervals, writes outputs/

No database or credentials needed.
"""
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
SQL = ROOT / "sql"
OUT = ROOT / "outputs"
METRICS = ["visits", "days_with_visit", "contributions", "share_of_months_active", "revenue_usd"]


def build() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"SET file_search_path = '{ROOT.as_posix()}'")
    for step in sorted(SQL.glob("0*.sql")):
        con.execute(step.read_text(encoding="utf-8"))
    return con


def bootstrap_did(con: duckdb.DuckDBPyConnection, reps: int = 500, seed: int = 3) -> pd.DataFrame:
    """95% interval for the relative DiD, resampling members within each group."""
    mp = con.table("member_periods").df()
    wide = mp.pivot_table(index=["member_id", "study_group"], columns="period", values=METRICS).reset_index()
    rng = np.random.default_rng(seed)
    groups = {g: wide[wide.study_group == g] for g in ("mentor_engaged", "comparison")}
    rows = []
    for metric in METRICS:
        e_b, e_a = groups["mentor_engaged"][(metric, "before")].to_numpy(), groups["mentor_engaged"][(metric, "after")].to_numpy()
        c_b, c_a = groups["comparison"][(metric, "before")].to_numpy(), groups["comparison"][(metric, "after")].to_numpy()
        ie = rng.integers(0, len(e_b), (reps, len(e_b)))
        ic = rng.integers(0, len(c_b), (reps, len(c_b)))
        did = (e_a[ie].mean(1) / e_b[ie].mean(1)) / (c_a[ic].mean(1) / c_b[ic].mean(1)) - 1
        rows.append({"metric": metric, "ci_low": np.quantile(did, 0.025), "ci_high": np.quantile(did, 0.975)})
    return pd.DataFrame(rows)


def true_effect(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Only possible with synthetic data: compare the mentor_engaged group's real "after"
    with the same members in the simulated world without the program."""
    cf = pd.read_csv(ROOT / "data/raw/counterfactual_after.csv")
    after = con.execute(
        "SELECT * FROM member_periods WHERE study_group = 'mentor_engaged' AND period = 'after'"
    ).df()
    cf = cf[cf.member_id.isin(after.member_id)]
    return pd.DataFrame(
        {"metric": METRICS, "true_effect": [after[m].mean() / cf[m].mean() - 1 for m in METRICS]}
    )


def main() -> None:
    con = build()
    OUT.mkdir(exist_ok=True)
    est = con.table("estimates").df().merge(bootstrap_did(con), on="metric")
    est = est.merge(true_effect(con), on="metric", how="left")
    est.to_csv(OUT / "estimates.csv", index=False)
    for t in ["group_means", "monthly_trend", "placebo"]:
        con.table(t).df().to_csv(OUT / f"{t}.csv", index=False)

    sizes = con.execute("SELECT study_group, COUNT(*) FROM study_groups GROUP BY 1 ORDER BY 1").fetchall()
    print("Groups:", ", ".join(f"{g} {n:,}" for g, n in sizes))
    show = est[["metric", "naive_gap", "baseline_gap", "did_relative", "ci_low", "ci_high", "true_effect"]]
    print("\n" + show.to_string(index=False, float_format=lambda x: f"{x:+.1%}"))
    print("\nPlacebo (fake launch in mid-2025):")
    print(con.table("placebo").df().to_string(index=False, float_format=lambda x: f"{x:+.1%}"))


if __name__ == "__main__":
    main()
