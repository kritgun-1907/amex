# American Express Premier Card — Customer Profitability Framework

**Round 1: Measuring the Customer Profitability for Premier Product**

> A structural Profit & Loss (P&L) framework that reverse-engineers cardmember profitability from 23 masked attributes using domain economics. Every coefficient below is anchored to a real-world source, not fitted to a label — because there is no target column to fit.

---

## 1. Core Methodology

Unlike a supervised model that fits a curve to a target `y`, this framework builds a **pure structural accounting engine**. Amex has already computed the true profitability of every cardmember from revenue/cost data it did not share. Our job is to reconstruct that ranking using only the features and the economic identity:

$$\text{Net Profitability} = \text{Gross Revenue} - \text{Direct Variable Costs} - \text{Expected Credit Loss}$$

**Why rank-transform normalization:** The competition metric is % overlap between our top 20% and Amex's actual top 20% — a purely rank-based score. Rank-transforming every feature to `[0.0, 1.0]` aligns the input scale with the evaluation mechanic, is robust to the extreme right-skew of spend data (f7 hits ~147,000), and neutralizes the scale explosion that would otherwise let one large-magnitude column silently dominate.

**Zero-floor rank (critical):** The EDA pipeline uses a custom zero-floor rank transform. Customers with a zero value receive rank exactly 0.0 (hard floor), not the average rank of all tied zeros. This is essential: a feature with 72% zeros would otherwise assign those 72% a rank of ~0.36 (midpoint of the tied mass), inventing a phantom positive signal for zero-activity customers. The harness includes a sanity check that aborts if the stale average-rank file is accidentally used.

**Effective vs raw weights:** A feature with 72% zeros (f21) only actively sorts 28% of the population — the remaining 72% are all at rank 0.0 and contribute nothing to relative ordering. The weight you *state* (raw weight) therefore does not equal the weight you *get* (effective sorting power). To reason cleanly about economics, all weights are set as **effective weights** (the desired sorting impact) and the harness back-solves the raw weight automatically:

$$\text{raw weight} = \frac{\text{desired effective weight}}{1 - \text{zero fraction}} = \frac{\text{desired effective weight}}{\text{coverage}}$$

This ensures stated weights mean what they say. All coefficients in this document are **effective weights**.

---

## 2. The Final Scoring Equation (v5 — effective-weight design, f3 override, f16 excluded)

> **v5 corrections over v4:**
>
> **Correction 1 — Zero-floor file validation:** v4 ran on `data_ranked.csv` built with average-rank (zeros sat at ~0.36, not 0.0). The entire coverage back-solve rested on a floor that did not exist. v5 requires the zero-floor ranked file produced by `eda_pipeline.py` Phase 5, and the harness aborts with a clear error if the stale average-rank file is detected.
>
> **Correction 2 — f21 not over-penalised:** With average-rank zeros (v4), inflating f21 to raw −0.43 produced a top 20% that was 95.6% rewards-dormant — the equation was *rewarding* inactivity (zero redeemers got a free pass). With the correct zero-floor file, the economically defensible effective weight for f21 is −0.10 (realized ~1c/pt cost, kept below credit risk in importance). Dormancy in the top 20% falls to ~86%, near the population base rate.
>
> **Correction 3 — f16 excluded cleanly:** v4 kept f16 at −0.06 behind a x1.15 tolerance gate that existed only to pass a known inversion. f16 is hard-capped at $64.40 and near-binary in the top quartile — it carries no rank signal there and no weight fixes the inversion. v5 drops f16 to weight 0 and states plainly: it is a structurally undifferentiable feature. The tolerance gate is removed; the harness prints a transparency note on f16's raw ratio instead.
>
> **Correction 4 — Smooth override (no −999 sentinel):** f3>0 customers are now bottom-ranked within the ordinary score range rather than assigned a −999 sentinel. The sentinel was a red flag to Amex reviewers and could break a bounded-score submission template.

**PRE-FILTER (applied before scoring):**
```
if f3 > 0 → INELIGIBLE (collections = near-certain loss; hard knock-out)
             Score is sunk to bottom of ordinary range — not a -999 sentinel.
             54,304 customers excluded; the top 20% is drawn from the remaining 89%.
```

