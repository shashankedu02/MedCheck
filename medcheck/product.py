"""Parse dataset product names and score product-identity evidence found in OCR text.

Dataset names look like
  "Linezolid Tablets IP 600mg (Brand Name : Linzotal 600)"
  "Telmisartan & Amlodipine Tablets IP (Telsa A) (Brand Name : NA)"
Product evidence is only ever CORROBORATION of a batch match; it can never alert on its own.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from . import config
from .normalization import normalize_text, tokens

_BRAND_CLAUSE = re.compile(r"\(\s*Brand\s*Name\s*:\s*(?P<brand>.*?)\s*\)\s*$", re.I | re.S)
_PAREN = re.compile(r"\(([^()]*)\)")
_STRENGTH = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|mcg|ug|µg|gm|g|ml|iu|i\.u\.|%)(?![a-z])", re.I)
_STOP = {
    "tablet", "tablets", "capsule", "capsules", "injection", "injections", "syrup", "suspension", "solution", "cream",
    "ointment", "gel", "drops", "drop", "lotion", "powder", "oral", "and", "with", "in", "of", "for", "the", "gastro",
    "resistant", "film", "coated", "sustained", "extended", "release", "dispersible", "chewable", "forte", "plus",
    "vitamin", "vit", "infusion", "intravenous", "usp", "bp", "ip", "eye", "ear", "nasal", "sterile", "water",
}
# Salt/hydrate words: weak identity signal, not required to match.
_SALT_PREFIXES = ("sodium", "potass", "hydrochlorid", "hcl", "sulph", "sulf", "acetate", "maleate", "tartrate", "citrate",
                  "phosphate", "besylate", "mesylate", "succinate", "hydrate", "anhydrous", "bromide", "hydrobromide")
_FORMS = {
    "tablet": "tablet", "tablets": "tablet", "capsule": "capsule", "capsules": "capsule", "injection": "injection",
    "syrup": "syrup", "suspension": "suspension", "solution": "solution", "cream": "cream", "ointment": "ointment",
    "gel": "gel", "drops": "drops", "lotion": "lotion", "powder": "powder",
}
_ORG_STOP = {"pharma", "pharmaceuticals", "pharmaceutical", "pvt", "ltd", "limited", "private", "labs", "laboratories",
             "laboratory", "healthcare", "health", "care", "lifesciences", "life", "sciences", "industries", "india",
             "unit", "drugs", "formulations", "the", "and", "llp", "co", "company", "plot", "no", "vill", "road"}


@dataclass(frozen=True)
class ProductInfo:
    brand_aliases: tuple[str, ...]  # real brand names only ("NA" excluded)
    ingredient_tokens: tuple[str, ...]  # distinctive active-ingredient words that must be found
    strengths: frozenset[tuple[float, str]]
    forms: frozenset[str]
    manufacturer_tokens: tuple[str, ...]  # distinctive words of the manufacturer name (optional corroboration)


def _norm_unit(unit: str) -> str:
    u = unit.lower().replace(".", "")
    return {"gm": "g", "ug": "mcg", "µg": "mcg"}.get(u, u)


def extract_strengths(text: str) -> frozenset[tuple[float, str]]:
    return frozenset((float(v), _norm_unit(u)) for v, u in _STRENGTH.findall(text))


def _is_salt(tok: str) -> bool:
    return tok.startswith(_SALT_PREFIXES)


def parse_product_name(name: str, manufacturer: str = "") -> ProductInfo:
    brand_aliases: list[str] = []
    generic = name
    m = _BRAND_CLAUSE.search(name)
    if m:
        brand = m.group("brand").strip()
        generic = name[: m.start()]
        if brand and normalize_text(brand) != "na":
            brand_aliases.append(brand)
    for p in _PAREN.findall(generic):  # extra parenthesised brand aliases, e.g. "(Telsa A)"
        if re.search(r"[A-Za-z]{3,}", p) and not extract_strengths(p):
            brand_aliases.append(p.strip())
    generic_no_paren = _PAREN.sub(" ", generic)
    forms = frozenset(_FORMS[t] for t in tokens(generic_no_paren) if t in _FORMS)
    ingr = []
    for t in tokens(generic_no_paren):
        if len(t) >= 4 and t.isalpha() and t not in _STOP and not _is_salt(t) and t not in ingr:
            ingr.append(t)
    if not ingr:  # the listed name is itself a brand-like string (e.g. "DEC-Plus")
        bare = generic_no_paren.strip(" .,-")
        if len(re.sub(r"[^A-Za-z0-9]", "", bare)) >= 4:
            brand_aliases.append(bare)
    org_tokens = [t for t in tokens(manufacturer.split(",")[0]) if len(t) >= 4 and t.isalpha() and t not in _ORG_STOP][:2]
    return ProductInfo(
        brand_aliases=tuple(brand_aliases),
        ingredient_tokens=tuple(ingr),
        strengths=extract_strengths(generic),
        forms=forms,
        manufacturer_tokens=tuple(org_tokens),
    )


@dataclass(frozen=True)
class IdentityEvidence:
    brand_match: bool
    ingredient_match: bool  # every required ingredient word found
    ingredient_found: tuple[str, ...]
    ingredient_missing: tuple[str, ...]
    strength_conflict: bool
    strength_match: bool
    form_conflict: bool
    manufacturer_match: bool

    @property
    def has_conflict(self) -> bool:
        return self.strength_conflict or self.form_conflict


def _compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize_text(text))


def _token_found(token: str, ocr_tokens: list[str]) -> bool:
    if len(token) < 6:
        return token in ocr_tokens
    return any(fuzz.ratio(token, t) >= config.INGREDIENT_MATCH_MIN_SCORE for t in ocr_tokens if abs(len(t) - len(token)) <= 3)


def score_identity(info: ProductInfo, ocr_text: str) -> IdentityEvidence:
    ocr_tokens = tokens(ocr_text)
    ocr_compact = _compact(ocr_text)

    brand_match = False
    for alias in info.brand_aliases:
        a = _compact(alias)
        if len(a) < 4:
            continue
        if len(a) <= 5:
            brand_match = a in ocr_compact
        else:
            brand_match = fuzz.partial_ratio(a, ocr_compact) >= config.BRAND_MATCH_MIN_SCORE
        if brand_match:
            break

    found = tuple(t for t in info.ingredient_tokens if _token_found(t, ocr_tokens))
    missing = tuple(t for t in info.ingredient_tokens if t not in found)
    ingredient_match = bool(info.ingredient_tokens) and not missing

    ocr_strengths = extract_strengths(ocr_text)
    strength_conflict = bool(info.strengths and ocr_strengths and not (info.strengths & ocr_strengths))
    strength_match = bool(info.strengths & ocr_strengths)

    ocr_forms = {_FORMS[t] for t in ocr_tokens if t in _FORMS}
    form_conflict = bool(info.forms and ocr_forms and not (info.forms & ocr_forms))

    manufacturer_match = bool(info.manufacturer_tokens) and _token_found(info.manufacturer_tokens[0], ocr_tokens)

    return IdentityEvidence(
        brand_match, ingredient_match, found, missing, strength_conflict, strength_match, form_conflict, manufacturer_match
    )
