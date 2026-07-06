# American Express Campus Challenge 2026 — Round 1 Context Pack

> **Purpose of this document:** This is a self-contained knowledge file. Drop it into a Claude Project so any conversation instantly understands the competition, the Premier Card product economics, the exact dataset (structure, statistics, quirks), the true nature of the problem, the profitability framework, the evaluation mechanics, and the strategy. It also records the analytical decisions and open questions so work can continue without re-explaining anything.
>
> **Last updated:** July 2026 — added Premier Card product overview (Section 4a), official attribute category map (Section 5a), and revised imputation reasoning for f4/f21 null segment.

---

## 0. How to read this file

- Sections 1–3 = **what the competition is and what Round 1 asks**.
- Section 4 = **the product** (needed to reason about card economics).
- **Section 4a** = **Premier Card product overview slide** (verbatim from competition PDF — reference this before building the equation).
- Sections 5–7 = **the dataset**: feature dictionary, real data profile with numbers, and the structural quirks/traps.
- **Section 5a** = **official attribute category map** (from competition PDF).
- Section 8 = **the core conceptual framing** (this is the part most teams get wrong).
- Sections 9–11 = **the profitability framework, feature importance, and pitfalls**.
- Sections 12–13 = **evaluation mechanics and the recommended approach**.
- Section 14 = **rules/constraints**. Section 15 = **open decisions still to be made**.

All statistics in Sections 6–7 were computed on the full 500,000-row dataset, not sampled.

---

## 1. The competition

The **American Express Campus Challenge 2026** ("It's about Premier Card") is an analytics, strategy, and product challenge for campus students in India, run by the American Express India Centre of Excellence (CoE). The CoE is a two-decade-old analytics arm powering Amex's Decision Science, Strategy, and Product teams across Risk, Fraud, and Marketing — the functions behind customer engagement, credit approve/decline, credit-limit assignment, and fraud detection.

**Stakes:** prizes for winners/top performers, Pre-Placement Interviews (PPIs) for top performers (T&Cs apply), merchandise, and participation certificates. For the user, the primary goal is the **PPI / internship path into Amex** — so the solution must be *defensible and presentable to a decision scientist*, not just leaderboard-optimal.

