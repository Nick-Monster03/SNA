"""
04_prepare_attributes.py - Attaches node-level and dyadic attributes to the network regions
for hypothesis testing (H1, H2) and assortativity analysis.

Run AFTER 01_build_networks.py, from the project root directory:
    python src/04_prepare_attributes.py

Reads:
  04_data/networks/metadata/regions.csv             node list (from 01_build_networks.py)
  04_data/external/NUTS_RG_20M_2016_4326.geojson    2016 boundaries: names & coordinates   [required]
  04_data/external/Eurostat_PIL_NUTS2.csv           Eurostat GDP per capita (nama_10r_2gdp) [required]
  04_data/external/NUTS_RG_20M_2021_4326.geojson    2021 boundaries - optional, for Croatia & Norway
  04_data/external/NUTS_RG_20M_2024_4326.geojson    2024 boundaries - optional, for Portugal & Netherlands

  If the GDP file also includes MIO_EUR (total GDP), merged regions are aggregated using
  population-weighted averages; otherwise, a simple average is used and flagged.
  Regions without an exact match (e.g., PT16 and PT18, split by Eurostat in 2024) are approximated
  by combining overlapping regions weighted by the fraction of area falling inside.

Outputs (saved in 04_data/networks/):
  metadata/region_attributes.csv   for each region: name, country, GDP per capita per period,
                                   and a note describing how the value was derived
  metadata/region_pairs.csv        for each unordered pair of regions: distance in km, same country,
                                   same official language, same language family
  metadata/languages.csv           for each country: official languages and language families
  logs/attributes_report.txt       summary report (for the report Data section)
"""

import json
import math
from itertools import combinations
from pathlib import Path

import pandas as pd
from shapely.geometry import shape
from shapely.ops import unary_union

# =============================================================================
# CONFIGURATION
# =============================================================================
NETWORKS_DIR = Path("04_data/networks")
METADATA_DIR = NETWORKS_DIR / "metadata"
LOGS_DIR = NETWORKS_DIR / "logs"

EXTERNAL_DIR = Path("04_data/external")
GDP_FILE = EXTERNAL_DIR / "Eurostat_PIL_NUTS2.csv"
BOUNDARIES_NETWORKS = EXTERNAL_DIR / "NUTS_RG_20M_2016_4326.geojson"  # baseline NUTS version of networks
BOUNDARIES_NEW = [
    EXTERNAL_DIR / "NUTS_RG_20M_2024_4326.geojson",  # newer NUTS versions used by Eurostat GDP
    EXTERNAL_DIR / "NUTS_RG_20M_2021_4326.geojson",  # (most recent available takes precedence)
]

GDP_UNIT = "EUR_HAB"  # "EUR_HAB" = euros per inhabitant; "PPS_EU27_2020_HAB" = purchasing power standard
PERIODS = {
    "pre_covid": (2018, 2019),
    "covid": (2020, 2021),
    "post_covid": (2022, 2023),
}

# Spatial overlay thresholds: a new region "falls inside" an old one if >= 90% of its area
# lies within it; a match is "exact" if the new regions cover >= 95% of the old region's area.
INSIDE_SHARE = 0.90
COVERAGE_SHARE = 0.95

# National official languages and language families for each country (multiple values separated by ";")
LANGUAGES = {
    "AL": ("Albanian", "Albanian"),
    "AT": ("German", "Germanic"),
    "BE": ("Dutch;French;German", "Germanic;Romance"),
    "BG": ("Bulgarian", "Slavic"),
    "CY": ("Greek;Turkish", "Hellenic;Turkic"),
    "CZ": ("Czech", "Slavic"),
    "DE": ("German", "Germanic"),
    "DK": ("Danish", "Germanic"),
    "EE": ("Estonian", "Uralic"),
    "EL": ("Greek", "Hellenic"),
    "ES": ("Spanish", "Romance"),
    "FI": ("Finnish;Swedish", "Uralic;Germanic"),
    "FR": ("French", "Romance"),
    "HR": ("Croatian", "Slavic"),
    "HU": ("Hungarian", "Uralic"),
    "IE": ("English;Irish", "Germanic;Celtic"),
    "IS": ("Icelandic", "Germanic"),
    "IT": ("Italian", "Romance"),
    "LI": ("German", "Germanic"),
    "LT": ("Lithuanian", "Baltic"),
    "LU": ("Luxembourgish;French;German", "Germanic;Romance"),
    "LV": ("Latvian", "Baltic"),
    "ME": ("Montenegrin", "Slavic"),
    "MK": ("Macedonian", "Slavic"),
    "MT": ("Maltese;English", "Semitic;Germanic"),
    "NL": ("Dutch", "Germanic"),
    "NO": ("Norwegian", "Germanic"),
    "PL": ("Polish", "Slavic"),
    "PT": ("Portuguese", "Romance"),
    "RO": ("Romanian", "Romance"),
    "RS": ("Serbian", "Slavic"),
    "SE": ("Swedish", "Germanic"),
    "SI": ("Slovenian", "Slavic"),
    "SK": ("Slovak", "Slavic"),
    "TR": ("Turkish", "Turkic"),
    "UK": ("English", "Germanic"),
}
# =============================================================================

