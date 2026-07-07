# CLAUDE.md — Amex Campus Challenge 2026 · Complete Project Brain

> Drop this file into any fresh Claude session and you are immediately at full context.
> Last updated: 2026-07-07 (v5 harness, effective-weight framework, f16 excluded).

---

## 0. What This Project Is

**American Express Campus Challenge 2026 — Round 1: "Measuring the Customer Profitability for Premier Product"**

- Hosted on Unstop. Run by Amex India Centre of Excellence (Decision Science / Analytics).
- **Goal:** Design a profitability equation that rank-orders 500,000 Premier cardmembers. Submit scores for all `unique_identifier`s on the Unstop template.
- **Evaluation metric:** % overlap between our top 20% and Amex's actual top 20% profitable customers. Purely rank-based. Absolute score values are irrelevant.
- **Public leaderboard:** scored on 70% of data, live. **Private leaderboard:** hidden 30%, revealed after Round 1 closes. Final rank = max score attained across submissions.
- **Max 10 submissions per team.** Amex flags gaming — the method must be defensible in a Round 3 presentation to a decision scientist.
- **Stakes:** Prizes + Pre-Placement Interviews (PPIs) for top performers. Primary goal = PPI / internship at Amex India CoE.

### Rounds
1. Round 1 — Data-driven profitability scoring (this repo)
2. Round 2 — Case-study competition
3. Round 3 — Deck submission and presentation to Amex

---

## 1. Files in This Repo

| File | Purpose |
|---|---|
| `6a3eb196bc7a3_campus_challenge_r1_data.csv` | Raw dataset — 500,000 rows × 24 cols (`id` + `f1`–`f23`) |
| `6a3eb1af6b994_feature_description.csv` | Feature code → description mapping |
| `eda_pipeline.py` | Phases 1–5: missingness → scale → cross-feature → imputation → zero-floor rank-transform. Produces `eda_outputs/data_imputed.csv` and `eda_outputs/data_ranked.csv` |
| `validation_harness.py` | v5 scoring engine: loads ranked file, back-solves raw weights, scores, validates, produces `eda_outputs/submission_scores_v5.csv` |
| `premier_card_profitability_framework.md` | Full economic justification for every coefficient (the Round 3 deck source) |
| `amex_campus_challenge_r1_context.md` | Full competition + dataset context pack |
| `eda_grilling_session_context.md` | EDA analytical decisions + grilling session notes |
| `eda_outputs/` | All pipeline outputs: ranked/imputed CSVs, plots, submission files, validation diagnostics |
| `.public/` | Amex competition PDF slides (product overview, attribute category map) |

---

## 2. The Core Conceptual Frame (what most teams get wrong)

- **There is no target column.** You cannot train a supervised model. There is no label to fit.
- Amex has computed true profitability internally from revenue/cost data they did NOT share.
- Our job: **reverse-engineer that ranking** using only the 23 masked features + card economics.
- The equation is a **structural P&L accounting engine**, not a fitted model.

```
Net Profitability = Gross Revenue − Direct Variable Costs − Expected Credit Loss
```

- The evaluation is **rank-based** (top 20% overlap), so rank-transforming every feature to [0, 1] directly aligns with the metric.
- **The counterintuitive core:** the most profitable customer is high-spending, moderately-revolving, low-risk, and does NOT milk the benefits. A high-spend high-benefit high-redemption customer who is risky is a loss-maker.

---

## 3. Dataset — Feature Dictionary

500,000 rows. 23 masked features + `id`. No PII.

