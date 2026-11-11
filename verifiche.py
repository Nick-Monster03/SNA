"""
verifiche.py - Verifiche sui dati prima di calcolare le misure (Fase 2).

Da lanciare DOPO costruisci_reti.py, dalla stessa cartella. Usa:
  reti/                          le reti prodotte da costruisci_reti.py
  NUTS_RG_20M_2016_4326.geojson  confini e nomi delle regioni (GISCO)
  Eurostat_PIL_NUTS2.csv         PIL per regione (Eurostat)  - facoltativo

Stampa i risultati e li salva in reti/verifiche.txt.

    python verifiche.py
"""

import json
from pathlib import Path

import networkx as nx
import pandas as pd

RETI = Path("reti")
# Le tre reti da confrontare (prodotte da costruisci_reti.py) e gli anni che contengono
PERIODI = {"pre_covid": (2018, 2019), "covid": (2020, 2021), "post_covid": (2022, 2023)}
SOGLIE = [1, 2, 3, 5, 10, 20]                # studenti l'anno per tenere un arco
FILE_CONFINI = Path("NUTS_RG_20M_2016_4326.geojson")
FILE_PIL = Path("Eurostat_PIL_NUTS2.csv")

righe = []


def scrivi(testo=""):
    print(testo)
    righe.append(str(testo))


def rete(nome):
    """Legge una rete: un anno (es. 2019) o un periodo (es. 'pre_covid')."""
    return pd.read_csv(RETI / f"rete_{nome}.csv")


# -----------------------------------------------------------------------------
def verifica_regno_unito():
    scrivi("=" * 78)
    scrivi("VERIFICA: come cambiano i flussi del Regno Unito (caso Brexit)")
    scrivi("=" * 78)
    anni = sorted(int(p.stem.split("_")[1]) for p in RETI.glob("rete_20*.csv"))
    tab = []
    for a in anni:
        r = rete(a)
        uk_out = r[r.origine.str.startswith("UK")]
        uk_in = r[r.destinazione.str.startswith("UK")]
        tot = r.studenti.sum()
        tab.append({"anno": a,
                    "UK_in_uscita": int(uk_out.studenti.sum()),
                    "UK_in_entrata": int(uk_in.studenti.sum()),
                    "quota_UK_sul_totale_%": round(100 * (uk_out.studenti.sum() + uk_in.studenti.sum()) / tot, 1),
                    "regioni_UK_presenti": len(set(uk_out.origine) | set(uk_in.destinazione))})
    scrivi(pd.DataFrame(tab).to_string(index=False))
    scrivi()


def verifica_soglia():
    scrivi("=" * 78)
    scrivi("VERIFICA: quale soglia usare per la versione binaria della rete")
    scrivi("Reti di periodo: un arco resta solo se ha in media almeno N studenti l'anno.")
    scrivi("=" * 78)
    n_regioni = len(pd.read_csv(RETI / "regioni.csv"))
    tab = []
    for nome in PERIODI:
        r = rete(nome)
        for s in SOGLIE:
            sel = r[r.studenti >= s]
            G = nx.from_pandas_edgelist(sel, "origine", "destinazione", create_using=nx.DiGraph)
            n = G.number_of_nodes()
            wcc = max((len(c) for c in nx.weakly_connected_components(G)), default=0)
            scc = max((len(c) for c in nx.strongly_connected_components(G)), default=0)
            tab.append({"rete": nome, "soglia": s, "regioni_con_archi": n,
                        "archi": G.number_of_edges(),
                        "densita": round(nx.density(G), 4) if n > 1 else 0,
                        "studenti_tenuti_%": round(100 * sel.studenti.sum() / r.studenti.sum(), 1),
                        "regioni_nella_comp_principale_%": round(100 * wcc / n_regioni, 1),
                        "regioni_mutuamente_raggiungibili_%": round(100 * scc / n_regioni, 1)})
    t = pd.DataFrame(tab)
    scrivi(t.to_string(index=False))
    t.to_csv(RETI / "verifica_soglia.csv", index=False)
    scrivi(f"\n(percentuali calcolate su tutte le {n_regioni} regioni; tabella salvata in {RETI}/verifica_soglia.csv)")
    scrivi()


def nomi_regioni():
    g = json.loads(FILE_CONFINI.read_text(encoding="utf-8"))
    return {f["properties"]["NUTS_ID"]: f["properties"]["NAME_LATN"]
            for f in g["features"] if f["properties"]["LEVL_CODE"] == 2}


def verifica_confini():
    scrivi("=" * 78)
    scrivi(f"VERIFICA: le regioni delle reti si trovano nel file dei confini ({FILE_CONFINI.name})?")
    scrivi("=" * 78)
    if not FILE_CONFINI.exists():
        scrivi(f"File {FILE_CONFINI} non trovato: verifica saltata.\n")
        return
    nomi = nomi_regioni()
    reg = pd.read_csv(RETI / "regioni.csv")
    mancanti = []
    for codice in reg.regione:
        parti = codice.split("+")          # le regioni unificate (es. NO01+NO03...) si cercano pezzo per pezzo
        if not all(p in nomi for p in parti):
            mancanti.append(codice)
    scrivi(f"Regioni delle reti: {len(reg)} - trovate: {len(reg) - len(mancanti)} - mancanti: {mancanti or 'nessuna'}")
    scrivi("(le regioni unificate dallo script sono cercate pezzo per pezzo)\n")


def verifica_pil():
    scrivi("=" * 78)
    scrivi(f"VERIFICA: ogni regione delle reti ha il suo PIL ({FILE_PIL.name})?")
    scrivi("=" * 78)
    if not FILE_PIL.exists():
        scrivi(f"File {FILE_PIL} non trovato: verifica saltata.\n")
        return
    pil = pd.read_csv(FILE_PIL)
    pil.columns = [c.strip() for c in pil.columns]
    if "unit" in pil.columns:
        scrivi(f"Unita' presenti nel file: {sorted(pil['unit'].unique())}")
        pil = pil[pil["unit"] == "EUR_HAB"]
    pil = pil[pil["geo"].astype(str).str.len() == 4]           # solo regioni NUTS 2
    reg = pd.read_csv(RETI / "regioni.csv")
    for nome, (a, b) in PERIODI.items():
        # una regione ha il PIL del periodo se c'e' un valore per ogni anno del periodo
        presenti = None
        for anno in range(a, b + 1):
            anno_ok = set(pil.loc[(pil["TIME_PERIOD"] == anno) & pil["OBS_VALUE"].notna(), "geo"])
            presenti = anno_ok if presenti is None else presenti & anno_ok
        mancanti = [c for c in reg.regione if not all(p in presenti for p in c.split("+"))]
        scrivi(f"{nome} ({a}-{b}): regioni senza PIL {len(mancanti)} su {len(reg)}")
        per_paese = pd.Series([m[:2] for m in mancanti]).value_counts()
        if len(per_paese):
            scrivi("      per paese: " + ", ".join(f"{p} {n}" for p, n in per_paese.items()))
            if len(mancanti) <= 40:
                scrivi("      " + ", ".join(mancanti))
    scrivi()


if __name__ == "__main__":
    verifica_regno_unito()
    verifica_soglia()
    verifica_confini()
    verifica_pil()
    (RETI / "verifiche.txt").write_text("\n".join(righe) + "\n", encoding="utf-8")
    print(f"Risultati salvati in {RETI}/verifiche.txt")