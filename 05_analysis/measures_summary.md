# Network measures (Phase 3): results and A → B → C sentences

Generated from the scripts in `05_analysis/` (see README). All numbers come from `tables/` and `reports/`.
Networks: weighted = average students/year in the period; binary = edge if ≥ 5 students/year
(robustness: ≥ 3). 319 NUTS 2 regions in every network.

**Important convention.** Two regions of the same country can never be linked (domestic flows
removed, decision 4). These pairs are *structural zeros*: densities and every null model
(random graphs, expected E-I, mixing matrices) use only the **feasible pairs** (regions in
different countries). This should be stated once in Methods.

## Key figures across periods

| | Pre-Covid 2018–19 | Covid 2020–21 | Post-Covid 2022–23 |
|---|---|---|---|
| Students/year | 230,542 | 159,752 | 216,334 |
| Binary edges (≥ 5) | 11,371 | 8,049 | 9,963 |
| Density, feasible pairs (binary) | 0.119 | 0.085 | 0.105 |
| Regions without any edge ≥ 5 | 12 | 24 | 18 |
| Largest strongly connected component | 266 | 239 | 248 |
| Average path length (undirected) | 1.94 | 2.04 | 2.00 |
| Gini of in-strength | 0.626 | 0.645 | 0.661 |
| Share of incoming students, top 10% regions | 45.0% | 47.1% | 49.3% |
| Reciprocity (binary) / weighted reciprocity | 0.585 / 0.594 | 0.553 / 0.573 | 0.598 / 0.616 |
| Max k-core (k / regions) | 52 / 85 | 40 / 85 | 49 / 81 |
| Core–periphery: core size / fit (r) | 96 / 0.75 | 82 / 0.74 | 90 / 0.77 |
| Louvain: communities / modularity Q | 4 / 0.136 | 4 / 0.135 | 3 / 0.131 |
| Average clustering / σ / ω | 0.53 / 0.91 / 0.26 | 0.49 / 0.86 / 0.30 | 0.52 / 0.87 / 0.27 |
| GDP assortativity (log GDP, weighted) | 0.31 | 0.29 | 0.27 |
| UK share of incoming / outgoing students | 7.1% / 3.9% | 5.0% / 3.2% | 3.5% / 1.4% |
| UK regions in the core–periphery core | 2 | 0 | 0 |

Main story in one paragraph: the network is a dense, highly integrated system (any two regions
are about two steps apart) organised around a stable core of large university regions in
Spain, France, Italy and Germany. Covid made it sparser and less reciprocal, but not fragmented
(one weak component in every period). The recovery restored the volume of students (94% of
pre-Covid), not the number of ties (−12% binary edges), and students are **more concentrated**
on the main destinations than before Covid (Gini and top-10% share rise in both later periods).
The UK loses its place in the core.

---

## 1. In/out degree and strength, net balance (weighted and binary)

**A → B → C.** A) Which regions attract and which send students. B) In/out-degree counts partner
regions; in/out-strength counts students per year; net balance = (in − out)/(in + out).
C) High in-strength = a much-chosen destination; a positive net balance = a region that gains
students (net receiver), a negative one = a net sender.

**Results.** The top destinations are stable: Andalucía (ES61), Madrid (ES30), Île-de-France
(FR10), Lisbon (PT17), Valencia (ES52), Cataluña (ES51), Lombardia, Lazio, Oslo area, Praha.
Spanish regions take 4 of the top 6 places in every period (consistent with Batagelj 2025, where
Spain is the main attractor). The largest senders are the same big regions, plus Istanbul
(TR10). Net balance (Fig. 3) separates net receivers (Nordic regions, UK, capital-surrounding
regions in Central-Eastern Europe such as HU12 Pest and PL92) from net senders (all Turkish
regions, around −0.9, and Albania; most French and German regions are moderate net senders). Rankings are very stable (Spearman
in-strength ≥ 0.97 between periods).

## 2. PageRank and HITS (weighted)

**A → B → C.** A) Which destinations are "prestigious". B) PageRank rewards regions receiving
students from important regions; HITS gives an authority score (chosen by good hubs) and a hub
score (sends students to good authorities). C) High authority = a destination chosen by the
regions that send students to the most sought-after places.

**Results.** Authorities: FR10, ES30, ES61, PT17, ES51, ES52, ITC4, ITI4, Oslo area, CZ01 (Madrid
becomes first post-Covid). Hubs: FR10, ITC4 Lombardia, ES30, ITI4 Lazio, ES61, Emilia-Romagna,
Rhône-Alpes. Big French and Italian regions are hubs more than authorities: they feed the
Spanish/Portuguese destinations. PageRank and authority almost reproduce in-strength (Spearman ≥ 0.99 within each period): who
sends the students adds little to how many arrive.

