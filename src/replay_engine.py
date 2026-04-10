import os
import pandas as pd

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

_PAYMENT_DATA_PATH = os.path.join(CURRENT_DIR, "../data/payment_data.csv")

_psp_df = pd.read_csv(_PAYMENT_DATA_PATH)

MAX_COST    = 3.0
MAX_LATENCY = 2500

# Combined score matching routing_engine formula:
# score = (0.8 * success_rate) + (0.1 * cost_score) + (0.1 * latency_score)
_psp_df["cost_score"]    = 1 - (_psp_df["base_cost"]   / MAX_COST)
_psp_df["latency_score"] = 1 - (_psp_df["latency_ms"]  / MAX_LATENCY)
_psp_df["combined_score"] = (
    (0.8 * _psp_df["success_rate"]) +
    (0.1 * _psp_df["cost_score"])   +
    (0.1 * _psp_df["latency_score"])
)

# best_psp = PSP with highest combined score per country/method
_best_psp_lookup = (
    _psp_df.sort_values("combined_score", ascending=False)
    .groupby(["country", "payment_method"])["psp"]
    .first()
    .to_dict()
)

# Per-PSP average combined score for regret calculation
_psp_score = _psp_df.groupby("psp")["combined_score"].mean().to_dict()

# Ground-truth ranked PSP list per country/method (descending combined_score)
_psp_ranked = (
    _psp_df.sort_values("combined_score", ascending=False)
    .groupby(["country", "payment_method"])["psp"]
    .apply(list)
    .to_dict()
)

print(f"[replay_engine] Loaded best_psp for {len(_best_psp_lookup)} country/method combinations")


def _decision_quality(regret: float, chosen_psp: str, best_psp: str) -> str:
    if chosen_psp == best_psp:
        return "Optimal"
    if regret < 0.05:
        return "Near-optimal"
    return "Suboptimal"


