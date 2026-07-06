# American Express Premier Card — Customer Profitability Framework

**Round 1: Measuring the Customer Profitability for Premier Product**

> A structural Profit & Loss (P&L) framework that reverse-engineers cardmember profitability from 23 masked attributes using domain economics. Every coefficient below is anchored to a real-world source, not fitted to a label — because there is no target column to fit.

---

## 1. Core Methodology

Unlike a supervised model that fits a curve to a target `y`, this framework builds a **pure structural accounting engine**. Amex has already computed the true profitability of every cardmember from revenue/cost data it did not share. Our job is to reconstruct that ranking using only the features and the economic identity:

$$\text{Net Profitability} = \text{Gross Revenue} - \text{Direct Variable Costs} - \text{Expected Credit Loss}$$

**Why rank-transform normalization:** The competition metric is % overlap between our top 20% and Amex's actual top 20% — a purely rank-based score. Rank-transforming every feature to `[0.0, 1.0]` aligns the input scale with the evaluation mechanic, is robust to the extreme right-skew of spend data (f7 hits ~147,000), and neutralizes the scale explosion that would otherwise let one large-magnitude column silently dominate.

---

## 2. The Final Scoring Equation (v4 — coverage-adjusted, f3 override)

> **v4 structural fixes over v3:**
>
> **Fix 1 — f3 Hard Override:** f3 (collections) had raw weight −0.25 but only 2.6% ablation impact because 89% of customers have f3=0. A linear weight only engages 11% of the population and is nearly ineffective. Fix: knock-out pre-filter — any customer with f3 > 0 receives score = −999 and is excluded from top 20% entirely. 54,304 collections customers now permanently ineligible.
>
> **Fix 2 — Coverage-Adjusted Weights:** Zero-floor rank gives rank 0.0 to all zero-value customers. A feature with 72% zeros (f21) only sorts 28% of the population — its nominal weight of −0.18 produced an effective sorting impact of only −0.050. To achieve the *intended* effective impact, raw weights must be back-solved: `raw = desired_effective / (1 − zero_fraction)`. Key corrections: f21: −0.18 → −0.43 | f13: −0.12 → −0.27 | f14: −0.08 → −0.16 | f15: −0.08 → −0.15.
>
> **Fix 3 — Benefit Inversion Resolved:** v3 top 20% had higher cab (f15) and entertainment credit (f16) usage than bottom 80% — the spend reward (effective +0.234) was drowning out benefit penalties (effective −0.052 on f15). After coverage adjustment, f15 effective = −0.098 and the inversion is eliminated. f16 has a residual 12.9% ratio (57.2 vs 50.7 mean) but this is structurally unavoidable: f16 is hard-capped at $64.40 with 97.3% coverage and the economic delta is only $6.34/year versus $57/year interchange premium from the spend difference.

**PRE-FILTER (applied before scoring):**
```
if f3 > 0 → INELIGIBLE (collections = near-certain loss; hard knock-out)
```

**SCORING EQUATION (applied to eligible customers only):**
```
Profitability Score =
    + 0.43 * rank(f1)      # Revolve Interest (NIM engine, ~20-30% APR)
    + 0.24 * rank(f5)      # Base Interchange Spend — primary anchor
    + 0.08 * rank(f6)      # Airlines Spend — premium interchange 2.3-3.3%
    + 0.04 * rank(f10)     # Dining Spend — premium interchange 1.85-2.75%
    + 0.03 * rank(f7)      # Other Spend — generic 1.4-2.4%
    + 0.03 * rank(f8)      # Entertainment Spend — mid-tier
    + 0.03 * rank(f9)      # Lodging Spend — mid-tier
    + 0.02 * rank(f17)     # Total Lend Capacity (Plan-It trust signal)
    + 0.03 * rank(f18)     # Consumer Lend Capacity

    - 0.42 * rank(f11)     # Expected Credit Loss (Basel III PD × EAD)
    - 0.43 * rank(f21)     # Realized Pts Redemption Cost ~1c/pt  ← adj for 28% coverage
    - 0.27 * rank(f13)     # Lounge Cost $24–32/visit             ← adj for 26% coverage
    - 0.17 * rank(f4)      # Deferred Reward Liability (IFRS 15 breakage-adj)
    - 0.16 * rank(f14)     # Airline Credit Drain ($0–$200 cap)   ← adj for 32% coverage
    - 0.15 * rank(f15)     # Cab Benefit Drain $15/month          ← adj for 65% coverage
    - 0.06 * rank(f16)     # Entertainment Credit (near-binary, hard-capped $64.40)
    - 0.12 * rank(f2)      # Retention Overhead / Churn Calls     ← adj for 17% coverage
```

**Effective weight totals** (raw × coverage = actual sorting impact):
Revenue effective = +0.579 | Cost effective = −0.783 | Net effective = −0.204

**Raw weight totals:** Revenue = +0.93 | Cost = −1.78 (asymmetry is intentional — high-zero cost features need inflated raw weights to deliver intended effective impact)

