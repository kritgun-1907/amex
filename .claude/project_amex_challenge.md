---
name: project-amex-challenge
description: "Full context for Amex Campus Challenge 2026 Round 1 — what it is, current equation version, key decisions, where we are"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2391c7b1-37da-4592-9d7c-f655193239c1
---

American Express Campus Challenge 2026 — Round 1: rank-order 500,000 Premier cardmembers by profitability. No target column. Pure structural P&L reverse-engineering.

**Competition:** Hosted on Unstop. Evaluated as % overlap between our top 20% and Amex's actual top 20%. Max 10 submissions. Public 70% / private 30% split.
**Stake:** PPI / internship at Amex India Decision Science CoE.

**Why:** Must be defensible in a Round 3 presentation to a decision scientist — not just leaderboard-optimal.

**Current equation version: v5** (as of 2026-07-07)
- Effective-weight design: all weights stated as desired sorting power; harness back-solves raw = effective / coverage
- f3 (collections calls) → smooth bottom-rank override, not a weight, not a −999 sentinel
- f16 (entertainment credit, hard-capped $64.40) → fully excluded (near-binary, structural inversion)
- Zero-floor rank-transform: zeros get rank 0.0 exactly, not average-rank midpoint
- Harness aborts with error if stale average-rank file is loaded instead of zero-floor file

**Key v5 effective weights:** f5 +0.22, f1 +0.20, f11 −0.26, f21 −0.10, f15 −0.09

**How to apply:** The complete equation, coverage table, imputation policy, and workflow are in `CLAUDE.md`. Read that first in any new session.
