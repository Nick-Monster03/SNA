# Phase 4 – Hypothesis tests: outcomes

*One row per claim. Scripts: `05_analysis/05_h1_wealth.py`, `06_h2_mrqap.py`, `07_h3_change.py`; every number comes from the `h1_*`, `h2_*` and `h3_*` files in `05_analysis/tables/` and `05_analysis/reports/`. Choices and their reasons: `01_organization/decisions.txt`, points 17–26. Values are given as pre-Covid / Covid / post-Covid when they differ by period. All p-values come from permutations: p = 0.0002 (5,000 permutations) and p = 0.001 (1,000 permutations) are the smallest values possible.*

## Summary

| Hypothesis | Outcome | In one sentence |
|---|---|---|
| **H1** Richer regions receive more students than they send | **Not supported** | The positive effect exists only because of Turkey (poor regions, strong senders); without Turkey, or within the same country, wealth does not predict the net balance. |
| **H2** Flows decrease with distance and increase with a shared language | **Not supported** | No distance decay, and a shared language *reduces* flows; flows are shaped instead by region size, similar wealth and related-but-different languages. |
| **H3** With Covid the network becomes sparser, more concentrated and less reciprocal; after Brexit the UK loses centrality | **Supported** (descriptive) | All claims hold, but the network never fragments, concentration was already rising before Covid and does not go back, and reciprocity fully recovers. Consistent with a Covid and a Brexit effect, not a proof of cause. |

## H1 – Wealth and attractiveness

Test: regression of the net balance (in − out)/(in + out) on log GDP per capita, p-values from 5,000 permutations of the net balance across regions. 276 regions (275 post-Covid: NL13 has no students).

| Claim / model | Key result | p | Outcome |
|---|---|---|---|
| M1: all regions with GDP | slope 0.22 / 0.21 / 0.21: doubling GDP raises the net balance by 0.15 / 0.15 / 0.14; r = 0.39 / 0.35 / 0.34 | 0.0002 in all periods | Supported |
| M2: without the 26 Turkish regions | slope 0.04 / 0.01 / 0.01; Spearman ρ ≈ 0 (−0.04 to 0.00) | 0.26 / 0.83 / 0.85 | Not supported |
| M3: within country (country fixed effects) | slope 0.05 / 0.01 / 0.07 | 0.31 / 0.76 / 0.14 | Not supported |
| Descriptive: GDP terciles | mean net balance −0.25 / −0.17 / −0.20 in the poorest tercile (all 26 Turkish regions are there), about 0 in the richest; but the share of net receivers is similar: 40–48% (poorest) vs 47–51% (richest) | – | – |
| **H1 overall** | | | **Not supported** |

* *For the Discussion:* Luxembourg is the richest region (GDP per capita about 100,000–120,000 euros) but a net sender (net balance −0.56 / −0.31 / −0.55, the largest negative residual): the University of Luxembourg requires a semester abroad from every bachelor student, so it sends about 480–510 students/year before and after Covid and receives about 120–150 – university rules matter more than wealth.

## H2 – Distance, language and flows

Test: MRQAP with Double Semi-Partialling, 1,000 permutations; 276 regions with GDP, 71,370 ordered cross-country pairs. Dependent variable log(1 + students/year); effects as % change in (1 + students/year). M1 = roadmap model; M2 = M1 + size of origin and destination; M3 = M1 + one fixed effect per origin and per destination. Language = the most spoken language of each region (`decisions.txt` point 22).

| Claim / variable | M1 | M2 | M3 | Outcome |
|---|---|---|---|---|
| Flows decrease with distance (distance ×2) | −2.8% / −0.5% / −1.1%; p = 0.37 / 0.87 / 0.73 | +5.6% / +5.0% / +5.4%; p = 0.002 / 0.002 / 0.001 | +1.7% / +2.8% / +3.5%; p = 0.002 / 0.001 / 0.001 | **Not supported**: no distance decay; the effect is null (M1) or slightly positive (M2, M3) |
| Flows increase with a shared language | −33% / −24% / −25%; p = 0.002 / 0.002 / 0.003 | −15% / −10% / −9%; p = 0.003 / 0.016 / 0.059 | −14% / −9% / −5%; p = 0.001 / 0.002 / 0.028 | **Not supported**: opposite sign (significant in 8 of 9 cases) |
| *Not in H2:* same language family | +18% / +18% / +20% | +13% / +11% / +12% | +12% / +10% / +9% | Positive (p = 0.001 everywhere) |
| *Not in H2:* GDP difference (one region twice as rich) | −24% / −21% / −26% | −16% / −13% / −16% | −23% / −21% / −26% | Negative (p = 0.001 everywhere): homophily, as in measure 11 |
| R² | 0.08–0.09 | 0.40–0.42 | 0.53–0.56 (includes the region effects) | – |
| **H2 overall** | | | | **Not supported** |