**SCORING EQUATION — all coefficients are EFFECTIVE weights:**
```
(Raw weights are back-solved by the harness: raw = effective / coverage)

Revenue:
    + 0.20 * rank(f1)      # Revolve Interest — NIM engine ~20-30% APR
    + 0.22 * rank(f5)      # Total Spend — primary interchange anchor
    + 0.05 * rank(f6)      # Airlines Spend — premium 2.3-3.3%
    + 0.03 * rank(f10)     # Dining Spend — premium 1.85-2.75%
    + 0.03 * rank(f7)      # Other Spend — generic 1.4-2.4%
    + 0.015 * rank(f8)     # Entertainment Spend — mid-tier
    + 0.015 * rank(f9)     # Lodging Spend — mid-tier
    + 0.01 * rank(f17)     # Total Lend Capacity — Plan-It trust signal
    + 0.01 * rank(f18)     # Consumer Lend Capacity

Cost:
    - 0.26 * rank(f11)     # Expected Credit Loss — Basel III PD × EAD (heaviest)
    - 0.10 * rank(f21)     # Realized Pts Cost ~1c/pt (below risk; not inflated)
    - 0.09 * rank(f15)     # Cab Benefit Drain — $15/mo partner cost
    - 0.07 * rank(f4)      # Deferred Reward Liability — IFRS 15 breakage-adj
    - 0.07 * rank(f13)     # Lounge Cost — per-visit $24-32
    - 0.05 * rank(f14)     # Airline Credit Drain — annual credit cap
    - 0.02 * rank(f2)      # Retention Overhead — churn signal

f16 EXCLUDED — hard-capped $64.40, near-binary above 75th pct, no top-quartile rank signal.
               No weight resolves the structural inversion. Exclusion is the correct call.
```

**Effective weight totals (= actual sorting power):**
Revenue = +0.575 | Cost = −0.560 | Net = +0.015

**Coverage table (zero fraction → raw weight back-solved by harness):**

| Feature | Zero % | Coverage | Effective W | Raw W (computed) |
|---|---|---|---|---|
| f1 | 53.2% | 46.8% | +0.20 | +0.427 |
| f5 | 6.5% | 93.5% | +0.22 | +0.235 |
| f6 | 34.4% | 65.6% | +0.05 | +0.076 |
| f10 | 30.5% | 69.5% | +0.03 | +0.043 |
| f7 | 23.3% | 76.7% | +0.03 | +0.039 |
| f8 | 47.2% | 52.8% | +0.015 | +0.028 |
| f9 | 51.2% | 48.8% | +0.015 | +0.031 |
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

## 3. Revenue Drivers — Weight Justifications

*All weights are EFFECTIVE weights (desired sorting power). Raw weights are computed by the harness as raw = effective / coverage.*

### f1 · Average Revolve Balance (12m) → effective **+0.20** *(v4 eff: +0.201)*
Primary Net Interest Margin engine. Outstanding balances carried month-to-month accrue high-margin interest. Premium revolving APRs run roughly **19.99%–29.99%**, versus interchange swipe fees that average only **~2%–3%**. A dollar of revolving balance therefore yields on the order of **10x** the gross revenue of a dollar of transactional volume — making f1 the strongest revenue-positive anchor, provided it is counterbalanced by risk.
Coverage: 46.8% → back-solved raw = **+0.427**

*Source: standard premium credit card financial disclosures / APR schedules.*

### f5 · Total Spend (12m) → effective **+0.22** *(v4 eff: +0.224)*
Baseline gross interchange engine — the merchant discount revenue proxy before category enhancements. Amex premium processing costs merchants roughly **2.50% + $0.10** per transaction (Amex Premium tier). f5 has only 6.5% zeros and 93.5% coverage, making it the most powerful individual lever in the equation (raw ≈ effective).
Coverage: 93.5% → back-solved raw = **+0.235**

*Source: Amex OptBlue / premium network fee schedules; retail comparison — Amex Premium 2.85% total fee on $500 = $14.45 vs. Visa Signature $12.40.*

