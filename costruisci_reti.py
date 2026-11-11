"""
costruisci_reti.py - Costruisce le reti Erasmus+ tra regioni europee (NUTS 2).

Dati: dataset di Vaisanen et al. (2025), Scientific Data,
      https://doi.org/10.1038/s41597-025-04789-0 - file su https://zenodo.org/records/16737523

Il file dei dati deve stare nella STESSA cartella di questo script. Lo script cerca
qualunque file che si chiami "Erasmus_..._individual..." e contenga "parquet" nel nome, ad es.:
  - Erasmus_2014-2023_individual.parquet         (versione consigliata, fino al 2023)
  - Erasmus_2014-2022_individual.parquet.gzip    (versione vecchia, fino al 2022)
Se ne trova piu' d'uno, usa quello con l'anno finale piu' recente.

Uso, dalla cartella in cui si trovano lo script e il file dei dati:
    python costruisci_reti.py --esplora    # mostra solo com'e' fatto il dataset
    python costruisci_reti.py              # costruisce le reti

Risultato, nella sottocartella reti/:
  rete_<anno>.csv        una rete per anno     (origine, destinazione, studenti)
  rete_<periodo>.csv     una rete per periodo  (peso = media annua di studenti)
  regioni.csv            elenco dei nodi con il paese
  paesi_esclusi.csv      studenti in uscita e in entrata dei paesi esclusi, anno per anno
  log_costruzione.txt    cosa e' stato tolto a ogni passo (per la sezione Data del report)
"""

import sys
from pathlib import Path

import pandas as pd

# =============================================================================
# SCELTE - ognuna va motivata nel documento delle decisioni
# =============================================================================
MODELLO_NOME_FILE = "Erasmus_*individual*parquet*"   # file dei dati cercato nella cartella
CARTELLA_RETI = Path("reti")

# Solo mobilita' per studio: si tengono le righe la cui attivita' contiene questo testo
COLONNA_ATTIVITA = "Activity (mob)"
TESTO_STUDIO = "for studies"

# Primo anno (anno di INIZIO della mobilita'). L'ultimo dipende dal file trovato.
PRIMO_ANNO = 2016

# Periodi di due anni. Se il file arriva solo al 2022, il post-Covid avra' un solo anno.
PERIODI = {"pre_covid": (2018, 2019), "covid": (2020, 2021), "post_covid": (2022, 2023)}

# Paesi: si tengono solo quelli che MANDANO studenti in tutti gli anni analizzati.
# Un paese che riceve ma non manda (o compare solo in alcuni anni) non partecipa davvero
# al programma e renderebbe le reti di anni diversi non confrontabili.
# La lista dei paesi esclusi viene calcolata dai dati e stampata.

# Codici delle regioni: dal 2021 il dataset usa la classificazione NUTS 2021, prima la NUTS 2016.
# Le corrispondenze tra codici vecchi e nuovi vengono ricavate dai dati: se una citta' sta
# nella regione A fino al 2020 e nella regione B dal 2021, A e B sono la stessa area.
ANNO_CAMBIO_NUTS = 2021
# =============================================================================

COL_ANNO, COL_ORIG, COL_DEST, COL_STUD = "year", "orig_NUTS", "dest_NUTS", "Actual Participants"
righe_log = []


def log(testo=""):
    print(testo)
    righe_log.append(testo)


def trova_file():
    trovati = sorted(Path(".").glob(MODELLO_NOME_FILE), reverse=True)   # 2023 prima di 2022
    if not trovati:
        presenti = "\n  - ".join(sorted(p.name for p in Path(".").iterdir() if p.is_file()))
        sys.exit("Nessun file dei dati trovato in questa cartella.\n"
                 f"Cerco un file che corrisponda a: {MODELLO_NOME_FILE}\n"
                 f"File presenti nella cartella:\n  - {presenti}")
    if len(trovati) > 1:
        print("Trovati piu' file dei dati, uso il primo:", ", ".join(p.name for p in trovati))
    return trovati[0]


def esplora(df):
    """Mostra com'e' fatto il dataset, senza scrivere nessun file."""
    print(f"\nRighe: {len(df):,}   Studenti: {df[COL_STUD].sum():,.0f}\n")
    print("COLONNE:")
    for c in df.columns:
        esempio = str(df[c].dropna().iloc[0])[:50] if df[c].notna().any() else ""
        print(f"  {c:<28} es. {esempio}")
    print("\nSTUDENTI PER ANNO:")
    print(df.groupby(COL_ANNO)[COL_STUD].sum().astype(int).to_string())
    print(f"\nTIPI DI MOBILITA' (colonne '{COLONNA_ATTIVITA}' e 'Field'), studenti:")
    tipi = (df.groupby([COLONNA_ATTIVITA, "Field"])[COL_STUD].sum().astype(int)
              .sort_values(ascending=False).reset_index())
    for _, r in tipi.iterrows():
        tenuta = TESTO_STUDIO.lower() in str(r[COLONNA_ATTIVITA]).lower()
        print(f"  {'TENUTA ' if tenuta else 'esclusa'}  {r[COL_STUD]:>9,}  {r[COLONNA_ATTIVITA][:70]:<70}  [{r['Field']}]")