Robustness checks:

* **Binary network** (edge ≥ 5 students/year, linear probability model): the same signs for every significant coefficient in every model and period; distance in M1 stays close to zero and not significant (p = 0.45–0.97).
* **Language coding of Phase 2** (1 = the two countries share a national official language; `h2_language_check.csv`): the shared-language effect is stronger (M1 −36% / −27% / −31%; M2 and M3 −17% to −23%, p = 0.001), because pairs that share only a minority language (Belgium–Germany, Finland–Sweden, Cyprus–Turkey) have few students. Distance and language family give the same conclusions with both codings.
* **The permutation test matters:** for distance in M1 pre-Covid the classic OLS t-value is −7.9, the permutation p-value 0.37.

* **Which variables weigh most** (standardised coefficients, M2): the size of origin and destination (0.40–0.44) by far; then the GDP difference (−0.15 / −0.16; about −0.26 in M1), the strongest of the roadmap variables; language family (0.05), distance (0.06) and same language (−0.01 to −0.02) are weak.
* *For the Discussion (Rusu et al.):* the distance effect does not weaken over time, because there is no negative effect to weaken: standardised coefficient −0.030 / −0.006 / −0.012 in M1 (never significant), +0.018 / +0.034 / +0.037 in M3.

## H3 – Covid and Brexit

Mainly a descriptive comparison between networks; the only formal test is the QAP correlation. Covid claims compare pre-Covid → Covid; UK claims compare pre-Covid → post-Covid. "Recovered" = share of the Covid change undone in 2022–23. "Normal" = year-to-year changes 2016–2019.

| Claim | Key result | Outcome |
|---|---|---|
| Sparser with Covid | edges ≥ 5 −29% (11,371 → 8,049); isolated regions 12 → 24; strong component 266 → 239; k_max 52 → 40; core 96 → 82 regions. Yearly: density 2019 → 2020 −41% (normal: −0.7% to +1.6%). Recovered 33–75% | Supported |
| *(Measure 7 expectation)* Fragmented | one weak component in every period | Not supported: sparser, but never split |
| More concentrated | Gini of arrivals 0.626 → 0.645 → 0.661; top 10% regions 45.0% → 47.1% → 49.3% of arrivals. Yearly: Gini 2019 → 2020 +1.6% (normal: +0.1% to +0.9%); the largest yearly rise is 2022 → 2023 (+2.8%), and the top 10% share goes from 45.3% (2019) to 50.1% (2023) | Supported, but the rise started before Covid (yearly Gini 0.622 → 0.628 in 2016–2019) and continues after it (not reversed) |
| Less reciprocal | binary reciprocity 0.585 → 0.553 (ρ 0.53 → 0.51). Yearly: 2019 → 2020 −14% (normal: −0.8% to +1.9%) | Supported; fully recovered (0.598 post-Covid, above pre-Covid) |
| *(Open question)* Does the recovery rebuild the same ties? | QAP r pre-Covid vs post-Covid 0.88 (weighted) / 0.74 (binary), p = 0.001; expected if only countries kept their ties: 0.22 / 0.15. 72% of pre-Covid edges (≥ 5 students/year) still present post-Covid; 18% of post-Covid edges are new. Yearly: in 2021, 42% of the edges did not exist in 2020 (normal: 20–22%) – the recovery also builds new ties | Largely yes: the stability belongs to the regions, not only to the countries |
| *(Benchmark)* Is the 2020 change unusual? | correlation with the previous year 0.835 (normal 0.891–0.894); edges kept 52% (normal 79–80%); after 2020 the network stays less stable than before (0.82–0.86 until 2023) | Yes: outside the normal range for every measure |
| UK loses centrality after Brexit | UK share of arrivals 7.1% → 3.5%, of departures 3.9% → 1.4%; UK regions among the top 50 authorities 4 → 0; mean PageRank position 173rd → 211th of 319. Yearly (2019 = 100): 2023 departures 8 (rest of the network 99), arrivals 36 (rest 100). 2019 → 2023: the largest fall of all 36 countries (departures −92%, arrivals −64%) | Supported; the collapse comes in 2023. Caveat: UK arrivals were already falling before Brexit (index 114 → 100 in 2016–2019, rest of the network 94 → 100) |
| **H3 overall** | | **Supported**, with the three nuances above (no fragmentation, concentration not reversed, reciprocity recovered) |

* *For the Discussion (Brexit, 2019 → 2023, to write with care: the change mixes Brexit and the recovery from Covid):* arrivals grow most in Malta (+34%), Cyprus (+26%), Italy (+23%), Norway and Iceland (+21%), while Ireland, although English-speaking, does not gain (−2%) and Germany (−16%) and Poland (−22%) lose; departures fall most in Serbia (−67%), Bulgaria (−36%) and Turkey (−24%); a possible reading is that students who went to the UK move to destinations where English is widely spoken.