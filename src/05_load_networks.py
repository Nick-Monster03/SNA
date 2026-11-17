"""
load_networks.py - Loads the Erasmus+ networks into networkx and checks the numbers
(roadmap Phase 2, task B+C: "load the networks in the chosen tool and check nodes, edges,
total students").

Two uses:

1) As a script, from the project root directory (run AFTER src/01-04):
       python 05_analysis/load_networks.py            # load everything and run the checks
       python 05_analysis/load_networks.py --gexf     # also export the period networks for Gephi

   Outputs:
     04_data/networks/logs/load_check_report.txt      full text log of the checks
     04_data/networks/gephi/*.gexf                    only with --gexf

2) As a module, from the other analysis scripts in 05_analysis/:
       from load_networks import load_period, load_binary, load_year

       G = load_period("pre_covid")                    # weighted, directed
       B = load_binary("covid")                        # binary, directed, threshold 5
       U = load_binary("covid", directed=False)        # binary, undirected (small-world)
       Y = load_year(2023)                             # weighted, directed, one year

What every graph contains:
  - ALL 319 regions as nodes, including those with no edges in that network (isolates), so that
    the three periods are always compared on the same node set. Pass all_regions=False to keep
    only the regions with at least one edge (this is what the logs of src/02 and src/03 count).
  - node attributes: name, country, gdp_pre_covid, gdp_covid, gdp_post_covid
    (a GDP attribute is simply absent for the 43 regions without GDP: UK, IS, LI).
  - weighted graphs only, edge attributes: weight = students (annual average for the periods),
    distance = 1 / weight (to be used as edge length for betweenness, measure 4).
  - graph attributes: G.graph["name"], G.graph["kind"] and, for binary graphs, G.graph["threshold"].
"""

import re
import sys
from pathlib import Path

import networkx as nx
import pandas as pd

# =============================================================================
# CONFIGURATION
# =============================================================================
ROOT = Path(__file__).resolve().parents[1]  # project root, so the module works from any directory
NETWORKS_DIR = ROOT / "04_data" / "networks"
YEARLY_DIR = NETWORKS_DIR / "yearly"
PERIODS_DIR = NETWORKS_DIR / "periods"
BINARY_DIR = NETWORKS_DIR / "binary"
METADATA_DIR = NETWORKS_DIR / "metadata"
LOGS_DIR = NETWORKS_DIR / "logs"
GEPHI_DIR = NETWORKS_DIR / "gephi"

PERIODS = {
    "pre_covid": (2018, 2019),
    "covid": (2020, 2021),
    "post_covid": (2022, 2023),
}
PRIMARY_THRESHOLD = 5   # main binary networks (decision 8)
CONTROL_THRESHOLD = 3   # robustness check
# =============================================================================

log_lines = []


def write_log(text=""):
    print(text)
    log_lines.append(str(text))


# -----------------------------------------------------------------------------
# LOADING
# -----------------------------------------------------------------------------
def load_regions():
    """Node table: region, country and, if src/04 has been run, name and GDP per period."""
    regions = pd.read_csv(METADATA_DIR / "regions.csv")
    attributes_file = METADATA_DIR / "region_attributes.csv"
    if attributes_file.exists():
        attributes = pd.read_csv(attributes_file).drop(columns=["country", "gdp_note"], errors="ignore")
        regions = regions.merge(attributes, on="region", how="left", validate="one_to_one")
    return regions


def _build_graph(edges, name, kind, weighted, directed=True, all_regions=True, **graph_attributes):
    G = nx.DiGraph(name=name, kind=kind, **graph_attributes)
    regions = load_regions()

    if all_regions:
        G.add_nodes_from(regions["region"])
    if weighted:
        for origin, destination, students in edges[["origin", "destination", "students"]].itertuples(index=False):
            G.add_edge(origin, destination, weight=float(students), distance=1.0 / float(students))
    else:
        G.add_edges_from(edges[["origin", "destination"]].itertuples(index=False, name=None))

    # Node attributes; missing values (e.g., GDP of UK regions) are left out instead of stored as NaN
    for row in regions.to_dict("records"):
        region = row.pop("region")
        if region in G:
            G.nodes[region].update({k: v for k, v in row.items() if pd.notna(v)})

    if not directed:
        # Undirected version: an edge exists if at least one direction exists (decision 9)
        if weighted:
            raise ValueError("The undirected version is defined only for the binary networks (decision 9).")
        G = G.to_undirected()
    return G


