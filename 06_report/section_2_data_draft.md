# 2. Data

## Source and Scope
We construct our networks from the geocoded Erasmus+ student mobility dataset by Väisänen et al. (2025), which records individual student exchanges across Europe with validated city-level and NUTS regional coordinates (over 96% geolocation accuracy). Starting from 2,460,819 raw records (2,554,116 students) covering 2014–2023, we apply five sequential filtering and harmonization steps to ensure construct validity and temporal comparability:

1. **Academic mobility only:** We retain only Higher Education student mobility for studies (*"for studies"*), removing 537,533 participants in traineeships, vocational education, and youth exchanges. This ensures that every directed tie has a single, unambiguous meaning: academic attractiveness.
2. **Temporal window (2016–2023):** We exclude 2014–2015 (356,807 students) because 2014 reflects partial rollout of the 2014–2020 programme. From 2016–2023 we extract three symmetric two-year period networks—**pre-Covid (2018–2019)**, **Covid (2020–2021)**, and **post-Covid (2022–2023)**—alongside annual networks (2016–2023) to track year-by-year dynamics.
3. **Consistent country coverage:** We exclude Switzerland (963 incoming students, 0.06% of the total, and zero outgoing students across all years) because it did not participate as a full Programme Country, which would otherwise create artificial sink nodes.
4. **NUTS classification harmonization:** Because the dataset switches from NUTS 2016 to NUTS 2021 in 2021, we track city-level region transitions directly in the data to merge split or recoded regions into time-invariant spatial units (specifically in Croatia `HR04`, Norway `NO01+NO03+NO04+NO05`, and Northern Ireland `UKN0`). Only 18 students in residual unmatchable codes (`ES64`, `NO0B`) are dropped.
5. **International flows only:** We remove 1,273 erroneous domestic records within the same country, as Erasmus+ is strictly international mobility.

## Network Definition and Thresholding
The resulting dataset comprises **1,657,522 study mobilities** across **319 NUTS 2 regions in 36 countries**. Each network is **monomodal and directed**, where nodes are NUTS 2 regions ($N = 319$) and a directed edge $i \to j$ represents students from universities in region $i$ studying in region $j$ (with $i$ and $j$ belonging to different countries).

* **Weighted period networks:** Edge weights represent the average annual number of students in each two-year window.
* **Binary period networks:** For unweighted topological measures, we construct binary networks by retaining edges with an average of at least **5 students/year** (with a secondary threshold of **3 students/year** used for robustness checks). Sensitivity analysis confirms that a threshold of 5 filters out sporadic exchanges while preserving 77.6%–83.3% of total student volume and keeping 92.5%–96.2% of all regions connected within a single giant weakly connected component (Table 1).

| Period Network | Years | Nodes ($N$) | Active Nodes (Weighted) | Weighted Edges | Avg. Students / Year | Binary Edges ($\ge 5$) | Binary Density (Active / All) | Giant WCC ($\ge 5$) | Students Kept ($\ge 5$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Pre-Covid** | 2018–2019 | 319 | 319 | 33,988 | 230,542 | 11,371 | 0.1210 / 0.1121 | 307 (96.2%) | 82.4% |
| **Covid** | 2020–2021 | 319 | 319 | 29,675 | 159,752 | 8,049 | 0.0928 / 0.0793 | 295 (92.5%) | 77.6% |
| **Post-Covid** | 2022–2023 | 319 | 318 | 31,108 | 216,334 | 9,963 | 0.1103 / 0.0982 | 301 (94.4%) | 83.3% |

*Table 1: Structural summary of the three period networks (weighted and primary binary versions at threshold $\ge 5$ students/year).*

## Regional Attributes (Validity and Reliability)
Using Eurostat (`nama_10r_2gdp`) and GISCO boundaries (2016, 2021, 2024), we match per-capita GDP (`EUR_HAB`) to **276 of 319 regions** across all three periods. For merged regions (`HR04`, `NO01+NO03+NO04+NO05`, `PT17`), we compute exact population-weighted averages using total regional GDP (`MIO_EUR`), while split Portuguese regions (`PT16`, `PT18`) are approximated via spatial area overlap. Where post-Covid GDP figures were not yet published (Norway and Albania), we rely on the latest available prior year (2021/2022).

The 43 regions lacking Eurostat regional GDP—United Kingdom (41), Iceland (1), and Liechtenstein (1)—remain included in all structural network analyses and are excluded solely from GDP-based tests (H1, H2, and economic assortativity). Finally, we compute great-circle Haversine distances between region representative points and code official languages and language families across all 47,636 cross-country region pairs.