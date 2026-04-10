# Architectural Decision Record — Crypto Payment Routing Intelligence System

Each decision is recorded with the context, reasoning, alternatives considered, and trade-offs accepted.

---

## ADR-001 — Thompson Sampling over Epsilon-Greedy

**Decision:** Use Thompson Sampling (Beta distribution posterior) as the core bandit algorithm.

**Reason:**
Epsilon-greedy treats exploration as a fixed, blunt instrument — it explores with probability ε regardless of how much uncertainty exists about a given PSP. Thompson Sampling is inherently uncertainty-aware: a PSP with 10 observations explores much more than one with 10,000, automatically and without any hyperparameter tuning. In payment routing, this matters because PSPs have wildly different data volumes across markets. A PSP like Relworx in Kenya has far fewer transactions than Checkout.com in the EU, and forcing identical exploration rates across both would either over-explore the high-volume PSP or under-explore the low-volume one.

Thompson Sampling also produces naturally smooth convergence. As evidence accumulates, the Beta distributions narrow and exploitation increases organically. There is no cliff-edge where the system suddenly stops exploring.

**Alternatives considered:**
- **Epsilon-greedy:** Simple to implement, predictable exploration rate. Rejected because it ignores uncertainty — a PSP with 5 observations and one with 5,000 get the same exploration probability.
- **Softmax / Boltzmann:** Exploration proportional to score differences. Sensitive to temperature parameter and requires tuning. Collapses to greedy at low temperature.
- **UCB-only (no Thompson):** Pure Upper Confidence Bound. Deterministic, which means identical transactions always produce the same routing decision — no portfolio diversity.

**Trade-offs accepted:**
- Thompson Sampling requires sampling from a Beta distribution on every routing call, which is slightly more compute than a simple ε-coin-flip. Acceptable at routing latency scales.
- Results are stochastic — two identical transactions may route differently. This is a feature (portfolio diversity) but complicates deterministic testing.

---

## ADR-002 — Hierarchical 3-Level Bandit Architecture

**Decision:** Maintain three separate bandit layers — local (country + payment method), regional (Africa / APAC / Europe / Americas), and global (all markets) — and combine their signals at a 50/30/20 weight split.

**Reason:**
A single flat bandit keyed by (country, payment_method) suffers from the cold-start problem. When a new country/method combination is encountered, or a rarely-used combination appears after a long gap, the local bandit has sparse data and high uncertainty. By pulling signal from a regional bandit (which aggregates across similar markets) and a global bandit (which aggregates across all markets), the system can make informed decisions even when local data is thin.

The 50/30/20 weighting reflects confidence in specificity: local data is most relevant (if it exists), regional data captures shared PSP behaviour within a geography (e.g., M-Pesa dominates all East African mobile money), and global data is a weak prior. Without the hierarchy, early-stage routing in sparse markets would be effectively random.

**Alternatives considered:**
- **Flat local bandit only:** Simple, but cold-starts badly. A new country/method combo has no data and routes randomly for hundreds of transactions before learning.
- **Single global bandit:** Loses all geographic specificity. Checkout.com being great in the EU tells us nothing about Xendit in Indonesia.
- **Two levels (local + global):** Simpler, but misses the regional structure. East African PSPs (Fincra, Relworx) behave similarly across Kenya/Ghana/Tanzania — a regional layer captures this.
- **Contextual linear bandit (LinUCB):** More principled generalisation, but requires feature engineering and matrix operations at routing time. Overkill for the current PSP count.

**Trade-offs accepted:**
- Three bandit stores increase memory and serialisation complexity (`bandit_state.json` must persist all three levels).
- The 50/30/20 weights are fixed heuristics, not learned. A meta-bandit that learns the mixing weights would be more principled but adds significant complexity.

---

## ADR-003 — UCB Combined with Thompson Sampling

**Decision:** Apply a UCB exploration bonus on top of the Thompson Sampling score: `ucb_score = sqrt(0.5 * log(total_trials) / psp_trials)`, blended at 80% Thompson / 20% UCB.

**Reason:**
Thompson Sampling can under-explore in certain conditions — particularly when one PSP has accumulated a strong prior early on (e.g., from warm-start) and other PSPs never get enough trials to narrow their uncertainty. UCB provides a deterministic floor: PSPs with fewer trials always receive a bonus, ensuring no PSP is permanently starved of traffic regardless of how the Thompson samples happen to fall.

The combination gives the best of both: Thompson's uncertainty-proportional exploration drives most decisions, while UCB prevents the long tail of under-explored PSPs from being permanently ignored.