# -------------------------------
# REPLAY ENGINE
# -------------------------------
def run_replay_engine(log_file_path: str):
    df = pd.read_csv(log_file_path)

    has_ranking_col = "psp_ranking" in df.columns

    total_regret = 0.0
    total_counterfactual_regret = 0.0
    total_txns = 0
    optimal_matches = 0
    near_optimal_matches = 0
    suboptimal_matches = 0

    replay_rows = []

    for _, row in df.iterrows():
        country = row["country"]
        payment_method = row["payment_method"]
        chosen_psp = row["selected_psp"]

        # Ground-truth best PSP for this country/method
        best_psp = _best_psp_lookup.get((country, payment_method))

        # Regret = best_score - chosen_score (positive when chosen is worse)
        best_score   = _psp_score.get(best_psp, 0.0)
        chosen_score = _psp_score.get(chosen_psp, 0.0)
        regret = max(0.0, round(best_score - chosen_score, 6))

        # --- Counterfactual: 2nd best PSP from the model's ranking at decision time ---
        # Prefer psp_ranking column; fall back to ground-truth ranking from payment_data.csv
        if has_ranking_col and pd.notna(row.get("psp_ranking")):
            ranked_psps = [p.strip() for p in str(row["psp_ranking"]).split("|") if p.strip()]
        else:
            ranked_psps = _psp_ranked.get((country, payment_method), [])

        # 2nd best = first PSP in the ranking that isn't the chosen one
        counterfactual_psp = next((p for p in ranked_psps if p != chosen_psp), None)
        if counterfactual_psp is None and len(ranked_psps) > 1:
            counterfactual_psp = ranked_psps[1]

        second_best_score = _psp_score.get(counterfactual_psp, 0.0) if counterfactual_psp else 0.0
        # Positive = chosen was better than 2nd; negative = chosen was worse
        counterfactual_regret = round(chosen_score - second_best_score, 6)

        quality = _decision_quality(regret, chosen_psp, best_psp)

        total_regret += regret
        total_counterfactual_regret += abs(counterfactual_regret)
        total_txns += 1

        is_optimal = int(quality == "Optimal")
        optimal_matches += is_optimal
        near_optimal_matches += int(quality == "Near-optimal")
        suboptimal_matches += int(quality == "Suboptimal")

        replay_rows.append({
            "txn_id":                row["txn_id"],
            "chosen_psp":            chosen_psp,
            "best_psp":              best_psp,
            "chosen_score":          round(chosen_score, 4),
            "best_score":            round(best_score, 4),
            "regret":                regret,
            "is_optimal":            is_optimal,
            "counterfactual_psp":    counterfactual_psp,
            "counterfactual_regret": counterfactual_regret,
            "decision_quality":      quality,
        })

    avg_regret = total_regret / total_txns if total_txns > 0 else 0.0
    avg_cf_regret = total_counterfactual_regret / total_txns if total_txns > 0 else 0.0
    optimal_selection_rate = optimal_matches / total_txns if total_txns > 0 else 0.0

    pct_optimal     = round(optimal_matches     / total_txns * 100, 2) if total_txns else 0.0
    pct_near        = round(near_optimal_matches / total_txns * 100, 2) if total_txns else 0.0
    pct_suboptimal  = round(suboptimal_matches   / total_txns * 100, 2) if total_txns else 0.0

    print("\n===== REPLAY RESULTS =====")
    print(f"Total Transactions:           {total_txns}")
    print(f"Total Regret:                 {round(total_regret, 6)}")
    print(f"Average Regret:               {round(avg_regret, 6)}")
    print(f"Optimal Selection Rate:        {round(optimal_selection_rate * 100, 2)}%")
    print(f"\n--- Decision Quality Breakdown ---")
    print(f"  Optimal:                    {pct_optimal}%")
    print(f"  Near-optimal:               {pct_near}%")
    print(f"  Suboptimal:                 {pct_suboptimal}%")
    print(f"  Avg Counterfactual Regret:  {round(avg_cf_regret, 6)}")

    output_df = pd.DataFrame(replay_rows)
    output_path = os.path.join(CURRENT_DIR, "replay_results.csv")
    output_df.to_csv(output_path, index=False)

    print(f"\nReplay results saved to: {output_path}")

    return {
        "total_txns":              total_txns,
        "total_regret":            total_regret,
        "avg_regret":              avg_regret,
        "optimal_selection_rate":  optimal_selection_rate,
        "pct_optimal":             pct_optimal,
        "pct_near_optimal":        pct_near,
        "pct_suboptimal":          pct_suboptimal,
        "avg_counterfactual_regret": avg_cf_regret,
    }


# -------------------------------
# A/B STRATEGY COMPARISON
# -------------------------------
def _group_stats(group_df: pd.DataFrame) -> dict:
    """Compute OSR, regret, quality breakdown, and avg reward for a transaction group."""
    n = len(group_df)
    if n == 0:
        return {}

    rows = []
    for _, row in group_df.iterrows():
        country        = row["country"]
        payment_method = row["payment_method"]
        chosen_psp     = row["selected_psp"]

        best_psp     = _best_psp_lookup.get((country, payment_method))
        best_score   = _psp_score.get(best_psp, 0.0)
        chosen_score = _psp_score.get(chosen_psp, 0.0)
        regret       = max(0.0, round(best_score - chosen_score, 6))
        quality      = _decision_quality(regret, chosen_psp, best_psp)

        rows.append({
            "regret":           regret,
            "is_optimal":       int(quality == "Optimal"),
            "is_near_optimal":  int(quality == "Near-optimal"),
            "is_suboptimal":    int(quality == "Suboptimal"),
            "reward":           row.get("reward", None),
        })

    stats_df = pd.DataFrame(rows)

    avg_reward = (
        stats_df["reward"].dropna().mean()
        if "reward" in stats_df.columns and stats_df["reward"].notna().any()
        else None
    )

    return {
        "n":              n,
        "osr":            round(stats_df["is_optimal"].mean() * 100, 2),
        "avg_regret":     round(stats_df["regret"].mean(), 6),
        "pct_optimal":    round(stats_df["is_optimal"].mean()     * 100, 2),
        "pct_suboptimal": round(stats_df["is_suboptimal"].mean()  * 100, 2),
        "avg_reward":     round(avg_reward, 4) if avg_reward is not None else None,
    }