def passo(nome, prima, df, motivo):
    dopo = df[COL_STUD].sum()
    log(f"  {nome:<22} tolti {prima - dopo:>9,.0f}  restano {dopo:>9,.0f}   ({motivo})")


def codici_spaiati(df):
    """Codici regionali presenti solo prima del cambio NUTS o solo dopo."""
    prima = set(df.loc[df[COL_ANNO] < ANNO_CAMBIO_NUTS, ["origine", "destinazione"]].values.ravel())
    dopo = set(df.loc[df[COL_ANNO] >= ANNO_CAMBIO_NUTS, ["origine", "destinazione"]].values.ravel())
    return prima - dopo, dopo - prima, prima & dopo


def descrivi_paesi_esclusi(df, esclusi, anni):
    """Mostra i dati dei paesi che verranno esclusi, prima di toglierli.

    Per ogni paese stampa (e salva in reti/paesi_esclusi.csv) gli studenti in uscita e in
    entrata anno per anno, il peso sul totale, i paesi con cui scambia e i tipi di mobilita'.
    """
    if not esclusi:
        return
    totale = df[COL_STUD].sum()
    righe_csv = []
    log("\n  PAESI CHE VERRANNO ESCLUSI - i loro dati prima dell'esclusione:")
    for paese in esclusi:
        esce = df[df["origine"].str[:2] == paese]
        entra = df[df["destinazione"].str[:2] == paese]
        coinvolti = df[(df["origine"].str[:2] == paese) | (df["destinazione"].str[:2] == paese)]
        log(f"\n  {paese}: {coinvolti[COL_STUD].sum():,.0f} studenti coinvolti "
            f"({coinvolti[COL_STUD].sum() / totale:.3%} del totale), "
            f"{esce[COL_STUD].sum():,.0f} in uscita, {entra[COL_STUD].sum():,.0f} in entrata")

        log(f"    {'anno':<6} {'uscita':>8} {'entrata':>8}")
        uscita = esce.groupby(COL_ANNO)[COL_STUD].sum()
        entrata = entra.groupby(COL_ANNO)[COL_STUD].sum()
        for anno in anni:
            u, e = int(uscita.get(anno, 0)), int(entrata.get(anno, 0))
            log(f"    {anno:<6} {u:>8,} {e:>8,}")
            righe_csv.append({"paese": paese, "anno": anno, "studenti_in_uscita": u, "studenti_in_entrata": e})

        if len(entra):
            da = entra.groupby(entra["origine"].str[:2])[COL_STUD].sum().sort_values(ascending=False)
            log("    studenti in entrata provenienti da: "
                + ", ".join(f"{p} {int(n)}" for p, n in da.head(8).items()))
            regioni = entra.groupby("destinazione")[COL_STUD].sum().sort_values(ascending=False)
            log("    regioni di destinazione: " + ", ".join(f"{r} {int(n)}" for r, n in regioni.items()))
        if len(esce):
            verso = esce.groupby(esce["destinazione"].str[:2])[COL_STUD].sum().sort_values(ascending=False)
            log("    studenti in uscita diretti verso: "
                + ", ".join(f"{p} {int(n)}" for p, n in verso.head(8).items()))
        tipi = coinvolti.groupby(COLONNA_ATTIVITA)[COL_STUD].sum().sort_values(ascending=False)
        log("    tipi di mobilita': " + "; ".join(f"{t} ({int(n)})" for t, n in tipi.items()))

    CARTELLA_RETI.mkdir(exist_ok=True)
    pd.DataFrame(righe_csv).to_csv(CARTELLA_RETI / "paesi_esclusi.csv", index=False)
    log(f"\n  Dettaglio per anno salvato in {CARTELLA_RETI}/paesi_esclusi.csv\n")


