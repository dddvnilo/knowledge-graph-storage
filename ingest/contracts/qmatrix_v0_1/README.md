# Izvor zajedničkog predloga v0.1

`paket-qm.schema.json` i `proveri.py` preuzeti su **bez izmena** iz foldera
`paket-v0.1`, koji je Danilo poslao Stefanu 16. 11. 2026. Autor ovog predloga
ugovora i validatora je Danilo; nisu novi rezultat razvoja CSV čitača.

Predlog obuhvata jednu verziju ili jedno pokretanje ekspertske/LLM Q-matrice
po JSON paketu. Njegov status ostaje **radni predlog za zajedničku potvrdu**.
Ova kopija omogućava da priprema radi iz samog repozitorijuma, bez fajlova
iz Stefanovog radnog foldera.

CSV čitač poziva iste `schema_errors` i `semantic_errors` provere. Za svoje
ulaze dodatno zahteva jednoznačne izvorne oznake, a za LLM i neprazan tačan
identifikator modela i tekst prompta. Time se ne menja zajednička šema.
Promena njenog ugovora zahteva usklađivanje proizvođača i primaoca paketa.

Ovaj format je granica predaje podataka. Aktuelni RDF model je dokumentovan
u [`ontology/README.md`](../../../ontology/README.md); pretvaranje paketa
u taj model i prijem u Virtuoso ostaju naredni korak.
