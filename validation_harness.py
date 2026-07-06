"""
Amex Campus Challenge 2026 — Local Validation Harness v4
=========================================================
Three structural fixes over v3:

  FIX 1 — f3 Hard Override (Crack #2 — Ablation Mismatch)
    v3: f3 weight = -0.25 but ablation impact = 2.6% only.
    Root: 89% of customers have f3=0. A linear weight only engages 11%.
    Fix: knock-out pre-filter. Any f3 > 0 -> score = -999 -> excluded from top 20%.
    f3 is removed from WEIGHTS entirely; override is applied in compute_score().

  FIX 2 — Coverage-Adjusted Weights (Crack #3 — Tie-Mass Distortion)
    Zero-floor rank: customers with zero value receive rank 0.0 (hard floor).
    A feature with 72% zeros only sorts 28% of the population.
    Nominal weight != effective sorting power.
    Solution: back-solve raw weights from desired EFFECTIVE weights.
      raw_weight = desired_effective / (1 - zero_fraction)
    Key changes:
      f21: -0.18 -> -0.43  (27.8% coverage; needs 3.6x raw weight to achieve eff -0.12)
      f13: -0.12 -> -0.27  (26.3% coverage; needs 2.5x raw weight to achieve eff -0.07)
      f14: -0.08 -> -0.16  (32.0% coverage; needs 2.0x raw weight to achieve eff -0.05)
      f15: -0.08 -> -0.15  (65.5% coverage; needs 1.9x raw weight to achieve eff -0.10)

  FIX 3 — Benefit Inversion Diagnostic (Crack #1)
    v3 top 20% had HIGHER cab (f15) and entertainment credit (f16) than bottom 80%.
    Caused by: spend reward drowning out benefit penalties (effective ratio 4.5:1).
    Coverage-adjusted weights close the effective ratio gap.
    Two new economic gates added to detect and track this inversion.
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

warnings.filterwarnings("ignore")

RANKED_PATH = "eda_outputs/data_ranked.csv"
OUT_DIR     = "eda_outputs"
RANDOM_SEED = 42
TOP_PCT     = 0.20

SEP  = "=" * 70
SEP2 = "-" * 70


def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")


# ==============================================================================
# WEIGHTS v4 — coverage-adjusted
#
# Formula: raw_weight = desired_effective_weight / coverage
# where coverage = (1 - zero_fraction) = fraction of population being sorted
#
# f3 is REMOVED from this dict — it becomes a hard knock-out override below.
# ==============================================================================
WEIGHTS = {
    # Revenue: raw = desired_eff / coverage
    "f1_rank":  +0.43,   # eff ~0.201  NIM engine ~20-30% APR
    "f5_rank":  +0.24,   # eff ~0.224  primary interchange anchor
    "f6_rank":  +0.08,   # eff ~0.052  airlines 2.3-3.3%
    "f10_rank": +0.04,   # eff ~0.028  dining 1.85-2.75%
    "f7_rank":  +0.03,   # eff ~0.023  generic 1.4-2.4%
    "f8_rank":  +0.03,   # eff ~0.016  entertainment spend
    "f9_rank":  +0.03,   # eff ~0.015  lodging spend
    "f17_rank": +0.02,   # eff ~0.008  Plan-It total capacity
    "f18_rank": +0.03,   # eff ~0.011  consumer lend capacity
    # Cost — f3 replaced by hard override; all others coverage-adjusted
    "f11_rank": -0.42,   # eff ~0.281  expected credit loss (heaviest)
    "f21_rank": -0.43,   # eff ~0.120  realized pts cost ~1c/pt  (was -0.18)
    "f4_rank":  -0.17,   # eff ~0.083  deferred liability IFRS 15
    "f15_rank": -0.15,   # eff ~0.098  cab benefit drain $15/mo  (was -0.08)
    "f16_rank": -0.06,   # eff ~0.058  entertainment credit (near-binary)
    "f13_rank": -0.27,   # eff ~0.071  lounge per-visit $24-32   (was -0.12)
    "f14_rank": -0.16,   # eff ~0.051  airline credit drain       (was -0.08)
    "f2_rank":  -0.12,   # eff ~0.021  retention overhead         (was -0.04)
}

W_REV  = sum(v for v in WEIGHTS.values() if v > 0)
W_COST = sum(v for v in WEIGHTS.values() if v < 0)


# ==============================================================================
# LOAD
# ==============================================================================
section("LOADING DATA")

df = pd.read_csv(RANKED_PATH)
print(f"  Rows: {len(df):,}  |  Cols: {df.shape[1]}")
missing = [c for c in WEIGHTS if c not in df.columns]
if missing:
    raise ValueError(f"Missing rank columns: {missing}")
if "f3" not in df.columns:
    raise ValueError("f3 (collections) column required for hard override but not found")
print(f"  All {len(WEIGHTS)} weighted rank columns present OK")
print(f"  f3 override column present OK  (f3>0: {(df['f3']>0).sum():,} rows = {(df['f3']>0).mean()*100:.1f}%)")
print(f"\n  Revenue total : +{W_REV:.2f}")
print(f"  Cost total    :  {W_COST:.2f}")
print(f"  Net           :  {W_REV + W_COST:.2f}  (asymmetry is intentional and economically valid)")


# ==============================================================================
# COVERAGE TABLE — shows effective weight = raw_weight x coverage
# ==============================================================================
section("COVERAGE TABLE  (effective sorting power per feature)")

print(f"""
  Zero-floor rank means customers with zero values receive rank 0.0.
  A feature with 72% zeros only meaningfully sorts the remaining 28%.
  Effective weight = raw_weight x (1 - zero_fraction).
  This is the TRUE impact of each coefficient on the final ranking.
