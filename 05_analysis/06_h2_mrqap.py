"""
06_h2_mrqap.py - Hypothesis H2 of the roadmap (Phase 4): distance, language and flows.

H2: the flow between two regions decreases with geographic distance and increases when the two
regions share a language.

Test (roadmap, section 7.3): MRQAP, a regression on matrices (one cell = one ordered pair of
regions, origin -> destination) with p-values from permutations of rows and columns, because
pairs that share a region are not independent observations. One test per period.

Sample (decisions 14 and 15):
  - the 276 regions with GDP, the same in every model and period (UK, IS, LI have no GDP);
  - only cross-country pairs: same-country pairs have zero flow by construction (decision 4),
    not because of distance, so they are left out (71,370 ordered pairs).

Dependent variable, two versions:
  weighted      log(1 + students per year). About 60% of the pairs have no student: the log keeps
                the zeros and reduces the weight of the few very large flows.
  binary_b5     1 if the pair is an edge of the binary network (>= 5 students/year), else 0
                (linear probability model): robustness check that does not depend on the size
                of the flows.

Explanatory variables (matrices):
  log_distance                  log of the great-circle distance between the regions (km)
  same_language                 1 = the most spoken language is the same in the two regions
  same_family                   1 = the most spoken languages of the two regions belong to the same
                                family (Romance, Germanic, Slavic...). Pairs with the same language
                                also have the same family, so same_family measures "related but
                                different" languages.
  gdp_difference                |log GDP per capita origin - log GDP per capita destination|
                                (0 = equally rich; 0.69 = one region twice as rich as the other)
  log_out_strength_origin       log(1 + students/year sent by the origin to all regions)
  log_in_strength_destination   log(1 + students/year received by the destination from all regions)

Language coding (decision 16, changed in Phase 4: decision 22). Every region gets ONE language,
the most spoken one: the first language of its country in languages.csv (for the countries with
several official languages - BE, CY, FI, IE, LU, MT - the first one listed is the most spoken),
except the cases in LANGUAGE_EXCEPTIONS: Montenegro, where Serbian is more spoken than Montenegrin
(2023 census), and four regions where most people speak another language than the rest of their
country (Brussels and Wallonia: French; Aland: Swedish; Bolzano/Bozen: German). The coding of
Phase 2 ("the two countries share a national official language", region_pairs.csv) made pairs
such as Belgium-Germany or Finland-Sweden "same language" because of small minorities; it is kept
as a robustness check (h2_language_check.csv).

Three models:
  M1_roadmap         distance, language, language family, GDP difference (as in the roadmap)
  M2_size            M1 + the size of origin and destination (students sent / received). Without
                     it, the other variables could partly capture the fact that large university
                     regions exchange more students with everyone. M2 asks: for regions of a given
                     size, where do students go?
  M3_fixed_effects   M1 + one effect for every origin and one for every destination (the standard
                     solution of gravity models). The effects absorb EVERYTHING that characterises
                     a region, measured or not: size, prestige, climate, cost of living, number of
                     universities. What is left is estimated by comparing, for the same origin,
                     destinations nearer or farther away, each with its own general attractiveness.
                     The size variables of M2 are not used: the effects already contain them.
                     M3 was added after M1 and M2, as a robustness check for the main objection to
                     the distance result (attractive destinations, e.g. in Southern Europe, are
                     far from most origins).

Permutations: Double Semi-Partialling (DSP, Dekker, Krackhardt and Snijders 2007), the default of
netlm in the R package sna. For each variable: (1) regress it on the other variables; (2) permute
rows and columns of the residual matrix together (= relabel the regions at random); (3) re-estimate
the model with the permuted residual instead of the variable. The p-value is the share of
permutations with a t-value at least as extreme as the observed one. The residuals are computed
on all pairs (distance, language and GDP exist for same-country pairs too) and the model is
always estimated on the cross-country pairs only.
The intercept (M1, M2) and the region effects (M3) are partialled out of every variable before
the regression (Frisch-Waugh-Lovell theorem): this gives exactly the coefficients of the full
regression, and in M3 it avoids estimating 551 dummy coefficients in every permutation.

Expectation (written before running M1 and M2): negative effect of distance and positive effect
of a shared language. Either result agrees with one of the two papers: Rusu et al. (2025,
countries) find that distance matters and that its effect weakens over time; Gadar et al. (2022,
institutions) find that it does not. GDP difference: negative, because measure 11 shows that
regions exchange more with regions of similar wealth.

Run from the project root directory (after src/01-04):
    python 05_analysis/06_h2_mrqap.py          (~2-3 minutes)

Outputs (05_analysis/tables/ and 05_analysis/reports/):
  h2_coefficients.csv     one row per period, dependent variable, model and explanatory variable
  h2_models.csv           one row per period, dependent variable and model: sample size, R2
  h2_language_check.csv   the three models (weighted network) with the Phase 2 language coding
  h2_report.txt           everything above, as text, with the language of every region that
                          differs from the default and the correlations between the variables
"""

