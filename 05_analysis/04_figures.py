"""
04_figures.py - Figures for the report, drawn from the tables written by 01-03.

Run from the project root directory, AFTER 01_centrality.py, 02_structure.py, 03_homophily.py:
    python 05_analysis/04_figures.py

Outputs (05_analysis/figures/, PNG at 300 dpi + PDF for the report):
  fig1_core_periphery_map      measure 5: core / periphery / below-threshold regions, 3 periods
  fig2_communities_map         measure 6: Louvain communities, 3 periods
  fig3_net_balance_map         measure 1: net balance (in - out) / (in + out), 3 periods
  fig4_degree_distribution     measure 9: complementary cumulative distributions (log-log)
  fig5_triad_census            measure 10: observed / expected triads (U|MAN)
"""

import json

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PatchCollection
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import Patch, Polygon
from shapely.geometry import shape

import common
from common import PERIODS, TABLES_DIR

# --- Style (reference palette of the dataviz guidelines; validated for colour-blind safety) ----
SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, NO_DATA = "#e1e0d9", "#c3c2b7", "#f0efec"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]          # blue, orange, aqua (first three slots)
PERIOD_COLOR = dict(zip(PERIODS, SERIES))
PERIOD_LABEL = {"pre_covid": "Pre-Covid 2018–19", "covid": "Covid 2020–21", "post_covid": "Post-Covid 2022–23"}
LON, LAT = (-11, 45), (34, 71.5)                       # mainland extent (overseas regions left out)

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 9, "axes.edgecolor": AXIS, "axes.labelcolor": INK_2,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.titlesize": 10, "axes.titlecolor": INK,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "legend.frameon": False, "axes.spines.top": False, "axes.spines.right": False,
})


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(common.FIGURES_DIR / f"{name}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  figures/{name}.png / .pdf")


# -----------------------------------------------------------------------------
# Maps
# -----------------------------------------------------------------------------
def load_shapes():
    data = json.loads(common.BOUNDARIES_FILE.read_text(encoding="utf-8"))
    return {
        f["properties"]["NUTS_ID"]: shape(f["geometry"])
        for f in data["features"] if f["properties"]["LEVL_CODE"] == 2
    }


def polygons(geom):
    parts = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    return [np.asarray(p.exterior.coords) for p in parts]


def draw_map(ax, shapes, colors, title):
    """colors: {network region: colour}. Regions outside the networks are drawn in light grey."""
    ax.set_facecolor(SURFACE)
    covered = {part for region in colors for part in region.split("+")}
    background = [Polygon(c) for code, g in shapes.items() if code not in covered for c in polygons(g)]
    ax.add_collection(PatchCollection(background, facecolor=NO_DATA, edgecolor="white", linewidth=0.2))
    patches, faces = [], []
    for region, color in colors.items():
        for part in region.split("+"):
            for c in polygons(shapes[part]):
                patches.append(Polygon(c))
                faces.append(color)
    ax.add_collection(PatchCollection(patches, facecolor=faces, edgecolor="white", linewidth=0.25))
    ax.set_xlim(*LON)
    ax.set_ylim(*LAT)
    ax.set_aspect(1 / np.cos(np.radians(52)))
    ax.set_axis_off()
    ax.set_title(title, loc="left")


def map_triptych(name, color_of, legend, suptitle, colorbar=None):
    shapes = load_shapes()
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.9))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.86, bottom=0.10 if colorbar is None else 0.16, wspace=0.03)
    for ax, period in zip(axes, PERIODS):
        draw_map(ax, shapes, color_of(period), PERIOD_LABEL[period])
    if legend:
        fig.legend(handles=legend, loc="lower center", ncol=len(legend), bbox_to_anchor=(0.5, 0.0),
                   handlelength=1.2, columnspacing=1.6, labelcolor=INK_2)
    if colorbar:
        colorbar(fig, axes)
    fig.suptitle(suptitle, x=0.01, ha="left", color=INK, fontsize=11)
    save(fig, name)


def fig_core_periphery():
    def color_of(period):
        t = pd.read_csv(TABLES_DIR / f"core_{period}.csv")
        return {
            r.region: (SERIES[0] if r.cp_core else ("#b7d3f6" if r.degree_undirected > 0 else "white"))
            for r in t.itertuples()
        }
    legend = [
        Patch(facecolor=SERIES[0], label="Core"),
        Patch(facecolor="#b7d3f6", label="Periphery"),
        Patch(facecolor="white", edgecolor=AXIS, label="No edge ≥ 5 students/year"),
        Patch(facecolor=NO_DATA, label="Not in the network"),
    ]
    map_triptych("fig1_core_periphery_map", color_of, legend,
                 "Core–periphery partition of the binary networks (Borgatti–Everett)")


