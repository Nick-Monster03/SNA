"""
07_h3_change.py - Hypothesis H3 of the roadmap (Phase 4): Covid and Brexit.

H3: with Covid the network becomes sparser, more concentrated on a few regions and less
reciprocal; after Brexit the UK regions lose centrality.

H3 is mainly a descriptive comparison between networks (roadmap, section 7.3), and the report must
say so clearly: the only formal test is the QAP correlation between the period matrices.
The script puts together four pieces of evidence:

  1. Claims table      the Phase 3 measures (01_centrality.py, 02_structure.py) across the three
                       periods, each with the direction H3 expects. Covid claims compare
                       pre_covid -> covid; UK claims compare pre_covid -> post_covid (Brexit).
                       recovered_share = (post - covid) / (pre - covid): share of the Covid change
                       undone in 2022-23 (1 = full recovery, 0 = none, < 0 = moved further away).
  2. QAP correlation   how similar the period matrices are (who sends students to whom), with
                       permutation p-values, plus the share of edges kept and new between periods.
  3. Yearly benchmark  the same similarity between consecutive years 2016-2023, and the key
                       Phase 3 measures (density, reciprocity, Gini, top 10% share, k_max) on every
                       yearly network: how much the network changes in a normal year (2016-2019),
                       and whether the 2019 -> 2020 change falls outside that range. With only three
                       normal year-to-year changes this is a range, not a distribution: it supports
                       "far outside the normal variation", not a p-value.
  4. United Kingdom    year by year 2016-2023 on the yearly networks (decision 10: the 2022-23
                       average hides the collapse of 2023), and a comparison with every other
                       country between 2019 and 2023, the last normal years before and after Covid
                       (2023 is beyond the validation of the dataset: 01_organization/decisions.txt, SOURCE).

QAP correlation (piece 2): Pearson correlation between two n x n matrices over the cross-country
pairs (same-country pairs are zero by construction, decision 4), on log(1 + students) for the
weighted networks and on 0/1 for the binary ones (>= 5 students/year). All 319 regions are used:
the UK is part of H3. Two permutation schemes, N_PERMUTATIONS each:
  p_qap                     classic QAP: the regions of the second matrix are relabelled at random
  null_mean_within_country  regions are relabelled only among regions of the SAME country, so
                            same-country pairs stay same-country pairs. This is the correlation
                            expected if only the countries, and not the single regions, kept
                            their ties: the gap between r and this value is the part of the
                            stability that belongs to the regions themselves.

Expectation (roadmap; written before running the QAP): a more fragile network in 2020-21 and a
recovery in 2022-23; open question: does the recovery rebuild the same ties? QAP: high correlation
between periods (Phase 3 rankings are very stable), lowest for the pairs involving Covid.
UK: the fall should be concentrated in 2023, when the Erasmus+ projects funded before Brexit end.

Run from the project root directory (after src/01-04, 05_analysis/01_centrality.py and
05_analysis/02_structure.py, whose tables it reads):
    python 05_analysis/07_h3_change.py          (~1 minute)

Outputs (05_analysis/tables/ and 05_analysis/reports/):
  h3_claims.csv              one row per claim and measure: values, changes, verdict
  h3_qap_periods.csv         QAP correlation and edge overlap between the period networks
  h3_yearly_similarity.csv   correlation and edge overlap between consecutive years
  h3_yearly_measures.csv     density, reciprocity, Gini, top 10% share, k_max for every year
  h3_yearly_break.csv        normal year-to-year range (2016-2019) vs the changes after 2019
  h3_uk_yearly.csv           the UK year by year: students, shares, index 2019 = 100, edges, PageRank
  h3_country_change.csv      incoming and outgoing students per country, 2019 vs 2023
  h3_report.txt              everything above, as text
"""

import networkx as nx
import numpy as np
import pandas as pd

import common
from common import PERIODS, PRIMARY_THRESHOLD, SEED