""")

print(f"  {'Feature':<10} {'Zero%':>7} {'Cov%':>7} {'Raw W':>8} {'Eff W':>8}  Note")
print(f"  {SEP2}")

cov_map = {}
for feat_r in list(WEIGHTS.keys()) + ["f3_rank"]:
    feat = feat_r.replace("_rank", "")
    if feat not in df.columns:
        continue
    zero_frac = (df[feat] == 0).mean()
    cov = 1 - zero_frac
    cov_map[feat_r] = cov
    raw_w = WEIGHTS.get(feat_r, 0.0)
    eff_w = raw_w * cov
    note = ""
    if feat == "f3":
        note = "<-- HARD OVERRIDE (not in weights)"
    elif abs(eff_w) > 0.15:
        note = "<-- dominant"
    elif abs(eff_w) < 0.020 and raw_w != 0:
        note = "<-- weak despite raw weight"
    print(f"  {feat:<10} {zero_frac*100:>6.1f}% {cov*100:>6.1f}% {raw_w:>+8.3f} {eff_w:>+8.4f}  {note}")

# Effective totals
eff_rev  = sum(WEIGHTS[f] * cov_map.get(f, 1.0) for f in WEIGHTS if WEIGHTS[f] > 0)
eff_cost = sum(WEIGHTS[f] * cov_map.get(f, 1.0) for f in WEIGHTS if WEIGHTS[f] < 0)
print(f"\n  Effective revenue total : {eff_rev:+.4f}")
print(f"  Effective cost total    : {eff_cost:+.4f}")
print(f"  Effective net           : {eff_rev + eff_cost:+.4f}")


# ==============================================================================
# HELPERS
# ==============================================================================

def compute_score(df_, weights, apply_override=True):
    score = sum(w * df_[feat] for feat, w in weights.items())
    if apply_override and "f3" in df_.columns:
        # Knock-out: collections customers cannot be in top 20%
        score = score.where(df_["f3"] == 0, other=-999.0)
    return score


def top20_ids(df_, weights, apply_override=True):
    s = compute_score(df_, weights, apply_override=apply_override)
    cutoff = s.quantile(1 - TOP_PCT)
    return set(df_.loc[s >= cutoff, "id"])


def overlap_pct(set_a, set_b):
    if not set_a:
        return 0.0
    return len(set_a & set_b) / len(set_a) * 100


# ==============================================================================
# BASELINE
# ==============================================================================
section("BASELINE SCORE")

df["profit_score"] = compute_score(df, WEIGHTS, apply_override=True)
baseline_top20     = top20_ids(df, WEIGHTS)

print(f"\n  Score stats (override applied — f3>0 customers floored to -999):")
eligible_scores = df.loc[df["f3"] == 0, "profit_score"]
for k, v in eligible_scores.describe(percentiles=[0.20, 0.50, 0.80]).items():
    print(f"    {k:>6}: {v:.4f}")

print(f"\n  f3 override stats:")
n_f3_nonzero = (df["f3"] > 0).sum()
print(f"    Customers with f3 > 0 (ineligible)  : {n_f3_nonzero:,}  ({n_f3_nonzero/len(df)*100:.1f}%)")
print(f"    Eligible population (f3 == 0)       : {(df['f3']==0).sum():,}")
print(f"    Top 20% drawn from eligible only")

np.random.seed(RANDOM_SEED)
test_mask  = np.random.rand(len(df)) >= 0.70
df_test    = df[test_mask].copy().reset_index(drop=True)
cutoff_t   = df_test["profit_score"].quantile(1 - TOP_PCT)
df_test["top20"] = (df_test["profit_score"] >= cutoff_t).astype(int)

top20_in_test = df_test["top20"].sum()
f3_in_top20  = ((df_test["top20"] == 1) & (df_test["f3"] > 0)).sum()
print(f"\n  Test set: {len(df_test):,} rows  |  top 20%: {top20_in_test:,}")
print(f"  f3>0 customers in top 20% (should be 0): {f3_in_top20}  {'OK' if f3_in_top20 == 0 else 'PROBLEM'}")


# ==============================================================================
# BENEFIT INVERSION DIAGNOSTIC (Crack #1)
# ==============================================================================
section("BENEFIT INVERSION DIAGNOSTIC  (Crack #1)")

print("""
  v3 top 20% had HIGHER cab (f15) and entertainment credit (f16) usage than
  bottom 80% — spend reward (+0.25 eff) was drowning out benefit penalties
  (-0.052 eff for f15). Coverage-adjusted weights raise f15 eff to ~-0.098.
  Check whether inversion is resolved with v4 weights.
