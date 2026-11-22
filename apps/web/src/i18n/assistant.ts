/** Copy for the basket assistant; only the /korpa chunk imports it. */
export const assistantCopy = {
  assistantLabel: 'Napiši šta kupuješ',
  assistantPlaceholder: 'npr. 2 mleka, hleb i desetak jaja',
  assistantSubmit: 'Predloži proizvode',
  assistantNote: 'Predlog pravi jezički model; cene su iz zvaničnih cenovnika. Proveri izbor pre dodavanja.',
  assistantCounter: '{count}/300 znakova',
  assistantResults: 'Predloženi proizvodi',
  assistantReady: 'Predlog je spreman. Proveri izbor pre dodavanja.',
  assistantSkip: 'Preskoči',
  assistantAdd: 'Dodaj izabrano u korpu',
  assistantMissing: 'Nismo našli proizvod',
  assistantInvalid: 'Upiši između 3 i 300 znakova.',
  assistantUnavailable: 'Pomoćnik trenutno nije dostupan',
  assistantWait: 'Previše zahteva. Pokušaj ponovo za {minutes} min.',
  assistantRateLimit: 'Previše zahteva. Pokušaj ponovo kasnije.',
  assistantFull: 'U korpi može biti najviše {max} proizvoda. Preskoči neki predlog ili ukloni proizvod iz korpe.',
  assistantAdded: 'Izabrani proizvodi su dodati u korpu.',
} as const
