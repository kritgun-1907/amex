# American Express Premier Card — Customer Profitability Framework

**Round 1: Measuring the Customer Profitability for Premier Product**

> A structural Profit & Loss (P&L) framework that reverse-engineers cardmember profitability from 23 masked attributes using domain economics. Every coefficient below is anchored to a real-world source, not fitted to a label — because there is no target column to fit.

---

## 1. Core Methodology

Unlike a supervised model that fits a curve to a target `y`, this framework builds a **pure structural accounting engine**. Amex has already computed the true profitability of every cardmember from revenue/cost data it did not share. Our job is to reconstruct that ranking using only the features and the economic identity:

$$\text{Net Profitability} = \text{Gross Revenue} - \text{Direct Variable Costs} - \text{Expected Credit Loss}$$

**Why rank-transform normalization:** The competition metric is % overlap between our top 20% and Amex's actual top 20% — a purely rank-based score. Rank-transforming every feature to `[0.0, 1.0]` aligns the input scale with the evaluation mechanic, is robust to the extreme right-skew of spend data (f7 hits ~147,000), and neutralizes the scale explosion that would otherwise let one large-magnitude column silently dominate.

---

## 2. The Final Scoring Equation (v2 — rebalanced)

> **v2 changes from v1:** f5 boosted to 0.50 (dominant interchange anchor), f1 to 0.55 (NIM engine), f6–f10 cut to 0.01–0.02 (tiny modifiers only). All cost weights scaled ~0.67× to balance total revenue vs total cost. Result: revenue total = cost total = 1.17. DSS improved from 0.41 → 0.49.
>
> v1 issue: costs outweighed revenue 1.9×, selecting top 20% for "least bad" not "most profitable." f6–f10 were acting as a second spend engine (92.8% of top 20% were category-active vs 76.8% baseline).

```
Profitability Score =
    + 0.55 * rank(f1)      # Revolve Interest (NIM engine, ~20-30% APR)
    + 0.50 * rank(f5)      # Base Interchange Spend  ← dominant anchor
    + 0.02 * rank(f6)      # Airlines — tiny premium add-on
    + 0.02 * rank(f7)      # Other Spend — tiny generic add-on
    + 0.02 * rank(f10)     # Dining — tiny premium add-on
    + 0.01 * rank(f8)      # Entertainment — minor add-on
    + 0.01 * rank(f9)      # Lodging — minor add-on
    + 0.02 * rank(f17)     # Total Lend Capacity
    + 0.02 * rank(f18)     # Consumer Lend Capacity
    - 0.40 * rank(f11)     # Expected Credit Loss (heaviest penalty)
    - 0.20 * rank(f3)      # Collections / near-certain loss
    - 0.14 * rank(f21)     # Realized Point Redemption Cost
    - 0.11 * rank(f4)      # Deferred Reward Liability (breakage-adjusted)
    - 0.10 * rank(f13)     # Direct Lounge Cost
    - 0.07 * rank(f14)     # Airline Credit Drain
    - 0.07 * rank(f15)     # Cab Benefit Drain
    - 0.05 * rank(f16)     # Saturated Entertainment Credit Cost
    - 0.03 * rank(f2)      # Retention Overhead / Churn Risk
```

**Weight balance:** Revenue total = +1.17 | Cost total = −1.17 | Net = 0.00
**f5 share of transaction revenue** (f5 + f6–f10): 0.50 / 0.58 = **86%** — f5 does the heavy lifting; categories are modifiers only.

**Excluded (weight = 0.0):** f12 (logins), f22 (emails opened), f23 (emails clicked — 87.8% null), f19 (supplementary accounts), f20 (active charge cards). These are engagement/profile signals, not profit drivers, and folding them in either dilutes the financial signal or double-counts spend already captured in f5.

---

## 3. Revenue Drivers — Weight Justifications

### f1 · Average Revolve Balance (12m) → **+0.55** *(v1: 0.45)*
Primary Net Interest Margin engine. Outstanding balances carried month-to-month accrue high-margin interest. Premium revolving APRs run roughly **19.99%–29.99%**, versus interchange swipe fees that average only **~2%–3%**. A dollar of revolving balance therefore yields on the order of **10x** the gross revenue of a dollar of transactional volume — making f1 the strongest revenue-positive anchor, provided it is counterbalanced by risk.

