"""
prepara_attributi.py - Collega alle regioni delle reti gli attributi che servono per le ipotesi.

Da lanciare dopo costruisci_reti.py, dalla stessa cartella:
    python prepara_attributi.py

LEGGE (nella cartella dello script)
  reti/regioni.csv                    le regioni delle reti (da costruisci_reti.py)
  NUTS_RG_20M_2016_4326.geojson       confini 2016: nomi e posizione delle regioni   [obbligatorio]
  Eurostat_PIL_NUTS2.csv              PIL Eurostat (nama_10r_2gdp)                    [obbligatorio]
  NUTS_RG_20M_2021_4326.geojson       confini 2021  - facoltativo, per Croazia e Norvegia
  NUTS_RG_20M_2024_4326.geojson       confini 2024  - facoltativo, per Portogallo e Paesi Bassi
  Se il file del PIL contiene anche l'unita' MIO_EUR (PIL totale), le regioni da ricombinare
  vengono calcolate in modo esatto; altrimenti con una media semplice, segnalata.
  Le regioni senza corrispondenza esatta (es. PT16 e PT18, divise da Eurostat nel 2024) sono
  approssimate unendo le regioni sovrapposte, ognuna per la parte di area che cade dentro.

SCRIVE (in reti/)
  regioni_attributi.csv   per ogni regione: nome, paese, PIL per abitante di ogni periodo,
                          e una nota su come e' stato ottenuto il valore
  coppie_regioni.csv      per ogni coppia di regioni: distanza in km, stesso paese,
                          stessa lingua ufficiale, stessa famiglia linguistica
  lingue.csv              per ogni paese: lingue ufficiali e famiglie linguistiche
  attributi.txt           riepilogo (per la sezione Data del report)
"""

import json
import math
from itertools import combinations
from pathlib import Path

import pandas as pd
from shapely.geometry import shape
from shapely.ops import unary_union

# =============================================================================
# SCELTE
# =============================================================================
RETI = Path("reti")
FILE_PIL = Path("Eurostat_PIL_NUTS2.csv")
CONFINI_RETI = Path("NUTS_RG_20M_2016_4326.geojson")          # versione delle regioni delle reti
CONFINI_NUOVI = [Path("NUTS_RG_20M_2024_4326.geojson"),       # versioni usate da Eurostat per il PIL
                 Path("NUTS_RG_20M_2021_4326.geojson")]       # (si usa la piu' recente disponibile)

UNITA_PIL = "EUR_HAB"     # "EUR_HAB" = euro per abitante; "PPS_EU27_2020_HAB" = parita' di potere d'acquisto
PERIODI = {"pre_covid": (2018, 2019), "covid": (2020, 2021), "post_covid": (2022, 2023)}

# Confronto tra confini: una regione nuova "sta dentro" una vecchia se almeno il 90% della sua
# area cade dentro; la corrispondenza e' "esatta" se le regioni nuove coprono il 95% della vecchia.
QUOTA_DENTRO = 0.90
QUOTA_COPERTURA = 0.95

# Lingue ufficiali nazionali e famiglia linguistica di ogni paese (piu' valori separati da ";")
LINGUE = {
    "AL": ("albanese", "albanese"), "AT": ("tedesco", "germanica"),
    "BE": ("olandese;francese;tedesco", "germanica;romanza"), "BG": ("bulgaro", "slava"),
    "CY": ("greco;turco", "ellenica;turcica"), "CZ": ("ceco", "slava"), "DE": ("tedesco", "germanica"),
    "DK": ("danese", "germanica"), "EE": ("estone", "uralica"), "EL": ("greco", "ellenica"),
    "ES": ("spagnolo", "romanza"), "FI": ("finlandese;svedese", "uralica;germanica"),
    "FR": ("francese", "romanza"), "HR": ("croato", "slava"), "HU": ("ungherese", "uralica"),
    "IE": ("inglese;irlandese", "germanica;celtica"), "IS": ("islandese", "germanica"),
    "IT": ("italiano", "romanza"), "LI": ("tedesco", "germanica"), "LT": ("lituano", "baltica"),
    "LU": ("lussemburghese;francese;tedesco", "germanica;romanza"), "LV": ("lettone", "baltica"),
    "ME": ("montenegrino", "slava"), "MK": ("macedone", "slava"), "MT": ("maltese;inglese", "semitica;germanica"),
    "NL": ("olandese", "germanica"), "NO": ("norvegese", "germanica"), "PL": ("polacco", "slava"),
    "PT": ("portoghese", "romanza"), "RO": ("rumeno", "romanza"), "RS": ("serbo", "slava"),
    "SE": ("svedese", "germanica"), "SI": ("sloveno", "slava"), "SK": ("slovacco", "slava"),
    "TR": ("turco", "turcica"), "UK": ("inglese", "germanica"),
}
# =============================================================================

