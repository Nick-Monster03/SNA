# Phase 3 notes – Network measures (1–11)

*Notes collected at the end of Phase 3 (measures computed on the three period networks). The scripts are in `05_analysis/` (`01_centrality.py`, `02_structure.py`, `03_homophily.py`, `04_figures.py`); every number comes from `05_analysis/tables/` and `05_analysis/reports/`. The A → B → C sentence for each measure is in `measures_summary.md`.*

## 0. How the measures were computed (for the Methods section)

* **Which network for which measure:**
  * **weighted** network (average students/year): strength, net balance, PageRank, HITS, betweenness, communities, weighted reciprocity, weighted homophily;
  * **binary directed** network ($\ge 5$ students/year): degree, reciprocity, density, components, distances, triad census, binary homophily;
  * **binary undirected** network (edge if at least one direction exists, decision 9): k-core, core–periphery, clustering and small-world.
* **Structural zeros.** Two regions of the same country can never be linked (domestic flows removed, decision 4). Densities, random reference graphs, expected E-I values and mixing matrices therefore use only the **feasible pairs** (regions in different countries). This should be stated once in Methods: without this correction many comparisons with chance would be biased.
* **Reproducible randomness:** seed 42 everywhere. Louvain: 20 runs, the run with the highest modularity is kept.
* **Null models:**
  * small-world: 20 random graphs with the same degrees and no same-country edges;
  * triad census: 50 random graphs with the same numbers of mutual, asymmetric and null dyads (U|MAN);
  * GDP homophily: 2,000 permutations of GDP across regions.
* **Country groups (measures 6 and 11):**
  * UN M49 macro-areas: Northern, Western, Southern, Eastern; Cyprus and Turkey form a separate group, "Western Asia";
  * programme groups: EU-15, EFTA, EU-13 (joined from 2004), candidate countries.
* **Tools:** Python, with networkx for the measures, `powerlaw` for the degree distribution (Clauset et al. method) and matplotlib for the figures.

## 1. Overview

| | Pre-Covid 2018–19 | Covid 2020–21 | Post-Covid 2022–23 |
|---|---|---|---|
| Students/year | 230,542 | 159,752 | 216,334 |
| Binary edges ($\ge 5$) | 11,371 | 8,049 | 9,963 |
| Density over feasible pairs | 0.119 | 0.085 | 0.105 |
| Regions with no edge $\ge 5$ | 12 | 24 | 18 |
| Gini of incoming students | 0.626 | 0.645 | 0.661 |
| Share of incoming students, top 10% regions | 45.0% | 47.1% | 49.3% |
| Reciprocity, binary / weighted | 0.585 / 0.594 | 0.553 / 0.573 | 0.598 / 0.616 |
| Core (core–periphery): regions | 96 | 82 | 90 |
| Communities / modularity Q | 4 / 0.136 | 4 / 0.135 | 3 / 0.131 |
| Average clustering / σ | 0.53 / 0.91 | 0.49 / 0.86 | 0.52 / 0.87 |
| GDP assortativity (log, weighted) | 0.31 | 0.29 | 0.27 |

* *The story in brief:* a highly integrated network (any two regions are about 2 steps apart) with a stable core of large university regions in Spain, France, Italy and Germany. Covid makes it sparser and less reciprocal, but does not break it apart. The recovery brings back the students, not the ties, and students are **more concentrated** on the main destinations than before Covid.

## 2. Centrality: who attracts and who sends (measures 1–4)

* **Main destinations (in-strength):** the same in all three periods: `ES61` Andalucía (first in every period, about 7,400 arrivals/year pre and post), `ES30` Madrid, `FR10` Île-de-France, `PT17` Lisbon, `ES52` Valencia, `ES51` Cataluña, then Lombardia, Lazio, the Oslo area and Prague. **4 of the top 6 are Spanish** in every period, consistent with Batagelj (Spain is the main attractor among countries).
* **Main senders (out-strength):** the same large regions (Madrid, Île-de-France, Andalucía, Lombardia) plus `TR10` Istanbul.
* **Net balance** (in − out)/(in + out), Fig. 3:
  * net receivers: Scandinavia, the United Kingdom, some regions around Central-Eastern capitals (`HU12` Pest, `PL92` Mazowiecki regionalny);
  * net senders: **all Turkish regions** (about −0.9) and Albania;
  * France and Germany are in slight deficit.
