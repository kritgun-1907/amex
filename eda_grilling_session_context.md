# Amex Campus Challenge 2026 — EDA Grilling Session Context

> **Purpose:** This document captures the key analytical decisions, frameworks, and reasoning established during the EDA grilling session. Drop this into any future Claude session to resume work without re-explaining the foundation.

---

## 0. The Core Mental Model

**Before writing any code, sort every feature into a P&L framework — not a statistical one.**

This is not a clustering problem. It is a reverse-engineering problem. Amex has already computed the true profitability of every cardmember. Your job is to reconstruct that ranking using only the 23 features and domain economics.

**Profit = Revenue − Cost**

The equation must be economically defensible for a Round 3 presentation to a decision scientist, not just leaderboard-optimal.

---

## 0a. Official Attribute Category Map (from competition PDF)

| Official Category | Meaning | Features |
|---|---|---|
| CM Spend & Balance | Industry level spends + revolve behavior | f1, f5, f6, f7, f8, f9, f10 |
| Benefit Usage | Lounge visit count + cab months utilized | f13, f14, f15, f16 |
| Engagement | Cancellation calls + website logins + cards held | f2, f3, f12, f19, f20 |
| Profile | Tenure + riskiness score | f11, + likely one masked tenure feature |

**Critical PM-level insight on f13 vs f15 data types:**
- f13 = **visit count** (integer 0–3) — cost per unit is fixed ~$30–50/visit
- f15 = **month count** (integer 0–11) — cost per unit is fixed $15/month
- f14 = **dollar amount** ($0–$200) — already in dollar terms
- f16 = **dollar amount** ($0–$64.40) — already in dollar terms, hard-capped

This matters for equation interpretation but NOT for rank-transform (rank handles both counts and dollars correctly).

---

## 1. Feature Classification (Revenue / Cost / Context)

| Feature | Description | Role | Notes |
|---|---|---|---|
| f1 | Avg Revolve Balance (12m) | **Revenue** | Interest income |
| f2 | Cancellation Calls (12m) | **Cost** | Servicing + churn signal |
| f3 | Cancellation Calls — Collections | **Cost** | Strong credit loss signal |
| f4 | Rewards Points Balance | **Cost (Liability)** | Future obligation, NOT realized — apply breakage discount |
| f5 | Total Spend (12m) | **Revenue** | Primary interchange anchor |
| f6 | Airlines Spend (12m) | **Revenue** | Higher interchange rate |
| f7 | Other Spend (12m) | **Revenue** | Lower interchange rate; has negatives (refunds) |
| f8 | Entertainment Spend (12m) | **Revenue** | Mid interchange |
| f9 | Lodging Spend (12m) | **Revenue** | Mid interchange |
| f10 | Dining Spend (12m) | **Revenue** | Higher interchange rate |
| f11 | Avg Risk Score (12m) | **Cost** | Expected loss driver |
| f12 | Login Counts | **Context** | Engagement proxy — do NOT let this dominate |
| f13 | Lounge Access — **visit count** (0–3) | **Cost** | COUNT of visits, NOT dollars. Each visit ~$30–50 issuer cost |
| f14 | Airline Credits Used — dollar amount ($0–$200) | **Cost** | Dollar amount; annual credit hard-capped at ~$200 |
| f15 | Cab Benefits — **months utilized** (0–11) | **Cost** | COUNT of months, NOT dollars. Actual cost ≈ f15 × $15 |
| f16 | Entertainment Credit Used — dollar amount ($0–$64.40) | **Cost** | Dollar amount; hard-capped; near-binary above 75th pct |
| f17 | Total Lend Line Amount | **Revenue (Capacity)** | NOT strictly ≥ f18 — treat independently |
| f18 | Consumer Lend Line Amount | **Revenue (Capacity)** | NOT strictly ≤ f17 — treat independently |
| f19 | Supplementary Accounts | **Context** | Profile signal |
| f20 | Active Charge Cards | **Context** | Profile signal |
| f21 | Rewards Points Redeemed (12m) | **Cost (Realized)** | Direct cash out — heaviest cost penalty |
| f22 | Emails Opened (6m) | **Context** | Engagement proxy — low weight |
| f23 | Emails Clicked (6m) | **Drop / Ignore** | 87.8% null — near-zero discriminatory power |

