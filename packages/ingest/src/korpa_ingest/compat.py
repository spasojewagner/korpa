"""Approved source mappings; additions require a new profile identifier."""

PROFILE = "compat-2026-11"
STRICT_PROFILE = "strict-v1"
LIST_TYPES = {
    "MESECNI_PRESEK": "MESEČNI_PRESEK",
    "VAZECI_CENOVNIK": "VAŽEĆI_CENOVNIK",
}
UNITS = frozenset({"kg", "g", "l", "ml", "kom", "pak"})
# Identity entries are explicit too: every input column must map exactly once.
HEADER_ALIASES = {
    "KATEGORIJA": "KATEGORIJA",
    "NAZIV KATEGORIJE": "NAZIV KATEGORIJE",
    "Naziv proizvoda": "Naziv proizvoda",
    "Robna marka": "Robna marka",
    "Barkod proizvoda": "Barkod proizvoda",
    "Jedinica mere": "Jedinica mere",
    "Naziv trgovca - formata": "Naziv trgovca - formata",
    "Naziv trgovca – formata": "Naziv trgovca - formata",
    "Datum cenovnika": "Datum cenovnika",
    "Redovna cena": "Redovna cena",
    "Cena po jedinici mere": "Cena po jedinici mere",
    "Snižena cena": "Snižena cena",
    "Datum početka sniženja": "Datum početka sniženja",
    "Datum kraja sniženja": "Datum kraja sniženja",
    "Stopa PDV": "Stopa PDV",
    "VRSTA_CENOVNIKA": "VRSTA_CENOVNIKA",
}
