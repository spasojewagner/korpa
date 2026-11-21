"""Approved source mappings; additions require a new profile identifier."""

PROFILE = "compat-2026-11.3"
PREVIOUS_PROFILE = "compat-2026-11.2"
LEGACY_PROFILE = "compat-2026-11"
PROFILES = frozenset({LEGACY_PROFILE, PREVIOUS_PROFILE, PROFILE})
EXTENDED_VALUE_PROFILES = frozenset({PREVIOUS_PROFILE, PROFILE})
STRICT_PROFILE = "strict-v1"
LIST_TYPES = {
    "MESECNI_PRESEK": "MESEČNI_PRESEK",
    "VAZECI_CENOVNIK": "VAŽEĆI_CENOVNIK",
}
UNITS = frozenset({"kg", "g", "l", "ml", "kom", "pak"})
UNIT_ALIASES = {"kom.": "kom", "gr": "g", "lit": "l"}
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

NEW_HEADER_ALIASES = {
    "Naziv trgovca - format": "Naziv trgovca - formata",
    "Naziv trgovca": "Naziv trgovca - formata",
    "Snizena cena": "Snižena cena",
    "Datum pocetka snizenja": "Datum početka sniženja",
    "Datum kraja snizenja": "Datum kraja sniženja",
}
# Header-only transliteration: preserve case, accents, punctuation and whitespace.
_CYRILLIC = "абвгдђежзијклљмнњопрстћуфхцчџш"
_LATIN = (
    "a",
    "b",
    "v",
    "g",
    "d",
    "đ",
    "e",
    "ž",
    "z",
    "i",
    "j",
    "k",
    "l",
    "lj",
    "m",
    "n",
    "nj",
    "o",
    "p",
    "r",
    "s",
    "t",
    "ć",
    "u",
    "f",
    "h",
    "c",
    "č",
    "dž",
    "š",
)
_CYRILLIC_MAP = dict(zip(_CYRILLIC, _LATIN, strict=True))
_CYRILLIC_MAP.update(
    {key.upper(): value.capitalize() for key, value in zip(_CYRILLIC, _LATIN, strict=True)}
)


def cyrillic_header(header: list[str]) -> list[str] | None:
    """Convert only a fully Serbian Cyrillic header, without normalizing names."""
    if not header or any(
        not any(character in _CYRILLIC_MAP for character in name)
        or any(character.isalpha() and character not in _CYRILLIC_MAP for character in name)
        for name in header
    ):
        return None
    return [
        "".join(_CYRILLIC_MAP.get(character, character) for character in name) for name in header
    ]