N_PERMUTATIONS = 1000
CHUNK = 50               # permutations computed together (limits memory use)
DAMPING = 0.85           # PageRank, as in 01_centrality.py
TOP_PAGERANK = 50        # "UK regions among the top 50 by PageRank"
BASE_YEAR = 2019         # index = 100; last year before Covid
LAST_YEAR = 2023         # first full year after the end of the UK's Erasmus+ projects
NORMAL_YEARS = (2016, 2019)  # the year-to-year changes inside this span are the "normal" variation
EDGES = f"edges_b{PRIMARY_THRESHOLD}"
BINARY = f"binary_b{PRIMARY_THRESHOLD}"
RECIPROCITY = f"reciprocity_b{PRIMARY_THRESHOLD}"
# yearly measures compared with the normal variation (edges are left out: same % change as density)
YEARLY_LEVELS = ["density_feasible", RECIPROCITY, "gini_in_strength", "top10pct_share_in", "k_max"]
YEARLY_SIMILARITIES = ["r_weighted", "r_binary", "share_kept"]
PERIOD_PAIRS = [("pre_covid", "covid"), ("covid", "post_covid"), ("pre_covid", "post_covid")]

# (claim, measure, source table, expected direction: +1 up / -1 down, period compared with pre_covid)
CLAIMS = [
    ("sparser", EDGES, "centrality_summary", -1, "covid"),
    ("sparser", "density_feasible", "cohesion", -1, "covid"),
    ("sparser", "isolated_regions", "cohesion", +1, "covid"),
    ("sparser", "giant_scc", "cohesion", -1, "covid"),
    ("sparser", "k_max", "core_periphery_summary", -1, "covid"),
    ("sparser", "cp_core_size", "core_periphery_summary", -1, "covid"),
    ("fragmented (measure 7)", "weak_components", "cohesion", +1, "covid"),
    ("more concentrated", "gini_in_strength", "centrality_summary", +1, "covid"),
    ("more concentrated", "top10pct_share_in", "centrality_summary", +1, "covid"),
    ("more concentrated", "gini_out_strength", "centrality_summary", +1, "covid"),
    ("less reciprocal", RECIPROCITY, "centrality_summary", -1, "covid"),
    ("less reciprocal", f"rho_b{PRIMARY_THRESHOLD}", "centrality_summary", -1, "covid"),
    ("less reciprocal", "reciprocity_weighted", "centrality_summary", -1, "covid"),
    ("UK loses centrality", "UK_share_in", "centrality_summary", -1, "post_covid"),
    ("UK loses centrality", "UK_share_out", "centrality_summary", -1, "post_covid"),
    ("UK loses centrality", "UK_regions_in_top50_authority", "centrality_summary", -1, "post_covid"),
    # higher number = lower position (1 = most central region)
    ("UK loses centrality", "UK_mean_pagerank_rank", "centrality_<period>", +1, "post_covid"),
]

log = common.Report("h3_report")


# -----------------------------------------------------------------------------
# 1. CLAIMS TABLE (measures of Phase 3)
# -----------------------------------------------------------------------------
def uk_mean_rank(pagerank):
    """Mean position of the UK regions when all regions are ranked by PageRank (1 = highest)."""
    ranks = pagerank.rank(ascending=False)
    return ranks[ranks.index.str.startswith("UK")].mean()


