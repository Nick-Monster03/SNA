"""
03_homophily.py - Measure 11 of the roadmap: homophily and assortativity.

Do regions exchange students with similar regions?
  - wealth: GDP per capita of the period (276 regions with GDP; UK, IS, LI excluded)
      assortativity = correlation between the GDP of origin and destination over the edges
      (binary: every edge counts 1; weighted: every student counts 1), on log GDP;
      p-value from 2,000 permutations of GDP across regions (edges stay fixed);
      share of students moving to a richer region; flows between GDP terciles.
  - geography / programme: UN macro-area and programme group of the country (see common.py)
      E-I index (-1 = all ties inside the group, +1 = all ties across groups), compared with the
      value expected if ties were spread over the feasible pairs at random (gravity-like
      expectation for the weighted network); Newman's assortativity coefficient; mixing matrices.

Run from the project root directory (after src/01-04):
    python 05_analysis/03_homophily.py

Outputs (05_analysis/tables/ and 05_analysis/reports/):
  homophily_gdp.csv         wealth assortativity per period and network version
  homophily_groups.csv      E-I index and assortativity for macro-area and programme group
  mixing_matrices.csv       flows between groups (GDP terciles, macro-areas, programme groups)
  homophily_report.txt      everything above, as text
"""

import numpy as np
import pandas as pd

import common
from common import MACRO_AREA, PERIODS, PRIMARY_THRESHOLD, PROGRAMME_GROUP, SEED

N_PERMUTATIONS = 2000
log = common.Report("homophily_report")


def weighted_corr(x, y, w):
    w = w / w.sum()
    mx, my = (w * x).sum(), (w * y).sum()
    cov = (w * (x - mx) * (y - my)).sum()
    return cov / np.sqrt((w * (x - mx) ** 2).sum() * (w * (y - my) ** 2).sum())


def edge_arrays(G, nodes, weighted):
    index = {n: i for i, n in enumerate(nodes)}
    e = [(index[u], index[v], d.get("weight", 1.0)) for u, v, d in G.edges(data=True) if u in index and v in index]
    src, dst, w = (np.array(c) for c in zip(*e))
    return src, dst, (w.astype(float) if weighted else np.ones(len(src)))


def gdp_assortativity(G, period, weighted, rng):
    nodes = [n for n in G if f"gdp_{period}" in G.nodes[n]]
    gdp = np.array([G.nodes[n][f"gdp_{period}"] for n in nodes], dtype=float)
    src, dst, w = edge_arrays(G, nodes, weighted)
    out = {}
    for label, values in (("log", np.log(gdp)), ("raw", gdp)):
        r = weighted_corr(values[src], values[dst], w)
        perm = np.array([
            weighted_corr(p[src], p[dst], w) for p in (rng.permutation(values) for _ in range(N_PERMUTATIONS))
        ])
        out[f"r_{label}"] = r
        out[f"p_{label}"] = (np.sum(np.abs(perm) >= abs(r)) + 1) / (N_PERMUTATIONS + 1)
    richer = gdp[dst] > gdp[src]
    share = (w * richer).sum() / w.sum()
    perm_share = np.array([
        (w * (p[dst] > p[src])).sum() / w.sum() for p in (rng.permutation(gdp) for _ in range(N_PERMUTATIONS))
    ])
    out["share_to_richer"] = share
    out["p_share_to_richer"] = (np.sum(np.abs(perm_share - 0.5) >= abs(share - 0.5)) + 1) / (N_PERMUTATIONS + 1)
    out["median_gdp_ratio_dest_origin"] = float(np.exp(np.median(np.log(gdp[dst] / gdp[src]))))
    out["regions"], out["edges"] = len(nodes), len(src)
    return out


def mixing(G, groups, weighted):
    """Observed flows between groups, and the flows expected if every region kept its total
    outgoing and incoming flow but chose partners at random among feasible (cross-country) pairs."""
    nodes = [n for n in G if n in groups]
    src, dst, w = edge_arrays(G, nodes, weighted)
    labels = np.array([groups[n] for n in nodes])
    out_tot = np.bincount(src, weights=w, minlength=len(nodes))
    in_tot = np.bincount(dst, weights=w, minlength=len(nodes))
    feasible = ~(np.array([n[:2] for n in nodes])[:, None] == np.array([n[:2] for n in nodes])[None, :])
    expected_matrix = np.outer(out_tot, in_tot) * feasible
    expected_matrix *= w.sum() / expected_matrix.sum()
    cats = sorted(set(labels))
    rows = []
    for a in cats:
        for b in cats:
            obs = w[(labels[src] == a) & (labels[dst] == b)].sum()
            exp = expected_matrix[np.ix_(labels == a, labels == b)].sum()
            rows.append({"from": a, "to": b, "observed": obs, "expected": exp})
    return pd.DataFrame(rows)