import networkx as nx
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.linalg import cho_factor, cho_solve

import common
from common import PERIODS, PRIMARY_THRESHOLD, SEED

N_PERMUTATIONS = 1000   # as netlm; minimum p-value = 1 / 1001
CHUNK = 50              # permutations computed together (limits memory use)
SIGNIFICANCE = 0.05
BINARY = f"binary_b{PRIMARY_THRESHOLD}"

MODELS = {
    "M1_roadmap": ["log_distance", "same_language", "same_family", "gdp_difference"],
    "M2_size": ["log_distance", "same_language", "same_family", "gdp_difference",
                "log_out_strength_origin", "log_in_strength_destination"],
    "M3_fixed_effects": ["log_distance", "same_language", "same_family", "gdp_difference"],
}
FIXED_EFFECTS_MODELS = {"M3_fixed_effects"}  # models with one effect per origin and per destination
EXPECTED_SIGN = {
    "log_distance": -1, "same_language": +1, "same_family": +1, "gdp_difference": -1,
    "log_out_strength_origin": +1, "log_in_strength_destination": +1,
}
# Step used to express each coefficient as an effect that can be written in the report
EFFECT_STEP = {
    "log_distance": (np.log(2), "distance x2"),
    "same_language": (1.0, "0 -> 1"),
    "same_family": (1.0, "0 -> 1"),
    "gdp_difference": (np.log(2), "GDP ratio x2"),
    "log_out_strength_origin": (np.log(2), "size x2"),
    "log_in_strength_destination": (np.log(2), "size x2"),
}
EFFECT_UNIT = {
    "weighted": "% change in (1 + students/year)",
    BINARY: "percentage points in the probability of an edge",
}
# Most spoken language (and its family) where it is NOT the first language of the country in
# languages.csv. Key = start of the region code: a country (2 letters), a NUTS 1 area (3) or a
# region (4); the longest matching key wins.
LANGUAGE_EXCEPTIONS = {
    "ME": ("Serbian", "Slavic"),       # 2023 census: Serbian 43.2%, Montenegrin 34.5% (mother tongue)
    "BE1": ("French", "Romance"),      # Brussels-Capital Region
    "BE3": ("French", "Romance"),      # Wallonia (the small German-speaking community is in BE33)
    "FI20": ("Swedish", "Germanic"),   # Aland
    "ITH1": ("German", "Germanic"),    # Bolzano/Bozen (South Tyrol)
}
LANGUAGE_CHECK = "official_languages"  # name of the Phase 2 coding in h2_language_check.csv

log = common.Report("h2_report")


# -----------------------------------------------------------------------------
# DATA
# -----------------------------------------------------------------------------
def sample_regions():
    """The regions with GDP in every period (decision 14) and their GDP per capita."""
    regions = common.load_regions()
    gdp_columns = [f"gdp_{p}" for p in PERIODS]
    sample = regions.dropna(subset=gdp_columns)
    return sample.region.tolist(), sample.set_index("region")[gdp_columns]


def dyadic_matrices(regions):
    """n x n matrices of distance, same country, and same language and same family with the
    Phase 2 coding (a shared national official language), built from the list of unordered pairs
    in region_pairs.csv. The diagonal (a region with itself) stays NaN."""
    index = {r: i for i, r in enumerate(regions)}
    n = len(regions)
    pairs = pd.read_csv(common.networks.METADATA_DIR / "region_pairs.csv")
    pairs = pairs[pairs.region_a.isin(index) & pairs.region_b.isin(index)]
    a = pairs.region_a.map(index).to_numpy()
    b = pairs.region_b.map(index).to_numpy()
    matrices = {}
    for column in ("distance_km", "same_country", "same_language", "same_family"):
        M = np.full((n, n), np.nan)
        M[a, b] = M[b, a] = pairs[column].to_numpy()  # every pair is symmetric
        matrices[column] = M
    return matrices