def claims_table():
    """One row per claim of H3 and measure: values in the three periods, changes and verdict."""
    sources = {}
    for name in {c[2] for c in CLAIMS} - {"centrality_<period>"}:
        file = common.TABLES_DIR / f"{name}.csv"
        if not file.exists():
            raise SystemExit(f"{file.name} not found: run 01_centrality.py and 02_structure.py first.")
        sources[name] = pd.read_csv(file).set_index("period")
    # UK position in the period networks, from the PageRank column of centrality_<period>.csv
    sources["centrality_<period>"] = pd.DataFrame(
        {"UK_mean_pagerank_rank": [
            uk_mean_rank(pd.read_csv(common.TABLES_DIR / f"centrality_{p}.csv").set_index("region").pagerank)
            for p in PERIODS]},
        index=PERIODS,
    )

    rows = []
    for claim, measure, source, expected, compared in CLAIMS:
        pre, covid, post = (float(sources[source].loc[p, measure]) for p in PERIODS)
        later = covid if compared == "covid" else post
        rows.append(
            {
                "claim": claim,
                "measure": measure,
                "source": source,
                "pre_covid": pre,
                "covid": covid,
                "post_covid": post,
                "change_covid_pct": 100 * (covid - pre) / pre if pre else np.nan,
                "change_post_pct": 100 * (post - pre) / pre if pre else np.nan,
                "recovered_share": (post - covid) / (pre - covid) if pre != covid else np.nan,
                "expected": "up" if expected > 0 else "down",
                "compared": f"pre_covid -> {compared}",
                "as_expected": bool(np.sign(later - pre) == expected),
            }
        )
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# 2-3. MATRICES, QAP CORRELATION AND EDGE OVERLAP
# -----------------------------------------------------------------------------
def flow_matrix(G, regions, binary):
    """n x n matrix of a network: 0/1 if binary, otherwise log(1 + students)."""
    A = nx.to_numpy_array(G, nodelist=regions, weight=None if binary else "weight")
    return A if binary else np.log1p(A)


def relabellings(n, size, rng, groups):
    """`size` random relabellings of n regions (one per row). With groups (country codes), every
    region is relabelled only among regions of its own group."""
    order = np.tile(np.arange(n), (size, 1))
    for g in np.unique(groups):
        members = np.flatnonzero(groups == g)
        order[:, members] = rng.permuted(order[:, members], axis=1)
    return order


def correlation_rows(a, B):
    """Pearson correlation between vector a and every row of matrix B."""
    ac = a - a.mean()
    Bc = B - B.mean(axis=1, keepdims=True)
    return Bc @ ac / np.sqrt((ac @ ac) * (Bc**2).sum(axis=1))


def qap_correlation(A, B, cells, countries, rng):
    """Correlation between matrices A and B over the cells, and its QAP null distributions:
    free relabelling of the regions of B, and relabelling within countries."""
    rows, cols = cells
    n = A.shape[0]
    a, b_flat = A[rows, cols], B.ravel()
    r = correlation_rows(a, B[rows, cols][None, :])[0]
    null = {}
    for scheme, groups in (("free", np.zeros(n, dtype=int)), ("within_country", countries)):
        values = []
        for start in range(0, N_PERMUTATIONS, CHUNK):
            size = min(CHUNK, N_PERMUTATIONS - start)
            relabel = relabellings(n, size, rng, groups)
            values.append(correlation_rows(a, b_flat[relabel[:, rows] * n + relabel[:, cols]]))
        null[scheme] = np.concatenate(values)
    return {
        "r": r,
        # one-sided: is the later network MORE similar to the earlier one than chance?
        "p_qap": (np.sum(null["free"] >= r) + 1) / (N_PERMUTATIONS + 1),
        "null_mean_free": null["free"].mean(),
        "null_mean_within_country": null["within_country"].mean(),
        "p_within_country": (np.sum(null["within_country"] >= r) + 1) / (N_PERMUTATIONS + 1),
    }


def edge_overlap(A, B, cells):
    """Edges of the earlier network (A) kept in the later one (B), and edges of B that are new."""
    a, b = A[cells] > 0, B[cells] > 0
    common_edges = int((a & b).sum())
    return {
        "edges_earlier": int(a.sum()),
        "edges_later": int(b.sum()),
        "common_edges": common_edges,
        "jaccard": common_edges / int((a | b).sum()),
        "share_kept": common_edges / int(a.sum()),
        "share_new": (int(b.sum()) - common_edges) / int(b.sum()),
    }