log_lines = []


def write_log(text=""):
    print(text)
    log_lines.append(str(text))


def load_boundaries(filepath):
    """Loads NUTS 2 regions from a GISCO GeoJSON file: {code: (name, geometry)}."""
    data = json.loads(Path(filepath).read_text(encoding="utf-8"))
    out = {}
    for feat in data["features"]:
        props = feat["properties"]
        if props["LEVL_CODE"] == 2:
            out[props["NUTS_ID"]] = (
                props.get("NAME_LATN") or props.get("NUTS_NAME"),
                shape(feat["geometry"]).buffer(0),
            )
    return out


def load_gdp():
    gdp = pd.read_csv(GDP_FILE)
    gdp = gdp[gdp["geo"].astype(str).str.len() == 4]
    units = sorted(gdp["unit"].unique())
    if GDP_UNIT not in units:
        raise SystemExit(f"Unit {GDP_UNIT} not found in GDP file. Available units: {units}")
    table = gdp.pivot_table(index=["geo", "TIME_PERIOD"], columns="unit", values="OBS_VALUE")
    return table, units


def annual_gdp_value(table, codes, year, has_totals, weights=None):
    """GDP per capita for a set of regions in a given year. Returns None if data is missing.
    weights = fraction of each region to include (1 = whole region; e.g., 0.53 = only the portion
    falling inside the target network region, with population estimated proportionally to area)."""
    weights = weights or [1.0] * len(codes)
    try:
        year_rows = [table.loc[(c, year)] for c in codes]
    except KeyError:
        return None
    per_capita = [r[GDP_UNIT] for r in year_rows]
    if any(pd.isna(v) for v in per_capita):
        return None
    if len(codes) == 1:
        return per_capita[0]
    if has_totals:
        # Regional population = total GDP in euros / GDP per capita in euros
        totals = [r.get("MIO_EUR") for r in year_rows]
        eur_hab = [r.get("EUR_HAB") for r in year_rows]
        if not any(pd.isna(x) for x in totals + eur_hab):
            pop = [w * t * 1e6 / e for w, t, e in zip(weights, totals, eur_hab)]
            # Combined per-capita value = population-weighted average
            return sum(p * a for p, a in zip(per_capita, pop)) / sum(pop)
    return sum(p * w for p, w in zip(per_capita, weights)) / sum(weights)  # simple weighted mean