def main_languages(regions):
    """The most spoken language of every region and its family: the first language (and first
    family) of the country in languages.csv, unless LANGUAGE_EXCEPTIONS says otherwise."""
    countries = pd.read_csv(common.networks.METADATA_DIR / "languages.csv").set_index("country")
    rows = []
    for r in regions:
        language = countries.loc[r[:2], "languages"].split(";")[0]
        family = countries.loc[r[:2], "families"].split(";")[0]
        for key in sorted(LANGUAGE_EXCEPTIONS, key=len):  # shorter keys first, longer ones override
            if r.startswith(key):
                language, family = LANGUAGE_EXCEPTIONS[key]
        rows.append({"region": r, "language": language, "family": family,
                     "exception": any(r.startswith(key) for key in LANGUAGE_EXCEPTIONS)})
    return pd.DataFrame(rows)


def language_matrices(languages):
    """n x n matrices of same language and same family from the most spoken language of every
    region. The diagonal stays NaN, as in dyadic_matrices()."""
    matrices = {}
    for name, column in (("same_language", "language"), ("same_family", "family")):
        values = languages[column].to_numpy()
        M = (values[:, None] == values[None, :]).astype(float)
        np.fill_diagonal(M, np.nan)
        matrices[name] = M
    return matrices


def flow_matrices(period, regions):
    """Dependent variables of a period (both versions) and the size of every region.
    The size counts the students sent to / received from ALL regions, UK included."""
    G = common.load_period(period)
    B = common.load_binary(period, PRIMARY_THRESHOLD)
    students = nx.to_numpy_array(G, nodelist=regions, weight="weight")
    edges = nx.to_numpy_array(B, nodelist=regions, weight=None)
    out_strength = np.array([G.out_degree(r, weight="weight") for r in regions])
    in_strength = np.array([G.in_degree(r, weight="weight") for r in regions])
    return {"weighted": np.log1p(students), BINARY: edges}, out_strength, in_strength


def explanatory_matrices(dyads, language, log_gdp, out_strength, in_strength):
    """All explanatory variables of a period as n x n matrices (row = origin, column = destination).
    `language` holds the same_language and same_family matrices of the coding to use."""
    n = len(log_gdp)
    return {
        "log_distance": np.log(dyads["distance_km"]),
        "same_language": language["same_language"],
        "same_family": language["same_family"],
        "gdp_difference": np.abs(log_gdp[:, None] - log_gdp[None, :]),
        # the same value along a row (origin) or along a column (destination)
        "log_out_strength_origin": np.repeat(np.log1p(out_strength)[:, None], n, axis=1),
        "log_in_strength_destination": np.repeat(np.log1p(in_strength)[None, :], n, axis=0),
    }


# -----------------------------------------------------------------------------
# TERMS PARTIALLED OUT OF EVERY VARIABLE: INTERCEPT OR REGION EFFECTS
# -----------------------------------------------------------------------------
class Absorbed:
    """The part of the model that is removed from every variable before the regression
    (Frisch-Waugh-Lovell): only the intercept (M1, M2), or one effect per origin and one per
    destination (M3). Removing it and regressing what is left gives exactly the coefficients of
    the full regression."""

    def __init__(self, cells, n, fixed_effects):
        rows, cols = cells
        m = len(rows)
        self.n, self.fixed_effects = n, fixed_effects
        if fixed_effects:
            # One 0/1 column per origin (0..n-1) and one per destination (n..2n-1). The
            # destination column of the first region is dropped: all origin columns together
            # already add up to a constant, so keeping it would count the constant twice.
            pair = np.concatenate([np.arange(m), np.arange(m)])
            column = np.concatenate([rows, n + cols])
            dummies = sparse.csc_matrix((np.ones(2 * m), (pair, column)), shape=(m, 2 * n))
            self.design = dummies[:, np.r_[0:n, n + 1:2 * n]].tocsr()
        else:
            self.design = sparse.csr_matrix(np.ones((m, 1)))
        self.parameters = self.design.shape[1]  # 1, or 2n - 1 = 551 region effects
        self.factor = cho_factor((self.design.T @ self.design).toarray())

    def coefficients(self, V):
        """Coefficients of the absorbed terms for V (pairs,) or (pairs, k)."""
        return cho_solve(self.factor, self.design.T @ V)

    def remove(self, V):
        """V minus its absorbed part: V (pairs,) or (pairs, k)."""
        return V - self.design @ self.coefficients(V)

    def on_all_pairs(self, coefficients):
        """The absorbed part with the given coefficients, as an n x n matrix covering every pair
        (also the same-country pairs left out of the sample)."""
        if not self.fixed_effects:
            return np.full((self.n, self.n), coefficients[0])
        origin = coefficients[:self.n]
        destination = np.concatenate([[0.0], coefficients[self.n:]])  # first destination dropped
        return origin[:, None] + destination[None, :]