### f6 · Airlines Spend (12m) → effective **+0.05**
Premium-tier interchange bonus. Airline MCCs (**3000–3299 & 4511**) sit at the top of the fee spectrum, typically **2.30%–3.30%**, driven by large ticket sizes and premium travel economics. A dollar here is structurally more valuable than generic spend.
Coverage: 65.6% → back-solved raw = **+0.076**

*Source: Amex MCC wholesale discount rate manual; Travel & Entertainment wholesale rate 2.40% on transactions > $1,000.*

### f7 · Other Spend (12m) → effective **+0.03**
Generic retail/services volume. Processes at a lower baseline of **1.43%–2.40% + $0.10** (Retail MCC 5000–5999). Profitable but without premium margins.
**Negative values (down to −275) are legitimate refunds/returns and are kept, not floored** — rank-transform correctly pushes these customers to low spend percentiles.
Coverage: 76.7% → back-solved raw = **+0.039**

*Source: retail/everyday merchant interchange schedules; Amex "Other" wholesale rate 1.60%–2.00%.*

### f10 · Dining Spend (12m) → effective **+0.03**
High-velocity lifestyle interchange bonus. Dining MCCs (**5812 & 5814**) run **1.85%–2.75% + $0.10**, scaled by ticket size. Strong indicator of an active premium lifestyle user.
Coverage: 69.5% → back-solved raw = **+0.043**

*Source: Amex restaurant fee schedule.*

### f8 · Entertainment Spend & f9 · Lodging Spend (12m) → effective **+0.015 each**
Secondary vertical interchange modifiers commanding solid margins (~2.00%–2.40%). Clear supplementary signals of an affluent, high-spending profile.
f8 coverage: 52.8% → raw +0.028 | f9 coverage: 48.8% → raw +0.031

### f17 · Total Lend Line & f18 · Consumer Lend Line → effective **+0.01 each**
Approved borrowing capacity / underwriting-trust signals (Plan-It). Capacity does not earn interest on its own, so the weight is minimal — but a large lend line means Amex's internal risk models have vetted and trusted the customer.
**No hierarchy assumed:** f17 ≥ f18 holds only ~63.5% of the time, confirming independent masking.
f17 coverage: 41.5% → raw +0.024 | f18 coverage: 38.1% → raw +0.026

---

## 4. Cost & Risk Drivers — Weight Justifications

*All weights are EFFECTIVE weights. Raw weights are computed by the harness as raw = effective / coverage.*

### f11 · Average Risk Score (12m) → effective **−0.26** (heaviest cost) *(v4 eff: −0.281)*
Expected Credit Loss anchor. Default is catastrophic — it wipes out all associated revenue:

$$\text{Expected Loss} = \text{PD (Risk Score)} \times \text{EAD (Outstanding Balance)}$$

A single default obliterates the interchange profit generated by dozens of high-spending transactors, so f11 carries the most aggressive negative weight to keep high-risk revolvers out of the top tier.
Coverage: 67.0% → back-solved raw = **−0.388**

*Source: Basel III risk-weighted-assets framework; bank credit-loss provisioning standards.*

### f3 · Collections-Related Cancellation Calls → **HARD OVERRIDE** *(original weight: −0.25)*
Active delinquency / near-certain-loss signal — the customer has crossed from *predicted* risk into a *realized* operational loss threat.

**Why override instead of weight:** f3 is binary in practice (89% of customers have f3=0). A linear weight only engages 11% of the population and produces only 2.6% ablation impact. Any customer with f3 > 0 cannot be profitable regardless of spend or revolve. The override sinks f3>0 customers to the bottom of the ordinary score range (no −999 sentinel) — every row stays in-range and the top 20% is drawn entirely from the remaining 89%. 54,304 customers excluded.

*Source: retail-bank debt collection & Net Charge-Off standard operating procedures.*

### f21 · Rewards Points Redeemed (12m) → effective **−0.10** *(v4: inflated to eff −0.120)*
Realized variable rewards expense — hard cash leaving the bank to pay partners. Redeemed points are valued at **~1.0 cent per point** (flight redemptions via Amex Travel 1.0¢; Pay-with-Points ~0.7¢).