def match_regions(regions, net_bounds, gdp_bounds, gdp_codes):
    """Finds the Eurostat GDP region codes corresponding to each network region.
    Returns {region: (codes, weights, match_type)}; weights = fraction of each code to include."""
    out = {}
    gdp_countries = {c[:2] for c in gdp_codes}
    for reg in regions:
        parts = reg.split("+")
        if reg[:2] not in gdp_countries:
            out[reg] = (
                [],
                [],
                "excluded from GDP analyses: country absent from Eurostat file (region remains in networks)",
            )
            continue
        if all(p in gdp_codes for p in parts):
            out[reg] = (parts, [1.0] * len(parts), "direct" if len(parts) == 1 else "merged")
            continue
        if not gdp_bounds or not all(p in net_bounds for p in parts):
            out[reg] = ([], [], "missing")
            continue
        area = unary_union([net_bounds[p][1] for p in parts])
        # Candidates: GDP regions genuinely overlapping (not merely adjacent);
        # for each: fraction of ITS area falling inside the network region
        candidates = {}
        for c, (_, geom) in gdp_bounds.items():
            if c in gdp_codes and c[:2] == reg[:2]:
                overlap = geom.intersection(area).area
                if overlap / area.area > 0.01:
                    candidates[c] = (overlap, overlap / geom.area)
        if not candidates:
            out[reg] = (
                [],
                [],
                "missing: code not in GDP file and no overlapping region found "
                "(requires boundaries for the NUTS version used by Eurostat)",
            )
            continue
        # Coverage measured over land area shared across both boundary versions (coastal simplification
        # differences are not boundary changes)
        land = sum(overlap for overlap, _ in candidates.values())
        inside = sorted(c for c, (_, share) in candidates.items() if share >= INSIDE_SHARE)
        coverage = sum(candidates[c][0] for c in inside) / land
        if inside and coverage >= COVERAGE_SHARE:
            out[reg] = (inside, [1.0] * len(inside), "merged" if len(inside) > 1 else "recoded")
        else:
            # No exact match: combine all overlapping regions weighted by the fraction falling inside
            codes = sorted(candidates, key=lambda c: -candidates[c][0])
            weights = [1.0 if candidates[c][1] >= INSIDE_SHARE else round(candidates[c][1], 2) for c in codes]
            pieces = [f"{c} ({w:.0%})" if w < 1 else c for c, w in zip(codes, weights)]
            out[reg] = (
                codes,
                weights,
                "approximated from "
                + " + ".join(pieces)
                + " (in parentheses: area share, population estimated proportionally)",
            )
    return out


def gdp_by_period(table, codes, weights, has_totals):
    """Mean across years in the period; if all years are missing, falls back to latest prior year."""
    values, notes = {}, []
    available_years = sorted({y for (_, y) in table.index})
    for name, (a, b) in PERIODS.items():
        yearly_vals = [
            v
            for year in range(a, b + 1)
            if (v := annual_gdp_value(table, codes, year, has_totals, weights)) is not None
        ]
        if yearly_vals:
            values[name] = round(sum(yearly_vals) / len(yearly_vals), 1)
            if len(yearly_vals) < b - a + 1:
                notes.append(f"{name}: only {len(yearly_vals)} of {b - a + 1} years available")
            continue
        prior_years = [
            year
            for year in available_years
            if year < a and annual_gdp_value(table, codes, year, has_totals, weights) is not None
        ]
        if prior_years:
            values[name] = round(annual_gdp_value(table, codes, prior_years[-1], has_totals, weights), 1)
            notes.append(f"{name}: used {prior_years[-1]}")
        else:
            values[name] = None
    return values, notes