# -----------------------------------------------------------------------------
# MRQAP WITH DOUBLE SEMI-PARTIALLING
# -----------------------------------------------------------------------------
def ols(y, X, absorbed):
    """OLS of y on X, both already cleaned of the absorbed terms: coefficients and t-values.
    The degrees of freedom also count the absorbed parameters."""
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    residual = y - X @ beta
    df = len(y) - absorbed - X.shape[1]
    t = beta / np.sqrt(residual @ residual / df * np.diag(XtX_inv))
    return beta, t, residual


def t_of_extra_column(A, y, Z, absorbed):
    """t-value of the last coefficient in the regression of y on [A, z], for every row z of Z
    (one permuted residual per row); A, y and Z are already cleaned of the absorbed terms.
    It uses the normal equations, so a whole chunk of regressions on ~70,000 pairs is solved at
    once."""
    m, q = A.shape[0], A.shape[1] + 1
    b = len(Z)
    AtZ = Z @ A
    DtD = np.empty((b, q, q))
    DtD[:, :-1, :-1] = A.T @ A
    DtD[:, :-1, -1] = AtZ
    DtD[:, -1, :-1] = AtZ
    DtD[:, -1, -1] = np.einsum("ij,ij->i", Z, Z)
    Dty = np.concatenate([np.broadcast_to(A.T @ y, (b, q - 1)), (Z @ y)[:, None]], axis=1)
    inverse = np.linalg.inv(DtD)
    beta = np.einsum("bij,bj->bi", inverse, Dty)
    rss = y @ y - np.einsum("bi,bi->b", beta, Dty)
    return beta[:, -1] / np.sqrt(rss / (m - absorbed - q) * inverse[:, -1, -1])


def p_value(observed, permuted):
    """Two-sided permutation p-value (+1 in numerator and denominator, so p is never 0)."""
    return (np.sum(np.abs(permuted) >= abs(observed)) + 1) / (len(permuted) + 1)


def mrqap_dsp(y_matrix, x_matrices, cells, rng, fixed_effects=False):
    """MRQAP regression of y_matrix on x_matrices over the given cells (the cross-country pairs),
    with DSP permutation p-values. fixed_effects=True adds one effect per origin and per
    destination (M3). Returns a dict with coefficients, t-values, p-values and R2."""
    rows, cols = cells
    n = y_matrix.shape[0]
    absorbed = Absorbed(cells, n, fixed_effects)
    y_raw = y_matrix[rows, cols]
    X_raw = np.column_stack([x[rows, cols] for x in x_matrices])
    y, X = absorbed.remove(y_raw), absorbed.remove(X_raw)   # cleaned of intercept / region effects
    beta, t, residual = ols(y, X, absorbed.parameters)

    p_values = []
    for k in range(len(x_matrices)):
        # (1) residual of variable k after the other variables (and the absorbed terms),
        # estimated on the sample cells...
        others = np.delete(X, k, axis=1)
        gamma, _, _ = ols(X[:, k], others, absorbed.parameters)
        other_matrices = [x for j, x in enumerate(x_matrices) if j != k]
        absorbed_part = absorbed.coefficients(X_raw[:, k] - np.delete(X_raw, k, axis=1) @ gamma)
        # ...and computed on ALL pairs, so that relabelled regions always find a value
        fitted = absorbed.on_all_pairs(absorbed_part) + sum(g * x for g, x in zip(gamma, other_matrices))
        residual_k = (x_matrices[k] - fitted).ravel()

        # (2) + (3) relabel the regions at random and re-estimate, CHUNK permutations at a time.
        # A permutation maps the diagonal onto the diagonal, so the NaN diagonal is never used.
        permuted_t = []
        for start in range(0, N_PERMUTATIONS, CHUNK):
            size = min(CHUNK, N_PERMUTATIONS - start)
            relabel = rng.permuted(np.tile(np.arange(n), (size, 1)), axis=1)
            Z = residual_k[relabel[:, rows] * n + relabel[:, cols]]
            Z = absorbed.remove(Z.T).T  # the permuted residual must also be cleaned
            permuted_t.append(t_of_extra_column(others, y, Z, absorbed.parameters))
        p_values.append(p_value(t[k], np.concatenate(permuted_t)))

    # R2 of the full model (in M3 it includes the 551 region effects)
    tss = ((y_raw - y_raw.mean()) ** 2).sum()
    r2 = 1 - residual @ residual / tss
    n_parameters = absorbed.parameters + X.shape[1]
    return {
        "coefficient": beta,
        "std_coefficient": beta * X_raw.std(axis=0) / y_raw.std(),  # comparable across variables
        "t": t,
        "p_dsp": np.array(p_values),
        "r2": r2,
        "adj_r2": 1 - (1 - r2) * (len(y) - 1) / (len(y) - n_parameters),
        "cells": len(y),
        "mean_y": y_raw.mean(),
        "share_nonzero": (y_raw > 0).mean(),
    }


