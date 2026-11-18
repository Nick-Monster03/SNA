1. Regole da rispettare
Report in PDF, in inglese, massimo 5.000 parole anche dopo le revisioni (circa 9–10 pagine); oltre il limite c'è una penalità. Per sicurezza contare anche tabelle e didascalie, esclusa solo la bibliografia.
Usare il template del professore (Overleaf/LaTeX o Word).
Principio A → B → C per ogni misura e ogni test: A) quale fenomeno si studia; B) quale misura si applica; C) cosa significa la misura in questa rete.
Voto: 20% contesto, problema e motivazione; 60% dati, validità e affidabilità, misure e loro giustificazione, ipotesi, test e risultati; 20% interpretazione complessiva e critica breve.
Checklist del professore (da coprire tutta):
quante reti si analizzano e di che forma sono (qui tutte monomodali);
per ogni rete: cosa sono i nodi, quando esiste un arco, se è orientata;
una gamma ampia di misure (centralità, gruppi, clustering, omofilia, small-world, scale-free, coesione, connettività, compattezza, triad census, core–periphery);
per ogni misura, perché la si usa e cosa significa nella rete;
sforzo adeguato a 4 persone: dirlo esplicitamente. Lo stesso disegno è applicato a tre reti di periodo (più 8 reti annuali), che è proprio il suggerimento del professore.

L'analisi è congelata (tag analysis-freeze): non si calcola niente di nuovo. Ogni numero del report deve venire da 05_analysis/tables/ o 05_analysis/reports/.