def period_comparisons(regions, cells, countries, rng):
    """QAP correlation and edge overlap for every pair of periods, weighted and binary."""
    networks = {
        p: {"weighted": flow_matrix(common.load_period(p), regions, binary=False),
            BINARY: flow_matrix(common.load_binary(p, PRIMARY_THRESHOLD), regions, binary=True)}
        for p in PERIODS
    }
    rows = []
    for earlier, later in PERIOD_PAIRS:
        for version in ("weighted", BINARY):
            print(f"QAP {earlier} vs {later} ({version}) ...")
            A, B = networks[earlier][version], networks[later][version]
            rows.append(
                {"earlier": earlier, "later": later, "network": version,
                 **qap_correlation(A, B, cells, countries, rng), **edge_overlap(A, B, cells)}
            )
    return pd.DataFrame(rows)


def yearly_similarity(regions, cells):
    """Correlation (weighted) and edge overlap (edge = at least PRIMARY_THRESHOLD students in the
    year) between each year and the previous one. No p-values: this is the benchmark of how much
    the network changes from one year to the next."""
    years = common.networks.available_years()
    students = {y: nx.to_numpy_array(common.load_year(y), nodelist=regions, weight="weight") for y in years}
    rows = []
    for previous, year in zip(years[:-1], years[1:]):
        A, B = np.log1p(students[previous]), np.log1p(students[year])
        binary_a = (students[previous] >= PRIMARY_THRESHOLD).astype(float)
        binary_b = (students[year] >= PRIMARY_THRESHOLD).astype(float)
        rows.append(
            {"from_year": previous, "to_year": year,
             "r_weighted": correlation_rows(A[cells], B[cells][None, :])[0],
             "r_binary": correlation_rows(binary_a[cells], binary_b[cells][None, :])[0],
             **edge_overlap(binary_a, binary_b, cells)}
        )
    return pd.DataFrame(rows)


def yearly_measures(regions):
    """Key Phase 3 measures on every yearly network, with the same definitions used for the
    periods (binary edge = at least PRIMARY_THRESHOLD students in the year)."""
    feasible = common.feasible_pairs(regions)
    rows = []
    for year in common.networks.available_years():
        G = common.load_year(year)  # weighted, all 319 regions
        B = nx.DiGraph()
        B.add_nodes_from(G)
        B.add_edges_from((u, v) for u, v, w in G.edges(data="weight") if w >= PRIMARY_THRESHOLD)
        U = B.subgraph([r for r in B if B.degree(r) > 0]).to_undirected()
        strength = pd.DataFrame({"in": dict(G.in_degree(weight="weight")),
                                 "out": dict(G.out_degree(weight="weight"))})
        active = strength[(strength["in"] + strength["out"]) > 0]
        rows.append(
            {
                "year": year,
                EDGES: B.number_of_edges(),
                "density_feasible": B.number_of_edges() / feasible,    # as in 02_structure.py
                RECIPROCITY: nx.overall_reciprocity(B),                # as in 01_centrality.py
                "gini_in_strength": common.gini(active["in"]),         # as in 01_centrality.py
                "top10pct_share_in": common.top_share(active["in"], 0.10),
                "k_max": max(nx.core_number(U).values()),              # as in 02_structure.py
            }
        )
    return pd.DataFrame(rows)


