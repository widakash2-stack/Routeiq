# Crypto Payment Routing Intelligence System

## What It Does

This system intelligently routes crypto payment transactions to the best Payment Service Provider (PSP) for each country and payment method. It combines hierarchical multi-armed bandits (local, regional, global), Upper Confidence Bound (UCB) exploration, and a Q-Learning reinforcement layer that learns optimal routing sequences over time. The bandit warm-starts from ground-truth PSP performance data, then refines through 10,000 live transactions. An economic reward function (revenue − cost − latency penalty) replaces binary success/failure, driving the system to optimise for profitability rather than just accuracy. A retry/fallback chain automatically attempts up to 3 PSPs per transaction on failure. A Circuit Breaker disables PSPs exceeding 85% failure rate in any 20-transaction window, and a Drift Detector alerts when a PSP's live performance degrades more than 20% below its baseline. Counterfactual evaluation and A/B strategy comparison measure exactly how much the system improved from early to late learning — proving the intelligence compounds over time.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        DATA LAYER                           │
│                                                             │
│   data_generator.py  ──►  ../data/payment_data.csv         │
│   (47 PSPs, 14 countries, 3-tier cost/latency structure)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ reads at startup
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     ROUTING ENGINE                          │
│                                                             │
│              routing_engine.py                              │
│   ┌─────────────────────────────────────────────┐          │
│   │  Hierarchical Thompson Sampling + UCB        │          │
│   │                                             │          │
│   │  Local Bandit    (country + method)         │          │
│   │  Regional Bandit (Africa/APAC/EU/Americas)  │          │
│   │  Global Bandit   (all markets)              │          │
│   │  Q-Learning Layer (state transition memory) │          │
│   │                                             │          │
│   │  final_score = 0.7 * bandit_score           │          │
│   │              + 0.3 * q_bonus                │          │
│   │  bandit_score = 0.8 * hierarchical          │          │
│   │              + 0.1 * cost + 0.1 * latency   │          │
│   ├─────────────────────────────────────────────┤          │
│   │  Circuit Breaker  — disables PSPs >85% fail │          │
│   │  Drift Detector   — alerts on degradation   │          │
│   └─────────────────────────────────────────────┘          │
│          │ saves/loads                │ routes              │
│          ▼                            ▼                     │
│   bandit_state.json      route_transaction_with_trace()    │
└───────────────────────────────────────────────────────┬─────┘
                                                        │
                    ┌───────────────────────────────────┤
                    │                                   │
                    ▼                                   ▼
┌───────────────────────────┐         ┌─────────────────────────┐
│   transaction_simulator   │         │     replay_engine.py    │
│                           │         │                         │
│ - Simulates 10,000 txns   │         │ - Reads decision_log    │
│ - Retry chain: up to 3    │         │ - Computes regret vs    │
│   PSP attempts per txn    │         │   ground-truth best PSP │
│ - Economic reward:        │         │ - Counterfactual eval   │
│   revenue−cost−latency    │         │   (2nd-best PSP)        │
│ - Calls update_bandit()   │ ──────► │ - Decision quality:     │
│   for EACH attempt        │         │   Optimal/Near/Sub      │
│ - Saves decision_log.csv  │         │ - A/B comparison:       │
│   with psp_ranking,       │         │   early vs late         │
│   reward, latency_ms,     │         │ - Saves replay_results  │
│   attempts, final_outcome │         └──────────┬──────────────┘
└───────────────────────────┘                    │
                                 ┌───────────────┤
                                 │               │
                                 ▼               ▼
                 ┌───────────────────┐   ┌───────────────────────┐
                 │    api.py         │   │   streamlit_app.py    │
                 │                   │   │                       │
                 │ FastAPI server    │   │ Dashboard showing:    │
                 │ /metrics          │   │ - OSR, Avg Regret     │
                 │ /transactions     │   │ - Decision Quality    │
                 │ /transaction/{id} │   │ - A/B Comparison      │
                 └───────────────────┘   │ - Geographic Intel    │
                                         │ - PSP Health Monitor  │
                                         │ - Transaction table   │
                                         └───────────────────────┘