| Feature | Description | Economic Role | Key Stats |
|---|---|---|---|
| `f1` | Avg Revolve Balance (12m) | **Revenue** — interest income ~20–30% APR | 53.2% zeros; max 17,968 |
| `f2` | Cancellation Calls (12m) | **Cost** — churn/servicing signal | 82.6% zeros; binary 0/1 |
| `f3` | Cancellation Calls — Collections | **HARD OVERRIDE** — near-certain loss | 89% zeros; binary 0/1; 54,304 have f3>0 |
| `f4` | Rewards Points Balance | **Cost** — deferred IFRS 15 liability | 51.4% null → 0-fill; max 697,899 |
| `f5` | Total Spend (12m) | **Revenue** — primary interchange anchor | 6.5% zeros; median 2,166; max 13,596 |
| `f6` | Airlines Spend (12m) | **Revenue** — premium interchange 2.3–3.3% | 34.4% zeros; 23.1% null group |
| `f7` | Other Spend (12m) | **Revenue** — generic 1.4–2.4% | 23.3% zeros; **has negatives** (min −275 = refunds) |
| `f8` | Entertainment Spend (12m) | **Revenue** — mid-tier | 47.2% zeros |
| `f9` | Lodging Spend (12m) | **Revenue** — mid-tier | 51.2% zeros |
| `f10` | Dining Spend (12m) | **Revenue** — premium 1.85–2.75% | 30.5% zeros |
| `f11` | Avg Risk Score (12m) | **Cost** — Expected Credit Loss anchor | 33% zeros; range 0–0.33 |
| `f12` | Login Counts | **Context** — excluded from equation | |
| `f13` | Lounge Access — **visit count** (0–3) | **Cost** — $24–32/visit | 73.7% zeros |
| `f14` | Airline Credits Used — **dollars** ($0–$200) | **Cost** — annual credit drain | 68% zeros |
| `f15` | Cab Benefits — **months utilized** (0–11) | **Cost** — $15/month partner cost | 34.5% zeros |
| `f16` | Entertainment Credit — **dollars** ($0–$64.40) | **EXCLUDED** — near-binary, hard-capped | 75th pct = max |
| `f17` | Total Lend Line Amount | **Revenue** — Plan-It trust signal | 58.5% null → 0-fill |
| `f18` | Consumer Lend Line Amount | **Revenue** — capacity signal | 61.9% null → 0-fill |
| `f19` | Supplementary Accounts | **Context** — excluded | |
| `f20` | Active Charge Cards | **Context** — excluded | |
| `f21` | Rewards Points Redeemed (12m) | **Cost** — realized ~1¢/pt | 72.2% zeros |
| `f22` | Emails Opened (6m) | **Context** — excluded | |
| `f23` | Emails Clicked (6m) | **DROPPED** — 87.8% null | |

### Critical Data Quirks
- **f5 ≠ sum(f6–f10).** Correlation only 0.09. They are independently masked/scaled. Never build `f6/f5` share features.
- **f17 ≥ f18 only ~63.5% of the time.** No hierarchy. Never build `f17 − f18`.
- **f7 has negative values** (down to −275) — legitimate refunds. Keep negatives; do not floor.
- **f16 is hard-capped at $64.40** — 75th percentile = max. Near-binary in top quartile. Excluded.
- **Structured null groups** (nulls arrive in locked groups — MNAR, not random):
  - f4 & f21 null together (51.4%) — no recorded rewards activity (NOT "not enrolled"; all Premier CMs earn 1x by default)
  - f6–f10 null together (23.1%) — no spend in premium categories
  - f13–f16 null together (2.7%) — no perk utilization
  - f17, f18 null independently (58–62%) — not approved for Plan-It lend product

---

## 4. Imputation Policy (Locked)

| Feature Group | Fill | Reason |
|---|---|---|
| f4, f21 (Rewards) | **0** | Zero recorded activity. NOT "not enrolled." |
| f6–f10 (Category Spend) | **0** | No spend in those categories |
| f13–f16 (Benefits) | **0** | No perk utilization → zero cost to bank |
| f17, f18 (Lend Lines) | **0** | Not approved for lend product |
| f5 (Total Spend) | **Median** | Low null rate (1.3%); genuinely unknown |
| f11 (Risk Score) | **Median** | Low null rate (0.5%); possibly new customer |
| f23 (Emails Clicked) | **Drop** | 87.8% null — zero discriminatory power |

Mean/median-imputing the structured-null groups manufactures fake P&L. Zero-fill is the correct economic interpretation.

---

## 5. Normalization — Zero-Floor Rank Transform

**Why rank-transform:** metric is top-20% overlap (purely rank-based), rank-transform aligns inputs with the evaluation mechanic, robust to extreme right-skew and scale explosion (f7 hits ~147,000).

**The zero-floor rule (critical):** customers with value = 0 get rank exactly **0.0** (hard floor), NOT the average rank of all tied zeros. Without this, 72% of f21 customers (all zero-redeemers) would receive rank ~0.36, inventing a phantom positive signal. Zero-floor ensures zero activity = zero contribution.

**Exception:** f7 uses standard rank because it has real negatives (refunds) that must rank below zero-spend customers.

**Implemented in:** `eda_pipeline.py` → `zero_floor_rank()` function (Phase 5). The harness includes a sanity check that aborts if the stale average-rank file is accidentally loaded.

---

## 6. The Scoring Equation — v5 (Current Best)

### Effective vs Raw Weights

A feature with 72% zeros only actively sorts 28% of the population. The weight you *state* (raw weight) ≠ the weight you *get* (effective sorting power). All weights are specified as **effective weights** (desired impact) and the harness back-solves the raw weight:

```
raw weight = effective weight / (1 - zero fraction) = effective weight / coverage
```

### PRE-FILTER
```
if f3 > 0 → INELIGIBLE
  Sinks to bottom of ordinary score range (NOT a -999 sentinel).
  54,304 customers excluded. Top 20% drawn from remaining 89%.
```