def corrispondenze_dai_dati(df):
    """Ricava dai dati quali codici vecchi e nuovi indicano la stessa area.

    Per ogni citta' si guarda in quale regione e' stata collocata prima e dopo il cambio
    di classificazione. Se cambia, e uno dei due codici esiste solo in un periodo, i due
    codici vengono collegati. I gruppi di codici collegati diventano un'unica regione.
    """
    solo_prima, solo_dopo, stabili = codici_spaiati(df)
    spaiati = solo_prima | solo_dopo
    luoghi = pd.concat([
        pd.DataFrame({"citta": df["origin"], "codice": df["origine"], "anno": df[COL_ANNO], "w": df[COL_STUD]}),
        pd.DataFrame({"citta": df["destination"], "codice": df["destinazione"], "anno": df[COL_ANNO], "w": df[COL_STUD]}),
    ])
    luoghi["dopo"] = luoghi["anno"] >= ANNO_CAMBIO_NUTS
    # codice prevalente di ogni citta' prima e dopo il cambio
    prevalente = (luoghi.groupby(["citta", "dopo", "codice"])["w"].sum().reset_index()
                  .sort_values("w").groupby(["citta", "dopo"]).tail(1)
                  .pivot(index="citta", columns="dopo", values="codice").dropna())
    prevalente.columns = ["prima", "dopo"]
    cambi = prevalente[(prevalente["prima"] != prevalente["dopo"])
                       & (prevalente["prima"].isin(spaiati) | prevalente["dopo"].isin(spaiati))]
    collegamenti = cambi.groupby(["prima", "dopo"]).size()

    # gruppi di codici collegati (union-find)
    capo = {}

    def radice(c):
        capo.setdefault(c, c)
        while capo[c] != c:
            c = capo[c]
        return c

    for a, b in collegamenti.index:
        capo[radice(a)] = radice(b)
    gruppi = {}
    for c in list(capo):
        gruppi.setdefault(radice(c), set()).add(c)

    # nome del gruppo: il codice stabile se c'e', altrimenti i codici vecchi uniti da "+"
    unione = {}
    for membri in gruppi.values():
        stabile = sorted(membri & stabili)
        nome = stabile[0] if stabile else "+".join(sorted(membri & solo_prima))
        for c in membri:
            unione[c] = nome
    return collegamenti, unione


