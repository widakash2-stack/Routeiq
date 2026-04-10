import os
import sys
import uuid
import random
from datetime import datetime

import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routing_engine import route_transaction_with_trace, update_bandit, retry_ql

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(CURRENT_DIR, "../data/payment_data.csv")
OUTPUT_PATH = os.path.join(CURRENT_DIR, "decision_log.csv")


def compute_reward(amount, psp, outcome_success, latency_ms, psp_data):
    TAKE_RATE = 0.015
    revenue = amount * TAKE_RATE

    psp_row = psp_data[psp_data["psp"] == psp]
    psp_row = psp_row.iloc[0] if len(psp_row) > 0 else None
    psp_cost = float(psp_row["base_cost"]) if psp_row is not None else 1.5

    latency_penalty = latency_ms / 100000

    if outcome_success:
        reward = revenue - psp_cost - latency_penalty
    else:
        failure_cost = revenue * 0.5
        reward = -(psp_cost + failure_cost + latency_penalty)

    return round(reward, 4)


def simulate(n=20000):
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} PSP records from payment_data.csv")

    combos = df[["country", "payment_method"]].drop_duplicates().to_dict("records")
    psp_success = df.groupby("psp")["success_rate"].mean().to_dict()
    psp_latency = df.groupby("psp")["latency_ms"].mean().to_dict()

    # Weighted sampling: region share divided equally across countries in that region
    # APAC 39% / 5 countries = 7.8% each
    # Africa 30% / 4 countries = 7.5% each
    # Europe 19% / 1 country  = 19.0% each
    # Americas 12% / 4 countries = 3.0% each
    COUNTRY_WEIGHT = {
        "Indonesia": 7.8, "Philippines": 7.8, "Vietnam": 7.8, "Thailand": 7.8, "Malaysia": 7.8,
        "Nigeria":   7.5, "Kenya":       7.5, "Ghana":   7.5, "Tanzania": 7.5,
        "EU":        19.0,
        "Brazil":    3.0, "Mexico":      3.0, "Chile":   3.0, "USA":      3.0,
    }

    # Assign each (country, method) combo a weight equal to its country's share
    # divided by the number of payment methods for that country
    method_counts = df.groupby("country")["payment_method"].nunique().to_dict()
    combo_weights = [
        COUNTRY_WEIGHT.get(c["country"], 1.0) / method_counts.get(c["country"], 1)
        for c in combos
    ]

    records = []

    for i in range(n):
        combo = random.choices(combos, weights=combo_weights, k=1)[0]

        txn = {
            "txn_id":         f"txn_{i + 1}",
            "country":        combo["country"],
            "payment_method": combo["payment_method"],
            "amount":         round(random.uniform(50, 5000), 2),
            "timestamp":      datetime.utcnow().isoformat(),
        }

        outcome_success = None
        best_psp = None
        total_reward = None
        first_latency_ms = None
        selected_psp = None
        attempts_log = []
        final_psp = None
        final_outcome = "failure"
        psp_ranking_str = None

        try:
            selected_psp, trace = route_transaction_with_trace(txn)
            best_psp = trace.get("best_psp")
            psp_ranking = [entry["psp"] for entry in trace.get("psp_ranking", [])]
            psp_ranking_str = "|".join(psp_ranking)

            context = (txn["country"], txn["payment_method"])

            # Build candidate list: selected_psp first, then remaining ranked PSPs (up to 3 total)
            candidates = [selected_psp] if selected_psp else []
            for psp in psp_ranking:
                if psp not in candidates:
                    candidates.append(psp)
                if len(candidates) == 3:
                    break

            total_reward = 0.0
            last_failure_type = None
            last_retry_state  = None

            for attempt_num, _ in enumerate(range(3)):
                # Attempt 0: use bandit-selected PSP; attempts 1-2: use retry_ql
                if attempt_num == 0:
                    psp = candidates[0] if candidates else None
                else:
                    if last_failure_type is None:
                        break  # previous attempt succeeded
                    retry_state = retry_ql.get_state(
                        txn["country"], txn["payment_method"],
                        attempt_num, last_failure_type,
                    )
                    remaining = [p for p in candidates if p not in attempts_log]
                    if not remaining:
                        break
                    psp = retry_ql.select_psp(retry_state, remaining, attempts_log[-1])
                    last_retry_state = retry_state

                if psp is None:
                    break

                success_rate = psp_success.get(psp, 0.8)
                base_latency = psp_latency.get(psp, 1000)
                latency_ms   = round(random.uniform(base_latency * 0.8, base_latency * 1.2))

                if attempt_num == 0:
                    first_latency_ms = latency_ms

                attempt_success = random.random() < success_rate
                reward = compute_reward(txn["amount"], psp, attempt_success, latency_ms, df)
                total_reward += reward

                update_bandit(context, psp, reward)
                attempts_log.append(psp)

                if attempt_success:
                    outcome_success = True
                    final_psp = psp
                    final_outcome = "success"
                    # Update retry_ql on success if this was a retry attempt
                    if last_retry_state is not None:
                        done = True
                        next_state = retry_ql.get_state(
                            txn["country"], txn["payment_method"], attempt_num + 1, None
                        )
                        retry_ql.update(last_retry_state, psp, reward, next_state, done=done)
                    break
                else:
                    # Classify failure type for next retry decision
                    dist = {
                        "soft_decline": 0.40,
                        "retryable":    0.40,
                        "hard_fail":    0.15,
                        "user_drop":    0.05,
                    }
                    last_failure_type = random.choices(
                        list(dist.keys()), weights=list(dist.values()), k=1
                    )[0]
                    # Update retry_ql on failure if this was a retry attempt
                    if last_retry_state is not None:
                        is_last = (attempt_num == 2)
                        next_state = retry_ql.get_state(
                            txn["country"], txn["payment_method"],
                            attempt_num + 1, last_failure_type,
                        )
                        retry_ql.update(last_retry_state, psp, reward, next_state, done=is_last)

            total_reward = round(total_reward, 4)

        except Exception:
            selected_psp = None

        records.append({
            "txn_id":         txn["txn_id"],
            "country":        txn["country"],
            "payment_method": txn["payment_method"],
            "amount":         txn["amount"],
            "timestamp":      txn["timestamp"],
            "selected_psp":   selected_psp,
            "best_psp":       best_psp,
            "outcome":        "success" if outcome_success else "failure",
            "reward":         total_reward,
            "latency_ms":     first_latency_ms,
            "attempts":       "→".join(attempts_log) if attempts_log else None,
            "final_psp":      final_psp if final_psp else (selected_psp if not attempts_log else attempts_log[-1]),
            "final_outcome":  final_outcome,
            "psp_ranking":    psp_ranking_str,
        })

        if (i + 1) % 100 == 0:
            print(f"Progress: {i + 1}/{n} transactions simulated")

    output_df = pd.DataFrame(records)
    output_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nDone. {n} transactions saved to: {OUTPUT_PATH}")
    print("\nPSP selection counts:")
    print(output_df["selected_psp"].value_counts())


if __name__ == "__main__":
    simulate()