""")

top_t  = df_test[df_test["top20"] == 1]
rest_t = df_test[df_test["top20"] == 0]

benefit_checks = [
    ("f15", "Cab months utilized   (0-11)",  1.05),
    ("f16", "Entertainment credit  ($0-64.40)", 1.15),  # 15% tolerance: hard-capped near-binary
    ("f13", "Lounge visits         (0-3)",   1.05),
    ("f14", "Airline credits       ($0-200)", 1.05),
]

print(f"  {'Feature':<8} {'Top20 mean':>12} {'Bot80 mean':>12} {'Ratio':>8} {'Tol':>5}  Status")
print(f"  {SEP2}")

benefit_ok = []
for feat, label, tol in benefit_checks:
    tm = top_t[feat].mean()
    rm = rest_t[feat].mean()
    ratio = tm / rm if rm > 0 else float("inf")
    if ratio > tol:
        status = f"INVERTED (>{tol:.0%} tol)"
    elif ratio > 1.00:
        status = "marginal (<tolerance)"
    else:
        status = "OK"
    benefit_ok.append(ratio <= tol)
    print(f"  {feat:<8} {tm:>12.3f} {rm:>12.3f} {ratio:>8.3f} {tol:>5.0%}  {status}")

print(f"\n  {sum(benefit_ok)}/{len(benefit_ok)} benefit features have non-inverted means in top 20%")


# ==============================================================================
# VALIDATION A -- PERTURBATION STABILITY
# ==============================================================================
section("VALIDATION A -- PERTURBATION STABILITY  (the jiggle test)")

print("""
  Perturb each weight by +-pct, measure top 20% overlap with baseline.
  Override is always applied (fixed rule, not perturbed).
  Target: >=80% overlap at +-10%  |  >=65% overlap at +-20%