**Load-bearing features** (ablation impact >5%): f1 (39.9%), f11 (38.5%), f5 (22.1%), f21 (21.8%), f13 (15.7%), f15 (15.6%), f4 (16.7%), f14 (11.2%), f6 (8.1%), f2 (7.5%)

**Excluded (weight = 0.0):** f12 (logins), f22 (emails opened), f23 (emails clicked — 87.8% null), f19 (supplementary accounts), f20 (active charge cards). These are engagement/profile signals, not profit drivers, and folding them in either dilutes the financial signal or double-counts spend already captured in f5.

---

## 3. Revenue Drivers — Weight Justifications

### f1 · Average Revolve Balance (12m) → **+0.43** *(v3: +0.45)*
Primary Net Interest Margin engine. Outstanding balances carried month-to-month accrue high-margin interest. Premium revolving APRs run roughly **19.99%–29.99%**, versus interchange swipe fees that average only **~2%–3%**. A dollar of revolving balance therefore yields on the order of **10x** the gross revenue of a dollar of transactional volume — making f1 the strongest revenue-positive anchor, provided it is counterbalanced by risk.

*Source: standard premium credit card financial disclosures / APR schedules.*

### f5 · Total Spend (12m) → **+0.24** *(v3: +0.25)*
Baseline gross interchange engine — the merchant discount revenue proxy before category enhancements. Amex premium processing costs merchants roughly **2.50% + $0.10** per transaction (Amex Premium tier), higher than Visa Signature (~2.44%) and World Elite Mastercard (~2.55%). Absolute transaction volume sets the organic profitability floor.

*Source: Amex OptBlue / premium network fee schedules; retail comparison — Amex Premium 2.85% total fee on $500 = $14.45 vs. Visa Signature $12.40.*

### f6 · Airlines Spend (12m) → **+0.02** *(v1: 0.08)*
Premium-tier interchange bonus. Airline MCCs (**3000–3299 & 4511**) sit at the top of the fee spectrum, typically **2.30%–3.30%**, driven by large ticket sizes and premium travel economics. A dollar here is structurally more valuable than generic spend.

*Source: Amex MCC wholesale discount rate manual; Travel & Entertainment wholesale rate 2.40% on transactions > $1,000.*

### f7 · Other Spend (12m) → **+0.02** *(v1: 0.05)*
Generic retail/services volume. Processes at a lower baseline of **1.43%–2.40% + $0.10** (Retail MCC 5000–5999). Profitable but without premium margins.
**Negative values (down to −275) are legitimate refunds/returns and are kept, not floored** — rank-transform correctly pushes these customers to low spend percentiles.

*Source: retail/everyday merchant interchange schedules; Amex "Other" wholesale rate 1.60%–2.00%.*

### f10 · Dining Spend (12m) → **+0.02** *(v1: 0.04)*
High-velocity lifestyle interchange bonus. Dining MCCs (**5812 & 5814**) run **1.85%–2.75% + $0.10**, scaled by ticket size (large checks trigger premium tiers — e.g. Restaurant wholesale rate jumps to 2.40% above $200). Strong indicator of an active premium lifestyle user.

*Source: Amex restaurant fee schedule.*

### f8 · Entertainment Spend & f9 · Lodging Spend (12m) → **+0.01 each** *(v1: 0.04 each)*
Secondary vertical interchange modifiers commanding solid margins (~2.00%–2.40%). Clear supplementary signals of an affluent, high-spending profile.

### f17 · Total Lend Line & f18 · Consumer Lend Line → **+0.02 each**
Approved borrowing capacity / underwriting-trust signals (Plan-It). Capacity does not earn interest on its own, so the weight is minimal — but a large lend line means Amex's internal risk models have vetted and trusted the customer.
**No hierarchy assumed:** f17 ≥ f18 holds only ~63.5% of the time, confirming independent masking. Difference features would produce nonsensical negatives, so both are treated as standalone capacity signals.

---

## 4. Cost & Risk Drivers — Weight Justifications

### f11 · Average Risk Score (12m) → **−0.42** (heaviest) *(v3: −0.50)*
Expected Credit Loss anchor. Default is catastrophic — it wipes out all associated revenue:

$$\text{Expected Loss} = \text{PD (Risk Score)} \times \text{EAD (Outstanding Balance)}$$

A single default obliterates the interchange profit generated by dozens of high-spending transactors, so f11 carries the most aggressive negative weight to keep high-risk revolvers out of the top tier.

*Source: Basel III risk-weighted-assets framework; bank credit-loss provisioning standards.*

### f3 · Collections-Related Cancellation Calls → **HARD OVERRIDE** *(v3: −0.25 weight)*
Active delinquency / near-certain-loss signal — the customer has crossed from *predicted* risk into a *realized* operational loss threat.

**Why override instead of weight:** f3 is binary in practice (89% of customers have f3=0). A linear weight of −0.25 only engages 11% of the population and produces only 2.6% ablation impact. Any customer with f3 > 0 cannot be profitable regardless of spend or revolve — they are in active collections. A hard knock-out pre-filter is economically correct and eliminates the "wasted weight" problem. 54,304 customers are permanently excluded.

*Source: retail-bank debt collection & Net Charge-Off standard operating procedures.*

