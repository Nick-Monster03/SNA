"""
01_build_networks.py - Builds the Erasmus+ student mobility networks between European regions (NUTS 2).

Data: dataset by Vaisanen et al. (2025), Scientific Data,
      https://doi.org/10.1038/s41597-025-04789-0 - files at https://zenodo.org/records/16737523

The raw data file must be placed in 04_data/raw/. The script searches for any file matching
"Erasmus_*individual*parquet*", e.g.:
  - Erasmus_2014-2023_individual.parquet         (recommended version, up to 2023)
  - Erasmus_2014-2022_individual.parquet.gzip    (older version, up to 2022)
If multiple files are found, it uses the one with the most recent end year.

Usage, from the project root directory:
    python src/01_build_networks.py --explore    # only shows dataset structure without writing files
    python src/01_build_networks.py              # builds the networks

Outputs, saved inside 04_data/networks/:
  yearly/network_<year>.csv        one network per year    (origin, destination, students)
  periods/network_<period>.csv     one network per period  (students = annual average)
  metadata/regions.csv             list of region nodes with their country code (region, country)
  logs/excluded_countries.csv      outgoing and incoming students of excluded countries, year by year
  logs/build_log.txt               summary of filtered records at each step (for the report Data section)
"""

import sys
from pathlib import Path

import pandas as pd

# =============================================================================
# CONFIGURATION & DATA CHOICES - each choice is documented in data_decisions.txt
# =============================================================================
RAW_DIR = Path("04_data/raw")
FILE_PATTERN = "Erasmus_*individual*parquet*"

NETWORKS_DIR = Path("04_data/networks")
YEARLY_DIR = NETWORKS_DIR / "yearly"
PERIODS_DIR = NETWORKS_DIR / "periods"
METADATA_DIR = NETWORKS_DIR / "metadata"
LOGS_DIR = NETWORKS_DIR / "logs"

# Study mobility only: keep rows whose activity contains this substring
ACTIVITY_COL = "Activity (mob)"
STUDY_TEXT = "for studies"

# First year (mobility start year). The last year depends on the input file found.
FIRST_YEAR = 2016

# Two-year periods. If the input file only reaches 2022, post_covid will cover a single year.
PERIODS = {
    "pre_covid": (2018, 2019),
    "covid": (2020, 2021),
    "post_covid": (2022, 2023),
}

# Countries: keep only countries that SEND students in every analyzed year.
# A country that receives but never sends (or only appears in some years) does not fully
# participate in the program and would make networks across different years incomparable.

# Region codes: from 2021 the dataset uses NUTS 2021 classification, previously NUTS 2016.
# Correspondences between old and new codes are derived directly from the data: if a city
# belongs to region A until 2020 and to region B from 2021, A and B represent the same area.
NUTS_CHANGE_YEAR = 2021
# =============================================================================

COL_YEAR, COL_ORIG, COL_DEST, COL_STUD = "year", "orig_NUTS", "dest_NUTS", "Actual Participants"
log_lines = []


def log(text=""):
    print(text)
    log_lines.append(text)


def find_data_file():
    found = sorted(RAW_DIR.glob(FILE_PATTERN), reverse=True)  # 2023 before 2022
    if not found:
        existing = (
            "\n  - ".join(sorted(p.name for p in RAW_DIR.iterdir() if p.is_file()))
            if RAW_DIR.exists()
            else "(directory does not exist)"
        )
        sys.exit(
            f"No data file found in {RAW_DIR}/.\n"
            f"Looking for a file matching: {FILE_PATTERN}\n"
            f"Files currently in {RAW_DIR}/:\n  - {existing}"
        )
    if len(found) > 1:
        print("Multiple data files found, using the first:", ", ".join(p.name for p in found))
    return found[0]


def explore(df):
    """Displays the dataset structure without writing any output files."""
    print(f"\nRows: {len(df):,}   Students: {df[COL_STUD].sum():,.0f}\n")
    print("COLUMNS:")
    for c in df.columns:
        example = str(df[c].dropna().iloc[0])[:50] if df[c].notna().any() else ""
        print(f"  {c:<28} e.g. {example}")
    print("\nSTUDENTS BY YEAR:")
    print(df.groupby(COL_YEAR)[COL_STUD].sum().astype(int).to_string())
    print(f"\nMOBILITY TYPES (columns '{ACTIVITY_COL}' and 'Field'), students:")
    types = (
        df.groupby([ACTIVITY_COL, "Field"])[COL_STUD]
        .sum()
        .astype(int)
        .sort_values(ascending=False)
        .reset_index()
    )
    for _, r in types.iterrows():
        kept = STUDY_TEXT.lower() in str(r[ACTIVITY_COL]).lower()
        status = "KEPT    " if kept else "excluded"
        print(f"  {status}  {r[COL_STUD]:>9,}  {r[ACTIVITY_COL][:70]:<70}  [{r['Field']}]")


