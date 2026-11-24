# Nacrti poruka trgovcima — provera 24.11.2026.

Za ručno slanje posle pregleda; adrese i potpisi nisu pretpostavljeni. TODO: održavalac dodaje provereni kontakt
i potpis i osvežava nalaz neposredno pre slanja. Poruke nisu poslate.

Izvor statusa: [sačuvani quality.json](evidence/2026-11-24/quality.json), `as_of: 2026-11-24`.
Ima sedam neuspešnih izdavača: Aksa, BRICO, Konovo, Leon, Qvattro, RIČ i Statovac. Pet ranije navedenih
izdavača je i dalje u tom skupu, ali nije ceo spisak. Aksa i Leon imaju grešku preuzimanja u objavljenom izveštaju;
to nije dokaz greške CSV strukture. Naknadno lokalno preuzimanje oba fajla uspelo je bez upisa u bazu.

Za svaku poruku ispod [evidencija preuzimanja](evidence/2026-11-24/retailer-observations.json) daje URL,
vreme, SHA-256, zaglavlje, primer i rezultate neizmenjenog parsera. Brojevi iz naknadne lokalne provere
nisu novi produkcioni rezultati. `errors` je prvi neuspešan uslov po redu; `errors_by_rule` može brojati isti red
pod više pravila. Na primer, broj fizičkih redova uz odbijeno zaglavlje ne znači da je svaki semantički pregledan.

