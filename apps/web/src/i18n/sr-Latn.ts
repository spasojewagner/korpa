export const copy = {
  sourceDate: 'Cenovnik od {date}',
  perUnit: '{price}/{unit}',
  errorMessage: 'Podaci trenutno nisu dostupni. Pokušajte ponovo.',

  brand: 'Korpa',
  skip: 'Pređi na sadržaj',
  metaDescription: 'Uporedite cene namirnica iz javno objavljenih cenovnika trgovaca u Srbiji.',
  source: 'Portal otvorenih podataka',
  disclaimer: 'Nezavisan projekat zasnovan na otvorenim podacima. Nije povezan sa Ministarstvom.',
  scriptLabel: 'Pismo',
  latin: 'Latinica',
  cyrillic: 'Ћирилица',

  navLabel: 'Glavni meni',
  navBasket: 'Korpa',
  navIndex: 'Indeks cena',
  navQuality: 'Kvalitet podataka',
  navAbout: 'O projektu',
  navSearch: 'Pretraga',
  navData: 'Podaci',
  navShop: 'Kupovina',
  homeLabel: 'Korpa, početna',
  dataIndex: 'Indeks i signali',
  dataApi: 'API i MCP',
  latinShort: 'Lat',
  cyrillicShort: 'Ћир',
  footerTagline: 'Cene namirnica iz zvaničnih cenovnika trgovaca, svako jutro.',
  footerShop: 'Kupovina',
  footerData: 'Podaci',
  footerProject: 'Projekat',
  basketLive: 'U korpi: {items}',


  searchLabel: 'Pretraga proizvoda',
  searchPlaceholder: 'npr. mleko, hleb, 8600…',
  searchButton: 'Traži',
  footerSources: 'Izvor podataka',
  footerLicense: 'Licenca podataka: Srpska licenca za otvorene podatke.',
  footerCode: 'Izvorni kod',

  notFoundHeading: 'Stranica nije pronađena',
  notFoundText: 'Adresa ne postoji ili je promenjena.',
  goHome: 'Na početnu',
} as const

/** Serbian plural forms (Intl.PluralRules 'sr': one = 1, 21, 31…; few = 2–4, 22–24…; other). */
export const plurals = {
  formats: { one: 'u {n} formatu', few: 'u {n} formata', other: 'u {n} formata' },
  missing: {
    one: 'Nedostaje {n} proizvod',
    few: 'Nedostaju {n} proizvoda',
    other: 'Nedostaje {n} proizvoda',
  },
  basketItems: { one: '{n} proizvod', few: '{n} proizvoda', other: '{n} proizvoda' },
  basketStores: { one: 'Kupovina u {n} formatu prodavnice', few: 'Kupovina u {n} formata prodavnica', other: 'Kupovina u {n} formata prodavnica' },
  results: {
    one: 'Pronađen je {n} proizvod',
    few: 'Pronađena su {n} proizvoda',
    other: 'Pronađeno je {n} proizvoda',
  },
  daysAgo: { one: 'pre {n} dan', few: 'pre {n} dana', other: 'pre {n} dana' },
} as const

export { codeLabels } from './quality-labels'

export type CopyKey = keyof typeof copy
export type PluralKey = keyof typeof plurals


