# Primer upotrebe — nacrt za ručnu objavu

## Naslov

Korpa — poređenje cena namirnica iz otvorenih cenovnika

## Kratak opis

Korpa pretvara objavljene cenovnike trgovaca u pretragu proizvoda, poređenje korpe i pregled kvaliteta
podataka, uz jasno prikazane datume izvora.

## Duži opis

Na jednom mestu možete pretražiti proizvod, uporediti cene po trgovinskom formatu i sastaviti korpu.
Kompletne i nepotpune korpe su odvojeno označene, a pregled najjeftinijeg izbora po artiklu pokazuje
kada bi kupovina obuhvatila više formata. Dostupnost robe, put i dostava nisu uključeni u poređenje.

Podaci se preuzimaju sa Portala otvorenih podataka i proveravaju prema dokumentovanom profilu.
Izveštaj prikazuje prihvaćene redove, odstupanja i greške; neuspešan uvoz sam po sebi nije nalaz o
zakonitosti rada trgovca. Mesečni indeks prati redovne cene proizvoda koji postoje i u baznom i u
posmatranom periodu. To nije zvanični indeks potrošačkih cena.

Opcioni pomoćnik iz rečenice predlaže pretrage i količine. Korisnik bira stvarne artikle i potvrđuje
dodavanje; cene se računaju iz baze, a ne iz odgovora modela. Javna dokumentacija opisuje ograničenja,
izvore i metod. REST, read-only GraphQL i MCP omogućavaju dalju upotrebu podataka.

Nezavisan projekat zasnovan na otvorenim podacima. Nije povezan sa Ministarstvom.

## Korišćeni skupovi podataka

Objedinjeni cenovnici trgovaca objavljeni na [Portalu otvorenih podataka](https://data.gov.rs/).
Za izbor skupova u obrascu koristiti [snimak metapodataka](evidence/2026-11-24/datasets.json),
preuzet 24.11.2026, sa stvarnim `dataset_id`, izdavačem, resursom i deklarisanom licencom.
Link pojedinačnog skupa je `https://data.gov.rs/api/1/datasets/<dataset_id>/`;
to je API metapodataka, ne nagađana adresa CSV-a. U obrascu označiti stvarno korišćene skupove,
a ne tvrditi da neuspešno preuzeti skup ima upotrebljive aktuelne cene.

Primeri stvarno otkrivenih izvora navedeni su u [evidenciji izvora](evidence/README.md).
TODO pre objave: proveriti aktuelni izbor skupova i tekst licenci/atribucije po skupu; deklaracija
`sodl` nije zamena za pregled uslova. Ovaj nacrt ne potvrđuje da je primer upotrebe već podnet.

## Linkovi i prilozi

- Aplikacija: [ai-korpa.vercel.app](https://ai-korpa.vercel.app).
- Izvorni kod: [spasojewagner/korpa](https://github.com/spasojewagner/korpa).
- [Početna](../images/v1/home.png): ulaz u pretragu i odvojeni pregled podataka.
- [Korpa](../images/v1/basket.png): datirani iznosi, potpune/nepotpune korpe i izbor po artiklu.
- [Indeks](../images/v1/index.png): vremenska serija i metoda.
- [Kvalitet](../images/v1/quality.png): statusi izdavača i provera podataka.

Snimci su sa produkcije od 24.11.2026; [provenijencija](../images/v1/provenance.json) sadrži adrese i vreme.
Prikazane cene su zabeležena opažanja, bez obećanja iste cene ili dostupnosti u konkretnoj radnji.