righe = []


def scrivi(testo=""):
    print(testo)
    righe.append(str(testo))


def leggi_confini(file):
    """Regioni NUTS 2 di un file GISCO: {codice: (nome, geometria)}."""
    dati = json.loads(Path(file).read_text(encoding="utf-8"))
    out = {}
    for f in dati["features"]:
        p = f["properties"]
        if p["LEVL_CODE"] == 2:
            out[p["NUTS_ID"]] = (p.get("NAME_LATN") or p.get("NUTS_NAME"), shape(f["geometry"]).buffer(0))
    return out


def leggi_pil():
    pil = pd.read_csv(FILE_PIL)
    pil = pil[pil["geo"].astype(str).str.len() == 4]
    unita = sorted(pil["unit"].unique())
    if UNITA_PIL not in unita:
        raise SystemExit(f"Nel file del PIL non c'e' l'unita' {UNITA_PIL}. Unita' presenti: {unita}")
    tab = pil.pivot_table(index=["geo", "TIME_PERIOD"], columns="unit", values="OBS_VALUE")
    return tab, unita


def valore_annuale(tab, codici, anno, con_totali, quote=None):
    """PIL per abitante di un insieme di regioni in un anno. None se manca qualcosa.
    quote = parte di ogni regione da contare (1 = tutta; es. 0.53 = solo la parte che cade
    nella regione delle reti, con abitanti stimati in proporzione all'area)."""
    quote = quote or [1.0] * len(codici)
    try:
        righe_anno = [tab.loc[(c, anno)] for c in codici]
    except KeyError:
        return None
    pro_capite = [r[UNITA_PIL] for r in righe_anno]
    if any(pd.isna(v) for v in pro_capite):
        return None
    if len(codici) == 1:
        return pro_capite[0]
    if con_totali:
        # abitanti di ogni regione = PIL totale in euro / PIL per abitante in euro
        totali = [r.get("MIO_EUR") for r in righe_anno]
        euro_ab = [r.get("EUR_HAB") for r in righe_anno]
        if not any(pd.isna(x) for x in totali + euro_ab):
            abitanti = [q * t * 1e6 / e for q, t, e in zip(quote, totali, euro_ab)]
            # valore per abitante dell'area unita = media dei valori pesata per gli abitanti
            # (in euro equivale a: somma dei PIL / somma degli abitanti)
            return sum(p * a for p, a in zip(pro_capite, abitanti)) / sum(abitanti)
    return sum(p * q for p, q in zip(pro_capite, quote)) / sum(quote)   # media semplice (approssimata)