**Why effective −0.10 (not inflated):** v4 set effective −0.12 which drove the top 20% to 95.6% rewards-dormant — the equation was rewarding inactivity (zero-redeemers got a free pass). High spenders redeem *because* they spend; over-penalising redemption suppresses the wrong customers. Effective −0.10 keeps f21 below f11 in importance (credit risk > rewards cost) while still penalizing aggressive redemption. Dormancy in the top 20% falls to ~86%, near the population base rate.
Coverage: 27.8% → back-solved raw = **−0.360**

*Source: Amex Membership Rewards program terms; redemption examples — 50,000 points = $500 flight (1.0¢/pt).*

### f15 · Cab Benefits Used (months, 0–11) → effective **−0.09** *(v4 eff: −0.098)*
Partner credit expense. This is a **months-utilized count, not dollars** — structured as **$15/month + a $20 December bonus** (Amex Platinum Uber Cash: $15 monthly + $20 in December = up to $200/year). Credits expire monthly at 11:59 PM HST, triggering high organic breakage.

**Benefit inversion resolved:** With old v3 raw weight −0.08 (eff −0.052), the spend reward was dragging high-spend cab users into the top 20% (top 20% mean 3.98 months vs bottom 80% mean 3.86). Coverage-adjusted effective −0.09 eliminates this: top 20% mean = 3.11 vs bottom 80% mean = 4.09 — correctly lower.
Coverage: 65.5% → back-solved raw = **−0.137**

*Source: Amex Platinum Uber Cash / Uber One benefit disclosures.*

### f4 · Rewards Points Balance → effective **−0.07** *(v4 eff: −0.083)*
Deferred revenue liability. Under IFRS 15 / GAAP, unredeemed points sit on the balance sheet as a liability — discounted by an estimated **15%–20% breakage rate**. Set below f21 (realized cost) to reflect that outstanding balance may never be fully redeemed.
**Not given a positive weight** as a spend proxy — spend is already captured in f5–f10.
Coverage: 48.6% → back-solved raw = **−0.144**

*Source: IFRS 15 / GAAP deferred reward liability standards. Breakage is driven by forfeiture on delinquency/cancellation, not time expiry.*

### f13 · Lounge Access Count (0–3) → effective **−0.07** *(v4 eff: −0.071)*
Fixed per-usage variable cost. This is a **visit count, not dollars** — each lounge swipe costs the issuer a wholesale operator fee of roughly **$24–$32** (Priority Pass USD 32 per additional guest visit). Frequent exploitation generates substantial direct cost.
Coverage: 26.3% → back-solved raw = **−0.266**

*Source: Priority Pass / Centurion issuer partnership terms — USD 32 guest visit fee.*

### f14 · Airline Credits Used ($0–$200) → effective **−0.05** *(v4 eff: −0.051)*
Ancillary travel-credit direct cost — statement reimbursements up to a fixed annual cap (hard-capped at $200 in data). Benefit inversion guard: top 20% mean should be lower than bottom 80% mean.
Coverage: 32.0% → back-solved raw = **−0.156**

### f16 · Entertainment Credit Used ($0–$64.40) → **EXCLUDED** *(v4: −0.06 raw)*
Hard-capped at $64.40 (75th percentile = maximum). **Near-binary in the top quartile** — everyone above the 75th percentile carries the identical cost, so it cannot differentiate the best customers from each other. No weight eliminates the structural inversion (the top 20% are high spenders who also use this credit). Excluding it is the correct call. The harness reports f16's raw top/bottom ratio for transparency but does not gate it.

### f2 · Cancellation Calls (12m) → effective **−0.02** *(v4 eff: −0.021)*
Churn-intention and retention-cost indicator. Retention specialists offer statement credits, fee waivers, or point bundles, so these calls proxy fee leakage plus servicing overhead.
Coverage: 17.4% → back-solved raw = **−0.115**

*Source: credit card retention operations disclosures.*

---

## 5. Excluded Features (Weight = 0.0)