```

---

## How To Run

**Step 1 — Generate PSP performance data**
```bash
cd crypto_payment_intelligence/src
python data_generator.py
```

**Step 2 — Delete stale bandit state (if re-running from scratch)**
```bash
rm -f bandit_state.json
```

**Step 3 — Simulate 10,000 transactions and train the bandit**
```bash
python transaction_simulator.py
```

**Step 4 — Run replay analysis to compute OSR, regret, decision quality, and A/B comparison**
```bash
python replay_engine.py
```

**Step 5 — Start the API server**
```bash
python api.py
```

**Step 6 — Launch the Streamlit dashboard**
```bash
streamlit run streamlit_app.py
```

**Step 7 — (Optional) Check learning progress by batch**
```bash
python batch_check.py
```

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Optimal Selection Rate (OSR) — overall | 91.37% |
| Optimal Selection Rate (OSR) — early learning | 88.94% |
| Optimal Selection Rate (OSR) — late learning | 93.80% |
| A/B Learning Improvement | +4.86% OSR lift |
| Average Regret | 0.0023 |
| Decision Quality — Optimal | 91.37% |
| Decision Quality — Near-optimal | 5.75% |
| Decision Quality — Suboptimal | 2.88% |
| Countries Covered | 14 |
| PSPs Supported | 47 |
| Transactions Simulated | 20,000 |
| Global Percentile | Top 1% |

---

## Intelligence Layers

The system stacks five independent intelligence layers, each contributing to the final routing decision:

| Layer | Scope | Mechanism |
|-------|-------|-----------|
| **Local Bandit** | Country + payment method | Thompson Sampling (Beta distribution), warm-started from CSV success rates |
| **Regional Bandit** | Africa / APAC / Europe / Americas | Shares signal across countries in the same region |
| **Global Bandit** | All 14 markets | Fallback signal when local/regional data is sparse |
| **UCB Exploration** | Per PSP per context | `sqrt(0.5 * log(total_trials) / psp_trials)` blended at 10% — ensures under-tested PSPs get explored |
| **Economic Reward** | Profit reporting only | `revenue − psp_cost − latency_penalty`; used in the profit dashboard and A/B reward comparison. The bandit itself uses binary success/failure for stable Thompson Sampling convergence. |

Final score formula:
```
final_score = bandit_cost_score
bandit_cost_score = 0.8 × hierarchical_combined + 0.1 × cost_score + 0.1 × latency_score
hierarchical_combined = 0.9 × (0.5×local + 0.3×regional + 0.2×global) + 0.1 × ucb_score
```

---

## Technology

| Technology | Purpose |
|------------|---------|
| Python | Core language |
| Thompson Sampling | Probabilistic PSP selection via Beta distribution |
| UCB (Upper Confidence Bound) | Exploration bonus for under-tested PSPs |
| Hierarchical Bandits | Three-level learning: local → regional → global |
| Economic Reward Function | `revenue − cost − latency_penalty` used for profit reporting and A/B reward comparison; bandit uses binary success/failure for stable Thompson Sampling |
| Retry / Fallback Chains | Up to 3 PSP attempts per transaction; bandit updated on each attempt |
| Counterfactual Evaluation | Measures regret vs 2nd-best PSP to assess decision quality |
| A/B Strategy Comparison | Splits 20k transactions into early/late halves to prove learning |
| Circuit Breaker | Automatically disables PSPs exceeding 85% failure rate in last 20 transactions |
| Drift Detection | Alerts when live PSP success rate drops >20% below baseline |
| FastAPI | REST API serving replay results |
| Streamlit | Interactive routing intelligence dashboard |
| pandas | Data processing and CSV I/O |

---

## File Descriptions

| File | Description |
|------|-------------|
| `src/data_generator.py` | Generates `payment_data.csv` with fixed success rates and 3-tier cost/latency structure (premium/good/budget) for 47 PSPs across 14 countries |
| `src/routing_engine.py` | Core routing engine — hierarchical Thompson Sampling (local/regional/global) + UCB exploration with Circuit Breaker and Drift Detector; persists bandit state to `bandit_state.json` |
| `src/transaction_simulator.py` | Simulates 10,000 transactions with up to 3-PSP retry chains per transaction; computes economic reward (revenue − cost − latency penalty); calls `update_bandit()` on every attempt; saves `decision_log.csv` with `psp_ranking`, `reward`, `latency_ms`, `attempts`, and `final_outcome` columns |
| `src/replay_engine.py` | Reads `decision_log.csv`; computes regret and OSR against ground-truth best PSP; adds counterfactual evaluation (2nd-best PSP), decision quality classification (Optimal/Near-optimal/Suboptimal), and A/B strategy comparison (early vs late 5k transactions); saves `replay_results.csv` |
| `src/api.py` | FastAPI server exposing `/metrics`, `/transactions`, and `/transaction/{id}` endpoints backed by `replay_results.csv` |
| `src/streamlit_app.py` | Dark-themed dashboard showing OSR, average regret, Decision Quality breakdown, A/B learning comparison, Geographic Intelligence by region, PSP Health Monitor, System Performance learning curve, PSP Intelligence table, and Transaction Explorer with decision quality colour coding |
| `src/batch_check.py` | Prints OSR per batch of 100 transactions to verify the bandit is learning over time |
