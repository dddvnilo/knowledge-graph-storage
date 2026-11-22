# Priprema ekspertskih i AI Q-matrica

Ovo je Stefanova početna osnova za pripremu ulaza: **CSV Q-matrica + JSON sa
pratećim podacima → proveren JSON paket v0.1 za Danilov prijem**.

Čitač podržava jedan opisan tabelarni oblik. Rezultat je paket za predaju;
konverzija u RDF i upis u Virtuoso još nisu implementirani ovim dodatkom.
Korisnik dostavlja već postojeću Q-matricu i podatke o njenom nastanku.

## Pokretanje

Komande se izvršavaju iz korena repozitorijuma. Potreban je Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r ingest/requirements.txt
.\.venv\Scripts\python.exe -m ingest.qmatrix_csv --input examples/ingest/qmatrix/expert.csv --metadata examples/ingest/qmatrix/expert.metadata.json --output examples/ingest/qmatrix/generated/expert-package.json
.\.venv\Scripts\python.exe -m ingest.qmatrix_csv --input examples/ingest/qmatrix/llm.csv --metadata examples/ingest/qmatrix/llm.metadata.json --output examples/ingest/qmatrix/generated/llm-package.json
.\.venv\Scripts\python.exe ingest/contracts/qmatrix_v0_1/proveri.py examples/ingest/qmatrix/generated/expert-package.json examples/ingest/qmatrix/generated/llm-package.json
```

Na Linuxu/macOS-u koristi se `.venv/bin/python` umesto Windows putanje.
Aktiviranje virtuelnog okruženja nije potrebno za navedene komande.

Priložena su oba izvorna primera, metapodaci i generisani paketi. **Svi
podaci su izmišljeni**: AI model nije pozivan, a kompetencije nije određivao
stvarni ekspert. Oznake demonstracionog testa odvojene su od testa T1 iz
postojećeg RDF primera. Ponovno pokretanje menja `package.created_at`;
izvorna matrica i podaci o njenom nastanku ostaju isti.

## Podržani CSV

```csv
zadatak,K1,K2
Zadatak 1,x,-
Zadatak 2,x,x
Zadatak 3,x,?
```

- Kodiranje je UTF-8, sa opcionim BOM-om. Separator se navodi u `csv.delimiter`:
  zarez (podrazumevano), tačka-zarez ili tabulator.
- Prva kolona sadrži izvorne oznake zadataka; njen naziv je `csv.item_column`.
  Ostale kolone su kompetencije. Dodatne kolone nisu podržane.
- Svaka oznaka reda mora imati tačno jedno poklapanje sa
  `items[].source_label`, a svaka kompetencijska kolona sa
  `competencies[].source_label`. Čitač ne izmišlja niti pogađa identifikatore.
- Sve deklarisane stavke i kompetencije moraju biti prisutne tačno jednom.
  Redosled redova i kolona iz CSV-a prenosi se u izlazni paket; lista u
  metapodacima služi za povezivanje, a ne za tiho preuređivanje matrice.
- Značenje svakog dozvoljenog zapisa navodi se u `csv.values`, na primer
  `{"x": 1, "-": 0, "?": null}` ili `{"1": 1, "0": 0, "?": null}`.
  Nepoznata vrednost ostaje `null`. Prazna ćelija je dozvoljena samo ako
  mapa izričito sadrži `"": null` ili drugo dogovoreno značenje.
- Nema automatskog uklanjanja razmaka, pogađanja značenja praznih ćelija ili
  preskakanja neispravnih redova. Nepoznat zapis, duplikat, pogrešan broj
  polja ili izostavljen zadatak dovode do greške sa opisom mesta problema.

XLSX, slobodan tekst odgovora AI modela, više tabela u jednom fajlu i druge
vrste struktura zahtevaju poseban čitač ili naknadni dogovor.

## Šta sadrži prateći JSON

Potpuni primeri su u [`examples/ingest/qmatrix/`](../examples/ingest/qmatrix/).

| Polje | Šta korisnik dostavlja |
|---|---|
| `csv` | Naziv prve kolone, separator i izričito značenje vrednosti. |
| `structure` | Identitet matrice, testa i šeme kompetencija; verziju ili pokretanje. |
| `items` | Lokalne identifikatore, izvorne oznake i raspoložive tekstove zadataka. |
| `competencies` | Lokalne identifikatore, izvorne oznake, nazive i opise kompetencija. |
| `provenance` | Poreklo same matrice: ekspert/model, metod/prompt, parametri, ulazi i vreme. |
| `cell_annotations` | Opcione pouzdanosti i obrazloženja po ćeliji, ako ih izvor ima. |

Ostala polja se odbijaju umesto da budu izgubljena. Nepoznati podaci o
ekspertu ili vremenu nastanka označavaju se prema zajedničkom predlogu, npr.
`name: null` i `generated_at: null`. Za LLM se zahteva softverski agent sa
nepraznim `version` i neprazan `provenance.plan.text`; model i prompt se
ne zaključuju iz imena fajla.

Program sam pravi `schema_version` i blok `package`: stvarno UTC vreme
pripreme, naziv/verziju čitača, naziv i SHA-256 izvornog CSV-a i spisak
primenjenih preslikavanja. Hash označava tačne bajtove CSV fajla, uključujući
njegove završetke redova. `package` opisuje pripremu, a `provenance` ostaje
opis prvobitnog nastanka matrice. Metapodaci nisu menjani u izvornom fajlu.

## Provera i izlaz

Zajednički [predlog šeme i validatora](contracts/qmatrix_v0_1/README.md)
preuzet je od Danila bez izmena. Pre pisanja izlaza pozivaju se njegove
provere šeme, dimenzija, identifikatora, referenci anotacija i datuma.
Čitač ima i prethodne provere svog CSV oblika i pratećih podataka.

Uspeh vraća izlazni kod `0`. Greška vraća `1` i razlog na standardnom izlazu
za greške (`stderr`); pogrešni CLI argumenti vraćaju `2`. Neuspešna priprema
ne pravi novi izlaz niti menja raniji paket. Uspešna priprema u celosti
zamenjuje postojeći izlaz. Izlaz ne sme biti isti fajl kao CSV ili metapodaci.

Provera paketa znači **provereno**, ne **sačuvano u Virtuosu**. Provere koje
zahtevaju bazu, kao postojanje prethodne verzije i prepoznavanje ponovljenog
unosa, ostaju na prijemu.

## Provere programa

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s ingest/tests -v
```

