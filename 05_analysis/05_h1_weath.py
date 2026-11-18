
"""
05_h1_wealth.py - Hypothesis H1 of the roadmap (Phase 4): wealth and attractiveness.
 
H1: richer regions (higher GDP per capita) receive more students than they send.
 
Test (roadmap, section 7.3): regression with permutations, run separately for each period.
  dependent variable    net balance = (in - out) / (in + out) on the weighted network
                        (+1 = only receives, -1 = only sends). It does not depend on the size of
                        the region, so a large region does not look attractive just because it is large.
  explanatory variable  log GDP per capita of the period (euro, current prices). With the log,
                        inflation only shifts the intercept, so the slopes of the three periods can
                        be compared even though GDP is not deflated (decision 11).
  p-values              permutations of the net balance across regions. The regions of a network
                        are not independent observations, so the usual OLS p-value is not valid.
 
Three models per period:
  M1_all              the regions with GDP (UK, IS, LI have none: decision 12)
  M2_no_turkey        without the Turkish regions, which are all strong senders (net balance
                      about -0.9): checks that the result is not driven by a single country
  M3_within_country   country fixed effects: GDP and net balance are measured as differences from
                      the country mean, and the permutations shuffle regions only inside their own
                      country. Question: within the same country, do richer regions attract more?
                      Countries with a single region add nothing to this model.
Plus a descriptive table: net balance by GDP tercile (the same terciles as measure 11).
 
Expectation (written before running the test): uncertain. Rich regions should gain students
(Rusu et al. 2025 find that the GDP of the destination matters), but Spain is the main attractor
without being among the richest countries (Batagelj 2025), and only 52-55% of students move to a
richer region (measure 11). Turkey (poor, strong sender) could produce a positive slope on its
own: M2 checks this.
 
Run from the project root directory (after src/01-04):
    python 05_analysis/05_h1_wealth.py
 
Outputs (05_analysis/tables/ and 05_analysis/reports/):
  h1_tests.csv      one row per period and model: slope, effect of doubling GDP, r, p-values
  h1_terciles.csv   net balance by GDP tercile and period
  h1_data.csv       the region-level data used in the tests (for checks and figures)
  h1_report.txt     everything above, as text
"""
 
import numpy as np
import pandas as pd
from scipy.stats import rankdata
 
import common
from common import PERIODS, SEED
 
N_PERMUTATIONS = 5000
SIGNIFICANCE = 0.05
COUNTRY_EXCLUDED_IN_M2 = "TR"
TOP_RESIDUALS = 8  # regions listed in the report as "far above / far below what their GDP predicts"
MODELS = {
    "M1_all": "all regions with GDP",
    "M2_no_turkey": "without the Turkish regions",
    "M3_within_country": "country fixed effects, permutations within each country",
}
 
log = common.Report("h1_report")
 
 
# -----------------------------------------------------------------------------
# DATA
# -----------------------------------------------------------------------------
def region_data(period):
    """One row per region of the period: in/out strength, net balance, GDP per capita and GDP
    tercile. Returns the regions used in the tests and, separately, the regions dropped because
    they have no GDP or no students at all (so the report can list them)."""
    G = common.load_period(period)  # weighted, directed, all 319 regions
    in_strength = dict(G.in_degree(weight="weight"))
    out_strength = dict(G.out_degree(weight="weight"))
 
    rows = []
    for r in G.nodes():
        s_in, s_out = in_strength[r], out_strength[r]
        rows.append(
            {
                "period": period,
                "region": r,
                "name": G.nodes[r].get("name", ""),
                "country": r[:2],
                "in_strength": s_in,
                "out_strength": s_out,
                # same formula as 01_centrality.py (column net_balance of centrality_<period>.csv)
                "net_balance": (s_in - s_out) / (s_in + s_out) if s_in + s_out else np.nan,
                "gdp": G.nodes[r].get(f"gdp_{period}", np.nan),
            }
        )
    df = pd.DataFrame(rows)
 
    # GDP terciles over all regions with GDP, exactly as in 03_homophily.py (measure 11)
    has_gdp = df.gdp.notna()
    df.loc[has_gdp, "gdp_tercile"] = pd.qcut(df.gdp[has_gdp], 3, labels=["1 low", "2 middle", "3 high"]).astype(str)
 
    no_gdp = df[~has_gdp]
    no_students = df[has_gdp & df.net_balance.isna()]
    used = df[has_gdp & df.net_balance.notna()].reset_index(drop=True)
    used["log_gdp"] = np.log(used.gdp)
    return used, no_gdp, no_students
 
 
