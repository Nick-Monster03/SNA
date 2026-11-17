"""
02_structure.py - Measures 5-10 of the roadmap on the three period networks.

   5. k-core and core-periphery (Borgatti-Everett)   binary, undirected
   6. Communities (Louvain) and modularity            weighted, directed
   7. Density, components, average distances          binary, directed and undirected
   8. Clustering and small-world (sigma, omega)       binary, undirected
   9. Degree distribution (heavy tails)               binary and weighted
  10. Triad census vs. random graphs (U|MAN)          binary, directed

Every null model and every density uses only FEASIBLE pairs: two regions of the same country can
never be linked (domestic flows are removed, decision 4), so those pairs are structural zeros and
random graphs never place edges there.

Run from the project root directory (after src/01-04):
    python 05_analysis/02_structure.py                 # primary binary threshold (5 students/year)
    python 05_analysis/02_structure.py --threshold 3   # robustness check; outputs end in _t3

Takes a few minutes (the triad census null model is the slow part).

Outputs (05_analysis/tables/ and 05_analysis/reports/):
  cohesion.csv                     measure 7, one row per period
  core_<period>.csv                measure 5, one row per region (k-core number, core-periphery)
  core_periphery_summary.csv       measure 5, one row per period
  communities_<period>.csv         measure 6, community of each region
  communities_summary.csv          measure 6, one row per community
  small_world.csv                  measure 8
  degree_distribution_fits.csv     measure 9
  triad_census.csv                 measure 10
  structure_report.txt             everything above, as text
"""

import argparse
import math
import random
import warnings
from collections import Counter

import networkx as nx
import numpy as np
import pandas as pd
from scipy.sparse.csgraph import shortest_path

import common
from common import MACRO_AREA, PERIODS, PRIMARY_THRESHOLD, PROGRAMME_GROUP, SEED

N_RANDOM_SMALL_WORLD = 20   # degree-preserving random graphs for sigma and omega
N_RANDOM_TRIADS = 50        # U|MAN random graphs for the triad census
N_LOUVAIN_RUNS = 20         # Louvain is random: keep the run with the highest modularity

TRIAD_TYPES = ["003", "012", "102", "021D", "021U", "021C", "111D", "111U",
               "030T", "030C", "201", "120D", "120U", "120C", "210", "300"]


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------
def active_subgraph(G):
    return G.subgraph([n for n, d in G.degree() if d > 0]).copy()


def path_stats(G):
    """Average shortest path length and diameter (in steps) over the reachable pairs of G."""
    nodes = list(G)
    A = nx.to_scipy_sparse_array(G, nodelist=nodes, weight=None)
    D = shortest_path(A, directed=G.is_directed(), unweighted=True)
    off = ~np.eye(len(nodes), dtype=bool)
    finite = np.isfinite(D) & off
    return float(D[finite].mean()), int(D[finite].max())


def ranked(counter):
    """Counter items by count, ties in alphabetical order (stable output from run to run)."""
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))


def same_country_mask(nodes):
    c = np.array([n[:2] for n in nodes])
    return c[:, None] == c[None, :]


# -----------------------------------------------------------------------------
# 7. Cohesion
# -----------------------------------------------------------------------------
def cohesion(period, B, W):
    A = active_subgraph(B)
    n_all, n_act = B.number_of_nodes(), A.number_of_nodes()
    wcc = sorted((len(c) for c in nx.weakly_connected_components(A)), reverse=True)
    scc = max(nx.strongly_connected_components(A), key=len)
    L_dir, diam_dir = path_stats(A.subgraph(scc))
    U = A.to_undirected()
    L_und, diam_und = path_stats(U.subgraph(max(nx.connected_components(U), key=len)))
    return {
        "period": period,
        "active_regions": n_act,
        "isolated_regions": n_all - n_act,
        "edges": A.number_of_edges(),
        "density_all_319": round(nx.density(B), 4),
        "density_active": round(nx.density(A), 4),
        "density_feasible": round(A.number_of_edges() / common.feasible_pairs(list(B)), 4),
        "density_feasible_any_flow": round(W.number_of_edges() / common.feasible_pairs(list(W)), 4),
        "weak_components": len(wcc),
        "giant_wcc": wcc[0],
        "giant_scc": len(scc),
        "avg_path_directed_scc": round(L_dir, 3),
        "diameter_directed_scc": diam_dir,
        "avg_path_undirected": round(L_und, 3),
        "diameter_undirected": diam_und,
    }


