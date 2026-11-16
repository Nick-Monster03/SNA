"""
03_build_binary_networks.py - Generates the binary (unweighted) versions of the period networks.

In the binary version, a directed edge exists (1) or does not exist (0): it is kept only if
there were, on average, at least THRESHOLD students/year during that period. These networks are
used for unweighted measures (k-core, clustering, small-world, triad census, etc.).

Run AFTER 01_build_networks.py, from the project root directory:
    python src/03_build_binary_networks.py

Reads:
  04_data/networks/periods/network_<period>.csv
  04_data/networks/metadata/regions.csv

Outputs (saved in 04_data/networks/):
  binary/network_<period>_thresh<N>.csv   (columns: origin, destination)
                                          for both the primary and robustness thresholds
  logs/binary_networks_report.txt         summary table (for the report Data section)
"""

from pathlib import Path

import networkx as nx
import pandas as pd

# =============================================================================
# CONFIGURATION
# =============================================================================
NETWORKS_DIR = Path("04_data/networks")
PERIODS_DIR = NETWORKS_DIR / "periods"
METADATA_DIR = NETWORKS_DIR / "metadata"
BINARY_DIR = NETWORKS_DIR / "binary"
LOGS_DIR = NETWORKS_DIR / "logs"

PERIODS = ["pre_covid", "covid", "post_covid"]
PRIMARY_THRESHOLD = 5     # main choice: at least 5 students/year (see threshold_checks.csv)
CONTROL_THRESHOLD = 3     # secondary threshold, for robustness check
# =============================================================================

log_lines = []


def write_log(text=""):
    print(text)
    log_lines.append(str(text))


def main():
    BINARY_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Clean old binary network files
    for old_file in BINARY_DIR.glob("network_*.csv"):
        old_file.unlink()

    n_regions = len(pd.read_csv(METADATA_DIR / "regions.csv"))
    write_log(
        f"Binary networks: an edge is kept if it has on average at least N students/year "
        f"(percentages over all {n_regions} regions)\n"
    )
    write_log(
        f"{'network':<12} {'thresh':>6} {'regions':>8} {'edges':>7} {'density':>8} "
        f"{'students kept':>15} {'connected regions':>18}"
    )

    for threshold in (PRIMARY_THRESHOLD, CONTROL_THRESHOLD):
        for period in PERIODS:
            net = pd.read_csv(PERIODS_DIR / f"network_{period}.csv")
            kept = net[net["students"] >= threshold]
            kept[["origin", "destination"]].to_csv(
                BINARY_DIR / f"network_{period}_thresh{threshold}.csv", index=False
            )

            G = nx.from_pandas_edgelist(kept, "origin", "destination", create_using=nx.DiGraph)
            giant_wcc = max((len(c) for c in nx.weakly_connected_components(G)), default=0)
            write_log(
                f"{period:<12} {threshold:>6} {G.number_of_nodes():>8} {G.number_of_edges():>7,} "
                f"{nx.density(G):>8.4f} {kept['students'].sum() / net['students'].sum():>14.1%} "
                f"{giant_wcc / n_regions:>17.1%}"
            )
        write_log()

    write_log(
        f"Files saved in {BINARY_DIR}/: network_<period>_thresh{PRIMARY_THRESHOLD}.csv (primary) and "
        f"network_<period>_thresh{CONTROL_THRESHOLD}.csv (robustness check)"
    )
    (LOGS_DIR / "binary_networks_report.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()