# -----------------------------------------------------------------------------
# PERMUTATION TEST
# -----------------------------------------------------------------------------
def permutations(n, rng, groups=None):
    """N_PERMUTATIONS random orderings of n regions, one per row of the returned matrix.
    With groups (country codes), every region is shuffled only among regions of its own group."""
    if groups is None:
        groups = np.zeros(n, dtype=int)  # a single group = free permutation of all regions
    order = np.tile(np.arange(n), (N_PERMUTATIONS, 1))
    for g in np.unique(groups):
        members = np.flatnonzero(groups == g)
        order[:, members] = rng.permuted(order[:, members], axis=1)
    return order
 
 
def slope_and_r(x, Y):
    """OLS slope and Pearson r of y on x. Y is either one vector or a matrix with one (permuted)
    y per row: in that case all the slopes are computed at once."""
    xc = x - x.mean()
    Yc = Y - Y.mean(axis=-1, keepdims=True)
    slope = Yc @ xc / (xc @ xc)
    r = Yc @ xc / np.sqrt((xc @ xc) * (Yc**2).sum(axis=-1))
    return slope, r
 
 
def p_value(observed, permuted):
    """Two-sided permutation p-value: share of permutations at least as extreme as the observed
    value (+1 in numerator and denominator, so p is never exactly 0)."""
    return (np.sum(np.abs(permuted) >= abs(observed)) + 1) / (len(permuted) + 1)
 
 
def run_model(df, model, rng):
    """Fits one model on the regions of one period and tests the slope with permutations."""
    if model == "M2_no_turkey":
        df = df[df.country != COUNTRY_EXCLUDED_IN_M2]
 
    x = df.log_gdp.to_numpy()
    y = df.net_balance.to_numpy()
    groups = None
    if model == "M3_within_country":
        # Fixed effects = differences from the country mean. Shuffling y inside a country does
        # not change the country mean, so permuting the demeaned y within country is exact.
        groups = df.country.to_numpy()
        x = x - df.groupby("country").log_gdp.transform("mean").to_numpy()
        y = y - df.groupby("country").net_balance.transform("mean").to_numpy()
 
    order = permutations(len(y), rng, groups)
    slope, r = slope_and_r(x, y)
    permuted_slopes, _ = slope_and_r(x, y[order])
 
    sizes = df.country.value_counts()
    result = {
        "model": model,
        "regions": len(df),
        "countries": len(sizes) if groups is None else int((sizes > 1).sum()),
        "slope": slope,
        "effect_doubling_gdp": slope * np.log(2),  # change in net balance when GDP doubles
        "r": r,
        "r2": r**2,
        # with x fixed, slope and r give the same permutation p-value
        "p_permutation": p_value(slope, permuted_slopes),
        "spearman_rho": np.nan,
        "p_spearman": np.nan,
    }
    if groups is None:
        # Spearman rho = Pearson r on ranks: checks that the result does not depend on a few
        # extreme regions or on a linear form. Same permutations as the slope.
        rank_x, rank_y = rankdata(x), rankdata(y)
        _, rho = slope_and_r(rank_x, rank_y)
        _, permuted_rho = slope_and_r(rank_x, rank_y[order])
        result["spearman_rho"] = rho
        result["p_spearman"] = p_value(rho, permuted_rho)
    return result
 
 
# -----------------------------------------------------------------------------
# DESCRIPTIVE TABLES
# -----------------------------------------------------------------------------
def tercile_table(df):
    """Net balance by GDP tercile: an easy-to-read version of the test for the report."""
    table = (
        df.groupby("gdp_tercile")
        .agg(
            regions=("region", "size"),
            gdp_min=("gdp", "min"),
            gdp_max=("gdp", "max"),
            mean_net_balance=("net_balance", "mean"),
            median_net_balance=("net_balance", "median"),
            share_net_receivers=("net_balance", lambda v: (v > 0).mean()),
            turkish_regions=("country", lambda c: int((c == "TR").sum())),
        )
        .reset_index()
    )
    table.insert(0, "period", df.period.iloc[0])
    return table
 
 