def log_step(name, before, df, reason):
    after = df[COL_STUD].sum()
    log(f"  {name:<22} removed {before - after:>9,.0f}  remaining {after:>9,.0f}   ({reason})")


def unmatched_codes(df):
    """Regional codes appearing only before or only after the NUTS classification change."""
    before = set(df.loc[df[COL_YEAR] < NUTS_CHANGE_YEAR, ["origin", "destination"]].values.ravel())
    after = set(df.loc[df[COL_YEAR] >= NUTS_CHANGE_YEAR, ["origin", "destination"]].values.ravel())
    return before - after, after - before, before & after


def describe_excluded_countries(df, excluded, years):
    """Logs details about countries that will be excluded, before removing them.

    For each country, prints (and saves to logs/excluded_countries.csv) outgoing and incoming
    students year by year, share of total flow, partner countries, and mobility types.
    """
    if not excluded:
        return
    total = df[COL_STUD].sum()
    csv_rows = []
    log("\n  COUNTRIES TO BE EXCLUDED - data prior to exclusion:")
    for country in excluded:
        outgoing = df[df["origin"].str[:2] == country]
        incoming = df[df["destination"].str[:2] == country]
        involved = df[(df["origin"].str[:2] == country) | (df["destination"].str[:2] == country)]
        log(
            f"\n  {country}: {involved[COL_STUD].sum():,.0f} students involved "
            f"({involved[COL_STUD].sum() / total:.3%} of total), "
            f"{outgoing[COL_STUD].sum():,.0f} outgoing, {incoming[COL_STUD].sum():,.0f} incoming"
        )

        log(f"    {'year':<6} {'outgoing':>8} {'incoming':>8}")
        out_by_year = outgoing.groupby(COL_YEAR)[COL_STUD].sum()
        in_by_year = incoming.groupby(COL_YEAR)[COL_STUD].sum()
        for year in years:
            u, e = int(out_by_year.get(year, 0)), int(in_by_year.get(year, 0))
            log(f"    {year:<6} {u:>8,} {e:>8,}")
            csv_rows.append(
                {
                    "country": country,
                    "year": year,
                    "outgoing_students": u,
                    "incoming_students": e,
                }
            )

        if len(incoming):
            from_c = incoming.groupby(incoming["origin"].str[:2])[COL_STUD].sum().sort_values(ascending=False)
            log("    incoming students from: " + ", ".join(f"{p} {int(n)}" for p, n in from_c.head(8).items()))
            regions = incoming.groupby("destination")[COL_STUD].sum().sort_values(ascending=False)
            log("    destination regions: " + ", ".join(f"{r} {int(n)}" for r, n in regions.items()))
        if len(outgoing):
            to_c = outgoing.groupby(outgoing["destination"].str[:2])[COL_STUD].sum().sort_values(ascending=False)
            log("    outgoing students to: " + ", ".join(f"{p} {int(n)}" for p, n in to_c.head(8).items()))
        types = involved.groupby(ACTIVITY_COL)[COL_STUD].sum().sort_values(ascending=False)
        log("    mobility types: " + "; ".join(f"{t} ({int(n)})" for t, n in types.items()))

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(csv_rows).to_csv(LOGS_DIR / "excluded_countries.csv", index=False)
    log(f"\n  Yearly breakdown saved to {LOGS_DIR}/excluded_countries.csv\n")