Testovi proveravaju značenje matrice, očuvanje nepoznatih vrednosti,
redosleda, identiteta i porekla, odbijanje neispravnih izvora i zaštitu
postojećih fajlova pri grešci. R i Virtuoso nisu potrebni za ovaj deo.

## Predaja Danilu i otvorene odluke

Predaje se jedan generisani JSON po verziji/pokretanju Q-matrice. Prijem
zatim treba da proveri paket, prevede ga u aktuelni RDF model i učita u
Virtuoso. Priprema i prijem treba da koriste usklađenu verziju ugovora.

Za nastavak treba potvrditi:

1. Koji stvarni ekspertski i AI fajlovi su dostupni i za koji domen?
2. Koriste li ekspert i AI isti test i istu listu kompetencija? Demonstracija
   to pretpostavlja; različite liste zahtevaju zasebno provereno mapiranje.
3. Da li oba dela prihvataju paket v0.1 i da li je potreban dodatni sadržaj
   nakon pregleda stvarnih fajlova? CSV čitač ne proširuje ugovor prećutno.

Learning Commons je sledeća faza: nakon izbora domena pregledati mali
podgraf, sačuvati izvorne oznake i vrste veza, pa zajedno definisati novi
tip paketa. Postojeći Q-matrix paket ne koristi se za tu drugu vrstu ulaza.
