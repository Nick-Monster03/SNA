# Appunti preliminari per le sezioni Results e Discussion

*Note raccolte al termine della Fase 2 (costruzione e validazione dati) ed esplorazione visiva preliminare.*

## 1. Impatto della pandemia COVID-19 (Ipotesi H3)
* **Crollo nei volumi:** La mobilità media annua scende del **-30,7%** tra `pre_covid` (230.542 studenti/anno) e `covid` (159.752 studenti/anno). Guardando alle singole annualità, il picco negativo si registra nel **2020** (122.344 studenti, **-46,9%** rispetto ai 230.552 del 2019), seguito da un primo rimbalzo nel **2021** (197.161 studenti).
* **Concentrazione sulle rotte principali:** Nel periodo `post_covid` (2022–2023) i flussi recuperano il **93,8%** del volume pre-pandemico (216.334 studenti/anno, fino a 221.044 nel 2023), ma il numero di collegamenti attivi rimane sensibilmente più basso:
  * Rete pesata: **31.108 archi** nel `post_covid` contro **33.988** nel `pre_covid` (**-8,5%**).
  * Rete binaria ($\ge 5$ stud./anno): **9.963 archi** contro **11.371** (**-12,4%**).
  * *Interpretazione:* La ripresa post-pandemica ha ricostruito i volumi complessivi concentrando però gli studenti su un numero inferiore di rotte consolidate, mentre molti collegamenti periferici/occasionali non sono stati riattivati.

## 2. Effetto ritardato e asimmetrico della Brexit (Ipotesi H3)
* **Peso storico del Regno Unito:** Nel periodo pre-pandemico (2016–2019), le 41 regioni del Regno Unito costituivano uno dei principali poli attrattori europei, pesando per l'**11–12%** dell'intera mobilità Erasmus+ (circa 17.500 arrivi contro ~9.200 partenze l'anno).
* **L'effetto "coda" dei progetti pluriennali (2021–2022):** Sebbene il Regno Unito sia uscito formalmente dal programma Erasmus+ nel settembre 2021 (sostituito dal *Turing scheme*), i flussi non si azzerano immediatamente nel 2021 (quota 7,7%) e nel 2022 (quota 7,1%: 9.648 arrivi e 5.349 partenze) a causa della durata pluriennale dei finanziamenti Erasmus+ già assegnati.
* **Il crollo strutturale nel 2023:** Nel **2023** la quota complessiva del UK precipita al **2,9%** del totale europeo, con un crollo verticale soprattutto delle partenze (**705 studenti** contro 9.246 nel 2018, **-92,4%**) rispetto agli arrivi (**5.598 studenti**, **-67,8%**).
* *Nota metodologica per il report:* È importante sottolineare che la media biennale `post_covid` (2022–2023) attenua parzialmente l'impatto della Brexit perché ingloba il 2022; l'analisi delle reti annuali permette di isolare con precisione questo sfasamento temporale.

## 3. Coesione della componente gigante
* In tutte e sei le reti binarie (sia a soglia principale $\ge 5$ sia a soglia di controllo $\ge 3$), **tutti i nodi attivi appartengono all'unica componente debolmente connessa gigante** (es. nel `pre_covid` a soglia 5: 307 regioni attive su 319 e 307 nella giant WCC).
* *Significato strutturale:* Le regioni che superano la soglia minima di mobilità non formano mai sottoreti isolate, ma risultano integrate in un'unica infrastruttura europea connessa; la contrazione pandemica si manifesta nell'aumento dei nodi isolati sotto soglia (da 12 nel `pre_covid` a 24 nel `covid`, poi 18 nel `post_covid`).

## 4. Struttura visiva preliminare (Core–Periphery)
* L'ispezione grafica della rete binaria pre-Covid mostra una netta configurazione **centro-periferia**: un nucleo centrale molto denso dominato dalle principali regioni universitarie spagnole (`ES30` Madrid, `ES51` Catalogna, `ES61` Andalusia, `ES52` Valencia), italiane (`ITC4` Lombardia, `ITH3` Veneto), francesi (`FRK2`, `FRL0`) e capitali centro-europee (`DE30` Berlino, `HU11` Budapest), circondato da una periferia sparsa legata al nucleo e priva di collegamenti diretti intra-nazionali.