# -----------------------------------------------------------------------------
# 5. k-core and core-periphery
# -----------------------------------------------------------------------------
def core_periphery(U):
    """Discrete Borgatti-Everett core-periphery model on an undirected binary graph.

    Finds the core that maximizes the correlation between the observed adjacency matrix and an
    ideal pattern (core-core pairs = 1, periphery-periphery pairs = 0; core-periphery pairs are
    left out, the usual 'density' variant). Same-country pairs are structural zeros and are left
    out too. Search: best core size along the degree ranking, then single-node moves until no
    move improves the correlation."""
    nodes = sorted(U, key=lambda n: -U.degree(n))
    A = nx.to_numpy_array(U, nodelist=nodes, weight=None)
    iu = np.triu_indices(len(nodes), k=1)
    feasible = ~same_country_mask(nodes)[iu]
    a = A[iu][feasible]
    rows, cols = iu[0][feasible], iu[1][feasible]

    def corr(core):
        ci, cj = core[rows], core[cols]
        keep = ci == cj
        x, y = a[keep], ci[keep].astype(float)
        if y.std() == 0 or x.std() == 0:
            return -1.0
        return float(np.corrcoef(x, y)[0, 1])

    best_core, best = None, -1.0
    for k in range(2, len(nodes) - 1):
        core = np.zeros(len(nodes), dtype=bool)
        core[:k] = True
        c = corr(core)
        if c > best:
            best_core, best = core, c
    improved = True
    while improved:
        improved = False
        for i in range(len(nodes)):
            trial = best_core.copy()
            trial[i] = ~trial[i]
            c = corr(trial)
            if c > best + 1e-12:
                best_core, best, improved = trial, c, True

    core_set = {n for n, c in zip(nodes, best_core) if c}

    def block_density(f):
        sel = np.array([f(nodes[i] in core_set, nodes[j] in core_set) for i, j in zip(rows, cols)])
        return float(a[sel].mean()) if sel.any() else float("nan")

    densities = {
        "density_core_core": block_density(lambda x, y: x and y),
        "density_core_periphery": block_density(lambda x, y: x != y),
        "density_periphery_periphery": block_density(lambda x, y: not x and not y),
    }
    return core_set, best, densities


# -----------------------------------------------------------------------------
# 6. Communities
# -----------------------------------------------------------------------------
def nmi(labels_a, labels_b):
    """Normalized mutual information between two partitions (0 = unrelated, 1 = identical)."""
    table = pd.crosstab(pd.Series(labels_a), pd.Series(labels_b)).to_numpy(dtype=float)
    p = table / table.sum()
    pa, pb = p.sum(1), p.sum(0)
    nz = p > 0
    mi = (p[nz] * np.log(p[nz] / np.outer(pa, pb)[nz])).sum()
    ha, hb = -(pa * np.log(pa)).sum(), -(pb * np.log(pb)).sum()
    return float(2 * mi / (ha + hb)) if ha + hb > 0 else 1.0