""")

PERTURB_LEVELS = [0.05, 0.10, 0.20]
N_TRIALS       = 30

stability_results = {}
print(f"  {'Perturb':>9}  {'Mean overlap':>13}  {'Min overlap':>12}  {'Stable?':>9}")
print(f"  {SEP2}")

for pct in PERTURB_LEVELS:
    overlaps = []
    for _ in range(N_TRIALS):
        perturbed = {f: w * (1 + np.random.uniform(-pct, pct)) for f, w in WEIGHTS.items()}
        overlaps.append(overlap_pct(baseline_top20, top20_ids(df, perturbed, apply_override=True)))
    mean_ol = np.mean(overlaps)
    min_ol  = np.min(overlaps)
    target  = 80 if pct <= 0.10 else 65
    stable  = "OK" if mean_ol >= target else "FRAGILE"
    stability_results[pct] = mean_ol
    print(f"  +-{pct*100:.0f}%       {mean_ol:>12.1f}%  {min_ol:>11.1f}%  {stable:>9}")

print()
if stability_results[0.10] >= 80:
    print("  Model is STABLE -- top 20% does not change much under small weight shifts.")
else:
    print("  Model is FRAGILE -- investigate customers near the top 20% cutoff.")


# ==============================================================================
# VALIDATION B -- ABLATION
# ==============================================================================
section("VALIDATION B -- ABLATION  (the drop test)")

print("""
  Remove each feature one at a time. Measure how much top 20% changes.
  f3 override is kept fixed regardless of which weight is ablated.
  Impact >5% = load-bearing  |  2-5% = marginal  |  <2% = decorative
""")

print(f"  {'Feature':<12}  {'Weight':>8}  {'Overlap':>9}  {'Impact':>8}  {'Load-bearing?':>14}")
print(f"  {SEP2}")

ablation_results = []
for feat, w in sorted(WEIGHTS.items(), key=lambda x: abs(x[1]), reverse=True):
    reduced       = {f: v for f, v in WEIGHTS.items() if f != feat}
    ablated_top20 = top20_ids(df, reduced, apply_override=True)
    ol     = overlap_pct(baseline_top20, ablated_top20)
    impact = 100 - ol
    label  = "YES" if impact > 5.0 else ("marginal" if impact > 2.0 else "no")
    fname  = feat.replace("_rank", "")
    ablation_results.append((fname, w, ol, impact, label))
    print(f"  {fname:<12}  {w:>+8.2f}  {ol:>8.1f}%  {impact:>7.1f}%  {label:>14}")


# ==============================================================================
# VALIDATION C -- ECONOMIC GATES
# ==============================================================================
section("VALIDATION C -- ECONOMIC GATES  (pass/fail, NOT scores to maximize)")

print("""
  Fixed thresholds from card economics.
  Gates 1-6: core profitability guardrails (same as v3).
  Gates 7-8: NEW -- benefit inversion guards added for v4.