def add_m1_residuals(df):
    """Residual of the M1 line: positive = the region attracts more than its GDP predicts."""
    x, y = df.log_gdp.to_numpy(), df.net_balance.to_numpy()
    slope, _ = slope_and_r(x, y)
    intercept = y.mean() - slope * x.mean()
    return df.assign(residual_m1=y - (intercept + slope * x))
 
 
# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
def main():
    common.output_dirs()
    rng = np.random.default_rng(SEED)
    test_rows, tercile_tables, data_frames, excluded_lines = [], [], [], []
 
    for period in PERIODS:
        print(f"{period} ...")
        df, no_gdp, no_students = region_data(period)
        excluded_lines.append(
            f"{period}: {len(df)} regions used; without GDP {len(no_gdp)} "
            f"({', '.join(f'{c} {n}' for c, n in no_gdp.country.value_counts().items())}); "
            f"without any student {len(no_students)}"
            + (f" ({', '.join(no_students.region)})" if len(no_students) else "")
        )
        for model in MODELS:
            test_rows.append({"period": period, **run_model(df, model, rng)})
        tercile_tables.append(tercile_table(df))
        data_frames.append(add_m1_residuals(df))
 
    tests = pd.DataFrame(test_rows)
    tests["supports_h1"] = (tests.slope > 0) & (tests.p_permutation < SIGNIFICANCE)
    tests = tests.round(4)
    tests.to_csv(common.TABLES_DIR / "h1_tests.csv", index=False)
    terciles = pd.concat(tercile_tables).round(3)
    terciles.to_csv(common.TABLES_DIR / "h1_terciles.csv", index=False)
    data = pd.concat(data_frames)[
        ["period", "region", "name", "country", "gdp", "log_gdp", "gdp_tercile",
         "in_strength", "out_strength", "net_balance", "residual_m1"]
    ].round(4)
    data.to_csv(common.TABLES_DIR / "h1_data.csv", index=False)
 
    # --- Report ------------------------------------------------------------------
    log.title("H1: RICHER REGIONS RECEIVE MORE STUDENTS THAN THEY SEND")
    log("Dependent variable: net balance (in - out) / (in + out), weighted network.")
    log("Explanatory variable: log GDP per capita of the period.")
    log(f"p-values: {N_PERMUTATIONS} permutations of the net balance across regions (two-sided).")
    log("Models:")
    for model, description in MODELS.items():
        log(f"  {model:<18} {description}")
    log("\nRegions used:")
    for line in excluded_lines:
        log(f"  {line}")
 
    log.title("TESTS")
    log("slope: change in net balance for +1 in log GDP; effect_doubling_gdp = slope x ln 2.")
    log(f"supports_h1: slope > 0 and p_permutation < {SIGNIFICANCE}. In M3 'countries' counts only "
        "countries with at least 2 regions (the others add nothing).")
    log(tests.to_string(index=False))
 
    log.title("NET BALANCE BY GDP TERCILE")
    log("share_net_receivers: share of regions with net balance > 0.")
    log(terciles.to_string(index=False))
 
    log.title(f"REGIONS FURTHEST FROM THE M1 LINE ({TOP_RESIDUALS} per side)")
    log("Positive residual = attracts more than its GDP predicts; negative = attracts less.")
    columns = ["region", "name", "gdp", "net_balance", "residual_m1"]
    for period, df in zip(PERIODS, data_frames):
        df = df.sort_values("residual_m1")
        log(f"\n{period} - above the line:")
        log(df.tail(TOP_RESIDUALS).iloc[::-1][columns].round(3).to_string(index=False))
        log(f"{period} - below the line:")
        log(df.head(TOP_RESIDUALS)[columns].round(3).to_string(index=False))
    log.save()
 
 
if __name__ == "__main__":
    main()
 