2. Sezione per sezione: fonti, cosa c'è già, cosa manca
1. Introduction (850)
Fonti: roadmap (01_organization/Roadmap_...pdf, pag. 1 e sezioni 2 e 7.1); paper in 02_literature/; schede in 03_reading_notes/.
Già scritto: niente come testo.
Da scrivere:
contesto: Erasmus+ e le gerarchie tra regioni;
problema: manca una lettura regionale e recente che includa Covid e Brexit;
motivazione: politiche di coesione;
domanda di ricerca e H1–H3 in tre righe;
una frase sullo stesso disegno applicato a più reti.
Densa: niente frasi generiche sull'Erasmus.
2. Data (600)
Fonti:
01_organization/decisions.txt (SOURCE e punti 1–16, 22);
06_report/section_2_data_draft.md (vecchia bozza, solo come base);
04_data/networks/logs/ (checks_report.txt, attributes_report.txt, build_log.txt).
Tabella 1 obbligatoria: una riga per versione della rete. Nodi = 319 regioni NUTS 2 di 36 paesi. Versioni:
pesata e orientata (peso = media annua degli studenti);
binaria e orientata (arco se ≥ 5 studenti l'anno; controllo con soglia 3);
binaria non orientata (arco se esiste almeno una direzione);
8 reti annuali pesate (2016–2023).
Periodi: pre_covid 2018–19, covid 2020–21, post_covid 2022–23.
Attenzione, la vecchia bozza contiene due errori:
il 2014–2015 è escluso per i codici NUTS 2013 e perché il PIL parte dal 2016, non per il "partial rollout";
la lingua ora è la lingua più parlata di ogni regione (decisions 22), non "una lingua ufficiale in comune".
Da aggiungere (non c'è nella bozza):
il paper valida i dati solo fino al 2022 (il 2023 va oltre);
PIL in euro correnti, senza correzione per l'inflazione;
perché non la soglia 10 (la rete Covid si spezza);
il Regno Unito resta nelle reti perché è parte di H3, ma esce dalle analisi sul PIL (43 regioni senza PIL: UK, IS, LI);
le coppie dello stesso paese sono zeri strutturali.
Da verificare sul paper di Väisänen prima di scriverlo: "studenti maggiorenni e soggiorni di almeno 3 mesi".
3. Methods (1.400)
Fonti:
05_analysis/measures_summary.md: le frasi A → B → C di tutte le 11 misure, da accorciare;
06_report/section_3_network_measures.md, sezione 0: quale versione della rete per ogni misura, zeri strutturali, modelli nulli, seed;
decisions.txt punti 17–26: test delle ipotesi;
le docstring degli script 05_analysis/05_h1_wealth.py, 06_h2_mrqap.py, 07_h3_change.py.
Convenzioni da dire una volta:
versione della rete usata per ogni misura;
densità e modelli nulli calcolati solo sulle coppie tra paesi diversi;
tutti i p-value da permutazioni (le regioni non sono osservazioni indipendenti);
seed 42.
Ipotesi e test:
H1: regressione del bilancio netto sul log del PIL pro capite, 5.000 permutazioni. Tre modelli: tutte le regioni; senza Turchia; dentro ogni paese.
H2: MRQAP con Double Semi-Partialling, 1.000 permutazioni, variabile dipendente log(1 + studenti), controllo binario. Tre modelli: M1 della roadmap; M2 con la dimensione delle regioni; M3 con effetti fissi per origine e destinazione. Lingua = lingua più parlata (controllo con la codifica della Fase 2).
H3: confronto descrittivo tra reti più correlazione QAP. Gli anni 2016–2019 sono il riferimento "normale"; il Regno Unito si guarda anno per anno (indice 2019 = 100 contro il resto della rete).
4. Results (1.150)
Fonti:
05_analysis/measures_summary.md (tabella "Key figures across periods" per la tabella 2);
06_report/section_3_network_measures.md (sezioni 1–12);
06_report/table_hypothesis_tests.md (riepilogo per la tabella 3, numeri dei test, controlli di robustezza);
report e tabelle in 05_analysis/.
Già scritto (come appunti): tutto il materiale numerico, compresi i punti aggiunti (quali variabili pesano di più in H2, concentrazione più forte nel 2023, 42% di archi nuovi nel 2021, quarta comunità).
Da fare: trasformarlo in testo. Ogni paragrafo deve rispondere a una parte della domanda di ricerca: i numeri vanno nelle tabelle, non elencati nel testo.
Esiti da riportare:
H1 respinta: l'effetto esiste solo per via della Turchia;
H2 respinta: la distanza non riduce i flussi; la lingua comune li riduce; contano dimensione, PIL simile e famiglia linguistica;
H3 confermata come confronto descrittivo, con tre sfumature: rete mai spezzata, concentrazione che non torna indietro, reciprocità recuperata.
5. Discussion (900)
Fonti:
table_hypothesis_tests.md, righe "For the Discussion": il Lussemburgo, Rusu e la distanza, chi guadagna e chi perde con la Brexit;
section_3_network_measures.md, sezioni 10, 11 (interpretazioni) e 13 (limiti);
decisions.txt (limiti ai punti SOURCE, 11, 18, 21, 24, 25, 26);
06_report/appunti_preliminari_per_results_e_discussion.md (note della Fase 2: verificare che siano ancora coerenti con i risultati).
Da scrivere (manca):
confronto con i paper:
Gadár et al.: la distanza non conta → coerente;
Rusu et al.: la distanza conta e si indebolisce nel tempo → non coerente, anche per la differenza di livello tra paesi e regioni;
Batagelj: la Spagna è l'attrattore principale → coerente;
De Benedictis e Leoni: code pesanti → coerente;
interpretazione dei risultati "strani" di H2:
lingua comune → meno flussi: chi fa l'Erasmus cerca un'altra lingua, ma affine;
distanza positiva: le mete del Sud sono lontane e attraenti, ma con gli effetti fissi il risultato regge;
small-world: σ < 1, il clustering viene dai grandi nodi, non da gruppi locali;
un solo elenco dei limiti, in ordine di importanza:
H3 descrittiva, nessuna prova di causa ("consistent with a Covid effect");
il 2023 oltre la validazione del dataset;
il programma Erasmus+ 2021–27 e i progetti prolungati come fattori confondenti;
il Regno Unito in calo già prima della Brexit;
PIL in euro correnti;
43 regioni senza PIL;
prestigio delle università non misurabile (H1);
materie non analizzabili a livello regionale;
codifica della lingua;
betweenness solo strutturale;
modularità e assortatività di Newman ignorano gli zeri strutturali;
core–periphery trovato con un'euristica;
anni "normali" = solo tre variazioni.