### Equation (all coefficients are EFFECTIVE weights)
```
Revenue:
  + 0.22 × rank(f5)     # total spend — primary interchange anchor (93.5% coverage)
  + 0.20 × rank(f1)     # revolve interest — NIM engine ~20-30% APR
  + 0.05 × rank(f6)     # airlines — premium interchange 2.3-3.3%
  + 0.03 × rank(f10)    # dining — premium interchange 1.85-2.75%
  + 0.03 × rank(f7)     # other spend — generic 1.4-2.4%
  + 0.015 × rank(f8)    # entertainment spend — mid-tier
  + 0.015 × rank(f9)    # lodging spend — mid-tier
  + 0.01 × rank(f17)    # lend capacity (Plan-It trust signal)
  + 0.01 × rank(f18)    # consumer lend capacity

Cost:
  - 0.26 × rank(f11)    # expected credit loss (heaviest penalty)
  - 0.10 × rank(f21)    # realized pts cost ~1¢/pt (kept below risk)
  - 0.09 × rank(f15)    # cab months $15/mo partner cost
  - 0.07 × rank(f4)     # deferred liability (IFRS 15 breakage-adj)
  - 0.07 × rank(f13)    # lounge per-visit $24-32
  - 0.05 × rank(f14)    # airline credit drain
  - 0.02 × rank(f2)     # retention overhead / churn signal

f16 EXCLUDED — hard-capped $64.40, near-binary in top quartile, no rank signal.
               No weight fixes the structural inversion.
```

**Effective weight totals:** Revenue = +0.575 | Cost = −0.560 | Net = +0.015

### Coverage Table (raw weights back-solved by harness)

| Feature | Zero % | Coverage | Effective W | Raw W |
|---|---|---|---|---|
| f1 | 53.2% | 46.8% | +0.20 | +0.427 |
| f5 | 6.5% | 93.5% | +0.22 | +0.235 |
| f6 | 34.4% | 65.6% | +0.05 | +0.076 |
| f7 | 23.3% | 76.7% | +0.03 | +0.039 |
| f8 | 47.2% | 52.8% | +0.015 | +0.028 |
| f9 | 51.2% | 48.8% | +0.015 | +0.031 |
| f10 | 30.5% | 69.5% | +0.03 | +0.043 |
| f17 | 58.5% | 41.5% | +0.01 | +0.024 |
| f18 | 61.9% | 38.1% | +0.01 | +0.026 |
| f11 | 33.0% | 67.0% | −0.26 | −0.388 |
| f21 | 72.2% | 27.8% | −0.10 | −0.360 |
| f15 | 34.5% | 65.5% | −0.09 | −0.137 |
| f4 | 51.4% | 48.6% | −0.07 | −0.144 |
| f13 | 73.7% | 26.3% | −0.07 | −0.266 |
| f14 | 68.0% | 32.0% | −0.05 | −0.156 |
| f2 | 82.6% | 17.4% | −0.02 | −0.115 |

---

## 7. Version History of the Equation

| Version | Key change | Issue it fixed |
|---|---|---|
| v3 | Initial weighted equation, average-rank normalization | Baseline |
| v4 | Added coverage back-solve concept, raw/effective distinction | Still running on stale average-rank file; f21 inflated to eff −0.12; f16 kept with rigged ±1.15 tolerance gate; used −999 sentinel for f3 |
| **v5 (current)** | Zero-floor ranked file (harness aborts if stale); eff weights; f21 held at −0.10; f16 fully excluded; f3 smooth bottom-rank (no −999) | All v4 defects fixed |

### v5 Corrections Over v4 in Detail
1. **Zero-floor file validation** — v4 ran on average-rank zeros (~0.36). v5 requires zero-floor ranked file; harness aborts with error if stale file detected.
2. **f21 not over-penalized** — v4 inflated f21 to eff −0.12 → top 20% was 95.6% rewards-dormant (equation was rewarding inactivity). v5 holds eff −0.10; dormancy in top 20% falls to ~86%, near population base rate.
3. **f16 excluded cleanly** — v4 kept f16 at −0.06 behind a ×1.15 tolerance gate. v5 drops f16 to weight 0 and states plainly: structurally undifferentiable feature. Gate removed.
4. **Smooth f3 override** — v4 used −999 sentinel. v5 sinks f3>0 customers to bottom of ordinary score range. Every row stays in-range; no red flag to Amex reviewers.

---

## 8. How to Run

### Step 1 — EDA Pipeline (run once, or after any data change)
```bash
python eda_pipeline.py
```
Produces:
- `eda_outputs/data_imputed.csv` — post-imputation, pre-rank
- `eda_outputs/data_ranked.csv` — zero-floor rank-transformed (this is what the harness needs)
- Plots: `p1_missingness_heatmap.png`, `p2_distributions.png`, `p3_*.png`, `p5_ranked_distributions.png`

