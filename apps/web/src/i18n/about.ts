/** Copy for the About page; only its chunk imports it. */
export const aboutCopy = {
  staticDescription: 'Saznajte kako Korpa koristi otvorene cenovnike, odakle dolaze podaci, koja je licenca i kako prijaviti problem.',
  aboutHeading: 'O projektu',
  aboutWhat: 'Korpa je nezavisan, nekomercijalan projekat. Cenovnike namirnica koje trgovci po zakonu objavljuju kao otvorene podatke pretvara u alat za poređenje cena.',
  aboutNotHeading: 'Šta Korpa nije',
  aboutNot: 'Korpa nije državni servis i nije povezana sa Ministarstvom ni sa trgovcima. Ne prodaje proizvode i ne prikazuje reklame.',
  aboutSourceHeading: 'Izvor i licenca',
  aboutSource: 'Podaci potiču sa Portala otvorenih podataka i objavljeni su pod Srpskom licencom za otvorene podatke. Prikazujemo ih bez izmena, a uz svaku cenu piše datum cenovnika.',
  aboutMethodHeading: 'Metod',
  aboutSignalsHeading: 'Signali za proveru',
  aboutSignals: 'Sniženje posle skoka redovne cene je signal, a ne tvrdnja o prekršaju: sniženje je aktivno na dan provere, redovna cena istog proizvoda u istom formatu porasla je najmanje 20 % i najviše tri puta u 60 dana pre početka sniženja, a snižena cena je najmanje 98 % redovne cene pre tog rasta. Rast računamo između uzastopnih zabeleženih cena. Različite nazive istog barkoda kod trgovaca prikazujemo informativno, bez prepravljanja naziva.',
  aboutMethod: 'Cenovnici se preuzimaju, proveravaju po zvaničnom tehničkom standardu i upisuju u bazu. Redovi koji ne prođu proveru se broje i prikazuju na stranici o kvalitetu podataka.',
  aboutContactHeading: 'Kontakt',
  aboutContact: 'Greške i predloge prijavite na GitHubu.',
  reportIssue: 'Prijavi problem',
} as const