## 3. Reciprocity (binary and weighted)

**A → B → C.** A) Whether exchanges are balanced. B) Share of edges that also exist in the
opposite direction (binary); share of the flow matched by the opposite flow (weighted);
ρ (Garlaschelli–Loffredo) corrects for density (ρ > 0 = more reciprocal than chance).
C) High = balanced bilateral exchanges; low = one-way flows from senders to receivers.

**Results.** About 59% of binary ties are reciprocated, far above chance (ρ = 0.51–0.55).
Reciprocity falls during Covid (0.585 → 0.553) and recovers afterwards (0.598): the pandemic hit
the reverse direction of many ties first. Weighted reciprocity 0.57–0.62: about 40% of the
flow is unbalanced, consistent with the large net senders (Turkey) and receivers.

## 4. Betweenness (weighted, edge length = 1/students)

**A → B → C.** A) Which regions connect different parts of the network. B) Share of shortest paths
between other pairs passing through the region. C) High = a structural bridge between groups.
Caveat for the report: students do not "travel through" regions; the reading is structural only.

**Results.** Concentrated on a few regions: ES61 (0.40), FR10 (0.33), ES30, ITC4, ES52; FR10
becomes first during Covid (0.49). Least stable measure across periods (Spearman 0.68–0.78), so
it is the first measure to drop if space is short.

## 5. k-core and core–periphery (binary, undirected)

**A → B → C.** A) Whether a core of dominant regions exists. B) The k-core is the largest group in
which every region is linked to at least k others of the group; the Borgatti–Everett model
splits regions into a dense core and a periphery linked to the core. C) Core regions hold the
network together; comparing periods shows whether Covid shrank the core or hit the periphery.

**Results.** Clear core–periphery structure (correlation with the ideal pattern 0.74–0.77):
core–core density 0.73–0.79, core–periphery 0.18–0.21, periphery–periphery 0.03–0.04. The
core has 82–96 regions in 24–26 countries, led by Germany, France, Spain, Italy (Fig. 1).
Covid shrank the core (96 → 82) and lowered k_max (52 → 40), mostly by thinning the periphery
(mean core number 31.6 → 23.1). The core is very stable (Jaccard 0.85–0.90 between periods).
UK regions leave the core (2 → 0 → 0) and the max k-core (4 → 2 → 0).

## 6. Communities (Louvain, weighted directed)

**A → B → C.** A) Whether blocks of regions exchange mainly among themselves. B) Louvain splits
the network into groups with more flow inside than expected; modularity Q measures how sharp the
split is. C) A community can never be a country (no domestic flows): we check whether it groups
countries by area, language or development.

**Results.** Weak but stable blocks (Q ≈ 0.13; ~50% of the flow inside communities; stability
across runs NMI 0.67–0.76), Fig. 2:
1. an EU-15 block anchored in the UK, with regions of Germany, France, the Netherlands, Belgium,
   Denmark, Norway and Sweden (92% EU-15);
2. a large southern–eastern block: Spain, Italy, Greece, Portugal with Poland, Romania,
   Hungary, Czechia, the Balkans and Turkey (EU-15 South 40%, EU-13 38%, candidates 23%);
3. a second EU-15 block around Germany and Austria, with Finland, eastern Sweden and Ireland.
4. Pre-Covid and Covid only: a **small fourth block** of 15–17 regions from 9–11 countries (e.g. Valencia, Emilia-Romagna, Hainaut and Liège, Bourgogne, three English regions, two Greek island regions), about 12,000 arrivals/year pre-Covid; post-Covid its regions join the other blocks (3 communities).
This matches the "more vs less developed" blocks of Batagelj (2025), but Southern Europe sits
with the East, not with the North-West. Regions of the same country fall into different
communities (NMI with country only 0.21–0.23). Caveat: the modularity null model expects
same-country flows too, so Q is deflated; compare Q across periods only.

## 7. Density, components, distances (binary)

**A → B → C.** A) How integrated the network is. B) Density over feasible pairs, connected
components, average shortest path and diameter. C) If density falls and the giant component
shrinks with Covid, the network fragmented.

**Results.** Density over feasible pairs 0.119 → 0.085 → 0.105. The network never splits: all
regions with at least one edge form a single weak component in every period; Covid instead
pushes regions *out* of the network (isolates 12 → 24 → 18) and shrinks the strongly connected
core (266 → 239 → 248). Very compact: average path ≈ 2, diameter 4–5.

## 8. Clustering and small-world (binary, undirected)