**Alternatives considered:**
- **Thompson Sampling alone:** Can create winner-takes-most dynamics early in learning, especially with warm-start priors. The warm-start sets strong priors that may take thousands of transactions to overcome if a PSP performs differently in practice.
- **UCB alone:** Deterministic — identical inputs always produce the same PSP. No portfolio diversity. Also computationally heavier to compute UCB bonus for all PSPs on every call.
- **Pure random exploration for new PSPs:** Simpler, but wastes transactions on truly poor PSPs.

**Trade-offs accepted:**
- The UCB coefficient (0.5) and blend weight (20%) are fixed. In production these would be tuned per market.
- UCB is computed over total local trials, which means the bonus shrinks as total volume grows even if an individual PSP remains under-explored. Acceptable because warm-start provides a baseline for all PSPs.

---

## ADR-004 — Success Rate Weighted 80%, Cost/Latency 20%

**Decision:** The combined bandit score weights success rate at 80% and splits the remaining 20% equally between cost score and latency score.

**Reason:**
Payment routing has a clear primary objective: the transaction must succeed. A failed transaction costs the merchant, damages user experience, and generates support load. Cost and latency matter for profitability and UX respectively, but a cheap, fast PSP that fails 40% of the time is far worse than an expensive, slow one that succeeds 90% of the time.

The 80/10/10 split encodes this hierarchy explicitly. It also means the scoring is robust to PSPs that game cost/latency figures — their overall score cannot compensate for a poor success rate.

**Alternatives considered:**
- **Equal weighting (33/33/33):** Gives cost and latency equal standing with success rate. A PSP with 45% success rate but very low cost could score higher than a 75% success rate PSP with medium cost — wrong outcome.
- **Success rate only (100/0/0):** Ignores cost entirely. Leads to routing all traffic through premium PSPs (Checkout.com, Relworx) regardless of whether the margin justifies it. Also loses the cost-differentiation signal that justifies budget PSPs for low-value transactions.
- **Learned weights via meta-bandit:** Most principled, but adds a layer of complexity that is hard to explain to stakeholders.

**Trade-offs accepted:**
- Cost and latency are deliberately secondary. A high-cost PSP with a great success rate will consistently win over a low-cost PSP with moderate success rate. This is intentional — reliability is the non-negotiable.
- The 80/10/10 split is fixed and not market-specific. In reality, high-volume low-margin markets (e.g., SEPA transfers in EU) might justify a higher cost weighting.

---

## ADR-005 — Q-Learning Layer on Top of Bandit

**Decision:** Add a Q-Learning layer that learns the value of PSP choices in terms of state transitions, with state defined as `(country, payment_method, top_psp)`.

**Reason:**
The bandit treats each transaction as independent. In practice, routing decisions have sequential dependencies — if Relworx fails, routing to Fincra next produces a different outcome than routing to Fincra first. Q-Learning captures this temporal structure by maintaining a Q-table over `(state, action)` pairs and updating via the Bellman equation. Over time it learns not just which PSP is best in isolation, but which PSP is best *given the current state of the routing portfolio*.

The Q-bonus is blended at 30% of the final score, keeping the bandit as the primary signal while allowing the RL layer to bias decisions based on learned sequences.

**Alternatives considered:**
- **No RL layer (bandit only):** Simpler, but ignores sequential structure. Cannot learn "if Checkout.com just failed, try ClearJunction not OpenPayd."
- **Full Deep Q-Network (DQN):** More powerful, but requires neural network infrastructure, GPU, and far more data to converge. Overkill for 47 PSPs and 14 markets.
- **Policy gradient (REINFORCE):** More sample-efficient than Q-Learning for sparse rewards, but harder to implement stably and requires episode definitions that don't cleanly map to independent payment transactions.
- **SARSA (on-policy Q-Learning):** More conservative than Q-Learning (off-policy). Chosen against because Q-Learning's off-policy nature allows learning from observed transitions without needing to follow the exact policy.

**Trade-offs accepted:**
- Q-table grows with the number of unique `(country, method, top_psp)` states. With 14 countries, ~3 methods average, and 47 PSPs, the state space is bounded but not trivial.
- Q-values need thousands of transitions to converge meaningfully. Early in training the Q-bonus is close to zero and contributes little — which is correct, but means the RL layer only meaningfully contributes in the second half of the 10,000-transaction simulation.

---

## ADR-006 — Circuit Breaker at 85% Failure Rate over 10 Transactions

**Decision:** Disable a PSP when its failure rate in the last 20 transactions exceeds 85%, with a minimum of 10 transactions required before tripping, and a 600-second recovery window.

**Reason:**
PSPs can degrade suddenly — API outages, rate limits, regional infrastructure failures. Without a circuit breaker, the bandit would continue routing traffic to a failing PSP while slowly accumulating negative evidence over hundreds of transactions, causing real revenue loss during the degradation window.