* **PageRank and HITS:** PageRank and authority almost coincide with the number of arrivals (Spearman ≥ 0.99 within each period). *Interpretation:* where students come from adds little to how many arrive. Hubs are the large French and Italian regions: `FR10` is the top hub in every period, followed by Lombardia and Lazio. *Interpretation:* France and Italy "feed" the Spanish and Portuguese destinations. Post-Covid, Madrid becomes the top authority.
* **Reciprocity:**
  * 59% of binary ties are reciprocated, far above chance (ρ = 0.51–0.55);
  * it drops with Covid (0.585 → 0.553) and recovers afterwards (0.598);
  * about 40% of the weighted flow is unbalanced.
  * *Interpretation:* exchanges are largely bilateral, but Covid hit the return direction of many ties first.
* **Betweenness:** concentrated on very few regions (`ES61`, `FR10`, `ES30`, `ITC4`); during Covid `FR10` becomes first (0.49).
  * It is the least stable measure across periods (Spearman 0.68–0.78).
  * The reading is structural only: students do not "travel through" regions.
  * If space in the report is short, it is the first measure to drop.
* **Rank stability:** very high for arrivals, departures, PageRank and authority (Spearman 0.95–0.99 between periods). *Interpretation:* Covid reduced volumes without changing who is at the top.

## 3. Core and periphery (measure 5)

* **Core–periphery (Borgatti–Everett):** a clear structure, with correlation 0.74–0.77 with the ideal pattern. Density among core regions 0.73–0.79, between core and periphery 0.18–0.21, within the periphery 0.03–0.04.
* **Core composition:** 82–96 regions in 24–26 countries. Pre-Covid: Germany 15, France 12, Spain 11, Italy 8, Netherlands 6, Poland 5. Fig. 1.
* **Covid effect:**
  * the core shrinks (96 → 82 regions) and the maximum k-core drops (k = 52 → 40);
  * above all, the periphery thins out: the mean core number falls from 31.6 to 23.1;
  * the core stays almost the same (Jaccard 0.85–0.90 between periods).
  * *Interpretation:* the pandemic hit mainly the peripheral ties. The core held.
* **United Kingdom:** 2 regions in the core pre-Covid, 0 during and after Covid; in the maximum k-core 4 → 2 → 0.
* *Confirms note 4 of Phase 2:* the core–periphery structure seen in the Gephi visualisation is now confirmed with numbers.

## 4. Communities (measure 6)

* **Louvain on the weighted network:** 3–4 weak but stable blocks. Modularity about 0.13, half of the flow inside communities, stability across runs (NMI) 0.67–0.76. Fig. 2.
  1. **North-West block around the United Kingdom**, with regions of Germany, France, the Netherlands, Belgium, Denmark, Norway and Sweden (92% EU-15).
  2. **Large South-East block:** Spain, Italy, Greece and Portugal together with Poland, Romania, Hungary, Czechia, the Balkans and Turkey (Southern EU-15 40%, EU-13 38%, candidates 23%).
  3. **Block around Germany and Austria**, with Finland, eastern Sweden and Ireland.
* *Interpretation:* this recalls Batagelj's two blocks of "more and less developed" countries, but Southern Europe sits with the East, not with the North-West: southern destinations attract many students from the East and from Turkey.
* Regions of the same country fall into different communities (NMI with country only 0.21–0.23): Germany, for example, is split across blocks.
* *Methodological note:* the modularity null model also expects flows within countries, which are impossible here. Q is therefore deflated: compare it only across periods, not with other networks.

## 5. Cohesion and compactness (measure 7)

* The network **never splits**: in every period all regions with at least one edge belong to a single (weak) component.
* Covid does not fragment the network but **pushes regions out** of it: regions with no edges go from 12 to 24, then 18. The strongly connected component shrinks from 266 to 239 regions, then recovers to 248.
* Very compact network: average path about 2 steps, diameter 4–5.
* *Update to note 3 of Phase 2:* confirmed. The contraction shows up in isolated regions and in the strong component, not in a split of the network.

## 6. Small-world (measure 8)

* Average clustering (0.49–0.53) is about **3 times** that of a random graph with the same density, with equally short paths: small-world in the classic sense.
* **But** compared with random graphs with the **same degrees**, clustering is not higher: σ = 0.86–0.91 (below 1) and ω ≈ 0.27 (closer to random).
* *Interpretation (good for the Discussion):* the high clustering does not come from closed local groups, but from large hubs connected to everyone.

## 7. Degree distribution (measure 9)

