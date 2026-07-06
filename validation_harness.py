"""
Amex Campus Challenge 2026 — Local Validation Harness
======================================================
Purpose: test the profitability equation locally without burning competition submissions.

Workflow:
  1. Load ranked dataset from eda_outputs/data_ranked.csv
  2. Apply equation weights to compute a profitability score for all 500K rows
  3. Simulate the 70/30 public/private leaderboard split
  4. Flag top 20% on the held-out 30% (private leaderboard proxy)
  5. Print economic sanity check — does the top 20% look like genuinely
     profitable customers (high spend, low risk, low cost)?
  6. Compute a Directional Sanity Score to compare weight iterations
  7. Save diagnostic plots

Modify WEIGHTS below and re-run to test a new equation version.
No competition submissions needed.
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns

warnings.filterwarnings("ignore")

RANKED_PATH = "eda_outputs/data_ranked.csv"
RAW_PATH    = "6a3eb196bc7a3_campus_challenge_r1_data.csv"
OUT_DIR     = "eda_outputs"
RANDOM_SEED = 42
TOP_PCT     = 0.20   # top quintile threshold

SEP  = "=" * 70
SEP2 = "-" * 70


def section(title: str) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")


# ══════════════════════════════════════════════════════════════════════════════
# WEIGHTS — modify here to test a new equation version
# ══════════════════════════════════════════════════════════════════════════════
WEIGHTS = {
    # -- Revenue  (v2: f5 boosted to 0.50, f1 to 0.55, f6-f10 cut to 0.01-0.02)
    # f5 carries ~43% of transaction-revenue weight; f5+f1 = ~90% of all revenue.
    # Category columns (f6-f10) are tiny add-ons, NOT a second spend engine.
    "f1_rank":  +0.55,   # Revolve balance        -- NIM engine (~20-30% APR)
    "f5_rank":  +0.50,   # Total spend            -- dominant interchange anchor
    "f6_rank":  +0.02,   # Airlines spend         -- tiny premium add-on
    "f7_rank":  +0.02,   # Other spend            -- tiny generic add-on
    "f10_rank": +0.02,   # Dining spend           -- tiny premium add-on
    "f8_rank":  +0.01,   # Entertainment spend    -- minor add-on
    "f9_rank":  +0.01,   # Lodging spend          -- minor add-on
    "f17_rank": +0.02,   # Total lend capacity    -- Plan-It underwriting signal
    "f18_rank": +0.02,   # Consumer lend capacity -- independent capacity signal
    # -- Cost / Risk  (v2: all scaled ~0.67x to balance revenue total)
    # Relative ordering of penalties preserved exactly from v1.
    "f11_rank": -0.40,   # Avg risk score         -- expected credit loss (heaviest)
    "f3_rank":  -0.20,   # Collections calls      -- near-certain realized loss
    "f21_rank": -0.14,   # Points redeemed        -- realized rewards cost (~1c/pt)
    "f4_rank":  -0.11,   # Rewards balance        -- deferred liability (IFRS 15)
    "f13_rank": -0.10,   # Lounge visits          -- per-visit cost ($24-32 wholesale)
    "f14_rank": -0.07,   # Airline credits used   -- annual credit drain
    "f15_rank": -0.07,   # Cab months utilized    -- $15/month partner cost
    "f16_rank": -0.05,   # Entertainment credit   -- near-binary above 75th pct
    "f2_rank":  -0.03,   # Cancellation calls     -- retention overhead / churn
    # -- Excluded (weight 0)
    # f12: logins     -- engagement, not P&L
    # f22: emails     -- engagement, not P&L
    # f23: dropped    -- 87.8% null
    # f19: supp accts -- spend already in f5
    # f20: cards held -- profile only
}

W_REV  = sum(v for v in WEIGHTS.values() if v > 0)
W_COST = sum(v for v in WEIGHTS.values() if v < 0)


# ══════════════════════════════════════════════════════════════════════════════
# LOAD
# ══════════════════════════════════════════════════════════════════════════════
section("LOADING DATA")

df_ranked = pd.read_csv(RANKED_PATH)

print(f"  Ranked dataset : {df_ranked.shape[0]:,} rows × {df_ranked.shape[1]} cols")
print(f"  (Contains original imputed features + rank columns — no separate raw load needed)")

# verify all rank columns are present
missing = [c for c in WEIGHTS if c not in df_ranked.columns]
if missing:
    raise ValueError(f"Missing rank columns in ranked dataset: {missing}")
print(f"  All {len(WEIGHTS)} weighted rank columns present ✓")

print(f"\n  Weight summary:")
print(f"    Revenue weights total  : +{W_REV:.2f}")
print(f"    Cost weights total     : {W_COST:.2f}")
print(f"    Net (revenue - |cost|) : {W_REV + W_COST:.2f}")
print(f"\n  ⚠  Cost weights outweigh revenue {abs(W_COST)/W_REV:.1f}×. "
      f"Sanity check will confirm whether top 20% is cost-driven or spend-driven.")


# ══════════════════════════════════════════════════════════════════════════════
# COMPUTE PROFITABILITY SCORE
# ══════════════════════════════════════════════════════════════════════════════
section("COMPUTING PROFITABILITY SCORE")

df_ranked["profit_score"] = sum(
    w * df_ranked[feat] for feat, w in WEIGHTS.items()
)

print(f"\n  Score distribution (all 500K rows):\n")
stats = df_ranked["profit_score"].describe(percentiles=[0.01, 0.10, 0.20, 0.50, 0.80, 0.90, 0.99])
for k, v in stats.items():
    print(f"    {k:>6} : {v:.4f}")

score_range = df_ranked["profit_score"].max() - df_ranked["profit_score"].min()
print(f"\n    range  : {score_range:.4f}")
print(f"\n  Note: absolute scale is irrelevant — only rank order matters.")


# ══════════════════════════════════════════════════════════════════════════════
# 70 / 30 SPLIT  (simulate public / private leaderboard)
# ══════════════════════════════════════════════════════════════════════════════
section("70 / 30 SPLIT  (public / private leaderboard simulation)")

np.random.seed(RANDOM_SEED)
mask_test  = np.random.rand(len(df_ranked)) >= 0.70
# df_ranked already contains original imputed feature values + rank columns
# (it was built as df_imp.copy() in eda_pipeline, so no separate merge needed)
df_train   = df_ranked[~mask_test].copy().reset_index(drop=True)
df_test    = df_ranked[mask_test].copy().reset_index(drop=True)

print(f"\n  Train (public proxy)  : {len(df_train):,} rows  ({len(df_train)/len(df_ranked)*100:.1f}%)")
print(f"  Test  (private proxy) : {len(df_test):,}  rows  ({len(df_test)/len(df_ranked)*100:.1f}%)")


# ══════════════════════════════════════════════════════════════════════════════
# TOP 20% IDENTIFICATION
# ══════════════════════════════════════════════════════════════════════════════
section("TOP 20% IDENTIFICATION")

cutoff_train = df_train["profit_score"].quantile(1 - TOP_PCT)
cutoff_test  = df_test["profit_score"].quantile(1 - TOP_PCT)

df_train["top20"] = (df_train["profit_score"] >= cutoff_train).astype(int)
df_test["top20"]  = (df_test["profit_score"]  >= cutoff_test).astype(int)

n_top_train = df_train["top20"].sum()
n_top_test  = df_test["top20"].sum()

print(f"\n  Train set — top 20% cutoff score : {cutoff_train:.4f}")
print(f"  Train set — customers in top 20% : {n_top_train:,}  ({n_top_train/len(df_train)*100:.1f}%)")
print(f"\n  Test  set — top 20% cutoff score : {cutoff_test:.4f}")
print(f"  Test  set — customers in top 20% : {n_top_test:,}  ({n_top_test/len(df_test)*100:.1f}%)")


# ══════════════════════════════════════════════════════════════════════════════
# ECONOMIC SANITY CHECK
# ══════════════════════════════════════════════════════════════════════════════
section("ECONOMIC SANITY CHECK  (test set — private leaderboard proxy)")

# raw feature stats for top 20% vs rest
raw_cols = {
    "f1":  "Revolve Balance",
    "f5":  "Total Spend",
    "f6":  "Airlines Spend",
    "f10": "Dining Spend",
    "f11": "Risk Score",
    "f3":  "Collections Calls",
    "f21": "Points Redeemed",
    "f13": "Lounge Visits",
    "f4":  "Rewards Balance",
    "f17": "Total Lend Line",
}

# df_test already has all original imputed feature columns — no merge needed
df_test_raw = df_test.copy()

print(f"\n  {'Feature':<25} {'Top 20% mean':>14} {'Bottom 80% mean':>16} {'Ratio T/B':>10}  {'Direction OK?':>14}")
print(f"  {SEP2}")

directions = {
    "f1": "higher",  "f5": "higher", "f6": "higher",
    "f10": "higher", "f11": "lower", "f3": "lower",
    "f21": "lower",  "f13": "lower", "f4": "neutral",
    "f17": "higher",
}
sanity_passes = 0
sanity_total  = 0

for feat, label in raw_cols.items():
    top_mean  = df_test_raw.loc[df_test_raw["top20"] == 1, feat].mean()
    rest_mean = df_test_raw.loc[df_test_raw["top20"] == 0, feat].mean()
    ratio     = top_mean / rest_mean if rest_mean != 0 else float("inf")
    expected  = directions[feat]

    if expected == "higher":
        ok = "✓" if ratio > 1.0 else "✗  FAIL"
        sanity_passes += int(ratio > 1.0)
    elif expected == "lower":
        ok = "✓" if ratio < 1.0 else "✗  FAIL"
        sanity_passes += int(ratio < 1.0)
    else:
        ok = "—"

    sanity_total += int(expected != "neutral")
    print(f"  {label:<25} {top_mean:>14,.2f} {rest_mean:>16,.2f} {ratio:>10.3f}  {ok:>14}")

print(f"\n  Sanity score: {sanity_passes}/{sanity_total} directional checks passed")
if sanity_passes == sanity_total:
    print("  ✓ All economic directions are correct — equation is well-calibrated.")
elif sanity_passes >= sanity_total * 0.8:
    print("  ⚠  Most directions correct but some features are misaligned. Review flagged rows.")
else:
    print("  ✗  Multiple economic directions wrong — equation needs significant rebalancing.")


# ══════════════════════════════════════════════════════════════════════════════
# COMPOSITION DEEP-DIVE
# ══════════════════════════════════════════════════════════════════════════════
section("TOP 20% COMPOSITION DEEP-DIVE")

top    = df_test_raw[df_test_raw["top20"] == 1]
bottom = df_test_raw[df_test_raw["top20"] == 0]

print(f"\n  [A] Collections calls (f3) in top 20%:")
f3_zero_top = (top["f3"] == 0).mean() * 100
f3_zero_bot = (bottom["f3"] == 0).mean() * 100
print(f"      % with zero collections in top 20%   : {f3_zero_top:.1f}%  (should be very high)")
print(f"      % with zero collections in bottom 80%: {f3_zero_bot:.1f}%")

print(f"\n  [B] Rewards redemption (f21) zero rate:")
f21_zero_top = (top["f21"] == 0).mean() * 100
f21_zero_bot = (bottom["f21"] == 0).mean() * 100
print(f"      % with zero redemptions in top 20%   : {f21_zero_top:.1f}%")
print(f"      % with zero redemptions in bottom 80%: {f21_zero_bot:.1f}%")

print(f"\n  [C] Revenue-to-cost ratio (raw sum, test set):")
rev_cols  = ["f1", "f5", "f6", "f7", "f8", "f9", "f10"]
cost_cols = ["f21", "f13", "f14", "f15", "f16"]
top_rev   = top[rev_cols].sum(axis=1).mean()
top_cost  = top[cost_cols].sum(axis=1).mean()
bot_rev   = bottom[rev_cols].sum(axis=1).mean()
bot_cost  = bottom[cost_cols].sum(axis=1).mean()
print(f"      Top 20%   avg raw revenue proxy : {top_rev:>12,.0f}")
print(f"      Top 20%   avg raw cost proxy    : {top_cost:>12,.0f}")
print(f"      Bottom 80% avg raw revenue proxy: {bot_rev:>12,.0f}")
print(f"      Bottom 80% avg raw cost proxy   : {bot_cost:>12,.0f}")

print(f"\n  [D] Double-reward check — are category-active customers over-represented?")
cat_feats = ["f6", "f7", "f8", "f9", "f10"]
cat_active_top = (df_test_raw.loc[df_test_raw["top20"]==1, cat_feats].sum(axis=1) > 0).mean() * 100
cat_active_bot = (df_test_raw.loc[df_test_raw["top20"]==0, cat_feats].sum(axis=1) > 0).mean() * 100
print(f"      % with non-null category spend in top 20%   : {cat_active_top:.1f}%")
print(f"      % with non-null category spend in bottom 80%: {cat_active_bot:.1f}%")
if cat_active_top > cat_active_bot + 15:
    print(f"  ⚠  Top 20% is heavily skewed toward category-active customers.")
    print(f"     Consider reducing f6-f10 weights or adding a category-null penalty adjustment.")
else:
    print(f"  ✓ Category-active representation looks proportional.")

print(f"\n  [E] Risk-revolve tension:")
high_revolve_low_risk = ((top["f1"] > top["f1"].median()) & (top["f11"] < 0.05)).mean() * 100
print(f"      % of top 20% with above-median revolve AND risk < 0.05: {high_revolve_low_risk:.1f}%")
print(f"      (Should be a large proportion — the ideal Premier customer)")


# ══════════════════════════════════════════════════════════════════════════════
# DIRECTIONAL SANITY SCORE — single number for comparing weight iterations
# ══════════════════════════════════════════════════════════════════════════════
section("DIRECTIONAL SANITY SCORE  (use to compare weight versions)")

print("""
  This score measures how cleanly the top 20% is separated from the bottom 80%
  on each key economic dimension. Each dimension is scored as:
    (top_20_mean - bottom_80_mean) / population_std  (Cohen's d)
  Revenue dimensions: positive d is good (top 20% should be higher).
  Cost dimensions:    negative d is good (top 20% should be lower).
  The overall DSS = mean(|d|) across all dimensions — higher is better.
""")

dims = {
    "f1":  ("revenue", "Revolve Balance"),
    "f5":  ("revenue", "Total Spend"),
    "f11": ("cost",    "Risk Score"),
    "f21": ("cost",    "Points Redeemed"),
    "f3":  ("cost",    "Collections"),
    "f13": ("cost",    "Lounge Visits"),
}

dss_parts = []
print(f"  {'Dimension':<25} {'Cohen d':>9}  {'Direction':>10}  {'Contributes?':>13}")
print(f"  {SEP2}")

for feat, (role, label) in dims.items():
    col   = df_test_raw[feat]
    top_m = df_test_raw.loc[df_test_raw["top20"]==1, feat].mean()
    bot_m = df_test_raw.loc[df_test_raw["top20"]==0, feat].mean()
    std   = col.std()
    d     = (top_m - bot_m) / std if std > 0 else 0.0
    expected_sign = "positive" if role == "revenue" else "negative"
    correct = (d > 0 and role == "revenue") or (d < 0 and role == "cost")
    dss_parts.append(abs(d))
    print(f"  {label:<25} {d:>9.4f}  {expected_sign:>10}  {'✓' if correct else '✗  FAIL':>13}")

dss = np.mean(dss_parts)
print(f"\n  ► Directional Sanity Score (DSS): {dss:.4f}")
print(f"    Interpretation: >0.30 = good separation  |  >0.50 = strong  |  <0.15 = weak")
print(f"    Use this number to compare weight versions — higher DSS = better equation.")


# ══════════════════════════════════════════════════════════════════════════════
# DIAGNOSTIC PLOTS
# ══════════════════════════════════════════════════════════════════════════════
section("SAVING DIAGNOSTIC PLOTS")

fig = plt.figure(figsize=(20, 14))
gs  = gridspec.GridSpec(3, 4, figure=fig, hspace=0.45, wspace=0.35)

# 1. Score distribution with top 20% shaded
ax1 = fig.add_subplot(gs[0, :2])
scores = df_test["profit_score"]
ax1.hist(scores, bins=100, color="#bdc3c7", edgecolor="none", label="Bottom 80%")
ax1.hist(scores[df_test["top20"]==1], bins=100, color="#e74c3c", edgecolor="none",
         alpha=0.7, label="Top 20%")
ax1.axvline(cutoff_test, color="#c0392b", linewidth=2, linestyle="--", label="Cutoff")
ax1.set_title("Profitability Score Distribution (test set)", fontsize=10)
ax1.set_xlabel("Score")
ax1.legend(fontsize=8)

# 2. Score vs f5 (total spend) scatter — check spend drives top 20%
ax2 = fig.add_subplot(gs[0, 2:])
sample = df_test_raw.sample(n=min(8000, len(df_test_raw)), random_state=42)
colors = ["#e74c3c" if t else "#bdc3c7" for t in sample["top20"]]
ax2.scatter(sample["f5"], sample["profit_score"], c=colors, alpha=0.3, s=4)
ax2.set_title("Score vs Total Spend (red = top 20%)", fontsize=10)
ax2.set_xlabel("f5 — Total Spend (raw)")
ax2.set_ylabel("Profit Score")

# 3-6. Key feature distributions: top 20% vs rest (4 panels)
compare_feats = [
    ("f5",  "Total Spend",       "#27ae60"),
    ("f1",  "Revolve Balance",   "#2980b9"),
    ("f11", "Risk Score",        "#c0392b"),
    ("f21", "Points Redeemed",   "#8e44ad"),
]
for i, (feat, label, color) in enumerate(compare_feats):
    ax = fig.add_subplot(gs[1, i])
    top_vals    = df_test_raw.loc[df_test_raw["top20"]==1, feat]
    bottom_vals = df_test_raw.loc[df_test_raw["top20"]==0, feat]
    ax.hist(bottom_vals, bins=40, color="#bdc3c7", alpha=0.6, density=True, label="Bot 80%")
    ax.hist(top_vals,    bins=40, color=color,     alpha=0.7, density=True, label="Top 20%")
    ax.set_title(f"{feat} — {label}", fontsize=9)
    ax.legend(fontsize=7)
    ax.set_xlabel("Raw value")

# 7-8. Risk-revolve scatter (should show top 20% = high revolve + low risk)
ax7 = fig.add_subplot(gs[2, :2])
s2 = df_test_raw.sample(n=min(8000, len(df_test_raw)), random_state=1)
c2 = ["#e74c3c" if t else "#bdc3c7" for t in s2["top20"]]
ax7.scatter(s2["f1"], s2["f11"], c=c2, alpha=0.3, s=4)
ax7.set_title("Revolve (f1) vs Risk (f11)\nTop 20% should cluster: high f1, low f11", fontsize=9)
ax7.set_xlabel("f1 — Revolve Balance")
ax7.set_ylabel("f11 — Risk Score")

# 9-10. Cost feature boxplots: top 20% vs rest
ax8 = fig.add_subplot(gs[2, 2:])
cost_compare = pd.DataFrame({
    "f21_top":  [df_test_raw.loc[df_test_raw["top20"]==1, "f21"].median()],
    "f21_bot":  [df_test_raw.loc[df_test_raw["top20"]==0, "f21"].median()],
    "f13_top":  [df_test_raw.loc[df_test_raw["top20"]==1, "f13"].median()],
    "f13_bot":  [df_test_raw.loc[df_test_raw["top20"]==0, "f13"].median()],
})
x    = np.arange(2)
w    = 0.35
tops = [
    df_test_raw.loc[df_test_raw["top20"]==1, "f21"].median(),
    df_test_raw.loc[df_test_raw["top20"]==1, "f13"].median(),
]
bots = [
    df_test_raw.loc[df_test_raw["top20"]==0, "f21"].median(),
    df_test_raw.loc[df_test_raw["top20"]==0, "f13"].median(),
]
ax8.bar(x - w/2, tops, w, label="Top 20%",    color="#e74c3c", alpha=0.8)
ax8.bar(x + w/2, bots, w, label="Bottom 80%", color="#bdc3c7", alpha=0.8)
ax8.set_xticks(x)
ax8.set_xticklabels(["Pts Redeemed (f21)", "Lounge Visits (f13)"])
ax8.set_title("Cost Feature Medians: Top 20% vs Bottom 80%\n(Top 20% should be lower)", fontsize=9)
ax8.legend(fontsize=8)

fig.suptitle(
    f"Validation Harness — Profitability Equation Diagnostics\n"
    f"Revenue weights: +{W_REV:.2f}  |  Cost weights: {W_COST:.2f}  |  DSS: {dss:.4f}",
    fontsize=11,
)

plot_path = f"{OUT_DIR}/validation_diagnostics.png"
fig.savefig(plot_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"\n  Saved → {plot_path}")


# ══════════════════════════════════════════════════════════════════════════════
# SUBMISSION PREVIEW
# ══════════════════════════════════════════════════════════════════════════════
section("SUBMISSION PREVIEW (top 20 and bottom 20 by score)")

df_all = df_ranked.copy()
df_all["profit_score"] = sum(w * df_all[feat] for feat, w in WEIGHTS.items())
df_all["rank_position"] = df_all["profit_score"].rank(ascending=False, method="first").astype(int)
df_all_sorted = df_all.sort_values("profit_score", ascending=False)

print("\n  Top 20 customers by profitability score:\n")
top20_preview = df_all_sorted[["id", "profit_score", "rank_position"]].head(20)
print(top20_preview.to_string(index=False))

print("\n  Bottom 20 customers by profitability score:\n")
bot20_preview = df_all_sorted[["id", "profit_score", "rank_position"]].tail(20)
print(bot20_preview.to_string(index=False))

# save full scored file for submission template
submission = df_all[["id", "profit_score", "rank_position"]].sort_values("rank_position")
submission_path = f"{OUT_DIR}/submission_scores.csv"
submission.to_csv(submission_path, index=False)
print(f"\n  Full scored file saved → {submission_path}")
print(f"  Rows in top 20% (all 500K): {(df_all['profit_score'] >= df_all['profit_score'].quantile(0.80)).sum():,}")


# ══════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
section("FINAL SUMMARY")

print(f"""
  Equation version stats:
    Revenue weight total : +{W_REV:.2f}
    Cost weight total    : {W_COST:.2f}
    Net balance          : {W_REV + W_COST:.2f}

  Test set (30% / private proxy):
    Customers evaluated  : {len(df_test):,}
    Top 20% identified   : {n_top_test:,}
    Sanity checks passed : {sanity_passes}/{sanity_total}
    Directional Sanity Score (DSS): {dss:.4f}

  Key flags:
    Collections-free top 20%    : {f3_zero_top:.1f}%
    Zero-redemption top 20%     : {f21_zero_top:.1f}%
    Category-active top 20%     : {cat_active_top:.1f}% (population avg: {(df_test_raw[cat_feats].sum(axis=1)>0).mean()*100:.1f}%)
    High-revolve + low-risk in top 20%: {high_revolve_low_risk:.1f}%

  To iterate: change WEIGHTS dict above and re-run this script.
  Compare DSS across runs — higher DSS = better economic separation.
  Only submit to competition when DSS improves AND sanity checks all pass.
""")
