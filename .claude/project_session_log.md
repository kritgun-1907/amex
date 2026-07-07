---
name: project-session-log
description: "Compacted log of all sessions — what was done, what was fixed, what was discussed, current state"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2391c7b1-37da-4592-9d7c-f655193239c1
---

## Session 1 — 2026-07-07 (yesterday / early hours, ~12AM–5AM IST)

**Starting state:** Raw dataset (`campus_challenge_r1_data.csv`, 500K rows), feature description file, blank repo.

**What was built:**
- `amex_campus_challenge_r1_context.md` — full competition + dataset context pack
- `eda_grilling_session_context.md` — EDA analytical decisions and grilling session notes
- `eda_pipeline.py` — 5-phase EDA pipeline (missingness, scale/outliers, cross-feature validation, imputation, zero-floor rank-transform)
- `validation_harness.py` — v3 → v4 → v5 scoring engine with perturbation stability, ablation, economic gates, submission writer

**Key discoveries during EDA:**
- f5 vs sum(f6:f10) correlation = 0.09 → independently masked, do not reconcile
- f17 ≥ f18 only 63.5% of the time → no hierarchy, no difference feature
- f7 has negative values (−275 minimum) → refunds; keep negatives
- f16 hard-capped at $64.40 (75th pct = max) → near-binary
- Null groups are MNAR — f4/f21 null together (51.4%), f6–f10 together (23.1%), f13–f16 together (2.7%)
- f4/f21 null segment: initially misidentified as "not enrolled." Corrected: all Premier CMs earn 1x by default — these are dormant/masked/cashback-rail customers

**Equation iterations:**
- v3: initial equation, average-rank normalization
- v4: added coverage back-solve concept, but still running on stale average-rank file; f21 inflated to eff −0.12 → top 20% was 95.6% rewards-dormant (equation was rewarding inactivity); f16 kept with rigged ×1.15 tolerance gate; used −999 sentinel for f3
- v5: zero-floor file (harness aborts if stale); f21 held at eff −0.10 (dormancy in top 20% drops to ~86%); f16 fully excluded; f3 smooth bottom-rank; template-agnostic submission writer

**Commits (all 2026-07-07):**
- `aa09e67` — amex_competition (initial commit)
- `7475a84` — dead weights removed
- `712fe63` — validation harnessing performed
- `fbd99c2` — doing some iterations (v3→v4, CLAUDE.md created empty)
- `09ffcbd` — v5 harness complete
- `0c00a69` — updated .md files (framework and grilling context updated to v5)

---

## Session 2 — 2026-07-07 (current session, afternoon IST)

**What was discussed:**
- Explained the raw weight formula: `raw = effective / (1 - zero fraction) = effective / coverage`. Intuition: a feature with 72% zeros only sorts 28% of the population, so the weight must be inflated to achieve the stated effective sorting impact.
- Explained the zero-floor rule in depth: standard average-rank assigns tied zeros the midpoint rank (~0.36 for f21 with 72% zeros), inventing phantom signal. Zero-floor hard-codes zeros to rank 0.0, making zero activity = zero contribution.

**What was created:**
- `CLAUDE.md` — comprehensive project brain (full equation, decisions, workflow, exclusions, traps, feature dictionary, version history)
- Memory files in `.claude/projects/` (this file + `project_amex_challenge.md` + `project_equation_decisions.md`)

**Current state of the project:**
- v5 equation and harness are complete and locked
- `submission_scores_v5.csv` exists in `eda_outputs/` — ready to submit once `SUBMISSION_COLUMNS` in `validation_harness.py` is set to match the exact Unstop template header
- Submissions used so far: unknown (not recorded)

**Open items:**
- Set `SUBMISSION_COLUMNS` to the actual Unstop template header before submitting
- Verify all economic gates pass + perturbation stability ≥80% at ±10% on the current run
- Actual public leaderboard score not yet recorded
- Potential further weight tuning (f6 vs f10 relative emphasis; f17/f18 marginal contribution)