The 85% threshold is deliberately high to avoid false positives. A PSP with a baseline 75% success rate will naturally have runs of 3–4 consecutive failures without any systemic issue. Tripping below 85% would cause unnecessary circuit breaks on statistically normal variance.

The 10-transaction minimum prevents the circuit breaker from firing on the very first few transactions, where a single bad run could look catastrophic due to small sample size.

**Alternatives considered:**
- **Lower threshold (e.g. 60%):** Too sensitive. Would trip on normal statistical variance, especially for PSPs with baseline 60–70% success rates.
- **Higher threshold (e.g. 95%):** Would miss genuine degradation events until 19 out of 20 transactions have failed — too slow.
- **Consecutive failures (not rate-based):** 5 consecutive failures is simpler, but a PSP alternating success/failure would never trip the breaker despite a 50% success rate.
- **No circuit breaker:** The bandit will eventually learn to avoid a bad PSP, but "eventually" can mean hundreds of wasted transactions and failed payments during an outage.

**Trade-offs accepted:**
- The 600-second recovery time is fixed. In production this should be adaptive (e.g. exponential backoff).
- A tripped circuit breaker reduces the available PSP pool, which may force the router to use lower-ranked PSPs. This is the correct behaviour — a known-bad PSP is worse than a second-best PSP.

---

## ADR-007 — Drift Detection Threshold at 20%

**Decision:** Alert when a PSP's rolling 50-transaction success rate falls more than 20 percentage points below its baseline, with deduplication via an `already_alerted` set.

**Reason:**
Drift detection serves a different purpose from the circuit breaker. The circuit breaker reacts to acute outages; drift detection identifies gradual degradation that stays below the circuit-breaker threshold but represents a meaningful change from expected behaviour.

A 20% threshold means: if Relworx has a baseline of 75% success rate and its recent rate falls to 54%, an alert fires. This is a meaningful signal that warrants human investigation, while being wide enough to ignore normal statistical noise in a 50-transaction window.

The `already_alerted` set prevents alert storms — once an alert fires for a PSP, it will not fire again until the state is reset (system restart). In production this would be replaced by a proper alerting cooldown per PSP.

**Alternatives considered:**
- **10% threshold:** More sensitive, but a 50-transaction window has meaningful variance. A 65% success-rate PSP could hit 55% purely by chance over 50 transactions without any real degradation.
- **30% threshold:** Misses important degradation. A PSP at 75% baseline dropping to 46% should definitely alert.
- **No deduplication (alert every check):** Would flood logs with repeated alerts for the same PSP during an ongoing degradation event.
- **Statistical significance test (e.g. z-test):** More principled, but requires storing the full baseline distribution rather than just the mean. Added complexity for marginal benefit at this scale.

**Trade-offs accepted:**
- Drift detection is informational only — it does not route around the degraded PSP unless the circuit breaker also trips. This is intentional: degradation alone should trigger human review, not automatic exclusion.
- The rolling window of 50 transactions means recent high-volume PSPs update their drift status frequently, while low-volume PSPs may have stale windows.

---

## ADR-008 — Synthetic Data with Fixed Success Rates

**Decision:** Generate `payment_data.csv` with deterministic, fixed success rates per PSP (e.g. Relworx=0.75, Korapay=0.67) rather than random or sampled rates.

**Reason:**
Fixed success rates create a knowable ground truth that makes the system's performance measurable. If success rates were randomly drawn, the optimal PSP for a given country/method would be a moving target, and regret calculations would be comparing against a shifting baseline — making it impossible to say whether the system is learning or just tracking noise.

Fixed rates also allow the replay engine to compute a deterministic `best_psp` and `best_score` for every transaction, producing OSR and regret metrics that mean something. The bandit's job becomes: learn which PSP has which success rate through repeated observations, starting from the warm-start prior and refining through 10,000 simulated transactions.

The three-tier structure (0.75 / 0.67 / 0.60 / 0.55 / 0.45) creates clear signal gaps that a well-tuned bandit should be able to distinguish — not so large that learning is trivial, not so small that the signal is buried in noise.

**Alternatives considered:**
- **Randomly sampled success rates:** Harder to evaluate — you'd need to store the true rates used at generation time to compute regret accurately.
- **Real PSP data:** Ideal, but not available for a training project. Real data would also require compliance and data-sharing agreements.
- **Time-varying success rates (simulate degradation):** More realistic, but makes ground truth a moving target. Valuable for future work, but would require the replay engine to also record the ground-truth rate at each time step.

**Trade-offs accepted:**
- Fixed rates mean the simulation does not capture PSP variability over time, seasonality, or market events. The system is learning a static target, which is easier than the real-world problem.
- The three-tier cost/latency structure (premium/good/budget) is also fixed, which means the economic reward landscape does not change during training.

---

## ADR-009 — Maximum 3 Retry Attempts per Transaction