def communities(W):
    A = active_subgraph(W)
    runs = []
    for i in range(N_LOUVAIN_RUNS):
        parts = nx.community.louvain_communities(A, weight="weight", resolution=1, seed=SEED + i)
        runs.append((nx.community.modularity(A, parts, weight="weight"), parts))
    q_best, best = max(runs, key=lambda r: r[0])
    best = sorted(best, key=lambda c: -sum(d for _, d in A.in_degree(c, weight="weight")))
    label = {n: k + 1 for k, c in enumerate(best) for n in c}
    nodes = list(A)

    def as_labels(parts):
        lab = {n: k for k, c in enumerate(parts) for n in c}
        return [lab[n] for n in nodes]

    best_labels = as_labels(best)
    stability = np.mean([nmi(best_labels, as_labels(p)) for _, p in runs])

    # How much do the communities follow geography / programme groups?
    by_area = [{n for n in nodes if MACRO_AREA[n[:2]] == g} for g in set(MACRO_AREA.values())]
    by_group = [{n for n in nodes if PROGRAMME_GROUP[n[:2]] == g} for g in set(PROGRAMME_GROUP.values())]
    by_area = [c for c in by_area if c]
    by_group = [c for c in by_group if c]
    within = sum(w for u, v, w in A.edges(data="weight") if label[u] == label[v]) / A.size(weight="weight")
    summary = {
        "modularity": q_best,
        "modularity_range_runs": (min(r[0] for r in runs), max(r[0] for r in runs)),
        "n_communities": len(best),
        "stability_nmi": stability,
        "share_flow_within": within,
        "nmi_macro_area": nmi(best_labels, [MACRO_AREA[n[:2]] for n in nodes]),
        "nmi_programme_group": nmi(best_labels, [PROGRAMME_GROUP[n[:2]] for n in nodes]),
        "nmi_country": nmi(best_labels, [n[:2] for n in nodes]),
        "modularity_macro_area": nx.community.modularity(A, by_area, weight="weight"),
        "modularity_programme_group": nx.community.modularity(A, by_group, weight="weight"),
    }
    rows = []
    for k, c in enumerate(best, start=1):
        countries = Counter(n[:2] for n in c)
        mix = lambda groups: ", ".join(
            f"{g} {m / len(c):.0%}" for g, m in ranked(Counter(groups[n[:2]] for n in c))
        )
        rows.append(
            {
                "community": k,
                "regions": len(c),
                "countries": len(countries),
                "incoming_students": round(sum(d for _, d in A.in_degree(c, weight="weight"))),
                "programme_groups": mix(PROGRAMME_GROUP),
                "macro_areas": mix(MACRO_AREA),
                "countries_by_regions": ", ".join(f"{ct} {m}" for ct, m in ranked(countries)),
            }
        )
    return label, summary, pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# 8. Small-world
# -----------------------------------------------------------------------------
def rewire(U, rng, swaps_per_edge=10):
    """Degree-preserving random graph (double edge swaps) that never creates same-country edges."""
    edges = [tuple(e) for e in U.edges()]
    present = {frozenset(e) for e in edges}
    target, done, tries = swaps_per_edge * len(edges), 0, 0
    while done < target and tries < 20 * target:
        tries += 1
        i, j = rng.randrange(len(edges)), rng.randrange(len(edges))
        (a, b), (c, d) = edges[i], edges[j]
        if rng.random() < 0.5:
            c, d = d, c
        if len({a, b, c, d}) < 4 or a[:2] == d[:2] or c[:2] == b[:2]:
            continue
        e1, e2 = frozenset((a, d)), frozenset((c, b))
        if e1 in present or e2 in present:
            continue
        present -= {frozenset((a, b)), frozenset((c, d))}
        present |= {e1, e2}
        edges[i], edges[j] = (a, d), (c, b)
        done += 1
    R = nx.Graph()
    R.add_nodes_from(U)
    R.add_edges_from(edges)
    return R


