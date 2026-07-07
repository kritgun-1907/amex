# Submission Plan — One Variable at a Time, Ordered by Leverage

> **Philosophy:** Every slot answers exactly one question. Winner carries forward. Never change two axes at once.
> **Slots total:** 10 | **Used:** 6 (incl. 1 failed) | **Remaining:** 4 | **Best score:** 0.482 (Slot 1)

---

## Results Log

| Slot | File | Score | Status | What changed vs v5 |
|---|---|---|---|---|
| 1 | final_submission_v5.xlsx | **0.482** | ✅ Best | Baseline |
| — | final_submission_v5.xlsx | 0.000 | ❌ Failed | Framework sections blank (bug) |
| 2 | sub2_spend_revolve_isolated.xlsx | 0.338 | ✅ | f5: +0.22→+0.35, f1: +0.20→+0.10 |
| 3 | sub3a_f3off_from_sub1.xlsx | 0.463 | ✅ | v5 weights + f3 override OFF |
| 4 | sub3b_f3off_from_sub2.xlsx | 0.331 | ✅ | sub2 weights + f3 override OFF |
| 5 | sub5_interaction_el.xlsx | 0.421 | ✅ | v5 + replace f11 with rank(f11×f1) eff=-0.18 |
| 6 | sub6_loosen_f21.xlsx | **PENDING** | ⏳ | v5 + f21: -0.10→-0.05 only |

---

## Slot 1 — DONE (Baseline)
**Score: 0.482 ← BEST SO FAR**
**Config:** f1=+0.20, f5=+0.22, f3 hard override ON, f21=-0.10, f11=-0.26 flat, all other weights as designed.

**Top 20% profile:** f1 ratio 3.21x | f5 ratio 1.77x | f21 ratio 0.23x | EL 121 vs 172

---

## Slot 2 — Spend/Revolve Rebalance (ISOLATED)
**Score: 0.338 — DOWN 14.4 pts**
**Change:** f5: +0.22→+0.35 | f1: +0.20→+0.10. Everything else = v5.
**Top 20% profile shifted to:** f1 ratio 1.27x | f5 ratio 2.40x

**What we learned:** Revolve (f1) is THE dominant signal. Cutting it cost 14 points — the single largest drop of any experiment. This is not a weight miscalibration; f1 is structurally critical. Amex's actual top customers are high revolvers. Plan-It interest at 17–24% APR generates more NIM than interchange. **Do not reduce f1.**

---

## Slot 3 — f3 Override OFF from v5
**Score: 0.463 — DOWN 1.9 pts**
**Change:** f3 hard knockout removed, f3 weight=0. v5 weights held constant.
**Top 20% profile:** f1 ratio 3.92x (MORE revolve-dominant, f3>0 high-revolvers entered), f3>0 in top 20%: 2,265 (7.6%)

**What we learned:** f3 override is correct — keeping it ON scores 0.019 higher than removing it. The 2,265 f3>0 customers who entered our top 20% are NOT in Amex's actual top 20%. However, the gap is small (1.9 pts), which means the override's effect is mostly correct but not dramatic. **Keep f3 override ON.**

---

## Slot 4 — f3 Override OFF from sub2
**Score: 0.331 — DOWN 15.1 pts from v5**
**Change:** sub2 weights (spend-tilted) + f3 override off.

**What we learned:** Combining two individually bad changes compounds the damage. No new information.

---

## Slot 5 — f11×f1 Expected Loss Interaction
**Score: 0.421 — DOWN 6.1 pts**
**Change:** v5 weights, f11 flat replaced with rank(f11×f1) at eff=-0.18. Everything else v5.
**Top 20% profile:** f1 ratio 2.18x | f5 ratio 1.88x | EL top=59 vs bot=187

**What we learned:** The interaction is too surgically strong — it filters out risky revolvers so aggressively that the f1 ratio in top 20% drops from 3.21x to 2.18x, diluting the revolve signal. This behaves like a softer version of sub2. The flat f11 already handles risk well enough. More importantly: **the top 20% needs a high f1 ratio (~3x+) to score well. Any mechanism that reduces it costs points.**

---

## Slot 6 — Loosen f21 Penalty (PENDING)
**File:** `submissions/sub6_loosen_f21.xlsx` ← SUBMITTED, AWAITING RESULT
**Change:** f21: -0.10 → -0.05 effective. Everything else = v5 exactly.
**Predicted top 20% profile:** f1 ratio 3.68x | f5 ratio 1.82x | f21 mean 19,343 vs 33,069

**Hypothesis:** The heavy f21 penalty was filtering out the best customers. A high-spend ($50k/yr) high-revolve customer who also redeems 20k pts generates ~$1,250 interchange − $200 redemption cost = still $1,050 net revenue. v5 was penalizing these customers so hard they fell out of top 20%. Loosening f21 lets them back in, which ALSO increases f1 ratio (3.68x) and f5 ratio (1.82x) — both directions confirmed good.

**Decision rules:**
- **If UP** → f21 over-penalized. Try f21=-0.03 in Slot 7.
- **If DOWN** → f21=-0.10 is correct. Try f1 boost with compensating f11 boost in Slot 7.

---

## Slots 7–9 — Reserved

### If Slot 6 goes UP:
**Slot 7 → f21=-0.03 (push further in same direction)**
- f21: -0.05 → -0.03. One change. Tests whether more loosening helps.
- Predicted: f1 ratio 3.86x, f5 1.85x, f21 mean 26,785 vs 31,208

**Slot 8 → Winner config + best refinement of remaining signals**

### If Slot 6 goes DOWN:
**Slot 7 → f1 boost + f11 boost together (f1: +0.24, f11: -0.33)**
- Simultaneously boost revolve reward AND risk penalty to get more revolvers without pulling in risky ones
- At f1=+0.24, f11=-0.33: f1 ratio 3.38x | EL top=108 vs bot=175 (maintains clean profile)

**Slot 8 → Based on Slot 7 result**

### Hard rules for remaining slots:
1. One variable change per slot. No exceptions.
2. f3 override stays ON (proven to help).
3. Never reduce f1 weight. It is the load-bearing signal.
4. Max score so far is 0.482. Every slot must have a clear hypothesis for why it beats 0.482.

---

## Key Learnings Summary

| Finding | Confidence | Implication |
|---|---|---|
| f1 (revolve) is the dominant signal | **Very high** — 14pt drop when cut | Never reduce f1 |
| f3 override is mostly correct | **High** — 1.9pt gap with/without | Keep override ON |
| f11 flat is sufficient (no interaction needed) | **High** — interaction dropped 6pts | Use flat f11 |
| f21=-0.10 may be too harsh | **Hypothesis** — slot 6 tests this | Pending |
| f5 (spend) matters but is secondary to f1 | **High** | Don't sacrifice f1 for f5 |
| Anything that lowers f1 ratio below ~3x hurts | **High** | f1 ratio ~3.5x+ is target |

---

## Slot Usage

```
[✅ 0.482] [❌ 0.000] [✅ 0.338] [✅ 0.463] [✅ 0.331] [✅ 0.421] [⏳ pending] [ ] [ ] [ ]
  Slot 1    Failed     Slot 2     Slot 3     Slot 4     Slot 5     Slot 6    7   8   9
```