def main():
    file_dati = trova_file()
    print(f"Leggo {file_dati} ...")
    df = pd.read_parquet(file_dati)
    df[COL_STUD] = pd.to_numeric(df[COL_STUD], errors="coerce").fillna(0)
    df[COL_ANNO] = pd.to_numeric(df[COL_ANNO], errors="coerce")

    if "--esplora" in sys.argv:
        esplora(df)
        return

    ultimo_anno = int(df[COL_ANNO].max())
    log(f"Dataset: {file_dati.name} - {len(df):,} righe, {df[COL_STUD].sum():,.0f} studenti, "
        f"anni {int(df[COL_ANNO].min())}-{ultimo_anno}")
    if ultimo_anno < 2023:
        log(f"ATTENZIONE: il file arriva al {ultimo_anno}: il periodo post-Covid sara' piu' corto degli altri.")
    log("\nPASSI (numero di studenti):")
    log(f"  {'partenza':<22} {'':>15}  restano {df[COL_STUD].sum():>9,.0f}")

    # 1. solo mobilita' per studio
    if COLONNA_ATTIVITA not in df.columns:
        sys.exit(f"Colonna '{COLONNA_ATTIVITA}' non trovata. Lancia con --esplora per vedere le colonne.")
    prima = df[COL_STUD].sum()
    df = df[df[COLONNA_ATTIVITA].astype(str).str.contains(TESTO_STUDIO, case=False, regex=False)]
    passo("1. solo studio", prima, df, f"attivita' che contengono '{TESTO_STUDIO}'")

    # 2. anni
    prima = df[COL_STUD].sum()
    df = df[df[COL_ANNO].between(PRIMO_ANNO, ultimo_anno)].copy()
    df[COL_ANNO] = df[COL_ANNO].astype(int)
    passo("2. anni", prima, df, f"dal {PRIMO_ANNO} al {ultimo_anno}")

    # 3. da NUTS 3 a NUTS 2: i primi 4 caratteri del codice
    df["origine"] = df[COL_ORIG].astype(str).str[:4]
    df["destinazione"] = df[COL_DEST].astype(str).str[:4]

    # 4. paesi: solo quelli che mandano studenti in tutti gli anni
    anni = sorted(df[COL_ANNO].unique())
    invii = df.assign(paese=df["origine"].str[:2]).groupby(["paese", COL_ANNO])[COL_STUD].sum().unstack(fill_value=0)
    invii = invii.reindex(columns=anni, fill_value=0)
    tenuti = set(invii[(invii > 0).all(axis=1)].index)
    tutti = set(df["origine"].str[:2]) | set(df["destinazione"].str[:2])
    esclusi = sorted(tutti - tenuti)
    descrivi_paesi_esclusi(df, esclusi, anni)
    prima = df[COL_STUD].sum()
    df = df[df["origine"].str[:2].isin(tenuti) & df["destinazione"].str[:2].isin(tenuti)]
    passo("3. paesi esclusi", prima, df,
          f"non mandano studenti in tutti gli anni: {', '.join(esclusi) or 'nessuno'}")

    # 5. codici cambiati con la nuova classificazione NUTS: corrispondenze ricavate dai dati
    solo_prima, solo_dopo, _ = codici_spaiati(df)
    log(f"\n  Codici presenti solo fino al {ANNO_CAMBIO_NUTS - 1}: {sorted(solo_prima)}")
    log(f"  Codici presenti solo dal {ANNO_CAMBIO_NUTS}:     {sorted(solo_dopo)}")
    collegamenti, unione = corrispondenze_dai_dati(df)
    log("  Corrispondenze trovate nei dati (citta' che passano da un codice all'altro):")
    for (a, b), n in collegamenti.items():
        log(f"    {a} -> {b}   ({n} citta')")
    log("  Regioni unificate:")
    for nome in sorted(set(unione.values())):
        log(f"    {nome:<22} <- {', '.join(sorted(c for c in unione if unione[c] == nome))}")
    df["origine"] = df["origine"].replace(unione)
    df["destinazione"] = df["destinazione"].replace(unione)

    # codici rimasti senza corrispondenza: esistono solo in una parte degli anni
    solo_prima, solo_dopo, _ = codici_spaiati(df)
    rimasti = solo_prima | solo_dopo
    prima = df[COL_STUD].sum()
    df = df[~df["origine"].isin(rimasti) & ~df["destinazione"].isin(rimasti)]
    log("")
    passo("4. codici senza pari", prima, df,
          f"regioni presenti solo in parte degli anni: {', '.join(sorted(rimasti)) or 'nessuna'}")

    # 6. flussi interni a un paese (l'Erasmus e' mobilita' verso l'estero)
    prima = df[COL_STUD].sum()
    df = df[df["origine"].str[:2] != df["destinazione"].str[:2]]
    passo("5. flussi interni", prima, df, "stesso paese di origine e destinazione")

    # 7. reti annuali
    CARTELLA_RETI.mkdir(exist_ok=True)
    for vecchio in CARTELLA_RETI.glob("rete_*.csv"):
        vecchio.unlink()
    annuali = (df.groupby([COL_ANNO, "origine", "destinazione"], as_index=False)[COL_STUD].sum()
                 .rename(columns={COL_STUD: "studenti"}))
    annuali["studenti"] = annuali["studenti"].astype(int)
    log("\nRETI ANNUALI:")
    for anno, rete in annuali.groupby(COL_ANNO):
        rete = rete[["origine", "destinazione", "studenti"]]
        rete.to_csv(CARTELLA_RETI / f"rete_{anno}.csv", index=False)
        nodi = len(set(rete["origine"]) | set(rete["destinazione"]))
        log(f"  rete_{anno}.csv   {nodi:>4} regioni  {len(rete):>7,} archi  {rete['studenti'].sum():>8,} studenti")

    # 8. reti di periodo: media annua di studenti
    log("\nRETI DI PERIODO (media annua):")
    for nome, (a, b) in PERIODI.items():
        b = min(b, ultimo_anno)
        if a > b:
            log(f"  {nome}: saltato, il file non contiene questi anni")
            continue
        sel = annuali[annuali[COL_ANNO].between(a, b)]
        rete = sel.groupby(["origine", "destinazione"], as_index=False)["studenti"].sum()
        rete["studenti"] = (rete["studenti"] / (b - a + 1)).round(2)
        rete.to_csv(CARTELLA_RETI / f"rete_{nome}.csv", index=False)
        nodi = len(set(rete["origine"]) | set(rete["destinazione"]))
        log(f"  rete_{nome}.csv ({a}-{b})   {nodi:>4} regioni  {len(rete):>7,} archi  "
            f"{rete['studenti'].sum():>10,.0f} studenti l'anno")

    # 9. elenco dei nodi
    regioni = sorted(set(annuali["origine"]) | set(annuali["destinazione"]))
    pd.DataFrame({"regione": regioni, "paese": [r[:2] for r in regioni]}).to_csv(
        CARTELLA_RETI / "regioni.csv", index=False)
    log(f"\nIn totale: {len(regioni)} regioni di {len(set(r[:2] for r in regioni))} paesi")

    (CARTELLA_RETI / "log_costruzione.txt").write_text("\n".join(righe_log) + "\n", encoding="utf-8")
    print(f"\nFatto. File salvati nella cartella {CARTELLA_RETI}/")


if __name__ == "__main__":
    main()