**A → B → C.** A) Whether European higher education is a "small world". B) Clustering and average
path length compared with random graphs of the same size (σ, ω). C) Small-world = local groups
but every region a few steps from any other.

**Results.** Clustering 0.49–0.53 is about 3 times that of a random graph with the same density
and paths are as short (≈ 2): small-world in the classic sense. But against random graphs with
the **same degrees** clustering is not higher (σ = 0.86–0.91 < 1, ω ≈ 0.27, closer to random):
the clustering is explained by the hubs, not by local cliques. Good point for the Discussion.

## 9. Degree distribution (binary and weighted)

**A → B → C.** A) Whether a few hubs dominate. B) Complementary cumulative distributions
(log–log) and power-law fits compared with exponential and log-normal (Clauset et al., package
`powerlaw`). C) Heavy tails = a network dominated by few hub regions.

**Results.** Heavy-tailed but **not scale-free** (Fig. 4): the largest region has 10–12 times
the mean in-strength, but for degrees a power law is rejected against both exponential and
log-normal (p ≤ 0.06); for strengths the tests are inconclusive (p > 0.19). With ~300 nodes a
prudent reading is required. Compare with Derzsi et al. (exponential, 2003) and De Benedictis
& Leoni (heavy tails, 2008–2013).

## 10. Triad census (binary, directed)

**A → B → C.** A) How relations among three regions are organised. B) Counts of the 16 MAN triad
types compared with random graphs with the same numbers of mutual, asymmetric and null dyads
(U|MAN, 50 simulations, feasible pairs only). C) Many all-mutual triads = "clubs" of regions
exchanging with each other; many transitive one-way triads = hierarchies.

**Results.** Fully mutual triads (300) are 17–27 times more frequent than chance, and 210
6–10 times: closed clubs of reciprocal exchange. Transitive triads (030T, 120D, 120U) are also
over-represented (about 4–9×) while cyclic ones (030C) are under-represented (0.55–0.85×): flows
follow a hierarchy (periphery → semi-periphery → core), not cycles (Fig. 5). Both patterns are
strongest during Covid, when the network keeps mainly its densest, most reciprocal part.

## 11. Homophily and assortativity (binary and weighted)

**A → B → C.** A) Whether regions link to similar regions. B) Correlation of origin and
destination GDP per capita over edges (p from 2,000 permutations); E-I index for macro-area and
programme group against the value expected over feasible pairs. C) Positive = rich regions
exchange mainly with rich regions; negative = exchanges between different regions (e.g. East → West).

**Results.**
- **Wealth:** clear positive assortativity (r = 0.27–0.31 on log GDP, p < 0.001), slowly
  declining. GDP terciles: low-GDP regions send 2.2–2.4 times more students than expected to
  other low-GDP regions, rich to rich 1.2×. Only 52–55% of students (or edges) go to a richer region,
  barely above 50%: flows are **not** mainly "poor → rich" (relevant for H1).
- **Groups:** more ties inside the programme group than expected (EI −0.31 vs −0.20) and
  inside the macro-area (0.52 vs 0.59). Candidates → EU-13 is 2.4× the expected flow;
  Candidates → EFTA almost nil. Newman's assortativity is near zero or negative for macro-area
  because it ignores the structural zeros: use the E-I comparison in the report.
- Caveat: the low-GDP tercile is about 28% Turkish regions (26 of 92), then Polish and Greek ones;
  country effects matter.

## Robustness: threshold 3 instead of 5 (`*_t3` files)

All conclusions hold: more edges and a larger core (k_max 65/55/60), same Covid dip in every
measure, core–periphery fit 0.76–0.77, σ still < 1 (0.90–0.95), same triad pattern (300 is
10–16× chance). Communities are computed on the weighted network and do not depend on the threshold.

## Figures (05_analysis/figures/, PNG + PDF)

1. `fig1_core_periphery_map` – measure 5
2. `fig2_communities_map` – measure 6
3. `fig3_net_balance_map` – measure 1 (useful for H1)
4. `fig4_degree_distribution` – measure 9
5. `fig5_triad_census` – measure 10

## Choices to state in Methods

- Macro-areas: UN M49 geoscheme (Cyprus and Turkey = Western Asia). Programme groups: EU-15,
  EFTA, EU-13 (joined from 2004), candidate countries.
- Louvain: 20 runs (seeds 42–61), best modularity kept. All random steps use seed 42.
- Small-world random graphs: 20 degree-preserving rewirings without same-country edges; lattice
  clustering from the ring-lattice formula 3(k−2)/4(k−1).
- Core–periphery: discrete Borgatti–Everett, core–periphery block excluded, same-country pairs
  excluded; heuristic search (degree ranking + single-node moves).
- Betweenness: shortest paths with edge length 1/students.