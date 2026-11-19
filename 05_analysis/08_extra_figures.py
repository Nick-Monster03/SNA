"""
08_extra_figures.py - Three extra figures for the report (no new analysis: only drawing).

Run from the project root directory, AFTER 01-07:
    python 05_analysis/08_extra_figures.py

Outputs (05_analysis/figures/, PNG at 300 dpi + PDF for the report):
  fig6_network_map     the weighted pre-Covid network on the map: one dot per region (size = students
                       received per year), only the strongest flows (width = students per year)
  fig7_uk_yearly       H3: arrivals and departures 2016-2023, United Kingdom vs rest of the network,
                       index 2019 = 100 (from tables/h3_uk_yearly.csv)
  fig8_h1_scatter      H1: net balance vs GDP per capita, Turkish regions highlighted, with the
                       slopes of tables/h1_tests.csv (all regions vs without Turkey)

Data used (all already in the repository):
  04_data/networks/periods/network_<period>.csv, 04_data/networks/metadata/region_attributes.csv,
  04_data/external/NUTS_RG_20M_2016_4326.geojson, tables/h3_uk_yearly.csv, tables/h1_data.csv,
  tables/h1_tests.csv.
Region centres follow the same rule as src/04_prepare_attributes.py (centroid of the 2016
boundaries, or a representative point if the centroid falls outside the region).
"""

import importlib

import matplotlib
from matplotlib.lines import Line2D

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import patheffects
from matplotlib.patches import FancyArrowPatch
from shapely.ops import unary_union

import common
from common import TABLES_DIR

# Same style, palette and map helpers as the other figures
F = importlib.import_module("04_figures")
SURFACE, INK, INK_2, MUTED, AXIS, GRID = F.SURFACE, F.INK, F.INK_2, F.MUTED, F.AXIS, F.GRID
BLUE, ORANGE, AQUA = F.SERIES
NETWORK_DIR = common.ROOT / "04_data" / "networks"

# --- Settings ------------------------------------------------------------------------------
MAP_PERIOD = "pre_covid"   # network drawn in fig6 (last "normal" period)
TOP_FLOWS = 150            # number of strongest directed flows drawn in fig6
H1_PERIOD = "pre_covid"    # period drawn in fig8
LABELS = 8                 # fig6: name the regions with the most arrivals


# -----------------------------------------------------------------------------
# Fig. 6 - the network on the map
# -----------------------------------------------------------------------------
def region_centres(shapes, regions):
    centres = {}
    for reg in regions:
        geom = unary_union([shapes[p] for p in reg.split("+") if p in shapes])
        point = geom.centroid if geom.centroid.within(geom) else geom.representative_point()
        centres[reg] = (point.x, point.y)
    return centres


def fig_network_map():
    shapes = F.load_shapes()
    edges = pd.read_csv(NETWORK_DIR / "periods" / f"network_{MAP_PERIOD}.csv")
    attrs = pd.read_csv(NETWORK_DIR / "metadata" / "region_attributes.csv").set_index("region")
    regions = attrs.index.tolist()
    xy = region_centres(shapes, regions)
    arrivals = edges.groupby("destination").students.sum().reindex(regions, fill_value=0)

    top = edges.nlargest(TOP_FLOWS, "students")
    share = top.students.sum() / edges.students.sum()

    fig, ax = plt.subplots(figsize=(8.2, 7.4))
    # background: all regions in light grey
    F.draw_map(ax, shapes, {r: "#eceae4" for r in regions}, "")

    # flows: curved so that A->B and B->A do not overlap; width proportional to students
    smax = top.students.max()
    for e in top.sort_values("students").itertuples():
        (x0, y0), (x1, y1) = xy[e.origin], xy[e.destination]
        w = 0.25 + 2.8 * (e.students / smax) ** 0.75
        ax.add_patch(FancyArrowPatch(
            (x0, y0), (x1, y1), connectionstyle="arc3,rad=0.2", arrowstyle="-|>",
            mutation_scale=3 + 2 * w, lw=w, color=ORANGE, alpha=0.4, zorder=3,
            shrinkA=2, shrinkB=4))

    # nodes: area proportional to students received per year
    size = 2 + 220 * arrivals / arrivals.max()
    ax.scatter([xy[r][0] for r in regions], [xy[r][1] for r in regions], s=size.values,
               color=BLUE, edgecolor="white", linewidth=0.4, zorder=4)

    placed = []
    for r in arrivals.nlargest(LABELS).index:
        name = attrs.loc[r, "name"].split(" + ")[0].split("/")[0]
        x, y = xy[r]
        clash = any(abs(y - py) < 1.2 and abs(x - px) < 7 for px, py in placed)
        offset = (5, -11) if clash else (5, 4)
        ax.annotate(name, (x, y), xytext=offset, textcoords="offset points", fontsize=7,
                    color=INK, zorder=5, fontweight="bold",
                    path_effects=[patheffects.withStroke(linewidth=2.5, foreground=SURFACE)])
        placed.append((x, y))

    legend = [
        Line2D([], [], marker="o", ls="", color=BLUE, markersize=8, label="Region (size = students received)"),
        Line2D([], [], color=ORANGE, lw=2.5, label=f"Top {TOP_FLOWS} flows (width = students/year)"),
    ]
    ax.legend(handles=legend, loc="lower left", fontsize=8, labelcolor=INK_2)
    ax.set_title(f"{F.PERIOD_LABEL[MAP_PERIOD]}: the {TOP_FLOWS} strongest flows "
                 f"({share:.0%} of all students)", loc="left", fontsize=10)
    F.save(fig, "fig6_network_map")


