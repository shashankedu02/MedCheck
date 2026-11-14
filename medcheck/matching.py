"""Batch-led matching against the NSQ dataset. Produces a MatchAssessment, never a final status.

Rules (docs/MATCHING.md):
  * exact normalized batch key is the only route to CONFIRMED;
  * product identity must corroborate (brand OR all active-ingredient words, no strength/form
    conflict); short batches need two independent identity signals;
  * a confusable-equivalent rival row (O/0, I/1/L, S/5, B/8) or several exact rows -> COLLISION;
  * near-batch candidates (confusable-equivalent or small edit distance) -> FUZZY_ONLY, never proof.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from rapidfuzz.distance import Levenshtein

from . import config
from .dataset import Dataset, DatasetIntegrityError, DatasetRecord
from .dates import manufacture_after_expiry
from .models import MatchAssessment, MatchOutcome
from .normalization import BatchKey, batch_key
from .product import ProductInfo, parse_product_name, score_identity


@dataclass(frozen=True)
class DatasetIndex:
    dataset: Dataset
    by_key: dict[str, tuple[DatasetRecord, ...]]
    by_confusable: dict[str, tuple[DatasetRecord, ...]]
    keys: dict[int, BatchKey]
    products: dict[int, ProductInfo]

    @classmethod
    def build(cls, dataset: Dataset) -> "DatasetIndex":
        by_key: dict[str, list[DatasetRecord]] = defaultdict(list)
        by_conf: dict[str, list[DatasetRecord]] = defaultdict(list)
        keys: dict[int, BatchKey] = {}
        products: dict[int, ProductInfo] = {}
        for r in dataset.records:
            bk = batch_key(r.batch_number)
            if not bk.key:
                raise DatasetIntegrityError("dataset batch number has no letters or digits")
            keys[r.serial] = bk
            by_key[bk.key].append(r)
            by_conf[bk.confusable_key].append(r)
            products[r.serial] = parse_product_name(r.product_name, r.manufactured_by)
        return cls(dataset, {k: tuple(v) for k, v in by_key.items()}, {k: tuple(v) for k, v in by_conf.items()}, keys, products)


def _fuzzy_limit(length: int) -> int:
    """Max edit distance for retrieval; keys shorter than 6 get exact-only retrieval."""
    if length < config.SHORT_BATCH_KEY_LENGTH:
        return 0
    return 2 if length >= 10 else config.FUZZY_BATCH_MAX_DISTANCE


def _source_caveats(rec: DatasetRecord, bk: BatchKey) -> tuple[str, ...]:
    out: list[str] = []
    if manufacture_after_expiry(rec.manufacturing_date, rec.expiry_date):
        out.append("The listed record itself shows an expiry date earlier than its manufacturing date (as published by CDSCO).")
    if any(not c.isalnum() for c in rec.batch_number):
        out.append(f"The listed batch is published as '{rec.batch_number}'; punctuation and spacing were ignored when comparing.")
    return tuple(out)


def match_batch(index: DatasetIndex, batch: BatchKey, ocr_text: str) -> MatchAssessment:
    """Match one cleanly-read batch. `ocr_text` is only used as product corroboration."""
    if not batch.key:
        raise ValueError("batch key is empty; extraction must not pass an unreadable batch to matching")

    exact = index.by_key.get(batch.key, ())
    if len(exact) > 1:
        return MatchAssessment(
            MatchOutcome.COLLISION,
            "several dataset rows share this batch key",
            candidate_serials=tuple(r.serial for r in exact),
            evidence=(f"Listed serials {', '.join(str(r.serial) for r in exact)} share the same normalized batch.",),
        )

    if len(exact) == 1:
        rec = exact[0]
        rivals = [r for r in index.by_confusable.get(batch.confusable_key, ()) if r.serial != rec.serial]
        if rivals:
            serials = tuple(sorted([rec.serial, *(r.serial for r in rivals)]))
            return MatchAssessment(
                MatchOutcome.COLLISION,
                "batch is confusable with another listed batch",
                candidate_serials=serials,
                evidence=(
                    f"The batch matches listed serial {rec.serial}, but listed serial(s) "
                    f"{', '.join(str(r.serial) for r in rivals)} differ only by look-alike characters (O/0, I/1/L, S/5, B/8) "
                    "or spacing, so the reading cannot be tied to one entry.",
                ),
            )
        ident = score_identity(index.products[rec.serial], ocr_text)
        short = len(batch.key) < config.SHORT_BATCH_KEY_LENGTH
        lines = [f"Exact batch match with listed serial {rec.serial}."]
        lines.append("Brand name found in the photo text." if ident.brand_match else "Brand name not found in the photo text.")
        lines.append(
            "All active-ingredient words found in the photo text."
            if ident.ingredient_match
            else f"Active-ingredient words not all found (missing: {', '.join(ident.ingredient_missing) or 'none listed'})."
        )
        if ident.strength_match:
            lines.append("Strength matches.")
        if ident.manufacturer_match:
            lines.append("Manufacturer name found in the photo text.")
        if ident.strength_conflict:
            lines.append("Strength in the photo conflicts with the listed strength.")
        if ident.form_conflict:
            lines.append("Dosage form in the photo conflicts with the listed form.")
        if short:
            lines.append("Short batch number: stronger identity evidence is required.")
        ev = tuple(lines)

        if ident.has_conflict:
            return MatchAssessment(MatchOutcome.CONFLICT, "product strength/form conflicts", candidate_serials=(rec.serial,), evidence=ev)
        corroborated = (
            (ident.ingredient_match and (ident.brand_match or ident.manufacturer_match))
            if short
            else (ident.brand_match or ident.ingredient_match)
        )
        if not corroborated:
            return MatchAssessment(MatchOutcome.UNCORROBORATED, "identity evidence insufficient", candidate_serials=(rec.serial,), evidence=ev)
        return MatchAssessment(
            MatchOutcome.CONFIRMED,
            "unique exact batch with corroborating product identity",
            matched_serial=rec.serial,
            candidate_serials=(rec.serial,),
            evidence=ev,
            source_caveats=_source_caveats(rec, batch),
        )

    # No exact row. Look for near candidates (retrieval only).
    near: dict[int, str] = {}
    for r in index.by_confusable.get(batch.confusable_key, ()):
        near[r.serial] = "look-alike characters"
    limit = _fuzzy_limit(len(batch.key))
    if limit:
        for serial, bk in index.keys.items():
            if len(bk.key) >= config.SHORT_BATCH_KEY_LENGTH and serial not in near:
                d = Levenshtein.distance(batch.key, bk.key, score_cutoff=limit)
                if d <= limit:
                    near[serial] = f"edit distance {d}"
    if near:
        return MatchAssessment(
            MatchOutcome.FUZZY_ONLY,
            "only similar batches exist in the dataset",
            candidate_serials=tuple(sorted(near)),
            evidence=tuple(f"Listed serial {s} has a similar batch ({why}); similarity is not a match." for s, why in sorted(near.items())),
        )
    return MatchAssessment(MatchOutcome.NO_MATCH, "no listed batch matches or resembles the reading")
