"""Serbian query transliteration and the Latin twin of korpa_norm."""

import json
from importlib.resources import files
from typing import cast

_UNACCENT = str.maketrans(
    cast(
        dict[str, str],
        json.loads(
            files("korpa_api").joinpath("data/unaccent16.json").read_text(encoding="utf-8"),
        ),
    )
)

_LOWER = dict(
    zip(
        "абвгдђежзијклљмнњопрстћуфхцчџш",
        (
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
        ),
        strict=True,
    )
)
_MAP = {**_LOWER, **{key.upper(): value.capitalize() for key, value in _LOWER.items()}}


def transliterate(text: str) -> str:
    return "".join(_MAP.get(character, character) for character in text)


def normalize(text: str) -> str:
    """Lowercase, expand đ, then apply the verified PostgreSQL 16 dictionary."""
    lowered = text.lower().replace("đ", "dj")
    return lowered.translate(_UNACCENT)


def normalize_query(text: str) -> str:
    return normalize(transliterate(text))