def correspondences_from_data(df):
    """Derives from the data which old and new NUTS codes refer to the same geographic area.

    For each city, checks which region code it was assigned to before and after the NUTS
    classification change. If it changes, and one of the two codes only exists in a single period,
    the two codes are linked. Connected groups of codes are merged into a single region.
    """
    only_before, only_after, stable = unmatched_codes(df)
    unmatched = only_before | only_after
    places = pd.concat(
        [
            pd.DataFrame({"city": df["origin_city"], "code": df["origin"], "year": df[COL_YEAR], "w": df[COL_STUD]}),
            pd.DataFrame({"city": df["dest_city"], "code": df["destination"], "year": df[COL_YEAR], "w": df[COL_STUD]}),
        ]
    )
    places["after"] = places["year"] >= NUTS_CHANGE_YEAR
    # Predominant code for each city before and after the classification change
    predominant = (
        places.groupby(["city", "after", "code"])["w"]
        .sum()
        .reset_index()
        .sort_values("w")
        .groupby(["city", "after"])
        .tail(1)
        .pivot(index="city", columns="after", values="code")
        .dropna()
    )
    predominant.columns = ["before", "after"]
    changes = predominant[
        (predominant["before"] != predominant["after"])
        & (predominant["before"].isin(unmatched) | predominant["after"].isin(unmatched))
    ]
    links = changes.groupby(["before", "after"]).size()

    # Connected components of codes (union-find)
    parent = {}

    def find_root(c):
        parent.setdefault(c, c)
        while parent[c] != c:
            c = parent[c]
        return c

    for a, b in links.index:
        parent[find_root(a)] = find_root(b)
    groups = {}
    for c in list(parent):
        groups.setdefault(find_root(c), set()).add(c)

    # Group name: the stable code if available, otherwise the old codes joined by "+"
    mapping = {}
    for members in groups.values():
        stable_members = sorted(members & stable)
        name = stable_members[0] if stable_members else "+".join(sorted(members & only_before))
        for c in members:
            mapping[c] = name
    return links, mapping