---

## 2. Key EDA Decisions

### 2.1 f4 (Rewards Balance) vs f21 (Points Redeemed) — Not Equal Penalties

- **f21** is a **realized cost** — points already redeemed, cash already out the door. Apply the heaviest negative weight.
- **f4** is an **accounting liability** — future obligation that may never be fully redeemed. Apply a discounted negative weight (breakage rate means a % of points expire unused).
- **Critical trap:** Do NOT give f4 a positive weight as a proxy for "high historical spend." Spend is already captured in f5–f10. Doing so double-counts revenue.

### 2.2 f5 vs f6–f10 — They Do NOT Reconcile

- Correlation between f5 and sum(f6:f10) is only **0.09**.
- Both are described as 12-month features — the mismatch is due to **independent masking and scaling** by Amex, not a temporal difference.
- **Do NOT build category-share features** (e.g., f6/f5) — the columns don't share the same mathematical space.
- **Strategy:** Use f5 as the primary gross spend anchor (high coverage). Treat f6–f10 as **independent behavioral modifiers** with differential interchange weights (airlines/dining weighted higher than other).

### 2.3 f17 vs f18 — No Hierarchy Assumption

- f17 ≥ f18 is only true **~63% of the time** among non-null rows.
- **Do NOT build f17 − f18** as a "business lend exposure" feature — it produces negative values for 37% of customers, which is economically impossible.
- Treat f17 and f18 as **independent, correlated capacity signals**.

### 2.4 f7 Negative Values

- Negative values (down to −275) represent **refunds and returns** — reversed interchange revenue.
- **Decision: Keep negatives. Do NOT floor at 0.**
- Rank-transforming the raw negative values correctly pushes these customers to low spend percentiles, which is economically accurate.

### 2.5 f16 Hard Cap

- f16 (Entertainment Credit Used) caps at **64.40** — 75th percentile = maximum.
- This feature becomes **near-binary in the top quartile**: everyone above the 75th percentile carries the identical cost burden.
- f16 cannot differentiate customers within the top 25%. Rely on f5 (spend) and f1 (revolve balance) to sort the top of the portfolio.

---

## 3. The Missingness Map — Structured Nulls (MNAR)

The nulls in this dataset are **NOT random**. They arrive in locked groups representing distinct customer segments.

| Group | Features | Null % | Interpretation |
|---|---|---|---|
| Rewards Group | f4, f21 | 51.4% | No recorded rewards activity — dormant, data-masked, or cashback sub-variant (NOT "not enrolled" — all Premier CMs earn 1x points by default) |
| Category Spend Group | f6–f10 | 23.1% | No spend in those premium categories |
| Benefits Group | f13–f16 | 2.7% | No Premier Card perk utilization |
| Lend Group | f17, f18 | 58–62% | Not approved for Plan It / lend product |

**Key insight:** Missing ≠ unknown. Missing = zero economic activity in that segment. Imputing with mean/median manufactures fake revenue or fake costs for customers who generated neither.

---

## 4. Imputation Policy (Locked)

| Feature Group | Null % | Fill Value | Justification |
|---|---|---|---|
| f4, f21 (Rewards) | 51.4% | **0** | No recorded rewards activity in data window — zero-activity assumption. NOT "no account" (all Premier CMs earn rewards). |
| f6–f10 (Category Spend) | 23.1% | **0** | No spend in those categories |
| f13–f16 (Benefits) | 2.7% | **0** | No perk utilization — zero cost to bank |
| f17, f18 (Lend Lines) | 58–62% | **0** | Not approved for lend product — zero exposure |
| f5 (Total Spend) | 1.3% | **Median** | Low null rate; truly unknown value |
| f11 (Risk Score) | 0.5% | **Median** | Low null rate; possibly new customer with no history |
| f23 (Emails Clicked) | 87.8% | **Drop / Ignore** | Near-empty column; no discriminatory power |