# -----------------------------------------------------------------------------
# Fig. 7 - United Kingdom year by year (H3)
# -----------------------------------------------------------------------------
def fig_uk_yearly():
    t = pd.read_csv(TABLES_DIR / "h3_uk_yearly.csv")
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    panels = [("incoming", "Arrivals"), ("outgoing", "Departures")]
    for ax, (kind, title) in zip(axes, panels):
        ax.axvspan(2019.5, 2021.5, color=GRID, alpha=0.6, lw=0)
        ax.text(2020.5, 122, "Covid", ha="center", fontsize=8, color=MUTED)
        ax.axvline(2021.67, color=AXIS, lw=1, ls="--")
        ax.text(2021.75, 122, "Turing scheme\n(Sep 2021)", fontsize=7, color=MUTED, va="top")
        ax.axhline(100, color=AXIS, lw=0.8)
        ax.plot(t.year, t[f"index_rest_{kind}"], marker="o", ms=4, color=BLUE, lw=2,
                label="Rest of the network")
        ax.plot(t.year, t[f"index_uk_{kind}"], marker="o", ms=4, color=ORANGE, lw=2,
                label="United Kingdom")
        last = t.iloc[-1]
        ax.annotate(f"{last[f'index_uk_{kind}']:.0f}", (last.year, last[f"index_uk_{kind}"]),
                    xytext=(6, -2), textcoords="offset points", fontsize=8, color=ORANGE)
        ax.set_title(title, loc="left")
        ax.set_xticks(t.year)
        ax.set_ylim(0, 125)
        ax.grid(axis="y", color=GRID, lw=0.6)
    axes[0].set_ylabel("Students (2019 = 100)")
    axes[0].legend(loc="lower left", fontsize=8, labelcolor=INK_2)
    fig.suptitle("United Kingdom vs rest of the network, 2016–2023", x=0.01, ha="left",
                 color=INK, fontsize=11)
    fig.tight_layout()
    F.save(fig, "fig7_uk_yearly")


# -----------------------------------------------------------------------------
# Fig. 8 - GDP and net balance (H1)
# -----------------------------------------------------------------------------
def fig_h1_scatter():
    d = pd.read_csv(TABLES_DIR / "h1_data.csv")
    d = d[d.period == H1_PERIOD].dropna(subset=["log_gdp", "net_balance"])
    tests = pd.read_csv(TABLES_DIR / "h1_tests.csv").set_index(["period", "model"])
    turkey = d.country == "TR"

    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    ax.axhline(0, color=AXIS, lw=0.8)
    ax.scatter(np.exp(d.log_gdp[~turkey]), d.net_balance[~turkey], s=14, color=BLUE, alpha=0.7,
               edgecolor="white", linewidth=0.3, label="Other regions")
    ax.scatter(np.exp(d.log_gdp[turkey]), d.net_balance[turkey], s=16, color=ORANGE, alpha=0.9,
               edgecolor="white", linewidth=0.3, label="Turkish regions")

    # regression lines with the slopes of h1_tests.csv (OLS: the line passes through the means)
    for model, sub, style, label in [
        ("M1_all", d, "--", "All regions"),
        ("M2_no_turkey", d[~turkey], "-", "Without Turkey"),
    ]:
        row = tests.loc[(H1_PERIOD, model)]
        x = np.linspace(sub.log_gdp.min(), sub.log_gdp.max(), 50)
        y = sub.net_balance.mean() + row.slope * (x - sub.log_gdp.mean())
        ax.plot(np.exp(x), y, ls=style, color=INK_2, lw=1.4,
                label=f"{label}: +{row.effect_doubling_gdp:.2f} per doubling, p = {row.p_permutation:.2g}")

    ax.set_xscale("log")
    ax.set_xticks([5000, 10000, 20000, 50000, 100000])
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v / 1000:.0f}k"))
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel("GDP per capita (euro, log scale)")
    ax.set_ylabel("Net balance (in − out) / (in + out)")
    ax.set_ylim(-1.05, 1.05)
    ax.grid(color=GRID, lw=0.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, fontsize=7.5,
              labelcolor=INK_2)
    ax.set_title(f"H1, {F.PERIOD_LABEL[H1_PERIOD]}: GDP per capita and net balance", loc="left")
    fig.tight_layout()
    F.save(fig, "fig8_h1_scatter")


def main():
    common.output_dirs()
    fig_network_map()
    fig_uk_yearly()
    fig_h1_scatter()


if __name__ == "__main__":
    main()