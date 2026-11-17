# Erasmus+ Regional Mobility Network Analysis

Social Network Analysis project investigating the structure of the European Erasmus+ student mobility network across NUTS 2 regions, its evolution before, during, and after the COVID-19 pandemic (including the UK Brexit shock), and its socio-economic and geographic drivers.

## Repository Structure

```text
├── 01_organization/           # Project roadmap, meeting notes, and data cleaning decisions
├── 02_literature/             # Reference papers (Väisänen et al., Batagelj, De Benedictis & Leoni, Gadár et al., Rusu et al.)
├── 03_reading_notes/          # One-page literature summaries
├── 04_data/
│   ├── raw/                   # Raw Zenodo Erasmus+ individual mobility parquet dataset
│   ├── external/              # Eurostat regional GDP (nama_10r_2gdp) & GISCO NUTS 2 GeoJSON boundaries
│   └── networks/
│       ├── yearly/            # Annual weighted directed networks (2016–2023)
│       ├── periods/           # Period-averaged weighted directed networks (pre_covid, covid, post_covid)
│       ├── binary/            # Unweighted binary networks (thresholds: 5 and 3 students/year)
│       ├── metadata/          # Node list, regional GDP attributes, dyadic distances & language covariates
│       └── logs/              # Automated data validation reports and filtering logs
├── 05_analysis/               # Scripts, tables, and figures for network measures (1–11) and QAP/MRQAP tests
├── 06_report/                 # Final report drafts and submission PDF
└── src/                       # Data processing & network construction pipeline
    ├── 01_build_networks.py
    ├── 02_verify_data.py
    ├── 03_build_binary_networks.py
    ├── 04_prepare_attributes.py
    └── 05_load_networks.py
```

## Prerequisites

- **Python 3.10+**
- **Raw Zenodo dataset** placed in `04_data/raw/` matching `Erasmus_*individual*parquet*`
- **External files** placed in `04_data/external/`:
  - `Eurostat_PIL_NUTS2.csv`
  - `NUTS_RG_20M_2016_4326.geojson`
  - `NUTS_RG_20M_2021_4326.geojson` *(optional, for Croatia & Norway crosswalks)*
  - `NUTS_RG_20M_2024_4326.geojson` *(optional, for Portugal & Netherlands crosswalks)*

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Data Pipeline Execution

Run all scripts from the project root directory in numerical order:

```bash
# 1) Inspect raw dataset structure without generating files
python src/01_build_networks.py --explore

# 2) Build yearly and period weighted networks + node list
python src/01_build_networks.py

# 3) Run data validation, UK/Brexit trends, and threshold sensitivity checks
python src/02_verify_data.py

# 4) Generate binary networks (primary threshold = 5, robustness threshold = 3)
python src/03_build_binary_networks.py

# 5) Attach regional GDP, great-circle distances, and language attributes
python src/04_prepare_attributes.py

# 6) Load every network in networkx and check the numbers against the logs
python src/05_load_networks.py
```

## Network Measures (Phase 3)

Run from the project root, after the data pipeline, in this order:

```bash
python 05_analysis/01_centrality.py               # measures 1-4  (~10 s)
python 05_analysis/02_structure.py                # measures 5-10 (~3 min)
python 05_analysis/03_homophily.py                # measure 11    (~5 s)
python 05_analysis/04_figures.py                  # figures for the report
python 05_analysis/02_structure.py --threshold 3  # robustness check (outputs end in _t3)
```

Outputs: `05_analysis/tables/` (CSV), `05_analysis/figures/` (PNG + PDF), `05_analysis/reports/` (text reports).
`05_analysis/measures_summary.md` summarises the results with the A → B → C sentence for every measure.

## Main Generated Outputs

All outputs are automatically generated inside `04_data/networks/`:

- **`yearly/`**: `network_2016.csv` ... `network_2023.csv` (`origin`, `destination`, `students`)
- **`periods/`**: `network_pre_covid.csv`, `network_covid.csv`, `network_post_covid.csv` (`origin`, `destination`, `students` as annual average)
- **`binary/`**: `network_<period>_thresh5.csv` (primary) and `network_<period>_thresh3.csv` (robustness check)
- **`metadata/`**: `regions.csv`, `region_attributes.csv`, `region_pairs.csv`, `languages.csv`
- **`logs/`**: `build_log.txt`, `excluded_countries.csv`, `checks_report.txt`, `threshold_checks.csv`, `binary_networks_report.txt`, `attributes_report.txt`