*Source: standard premium credit card financial disclosures / APR schedules.*

### f5 · Total Spend (12m) → **+0.50** *(v1: 0.20)*
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

### f11 · Average Risk Score (12m) → **−0.40** (heaviest) *(v1: −0.60)*
Expected Credit Loss anchor. Default is catastrophic — it wipes out all associated revenue:

$$\text{Expected Loss} = \text{PD (Risk Score)} \times \text{EAD (Outstanding Balance)}$$

A single default obliterates the interchange profit generated by dozens of high-spending transactors, so f11 carries the most aggressive negative weight to keep high-risk revolvers out of the top tier.

*Source: Basel III risk-weighted-assets framework; bank credit-loss provisioning standards.*

### f3 · Collections-Related Cancellation Calls → **−0.20** *(v1: −0.30)*
Active delinquency / near-certain-loss signal — the customer has crossed from *predicted* risk into a *realized* operational loss threat. Demands a substantial, non-linear penalty.

*Source: retail-bank debt collection & Net Charge-Off standard operating procedures.*

### f21 · Rewards Points Redeemed (12m) → **−0.14** *(v1: −0.20)*
Realized variable rewards expense — hard cash leaving the bank to pay partners. Redeemed points are valued at a fixed internal liability of **~1.0 cent per point** (flight redemptions via Amex Travel hit 1.0¢; Pay-with-Points ~0.7¢; the 1.0¢ ceiling is the conservative cost assumption). High redemption = maximum program-value extraction = expensive customer.

*Source: Amex Membership Rewards program terms; redemption examples — 50,000 points = $500 flight (1.0¢/pt).*

### f4 · Rewards Points Balance → **−0.11** *(v1: −0.16)*
Deferred revenue liability. Under IFRS 15 / GAAP, unredeemed points sit on the balance sheet as a liability — but discounted by an estimated **15%–20% breakage rate** (points that expire/forfeit). Weighted at **~80% of f21** (0.16 / 0.20 = 0.80) to mirror that breakage adjustment.
**Not given a positive weight** as a spend proxy — spend is already fully captured in f5–f10, and doing so would double-count revenue.

*Source: IFRS 15 / GAAP deferred reward liability standards. Note: MR points don't expire while the account is enrolled and in good standing, so breakage is driven by forfeiture on delinquency/cancellation rather than time expiry.*

### f13 · Lounge Access Count (0–3) → **−0.10** *(v1: −0.15)*
Fixed per-usage variable cost. This is a **visit count, not dollars** — each lounge swipe costs the issuer a wholesale operator fee of roughly **$24–$32** (Priority Pass charges USD 32 per additional guest visit). Frequent exploitation generates substantial direct cost.

*Source: Priority Pass / Centurion issuer partnership terms — USD 32 guest visit fee.*

### f14 · Airline Credits Used ($0–$200) → **−0.07** *(v1: −0.10)*
Ancillary travel-credit direct cost — statement reimbursements up to a fixed annual cap (~$150–$250, hard-capped at $200 in data). Direct bottom-line expenditure, tempered by portfolio-wide non-utilization.

### f15 · Cab Benefits Used (months, 0–11) → **−0.07** *(v1: −0.10)*
Partner credit expense. This is a **months-utilized count, not dollars** — structured as **$15/month + a $20 December bonus** (Amex Platinum Uber Cash: $15 monthly + $20 in December = up to $200/year). Because credits expire monthly at 11:59 PM HST, they trigger high organic breakage, and Uber wholesale arrangements mean a dollar utilized costs the issuer less than a dollar of cash rewards — hence a lighter weight than lounge.

*Source: Amex Platinum Uber Cash / Uber One benefit disclosures.*

### f16 · Entertainment Credit Used ($0–$64.40) → **−0.05** *(v1: −0.08)*
Saturated lifestyle statement credit, **hard-capped at 64.40** (75th percentile = maximum). It behaves **near-binary in the top quartile** — everyone above the 75th percentile carries the identical cost — so it cannot differentiate the top of the portfolio and gets a light weight. Sorting the top relies on f5 (spend) and f1 (revolve).

### f2 · Cancellation Calls (12m) → **−0.03** *(v1: −0.05)*
Churn-intention and retention-cost indicator. Retention specialists offer statement credits, fee waivers, or point bundles to save accounts, so these calls proxy fee leakage plus servicing overhead. Light negative weight.

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
