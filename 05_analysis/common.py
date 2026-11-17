"""
common.py - Shared settings and helpers for the analysis scripts in 05_analysis/.

Not meant to be run on its own. The scripts in this folder import it with "import common".
Run every analysis script from the project root directory, e.g.:
    python 05_analysis/01_centrality.py
"""

import importlib
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "05_analysis"
TABLES_DIR = ANALYSIS_DIR / "tables"
FIGURES_DIR = ANALYSIS_DIR / "figures"
REPORTS_DIR = ANALYSIS_DIR / "reports"

# The network loader lives in src/ and its name starts with a digit: import it with importlib
sys.path.insert(0, str(ROOT / "src"))
networks = importlib.import_module("05_load_networks")
load_period = networks.load_period
load_binary = networks.load_binary
load_year = networks.load_year
load_regions = networks.load_regions
PERIODS = list(networks.PERIODS)
PRIMARY_THRESHOLD = networks.PRIMARY_THRESHOLD
CONTROL_THRESHOLD = networks.CONTROL_THRESHOLD
BOUNDARIES_FILE = ROOT / "04_data" / "external" / "NUTS_RG_20M_2016_4326.geojson"

SEED = 42  # one seed for every random step (null models, Louvain), so results are reproducible

# -----------------------------------------------------------------------------
# Country groups, used for homophily (measure 11) and to describe communities (measure 6)
# -----------------------------------------------------------------------------
# Geographic macro-areas: UN M49 geoscheme (unstats.un.org/unsd/methodology/m49).
# M49 places Cyprus and Turkey in Western Asia: they are kept as a separate group.
MACRO_AREA = {
    **dict.fromkeys(["DK", "EE", "FI", "IS", "IE", "LV", "LT", "NO", "SE", "UK"], "Northern"),
    **dict.fromkeys(["AT", "BE", "FR", "DE", "LI", "LU", "NL"], "Western"),
    **dict.fromkeys(["AL", "HR", "EL", "IT", "MT", "ME", "MK", "PT", "RS", "SI", "ES"], "Southern"),
    **dict.fromkeys(["BG", "CZ", "HU", "PL", "RO", "SK"], "Eastern"),
    **dict.fromkeys(["CY", "TR"], "Western Asia"),
}

# Programme membership: older EU members and EFTA, members that joined from 2004, candidates.
# Close to the "more / less developed" blocks found by Batagelj (2025) between countries.
PROGRAMME_GROUP = {
    **dict.fromkeys(
        ["AT", "BE", "DE", "DK", "EL", "ES", "FI", "FR", "IE", "IT", "LU", "NL", "PT", "SE", "UK"],
        "EU-15",
    ),
    **dict.fromkeys(["IS", "LI", "NO"], "EFTA"),
    **dict.fromkeys(
        ["BG", "CY", "CZ", "EE", "HR", "HU", "LT", "LV", "MT", "PL", "RO", "SI", "SK"], "EU-13"
    ),
    **dict.fromkeys(["AL", "ME", "MK", "RS", "TR"], "Candidates"),
}


class Report:
    """Collects the lines printed on screen and saves them to 05_analysis/reports/<name>.txt."""

    def __init__(self, name):
        self.path = REPORTS_DIR / f"{name}.txt"
        self.lines = []

    def __call__(self, text=""):
        print(text)
        self.lines.append(str(text))

    def title(self, text):
        self("\n" + "=" * 90)
        self(text)
        self("=" * 90)

    def save(self):
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        print(f"\nReport saved to {self.path.relative_to(ROOT)}")


def output_dirs():
    for d in (TABLES_DIR, FIGURES_DIR, REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def feasible_pairs(nodes):
    """Number of ordered pairs of distinct regions in DIFFERENT countries.
    Same-country pairs can never have an edge (decision 4), so they are structural zeros:
    densities and null models are also computed over the feasible pairs only."""
    countries = np.array([n[:2] for n in nodes])
    _, sizes = np.unique(countries, return_counts=True)
    n = len(nodes)
    return int(n * (n - 1) - (sizes * (sizes - 1)).sum())


def gini(values):
    """Gini coefficient (0 = all equal, 1 = everything in one region)."""
    x = np.sort(np.asarray(values, dtype=float))
    if x.sum() == 0:
        return 0.0
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def top_share(values, share):
    """Share of the total held by the top `share` fraction of regions (e.g. 0.10 = top 10%)."""
    x = np.sort(np.asarray(values, dtype=float))[::-1]
    k = max(1, int(round(share * len(x))))
    return float(x[:k].sum() / x.sum())