def break_table(measures, similarity):
    """For every yearly measure: the range of its year-to-year changes in the normal years
    (NORMAL_YEARS) and its changes after them. Levels (density, Gini...) use the % change from the
    previous year; similarities (QAP r, share of edges kept) use their value, which is already a
    comparison with the previous year."""
    series = {}
    levels = measures.set_index("year")
    for measure in YEARLY_LEVELS:
        series[(measure, "% change from previous year")] = 100 * levels[measure].pct_change()
    similarities = similarity.set_index("to_year")
    for measure in YEARLY_SIMILARITIES:
        series[(measure, "similarity with previous year")] = similarities[measure]

    first, last = NORMAL_YEARS
    rows = []
    for (measure, kind), values in series.items():
        normal = values.loc[first + 1:last]  # the changes first -> first+1, ..., last-1 -> last
        row = {"measure": measure, "kind": kind, "normal_min": normal.min(), "normal_max": normal.max()}
        for year in values.index[values.index > last]:
            row[f"{year - 1}->{year}"] = values.loc[year]
        row[f"outside_normal_{last}->{last + 1}"] = not normal.min() <= values.loc[last + 1] <= normal.max()
        rows.append(row)
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# 4. UNITED KINGDOM
# -----------------------------------------------------------------------------
def uk_yearly():
    """The UK in every yearly network: students, shares, edges and PageRank position."""
    rows = []
    for year in common.networks.available_years():
        G = common.load_year(year)
        uk = [r for r in G if r.startswith("UK")]
        total = G.size(weight="weight")
        uk_in = sum(G.in_degree(r, weight="weight") for r in uk)
        uk_out = sum(G.out_degree(r, weight="weight") for r in uk)
        pagerank = pd.Series(nx.pagerank(G, alpha=DAMPING, weight="weight"))
        rows.append(
            {
                "year": year,
                "total_students": total,
                "uk_incoming": uk_in,
                "uk_outgoing": uk_out,
                "uk_share_in": uk_in / total,
                "uk_share_out": uk_out / total,
                # same definition as the Brexit check of src/02_verify_data.py
                "uk_share_involving": (uk_in + uk_out) / total,
                "rest_incoming": total - uk_in,    # students arriving in non-UK regions
                "rest_outgoing": total - uk_out,   # students leaving from non-UK regions
                f"uk_edges_in_b{PRIMARY_THRESHOLD}": sum(
                    1 for u, v, w in G.edges(data="weight") if v.startswith("UK") and w >= PRIMARY_THRESHOLD),
                f"uk_edges_out_b{PRIMARY_THRESHOLD}": sum(
                    1 for u, v, w in G.edges(data="weight") if u.startswith("UK") and w >= PRIMARY_THRESHOLD),
                "uk_mean_pagerank_rank": uk_mean_rank(pagerank),
                f"uk_regions_top{TOP_PAGERANK}_pagerank": int(pagerank.nlargest(TOP_PAGERANK).index.str.startswith("UK").sum()),
            }
        )
    df = pd.DataFrame(rows)
    # Index BASE_YEAR = 100: Covid lowers everybody, Brexit only the UK -> compare UK with the rest
    base = df.set_index("year").loc[BASE_YEAR]
    for column in ("uk_incoming", "uk_outgoing", "rest_incoming", "rest_outgoing"):
        df[f"index_{column}"] = 100 * df[column] / base[column]
    return df