def run_ab_comparison(log_file_path: str) -> dict:
    """
    Split decision_log.csv into two equal halves (Group A = early, Group B = late)
    and compare performance metrics to demonstrate that the system learns over time.
    """
    df = pd.read_csv(log_file_path)
    total = len(df)
    mid   = total // 2

    group_a = df.iloc[:mid].copy()
    group_b = df.iloc[mid:mid * 2].copy()  # ensures equal size even if total is odd

    stats_a = _group_stats(group_a)
    stats_b = _group_stats(group_b)

    # --- OSR improvement ---
    osr_delta      = round(stats_b["osr"]         - stats_a["osr"],         2)
    regret_delta   = round(stats_a["avg_regret"]  - stats_b["avg_regret"],  6)   # positive = B improved
    sub_delta      = round(stats_a["pct_suboptimal"] - stats_b["pct_suboptimal"], 2)

    reward_delta = None
    if stats_a["avg_reward"] is not None and stats_b["avg_reward"] is not None:
        reward_delta = round(stats_b["avg_reward"] - stats_a["avg_reward"], 4)

    # Determine overall winner
    better_group = "B (late)" if osr_delta >= 0 else "A (early)"

    print("\n" + "═" * 56)
    print("  A/B STRATEGY COMPARISON  —  Early vs Late Learning")
    print("═" * 56)
    print(f"{'Metric':<30} {'Group A (txn 1–' + str(mid) + ')':<20} {'Group B (txn ' + str(mid+1) + '–' + str(mid*2) + ')'}")
    print("-" * 56)
    print(f"{'Transactions':<30} {stats_a['n']:<20} {stats_b['n']}")
    print(f"{'OSR %':<30} {stats_a['osr']:<20} {stats_b['osr']}")
    print(f"{'Avg Regret':<30} {stats_a['avg_regret']:<20} {stats_b['avg_regret']}")
    print(f"{'% Optimal':<30} {stats_a['pct_optimal']:<20} {stats_b['pct_optimal']}")
    print(f"{'% Suboptimal':<30} {stats_a['pct_suboptimal']:<20} {stats_b['pct_suboptimal']}")
    if stats_a["avg_reward"] is not None:
        print(f"{'Avg Reward':<30} {stats_a['avg_reward']:<20} {stats_b['avg_reward']}")
    print("-" * 56)
    print(f"\n  Winner: {better_group}")
    print(f"  OSR improvement:        {'+' if osr_delta >= 0 else ''}{osr_delta}%")
    print(f"  Regret reduction:       {'+' if regret_delta >= 0 else ''}{regret_delta}")
    print(f"  Suboptimal reduction:   {'+' if sub_delta >= 0 else ''}{sub_delta}%")
    if reward_delta is not None:
        print(f"  Reward improvement:     {'+' if reward_delta >= 0 else ''}{reward_delta}")
    print("═" * 56)

    return {
        "group_a":      stats_a,
        "group_b":      stats_b,
        "osr_delta":    osr_delta,
        "regret_delta": regret_delta,
        "sub_delta":    sub_delta,
        "reward_delta": reward_delta,
        "winner":       better_group,
    }


# -------------------------------
# ENTRYPOINT
# -------------------------------
if __name__ == "__main__":
    log_path = os.path.join(CURRENT_DIR, "decision_log.csv")

    if not os.path.exists(log_path):
        raise FileNotFoundError(f"decision_log.csv not found at: {log_path}")

    print(f"Using decision log: {log_path}")

    run_replay_engine(log_path)
    run_ab_comparison(log_path)
