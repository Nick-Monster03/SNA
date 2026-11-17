"""
01_centrality.py - Measures 1-4 of the roadmap on the three period networks.

  1. In/out degree and strength (+ net balance)    weighted and binary networks
  2. PageRank and HITS (hubs and authorities)      weighted network
  3. Reciprocity (binary and weighted)             binary and weighted networks
  4. Betweenness (edge length = 1 / students)      weighted network

Run from the project root directory (after src/01-04):
    python 05_analysis/01_centrality.py

Outputs:
  05_analysis/tables/centrality_<period>.csv   one row per region, every measure
  05_analysis/tables/centrality_summary.csv    network-level figures per period
  05_analysis/tables/top_regions.csv           top 10 regions per measure and period
  05_analysis/tables/rank_stability.csv        Spearman correlation of rankings between periods
  05_analysis/reports/centrality_report.txt    everything above, as text
"""

import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import common
from common import PERIODS, PRIMARY_THRESHOLD

TOP_N = 10
DAMPING = 0.85  # PageRank: probability of following an edge instead of jumping to a random region

log = common.Report("centrality_report")


def node_measures(period):
    G = common.load_period(period)                       # weighted, directed
    B = common.load_binary(period, PRIMARY_THRESHOLD)    # binary, directed

    in_strength = dict(G.in_degree(weight="weight"))
    out_strength = dict(G.out_degree(weight="weight"))
    pagerank = nx.pagerank(G, alpha=DAMPING, weight="weight")
    hubs, authorities = nx.hits(G, max_iter=1000, normalized=True)  # uses the 'weight' attribute
    betweenness = nx.betweenness_centrality(G, weight="distance", normalized=True)

    rows = []
    for r in G.nodes():
        s_in, s_out = in_strength[r], out_strength[r]
        rows.append(
            {
                "region": r,
                "name": G.nodes[r].get("name", ""),
                "country": r[:2],
                "in_degree": G.in_degree(r),          # partner regions sending students (any flow)
                "out_degree": G.out_degree(r),        # partner regions receiving its students
                f"in_degree_b{PRIMARY_THRESHOLD}": B.in_degree(r),
                f"out_degree_b{PRIMARY_THRESHOLD}": B.out_degree(r),
                "in_strength": round(s_in, 2),        # incoming students per year
                "out_strength": round(s_out, 2),      # outgoing students per year
                # (in - out) / (in + out): +1 only receives, -1 only sends (H1 dependent variable)
                "net_balance": round((s_in - s_out) / (s_in + s_out), 4) if s_in + s_out else np.nan,
                "pagerank": pagerank[r],
                "authority": authorities[r],
                "hub": hubs[r],
                "betweenness": betweenness[r],
            }
        )
    return G, B, pd.DataFrame(rows)


def reciprocity(G, B):
    """Binary reciprocity of the weighted network (any flow) and of the binary network, with the
    Garlaschelli-Loffredo correction (rho > 0: more reciprocated than chance), and weighted
    reciprocity (share of the flow balanced by the flow in the opposite direction)."""
    out = {}
    for label, H in (("any_flow", G), (f"b{PRIMARY_THRESHOLD}", B)):
        r = nx.overall_reciprocity(H)
        density = H.number_of_edges() / common.feasible_pairs(list(H.nodes()))
        out[f"reciprocity_{label}"] = r
        out[f"rho_{label}"] = (r - density) / (1 - density)
    balanced = sum(min(w, G[v][u]["weight"]) for u, v, w in G.edges(data="weight") if G.has_edge(v, u))
    out["reciprocity_weighted"] = balanced / G.size(weight="weight")
    return out


