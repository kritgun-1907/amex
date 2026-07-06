"""
Amex Campus Challenge 2026 — EDA Pipeline
==========================================
Phases:
  1. Missingness Map       — verify structured null groups
  2. Scale & Outliers      — describe(), magnitude gaps, negatives, caps
  3. Cross-Feature Check   — f5 vs category sum, f17 vs f18 hierarchy
  4. Imputation            — apply locked policy
  5. Rank-Transform        — normalize all features to [0,1] percentiles
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

warnings.filterwarnings("ignore")

# ── paths ──────────────────────────────────────────────────────────────────────
DATA_PATH = "6a3eb196bc7a3_campus_challenge_r1_data.csv"
OUT_DIR   = "eda_outputs"
os.makedirs(OUT_DIR, exist_ok=True)

# ── feature metadata ───────────────────────────────────────────────────────────
FEATURE_META = {
    "f1":  ("Avg Revolve Balance (12m)",        "REVENUE"),
    "f2":  ("Cancellation Calls (12m)",          "COST"),
    "f3":  ("Cancellation Calls — Collections",  "COST"),
    "f4":  ("Rewards Points Balance",            "COST-LIABILITY"),
    "f5":  ("Total Spend (12m)",                 "REVENUE"),
    "f6":  ("Airlines Spend (12m)",              "REVENUE"),
    "f7":  ("Other Spend (12m)",                 "REVENUE"),
    "f8":  ("Entertainment Spend (12m)",         "REVENUE"),
    "f9":  ("Lodging Spend (12m)",               "REVENUE"),
    "f10": ("Dining Spend (12m)",                "REVENUE"),
    "f11": ("Avg Risk Score (12m)",              "COST"),
    "f12": ("Login Counts",                      "CONTEXT"),
    "f13": ("Lounge Access — visit count 0-3",      "COST"),  # COUNT; ~$30-50/visit
    "f14": ("Airline Credits Used — dollars",       "COST"),  # dollar; capped ~$200
    "f15": ("Cab Benefits — months utilized 0-11",  "COST"),  # COUNT; ~$15/month
    "f16": ("Entertainment Credit Used — dollars",  "COST"),  # dollar; capped $64.40
    "f17": ("Total Lend Line Amount",            "REVENUE-CAPACITY"),
    "f18": ("Consumer Lend Line Amount",         "REVENUE-CAPACITY"),
    "f19": ("Supplementary Accounts",            "CONTEXT"),
    "f20": ("Active Charge Cards",               "CONTEXT"),
    "f21": ("Rewards Points Redeemed (12m)",     "COST-REALIZED"),
    "f22": ("Emails Opened (6m)",                "CONTEXT"),
    "f23": ("Emails Clicked (6m)",               "DROP"),
}

FEATURES = [f for f in FEATURE_META if f != "f23"]   # f23 dropped (87.8% null)

STRUCTURED_NULL_GROUPS = {
    "Rewards (f4, f21)":            ["f4", "f21"],
    "Category Spend (f6–f10)":      ["f6", "f7", "f8", "f9", "f10"],
    "Benefits (f13–f16)":           ["f13", "f14", "f15", "f16"],
    "Lend Lines (f17, f18)":        ["f17", "f18"],
}

IMPUTATION_POLICY = {
    "f4":  0,  "f21": 0,
    "f6":  0,  "f7":  0,  "f8":  0,  "f9":  0,  "f10": 0,
    "f13": 0,  "f14": 0,  "f15": 0,  "f16": 0,
    "f17": 0,  "f18": 0,
    "f5":  "median",
    "f11": "median",
}

SEP  = "=" * 70
SEP2 = "-" * 70


def section(title: str) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")


# ══════════════════════════════════════════════════════════════════════════════
# LOAD
# ══════════════════════════════════════════════════════════════════════════════
section("LOADING DATA")
df = pd.read_csv(DATA_PATH)
print(f"Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
print(f"Columns: {list(df.columns)}")


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — MISSINGNESS MAP
# ══════════════════════════════════════════════════════════════════════════════
section("PHASE 1 — MISSINGNESS MAP")

n = len(df)

# 1a. per-feature null table
print("\n[1a] Per-feature null counts\n")
null_df = (
    pd.DataFrame({
        "feature":     list(FEATURE_META.keys()),
        "description": [v[0] for v in FEATURE_META.values()],
        "role":        [v[1] for v in FEATURE_META.values()],
        "null_count":  [df[f].isna().sum() for f in FEATURE_META],
        "null_pct":    [df[f].isna().mean() * 100 for f in FEATURE_META],
    })
    .sort_values("null_pct", ascending=False)
    .reset_index(drop=True)
)
with pd.option_context("display.max_rows", 30, "display.float_format", "{:.1f}".format):
    print(null_df.to_string(index=False))

# 1b. verify structured null groups (same rows null together)
print(f"\n{SEP2}\n[1b] Structured null group verification\n")
for group_name, cols in STRUCTURED_NULL_GROUPS.items():
    cols_present = [c for c in cols if c in df.columns]
    null_masks   = [df[c].isna() for c in cols_present]
    joint_null   = null_masks[0].copy()
    for m in null_masks[1:]:
        joint_null &= m
    joint_count = joint_null.sum()
    first_count = null_masks[0].sum()
    synced      = "YES ✓" if joint_count == first_count else f"NO — mismatch ({first_count} vs {joint_count})"
    print(f"  {group_name:<30}  joint_null={joint_count:>7,}  ({joint_count/n*100:.1f}%)  perfectly_synced={synced}")

# 1c. missingness heatmap (sample for speed)
print(f"\n{SEP2}\n[1c] Saving missingness heatmap …")
sample = df[list(FEATURE_META.keys())].sample(n=min(5000, n), random_state=42)
fig, ax = plt.subplots(figsize=(14, 5))
sns.heatmap(sample.isna().T, cbar=False, xticklabels=False,
            yticklabels=list(FEATURE_META.keys()), ax=ax,
            cmap=["#e8f4f8", "#c0392b"])
ax.set_title("Missingness Heatmap (5,000-row sample) — red = null", fontsize=12)
plt.tight_layout()
fig.savefig(f"{OUT_DIR}/p1_missingness_heatmap.png", dpi=150)
plt.close()
print(f"  Saved → {OUT_DIR}/p1_missingness_heatmap.png")


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — SCALE & OUTLIER DETECTION
# ══════════════════════════════════════════════════════════════════════════════
section("PHASE 2 — SCALE & OUTLIER DETECTION")

# 2a. describe()
print("\n[2a] Statistical summary (all numeric features)\n")
desc = df[FEATURES].describe(percentiles=[0.01, 0.25, 0.5, 0.75, 0.99]).T
desc["range"] = desc["max"] - desc["min"]
with pd.option_context("display.float_format", "{:,.2f}".format,
                       "display.max_columns", 15,
                       "display.width", 200):
    print(desc[["count", "min", "25%", "50%", "75%", "99%", "max", "mean", "std", "range"]])

# 2b. magnitude disparity check
print(f"\n{SEP2}\n[2b] Magnitude disparity (max values)\n")
max_vals = df[FEATURES].max().sort_values(ascending=False)
for feat, val in max_vals.items():
    role = FEATURE_META[feat][1]
    flag = " ◄ EXTREME" if val > 10_000 else (" ◄ TINY" if val < 1 else "")
    print(f"  {feat:<5}  max={val:>12,.2f}  [{role}]{flag}")

# 2c. negative value audit
print(f"\n{SEP2}\n[2c] Features with negative values\n")
for feat in FEATURES:
    neg_count = (df[feat] < 0).sum()
    if neg_count > 0:
        neg_min = df[feat].min()
        print(f"  {feat}  ({FEATURE_META[feat][0]}):  {neg_count:,} negative rows  min={neg_min:.2f}")

# 2d. artificial cap detection
print(f"\n{SEP2}\n[2d] Artificial cap detection (75th pct == max)\n")
for feat in FEATURES:
    col  = df[feat].dropna()
    p75  = col.quantile(0.75)
    cmax = col.max()
    if abs(p75 - cmax) < 0.01 and cmax > 0:
        print(f"  {feat}  ({FEATURE_META[feat][0]}):  75th_pct={p75:.4f}  max={cmax:.4f}  ← CAPPED")

# 2e. distribution plots for high-impact features
print(f"\n{SEP2}\n[2e] Saving distribution plots for key features …")
key_feats = ["f5", "f1", "f7", "f11", "f21", "f4", "f13", "f14"]
fig, axes = plt.subplots(2, 4, figsize=(18, 8))
for ax, feat in zip(axes.flat, key_feats):
    data = df[feat].dropna()
    ax.hist(data, bins=60, color="#2980b9", edgecolor="none", alpha=0.8)
    ax.set_title(f"{feat} — {FEATURE_META[feat][0][:28]}", fontsize=8)
    ax.set_ylabel("Count")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.tick_params(axis="x", labelsize=7, rotation=30)
    role = FEATURE_META[feat][1]
    color = "#27ae60" if "REVENUE" in role else "#c0392b"
    ax.spines["top"].set_color(color)
    ax.spines["top"].set_linewidth(3)
plt.suptitle("Key Feature Distributions (green top = Revenue, red = Cost)", fontsize=10)
plt.tight_layout()
fig.savefig(f"{OUT_DIR}/p2_distributions.png", dpi=150)
plt.close()
print(f"  Saved → {OUT_DIR}/p2_distributions.png")


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — CROSS-FEATURE VALIDATION
# ══════════════════════════════════════════════════════════════════════════════
section("PHASE 3 — CROSS-FEATURE VALIDATION")

# 3a. f5 vs sum(f6:f10)
print("\n[3a] f5 (Total Spend) vs sum(f6:f10) (Category Spend)\n")
cat_cols  = ["f6", "f7", "f8", "f9", "f10"]
df["_cat_sum"] = df[cat_cols].fillna(0).sum(axis=1)
valid_mask = df["f5"].notna() & (df["_cat_sum"] > 0)
valid_rows = df.loc[valid_mask, ["f5", "_cat_sum"]]

pearson_r  = valid_rows["f5"].corr(valid_rows["_cat_sum"])
spearman_r = valid_rows["f5"].corr(valid_rows["_cat_sum"], method="spearman")
exact_match = (abs(valid_rows["f5"] - valid_rows["_cat_sum"]) < 1).sum()

print(f"  Rows used (both non-null, cat_sum > 0):  {len(valid_rows):,}")
print(f"  Pearson correlation:                      {pearson_r:.4f}")
print(f"  Spearman correlation:                     {spearman_r:.4f}")
print(f"  Rows where |f5 − cat_sum| < 1:           {exact_match:,}")
print()
if abs(pearson_r) < 0.2:
    print("  ► CONFIRMED: f5 and category columns are independently masked/scaled.")
    print("    Do NOT build f5 share features. Use f5 as primary anchor.")
    print("    Treat f6–f10 as independent behavioral modifiers.")

# scatter (sample)
fig, ax = plt.subplots(figsize=(7, 5))
s = valid_rows.sample(n=min(5000, len(valid_rows)), random_state=42)
ax.scatter(s["f5"], s["_cat_sum"], alpha=0.15, s=5, color="#2980b9")
ax.set_xlabel("f5 — Total Spend")
ax.set_ylabel("sum(f6:f10) — Category Spend Sum")
ax.set_title(f"f5 vs Category Sum  (Pearson r = {pearson_r:.3f})", fontsize=11)
plt.tight_layout()
fig.savefig(f"{OUT_DIR}/p3_f5_vs_catsum.png", dpi=150)
plt.close()
print(f"\n  Saved → {OUT_DIR}/p3_f5_vs_catsum.png")

# 3b. f17 vs f18 hierarchy
print(f"\n{SEP2}\n[3b] f17 (Total Lend) vs f18 (Consumer Lend) hierarchy check\n")
both_valid = df[["f17", "f18"]].dropna()
f17_gte_f18 = (both_valid["f17"] >= both_valid["f18"]).sum()
pct         = f17_gte_f18 / len(both_valid) * 100
print(f"  Rows where both f17 & f18 non-null:  {len(both_valid):,}")
print(f"  Rows where f17 >= f18:               {f17_gte_f18:,}  ({pct:.1f}%)")
print(f"  Rows where f17 < f18:                {len(both_valid) - f17_gte_f18:,}  ({100-pct:.1f}%)")
print()
if pct < 80:
    print("  ► CONFIRMED: No strict hierarchy. Do NOT build f17 − f18 as a feature.")
    print("    Treat f17 and f18 as independent, correlated capacity signals.")

# 3c. correlation heatmap (Spearman, revenue + cost features only)
print(f"\n{SEP2}\n[3c] Saving Spearman correlation heatmap …")
hmap_feats = ["f1","f5","f6","f7","f8","f9","f10",
              "f11","f13","f14","f15","f16","f4","f21","f17","f18"]
hmap_data  = df[hmap_feats].fillna(0)
corr_matrix = hmap_data.corr(method="spearman")

fig, ax = plt.subplots(figsize=(12, 10))
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
sns.heatmap(corr_matrix, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
            center=0, vmin=-1, vmax=1, linewidths=0.3, ax=ax,
            annot_kws={"size": 7})
ax.set_title("Spearman Correlation — Revenue & Cost Features", fontsize=12)
plt.tight_layout()
fig.savefig(f"{OUT_DIR}/p3_correlation_heatmap.png", dpi=150)
plt.close()
print(f"  Saved → {OUT_DIR}/p3_correlation_heatmap.png")

# cleanup temp column
df.drop(columns=["_cat_sum"], inplace=True)


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — IMPUTATION (LOCKED POLICY)
# ══════════════════════════════════════════════════════════════════════════════
section("PHASE 4 — IMPUTATION (LOCKED POLICY)")

df_imp = df.copy()
print(f"\n{'Feature':<8}  {'Policy':<34}  {'Nulls Before':>13}  {'Nulls After':>12}")
print(SEP2)

for feat, policy in IMPUTATION_POLICY.items():
    before = int(df_imp[feat].isna().sum())
    if policy == "median":
        fill_val = df_imp[feat].median()
        df_imp[feat] = df_imp[feat].fillna(fill_val)
        policy_str = f"median ({fill_val:,.2f})"
    else:
        df_imp[feat] = df_imp[feat].fillna(policy)
        policy_str = "0 (zero-fill)"
    after = int(df_imp[feat].isna().sum())
    print(f"  {feat:<6}  {policy_str:<32}  {before:>12,}  →  {after:>6,}")

# features with no explicit policy (f1=0, f2=0, f3=0 nulls; f12, f19, f20, f22 low nulls)
remaining_nulls = df_imp[FEATURES].isna().sum()
remaining_nulls = remaining_nulls[remaining_nulls > 0]
if not remaining_nulls.empty:
    print(f"\n  Remaining nulls (no explicit policy — filling with 0):\n")
    for feat, cnt in remaining_nulls.items():
        df_imp[feat] = df_imp[feat].fillna(0)
        print(f"    {feat}: {cnt:,} → 0")

print(f"\n  Total nulls after imputation: {df_imp[FEATURES].isna().sum().sum():,}")


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — RANK-TRANSFORM (PERCENTILE NORMALIZATION)
# ══════════════════════════════════════════════════════════════════════════════
section("PHASE 5 — RANK-TRANSFORM (PERCENTILE NORMALIZATION)")

print("""
  Rationale:
  - Metric is rank-based (top-20% overlap) → scale is irrelevant, rank is everything.
  - Rank-transform is outlier-resistant (f7 max ~147K can't distort the result).
  - Preserves relative order, not absolute magnitude.
  - All features normalized to [0, 1] percentile scale before weighting.
""")

df_ranked = df_imp.copy()
for feat in FEATURES:
    df_ranked[f"{feat}_rank"] = (
        df_imp[feat].rank(method="average", na_option="keep") / len(df_imp)
    )

rank_cols = [f"{f}_rank" for f in FEATURES]
rank_summary = df_ranked[rank_cols].describe().T[["min", "25%", "50%", "75%", "max"]]
rank_summary.index = FEATURES
print("  Rank-transformed feature summary (should all be ~0 to 1):\n")
with pd.option_context("display.float_format", "{:.4f}".format):
    print(rank_summary.to_string())

# distribution check post-rank (should be uniform)
print(f"\n{SEP2}\n  Saving post-rank distribution plots …")
fig, axes = plt.subplots(2, 4, figsize=(18, 8))
for ax, feat in zip(axes.flat, ["f5","f1","f7","f11","f21","f4","f13","f14"]):
    data = df_ranked[f"{feat}_rank"].dropna()
    ax.hist(data, bins=40, color="#27ae60", edgecolor="none", alpha=0.8)
    ax.set_title(f"{feat}_rank", fontsize=9)
    ax.set_xlim(0, 1)
plt.suptitle("Post Rank-Transform Distributions (expect near-uniform)", fontsize=10)
plt.tight_layout()
fig.savefig(f"{OUT_DIR}/p5_ranked_distributions.png", dpi=150)
plt.close()
print(f"  Saved → {OUT_DIR}/p5_ranked_distributions.png")


# ══════════════════════════════════════════════════════════════════════════════
# SAVE OUTPUTS
# ══════════════════════════════════════════════════════════════════════════════
section("SAVING OUTPUTS")

# imputed dataset (pre-rank, for reference)
imp_path    = f"{OUT_DIR}/data_imputed.csv"
ranked_path = f"{OUT_DIR}/data_ranked.csv"

df_imp.to_csv(imp_path, index=False)
df_ranked.to_csv(ranked_path, index=False)

print(f"\n  data_imputed.csv   → {imp_path}")
print(f"  data_ranked.csv    → {ranked_path}")
print(f"\n  Plots saved to:    ./{OUT_DIR}/")
print(f"\n  Columns in ranked output: {len(df_ranked.columns)}")
print(f"  (original {len(df.columns)} + {len(rank_cols)} rank columns)")


# ══════════════════════════════════════════════════════════════════════════════
# PHASE SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
section("EDA SUMMARY — KEY FINDINGS")

print("""
  Phase 1 — Missingness:
    • f4 & f21 null together for ~51.4% — no recorded rewards activity (dormant/masked segment; NOT "not enrolled" — all Premier CMs earn 1x rewards by default)
    • f6–f10 null together for ~23.1% — no premium category spend (zero-fill)
    • f13–f16 null together for ~2.7%  — no perk utilization (zero-fill)
    • f17/f18 null for 58–62%          — no lend product access (zero-fill)
    • f5, f11 low-null (<2%)           — median-imputed

  Phase 2 — Scale:
    • f7 max ~147K vs f11 max 0.33 → raw summation is meaningless
    • f7 has negative values (refunds) → kept, no floor
    • f16 capped at 64.40 → near-binary in top quartile

  Phase 3 — Cross-feature:
    • f5 vs sum(f6:f10) correlation ~0.09 → independently masked, do not reconcile
    • f17 >= f18 only ~63% of the time → no difference feature allowed

  Phase 4 — Imputation:
    • Locked policy applied (see table in eda_grilling_session_context.md)

  Phase 5 — Normalization:
    • All features rank-transformed to [0,1] percentiles
    • Ready for weighted P&L equation construction

  Next step: build the profitability equation using ranked features.
""")