def country_change():
    """Incoming and outgoing students of every country in BASE_YEAR and LAST_YEAR, with the %
    change and its rank (1 = largest fall). Both years are outside Covid, so the change shows
    which countries lost weight in the network."""
    totals = {}
    for year in (BASE_YEAR, LAST_YEAR):
        edges = nx.to_pandas_edgelist(common.load_year(year))
        totals[year] = pd.DataFrame({
            "incoming": edges.groupby(edges.target.str[:2]).weight.sum(),
            "outgoing": edges.groupby(edges.source.str[:2]).weight.sum(),
        }).fillna(0)
    df = pd.DataFrame(index=totals[BASE_YEAR].index.rename("country"))
    for direction in ("incoming", "outgoing"):
        first = totals[BASE_YEAR][direction]
        last = totals[LAST_YEAR][direction].reindex(df.index).fillna(0)
        df[f"{direction}_{BASE_YEAR}"] = first
        df[f"{direction}_{LAST_YEAR}"] = last
        df[f"{direction}_change_pct"] = 100 * (last - first) / first
        df[f"{direction}_rank_fall"] = df[f"{direction}_change_pct"].rank(method="min").astype(int)
    return df.reset_index().sort_values("outgoing_change_pct")


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
def main():
    common.output_dirs()
    rng = np.random.default_rng(SEED)

    regions = common.load_regions().region.tolist()   # all 319 regions, UK included
    countries = np.array([r[:2] for r in regions])
    cells = np.nonzero(countries[:, None] != countries[None, :])  # cross-country pairs only

    print("claims ...")
    claims = claims_table()
    qap = period_comparisons(regions, cells, countries, rng)
    print("yearly networks ...")
    yearly = yearly_similarity(regions, cells)
    measures = yearly_measures(regions)
    breaks = break_table(measures, yearly)
    uk = uk_yearly()
    countries_table = country_change()

    outputs = {
        "h3_claims": claims, "h3_qap_periods": qap, "h3_yearly_similarity": yearly,
        "h3_yearly_measures": measures, "h3_yearly_break": breaks,
        "h3_uk_yearly": uk, "h3_country_change": countries_table,
    }
    for name, table in outputs.items():
        table.round(4).to_csv(common.TABLES_DIR / f"{name}.csv", index=False)

    # --- Report ------------------------------------------------------------------
    log.title("H3: COVID AND BREXIT")
    log("Mainly a descriptive comparison between networks; the formal test is the QAP correlation.")
    log(f"QAP and overlap: all {len(regions)} regions, {len(cells[0]):,} ordered cross-country pairs, "
        f"{N_PERMUTATIONS} permutations.")

    log.title("1. CLAIMS: PHASE 3 MEASURES ACROSS THE PERIODS")
    log("as_expected: the change goes in the direction H3 expects (see column 'compared').")
    log("recovered_share: share of the Covid change undone in 2022-23 (1 = full, < 0 = moved further).")
    log(claims.drop(columns="source").round(3).to_string(index=False))

    log.title("2. QAP CORRELATION BETWEEN THE PERIOD NETWORKS")
    log("r: correlation over the cross-country pairs (weighted: log(1 + students); binary: 0/1).")
    log("p_qap: classic QAP (free relabelling), one-sided. null_mean_within_country: correlation "
        "expected if regions were relabelled within their country (only the countries keep their ties).")
    log("share_kept: edges of the earlier period still present later; share_new: edges of the later "
        "period that did not exist before (weighted: any flow; binary: >= "
        f"{PRIMARY_THRESHOLD} students/year).")
    log(qap.round(3).to_string(index=False))

    log.title("3. YEARLY BENCHMARK: EACH YEAR VS THE PREVIOUS ONE")
    log(f"Binary edge = at least {PRIMARY_THRESHOLD} students in the year. "
        f"{NORMAL_YEARS[0]}-{NORMAL_YEARS[1]} = normal year-to-year change.")
    log("\nSimilarity with the previous year:")
    log(yearly.round(3).to_string(index=False))
    log("\nPhase 3 measures on every yearly network (same definitions as for the periods):")
    log(measures.round(3).to_string(index=False))
    log(f"\nChanges after {NORMAL_YEARS[1]} vs the normal range ({NORMAL_YEARS[0]}-{NORMAL_YEARS[1]}, "
        "only three year-to-year changes: a range, not a distribution).")
    log("Levels: % change from the previous year. Similarities: value of the comparison with the previous year.")
    log(breaks.round(3).to_string(index=False))

    log.title("4a. UNITED KINGDOM YEAR BY YEAR")
    log(f"index_*: {BASE_YEAR} = 100. Covid lowers everybody; Brexit shows as the UK falling more than the rest.")
    log(uk.round(3).to_string(index=False))

    log.title(f"4b. COUNTRIES: CHANGE {BASE_YEAR} -> {LAST_YEAR}")
    log(f"rank_fall: 1 = largest fall among the {len(countries_table)} countries.")
    columns = ["country", f"outgoing_{BASE_YEAR}", f"outgoing_{LAST_YEAR}", "outgoing_change_pct",
               "outgoing_rank_fall", f"incoming_{BASE_YEAR}", f"incoming_{LAST_YEAR}",
               "incoming_change_pct", "incoming_rank_fall"]
    log(countries_table[columns].round(1).to_string(index=False))
    log.save()


if __name__ == "__main__":
    main()