def ei_and_assortativity(table):
    total = table.observed.sum()
    inside = table[table["from"] == table["to"]]
    I_obs, I_exp = inside.observed.sum(), inside.expected.sum()
    ei_obs = (total - 2 * I_obs) / total
    ei_exp = (total - 2 * I_exp) / total
    # Newman's assortativity coefficient from the mixing matrix
    e = table.pivot(index="from", columns="to", values="observed").to_numpy() / total
    trace, sq = np.trace(e), (e.sum(1) * e.sum(0)).sum()
    return {"EI_observed": ei_obs, "EI_expected": ei_exp, "share_inside_observed": I_obs / total,
            "share_inside_expected": I_exp / total, "assortativity_newman": (trace - sq) / (1 - sq)}


def main():
    common.output_dirs()
    rng = np.random.default_rng(SEED)
    gdp_rows, group_rows, mixing_rows = [], [], []

    for period in PERIODS:
        print(f"{period} ...")
        versions = {
            "weighted": (common.load_period(period), True),
            f"binary_b{PRIMARY_THRESHOLD}": (common.load_binary(period, PRIMARY_THRESHOLD), False),
        }
        for version, (G, weighted) in versions.items():
            gdp_rows.append({"period": period, "network": version, **gdp_assortativity(G, period, weighted, rng)})

            # GDP terciles of the period (regions with GDP only)
            gdp = pd.Series({n: G.nodes[n][f"gdp_{period}"] for n in G if f"gdp_{period}" in G.nodes[n]})
            terciles = pd.qcut(gdp, 3, labels=["1 low", "2 middle", "3 high"]).astype(str).to_dict()
            attributes = {
                "gdp_tercile": terciles,
                "macro_area": {n: MACRO_AREA[n[:2]] for n in G},
                "programme_group": {n: PROGRAMME_GROUP[n[:2]] for n in G},
            }
            for attribute, groups in attributes.items():
                table = mixing(G, groups, weighted)
                group_rows.append(
                    {"period": period, "attribute": attribute, "network": version, **ei_and_assortativity(table)}
                )
                table["ratio"] = table.observed / table.expected
                table.insert(0, "network", version)
                table.insert(0, "attribute", attribute)
                table.insert(0, "period", period)
                mixing_rows.append(table)

    gdp_df = pd.DataFrame(gdp_rows).round(4)
    gdp_df.to_csv(common.TABLES_DIR / "homophily_gdp.csv", index=False)
    group_df = pd.DataFrame(group_rows).round(4)
    group_df.to_csv(common.TABLES_DIR / "homophily_groups.csv", index=False)
    mix_df = pd.concat(mixing_rows).round(3)
    mix_df.to_csv(common.TABLES_DIR / "mixing_matrices.csv", index=False)

    # --- Report ------------------------------------------------------------------
    log.title("MEASURE 11: HOMOPHILY AND ASSORTATIVITY")
    log("Weighted: every student counts once; binary: every edge (>= "
        f"{PRIMARY_THRESHOLD} students/year) counts once. Regions without GDP (UK, IS, LI) excluded from GDP rows.")

    log.title("WEALTH: correlation between GDP per capita of origin and destination")
    log(f"p-values: {N_PERMUTATIONS} permutations of GDP across regions. share_to_richer: share of students "
        "(or edges) going to a region with higher GDP per capita.")
    log(gdp_df.to_string(index=False))

    log.title("GROUPS: E-I index (observed vs expected over feasible pairs) and Newman assortativity")
    log("EI = (external - internal) / total. EI_observed < EI_expected = more ties inside the group than chance.")
    log(group_df.to_string(index=False))

    log.title("MIXING MATRICES (weighted network): ratio observed / expected students")
    log("ratio > 1: more students than expected from the sizes of the two groups.")
    for attribute in ("gdp_tercile", "programme_group", "macro_area"):
        for period in PERIODS:
            sel = mix_df[(mix_df.period == period) & (mix_df.attribute == attribute) & (mix_df.network == "weighted")]
            log(f"\n{attribute} - {period} (rows = origin, columns = destination)")
            log(sel.pivot(index="from", columns="to", values="ratio").to_string())
    log.save()


if __name__ == "__main__":
    main()