Pravni izvor za poređenje: [zvanični prečišćeni pravilnik i prilog](https://pravno-informacioni-sistem.rs/eli/rep/sgrs/ministarstva/pravilnik/2026/76/3/reg),
pročitan 24.11.2026, brojevi 76/2026 i 98/2026. [Sačuvani tekst](evidence/2026-11-24/official-standard.txt).
Ovo su tehnička opažanja, ne pravni nalazi. Kod Statovca postoji ograničenje našeg parsera: zvanični ćirilični
prilog i sam koristi dugu crtu i ćirilične vrednosti. Zahtev za kompatibilnim izvozom ne sme biti predstavljen kao
obaveza da trgovac pređe na latinicu. Pravila standarda i stroži lokalni profil nisu isto.


## BRICO S DOO

Predmet: Provera javnog cenovnika — Korpa

Poštovani,

Razvijam Korpu, nezavisan projekat za poređenje javno objavljenih cena. U objavljenom izveštaju od
24.11.2026. vaš fajl je odbijen na zaglavlju (32.652 fizička podatkovna reda). Naknadna provera istog dana
ponovo nalazi 14 kolona: nema `VRSTA_CENOVNIKA`, a naziv formata ima završnu zvezdicu.
Primer prvog podatkovnog reda je ispod; za datum koristi tačke, a cena po jedinici mere je prazna.

Molim vas da proverite izvoz prema prilogu pravilnika: §4 navodi strukturu i kolonu vrste cenovnika;
§5 opisuje kategorije, datum i cenu po jedinici mere, a §7 propisuje format datuma i cena.
Naš parser ne može da pretpostavi tip cenovnika ili da popuni nedostajuću cenu.
Da li možete da potvrdite predviđeni format ili objavite ispravljen izvoz?

Hvala na objavljivanju podataka i pomoći da poređenje bude pouzdano.
Srdačan pozdrav,

Izvor: [CSV](https://data.gov.rs/s/resources/brico-s-doo-cenovnik/20261124-032949/cene-proizvoda-bricos-20261124.csv) · [metapodaci skupa](https://data.gov.rs/api/1/datasets/6a329a1969e6025495f2d2b6/).
Lokalno opažanje: `2026-11-24T15:30:15.564828+00:00`; SHA-256 `5339542f70930a9c7e58af7411fc3081381e3c21a1efbb09770965d66a62003e`.
Primer fizičkog reda 2 (JSON niz polja u izvornom redosledu; escape zapis čuva nevidljive znake):

```json
["10000", "GVOŽĐURIJA", "ZAVRŠETAK SRCE METALNO 10MM, 2KOM", "RM NIJE DEFINISANA", "3233690186748", "kom", "BRICO S DOO NOVI SAD", "24.11.2026", "179", "", "", "", "", "20"]
```


## Konovo doo

Predmet: Provera javnog cenovnika — Korpa

Poštovani,

Pri proveri podataka za Korpu, nezavisan projekat za poređenje cena, vaš objavljeni fajl nije prošao
proveru zaglavlja. Produkcioni izveštaj od 24.11.2026. navodi 9.883 reda, a naknadno preuzimanje istog
dana 9.885. Kolona `Šifra proizvoda` stoji umesto `VRSTA_CENOVNIKA`; prve dve kolone imaju drugačija
velika/mala slova od našeg ugovora. U prvom redu poslednja vrednost je šifra `G-43816`, ne tip cenovnika.

Prilog pravilnika u §4 navodi kolonu vrste cenovnika, a §5 njene vrednosti i šifarnik kategorija.
Molim vas da proverite da li je moguće objaviti zaseban izvoz sa vrstom cenovnika i odgovarajućim
kategorijama. Ne bismo preslikavali šifru artikla u tip cenovnika niti zaključivali kategoriju iz naziva.
Možete li da pojasnite predviđenu strukturu ovog izvora?

Hvala na pomoći i objavljenim podacima.
Srdačan pozdrav,

Izvor: [CSV](https://konovo.rs/wp-content/uploads/cenovnik/cene_proizvoda_konovo.csv) · [metapodaci skupa](https://data.gov.rs/api/1/datasets/6a693202d31a9dd3073aaf73/).
Lokalno opažanje: `2026-11-24T15:30:28.942034+00:00`; SHA-256 `52f268ef1a66f4c0bf439161838f6a200856c7387c709973c9b34f35c52ac7ea`.
Primer fizičkog reda 2 (JSON niz polja u izvornom redosledu; escape zapis čuva nevidljive znake):

```json
["17", "Tableti i Oprema za Tablete", "Tablet MeanIT X30 10.1, 1280x800, Quad Core, 5.000mAh, 2GB/16GB", "", "3858890342680", "kom", "Konovo", "24-11-2026", "12750.00", "12750.00", "", "", "", "20", "G-43816"]
```


## Qvattro Company

Predmet: Provera javnog cenovnika — Korpa

Poštovani,

U nezavisnom projektu Korpa proveravamo javne cenovnike. Izveštaj od 24.11.2026. za vaš izvor prikazuje
29.791 red i nijedan prihvaćen red. Naknadno preuzimanje potvrđuje isti ukupan broj: prvi neuspešni uslovi
su NUL znak (24.455), datum (4.265), barkod (45) i sniženje (1.026).
Primer reda 2 ispod sadrži NUL u poljima datuma sniženja; ovde je nevidljiv znak prikazan kao `\u0000`.

Molim vas da proverite izvoz: prilog pravilnika §7 traži da odsutna polja ostanu prazna i datumi budu
`DD-MM-YYYY`; §5 navodi da se odsutno sniženje ostavlja prazno, a §8 opisuje UTF-8 CSV.
NUL nije isto što i prazno polje. Ne pokušavamo da nagađamo nepoznate datume ili da prepravljamo cene.
Da li možete da proverite serijalizaciju praznih vrednosti i ponovite izvoz?

Hvala na saradnji i dostupnim podacima.
Srdačan pozdrav,

Izvor: [CSV](https://prodavnicasunce.rs/cenovnik/cene_proizvoda_QVATTRO_COMPANY.csv) · [metapodaci skupa](https://data.gov.rs/api/1/datasets/68f8cbfd1d835c729727825d/).
Lokalno opažanje: `2026-11-24T15:30:30.902810+00:00`; SHA-256 `0e219f6952cf0ba4d8b0b12c2563e4cc0aa40a29ee560cbc1a1f47f83026ca6e`.
Primer fizičkog reda 2 (JSON niz polja u izvornom redosledu; escape zapis čuva nevidljive znake):

```json
["1", "Mleko, mlečni i mešoviti proizvodi, jaja", "Gauda 45%mm 1kg Imlek", "IMLEK AD", "0000002800004", "KG", "QVATTRO COMPANY", "01-09-2026", "1399.99", "1399.99", "0.00", "\u0000", "\u0000", "20", "MESECNI_PRESEK"]
```


## RIČ doo Prokuplje

Predmet: Provera javnog cenovnika — Korpa

Poštovani,

Pri proveri javnog cenovnika za nezavisni projekat Korpa, izveštaj od 24.11.2026. prikazuje 31.897 redova
bez prihvaćenih zapisa. Naknadna provera nalazi da svih 31.897 redova pada na pravilu za PDV, dok
31.863 ima problem sa cenom; deo redova ima i neprihvaćene jedinice. Brojevi po pravilima se preklapaju.
U prvom redu je stopa `20.00`, a cena po jedinici mere je prazna.

Prema prilogu pravilnika §5, PDV se iskazuje kao ceo broj bez znaka procenta, a cena po jedinici mere
kao decimalni broj sa tačkom i dve decimale; §7 opisuje opšta pravila za cene.
Molim vas da proverite izvoz PDV-a, obaveznih cena i jedinica. Korpa ne može da dopuni nedostajuću
cenu ili da pretpostavi značenje nepoznate jedinice. Možete li da potvrdite ili korigujete ova polja?

Hvala na objavljenim podacima i vremenu.
Srdačan pozdrav,

Izvor: [CSV](https://www.podaci.ric.rs/cenovnici/cene_proizvoda_ric.csv) · [metapodaci skupa](https://data.gov.rs/api/1/datasets/6a95ed3adf0d645f96b6f3de/).
Lokalno opažanje: `2026-11-24T15:30:37.959733+00:00`; SHA-256 `1f8be43421fbe7cf9c6da9d93e3a66020b63f2edd43b1b036e42e416f62fc428`.
Primer fizičkog reda 2 (JSON niz polja u izvornom redosledu; escape zapis čuva nevidljive znake):

```json
["21", "Lična higijena i kozmetika", "Vlaz.maramice Kosili plave flip-top 70/1", "", "8606012144231", "kom", "RIČ", "01-09-2026", "224.99", "", "", "", "", "20.00", "MESECNI_PRESEK"]
```


## Statovac — kompatibilnost parsera

Predmet: Provera javnog cenovnika — Korpa

Poštovani,

U nezavisnom projektu Korpa trenutno ne uspevamo da obradimo vaš ćirilični cenovnik: izveštaj od
24.11.2026. odbija zaglavlje i navodi 32.636 fizičkih podatkovnih redova. Naknadna provera potvrđuje
zaglavlje `Назив трговца – формата`; naš tačan profil očekuje običnu crticu nakon transliteracije i zato
ne prihvata dugu crtu. Primer ispod ima i ćiriličnu jedinicu i tip cenovnika koje profil još ne podržava.

Zvanični ćirilični prilog pravilnika u §4–5 i sam koristi ove oblike, pa ovo opisujemo kao ograničenje
kompatibilnosti naše aplikacije, ne kao utvrđenu grešku vašeg standarda. Pregledamo mogućnosti podrške.
Da li eventualno već postoji i latinični izvoz istog sadržaja koji možemo testirati? Ne tražimo promenu
značenja podataka niti tvrdimo da je latinica obavezna.

Hvala na podacima i razumevanju.
Srdačan pozdrav,

Izvor: [CSV](https://data.gov.rs/s/resources/cenovnici-statovac/20261122-033030/cene-proizvoda-kengur.csv) · [metapodaci skupa](https://data.gov.rs/api/1/datasets/6a0aecd5c320c889bd9a2a96/).
Lokalno opažanje: `2026-11-24T15:30:40.954682+00:00`; SHA-256 `c17a3fb4e3a42e8ac596acc931774b99c5774377394c637baaacc95e61d2ebf3`.
Primer fizičkog reda 2 (JSON niz polja u izvornom redosledu; escape zapis čuva nevidljive znake):

```json
["2", "Безалкохолна пића, кафа, чај", "Brainrot Soda, gazirano bezalkoholno piće bez šećera, Six Seven, blue, 250ml", "", "8600828436238", "л", "Кенгур – малопродаја (сви малопродајни објекти)", "01-09-2026", "360.00", "1440.00", "", "", "", "20", "МЕСЕЧНИ_ПРЕСЕК"]
```


## Aksa d.o.o — dostupnost i naknadni nalaz

Predmet: Provera javnog cenovnika — Korpa

Poštovani,

U nezavisnom projektu Korpa produkcioni izveštaj od 24.11.2026. za vaš izvor beleži grešku preuzimanja
bez HTTP odgovora (`http_status: 0`), pa ne zaključujemo da je uzrok neispravan format.
Naknadno lokalno preuzimanje istog dana uspelo je (HTTP 200): od 36.674 reda parser prihvata 36.666.
U osam redova nalazi se problem sa cenom; prvi primer je fizički red 1718, naveden ispod.

Prilog pravilnika §5 i §7 opisuje cene kao decimalne brojeve sa tačkom i dve decimale.
Molim vas da proverite navedeni zapis. Za raniju nedostupnost nemamo dovoljno dokaza da utvrdimo
uzrok; možete li da potvrdite stabilan javni URL za automatizovano preuzimanje?

Hvala na objavljivanju podataka i pomoći.
Srdačan pozdrav,

Izvor: [CSV](https://aksa.keprom.rs/cene_proizvoda_aksa.csv) · [metapodaci skupa](https://data.gov.rs/api/1/datasets/6ad4c219024e6f2e2b3576dd/).
Lokalno opažanje: `2026-11-24T15:30:11.610667+00:00`; SHA-256 `ab2b226fb0bec096032575d7d27120193fed1d5d31bc06a6e408941de134bef2`.
Primer fizičkog reda 1718 (JSON niz polja u izvornom redosledu; escape zapis čuva nevidljive znake):

```json
["21", "Lična higijena i kozmetika", "A-derma Exomega Control krema 400ml", "A-DERMA", "3282770149685", "l", "Aksa - maloprodaja", "01-09-2026", "2849.00", "", "", "", "", "20", "MESECNI_PRESEK"]
```


## Leon Conditors DOO — dostupnost i naknadni nalaz

Predmet: Provera javnog cenovnika — Korpa

Poštovani,

Produkcioni izveštaj Korpe, nezavisnog projekta za poređenje cena, od 24.11.2026. beleži grešku preuzimanja
vašeg fajla bez HTTP odgovora. Naknadno lokalno preuzimanje uspelo je (HTTP 200), pa raniju grešku
ne pripisujemo strukturi CSV-a niti pretpostavljamo uzrok mrežnog problema.
Lokalna provera prihvata 805 od 9.671 reda. U prvom redu `Snižena cena` je `0`, a oba datuma su prazna;
nezavisna provera pravila nalazi 8.866 problema sa sniženjem i četiri sa jedinicom (brojevi se preklapaju).

Prilog pravilnika §5 kaže da polje snižene cene ostaje prazno kada nema sniženja; §7 opisuje prazna polja,
a §5 daje primere jedinica. Molim vas da proverite način izvoza odsutnog sniženja i jedinicu `1kg/l`.
Ne tumačimo automatski nulu kao odsustvo sniženja. Možete li da potvrdite i adresu za stabilno preuzimanje?

Hvala na podacima i saradnji.
Srdačan pozdrav,

Izvor: [CSV](https://www.leon.co.rs/cenovnik/cene-proizvoda-leon.csv) · [metapodaci skupa](https://data.gov.rs/api/1/datasets/68f1db0682d3fdfbdceeabcb/).
Lokalno opažanje: `2026-11-24T15:30:29.693205+00:00`; SHA-256 `f9926787e41b18043bcfcc55cb86c1a11bf6250d7baf1ed11b067ef16dbfcc4a`.
Primer fizičkog reda 2 (JSON niz polja u izvornom redosledu; escape zapis čuva nevidljive znake):

```json
["2", "BEZALKOHOLNA PIĆA, KAFA, ČAJ", "L.CAJ FUZE TEA BRESKVA PET 500ML", "RM NIJE DEFINISANA", "5449000235770", "kom", "LEON CONDITORS", "01-09-2026", "87.99", "87.99", "0", "", "", "20", "MESECNI_PRESEK"]
```