def small_world(B, rng):
    U = active_subgraph(B).to_undirected()
    U = U.subgraph(max(nx.connected_components(U), key=len)).copy()
    C, T = nx.average_clustering(U), nx.transitivity(U)
    L, _ = path_stats(U)
    Cr, Lr = [], []
    for _ in range(N_RANDOM_SMALL_WORLD):
        R = rewire(U, rng)
        R = R.subgraph(max(nx.connected_components(R), key=len))
        Cr.append(nx.average_clustering(R))
        Lr.append(path_stats(R)[0])
    Cr, Lr = float(np.mean(Cr)), float(np.mean(Lr))
    k = 2 * U.number_of_edges() / U.number_of_nodes()
    C_lattice = 3 * (k - 2) / (4 * (k - 1))   # clustering of a ring lattice with the same mean degree
    # Erdos-Renyi reference with the same density over feasible pairs (expected clustering = density)
    C_er = U.number_of_edges() / (common.feasible_pairs(list(U)) / 2)
    return {
        "regions": U.number_of_nodes(),
        "edges": U.number_of_edges(),
        "mean_degree": round(k, 1),
        "clustering_avg": round(C, 3),
        "transitivity": round(T, 3),
        "avg_path": round(L, 3),
        "clustering_random": round(Cr, 3),
        "avg_path_random": round(Lr, 3),
        "clustering_lattice": round(C_lattice, 3),
        "sigma": round((C / Cr) / (L / Lr), 3),
        "clustering_erdos_renyi": round(C_er, 3),
        "C_over_C_erdos_renyi": round(C / C_er, 2),
        "omega": round(Lr / L - C / C_lattice, 3),
    }


# -----------------------------------------------------------------------------
# 9. Degree distribution
# -----------------------------------------------------------------------------
def distribution_fits(B, W, period):
    import powerlaw

    A = active_subgraph(B)
    series = {
        "in_degree_binary": ([d for _, d in A.in_degree()], True),
        "out_degree_binary": ([d for _, d in A.out_degree()], True),
        "in_strength": ([d for _, d in W.in_degree(weight="weight") if d > 0], False),
        "out_strength": ([d for _, d in W.out_degree(weight="weight") if d > 0], False),
    }
    rows = []
    for name, (x, discrete) in series.items():
        x = np.asarray(x, dtype=float)
        x = x[x > 0]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = powerlaw.Fit(x, discrete=discrete, verbose=False)
            r_exp, p_exp = fit.distribution_compare("power_law", "exponential", normalized_ratio=True)
            r_ln, p_ln = fit.distribution_compare("power_law", "lognormal", normalized_ratio=True)
        rows.append(
            {
                "period": period,
                "variable": name,
                "n": len(x),
                "mean": round(x.mean(), 1),
                "max": round(x.max(), 1),
                "max_over_mean": round(x.max() / x.mean(), 1),
                "coef_variation": round(x.std() / x.mean(), 2),
                "powerlaw_alpha": round(fit.power_law.alpha, 2),
                "powerlaw_xmin": round(fit.power_law.xmin, 1),
                "n_tail": int((x >= fit.power_law.xmin).sum()),
                "R_vs_exponential": round(r_exp, 2),
                "p_vs_exponential": round(p_exp, 3),
                "R_vs_lognormal": round(r_ln, 2),
                "p_vs_lognormal": round(p_ln, 3),
            }
        )
    return rows


# -----------------------------------------------------------------------------
# 10. Triad census
# -----------------------------------------------------------------------------
def triad_census(B, rng):
    """Observed triad census vs. random graphs with the same numbers of mutual, asymmetric and
    null dyads (U|MAN), placed only on feasible (cross-country) pairs."""
    nodes = list(B)
    observed = nx.triadic_census(B)
    mutual = sum(1 for u, v in B.edges() if B.has_edge(v, u)) // 2
    asym = B.number_of_edges() - 2 * mutual
    pairs = [(u, v) for i, u in enumerate(nodes) for v in nodes[i + 1:] if u[:2] != v[:2]]
    sims = []
    for _ in range(N_RANDOM_TRIADS):
        chosen = rng.sample(pairs, mutual + asym)
        R = nx.DiGraph()
        R.add_nodes_from(nodes)
        for u, v in chosen[:mutual]:
            R.add_edges_from([(u, v), (v, u)])
        for u, v in chosen[mutual:]:
            R.add_edge(*((u, v) if rng.random() < 0.5 else (v, u)))
        sims.append(nx.triadic_census(R))
    rows = []
    for t in TRIAD_TYPES:
        values = np.array([s[t] for s in sims], dtype=float)
        mean, sd = values.mean(), values.std(ddof=1)
        rows.append(
            {
                "triad": t,
                "observed": observed[t],
                "expected": round(mean, 1),
                "ratio": round(observed[t] / mean, 2) if mean > 0 else math.nan,
                "z": round((observed[t] - mean) / sd, 1) if sd > 0 else math.nan,
            }
        )
    return pd.DataFrame(rows), {"mutual_dyads": mutual, "asymmetric_dyads": asym}


# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=int, default=PRIMARY_THRESHOLD)
    threshold = parser.parse_args().threshold
    suffix = "" if threshold == PRIMARY_THRESHOLD else f"_t{threshold}"

    common.output_dirs()
    log = common.Report(f"structure_report{suffix}")
    rng = random.Random(SEED)
    out = lambda name: common.TABLES_DIR / f"{name}{suffix}.csv"

    cohesion_rows, cp_rows, comm_rows, sw_rows, fit_rows, triads = [], [], [], [], [], []
    for period in PERIODS:
        print(f"\n--- {period} ---")
        W = common.load_period(period)
        B = common.load_binary(period, threshold)
        U = active_subgraph(B).to_undirected()

        print("cohesion ...")
        cohesion_rows.append(cohesion(period, B, W))

        print("k-core and core-periphery ...")
        core_number = nx.core_number(U)
        k_max = max(core_number.values())
        core_set, cp_corr, cp_dens = core_periphery(U)
        nodes_table = pd.DataFrame(
            {
                "region": list(B),
                "name": [B.nodes[n].get("name", "") for n in B],
                "country": [n[:2] for n in B],
                "degree_undirected": [U.degree(n) if n in U else 0 for n in B],
                "core_number": [core_number.get(n, 0) for n in B],
                "in_max_kcore": [int(core_number.get(n, 0) == k_max) for n in B],
                "cp_core": [int(n in core_set) for n in B],
            }
        )
        max_core = nodes_table[nodes_table.in_max_kcore == 1]
        cp_rows.append(
            {
                "period": period,
                "k_max": k_max,
                "max_kcore_size": len(max_core),
                "max_kcore_countries": max_core.country.nunique(),
                "mean_core_number": round(nodes_table.core_number[nodes_table.degree_undirected > 0].mean(), 1),
                "cp_core_size": len(core_set),
                "cp_core_countries": len({n[:2] for n in core_set}),
                "cp_correlation": round(cp_corr, 3),
                **{k: round(v, 3) for k, v in cp_dens.items()},
                "cp_core_by_country": ", ".join(
                    f"{c} {m}" for c, m in ranked(Counter(n[:2] for n in core_set))
                ),
            }
        )

        print("communities ...")
        label, comm_summary, comm_table = communities(W)
        nodes_table["community"] = [label.get(n, 0) for n in B]
        nodes_table[["region", "name", "country", "community"]].to_csv(out(f"communities_{period}"), index=False)
        nodes_table.drop(columns="community").to_csv(out(f"core_{period}"), index=False)
        comm_table.insert(0, "period", period)
        comm_rows.append((period, comm_summary, comm_table))

        print("small-world (random graphs) ...")
        sw_rows.append({"period": period, **small_world(B, rng)})

        print("degree distribution ...")
        fit_rows += distribution_fits(B, W, period)

        print("triad census (random graphs) ...")
        t, dyads = triad_census(B, rng)
        t.insert(0, "period", period)
        triads.append((period, t, dyads))

    cohesion_df = pd.DataFrame(cohesion_rows)
    cohesion_df.to_csv(out("cohesion"), index=False)
    cp_df = pd.DataFrame(cp_rows)
    cp_df.to_csv(out("core_periphery_summary"), index=False)
    pd.concat([c[2] for c in comm_rows]).to_csv(out("communities_summary"), index=False)
    sw_df = pd.DataFrame(sw_rows)
    sw_df.to_csv(out("small_world"), index=False)
    fit_df = pd.DataFrame(fit_rows)
    fit_df.to_csv(out("degree_distribution_fits"), index=False)
    triad_df = pd.concat([t[1] for t in triads])
    triad_df.to_csv(out("triad_census"), index=False)

    # --- Report ------------------------------------------------------------------
    log.title(f"MEASURES 5-10: STRUCTURE (binary networks: edge if >= {threshold} students/year)")
    log("Densities and null models use feasible pairs only (regions in different countries).")

    log.title("7. DENSITY, COMPONENTS, DISTANCES")
    log(cohesion_df.set_index("period").T.to_string())

    log.title("5. K-CORE AND CORE-PERIPHERY (undirected binary network)")
    log(cp_df.drop(columns="cp_core_by_country").set_index("period").T.to_string())
    for _, r in cp_df.iterrows():
        log(f"\n  {r.period}: core-periphery core by country: {r.cp_core_by_country}")
    sets = {p: set(pd.read_csv(out(f"core_{p}")).query("cp_core == 1").region) for p in PERIODS}
    for a, b in (("pre_covid", "covid"), ("covid", "post_covid"), ("pre_covid", "post_covid")):
        j = len(sets[a] & sets[b]) / len(sets[a] | sets[b])
        log(f"  core overlap {a} vs {b} (Jaccard): {j:.2f}")

    log.title("6. COMMUNITIES (Louvain on the weighted directed network)")
    for period, s, table in comm_rows:
        log(
            f"\n{period}: modularity Q = {s['modularity']:.3f} (runs: {s['modularity_range_runs'][0]:.3f}-"
            f"{s['modularity_range_runs'][1]:.3f}), {s['n_communities']} communities, "
            f"stability across runs (NMI) {s['stability_nmi']:.2f}, flow inside communities {s['share_flow_within']:.1%}"
        )
        log(
            f"  NMI with: country {s['nmi_country']:.2f}, macro-area {s['nmi_macro_area']:.2f}, "
            f"programme group {s['nmi_programme_group']:.2f} | modularity of partition by macro-area "
            f"{s['modularity_macro_area']:.3f}, by programme group {s['modularity_programme_group']:.3f}"
        )
        log(table.drop(columns="period").to_string(index=False, max_colwidth=120))
    log("\nNote: the modularity null model also expects flows between regions of the same country, which")
    log("are impossible here, so Q values are deflated (e.g. Q < 0 for the macro-area partition): compare")
    log("Q across periods and partitions, not with values from other networks.")

    log.title("8. CLUSTERING AND SMALL-WORLD (undirected binary, giant component)")
    log(sw_df.set_index("period").T.to_string())
    log("sigma > 1: small-world. omega near 0: small-world; near -1: lattice-like; near +1: random-like.")
    log("Random graphs: same degrees, no same-country edges. Lattice clustering: ring lattice formula.")
    log("Erdos-Renyi: random graph with the same density (no degree heterogeneity).")

    log.title("9. DEGREE DISTRIBUTION (powerlaw package; R > 0 favours power law, p < 0.1 = significant)")
    log(fit_df.to_string(index=False))

    log.title("10. TRIAD CENSUS vs U|MAN random graphs (same mutual/asymmetric/null dyads)")
    for period, t, dyads in triads:
        log(f"\n{period}: {dyads['mutual_dyads']:,} mutual dyads, {dyads['asymmetric_dyads']:,} asymmetric dyads")
    log(triad_df.pivot(index="triad", columns="period", values=["observed", "ratio", "z"]).reindex(TRIAD_TYPES).to_string())
    log.save()


if __name__ == "__main__":
    main()