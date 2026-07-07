---
name: project-equation-decisions
description: "All locked analytical decisions for the v5 profitability equation — imputation, normalization, exclusions, weight design"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2391c7b1-37da-4592-9d7c-f655193239c1
---

All decisions are locked and encoded in `eda_pipeline.py` + `validation_harness.py`. Do not re-litigate unless a validation gate fails or a new version is being designed.

**Imputation (locked):**
- f4, f21, f6–f10, f13–f16, f17, f18 → 0-fill (MNAR; zeros = no economic activity, NOT unknown)
- f5, f11 → median (low null rate, genuinely unknown)
- f23 → dropped (87.8% null)
- The f4/f21 null segment (51.4%) is NOT "not enrolled" — all Premier CMs earn 1x rewards by default; these are dormant/masked customers

**Normalization:** Zero-floor rank-transform. Zeros get rank 0.0 exactly. f7 uses standard rank (has real negatives from refunds that must rank below zero-spend). Zero-floor threshold: features with >20% zeros get the floor treatment.

**f5 vs f6–f10:** NOT reconcilable. Pearson r = 0.09. Independently masked/scaled by Amex. Use f5 as primary gross spend anchor; f6–f10 as independent behavioral modifiers. Never build share features (f6/f5, etc.).

**f17 vs f18:** No hierarchy. f17 ≥ f18 only ~63.5% of the time. Treat as independent correlated signals. Never build f17 − f18.

**f7 negatives:** Keep. Refunds/returns. Do not floor at zero. Rank-transform handles them correctly.

**f16:** Excluded entirely. Hard-capped at $64.40 (75th pct = max). Near-binary in top quartile. No weight resolves the structural inversion (high spenders also use this credit). The harness reports its top/bottom ratio for transparency but does not gate it.

**f3 override:** Any customer with f3 > 0 is ineligible. Implemented as smooth bottom-ranking within ordinary score range. 54,304 customers excluded. Do NOT use −999 sentinel.

**Effective weight design:** All weights expressed as desired effective sorting power. Harness back-solves: raw = effective / coverage. This is because a feature with 72% zeros only sorts 28% of the population — the raw weight must be inflated to achieve the stated effective impact.

**Why:** How to apply: see [[project-amex-challenge]] for version history and [[project_session_log]] for session decisions.
