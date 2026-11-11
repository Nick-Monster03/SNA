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

# Paesi esclusi (codice NUTS): la Svizzera non partecipa pienamente a Erasmus+
PAESI_ESCLUSI = ["CH"]

# Regioni che cambiano codice tra NUTS 2016 (dati fino al 2020) e NUTS 2021 (dal 2021).
# Si riuniscono in un codice unico, cosi' la stessa regione ha lo stesso codice in tutti gli anni.
CODICI_DA_UNIRE = {
    # Croazia: nel 2021 la regione continentale HR04 e' stata divisa in tre
    "HR02": "HR04", "HR05": "HR04", "HR06": "HR04",
    # Norvegia: nel 2021 le regioni del sud e dell'ovest sono state ridisegnate
    "NO01": "NOX1", "NO03": "NOX1", "NO04": "NOX1", "NO05": "NOX1",
    "NO08": "NOX1", "NO09": "NOX1", "NO0A": "NOX1",
    "NO0B": "NO07",
    # Irlanda del Nord: codice diverso nei due periodi
    "UKN1": "UKN0",
}
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
    print(f"\nTIPI DI MOBILITA' (colonna '{COLONNA_ATTIVITA}'), studenti:")
    print(df.groupby(COLONNA_ATTIVITA)[COL_STUD].sum().astype(int)
          .sort_values(ascending=False).head(12).to_string())


def passo(nome, prima, df, motivo):
    dopo = df[COL_STUD].sum()
    log(f"  {nome:<22} tolti {prima - dopo:>9,.0f}  restano {dopo:>9,.0f}   ({motivo})")


def codici_spaiati(df):
    """Codici regionali presenti solo prima del 2021 o solo dal 2021."""
    prima = set(df.loc[df[COL_ANNO] < 2021, ["origine", "destinazione"]].values.ravel())
    dopo = set(df.loc[df[COL_ANNO] >= 2021, ["origine", "destinazione"]].values.ravel())
    return sorted(prima - dopo), sorted(dopo - prima)


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

    # 4. paesi esclusi
    prima = df[COL_STUD].sum()
    df = df[~df["origine"].str[:2].isin(PAESI_ESCLUSI) & ~df["destinazione"].str[:2].isin(PAESI_ESCLUSI)]
    passo("3. paesi esclusi", prima, df, ", ".join(PAESI_ESCLUSI))

    # 5. codici cambiati tra NUTS 2016 e NUTS 2021
    solo_prima, solo_dopo = codici_spaiati(df)
    log(f"\n  Codici presenti solo fino al 2020: {solo_prima}")
    log(f"  Codici presenti solo dal 2021:     {solo_dopo}")
    df["origine"] = df["origine"].replace(CODICI_DA_UNIRE)
    df["destinazione"] = df["destinazione"].replace(CODICI_DA_UNIRE)
    solo_prima, solo_dopo = codici_spaiati(df)
    log(f"  Dopo l'unione dei codici, ancora spaiati: {solo_prima + solo_dopo}\n")

    # 6. flussi interni a un paese (l'Erasmus e' mobilita' verso l'estero)
    prima = df[COL_STUD].sum()
    df = df[df["origine"].str[:2] != df["destinazione"].str[:2]]
    passo("4. flussi interni", prima, df, "stesso paese di origine e destinazione")

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