### f21 · Rewards Points Redeemed (12m) → **−0.43** *(v3: −0.18)*
Realized variable rewards expense — hard cash leaving the bank to pay partners. Redeemed points are valued at a fixed internal liability of **~1.0 cent per point** (flight redemptions via Amex Travel hit 1.0¢; Pay-with-Points ~0.7¢; the 1.0¢ ceiling is the conservative cost assumption). High redemption = maximum program-value extraction = expensive customer.

**Why −0.43 raw weight (was −0.18):** f21 has 72.2% zeros — only 27.8% of customers have any redemptions. The zero-floor rank assigns all 72% a score of 0.0, so f21 only actively sorts 28% of the population. With a raw weight of −0.18, the effective sorting impact is only −0.18 × 0.278 = −0.050. To achieve the intended effective impact of −0.12 (major cost driver), the raw weight must be back-solved: −0.12 / 0.278 = **−0.43**.

*Source: Amex Membership Rewards program terms; redemption examples — 50,000 points = $500 flight (1.0¢/pt).*

### f4 · Rewards Points Balance → **−0.17** *(v3: −0.14)*
Deferred revenue liability. Under IFRS 15 / GAAP, unredeemed points sit on the balance sheet as a liability — but discounted by an estimated **15%–20% breakage rate** (points that expire/forfeit). Weighted at **~80% of f21** (0.16 / 0.20 = 0.80) to mirror that breakage adjustment.
**Not given a positive weight** as a spend proxy — spend is already fully captured in f5–f10, and doing so would double-count revenue.

*Source: IFRS 15 / GAAP deferred reward liability standards. Note: MR points don't expire while the account is enrolled and in good standing, so breakage is driven by forfeiture on delinquency/cancellation rather than time expiry.*

### f13 · Lounge Access Count (0–3) → **−0.27** *(v3: −0.12)*
Fixed per-usage variable cost. This is a **visit count, not dollars** — each lounge swipe costs the issuer a wholesale operator fee of roughly **$24–$32** (Priority Pass charges USD 32 per additional guest visit). Frequent exploitation generates substantial direct cost.

**Why −0.27 raw weight (was −0.12):** f13 has 73.7% zeros (count feature 0–3). Only 26.3% of customers visit the lounge at all. Effective impact of −0.12 raw = −0.032 — nearly invisible. Back-solved for effective target −0.07: −0.07 / 0.263 = **−0.27**. After adjustment, f13 has 15.7% ablation impact (was 9.4%).

*Source: Priority Pass / Centurion issuer partnership terms — USD 32 guest visit fee.*

### f14 · Airline Credits Used ($0–$200) → **−0.16** *(v3: −0.08)*
Ancillary travel-credit direct cost — statement reimbursements up to a fixed annual cap (~$150–$250, hard-capped at $200 in data). Direct bottom-line expenditure, tempered by portfolio-wide non-utilization.

### f15 · Cab Benefits Used (months, 0–11) → **−0.15** *(v3: −0.08)*
Partner credit expense. This is a **months-utilized count, not dollars** — structured as **$15/month + a $20 December bonus** (Amex Platinum Uber Cash: $15 monthly + $20 in December = up to $200/year). Because credits expire monthly at 11:59 PM HST, they trigger high organic breakage, and Uber wholesale arrangements mean a dollar utilized costs the issuer less than a dollar of cash rewards.

**Why −0.15 raw weight (was −0.08):** f15 has 34.5% zeros. Effective impact of −0.08 raw = −0.052 — so weak that the spend reward (+0.24 eff) was dragging high-spend cab users into the top 20% (benefit inversion confirmed: top 20% had mean 3.98 cab months vs 3.86 bottom 80%). Back-solved for effective target −0.10: −0.10 / 0.655 = **−0.15**. Post-fix: top 20% mean = 3.11 vs bottom 80% mean = 4.09 — inversion eliminated.

*Source: Amex Platinum Uber Cash / Uber One benefit disclosures.*

### f16 · Entertainment Credit Used ($0–$64.40) → **−0.05** *(v1: −0.08)*
Saturated lifestyle statement credit, **hard-capped at 64.40** (75th percentile = maximum). It behaves **near-binary in the top quartile** — everyone above the 75th percentile carries the identical cost — so it cannot differentiate the top of the portfolio and gets a light weight. Sorting the top relies on f5 (spend) and f1 (revolve).

### f2 · Cancellation Calls (12m) → **−0.12** *(v3: −0.04)*
Churn-intention and retention-cost indicator. Retention specialists offer statement credits, fee waivers, or point bundles to save accounts, so these calls proxy fee leakage plus servicing overhead.

**Why −0.12 raw weight (was −0.04):** f2 has 82.6% zeros — only 17.4% of customers place any cancellation calls. Effective impact of −0.04 raw = −0.007 (nearly invisible). Back-solved for effective target −0.02: −0.02 / 0.174 = **−0.12**. Now carries 7.5% ablation impact (was 2.6%).

*Source: credit card retention operations disclosures.*

---

## 5. Excluded Features (Weight = 0.0)

| Feature | Reason for exclusion |
|---|---|
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