**Decision:** After a primary PSP failure, retry with the 2nd and then 3rd ranked PSPs from the bandit's routing decision, for a maximum of 3 total attempts per transaction.

**Reason:**
Payment UX research consistently shows that users abandon checkout after 2–3 failures. Retrying beyond 3 attempts adds latency cost (each attempt adds 600–1600ms) without meaningful conversion uplift. Three attempts covers the most common failure patterns: primary PSP outage (route to backup) and backup degradation (route to tertiary).

The retry sequence follows the bandit's own ranking — the 2nd and 3rd attempts are not random; they are the system's next-best choices given current knowledge. This means the bandit is updated on all three attempts, including failures on the fallback PSPs, which generates richer learning signal than a single binary outcome per transaction.

**Alternatives considered:**
- **1 attempt (no retry):** Maximises simplicity. Rejected because a single PSP failure that could have been recovered by a fallback now becomes a lost transaction with no learning signal from the recovery path.
- **2 attempts (1 retry):** Reasonable. Rejected in favour of 3 because the third attempt catches cases where both the primary and first fallback are simultaneously degraded — a plausible scenario during regional infrastructure events.
- **Unlimited retries until success:** Unbounded latency and cost. A transaction that routes through 5 PSPs has accumulated 5x the PSP fees even if only 1 succeeds. Also creates incentive to route to poor PSPs.
- **Fixed fallback list (not bandit-ranked):** Simpler, but ignores everything the bandit has learned. A hardcoded fallback PSP may be the worst choice given current market conditions.

**Trade-offs accepted:**
- Total reward per transaction is the sum of all attempt rewards. Transactions requiring 3 attempts accumulate 2 failure penalties before the success reward, which is correctly reflected as a higher cost in the economic reward function.
- The bandit is updated on each retry attempt, meaning failed fallback PSPs receive negative signals even though they were not the primary routing choice. This is intentional — the bandit should learn the reliability of all PSPs in the ranking, not just the top choice.

---

## ADR-010 — Economic Reward Instead of Binary Reward

**Decision:** Replace binary reward (1.0 for success, 0.0 for failure) with an economic reward function: `reward = revenue − psp_cost − latency_penalty` on success, and `reward = −(psp_cost + failure_cost + latency_penalty)` on failure, where `revenue = amount × 0.015`, `failure_cost = revenue × 0.5`, and `latency_penalty = latency_ms / 100,000`.

**Reason:**
Binary reward treats a $50 successful transaction identically to a $5,000 one, and treats routing to a $1.20/transaction budget PSP identically to a $2.50/transaction premium PSP. Neither is true in practice. Payment routing is ultimately a profit-optimisation problem, not an accuracy-maximisation problem.

The economic reward aligns the bandit's objective with business reality:
- A high-amount transaction routed to a premium PSP that succeeds generates more reward than a low-amount transaction, correctly reflecting revenue contribution.
- Routing to a budget PSP saves cost, which is reflected in higher reward even at the same success rate.
- Failures generate negative reward proportional to the revenue opportunity lost, not a flat zero. This makes the bandit averse to high-failure-rate PSPs in high-value transaction contexts specifically.

The latency penalty is deliberately small (dividing by 100,000) so it influences rankings at the margin without overriding success rate or cost signals.

**Alternatives considered:**
- **Binary reward (1.0 / 0.0):** Simple and widely used in bandit literature. Rejected because it optimises for success rate rather than profit. A PSP with 70% success rate and $1.20 cost may be more profitable than one with 80% success rate and $2.50 cost on low-value transactions — binary reward cannot capture this.
- **Success rate only with cost as a secondary filter:** Apply a cost cap, then maximise success rate within that cap. Simpler, but loses the smooth cost/reward trade-off that allows the system to prefer cheaper PSPs when success rates are similar.
- **Discounted reward (future transaction value):** More appropriate for full RL settings where routing today affects volume tomorrow (e.g. merchant churn). Out of scope for this system which treats each transaction independently.
- **Sharpe-ratio-style reward (reward / variance):** Penalises inconsistent PSPs even if their expected reward is high. Interesting for risk-averse routing, but adds complexity and requires tracking reward variance per PSP.

**Trade-offs accepted:**
- Economic rewards are on a different scale than binary rewards (roughly −3 to +0.75 vs 0 to 1). This required recalibrating the Q-Learning layer and circuit breaker logic, which were designed around 0–1 reward signals.
- The take rate (1.5%) and failure cost (50% of revenue) are fixed constants. In production these vary by merchant agreement, currency, and payment method.
- Small transactions generate small rewards even when successful, which slightly biases the bandit toward routing high-value transactions through premium PSPs — a deliberate design choice that mirrors how a real payment operation would prioritise high-value customers.