def main():
    data_file = find_data_file()
    print(f"Reading {data_file} ...")
    df = pd.read_parquet(data_file)
    df[COL_STUD] = pd.to_numeric(df[COL_STUD], errors="coerce").fillna(0)
    df[COL_YEAR] = pd.to_numeric(df[COL_YEAR], errors="coerce")

    if "--explore" in sys.argv or "--esplora" in sys.argv:
        explore(df)
        return

    last_year = int(df[COL_YEAR].max())
    log(
        f"Dataset: {data_file.name} - {len(df):,} rows, {df[COL_STUD].sum():,.0f} students, "
        f"years {int(df[COL_YEAR].min())}-{last_year}"
    )
    if last_year < 2023:
        log(f"WARNING: file only reaches {last_year}: the post-Covid period will be shorter than the others.")
    log("\nFILTERING STEPS (number of students):")
    log(f"  {'initial':<22} {'':>17}  remaining {df[COL_STUD].sum():>9,.0f}")

    # 1. Study mobility only
    if ACTIVITY_COL not in df.columns:
        sys.exit(f"Column '{ACTIVITY_COL}' not found. Run with --explore to inspect columns.")
    before = df[COL_STUD].sum()
    df = df[df[ACTIVITY_COL].astype(str).str.contains(STUDY_TEXT, case=False, regex=False)]
    log_step("1. study only", before, df, f"activities containing '{STUDY_TEXT}'")

    # 2. Years
    before = df[COL_STUD].sum()
    df = df[df[COL_YEAR].between(FIRST_YEAR, last_year)].copy()
    df[COL_YEAR] = df[COL_YEAR].astype(int)
    log_step("2. years", before, df, f"from {FIRST_YEAR} to {last_year}")

    # 3. From NUTS 3 to NUTS 2: first 4 characters of the region code
    # Note: raw dataset already has columns named "origin" and "destination" (city names),
    # so we rename them before creating the NUTS 2 "origin" and "destination" columns.
    df = df.rename(columns={"origin": "origin_city", "destination": "dest_city"})
    df["origin"] = df[COL_ORIG].astype(str).str[:4]
    df["destination"] = df[COL_DEST].astype(str).str[:4]

    # 4. Countries: keep only those sending students in every analyzed year
    years = sorted(df[COL_YEAR].unique())
    sent = (
        df.assign(country=df["origin"].str[:2])
        .groupby(["country", COL_YEAR])[COL_STUD]
        .sum()
        .unstack(fill_value=0)
    )
    sent = sent.reindex(columns=years, fill_value=0)
    kept_countries = set(sent[(sent > 0).all(axis=1)].index)
    all_countries = set(df["origin"].str[:2]) | set(df["destination"].str[:2])
    excluded = sorted(all_countries - kept_countries)
    describe_excluded_countries(df, excluded, years)
    before = df[COL_STUD].sum()
    df = df[df["origin"].str[:2].isin(kept_countries) & df["destination"].str[:2].isin(kept_countries)]
    log_step(
        "3. excluded countries",
        before,
        df,
        f"do not send students in all years: {', '.join(excluded) or 'none'}",
    )

    # 5. NUTS codes changed in 2021: correspondences derived from city-level records
    only_before, only_after, _ = unmatched_codes(df)
    log(f"\n  Codes present only up to {NUTS_CHANGE_YEAR - 1}: {sorted(only_before)}")
    log(f"  Codes present only from {NUTS_CHANGE_YEAR}:     {sorted(only_after)}")

    links, mapping = correspondences_from_data(df)

    log("  Correspondences found in data (cities switching from one NUTS code to another):")
    for (a, b), n in links.items():
        log(f"    {a} -> {b}   ({n} cities)")
    log("  Merged regions:")
    for name in sorted(set(mapping.values())):
        log(f"    {name:<22} <- {', '.join(sorted(c for c in mapping if mapping[c] == name))}")
    df["origin"] = df["origin"].replace(mapping)
    df["destination"] = df["destination"].replace(mapping)

    # Unmatched codes remaining: present only in a subset of years
    only_before, only_after, _ = unmatched_codes(df)
    leftover = only_before | only_after
    before = df[COL_STUD].sum()
    df = df[~df["origin"].isin(leftover) & ~df["destination"].isin(leftover)]
    log("")
    log_step(
        "4. unmatched codes",
        before,
        df,
        f"regions present only in some years: {', '.join(sorted(leftover)) or 'none'}",
    )

    # 6. Domestic flows within the same country (Erasmus+ is international mobility)
    before = df[COL_STUD].sum()
    df = df[df["origin"].str[:2] != df["destination"].str[:2]]
    log_step("5. domestic flows", before, df, "same origin and destination country")

    # Ensure output directories exist
    for directory in (YEARLY_DIR, PERIODS_DIR, METADATA_DIR, LOGS_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    # Clean old network files
    for old_file in YEARLY_DIR.glob("network_*.csv"):
        old_file.unlink()
    for old_file in PERIODS_DIR.glob("network_*.csv"):
        old_file.unlink()

    # 7. Yearly networks
    yearly = (
        df.groupby([COL_YEAR, "origin", "destination"], as_index=False)[COL_STUD]
        .sum()
        .rename(columns={COL_STUD: "students"})
    )
    yearly["students"] = yearly["students"].astype(int)
    log("\nYEARLY NETWORKS:")
    for year, net in yearly.groupby(COL_YEAR):
        net = net[["origin", "destination", "students"]]
        net.to_csv(YEARLY_DIR / f"network_{year}.csv", index=False)
        nodes = len(set(net["origin"]) | set(net["destination"]))
        log(f"  yearly/network_{year}.csv   {nodes:>4} regions  {len(net):>7,} edges  {net['students'].sum():>8,} students")

    # 8. Period networks: annual average of students
    log("\nPERIOD NETWORKS (annual average):")
    for name, (a, b) in PERIODS.items():
        b = min(b, last_year)
        if a > b:
            log(f"  {name}: skipped, dataset does not cover these years")
            continue
        sel = yearly[yearly[COL_YEAR].between(a, b)]
        net = sel.groupby(["origin", "destination"], as_index=False)["students"].sum()
        net["students"] = (net["students"] / (b - a + 1)).round(2)
        net.to_csv(PERIODS_DIR / f"network_{name}.csv", index=False)
        nodes = len(set(net["origin"]) | set(net["destination"]))
        log(
            f"  periods/network_{name}.csv ({a}-{b})   {nodes:>4} regions  {len(net):>7,} edges  "
            f"{net['students'].sum():>10,.0f} students/year"
        )

    # 9. Node list
    regions = sorted(set(yearly["origin"]) | set(yearly["destination"]))
    pd.DataFrame({"region": regions, "country": [r[:2] for r in regions]}).to_csv(
        METADATA_DIR / "regions.csv", index=False
    )
    log(f"\nTotal: {len(regions)} regions across {len(set(r[:2] for r in regions))} countries")

    (LOGS_DIR / "build_log.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(f"\nDone. Files saved inside {NETWORKS_DIR}/")


if __name__ == "__main__":
    main()