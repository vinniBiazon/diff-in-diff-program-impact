"""Generate a synthetic Q&A community for the difference-in-differences case study.

Everything is invented. The story built into the data:

- A Q&A community launches a paid mentor program in November 2025: a small group of
  experienced members is paid to answer questions every week.
- Members who end up interacting a lot with mentor answers were ALREADY more engaged
  before the program existed (selection).
- The whole platform loses activity between 2025 and 2026 (a market-wide trend).
- On top of that, the program has a real effect on the members it reaches: more visits,
  more contributions and a lower chance of going quiet.

The generator also simulates the same community WITHOUT the program (same members, same
trend). The difference between the two worlds, for the members the analysis calls
"mentor engaged", is the true effect. data/raw/counterfactual_after.csv keeps that world so
run_analysis.py can check whether each method recovers it.

Run:  python data/generate.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 11
N_MEMBERS = 90_000
MONTHS = pd.date_range("2025-01-01", "2026-09-01", freq="MS")
LAUNCH = pd.Timestamp("2025-11-01")

# Planted effect for exposed members after launch
LIFT = {"visits": 0.08, "days_with_visit": 0.06, "contributions": 0.12}
QUIET_RISK_CUT = 0.25       # exposed members are 25% less likely to go quiet each month
MONTHLY_QUIET_RISK = 0.05   # same for everyone, so the two groups trend in parallel
AFTER_MONTHS = pd.date_range("2026-06-01", "2026-08-01", freq="MS")
PLATFORM_TREND = -0.12      # everyone loses 12% of activity from early 2025 to late 2026
OUT = Path(__file__).resolve().parent / "raw"


def main() -> None:
    rng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    members = pd.DataFrame(
        {
            "member_id": np.arange(700_001, 700_001 + N_MEMBERS),
            "joined_on": pd.Timestamp("2025-01-01") - pd.to_timedelta(rng.integers(30, 365 * 6, N_MEMBERS), unit="D"),
            "region": rng.choice(["North America", "Europe", "Latin America", "Asia-Pacific"], N_MEMBERS,
                                 p=[0.45, 0.28, 0.15, 0.12]),
            "plan": rng.choice(["Free", "Pro"], N_MEMBERS, p=[0.8, 0.2]),
        }
    )

    # Latent engagement drives everything, including who interacts with mentors later
    engagement = rng.lognormal(0.0, 0.7, N_MEMBERS)
    mentor_affinity = rng.lognormal(0.0, 0.6, N_MEMBERS) * engagement**0.9  # selection
    regular_affinity = rng.lognormal(0.0, 0.6, N_MEMBERS) * engagement**0.9
    pro = (members["plan"] == "Pro").to_numpy()

    # Who will end up heavily exposed to mentor answers (decided by affinity, used for the effect)
    exposed_true = mentor_affinity > np.quantile(mentor_affinity, 0.88)

    activity_rows, interaction_rows, cf_rows = [], [], []
    alive = np.ones(N_MEMBERS, dtype=bool)
    alive_cf = np.ones(N_MEMBERS, dtype=bool)  # the world without the program
    for t, month in enumerate(MONTHS):
        trend = 1 + PLATFORM_TREND * t / (len(MONTHS) - 1)
        season = 1 + 0.06 * np.sin(2 * np.pi * (month.month - 2) / 12)
        post = month >= LAUNCH

        # going quiet (shared random draws, so both worlds differ only by the program)
        hazard = np.full(N_MEMBERS, MONTHLY_QUIET_RISK)
        if post:
            hazard[exposed_true] *= 1 - QUIET_RISK_CUT
        u_quiet, u_back = rng.random(N_MEMBERS), rng.random(N_MEMBERS)
        alive = (alive & (u_quiet > hazard)) | (~alive & (u_back < 0.03))
        alive_cf = (alive_cf & (u_quiet > MONTHLY_QUIET_RISK)) | (~alive_cf & (u_back < 0.03))

        base = 6.0 * engagement * trend * season
        lift_v = np.where(post & exposed_true, 1 + LIFT["visits"], 1.0)
        lift_d = np.where(post & exposed_true, 1 + LIFT["days_with_visit"], 1.0)
        lift_c = np.where(post & exposed_true, 1 + LIFT["contributions"], 1.0)

        visits = np.where(alive, rng.poisson(base * lift_v), 0)
        days = np.minimum(np.where(alive, rng.poisson(0.55 * base * lift_d), 0), visits)
        contributions = np.where(alive, rng.poisson(0.35 * engagement * trend * lift_c), 0)
        # ad and subscription revenue, proportional to usage (Pro members are worth more per visit)
        revenue = 0.12 * visits * np.where(pro, 2.5, 1.0) * rng.lognormal(0, 0.2, N_MEMBERS)

        if month in AFTER_MONTHS:
            v_cf = np.where(alive_cf, rng.poisson(base), 0)
            d_cf = np.minimum(np.where(alive_cf, rng.poisson(0.55 * base), 0), v_cf)
            c_cf = np.where(alive_cf, rng.poisson(0.35 * engagement * trend), 0)
            r_cf = 0.12 * v_cf * np.where(pro, 2.5, 1.0) * rng.lognormal(0, 0.2, N_MEMBERS)
            cf_rows.append(pd.DataFrame({"member_id": members["member_id"].to_numpy(), "visits": v_cf,
                                         "days_with_visit": d_cf, "contributions": c_cf, "revenue_usd": r_cf,
                                         "active": (v_cf > 0).astype(int)}))

        active = visits > 0
        activity_rows.append(pd.DataFrame({
            "member_id": members["member_id"].to_numpy()[active],
            "month": month,
            "visits": visits[active],
            "days_with_visit": days[active],
            "contributions": contributions[active],
            "revenue_usd": revenue[active].round(2),
        }))

        # interactions (votes, replies, saves) with answers, split by who wrote the answer
        mentor_rate = np.where(post, 0.9 * mentor_affinity * trend, 0.0)
        regular_rate = 2.2 * regular_affinity * trend
        n_mentor = np.where(active, rng.poisson(mentor_rate), 0)
        n_regular = np.where(active, rng.poisson(regular_rate), 0)
        for source, n in (("mentor", n_mentor), ("regular", n_regular)):
            keep = n > 0
            interaction_rows.append(pd.DataFrame({
                "member_id": members["member_id"].to_numpy()[keep],
                "month": month,
                "answer_author": source,
                "interactions": n[keep],
            }))

    activity = pd.concat(activity_rows, ignore_index=True)
    interactions = pd.concat(interaction_rows, ignore_index=True)

    members.to_csv(OUT / "members.csv", index=False)
    activity.to_csv(OUT / "monthly_activity.csv", index=False)
    interactions.to_csv(OUT / "answer_interactions.csv", index=False)
    # Counterfactual "after" window, averaged per member per month
    cf = pd.concat(cf_rows).groupby("member_id").mean().reset_index()
    cf = cf.rename(columns={"active": "share_of_months_active"})
    cf.round(4).to_csv(OUT / "counterfactual_after.csv", index=False)

    print(f"members           {len(members):>10,}")
    print(f"monthly_activity  {len(activity):>10,}")
    print(f"interactions      {len(interactions):>10,}")


if __name__ == "__main__":
    main()
