"""
reti_binarie.py - Salva la versione binaria delle reti di periodo.

Nella versione binaria un arco esiste (1) o non esiste (0): si tiene solo se in quel periodo
ci sono stati, in media, almeno SOGLIA studenti l'anno. Serve per le misure che non usano
i pesi (k-core, clustering, small-world, centralizzazione...).

Da lanciare dopo costruisci_reti.py, dalla stessa cartella:
    python reti_binarie.py

Legge   reti/rete_<periodo>.csv
Scrive  reti/rete_<periodo>_soglia<N>.csv   (colonne: origine, destinazione)
        per la soglia principale e per quella di controllo,
        reti/reti_binarie.txt                (riepilogo, per la sezione Data)
"""

from pathlib import Path

import networkx as nx
import pandas as pd

RETI = Path("reti")
PERIODI = ["pre_covid", "covid", "post_covid"]
SOGLIA = 5              # scelta principale: almeno 5 studenti l'anno (vedi verifica_soglia.csv)
SOGLIA_CONTROLLO = 3    # seconda soglia, per il controllo di robustezza

righe = []


def scrivi(testo=""):
    print(testo)
    righe.append(str(testo))


def main():
    n_regioni = len(pd.read_csv(RETI / "regioni.csv"))
    scrivi(f"Reti binarie: un arco resta se ha in media almeno N studenti l'anno "
           f"(percentuali su {n_regioni} regioni)\n")
    scrivi(f"{'rete':<12} {'soglia':>6} {'regioni':>8} {'archi':>7} {'densita':>8} "
           f"{'studenti tenuti':>16} {'regioni connesse':>17}")
    for soglia in (SOGLIA, SOGLIA_CONTROLLO):
        for periodo in PERIODI:
            rete = pd.read_csv(RETI / f"rete_{periodo}.csv")
            tenuta = rete[rete["studenti"] >= soglia]
            tenuta[["origine", "destinazione"]].to_csv(RETI / f"rete_{periodo}_soglia{soglia}.csv", index=False)

            G = nx.from_pandas_edgelist(tenuta, "origine", "destinazione", create_using=nx.DiGraph)
            comp = max((len(c) for c in nx.weakly_connected_components(G)), default=0)
            scrivi(f"{periodo:<12} {soglia:>6} {G.number_of_nodes():>8} {G.number_of_edges():>7,} "
                   f"{nx.density(G):>8.4f} {tenuta['studenti'].sum() / rete['studenti'].sum():>15.1%} "
                   f"{comp / n_regioni:>16.1%}")
        scrivi()
    scrivi(f"File salvati in {RETI}/: rete_<periodo>_soglia{SOGLIA}.csv (principale) e "
           f"rete_<periodo>_soglia{SOGLIA_CONTROLLO}.csv (controllo)")
    (RETI / "reti_binarie.txt").write_text("\n".join(righe) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()