---

## 5. Normalization Strategy

**Choice: Rank-Transform (Percentile Scaling) — 0.0 to 1.0**

**Why not min-max:** Too sensitive to extreme outliers (f7 hits ~147,000; min-max squashes the rest of the distribution into near-zero).

**Why not z-score:** Assumes normal distribution. Financial spend data is right-skewed — z-score preserves skew distortion.

**Why rank-transform wins:** The competition metric is **% overlap of your top 20% vs Amex's top 20%** — a purely rank-based score. Rank-transforming features aligns the input scale directly with the evaluation mechanic. Absolute dollar magnitude is irrelevant; only relative ordering matters.

**Important distinction:** Rank-transform makes features equal in **scale**, not in **weight**. After transformation, the only levers are the coefficients you assign to each feature.

---

## 6. Profitability Equation Skeleton (Post-Normalization)

```
Profitability Score =
    + w_spend        × rank(f5)                          # gross spend anchor
    + w_airline      × rank(f6)                          # premium interchange
    + w_dining       × rank(f10)                         # premium interchange
    + w_other_spend  × rank(f7)                          # lower interchange
    + w_ent_spend    × rank(f8)
    + w_lodge        × rank(f9)
    + w_revolve      × rank(f1)                          # interest revenue
    + w_lend         × rank(f17)                         # lend capacity
    - w_pts_redeem   × rank(f21)                         # realized cost (heavy)
    - w_pts_bal      × rank(f4)                          # liability (discounted)
    - w_risk         × rank(f11)                         # expected loss
    - w_collections  × rank(f3)                          # hard credit loss signal
    - w_lounge       × rank(f13)                         # per-visit cost
    - w_airline_cred × rank(f14)                         # benefit cost
    - w_cab          × rank(f15)                         # benefit cost
    - w_ent_cred     × rank(f16)                         # benefit cost (binary above 75th)
    - w_cancel       × rank(f2)                          # servicing cost + churn
```

**Design principle:** Benefit-usage terms and risk terms must **subtract**. Any equation that rewards high benefit utilization has inverted economics.

---

## 7. Counterintuitive Core

The most profitable customer is:
- **High spending** (f5, f6, f10)
- **Moderately revolving** (f1)
- **Low risk** (f11 near zero)
- **Does NOT fully milk the benefits** (low f13, f14, f15, f16)
- **Does NOT redeem all points** (low f21)

A low-spend, high-risk customer who maxes every credit and redeems all points is a **loss-maker**, even if they look "engaged."

---

## 8. Open Decisions for Next Session

- [ ] Final coefficient weights for the equation (start with economic priors, tune one at a time)
- [ ] Whether to include f17/f18 given 58–62% null rate (0-fill + rank-transform may wash out signal)
- [ ] How to handle f3 (collections) — flat hard penalty vs large negative coefficient
- [ ] Whether f22 (emails opened, 18.9% null) adds meaningful signal or is pure noise
- [ ] Local validation split design — hold out 30% before touching public leaderboard
- [ ] f23 confirmation to drop (87.8% null)
- [ ] Category interchange weight ratios (airlines/dining vs other)

---

## 9. What NOT to Do

1. Do not train an ML model — there is no target column.
2. Do not sum raw un-normalized features — largest magnitude column silently dominates.
3. Do not mean/median-impute the structured-null groups — manufactures fake P&L.
4. Do not build f5 vs f6–f10 share features — they don't reconcile.
5. Do not assume f17 ≥ f18 or build a difference feature.
6. Do not reward benefit utilization — that rewards loss-makers.
7. Do not overfit the public leaderboard (70%) — private (30%) decides the outcome.
8. Do not give f4 a positive weight as a spend proxy — double-counts revenue already in f5–f10.

---

*Generated from EDA grilling session — July 2026. All statistics computed on the full 500,000-row dataset.*