def corrispondenze(regioni, confini_reti, confini_pil, codici_pil):
    """Per ogni regione delle reti trova le regioni del file del PIL che la rappresentano.
    Restituisce {regione: (codici, quote, tipo)}; quote = parte di ogni codice da contare."""
    out = {}
    paesi_pil = {c[:2] for c in codici_pil}
    for reg in regioni:
        parti = reg.split("+")
        if reg[:2] not in paesi_pil:
            out[reg] = ([], [], "escluso dalle analisi sul PIL: paese assente dal file Eurostat "
                                "(la regione resta nelle reti)")
            continue
        if all(p in codici_pil for p in parti):
            out[reg] = (parti, [1.0] * len(parti), "diretto" if len(parti) == 1 else "ricombinato")
            continue
        if not confini_pil or not all(p in confini_reti for p in parti):
            out[reg] = ([], [], "manca")
            continue
        area = unary_union([confini_reti[p][1] for p in parti])
        # candidati: regioni del file del PIL che si sovrappongono davvero (non solo confinanti);
        # per ognuna: quota della SUA area che cade nella regione delle reti
        candidati = {}
        for c, (_, g) in confini_pil.items():
            if c in codici_pil and c[:2] == reg[:2]:
                comune = g.intersection(area).area
                if comune / area.area > 0.01:
                    candidati[c] = (comune, comune / g.area)
        if not candidati:
            out[reg] = ([], [], "manca: codice non presente nel PIL e nessuna regione sovrapposta "
                                "(servono i confini della versione NUTS usata da Eurostat)")
            continue
        # copertura misurata sulla terra disegnata in entrambe le versioni: i confini semplificati
        # tracciano coste ed estuari in modo diverso, e quella differenza non e' un cambio di regione
        terra = sum(comune for comune, _ in candidati.values())
        dentro = sorted(c for c, (_, quota) in candidati.items() if quota >= QUOTA_DENTRO)
        copertura = sum(candidati[c][0] for c in dentro) / terra
        if dentro and copertura >= QUOTA_COPERTURA:
            out[reg] = (dentro, [1.0] * len(dentro), "ricombinato" if len(dentro) > 1 else "ricodificato")
        else:
            # nessuna corrispondenza esatta: si uniscono tutte le regioni sovrapposte, contando di
            # ognuna solo la parte che cade dentro (abitanti stimati in proporzione all'area)
            codici = sorted(candidati, key=lambda c: -candidati[c][0])
            quote = [1.0 if candidati[c][1] >= QUOTA_DENTRO else round(candidati[c][1], 2) for c in codici]
            pezzi = [f"{c} ({q:.0%})" if q < 1 else c for c, q in zip(codici, quote)]
            out[reg] = (codici, quote, "approssimato da " + " + ".join(pezzi)
                        + " (tra parentesi: quota dell'area, abitanti stimati in proporzione)")
    return out


def pil_per_periodo(tab, codici, quote, con_totali):
    """Media degli anni del periodo; se mancano tutti, l'ultimo anno precedente disponibile."""
    valori, note = {}, []
    anni_dati = sorted({a for (_, a) in tab.index})
    for nome, (a, b) in PERIODI.items():
        annuali = [v for anno in range(a, b + 1)
                   if (v := valore_annuale(tab, codici, anno, con_totali, quote)) is not None]
        if annuali:
            valori[nome] = round(sum(annuali) / len(annuali), 1)
            if len(annuali) < b - a + 1:
                note.append(f"{nome}: solo {len(annuali)} anno su {b - a + 1}")
            continue
        precedenti = [anno for anno in anni_dati if anno < a
                      and valore_annuale(tab, codici, anno, con_totali, quote) is not None]
        if precedenti:
            valori[nome] = round(valore_annuale(tab, codici, precedenti[-1], con_totali, quote), 1)
            note.append(f"{nome}: usato il {precedenti[-1]}")
        else:
            valori[nome] = None
    return valori, note