def load_period(period, all_regions=True):
    """Weighted directed network of a period ('pre_covid', 'covid', 'post_covid').
    weight = average students per year in the period."""
    if period not in PERIODS:
        raise ValueError(f"Unknown period '{period}'. Choose one of: {', '.join(PERIODS)}")
    edges = pd.read_csv(PERIODS_DIR / f"network_{period}.csv")
    return _build_graph(edges, period, "weighted", weighted=True, all_regions=all_regions)


def load_year(year, all_regions=True):
    """Weighted directed network of a single year (2016-2023). weight = students in that year."""
    edges = pd.read_csv(YEARLY_DIR / f"network_{int(year)}.csv")
    return _build_graph(edges, str(year), "weighted", weighted=True, all_regions=all_regions)


def load_binary(period, threshold=PRIMARY_THRESHOLD, directed=True, all_regions=True):
    """Binary network of a period: an edge exists if it has at least `threshold` students/year.
    directed=False gives the undirected version used for clustering and small-world."""
    if period not in PERIODS:
        raise ValueError(f"Unknown period '{period}'. Choose one of: {', '.join(PERIODS)}")
    file = BINARY_DIR / f"network_{period}_thresh{threshold}.csv"
    if not file.exists():
        available = sorted(p.stem.split("thresh")[1] for p in BINARY_DIR.glob(f"network_{period}_thresh*.csv"))
        raise FileNotFoundError(
            f"{file.name} not found. Thresholds available: {', '.join(available) or 'none'} "
            f"(binary networks are built by src/03_build_binary_networks.py)"
        )
    edges = pd.read_csv(file)
    return _build_graph(
        edges,
        f"{period}_thresh{threshold}",
        "binary",
        weighted=False,
        directed=directed,
        all_regions=all_regions,
        threshold=threshold,
    )


def available_years():
    return sorted(int(p.stem.split("_")[1]) for p in YEARLY_DIR.glob("network_20*.csv"))


def load_all():
    """All the networks in a dictionary: {'periods': {...}, 'binary': {(period, threshold): ...},
    'yearly': {...}}."""
    return {
        "periods": {p: load_period(p) for p in PERIODS},
        "binary": {
            (p, t): load_binary(p, t) for p in PERIODS for t in (PRIMARY_THRESHOLD, CONTROL_THRESHOLD)
        },
        "yearly": {y: load_year(y) for y in available_years()},
    }


# -----------------------------------------------------------------------------
# CHECKS
# -----------------------------------------------------------------------------
def _active_nodes(G):
    return [n for n, d in G.degree() if d > 0]


def _expected_from_build_log():
    """Numbers reported by src/01_build_networks.py: {name: (regions, edges, students)}."""
    file = LOGS_DIR / "build_log.txt"
    if not file.exists():
        return {}
    pattern = re.compile(r"network_(\w+)\.csv.*?(\d+) regions\s+([\d,]+) edges\s+([\d,]+) students")
    expected = {}
    for line in file.read_text(encoding="utf-8").splitlines():
        if m := pattern.search(line):
            expected[m.group(1)] = tuple(int(g.replace(",", "")) for g in m.groups()[1:])
    return expected


def _expected_from_threshold_checks():
    """Numbers reported by src/02_verify_data.py: {(period, threshold): row}."""
    file = LOGS_DIR / "threshold_checks.csv"
    if not file.exists():
        return {}
    table = pd.read_csv(file)
    return {(r["network"], int(r["threshold"])): r for _, r in table.iterrows()}