def main():
    common.output_dirs()
    tables, summary, tops = {}, [], []

    for period in PERIODS:
        G, B, t = node_measures(period)
        tables[period] = t
        t.to_csv(common.TABLES_DIR / f"centrality_{period}.csv", index=False)

        active = t[(t.in_strength + t.out_strength) > 0]
        uk = t[t.country == "UK"]
        row = {
            "period": period,
            "students_per_year": round(t.in_strength.sum()),
            "edges_weighted": G.number_of_edges(),
            f"edges_b{PRIMARY_THRESHOLD}": B.number_of_edges(),
            "mean_partners": round(active.out_degree.mean(), 1),
            "gini_in_strength": round(common.gini(active.in_strength), 3),
            "gini_out_strength": round(common.gini(active.out_strength), 3),
            "top10pct_share_in": round(common.top_share(active.in_strength, 0.10), 3),
            "top10pct_share_out": round(common.top_share(active.out_strength, 0.10), 3),
            **{k: round(v, 3) for k, v in reciprocity(G, B).items()},
            "UK_share_in": round(uk.in_strength.sum() / t.in_strength.sum(), 3),
            "UK_share_out": round(uk.out_strength.sum() / t.out_strength.sum(), 3),
            "UK_regions_in_top50_authority": int(uk.region.isin(t.nlargest(50, "authority").region).sum()),
        }
        summary.append(row)

        for measure in ("in_strength", "out_strength", "net_balance", "pagerank", "authority", "hub", "betweenness"):
            # net balance: only regions with at least 100 students/year, otherwise tiny regions dominate
            pool = t[(t.in_strength + t.out_strength) >= 100] if measure == "net_balance" else t
            for rank, (_, r) in enumerate(pool.nlargest(TOP_N, measure).iterrows(), start=1):
                tops.append(
                    {"period": period, "measure": measure, "rank": rank, "region": r.region,
                     "name": r["name"], "value": r[measure]}
                )
            if measure == "net_balance":
                for rank, (_, r) in enumerate(pool.nsmallest(TOP_N, measure).iterrows(), start=1):
                    tops.append(
                        {"period": period, "measure": "net_balance_lowest", "rank": rank,
                         "region": r.region, "name": r["name"], "value": r[measure]}
                    )

    summary = pd.DataFrame(summary)
    summary.to_csv(common.TABLES_DIR / "centrality_summary.csv", index=False)
    tops = pd.DataFrame(tops)
    tops.to_csv(common.TABLES_DIR / "top_regions.csv", index=False)

    # Rank stability: do the same regions stay central from one period to the next?
    stability = []
    for measure in ("in_strength", "out_strength", "pagerank", "authority", "hub", "betweenness", "net_balance"):
        for a, b in (("pre_covid", "covid"), ("covid", "post_covid"), ("pre_covid", "post_covid")):
            x = tables[a].set_index("region")[measure]
            y = tables[b].set_index("region")[measure].reindex(x.index)
            ok = x.notna() & y.notna()
            stability.append(
                {"measure": measure, "from": a, "to": b, "spearman": round(spearmanr(x[ok], y[ok])[0], 3)}
            )
    stability = pd.DataFrame(stability)
    stability.to_csv(common.TABLES_DIR / "rank_stability.csv", index=False)

    # --- Report ------------------------------------------------------------------
    log.title("MEASURES 1-4: CENTRALITY ON THE THREE PERIOD NETWORKS")
    log("Weighted network: weight = average students/year. Binary network: edge if >= "
        f"{PRIMARY_THRESHOLD} students/year.")
    log("Densities for rho use only feasible pairs (regions in different countries).")
    log("\nNETWORK-LEVEL SUMMARY")
    log(summary.set_index("period").T.to_string())

    names = {
        "in_strength": "IN-STRENGTH (incoming students/year): main destinations",
        "out_strength": "OUT-STRENGTH (outgoing students/year): main senders",
        "net_balance": "NET BALANCE, highest (regions with >= 100 students/year): net receivers",
        "net_balance_lowest": "NET BALANCE, lowest (regions with >= 100 students/year): net senders",
        "pagerank": "PAGERANK (weighted)",
        "authority": "HITS AUTHORITY: destinations chosen by the best hubs",
        "hub": "HITS HUB: regions sending students to the best authorities",
        "betweenness": "BETWEENNESS (weighted, edge length = 1/students)",
    }
    for measure, label in names.items():
        log.title(label)
        wide = {}
        for period in PERIODS:
            sel = tops[(tops.period == period) & (tops.measure == measure)]
            fmt = "{:.4f}" if measure in ("pagerank", "authority", "hub", "betweenness", "net_balance", "net_balance_lowest") else "{:,.0f}"
            wide[period] = [f"{r.region} {str(r['name'])[:22]} ({fmt.format(r.value)})" for _, r in sel.iterrows()]
        log(pd.DataFrame(wide, index=range(1, TOP_N + 1)).to_string())

    log.title("RANK STABILITY BETWEEN PERIODS (Spearman correlation over all regions)")
    log(stability.pivot(index="measure", columns=["from", "to"], values="spearman").to_string())
    log.save()


if __name__ == "__main__":
    main()