def distanza_km(p1, p2):
    """Distanza sul globo (formula di haversine) tra due punti (lon, lat)."""
    lon1, lat1, lon2, lat2 = map(math.radians, (*p1, *p2))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def main():
    regioni = pd.read_csv(RETI / "regioni.csv")["regione"].tolist()
    confini_reti = leggi_confini(CONFINI_RETI)

    # --- nomi e posizione ---------------------------------------------------------
    nomi, centri = {}, {}
    for reg in regioni:
        parti = reg.split("+")
        nomi[reg] = " + ".join(confini_reti[p][0] for p in parti if p in confini_reti)
        geom = unary_union([confini_reti[p][1] for p in parti if p in confini_reti])
        punto = geom.representative_point() if not geom.centroid.within(geom) else geom.centroid
        centri[reg] = (punto.x, punto.y)

    # --- PIL ----------------------------------------------------------------------
    tab, unita = leggi_pil()
    con_totali = "MIO_EUR" in unita and "EUR_HAB" in unita
    codici_pil = {g for (g, _) in tab.index}
    confini_pil = {}
    for f in reversed(CONFINI_NUOVI):                       # il piu' recente sovrascrive
        if f.exists():
            confini_pil.update(leggi_confini(f))
    scrivi(f"PIL: unita' usata {UNITA_PIL}; PIL totale (MIO_EUR) "
           f"{'presente: ricombinazioni esatte' if con_totali else 'ASSENTE: ricombinazioni con media semplice'}")
    scrivi("Confini usati per le corrispondenze: "
           + (", ".join(f.name for f in CONFINI_NUOVI if f.exists()) or "nessuno"))

    corr = corrispondenze(regioni, confini_reti, confini_pil, codici_pil)
    tabella = []
    for reg in regioni:
        codici, quote, tipo = corr[reg]
        valori, note = (pil_per_periodo(tab, codici, quote, con_totali) if codici
                        else ({p: None for p in PERIODI}, []))
        if len(codici) > 1 and not con_totali:
            note.insert(0, "media semplice")
        nota = tipo + (f" da {'+'.join(codici)}" if tipo in ("ricombinato", "ricodificato") else "")
        tabella.append({"regione": reg, "nome": nomi[reg], "paese": reg[:2],
                        **{f"pil_{p}": valori[p] for p in PERIODI},
                        "nota_pil": "; ".join([nota] + note)})
    att = pd.DataFrame(tabella)
    att.to_csv(RETI / "regioni_attributi.csv", index=False)

    scrivi("\nREGIONI CON PIL PER PERIODO:")
    for p in PERIODI:
        manca = att[att[f"pil_{p}"].isna()]
        scrivi(f"  {p:<11} con PIL {len(att) - len(manca)} su {len(att)}   senza: "
               + (", ".join(f"{k} {v}" for k, v in manca["paese"].value_counts().items()) or "nessuna"))
    scrivi("\nREGIONI NON DIRETTE (ricodificate, ricombinate, approssimate o senza dati):")
    altre = att[~att["nota_pil"].str.startswith("diretto")]
    for _, r in altre[altre["paese"] != "UK"].iterrows():
        scrivi(f"  {r['regione']:<22} {r['nome'][:35]:<35} {r['nota_pil']}")
    n_uk = (altre["paese"] == "UK").sum()
    if n_uk:
        scrivi(f"  ... e {n_uk} regioni del Regno Unito: {altre.loc[altre['paese'] == 'UK', 'nota_pil'].iloc[0]}")
    note_anni = att[att["nota_pil"].str.contains("usato il|solo ")]
    if len(note_anni):
        scrivi("\nPERIODI CON ANNI MANCANTI:")
        for _, r in note_anni.iterrows():
            scrivi(f"  {r['regione']:<22} {r['nota_pil']}")

    # --- lingue -------------------------------------------------------------------
    paesi = sorted({r[:2] for r in regioni})
    mancanti = [p for p in paesi if p not in LINGUE]
    if mancanti:
        raise SystemExit(f"Aggiungi la lingua di questi paesi nella tabella LINGUE: {mancanti}")
    pd.DataFrame([{"paese": p, "lingue": LINGUE[p][0], "famiglie": LINGUE[p][1]} for p in paesi]) \
        .to_csv(RETI / "lingue.csv", index=False)

    # --- coppie di regioni --------------------------------------------------------
    insieme = {p: (set(LINGUE[p][0].split(";")), set(LINGUE[p][1].split(";"))) for p in paesi}
    coppie = []
    for a, b in combinations(regioni, 2):
        pa, pb = a[:2], b[:2]
        coppie.append({"regione_a": a, "regione_b": b,
                       "distanza_km": round(distanza_km(centri[a], centri[b]), 1),
                       "stesso_paese": int(pa == pb),
                       "stessa_lingua": int(bool(insieme[pa][0] & insieme[pb][0])),
                       "stessa_famiglia": int(bool(insieme[pa][1] & insieme[pb][1]))})
    cp = pd.DataFrame(coppie)
    cp.to_csv(RETI / "coppie_regioni.csv", index=False)
    estere = cp[cp["stesso_paese"] == 0]
    scrivi(f"\nCOPPIE DI REGIONI: {len(cp):,} (di paesi diversi: {len(estere):,})")
    scrivi(f"  distanza tra regioni di paesi diversi: mediana {estere['distanza_km'].median():,.0f} km, "
           f"min {estere['distanza_km'].min():,.0f}, max {estere['distanza_km'].max():,.0f}")
    scrivi(f"  coppie di paesi diversi con stessa lingua: {estere['stessa_lingua'].mean():.1%}; "
           f"con stessa famiglia linguistica: {estere['stessa_famiglia'].mean():.1%}")

    scrivi(f"\nFile salvati in {RETI}/: regioni_attributi.csv, coppie_regioni.csv, lingue.csv")
    (RETI / "attributi.txt").write_text("\n".join(righe) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()