* **Heavy tails, but not scale-free** (Fig. 4): the largest region has 10–12 times the mean number of arrivals.
* For degree, the power law is rejected against both exponential and log-normal (p ≤ 0.06). For strength the test is inconclusive (p > 0.19).
* With about 300 nodes, a prudent reading is needed.
* Comparison with the literature: Derzsi et al. find an exponential distribution in 2003, De Benedictis and Leoni heavy tails in 2008–2013.

## 8. Triad census (measure 10)

* **Fully mutual triads (300): 17–27 times more frequent than chance**; 210 triads 6 to 10 times. *Interpretation:* closed "clubs" of regions exchanging with each other.
* Transitive triads (030T, 120D, 120U) are over-represented (about 4–9 times), cyclic ones (030C) under-represented (0.55–0.85). *Interpretation:* flows follow a hierarchy (periphery → semi-periphery → core), not cycles. Fig. 5.
* Both effects are **strongest during Covid**: in the pandemic mainly the densest, most reciprocal part of the network survives.

## 9. Homophily (measure 11)

* **Wealth:**
  * positive assortativity (r = 0.27–0.31 on log GDP, p < 0.001), slightly declining;
  * poor regions exchange with each other 2.2–2.4 times more than expected, rich ones 1.2 times.
* **Only 52–55% of students go to a richer region:** flows are **not** mainly "poor → rich". This is an important hint for H1.
* **Groups:**
  * more ties inside the same programme group and the same macro-area than expected (observed E-I −0.31 vs −0.20 expected);
  * candidate countries send 2.4 times the expected students to the EU-13, almost none to EFTA.
* *Methodological notes:*
  * Newman's assortativity by macro-area comes out near zero or negative, because it ignores the structural zeros: the report should use the observed vs expected E-I comparison;
  * the poorest tercile is 28% Turkish regions (26 of 92), followed by Polish and Greek ones: there is a country effect.

## 10. What the measures say about H3 (Covid and Brexit)

* **Covid:** sparser network (density −29%), more isolated regions, smaller core and k-core, lower reciprocity, slightly longer paths.
* **Incomplete and more concentrated recovery:** volumes at 94% of pre-Covid, binary edges −12%; the Gini and the share of the top regions **keep rising** in the post-Covid period too.
* **Stable structure:** same destinations at the top, almost identical core, similar communities. The recovery rebuilds the core, not the periphery.
* **Brexit:**
  * UK share of arrivals 7.1% → 5.0% → 3.5%, of departures 3.9% → 3.2% → 1.4%;
  * UK regions among the top 50 authorities 4 → 3 → 0;
  * average PageRank position from 173rd to 211th of 319;
  * exit from the core.
* Still to do in Phase 4: QAP correlation between the period matrices, and the UK year by year (2022 vs 2023).

## 11. Pointers for H1 and H2 (Phase 4)

* **H1** (GDP → net balance): the dependent variable is ready (`net_balance` in the `centrality_*.csv` tables). Expectation: uncertain. Poor Turkish regions are strong senders, but only 52–55% of flows go to richer regions, and Spain attracts without being among the richest.
* **H2** (distance, language, GDP difference): macro-area homophily and geographic communities suggest a negative effect of distance.

## 12. Robustness: threshold 3 instead of 5

* All conclusions hold:
  * more edges and a larger core (maximum k 65 / 55 / 60);
  * the same Covid drop in every measure;
  * core–periphery fit 0.76–0.77;
  * σ always below 1 (0.90–0.95);
  * the same over-represented triads (300 is 10 to 16 times chance).
* Communities use the weighted network, so they do not depend on the threshold.
* Files with the `_t3` suffix in `tables/` and `reports/`.

## 13. Limitations for the Discussion

* The betweenness reading is structural only.
* Modularity and Newman's assortativity ignore the structural zeros: this is why comparisons use the expected values over feasible pairs.
* The degree distribution has too few nodes for strong formal tests.
* Core–periphery is found with a heuristic search (degree ranking + single-node moves): it is a local optimum, not a guaranteed global one.
* GDP homophily excludes 43 regions (United Kingdom, Iceland, Liechtenstein).

## 14. Figures (in `05_analysis/figures/`, PNG and PDF)

1. `fig1_core_periphery_map`: core and periphery, three periods (measure 5)
2. `fig2_communities_map`: communities, colours matched across periods (measure 6)
3. `fig3_net_balance_map`: net balance by region (measure 1, useful for H1)
4. `fig4_degree_distribution`: cumulative distributions on a log–log scale (measure 9)
5. `fig5_triad_census`: observed vs expected triads (measure 10)