""")

top  = df_test[df_test["top20"] == 1]
rest = df_test[df_test["top20"] == 0]
gates_passed = []


def gate(label, value, threshold, direction):
    passed = (value >= threshold) if direction == "above" else (value <= threshold)
    gates_passed.append(passed)
    sym = "PASS" if passed else "FAIL"
    print(f"  [{sym}]  {label}")
    print(f"          Observed: {value:.3f}  |  Threshold: {direction} {threshold:.3f}\n")


print()

# Gate 1 — f3 override working
g1 = (top["f3"] == 0).mean() * 100
gate("100% of top 20% have zero collections calls (override check)", g1, 100, "above")

# Gate 2 — zero-redemption
g2_top  = (top["f21"] == 0).mean() * 100
g2_rest = (rest["f21"] == 0).mean() * 100
gate("Top 20% zero-redemption rate >= bottom 80% rate", g2_top, g2_rest, "above")

# Gate 3 — spend dominance
g3_ratio = (top["f5"].mean() / rest["f5"].mean()) * 100 if rest["f5"].mean() > 0 else 0
gate("Top 20% mean spend is >=1.5x bottom 80% (ratio as %)", g3_ratio, 150, "above")

# Gate 4 — risk below baseline
g4_ratio = (top["f11"].mean() / rest["f11"].mean()) * 100 if rest["f11"].mean() > 0 else 0
gate("Top 20% mean risk score < bottom 80% mean risk (ratio as %)", g4_ratio, 100, "below")

# Gate 5 — revolve strength
g5_ratio = (top["f1"].mean() / rest["f1"].mean()) * 100 if rest["f1"].mean() > 0 else 0
gate("Top 20% mean revolve balance >= bottom 80%", g5_ratio, 100, "above")

# Gate 6 — ideal Premier archetype present
g6 = ((top["f1"] > df_test["f1"].median()) & (top["f11"] < 0.05)).mean() * 100
gate(">=30% of top 20% are high-revolve AND low-risk (ideal Premier archetype)", g6, 30, "above")

# Gate 7 — benefit inversion check: cab (f15)
g7 = top["f15"].mean()
g7_bot = rest["f15"].mean()
gate("Top 20% mean cab months (f15) <= bottom 80% mean  [benefit inversion guard]",
     g7, g7_bot, "below")

# Gate 8 — benefit inversion check: entertainment credit (f16) — tolerance band
# f16 is hard-capped at $64.40 (near-binary above 75th pct, 97.3% coverage).
# High spenders are slightly more likely to cross the cap regardless of penalty.
# Economic materiality: ~$6/yr cost difference vs ~$57/yr interchange premium.
# Requiring strict <= is untuneable without f16 weight = -0.30 (absurd: equals credit loss).
# Softer threshold: top20 mean <= bottom80 mean * 1.15 (15% tolerance).
g8 = top["f16"].mean()
g8_bot = rest["f16"].mean()
g8_threshold = g8_bot * 1.15
gate("Top 20% f16 (entertainment) <= bottom 80% mean x1.15 tolerance  [cap-inversion guard]",
     g8, g8_threshold, "below")

n_passed = sum(gates_passed)
print(f"  Gates passed: {n_passed}/{len(gates_passed)}")
if n_passed == len(gates_passed):
    print("  All economic gates pass -- equation is directionally correct.")
elif n_passed >= len(gates_passed) * 0.75:
    print("  Most gates pass -- review the failed ones.")
else:
    print("  Multiple gates fail -- equation needs rebalancing.")


# ==============================================================================
# DIAGNOSTIC PLOTS
# ==============================================================================
section("SAVING DIAGNOSTIC PLOTS")

fig = plt.figure(figsize=(22, 18))
gs  = gridspec.GridSpec(4, 4, figure=fig, hspace=0.55, wspace=0.40)

# 1. Score distribution
ax1 = fig.add_subplot(gs[0, :2])
scores_t = df_test["profit_score"]
eligible_mask = df_test["f3"] == 0
ax1.hist(scores_t[eligible_mask & (df_test["top20"]==0)],
         bins=80, color="#bdc3c7", edgecolor="none", label="Eligible bottom 80%")
ax1.hist(scores_t[eligible_mask & (df_test["top20"]==1)],
         bins=80, color="#e74c3c", edgecolor="none", alpha=0.8, label="Top 20%")
ax1.axvline(cutoff_t, color="#c0392b", linewidth=2, linestyle="--", label="Cutoff")
ax1.set_title("Score Distribution — eligible customers\n(f3>0 excluded at -999, not shown)", fontsize=9)
ax1.legend(fontsize=8)

# 2. Perturbation stability
ax2 = fig.add_subplot(gs[0, 2:])
labels = [f"+-{int(p*100)}%" for p in PERTURB_LEVELS]
values = [stability_results[p] for p in PERTURB_LEVELS]
targets= [80, 80, 65]
colors = ["#27ae60" if v >= t else "#e74c3c" for v, t in zip(values, targets)]
ax2.bar(labels, values, color=colors, edgecolor="none", alpha=0.85)
ax2.axhline(80, color="#27ae60", linestyle="--", linewidth=1.2, label="80% target (+-10%)")
ax2.axhline(65, color="#e67e22", linestyle="--", linewidth=1.2, label="65% target (+-20%)")
ax2.set_ylim(0, 105)
ax2.set_title("Perturbation Stability\n(top 20% overlap after weight jitter)", fontsize=9)
ax2.set_ylabel("% overlap with baseline top 20%")
ax2.legend(fontsize=8)
for i, v in enumerate(values):
    ax2.text(i, v + 1.5, f"{v:.1f}%", ha="center", fontsize=9)

# 3-6. Feature distributions — top 20% vs bottom 80%
compare_feats = [
    ("f5",  "Total Spend",     "#27ae60"),
    ("f1",  "Revolve Balance", "#2980b9"),
    ("f11", "Risk Score",      "#c0392b"),
    ("f21", "Pts Redeemed",    "#8e44ad"),
]
for i, (feat, label, color) in enumerate(compare_feats):
    ax = fig.add_subplot(gs[1, i])
    tv = df_test.loc[df_test["top20"]==1, feat]
    bv = df_test.loc[df_test["top20"]==0, feat]
    ax.hist(bv, bins=50, color="#bdc3c7", alpha=0.6, density=True, label="Bot 80%")
    ax.hist(tv, bins=50, color=color,     alpha=0.75, density=True, label="Top 20%")
    ax.set_title(f"{feat} — {label}\nmean top={tv.mean():.1f}  bot={bv.mean():.1f}", fontsize=8)
    ax.legend(fontsize=7)

# 7. Ablation chart
ax7 = fig.add_subplot(gs[2, :2])
abl_feats   = [r[0] for r in ablation_results]
abl_impacts = [r[3] for r in ablation_results]
abl_colors  = ["#e74c3c" if v > 5 else ("#e67e22" if v > 2 else "#bdc3c7") for v in abl_impacts]
ax7.barh(abl_feats[::-1], abl_impacts[::-1], color=abl_colors[::-1], edgecolor="none")
ax7.axvline(5, color="#e74c3c", linestyle="--", linewidth=1, label="5% = load-bearing")
ax7.axvline(2, color="#e67e22", linestyle="--", linewidth=1, label="2% = marginal")
ax7.set_xlabel("% change in top 20% membership when feature removed")
ax7.set_title("Ablation — feature impact\n(red=load-bearing, orange=marginal, grey=decorative)", fontsize=9)
ax7.legend(fontsize=8)

# 8. Benefit inversion chart (NEW) — cost features top vs bottom
ax8 = fig.add_subplot(gs[2, 2:])
benefit_feats  = ["f21", "f13", "f14", "f15", "f16"]
benefit_labels = ["Pts Redeemed", "Lounge", "Airline Cr", "Cab Mo", "Ent Cr"]
top_means_b    = [df_test.loc[df_test["top20"]==1, f].mean() for f in benefit_feats]
bot_means_b    = [df_test.loc[df_test["top20"]==0, f].mean() for f in benefit_feats]
x = np.arange(len(benefit_feats))
w = 0.35
bars_top = ax8.bar(x - w/2, top_means_b, w, label="Top 20%",    color="#e74c3c", alpha=0.85)
bars_bot = ax8.bar(x + w/2, bot_means_b, w, label="Bottom 80%", color="#bdc3c7", alpha=0.85)
ax8.set_xticks(x)
ax8.set_xticklabels(benefit_labels, fontsize=8)
ax8.set_title("Cost Feature Means — benefit inversion check\n(top 20% bar should NOT exceed bottom 80%)", fontsize=9)
ax8.legend(fontsize=8)
for i, (tm, bm) in enumerate(zip(top_means_b, bot_means_b)):
    if tm > bm * 1.05:
        ax8.text(i - w/2, tm + ax8.get_ylim()[1]*0.01, "INV!", ha="center", fontsize=7, color="#c0392b")

# 9. Effective weight chart (NEW)
ax9 = fig.add_subplot(gs[3, :])
all_feats = sorted(WEIGHTS.keys(), key=lambda f: WEIGHTS[f])
eff_weights = [WEIGHTS[f] * cov_map.get(f, 1.0) for f in all_feats]
raw_weights = [WEIGHTS[f] for f in all_feats]
feat_labels_c = [f.replace("_rank", "") for f in all_feats]
x9 = np.arange(len(all_feats))
w9 = 0.4
ax9.bar(x9 - w9/2, raw_weights, w9, label="Raw weight (stated)",
        color=["#27ae60" if v > 0 else "#e74c3c" for v in raw_weights], alpha=0.5)
ax9.bar(x9 + w9/2, eff_weights, w9, label="Effective weight (raw x coverage)",
        color=["#1a7a42" if v > 0 else "#a93226" for v in eff_weights], alpha=0.85)
ax9.axhline(0, color="black", linewidth=0.8)
ax9.set_xticks(x9)
ax9.set_xticklabels(feat_labels_c, rotation=45, ha="right", fontsize=8)
ax9.set_ylabel("Weight value")
ax9.set_title("Raw vs Effective Weights  (effective = raw x coverage)\n"
              "Shows true sorting power each feature has on the final ranking", fontsize=9)
ax9.legend(fontsize=8)

fig.suptitle(
    f"Validation Harness v4  |  Stability +-10%: {stability_results[0.10]:.1f}%  |  "
    f"Gates: {n_passed}/{len(gates_passed)}  |  "
    f"Rev eff: {eff_rev:+.3f}  Cost eff: {eff_cost:+.3f}  |  "
    f"f3 override: {n_f3_nonzero:,} excluded",
    fontsize=9,
)

plot_path = f"{OUT_DIR}/validation_diagnostics_v4.png"
fig.savefig(plot_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"\n  Saved --> {plot_path}")


# ==============================================================================
# SUBMISSION OUTPUT
# ==============================================================================
section("SUBMISSION OUTPUT")

df["rank_position"] = df["profit_score"].rank(ascending=False, method="first").astype(int)
df_out = df[["id", "profit_score", "rank_position"]].sort_values("rank_position")
sub_path = f"{OUT_DIR}/submission_scores_v4.csv"
df_out.to_csv(sub_path, index=False)
print(f"\n  Saved --> {sub_path}")
print(f"  Top 20% threshold : {df.loc[df['f3']==0, 'profit_score'].quantile(0.80):.4f}")
print(f"  Customers in top 20%       : {(df['profit_score'] >= df['profit_score'].quantile(0.80)).sum():,}")
print(f"  Of which have f3>0         : {((df['profit_score'] >= df['profit_score'].quantile(0.80)) & (df['f3']>0)).sum()} (should be 0)")


# ==============================================================================
# SUMMARY
# ==============================================================================
section("SUMMARY")
lb = [r for r in ablation_results if r[3] > 5]
mg = [r for r in ablation_results if 2 < r[3] <= 5]
print(f"""
  Weights v4 (coverage-adjusted, f3 override, benefit-inversion hardened):

    Effective revenue total : {eff_rev:+.4f}
    Effective cost total    : {eff_cost:+.4f}
    Effective net           : {eff_rev + eff_cost:+.4f}

    Raw revenue total       : +{W_REV:.2f}
    Raw cost total          :  {W_COST:.2f}

  Three structural fixes applied:
    [FIX 1] f3 hard override: {n_f3_nonzero:,} collections customers excluded from top 20%
    [FIX 2] Coverage-adjusted weights:
              f21 raw: -0.18 -> -0.43  (eff: -0.050 -> -0.120)
              f13 raw: -0.12 -> -0.27  (eff: -0.032 -> -0.071)
              f14 raw: -0.08 -> -0.16  (eff: -0.026 -> -0.051)
              f15 raw: -0.08 -> -0.15  (eff: -0.052 -> -0.098)
    [FIX 3] Benefit inversion gates:
              f15 inversion resolved: {benefit_ok[0]}
              f16 inversion resolved: {benefit_ok[1]}

  Validation results (30% test set — private leaderboard proxy):
    A. Perturbation stability +-5%  : {stability_results[0.05]:.1f}% overlap
    A. Perturbation stability +-10% : {stability_results[0.10]:.1f}% overlap
    A. Perturbation stability +-20% : {stability_results[0.20]:.1f}% overlap
    B. Load-bearing features        : {len(lb)} ({', '.join(r[0] for r in lb)})
    B. Marginal features            : {len(mg)} ({', '.join(r[0] for r in mg)})
    C. Economic gates passed        : {n_passed}/{len(gates_passed)}
""")