### Stages
1. **Round 1 — Measuring the Customer Profitability for Premier Product** — data-driven analytical round (this document's focus).
2. **Round 2 — Elevating the Premier Card Experience** — case-study competition.
3. **Round 3 — Deck Submission and Presentation** — case-study presentation.

Because Round 3 is a human-judged presentation, the Round 1 method must be explainable and economically sound, not a black-box hack.

---

## 2. Round 1 problem statement (verbatim intent)

- Identify the most profitable Premier Cardmembers based on attributes such as spend behavior, revolving patterns, riskiness, and benefit utilization.
- **Objective:** design a framework or equation to quantify cardmember profitability **to the issuer** by incorporating **revenues and costs**, in order to identify and prioritize the most profitable customers.

The deliverable is a **profitability score per cardmember that rank-orders all customers**, submitted on a fixed template for all `unique_identifier`s.

---

## 3. What "profitability to the issuer" means

Card profit = **Revenue − Cost**, per customer. For an issuer like Amex (a spend-centric network), the components are:

**Revenue**
- **Interchange / discount revenue** — merchant fee earned on every dollar spent. This is Amex's core engine. Driven by total and category spend.
- **Interest / lend revenue** — interest on revolving balances and Plan-It / lend-line borrowing.
- **Annual fee** — $500–750, roughly constant across all Premier holders (so it barely differentiates ranking, except via retention leakage).

**Cost**
- **Rewards cost** — points earned/redeemed (1 point ≈ 1–2 cents).
- **Benefit / credit cost** — every annual credit *used* (lounge, airline, cab, entertainment, hotel) is a direct expense.
- **Credit loss** — expected loss ≈ risk × exposure; collections activity is a strong bad signal.
- **Servicing cost** — calls, etc. (minor).

**The counterintuitive core:** the most profitable customer is a **high-spending, moderately-revolving, low-risk** customer who does **not** fully milk the benefits. A low-spend, high-risk customer who maxes every credit, visits the lounge repeatedly, and redeems all points is a **loss-maker**, even though they look "engaged / premium." Benefit utilization and risk must **subtract** in the equation.

---

## 4. The Premier Card product (domain context)

Flagship personal ultra-premium **charge card** (no preset spending limit). Annual fee $500–750. Target: high-income, frequent travelers.

- **Rewards multipliers:** 5x points on flights/travel booked directly, 5x on prepaid hotels via travel portal, 1x on everything else. Points transfer to 20+ airline/hotel partners; 1 point ≈ 1–2 cents.
- **Welcome bonus:** 80,000–150,000 points on a spend threshold in first 6 months. No renewal bonus; value delivered via annual credits + retention offers.
- **Travel benefits:** ultra-premium lounge access (cardholder + 2 guests), priority airport services, $150–250 airline fee credit/year, trip cancellation/interruption + car rental insurance.
- **Hotel/loyalty:** elite hotel status, room upgrades, stay credits ($50–150 on 2-night stays).
- **Lifestyle credits (annual):** cabs $150–250, digital entertainment $180–280, commerce stores $105–205, fitness $250–350, clothing $50–150.
- **Protection:** purchase protection (120 days, up to $5K–15K), extended warranty (+2 yrs), return protection (90 days, up to $250–350/item), fraud zero-liability, emergency replacement.
- **Digital:** real-time alerts, points tracker/transfer, virtual card numbers, Plan-It installments, targeted offers.

**Why this matters for modeling:** the credits and lounge access above map directly to *cost* features in the data. High utilization = high issuer cost. Plan-It / lend lines explain why a "charge card" still shows revolving balances and lend-line fields.

---

## 4a. Premier Card product overview (verbatim from competition PDF slide)

> *Reference this section before assigning economic roles to features. Numbers below are from the official competition slide.*

**Positioning & Fee**
- Flagship ultra-premium card | Annual fee: $500–$750
- Target: high-income, frequent travelers | No preset spending limit (charge card)

**Rewards Rate & Multipliers**
- 5x on flights booked directly / Travel
- 5x CC points on prepaid hotels via Travel portal
- **1 CC point on ALL other purchases** ← baseline earn rate, applies to every cardmember
- 1 CC point = 1–2 cents (transfer to partners)
- Transfer to 20+ airline and hotel partners
- Welcome bonus: 80,000–150,000 CC points on spending threshold in first 6 months
- No renewal bonus; value delivered via annual credits + retention offers

**Travel Benefits**
- Ultra Premium Lounge access (cardholder + 2 guests)
- Priority airport services and travel conveniences
- $100–$250 airline fee credit per year (select airlines)
- Trip cancellation/interruption insurance
- Car rental loss & damage insurance

**Hotel & Loyalty Status**
- Elite status with luxurious hotel loyalty program
- Premium hotels room upgrades + credits
- Hotel stay credits and special offers ($50–$150 credit on 2-night stays)

**Lifestyle Credits (Annual)**
- $100–$250 Cabs credit — structured as **$15/month + $10 in December**
- $120–$280 Entertainment credit
- $105–$205 Commerce Stores credit
- $50–$150 Fitness credit
- $50–$150 Clothing credit

**Protection & Insurance**
- Purchase protection (120 days, up to $5K–$15K)
- Extended warranty (+2 years on purchases)
- Return protection (90 days, up to $250–$350/item)
- Emergency card replacement worldwide

**Digital & App Experience**
- Real-time spend notifications & alerts
- CC points tracker & transfer in-app
- Virtual card numbers for online use
- **Plan-It installment flexibility** ← explains why charge card has lend line fields (f17, f18)
- Offers targeted merchant deals

**Critical PM note:** Because rewards are earned on ALL purchases at 1x baseline, every Premier cardmember is enrolled in Membership Rewards by default. The 51.4% null segment on f4/f21 is NOT explained by "not enrolled" — it reflects dormant customers, data masking by Amex for the competition, or a product sub-variant on a cashback rail. Imputation remains 0-fill (zero recorded activity assumption), but the deck must NOT use the "not enrolled" framing.

---

## 5a. Official Attribute Category Map (from competition PDF slide)

> *Verbatim from "Card Member Attributes: Categories" slide. ~23 attributes spread across 4 categories. Attribute names are masked; no PII shared.*

| Category | What it measures | Features mapped |
|---|---|---|
| **CM Spend & Balance** | Industry level spends; Revolve behavior | f1, f5, f6, f7, f8, f9, f10 |
| **Benefit Usage** | No of lounge visits; No of months Cab credits utilized | f13, f14, f15, f16 |
| **Engagement** | No of calls to cancel premier card; Website logins; # of Cards held | f2, f3, f12, f19, f20 |
| **Profile** | Tenure; Riskiness score | f11, + likely one masked tenure feature |

**Key clarifications from this slide:**
- **f13** = Number of lounge **visits** (count, 0–3) — NOT a dollar amount
- **f15** = Number of **months** cab credits were utilized (count, 0–11) — NOT a dollar amount. At $15/month the bank's actual cost ≈ f15 × $15
- **"Tenure"** appears under Profile but has no directly visible column — may be masked within the 23 features or derivable from account age implied by other fields
- **f2 + f3** both fall under Engagement as cancellation-related calls — f3 (collections-related cancellations) is a harder credit-loss signal than f2 (general cancellation calls)

---

## 5. Dataset — feature dictionary

- **File:** `campus_challenge_r1_data.csv` — **500,000 rows × 24 columns** (`id` + `f1`…`f23`).
- **Only cardmember attributes are provided. There is NO target/profit column.** (~23 attributes across categories: CM spend & balance, benefit usage, engagement, profile.)
- Attribute names are masked; no PII.
- Companion file `feature_description.csv` maps codes to descriptions (below).

| Code | Description | Economic role |
|------|-------------|---------------|
| `id` | Identifier | **Excluded from solution** (rule) |
| `f1` | Average revolve balance, last 12m | Revenue (interest) |
| `f2` | Cancellation calls, last 12m | Cost / churn (fee leakage) |
| `f3` | Cancellation calls due to collection | Cost (strong risk/loss signal) |
| `f4` | Rewards points balance | Cost (liability) |
| `f5` | Total spend, last 12m | Revenue (interchange) |
| `f6` | Airlines spend, 12m | Revenue (interchange) |
| `f7` | Other spend, 12m | Revenue (interchange) |
| `f8` | Entertainment spend, 12m | Revenue (interchange) |
| `f9` | Lodging spend, 12m | Revenue (interchange) |
| `f10` | Dining spend, 12m | Revenue (interchange) |
| `f11` | Average risk score, 12m | Cost (expected loss) |
| `f12` | Login counts to website | Context (engagement) |
| `f13` | Lounge access — **visit count** (0–3) | Cost (benefit usage) — count, each visit ~$30–50 issuer cost |
| `f14` | Airline credits used — dollar amount ($0–$200) | Cost (benefit usage) — annual credit, hard-capped |
| `f15` | Cab benefits — **months utilized** (0–11) | Cost (benefit usage) — count of months; actual cost ≈ f15 × $15 |
| `f16` | Entertainment credit used — dollar amount ($0–$64.40) | Cost (benefit usage) — hard-capped; near-binary above 75th pct |
| `f17` | Total lend line amount | Revenue (lend capacity) |
| `f18` | Total consumer lend line amount | Revenue (lend capacity) |
| `f19` | Number of supplementary accounts | Context (profile) |
| `f20` | Count of active charge cards | Context (profile) |
| `f21` | Rewards points redeemed, 12m | Cost (realized) |
| `f22` | Emails opened, last 6m | Context (engagement) |
| `f23` | Emails clicked, last 6m | Context (engagement) |

---

## 6. Data profile (computed on all 500,000 rows)

### 6.1 Missingness (null count and %)

| Feature | Nulls | % null | Note |
|---------|------:|------:|------|
| `f1`, `f2`, `f3`, `id` | 0 | 0.0% | fully populated |
| `f5` (total spend) | 6,340 | 1.3% | |
| `f11` (risk) | 2,510 | 0.5% | |
| `f19` (supp accts) | 22 | 0.0% | |
| `f20` (charge cards) | 101 | 0.0% | |
| `f13`–`f16` (benefit usage) | 13,716 | 2.7% | **all null together** |
| `f12` (logins) | 25,005 | 5.0% | |
| `f22` (emails open) | 94,654 | 18.9% | |
| `f6`–`f10` (category spend) | 115,698 | 23.1% | **all null together** |
| `f4` (rewards bal) | 257,228 | 51.4% | **null for same rows as f21** |
| `f21` (pts redeemed) | 257,228 | 51.4% | **null for same rows as f4** |
| `f17` (lend line) | 292,254 | 58.5% | |
| `f18` (consumer lend) | 309,444 | 61.9% | |
| `f23` (emails clicked) | 438,965 | 87.8% | near-empty; low value |

**Critical fact — the nulls are structured, not random.** They arrive in locked groups: `f4` and `f21` are null for the *exact same* customers; `f6`–`f10` are null together; `f13`–`f16` are null together. This means **missing ≈ "no recorded activity" (treat as zero), not "value unknown."** Imputation policy therefore matters enormously and should mostly be **fill with 0**, not mean/median (see Section 7).

**Important revision on f4/f21 null segment:** Early analysis incorrectly framed these 257,228 customers as "not enrolled in Membership Rewards." This is WRONG — the Premier Card product slide confirms all cardmembers earn 1x points on every purchase by default. The correct interpretation is: these are customers with **no recorded rewards activity in the data window** — likely dormant/low-activity customers, an Amex-masked cohort for competition purposes, or a product sub-variant on a cashback rail. Imputation remains 0-fill (zero-activity assumption), but **the deck must NOT use the "not enrolled" framing.**

### 6.2 Distribution summary (min / 25% / median / mean / 75% / max)

| Feature | min | 25% | median | mean | 75% | max |
|---|---:|---:|---:|---:|---:|---:|
| `f1` revolve bal | 0 | 0 | 0 | 2,467 | 2,436 | 17,968 |
| `f2` cancel calls | 0 | 0 | 0 | 0.17 | 0 | 1 |
| `f3` collections | 0 | 0 | 0 | 0.11 | 0 | 1 |
| `f4` rewards bal | 2 | 8,097 | 50,705 | 126,607 | 150,491 | 697,899 |
| `f5` total spend | 0 | 669 | 2,166 | 3,465 | 4,912 | 13,596 |
| `f6` airline spend | 0 | 637 | 4,023 | 10,032 | 12,870 | 52,198 |
| `f7` other spend | **-275** | 3,338 | 14,396 | 30,822 | 41,279 | 146,701 |
| `f8` ent spend | 0 | 0 | 304 | 1,523 | 1,777 | 9,420 |
| `f9` lodging spend | 0 | 0 | 265 | 1,652 | 1,810 | 10,829 |
| `f10` dining spend | 0 | 325 | 1,802 | 4,536 | 6,311 | 21,651 |
| `f11` risk score | 0 | 0 | 0 | 0.03 | 0.01 | 0.33 |
| `f12` web logins | 0 | 9 | 19 | 30.9 | 42 | 116 |
| `f13` lounge visits | 0 | 0 | 0 | 0.48 | 1 | 3 |
| `f14` airline credit used | 0 | 0 | 0 | 43.1 | 72.1 | 200 |
| `f15` cab benefit use | 0 | 0 | 3 | 3.99 | 7 | 11 |
| `f16` ent credit used | 8.88 | 47.8 | 63.1 | 53.4 | 64.4 | **64.4 (capped)** |
| `f17` total lend line | 1,000 | 9,800 | 21,728 | 24,165 | 34,650 | 63,800 |
| `f18` consumer lend | 1,000 | 9,310 | 19,998 | 21,976 | 33,026 | 54,800 |
| `f21` pts redeemed | 0 | 0 | 11,186 | 62,730 | 84,460 | 365,166 |
| `f22` emails open | 0 | 1 | 3 | 4.58 | 7 | 15 |
| `f23` emails clicked | 1 | 1 | 1 | 1.31 | 1 | 3 |
| `f19` supp accts | 1 | 1 | 2 | 1.80 | 2 | 4 |
| `f20` charge cards | 1 | 1 | 1 | 1.19 | 1 | 2 |

---

## 7. Data quirks and traps (verified)

1. **`f5` is NOT the sum of `f6`–`f10`.** Total spend (median ~2,166) is on a completely different scale from the category spends (e.g., `f7` other-spend median ~14,396). Correlation between `f5` and the summed categories is only **0.09**, and they match on only ~6,000 of 500,000 rows. **Do not build "category share of total spend" features** — the columns measure different things or are independently masked/scaled.

2. **Scale explosion.** Features span from `f11` (0–0.33) to `f7` (up to ~147,000). If you sum raw features, the largest-magnitude column silently becomes the entire ranking. In a naive test, revolve balance alone drove ~85% of the ranking purely because of magnitude. **Normalize every feature before weighting.** Rank-transform is the safest choice and it matches the rank-based scoring.

3. **`f7` has ~22,451 negative values** (min −275) — legitimate refunds/returns. Decide whether to floor at 0 or keep.

4. **`f16` (entertainment credit used) is capped near 64.40** — 75th percentile = max = 64.40. It behaves like a saturated benefit, not a continuous spend.

5. **`f17` ≥ `f18` only ~63.5% of the time** among non-null rows — so despite the names ("total" vs "consumer" lend line), there is **no strict hierarchy**. Don't assume `f17 ≥ f18` and don't build a difference feature assuming it's positive.

6. **Correlated missingness = segment structure** (repeat of the key point): `f4`/`f21` null together (51%), `f6`–`f10` null together (23%), `f13`–`f16` null together (2.7%). Treating these as "unknown" and mean-imputing manufactures fake profit for customers who generate none and scrambles the top 20%. Default to **0-fill** for these groups unless there's a reason not to.

---

## 8. The core conceptual framing (the part most teams get wrong)

- **There is no target column.** You cannot train a supervised model — there is no label to fit. You also should not just cluster and hope. The signal is **economic**, not statistical.
- **Amex has already computed the "true" profitability** of every cardmember from revenue/cost data they did NOT share. Your job is to **reverse-engineer that ranking** using only the 23 features + domain economics.
- **Scoring is rank-based on the top quintile:** *Accuracy = % overlap between your top-20% and the actual top-20% profitable customers.* Consequences:
  - The **absolute dollar scale of your equation is irrelevant** — only the *rank order*, and specifically the ordering around the 80th-percentile cutoff, matters.
  - You need the **relative weights** between spend, revolve, risk, and benefit-cost right — not perfect coefficients.
- **Winning move = a defensible P&L equation**, not a leaderboard-gaming hack. Amex explicitly evaluates for gaming and wants a "scalable real-world" equation, and you must present the method in Round 3.

---

## 9. The profitability framework (equation skeleton)

Conceptually, on **normalized** features:

```
Profitability ≈
    w_spend        * Spend_component        (f5, and/or f6–f10, category-weighted)
  + w_revolve      * Revolve_interest       (f1)                     [+ lend capacity f17/f18]
  + w_fee          * Net_annual_fee         (~constant, minus leakage from f2)
  - w_rewards      * Rewards_cost           (f21 realized; f4 liability)
  - w_benefit      * Benefit_cost           (f13 lounge, f14 airline, f15 cab, f16 ent)
  - w_risk         * Expected_loss          (f11 risk, amplified by exposure; f3 collections)
  - w_servicing    * Servicing_cost         (f2, minor)
```

**Rough real-world priors for coefficients** (label them as assumptions in the deck; do NOT present as Amex facts):
- interchange ≈ ~1.5–2.5% of spend (travel/dining richer than "other"),
- points ≈ 1–2 cents each,
- expected loss ≈ risk_score × exposure (revolve/lend balance).

**Design principle:** benefit-usage terms and risk terms must **reduce** the score. If your ranking rewards high benefit utilization, the economics are inverted.

---

## 10. Feature importance (for ranking, not for the customer)

"Impact" = moves real issuer economics **and** has enough non-null coverage to differentiate 500K people.

- **High impact — Revenue:** `f5` total spend, `f7` other spend, `f6` airline, `f10` dining, `f1` revolve balance.
- **Medium — Revenue:** `f9` lodging, `f8` entertainment, `f17`/`f18` lend lines (heavy nulls temper them).
- **High impact — Cost:** `f11` risk, `f3` collections, `f13` lounge, `f14` airline credit, `f15` cab credit, `f16` ent credit.
- **Medium — Cost:** `f4` rewards balance, `f21` pts redeemed (51% null), `f2` cancel calls.
- **Low / context (do NOT let these dominate):** `f12` logins, `f22` emails opened, `f23` emails clicked (88% null — near useless), `f19` supp accounts, `f20` charge cards. These predict **churn/engagement, not profit**.

---

## 11. Pitfalls to avoid

1. Trying to train an ML model with no label. (There isn't one.)
2. Summing raw, un-normalized features → largest-magnitude column dominates.
3. Mean/median-imputing the structured-null groups → fabricates profit for zero-activity customers.
4. Building `f5` vs `f6`–`f10` "share" features → they don't reconcile.
5. Assuming `f17 ≥ f18`.
6. Rewarding benefit utilization / engagement instead of penalizing benefit cost.
7. **Overfitting the public (70%) leaderboard** — the private (30%) leaderboard is hidden and decides the outcome (classic public/private split collapse).
8. Gaming the metric with a non-scalable trick → flagged by Amex and indefensible in Round 3.

---

## 12. Evaluation mechanics and strategy

- **Metric:** Accuracy = % of Actual Top 20% profitable CMs vs Top 20% identified by your solution.
- **Public leaderboard:** score on 70% of data, live, publicly rank-ordered.
- **Private leaderboard:** score on the other 30%, hidden, published after Round 1.
- **Submissions:** max **10 per team**; final rank = max score attained.

**Strategy implications:**
- Hold out your **own** validation set locally; treat the public leaderboard as a sanity check, not an optimizer. Spend ~3–4 submissions, not all 10.
- Change **one economic assumption at a time**; inspect *who* lands in your top 20% and check they're economically sensible (high-spend, low-risk, low-benefit-cost).
- Prioritize a **robust, explainable equation** that will hold up on the hidden 30% and in the Round 3 presentation.

---

## 13. Recommended approach (roadmap)

1. **EDA with an economic lens:** distributions, the null-segment map, feature-to-feature correlations (find redundant columns), classify each feature as revenue-positive vs cost-negative. Decide null-handling per feature *with a reason* (default 0-fill for structured-null groups).
2. **Write the P&L equation on paper first** — revenue terms minus cost terms in plain English — before coding. Assign prior coefficients.
3. **Normalize every feature** (rank-transform recommended; robust to scale/outliers and matches the metric), then combine.
4. **Build v1, validate locally** on a held-out 30%; inspect the top-20% membership for economic sanity; tune the **risk and benefit penalties** if loss-makers leak into the top.
5. **Iterate weights, not features, one change at a time.** Only then probe the public leaderboard.
6. **Package a clean, reproducible script** that runs on all 500K `id`s and outputs the exact Unstop submission template — no nulls in the score, every row covered.

---

## 14. Rules and constraints (Round 1)

- Use only existing variables to formulate the equation. **Do not use identifier variables** (`id`) in the solution.
- **Do not add rows or alter the shared data.** The solution must run on all `unique_identifier`s.
- Submit **1 file** in Round 1, using the exact template from the Unstop website.
- The equation should be **scalable in the real world**, consistent with the evaluation criteria.
- Max **10 submissions** per team. Public leaderboard by submission; private leaderboard hidden until end.
- Amex evaluates all solutions for integrity/gaming. **Plagiarism → disqualification.** Amex's decisions are final and unexplained.

---

## 15. Open decisions still to be made

- **Null policy per feature group** — confirm 0-fill vs alternative for `f4`/`f21`, `f6`–`f10`, `f13`–`f16`, `f17`/`f18`.
- **Which spend to trust** — `f5` alone, `f6`–`f10` (category-weighted), or a blend, given they don't reconcile.
- **Category interchange weights** — how much richer travel/dining are vs "other."
- **Risk interaction** — whether risk multiplies exposure (revolve/lend) or subtracts as a flat penalty; how to treat `f3` collections (hard penalty vs large weight).
- **Benefit-cost calibration** — dollar cost per lounge visit / credit used to keep the penalty economically proportionate.
- **Normalization choice** — rank-transform vs z-score vs min-max, and whether to cap outliers.
- **Handling `f7` negatives** and the `f16` cap.
- **Public vs private overfitting guardrails** — local CV design and how many submissions to reserve.

---

*This file was generated from an analysis session on the actual 500K-row dataset. Statistics reflect the full data. Coefficient priors and interchange/point-value figures are modeling assumptions, not Amex-published numbers, and should be labeled as such in any deliverable.*
