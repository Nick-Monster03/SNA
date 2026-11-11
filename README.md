# SNA
Progetto di Social Network Analysis per lo studio delle reti Erasmus+ tra regioni europee.

## Prerequisiti
- Python 3.x
- file del dataset Erasmus in formato Parquet nella stessa cartella dello script
- file GISCO dei confini NUTS 2:
  - `NUTS_RG_20M_2016_4326.geojson`
  - `NUTS_RG_20M_2021_4326.geojson` (facoltativo, usato per alcune corrispondenze)
  - `NUTS_RG_20M_2024_4326.geojson` (facoltativo, usato per alcune corrispondenze)
- file Eurostat del PIL per regione:
  - `Eurostat_PIL_NUTS2.csv`

Il dataset deve essere presente nella cartella del progetto con un nome del tipo:
`Erasmus_*individual*parquet*`

## Setup
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Workflow completo
```bash
# 1) controlla la struttura del dataset senza generare output
python costruisci_reti.py --esplora

# 2) costruisce le reti annuali e di periodo in reti/
python costruisci_reti.py

# 3) verifica dati, soglie e compatibilità con confini/PIL
python verifiche.py

# 4) genera le reti binarie con soglie 5 e 3
python reti_binarie.py

# 5) prepara attributi per regione (PIL, lingue, distanza, ecc.)
python prepara_attributi.py
```

## Output principali
La cartella `reti/` contiene i file generati dal pipeline, tra cui:
- `rete_2016.csv`, ..., `rete_2023.csv`
- `rete_pre_covid.csv`, `rete_covid.csv`, `rete_post_covid.csv`
- `regioni.csv`
- `regioni_attributi.csv`
- `coppie_regioni.csv`
- `lingue.csv`
- `verifica_soglia.csv`
- `verifiche.txt`
- `attributi.txt`

## Note
- `costruisci_reti.py` legge il dataset più recente disponibile tra i file `Erasmus_*individual*parquet*`.
- `verifiche.py`, `reti_binarie.py` e `prepara_attributi.py` devono essere lanciati dopo `costruisci_reti.py`, nella stessa cartella del progetto.
- Lo script genera i file di rete e i report in `reti/` senza richiedere parametri aggiuntivi.
                      