def fig_communities():
    tables = {p: pd.read_csv(TABLES_DIR / f"communities_{p}.csv") for p in PERIODS}
    # Align the community numbers of every period to the pre-Covid ones (largest overlap)
    ref = tables["pre_covid"].set_index("region").community
    aligned = {}
    for p, t in tables.items():
        lab = t.set_index("region").community
        mapping, used = {}, set()
        sizes = lab[lab > 0].value_counts()
        for c in sizes.index:
            overlap = ref[lab[lab == c].index].value_counts()
            overlap = overlap[[i for i in overlap.index if i not in used and i > 0]]
            mapping[c] = overlap.index[0] if len(overlap) else 100 + c
            used.add(mapping[c])
        aligned[p] = lab.map(lambda c: mapping.get(c, 0))
    # Name communities by their countries with most regions (pre-Covid composition)
    names = {}
    for c in sorted(set(ref[ref > 0])):
        counts = tables["pre_covid"].query("community == @c").country.value_counts()
        top = sorted(counts.index, key=lambda k: (-counts[k], k))[:3]
        names[c] = f"{', '.join(top)} …"
    palette = {1: SERIES[0], 2: SERIES[1], 3: SERIES[2]}
    other = MUTED

    def color_of(period):
        return {r: palette.get(c, other if c else "white") for r, c in aligned[period].items()}
    legend = [Patch(facecolor=palette[c], label=f"Community {c} ({names[c]})") for c in (1, 2, 3)]
    if any(c not in palette for p in PERIODS for c in aligned[p] if c > 0):
        legend.append(Patch(facecolor=other, label="Smaller community"))
    map_triptych("fig2_communities_map", color_of, legend,
                 "Communities of the weighted networks (Louvain; colours matched across periods)")


def fig_net_balance():
    cmap = LinearSegmentedColormap.from_list("div", ["#e34948", "#f0efec", "#2a78d6"])
    norm = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)

    def color_of(period):
        t = pd.read_csv(TABLES_DIR / f"centrality_{period}.csv")
        return {r.region: (cmap(norm(r.net_balance)) if pd.notna(r.net_balance) else "white") for r in t.itertuples()}

    def colorbar(fig, axes):
        sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
        cax = fig.add_axes([0.25, 0.09, 0.5, 0.025])
        cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
        cb.set_label("Net balance = (incoming − outgoing) / (incoming + outgoing)   ·   red: net sender, blue: net receiver",
                     color=INK_2)
        cb.outline.set_visible(False)
    map_triptych("fig3_net_balance_map", color_of, None, "Net balance of students by region", colorbar)


# -----------------------------------------------------------------------------
# Charts
# -----------------------------------------------------------------------------
def ccdf(values):
    x = np.sort(np.asarray(values, dtype=float))
    x = x[x > 0]
    return x, 1 - np.arange(len(x)) / len(x)


def fig_degree_distribution():
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    specs = [
        (f"in_degree_b{common.PRIMARY_THRESHOLD}", "In-degree (binary network, ≥ 5 students/year)"),
        ("in_strength", "In-strength (incoming students/year)"),
    ]
    for ax, (column, label) in zip(axes, specs):
        for period in PERIODS:
            t = pd.read_csv(TABLES_DIR / f"centrality_{period}.csv")
            x, y = ccdf(t[column])
            ax.plot(x, y, color=PERIOD_COLOR[period], linewidth=2, label=PERIOD_LABEL[period])
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(label)
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}" if v >= 1 else f"{v:g}"))
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.grid(True, which="major", color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Share of regions with value ≥ x")
    axes[0].legend(loc="lower left", labelcolor=INK_2)
    fig.suptitle("Degree and strength distributions (complementary cumulative, log–log)",
                 x=0.01, ha="left", color=INK, fontsize=11)
    fig.tight_layout()
    save(fig, "fig4_degree_distribution")


def fig_triads():
    t = pd.read_csv(TABLES_DIR / "triad_census.csv")
    order = ["003", "012", "102", "021D", "021U", "021C", "111D", "111U",
             "030T", "030C", "201", "120D", "120U", "120C", "210", "300"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    y = np.arange(len(order))
    offsets = dict(zip(PERIODS, (-0.22, 0, 0.22)))
    for period in PERIODS:
        sel = t[t.period == period].set_index("triad").reindex(order)
        ax.scatter(sel.ratio, y + offsets[period], s=28, color=PERIOD_COLOR[period],
                   edgecolor=SURFACE, linewidth=1, label=PERIOD_LABEL[period], zorder=3)
    ax.axvline(1, color=AXIS, linewidth=1, zorder=1)
    ax.set_xscale("log")
    ax.set_yticks(y, order)
    ax.invert_yaxis()
    ax.set_xlabel("Observed / expected count (log scale; 1 = as in random graphs with the same dyad census)")
    ax.grid(True, axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_xticks([0.5, 1, 2, 5, 10, 20], ["0.5", "1", "2", "5", "10", "20"])
    ax.minorticks_off()
    ax.legend(loc="upper right", labelcolor=INK_2)
    ax.set_title("Triad census of the binary networks vs. U|MAN random graphs", loc="left", fontsize=11)
    fig.tight_layout()
    save(fig, "fig5_triad_census")


def main():
    common.output_dirs()
    fig_core_periphery()
    fig_communities()
    fig_net_balance()
    fig_degree_distribution()
    fig_triads()


if __name__ == "__main__":
    main()