# -----------------------------------------------------------------------------
# TABLES
# -----------------------------------------------------------------------------
def coefficient_rows(period, y_version, model, variables, result):
    """One row per explanatory variable, with the effect expressed for the report."""
    rows = []
    for k, variable in enumerate(variables):
        beta = result["coefficient"][k]
        step, step_label = EFFECT_STEP[variable]
        effect = 100 * (np.exp(beta * step) - 1) if y_version == "weighted" else 100 * beta * step
        rows.append(
            {
                "period": period,
                "y": y_version,
                "model": model,
                "variable": variable,
                "expected_sign": "+" if EXPECTED_SIGN[variable] > 0 else "-",
                "coefficient": beta,
                "std_coefficient": result["std_coefficient"][k],
                "t": result["t"][k],
                "p_dsp": result["p_dsp"][k],
                "effect": effect,
                "effect_of": step_label,
                "effect_unit": EFFECT_UNIT[y_version],
                "as_expected": bool(np.sign(beta) == EXPECTED_SIGN[variable]
                                    and result["p_dsp"][k] < SIGNIFICANCE),
            }
        )
    return rows


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
def main():
    common.output_dirs()
    rng = np.random.default_rng(SEED)

    regions, gdp = sample_regions()
    dyads = dyadic_matrices(regions)
    cells = np.nonzero(dyads["same_country"] == 0)  # cross-country pairs (the NaN diagonal is excluded)
    languages = main_languages(regions)
    coding = {
        "main": language_matrices(languages),  # most spoken language (used in all the models)
        LANGUAGE_CHECK: {k: dyads[k] for k in ("same_language", "same_family")},  # Phase 2 coding
    }

    coefficient_table, model_table, check_table, correlations = [], [], [], {}
    for period in PERIODS:
        log_gdp = np.log(gdp.loc[regions, f"gdp_{period}"].to_numpy())
        dependent, out_strength, in_strength = flow_matrices(period, regions)
        X_all = explanatory_matrices(dyads, coding["main"], log_gdp, out_strength, in_strength)
        correlations[period] = pd.DataFrame({v: X_all[v][cells] for v in X_all}).corr()

        for y_version, y_matrix in dependent.items():
            for model, variables in MODELS.items():
                print(f"{period} | {y_version} | {model} ...")
                result = mrqap_dsp(y_matrix, [X_all[v] for v in variables], cells, rng,
                                   fixed_effects=model in FIXED_EFFECTS_MODELS)
                coefficient_table += coefficient_rows(period, y_version, model, variables, result)
                model_table.append(
                    {"period": period, "y": y_version, "model": model, "regions": len(regions),
                     **{k: result[k] for k in ("cells", "mean_y", "share_nonzero", "r2", "adj_r2")}}
                )

        # Robustness check: the same three models (weighted network) with the Phase 2 coding
        X_check = explanatory_matrices(dyads, coding[LANGUAGE_CHECK], log_gdp, out_strength, in_strength)
        for model, variables in MODELS.items():
            print(f"{period} | weighted | {model} | {LANGUAGE_CHECK} ...")
            result = mrqap_dsp(dependent["weighted"], [X_check[v] for v in variables], cells, rng,
                               fixed_effects=model in FIXED_EFFECTS_MODELS)
            check_table += coefficient_rows(period, "weighted", model, variables, result)

    coefficients = pd.DataFrame(coefficient_table).round(4)
    coefficients.to_csv(common.TABLES_DIR / "h2_coefficients.csv", index=False)
    models = pd.DataFrame(model_table).round(4)
    models.to_csv(common.TABLES_DIR / "h2_models.csv", index=False)
    check = pd.DataFrame(check_table).round(4)
    check.insert(3, "language_coding", LANGUAGE_CHECK)
    check.to_csv(common.TABLES_DIR / "h2_language_check.csv", index=False)

    # --- Report ------------------------------------------------------------------
    log.title("H2: DISTANCE, LANGUAGE AND FLOWS (MRQAP, DOUBLE SEMI-PARTIALLING)")
    log(f"Sample: {len(regions)} regions with GDP (UK, IS, LI excluded), {len(cells[0]):,} ordered "
        "cross-country pairs (same-country pairs excluded: zero flow by construction).")
    log(f"p-values: {N_PERMUTATIONS} DSP permutations of rows and columns (two-sided, on the t-value).")
    log(f"Dependent variable: weighted = log(1 + students/year); {BINARY} = 1 if >= {PRIMARY_THRESHOLD} "
        "students/year (linear probability model).")
    for model, variables in MODELS.items():
        extra = " + one effect per origin and per destination" if model in FIXED_EFFECTS_MODELS else ""
        log(f"  {model:<17} {', '.join(variables)}{extra}")

    log.title("LANGUAGE CODING: THE MOST SPOKEN LANGUAGE OF EVERY REGION")
    log("Default: the first language of the country in languages.csv. Regions where it differs:")
    log(languages[languages.exception][["region", "language", "family"]].to_string(index=False))
    for name, matrices in coding.items():
        log(f"{name:<19} ordered cross-country pairs with the same language: "
            f"{int(matrices['same_language'][cells].sum()):,}; same family: "
            f"{int(matrices['same_family'][cells].sum()):,}")

    log.title("CORRELATIONS BETWEEN THE EXPLANATORY VARIABLES (cross-country pairs)")
    log("High values (above about 0.7) would make the single coefficients hard to separate.")
    for period in PERIODS:
        log(f"\n{period}")
        log(correlations[period].round(2).to_string())

    log.title("MODELS")
    log("mean_y: mean of the dependent variable (binary: share of pairs that are edges).")
    log("r2 of M3_fixed_effects includes the 551 region effects, so it is not comparable with M1 and M2.")
    log(models.to_string(index=False))

    log.title("COEFFICIENTS")
    log("std_coefficient: coefficient x sd(x) / sd(y), to compare the variables with each other.")
    log("effect: weighted = % change in (1 + students/year); binary = percentage points in the "
        "probability of an edge; for the step in effect_of.")
    log(f"as_expected: sign as expected and p_dsp < {SIGNIFICANCE}.")
    columns = ["period", "model", "variable", "expected_sign", "coefficient", "std_coefficient",
               "t", "p_dsp", "effect", "effect_of", "as_expected"]
    for y_version in ("weighted", BINARY):
        log(f"\nDependent variable: {y_version}")
        log(coefficients[coefficients.y == y_version][columns].to_string(index=False))

    log.title("DISTANCE ACROSS PERIODS (does its effect weaken over time, as in Rusu et al.?)")
    distance = coefficients[coefficients.variable == "log_distance"]
    log(distance.pivot_table(index=["y", "model"], columns="period", values="std_coefficient",
                             sort=False)[list(PERIODS)].to_string())
    log("(standardised coefficients: they are comparable across periods even though the number of "
        "students changes)")

    log.title(f"LANGUAGE CODING CHECK: MOST SPOKEN LANGUAGE vs {LANGUAGE_CHECK.upper()} (weighted)")
    log(f"{LANGUAGE_CHECK}: Phase 2 coding, 1 = the two countries share a national official language.")
    log("effect = % change in (1 + students/year) for 0 -> 1, with the permutation p-value.")
    both = pd.concat([coefficients[coefficients.y == "weighted"].assign(language_coding="main"), check])
    both = both[both.variable.isin(["same_language", "same_family", "log_distance"])]
    both["effect (p)"] = both.apply(lambda r: f"{r.effect:+.1f}% ({r.p_dsp:.3f})", axis=1)
    log(both.pivot_table(index=["variable", "model"], columns=["language_coding", "period"],
                         values="effect (p)", aggfunc="first", sort=False)
            .reindex(columns=list(PERIODS), level=1).to_string())
    log.save()


if __name__ == "__main__":
    main()