| Feature | Reason for exclusion |
|---|---|
| **f16** — Entertainment credit ($0–$64.40) | **Hard-capped, near-binary.** Structurally undifferentiable in the top quartile — everyone above the 75th pct carries the same cost. Benefit inversion cannot be resolved by any weight because the highest spenders (who we want in top 20%) also use this credit. Excluding is cleaner than a rigged tolerance gate. |
| **f12** — Login counts | Digital engagement, not asset-level profitability. A customer who logs in 100x but spends nothing is P&L-neutral. |
| **f22** — Emails opened | Marketing engagement signal; predicts churn, not profit. |
| **f23** — Emails clicked | **87.8% null** — structurally useless, near-zero discriminatory power. |
| **f19** — Supplementary accounts | Spend footprint already captured in f5; independent weight would double-count. |
| **f20** — Active charge cards | Profile context only; no direct P&L impact. |

---

## 6. Imputation Policy (Structured Nulls = MNAR)

Nulls arrive in **locked groups** representing distinct customer segments — missing means *no economic activity*, not *unknown*. Mean/median-imputing these groups would manufacture fake revenue or fake cost.

| Feature group | Null % | Fill | Justification |
|---|---|---|---|
| f4, f21 (rewards) | 51.4% | **0** | No recorded rewards activity in window. **Not** "not enrolled" — all Premier CMs earn 1x by default; likely dormant, masked, or cashback sub-variant. |
| f6–f10 (category spend) | 23.1% | **0** | No spend in those premium categories. |
| f13–f16 (benefits) | 2.7% | **0** | No perk utilization → zero cost to issuer. |
| f17, f18 (lend lines) | 58–62% | **0** | Not approved for Plan-It → zero exposure. |
| f5 (total spend) | 1.3% | **Median** | Low null rate; genuinely unknown value. |
| f11 (risk score) | 0.5% | **Median** | Low null rate; possibly new customer with no history. |
| f23 (emails clicked) | 87.8% | **Drop** | Near-empty; no signal. |

---

## 7. The Counterintuitive Core

The most profitable cardmember is **high-spending, moderately-revolving, low-risk, and does NOT fully milk the benefits or redeem all points**. A low-spend, high-risk customer who maxes every credit, visits the lounge repeatedly, and redeems every point is a **loss-maker** — even though they look "engaged" and "premium."

This is why every benefit-usage and risk term **subtracts**. Any equation that rewards high benefit utilization has inverted the economics.

---

## 8. Source Ledger

| # | Source | Used for |
|---|---|---|
| 1 | Amex merchant processing fee range (1.43%–3.30% + $0.10, all-in avg 2.35%–2.85%) | f5, f7 baseline interchange |
| 2 | Amex MCC wholesale discount rate manual (Airline 2.3%–3.3%; Dining 1.85%–2.75%; T&E 2.40% >$1k; Retail 1.43%–2.40%) | f6, f10, f8, f9 category weights |
| 3 | Premium rewards card comparison (Amex Premium 2.85% total on $500 = $14.45) | f5 vs. competitors |
| 4 | Amex Membership Rewards redemption terms (flights 1.0¢/pt, Pay-with-Points 0.7¢, gift cards ≤1.0¢) | f21 realized cost |
| 5 | IFRS 15 / GAAP deferred reward liability + 15–20% breakage | f4 liability discount |
| 6 | Priority Pass terms — USD 32 guest visit fee | f13 per-visit cost |
| 7 | Amex Platinum Uber benefit — $15/mo + $20 Dec, monthly HST expiry | f15 cab cost & breakage |
| 8 | Basel III RWA / bank credit-loss provisioning | f11 expected loss |
| 9 | Retail-bank collections / NCO procedures | f3 delinquency penalty |
| 10 | Premier Card product slide (annual fee $500–750, credit structures, caps) | product economics baseline |

---

*Coefficient priors and interchange/point-value figures are modeling assumptions grounded in the cited public sources — they are not Amex-published profitability numbers, and are labeled as assumptions in any Round 3 deliverable. The framework is fully transparent, scalable, and built to hold up on the hidden 30% private leaderboard and in a decision-scientist presentation.*