def haversine_km(p1, p2):
    """Great-circle distance (km) between two (lon, lat) coordinates."""
    lon1, lat1, lon2, lat2 = map(math.radians, (*p1, *p2))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def main():
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    regions = pd.read_csv(METADATA_DIR / "regions.csv")["region"].tolist()
    net_bounds = load_boundaries(BOUNDARIES_NETWORKS)

    # --- Region names and representative coordinates ------------------------------
    names, centroids = {}, {}
    for reg in regions:
        parts = reg.split("+")
        names[reg] = " + ".join(net_bounds[p][0] for p in parts if p in net_bounds)
        geom = unary_union([net_bounds[p][1] for p in parts if p in net_bounds])
        point = geom.representative_point() if not geom.centroid.within(geom) else geom.centroid
        centroids[reg] = (point.x, point.y)

    # --- GDP ----------------------------------------------------------------------
    table, units = load_gdp()
    has_totals = "MIO_EUR" in units and "EUR_HAB" in units
    gdp_codes = {g for (g, _) in table.index}
    gdp_bounds = {}
    for f in reversed(BOUNDARIES_NEW):  # most recent boundary file overwrites earlier ones
        if f.exists():
            gdp_bounds.update(load_boundaries(f))

    write_log(
        f"GDP: unit used {GDP_UNIT}; total GDP (MIO_EUR) "
        f"{'present: exact population-weighted aggregations' if has_totals else 'ABSENT: simple mean used'}"
    )
    write_log(
        "Boundary files used for crosswalks: "
        + (", ".join(f.name for f in BOUNDARIES_NEW if f.exists()) or "none")
    )

    matches = match_regions(regions, net_bounds, gdp_bounds, gdp_codes)
    rows = []
    for reg in regions:
        codes, weights, match_type = matches[reg]
        values, notes = (
            gdp_by_period(table, codes, weights, has_totals)
            if codes
            else ({p: None for p in PERIODS}, [])
        )
        if len(codes) > 1 and not has_totals:
            notes.insert(0, "simple mean")
        note = match_type + (
            f" from {'+'.join(codes)}" if match_type in ("merged", "recoded") else ""
        )
        rows.append(
            {
                "region": reg,
                "name": names[reg],
                "country": reg[:2],
                **{f"gdp_{p}": values[p] for p in PERIODS},
                "gdp_note": "; ".join([note] + notes),
            }
        )
    att = pd.DataFrame(rows)
    att.to_csv(METADATA_DIR / "region_attributes.csv", index=False)

    write_log("\nREGIONS WITH GDP BY PERIOD:")
    for p in PERIODS:
        missing = att[att[f"gdp_{p}"].isna()]
        write_log(
            f"  {p:<11} with GDP {len(att) - len(missing)} of {len(att)}   missing: "
            + (", ".join(f"{k} {v}" for k, v in missing["country"].value_counts().items()) or "none")
        )

    write_log("\nNON-DIRECT REGIONS (recoded, merged, approximated, or missing GDP):")
    other = att[~att["gdp_note"].str.startswith("direct")]
    for _, r in other[other["country"] != "UK"].iterrows():
        write_log(f"  {r['region']:<22} {r['name'][:35]:<35} {r['gdp_note']}")
    n_uk = (other["country"] == "UK").sum()
    if n_uk:
        write_log(
            f"  ... plus {n_uk} United Kingdom regions: "
            f"{other.loc[other['country'] == 'UK', 'gdp_note'].iloc[0]}"
        )

    year_notes = att[att["gdp_note"].str.contains(r"used \d{4}|only ", regex=True)]
    if len(year_notes):
        write_log("\nPERIODS WITH MISSING YEARS:")
        for _, r in year_notes.iterrows():
            write_log(f"  {r['region']:<22} {r['gdp_note']}")

    # --- Languages ----------------------------------------------------------------
    countries = sorted({r[:2] for r in regions})
    missing_langs = [c for c in countries if c not in LANGUAGES]
    if missing_langs:
        raise SystemExit(f"Add languages for these countries in LANGUAGES dict: {missing_langs}")
    pd.DataFrame(
        [{"country": c, "languages": LANGUAGES[c][0], "families": LANGUAGES[c][1]} for c in countries]
    ).to_csv(METADATA_DIR / "languages.csv", index=False)

    # --- Region pairs (dyadic covariates) -----------------------------------------
    lang_sets = {
        c: (set(LANGUAGES[c][0].split(";")), set(LANGUAGES[c][1].split(";")))
        for c in countries
    }
    pairs = []
    for a, b in combinations(regions, 2):
        ca, cb = a[:2], b[:2]
        pairs.append(
            {
                "region_a": a,
                "region_b": b,
                "distance_km": round(haversine_km(centroids[a], centroids[b]), 1),
                "same_country": int(ca == cb),
                "same_language": int(bool(lang_sets[ca][0] & lang_sets[cb][0])),
                "same_family": int(bool(lang_sets[ca][1] & lang_sets[cb][1])),
            }
        )
    cp = pd.DataFrame(pairs)
    cp.to_csv(METADATA_DIR / "region_pairs.csv", index=False)

    foreign = cp[cp["same_country"] == 0]
    write_log(f"\nREGION PAIRS: {len(cp):,} (cross-country pairs: {len(foreign):,})")
    write_log(
        f"  distance between cross-country regions: median {foreign['distance_km'].median():,.0f} km, "
        f"min {foreign['distance_km'].min():,.0f}, max {foreign['distance_km'].max():,.0f}"
    )
    write_log(
        f"  cross-country pairs sharing an official language: {foreign['same_language'].mean():.1%}; "
        f"sharing a language family: {foreign['same_family'].mean():.1%}"
    )

    write_log(
        f"\nFiles saved in {METADATA_DIR}/: region_attributes.csv, region_pairs.csv, languages.csv"
    )
    (LOGS_DIR / "attributes_report.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()