def _structural_problems(G, regions):
    """Problems that would mean the network was loaded or built incorrectly."""
    problems = []
    unknown = set(G) - set(regions)
    if unknown:
        problems.append(f"{len(unknown)} nodes not in regions.csv: {sorted(unknown)[:5]}")
    loops = nx.number_of_selfloops(G)
    if loops:
        problems.append(f"{loops} self-loops")
    domestic = sum(1 for u, v in G.edges() if u[:2] == v[:2])
    if domestic:
        problems.append(f"{domestic} edges within the same country")
    if G.graph["kind"] == "weighted":
        bad = sum(1 for _, _, w in G.edges(data="weight") if not w > 0)
        if bad:
            problems.append(f"{bad} edges with weight <= 0")
    return problems


def run_checks():
    """Loads every network and compares the numbers with the files and with the pipeline logs.
    Returns the number of failed checks."""
    regions = load_regions()["region"].tolist()
    n_regions = len(regions)
    build_log = _expected_from_build_log()
    thresholds = _expected_from_threshold_checks()
    failures = []

    def verdict(name, got, expected, problems):
        """Compares the loaded numbers with the log; returns the text for the 'check' column."""
        issues = list(problems)
        if expected is None:
            note = "no log"
        else:
            wrong = [f"{k}: loaded {g:,} vs log {e:,}" for k, g, e in zip(("regions", "edges", "students"), got, expected) if g != e]
            issues += wrong
            note = "= log"
        if issues:
            failures.append(f"{name}: " + "; ".join(issues))
            return "PROBLEM"
        return f"OK ({note})"

    write_log("=" * 92)
    write_log("LOAD CHECK: networks loaded in networkx vs numbers in the pipeline logs")
    write_log(f"networkx {nx.__version__} - node set: {n_regions} regions in {len({r[:2] for r in regions})} countries")
    write_log("'active' = regions with at least one edge; 'isolates' = regions in the node set with no edges")
    write_log("=" * 92)

    # --- Yearly networks ---------------------------------------------------------
    write_log("\nYEARLY NETWORKS (weighted, directed; weight = students in the year)")
    write_log(f"  {'network':<12} {'nodes':>6} {'active':>7} {'isolates':>9} {'edges':>8} {'students':>10}   check")
    for year in available_years():
        G = load_year(year)
        active = len(_active_nodes(G))
        students = round(G.size(weight="weight"))
        got = (active, G.number_of_edges(), students)
        status = verdict(f"yearly {year}", got, build_log.get(str(year)), _structural_problems(G, regions))
        write_log(
            f"  {year:<12} {G.number_of_nodes():>6} {active:>7} {n_regions - active:>9} "
            f"{G.number_of_edges():>8,} {students:>10,}   {status}"
        )

    # --- Period networks ---------------------------------------------------------
    write_log("\nPERIOD NETWORKS (weighted, directed; weight = average students per year)")
    write_log(f"  {'network':<12} {'nodes':>6} {'active':>7} {'isolates':>9} {'edges':>8} {'stud./year':>10}   check")
    period_graphs = {}
    for period, (a, b) in PERIODS.items():
        G = period_graphs[period] = load_period(period)
        active = len(_active_nodes(G))
        students = round(G.size(weight="weight"))
        got = (active, G.number_of_edges(), students)
        problems = _structural_problems(G, regions)

        # The period network must be exactly the average of its yearly networks
        years = [y for y in range(a, b + 1) if y in available_years()]
        total = {}
        for y in years:
            for u, v, w in load_year(y, all_regions=False).edges(data="weight"):
                total[(u, v)] = total.get((u, v), 0) + w
        mismatched = sum(
            1 for edge, w in total.items() if abs(G.edges[edge]["weight"] - w / len(years)) > 0.006
        ) if set(total) == set(G.edges()) else None
        if mismatched is None:
            problems.append("edges differ from the union of the yearly networks")
        elif mismatched:
            problems.append(f"{mismatched} weights differ from the yearly average")

        status = verdict(f"period {period}", got, build_log.get(period), problems)
        isolates = sorted(set(regions) - set(_active_nodes(G)))
        write_log(
            f"  {period:<12} {G.number_of_nodes():>6} {active:>7} {n_regions - active:>9} "
            f"{G.number_of_edges():>8,} {students:>10,}   {status}"
            + (f"   isolates: {', '.join(isolates)}" if isolates else "")
        )

    # --- Binary networks ---------------------------------------------------------
    write_log("\nBINARY NETWORKS (directed; edge = at least N students/year in the period)")
    write_log(
        f"  {'network':<12} {'thresh':>6} {'nodes':>6} {'active':>7} {'isolates':>9} {'edges':>8} "
        f"{'dens.319':>9} {'dens.active':>11} {'giant WCC':>10} {'undir. edges':>13}   check"
    )
    for threshold in (PRIMARY_THRESHOLD, CONTROL_THRESHOLD):
        for period in PERIODS:
            G = load_binary(period, threshold)
            W = period_graphs[period]
            active_nodes = _active_nodes(G)
            active = len(active_nodes)
            giant = max((len(c) for c in nx.weakly_connected_components(G.subgraph(active_nodes))), default=0)
            density_active = nx.density(G.subgraph(active_nodes))
            problems = _structural_problems(G, regions)

            # The binary network must be exactly the period edges with weight >= threshold
            expected_edges = {(u, v) for u, v, w in W.edges(data="weight") if w >= threshold}
            if set(G.edges()) != expected_edges:
                problems.append("edges differ from the period network filtered at the threshold")

            row = thresholds.get((period, threshold))
            if row is None:
                expected = None
            else:
                expected = (int(row["regions_with_edges"]), int(row["edges"]))
                if round(density_active, 4) != round(float(row["density"]), 4):
                    problems.append(f"density {density_active:.4f} vs log {row['density']}")
                if round(100 * giant / n_regions, 1) != float(row["regions_in_giant_wcc_%"]):
                    problems.append(f"giant WCC {100 * giant / n_regions:.1f}% vs log {row['regions_in_giant_wcc_%']}%")
            status = verdict(
                f"binary {period} thresh{threshold}", (active, G.number_of_edges()), expected, problems
            )
            undirected = load_binary(period, threshold, directed=False)
            write_log(
                f"  {period:<12} {threshold:>6} {G.number_of_nodes():>6} {active:>7} {n_regions - active:>9} "
                f"{G.number_of_edges():>8,} {nx.density(G):>9.4f} {density_active:>11.4f} "
                f"{giant:>10} {undirected.number_of_edges():>13,}   {status}"
            )
        write_log()

    write_log("  dens.319 = density over all 319 regions; dens.active = over the regions with edges only")
    write_log("  (dens.active and giant WCC are the figures reported in logs/threshold_checks.csv)")
    write_log("  undir. edges = edges of the undirected version (at least one direction), used for small-world")

    # --- Node attributes ---------------------------------------------------------
    G = period_graphs["pre_covid"]
    write_log("\nNODE ATTRIBUTES attached to every graph")
    for attribute in ("name", "country", *(f"gdp_{p}" for p in PERIODS)):
        n = sum(1 for _, value in G.nodes(data=attribute) if value is not None)
        write_log(f"  {attribute:<16} present for {n} of {G.number_of_nodes()} regions")

    # --- Summary -----------------------------------------------------------------
    write_log("\n" + "=" * 92)
    if failures:
        write_log(f"RESULT: {len(failures)} PROBLEM(S) FOUND")
        for f in failures:
            write_log(f"  - {f}")
    else:
        write_log("RESULT: all networks loaded correctly; every number matches the pipeline logs.")
    write_log("=" * 92)
    return len(failures)


def export_gexf():
    """Writes the period networks (weighted and primary binary) as .gexf files for Gephi."""
    GEPHI_DIR.mkdir(parents=True, exist_ok=True)
    for period in PERIODS:
        nx.write_gexf(load_period(period), GEPHI_DIR / f"network_{period}.gexf")
        nx.write_gexf(
            load_binary(period), GEPHI_DIR / f"network_{period}_thresh{PRIMARY_THRESHOLD}.gexf"
        )
    write_log(f"\nGephi files saved in {GEPHI_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    n_failures = run_checks()
    if "--gexf" in sys.argv:
        export_gexf()
    (LOGS_DIR / "load_check_report.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(f"\nReport saved to {(LOGS_DIR / 'load_check_report.txt').relative_to(ROOT)}")
    sys.exit(1 if n_failures else 0)