### Step 2 — Validation Harness (run after any weight change)
```bash
python validation_harness.py
```
Produces:
- `eda_outputs/submission_scores_v5.csv` — the file to submit to Unstop
- `eda_outputs/validation_diagnostics_v5.png` — 6-panel diagnostic plot

**Before a real submission:** Set `SUBMISSION_COLUMNS` in `validation_harness.py` to match the exact Unstop template header. Confirm all gates pass and stability ≥80% at ±10%.

---

## 9. Validation Checks (built into harness)

**Sanity check:** Aborts if `data_ranked.csv` is the stale average-rank file (checks that zero-value rows have mean rank < 0.01 for f21, f13, f4, f15).

**Validation A — Perturbation Stability:** Perturbs all weights by ±5/10/20% (30 trials each). Target: ≥80% top-20% overlap at ±10%, ≥65% at ±20%.

**Validation B — Ablation:** Removes one feature at a time, measures % change in top-20% membership. Labels features as load-bearing (>5%), marginal (2–5%), or decorative (<2%).

**Validation C — Economic Gates (strict, no tolerance rigging):**
- 100% of top 20% have f3 = 0 (f3 override guard)
- Top 20% mean spend ≥ 1.5× bottom 80%
- Top 20% mean risk < bottom 80%
- Top 20% mean revolve ≥ bottom 80%
- ≥30% of top 20% are high-revolve AND low-risk (ideal archetype check)
- Top 20% mean lounge/airline credit/cab months/pts redeemed ≤ bottom 80% (benefit-inversion guard, strict)

---

## 10. Excluded Features and Why

| Feature | Reason |
|---|---|
| **f16** | Hard-capped at $64.40 (75th pct = max). Near-binary in top quartile — cannot differentiate best customers. Inversion cannot be fixed by any weight. |
| **f12** | Digital engagement proxy. A customer who logs in 100× but spends nothing is P&L-neutral. |
| **f22** | Marketing engagement. Predicts churn, not profit. |
| **f23** | 87.8% null. Near-zero discriminatory power. Dropped entirely. |
| **f19** | Spend footprint already captured in f5. Would double-count. |
| **f20** | Profile context only. No direct P&L impact. |

---

## 11. The 12 Things NOT to Do

1. Do NOT train an ML model — there is no target column.
2. Do NOT sum raw un-normalized features — largest magnitude column silently dominates.
3. Do NOT mean/median-impute structured-null groups — manufactures fake P&L.
4. Do NOT build `f5` vs `f6–f10` share features — correlation is only 0.09.
5. Do NOT assume f17 ≥ f18 or build a difference feature.
6. Do NOT reward benefit utilization — that rewards loss-makers.
7. Do NOT overfit the public leaderboard (70%) — private (30%) decides the outcome.
8. Do NOT give f4 a positive weight as a spend proxy — double-counts revenue already in f5–f10.
9. Do NOT use average-rank for zero-value customers — use zero-floor rank.
10. Do NOT set raw weights directly without checking coverage — always state effective weights and let the harness back-solve.
11. Do NOT use −999 sentinels in submission output — red flag to Amex reviewers, may break bounded-score templates.
12. Do NOT apply a tolerance gate to pass a known inversion — if a feature's inversion cannot be fixed (f16), exclude it.

---

## 12. What the Ideal Top-20% Customer Looks Like

- **High total spend** (f5) and **revolving balance** (f1)
- **Premium category spend** (airlines f6, dining f10)
- **Low risk score** (f11 near zero)
- **Zero collections calls** (f3 = 0, non-negotiable)
- **Low benefit utilization** (low f13 lounge, f14 airline credit, f15 cab months)
- **Low redemptions** (low f21 — high spenders earn points but don't redeem everything)
- **Not maxing every credit** — doing so flags a loss-maker, not a premium customer

---

## 13. Competition Strategy

- Use ≤3–4 of the 10 submission slots on the public leaderboard. Reserve the rest.
- Change ONE economic assumption at a time. Inspect who lands in top 20% for economic sanity.
- The public leaderboard is a sanity check, NOT an optimizer. The private 30% decides the outcome.
- The equation must be presentable to a decision scientist in Round 3. Defensibility > leaderboard rank.

---

## 14. Open Decisions (as of 2026-07-07)

- Whether to tweak weights further (f6 airlines vs f10 dining relative emphasis)
- Whether f17/f18 are adding signal or noise given 58–62% null (currently eff +0.01 each — marginal)
- Local CV validation result numbers (harness runs on a 30% random hold-out proxy)
- Actual public leaderboard score not yet recorded here

---

*All coefficient priors and interchange/point-value figures are modeling assumptions grounded in cited public sources — not Amex-published profitability numbers. Labeled as assumptions in any Round 3 deliverable.*
