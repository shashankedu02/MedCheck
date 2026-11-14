# Independent Evaluation Strategy and Testing Feasibility Assessment

Status: **assessment written 2026-11-15 before the completion sprint** (no code was changed to produce it; no reserved photograph was opened).

**Sprint outcome (M13, same day):**
- **F1:** the metrics are now confirmation-aware (D-028). D-014 stays OPEN, and the category design is proposed in `docs/EVALUATION.md`.
- **F2/F3:** mitigated by the alert-side check (D-027) and documented as limitations. Matching is unchanged; the manufacturer rule is post-demonstration work.
- **F6:** labelled fixtures and a separate fixture check exist (category C2).
- **F10:** the documentation contradictions are fixed.
- **Not done (post-demonstration):** F4 (human study), F5 (physically verified references), F7, F8 (date agreement before D-007).
- Sections 0-9 below are the assessment as written.

Evidence tags used throughout:
- **[M]** measured in this session (command run, output seen);
- **[S]** source-derived (read from code, tests, docs or the official dataset);
- **[A]** assumption (not verified);
- **[R]** recommendation.

---

## 0. State verification (post-compaction)

| Check | Result |
|---|---|
| Git | **[M]** `master` at `e7eda99`, working tree clean. History `d7f6e7a` (M1) ... `a735acb` (M9), `a840a31` (M10), `c83ecf3` (M11), `e7eda99` (M12), matching the brief. |
| Tests | **[M]** `pytest -q` -> **343 passed** in 78.5 s (matches `BUILD_PROGRESS.md`). |
| Dataset | **[S]** 220 records, single reporting period `AUG-2026`, canonical SHA-256 pinned (`docs/DATASET.md`). |
| Expiry | **[S]** `config.EXPIRY_POLICY_APPROVED = False` (`medcheck/config.py:114`); `Expired` is never emitted. |
| Reserved photos | **[S]** Spent on 2026-11-15 (`docs/HELDOUT_EVALUATION.md`, `evaluation/heldout_ids.txt`). |

**Contradictions found (documentation only; none blocks this assessment; not fixed, by instruction):**
1. `BUILD_PROGRESS.md` line 13 ("7 photos are reserved and untouched"), "What remains" item 3 (held-out run still to do), and "Next action" ("decide whether to run the held-out photographs") contradict M12 and `docs/HELDOUT_EVALUATION.md`.
2. `docs/MATCHING.md` line 19 says near-batch retrieval uses edit distance **1** for 6-9 character keys. Line 29 of the same file, the code (`medcheck/matching.py:50-54`, `_fuzzy_limit`) and `config.FUZZY_BATCH_MAX_DISTANCE = 2` all use **2** for every key of 6+ characters. The code is the more cautious of the two (wider abstention).
3. `docs/EVALUATION.md` "Planned study" and `docs/PROJECT_SPEC.md` line 33 still plan **30 NSQ-listed photographs**. The brief states this is not obtainable; see finding F1.
4. `medcheck/evaluation.py` (the D-014 metric script, M6) predates D-026; see finding F1.
5. The system-error text for `OCR_ENGINE_UNAVAILABLE` (`medcheck/decision.py:41`) names only Tesseract, although RapidOCR is primary. The reporting rules in `docs/EVALUATION.md` mention only the Tesseract version.

One premise in the brief is challenged: expired medicines are not hard to obtain, and are not needed for most expiry testing (section 3.C).

Missing information that changes the roadmap: **the summit date.** If it is days away, only phases 0-1 and the demo fixtures (section 6) are realistic before it.

---

## 1. Ranked findings (severity x practical importance)

| # | Severity | Finding | Tag |
|---|---|---|---|
| F1 | **Critical (evaluation validity)** | The D-014 protocol cannot be executed as written, and its metric script gives misleading numbers since D-026 | S |
| F2 | **High (false positive)** | Sibling-batch pathway: a one-character misread of an unlisted sibling batch gives an immediate `Alert found` | S, M |
| F3 | **High (false positive)** | Product corroboration is weak for many rows; a legible conflicting manufacturer never blocks an alert; background text can corroborate | S, M |
| F4 | **High (false negative)** | D-026 moves the false-negative risk onto an unmeasured human comparison | S |
| F5 | **High (evaluation integrity)** | No reference is independent: all were read by the AI that tuned the system; none is physically verified; the held-out set leaked and is spent | S |
| F6 | Medium | All positive-path evidence is self-referential (dataset wording and dataset strings rendered in Arial) | S |
| F7 | Medium | The single-image design versus corroboration: the batch face often lacks the brand, so real alerts may abstain | S, A |
| F8 | Medium (latent) | Dates are accepted from a single OCR pass and are not confirmed by the user; harmless while D-007 is off, unsafe if it is approved as is | S |
| F9 | Medium (claims) | One monthly list, about 3 months old at the summit; 2 listed batches can never be detected; 27 short keys get exact-only retrieval | S, M |
| F10 | Low | Documentation contradictions listed in section 0 | S |
| F11 | Low | Timing comes from one machine under variable load | S |

### F1. The D-014 protocol cannot be executed and its metrics are now wrong
- **[S]** `docs/EVALUATION.md` and `docs/PROJECT_SPEC.md` require 30 NSQ-listed photographs. These cannot be obtained.
- **[S]** `medcheck/evaluation.py:61-65` counts only `NO_ALERT_FOUND` as a true negative and only `NO_ALERT_FOUND`/`EXPIRED` as a false negative.
  - Since D-026, `MedCheckPipeline.check()` never shows a clean negative, because nobody confirms the batch. The script would therefore report specificity of about 0% and abstention of about 100% for every non-listed image.
  - A listed batch misread as an unlisted string becomes `ocr_batch_unconfirmed`. It is counted as an abstention, not as a near-miss false negative.
  - `medcheck/real_eval.py` already handles D-026 (Inconclusive plus `batch_result`); `evaluation.py` does not.
- **[R]** Replace the 30/30 design with the category architecture in section 4. Update the metric tooling before any study. Until then, `scripts/evaluate.py` must not be used for any headline number.

### F2. Sibling-batch false-positive pathway (most realistic false alert)
- **[M]** 22 pairs of listed batch keys (6+ characters) are within edit distance 2 of each other. Of the 16 pairs I inspected, 12 share a manufacturer and at least 8 are the same product and strength:
  - `PAK-636`/`PAK-637` (serials 118, 113), paracetamol 500 mg;
  - `493TTF024`/`493TTF026`, telmisartan 40 mg;
  - `TGT25-100`/`TGT25-104`, valproate;
  - `V260302`/`V260305`;
  - `KBI26068C`/`KBI26030C`.
- **[M]** 14 one-digit changes of a listed key land exactly on another listed key.
- **[S]** These show that manufacturers number batches sequentially. **[A]** Unlisted siblings (`PAK-635`, `493TTF025` ...) are therefore very likely in circulation, and much more likely on a shelf than a random string.
- **The pathway [S]:**
  1. The pack carries an unlisted sibling batch.
  2. Two OCR passes agree on a one-character misread that equals a listed sibling. Consistent misreads do happen: `HLA50019` on two views, and `UBO20` on two passes in T009.
  3. `match_batch` (`medcheck/matching.py:80-132`) finds a unique exact key. The confusable check folds only O/0, I/1/L, S/5 and B/8, so a 3/5 or 6/8 difference is not a collision.
  4. Product corroboration is guaranteed, because the sibling is the same product.
  5. The result is `Alert found` immediately. Alerts are not delayed (D-026), and nothing asks the user to compare the printed batch.
- **[S]** The D-026 rationale in `docs/MATCHING.md` ("a misread rarely satisfies exact listed batch plus product corroboration") is weakest exactly in this case.
- **Not measured:** the real-world rate. It depends on OCR digit-confusion rates for real print, which no current data measures.
- **[R]** Measure it (matrix rows P10 and R11). Put a separate owner decision on an alert-side comparison prompt: show the batch read next to the listed batch and ask the user to check it on the pack before acting. This would not delay or suppress the alert. It is a UI change, so it is not for now.

### F3. Weak corroboration, ignored manufacturer conflict, background text
Weak corroboration:
- **[M]** 80 of 220 rows have no brand alias, so they depend on ingredient words alone.
- **[M]** 45 rows with a key of 6+ characters are corroborated by a **single ingredient word** and no brand (e.g. `vildagliptin`, `dexamethasone`, `itraconazole`). Paracetamol alone covers 9 rows.

Conflict checks that cannot fire:
- **[M]** 138 of 220 product names contain no strength, so the strength-conflict check (`medcheck/product.py:140-142`) cannot fire for 63% of rows.

Manufacturer:
- **[S]** The manufacturer only ever adds support (`product.py:147`, D-006). A legible *different* manufacturer never blocks an alert.
- **Pathway:** a different maker's paracetamol whose batch string happens to equal a listed one gives `Alert found`, attributed to the wrong maker.
- **[A]** Batch strings are not globally unique; they are assigned independently by about 189 manufacturers.

Background text:
- **[S]** Corroboration text is `ExtractionResult.product_text` (`medcheck/extraction.py:224-236`). It is every line recognised from every pass, including rotations, the full frame and Tesseract output. Brand or ingredient words from a second pack in the background, or from a shelf label, count.

**Not measured:** how often any of this happens on real photos.

**[R]** Add the tests in matrix rows P3-P5 to pin the current behaviour, measure corroboration discrimination on real OCR text (section 3.B), and refer a "legible conflicting manufacturer -> abstain" rule to the owner. That rule would only make the system more cautious; it is not for now.

### F4. D-026 shifts false-negative risk onto an unmeasured human step
**[S][M] What reaches the user's comparison step:** every misread that is neither exact, confusable nor near a listed batch. That includes:
- **842 one-digit misreads of short keys:** all 842 one-digit misreads that end in no match come from the 27 short listed keys (under 6 characters), which get exact-only retrieval.
- **Long misreads:** any misread more than 2 edits from the listed key.
- **Glued labels:** a 3-character glued label on a listed batch (`...MF6`).

Whether a typical user catches `S` vs `5`, `8` vs `B` or a missing final character is **unmeasured**:
- The owner's browser test shows a motivated developer catching a known error, not a typical user.
- **[A]** Automation bias makes "tick without looking" likely when the app shows a clean-looking string. `docs/MATCHING.md` already concedes this.

**[R]** Run a human-factors study (category C5, matrix H1). Report the "wrong string offered for confirmation" rate as the load placed on the human.

### F5. Ground truth is not independent
- **[S]** Every reference (`evaluation/reference_batches.csv`, `evaluation/reference_batches_heldout.csv`) was read by eye by the same AI assistant that designed the parser and guards. None has been checked against a physical pack.
- **[S]** T019's reference was read *after* V2 had produced the same string, as the CSV note says.
- **[S]** T024 is the same pack as dev photo T003, and T027 comes from the same maker as T026.
- **[S]** The dev misreads are encoded in tests (`KNOWN_WRONG` in `tests/test_v2_parser_and_misreads.py`; `tests/test_v2_pipeline.py:95`).
- **[S]** Result: no real photograph exists that is both unseen by development and human-labelled from the pack.
- **[R]** Retire AI-read references from all scoring. Ground truth comes from two independent human readers looking at the physical pack, recorded before the software runs (section 3.B).

### F6. Positive-path evidence is self-referential
- **[S]** The 220-row test (`tests/test_matching.py:145-163`) uses `photo_text(r)`, built from the dataset's own product wording. Real packs print brand-led text, composition lines and different spellings.
- **[S]** The demo and test images (`scripts/make_demo_images.py`, `tests/helpers.py`) render dataset strings in Arial, black on white.
- **[S]** The listed string may itself differ from what is printed on the pack. Lab transcriptions such as serial 121 `0l25038` and serial 157 `BKBP O2601` (an O in place of a zero) suggest this. Any positive built from the list is an exact match by construction, so it can never reveal such a difference.
- **[R]** Label all such evidence "logic consistency" or "fixture pass rate", never "detection".

### F7. Single image versus corroboration
- **[S]** One image per check (D-009). An alert needs the batch and the brand or ingredients in the same frame.
- **[A]** On many cartons the batch sits on an end flap and the brand on the front. Strips repeat both, but often at opposite ends.
- **Effect:** a listed pack photographed batch-face-only gives `identity_uncorroborated`. That is safe, but it is a miss in practice.
- **[R]** Test it (rows P6 and R13), and give users framing guidance.

### F8. Dates: single-pass acceptance and no confirmation
- **[S]** `reconcile_date` (`medcheck/extraction.py:198-205`) accepts a date from **one** pass, whereas a batch needs two. Dates are never user-confirmed.
- **[S]** T027 showed a year disagreement (`06/2029` vs `06/2026`). It was caught only because two passes read it.
- **Effect if D-007 is approved unchanged:**
  - A single-pass misread year could produce a false `Expired`.
  - Worse, it could produce a reassuring "has not passed" note (`medcheck/dates.py:86`).
- **[R]** Treat date agreement plus user confirmation as preconditions of D-007 (section 7).

### F9. Scope and coverage limits
- **[S]** One list (August 2026). **[A]** By the summit it will be about 3 months old, and later monthly lists are not checked. The wording already says so; demo messaging must too.
- **[S][M]** Serials 24 (`49`) and 26 (`38`) have 2-character batches and are never extracted (`tests/test_extraction.py:107-116`).
- **[S][M]** 27 keys are under 6 characters, and 26 keys are digits only.

---

## 2. What each existing piece of evidence actually shows

| Evidence | Shows | Does not show |
|---|---|---|
| 343 automated tests [M] | Specification compliance of normalization, matching, decision, extraction guards, pipeline control flow, privacy and integrity failures, UI wording, for all 220 listed rows at text level | Any real-world OCR accuracy; any rate |
| 27-photo baseline (Tesseract) [S] | Tesseract failed on real photos (25 not found) | Anything about V2 |
| 20-photo dev runs [S] | Diagnostics on tuning data: 0 wrong batches accepted among 7 AI-read references | Unbiased performance (in-sample, unverified references) |
| 7-photo reserved run [S] | One consistent misread withheld by D-026; 0 wrong among 4 AI-read references; 5 abstentions | Accuracy (n=4, leakage, no listed pack, unverified references) |
| Owner browser tests [S] | The UI workflow behaves as designed in a real browser | OCR accuracy; behaviour of typical users |

---

## 3. Technical assessment by question

### 3.A Testing positive NSQ detection without the physical medicine
Layers, from logic to physical:

| Layer | What it exercises | OCR? | Matching? | UI/workflow? | Realism |
|---|---|---|---|---|---|
| A1. Direct matching tests with known strings (exists: `test_matching.py`) | `match_batch`, `score_identity`, `decide` | no | **yes** | no | logic only |
| A2. Pipeline tests with injected OCR passes (exists: fake engines in `test_v2_pipeline.py`) | extraction, reconciliation, strict agreement, cascade control, matching, decision | no (engine faked) | yes | no | logic only |
| A3. Integration tests over all 220 real records with realistic pack wording (**new**) | corroboration on pack-like text, not CDSCO wording | no | yes | no | semi-realistic text |
| A4. Rendered synthetic images through the real engines (exists for 6 demo cases; **extend**) | real OCR on clean renders, the full chain | **yes, optimistic** | yes | yes (via AppTest) | low |
| A5. Real photos of ordinary packs with listed batch text inserted digitally (**new**) | real OCR in real context, but the inserted glyphs are artificial unless transplanted from the same pack | partly | yes | yes | medium; must be watermarked |
| A6. Controlled physical fixtures: a listed batch printed on a label applied to an **empty** carton of the matching generic, marked TEST (**new**) | real camera, lighting, substrate and framing; print differs from industrial inkjet or laser | **yes, closest feasible** | yes | yes | medium-high |
| A7. Real photographs of quarantined or recalled NSQ stock (opportunistic) | everything | yes | yes | yes | real |

Assessment:
- **A1-A3** are the backbone. They are cheap, exhaustive over the 220 rows, and deterministic. They can prove "for every listed row, given a correct reading and pack-like text, the system alerts or abstains, and never gives a clean negative". They prove nothing about reading.
- **A4** is a regression and demo tool. Rendered Arial text is the easiest possible OCR input, so any pass rate here is an upper bound, not an estimate.
- **A5 vs A6:**
  - A5 is reproducible and cheap, but creates convincing images of "affected" packs. Every pixel copy needs a visible in-image watermark plus metadata, and the files must never be shown without the label.
  - **"Glyph transplant"** (composing the listed number from characters the same pack already prints) is the most realistic variant, but it is labour-intensive.
  - A6 gives physically real captures and a strong demo, but needs ethics rules: empty packaging only, never saleable stock, a visible "TEST FIXTURE - NOT A MEDICINE" mark, an inventory, and destruction afterwards.
- **A7:** **[A]** pharmacies may hold NSQ or recalled stock in quarantine pending return. With a pharmacist's or drug inspector's permission, *photographs* of it would be the only real positives. Worth asking; never to be depended on.
- **Choosing rows for A5/A6:** prefer listed rows with a real brand, so the stronger corroboration path is shown. Also include one brand-`NA` single-ingredient row, because it demonstrates F3 honestly.
- **Never** insert synthetic batches into the production dataset. Fixtures must use real public rows. A test-only dataset may be used inside tests only, loaded through a separate path that cannot reach the app.

### 3.B Negative-case testing with ordinary pharmacy photographs
Ground truth needed per pack, recorded **before** the software runs:
- the exact printed batch;
- brand, generic and strength;
- manufacturer;
- manufacturing and expiry dates as printed;
- which faces are in each photo.

Verifying batch identity:
- Two independent readers, neither the developer nor any AI, read the **physical pack** under good light with a loupe.
- Disagreement goes to adjudication. Anything still uncertain is excluded and counted.
- Store a private close-up reference shot for audit.
- Commit the label file, or its SHA-256, before the run as pre-registration.

Establishing that a pack is a regulatory negative:
- Look up the human-recorded batch string in the official extraction: an exact-string check plus a manual look for near neighbours.
- **Do not** use MedCheck's matcher to define truth; that would be circular.
- Record separately whether the true batch is within 2 edits of a listed batch. If it is, the *spec-expected* outcome is `Unable to verify` (fuzzy), not a clean negative.

Two expected outcomes per pack:
- **(a) regulatory truth:** listed or not;
- **(b) spec-expected behaviour given a perfect reading.**

Scoring:
- FP and FN are scored against (a); spec compliance against (b).
- Under D-026 the decisive automated quantities on negatives are:
  1. **false alerts** (count, with a rule-of-three upper bound);
  2. the **batch string offered for confirmation**: exact, wrong or abstained;
  3. abstention reasons.
- "No alert found" itself requires a human, so it belongs to category C5.

Testing product and manufacturer corroboration with real data, but no NSQ packs (**hybrid**):
- For each fresh real photo, take its recorded OCR `product_text` and run `score_identity` against all 220 rows.
- This measures:
  - (i) corroboration sensitivity: rows of the *same* product as the pack should corroborate;
  - (ii) spurious corroboration: rows of *other* products should not.
- Real noisy text, no NSQ pack needed. Label it "semi-synthetic".
- Use dev or fresh photos only, never the spent reserved set.

Avoiding unverified visual readings as truth:
- Keep a `label_source` field on every label.
- Only `human-physical-double` labels are scored. AI or visual-only readings are kept as `unscored`.

### 3.C Expiry testing (verdict stays disabled)
- **Premise challenge [A]:** expired packs are common in household medicine cabinets and in pharmacy expiry-return bins, so they are photographable with permission. More importantly, they are not needed:
  - **Date reading** is tested on *any* pack; every pack prints an expiry date.
  - **Verdict logic** is tested by clock injection: `MedCheckPipeline(today=...)` (`medcheck/pipeline.py:102`) turns any real photo into a "clearly expired" or "clearly unexpired" case. This runs only in tests, with the policy flag patched inside the test, never in configuration.
- **Formats [S]:** the parser supports MM/YYYY, MM-YY, MMM YYYY, MMMYY, YYYY-MM; day-level dates are rejected. Existing tests: `tests/test_normalization_dates.py:55-63`. **[M]** All 220 listed dates are `Mon-YYYY`.
- **Ambiguous or incomplete:** missing year, 2-digit year, both dates unlabelled, expiry label adjacent to a price, `USE BEFORE`, a pack with only one date. The expected result is "not read", never guessed.
- **OCR date errors:**
  - 2026/2028 and 6/8 confusions;
  - a single-pass misread (F8);
  - a month name misread (`JUN`/`JAN`).
  - Expected now: a display-only reading with a note. For D-007: agreement plus confirmation (section 7).
- **Boundaries:** last day of the printed month versus the first of the next; device clock and timezone (IST); the expiry-before-manufacture anomaly (exists).
- **Do not** recommend enabling `Expired` (section 7).

### 3.D OCR robustness: realism of each condition

| Condition | Real capture (RC) | Realistic transform of a real photo (RT) | Artificial (AR) |
|---|---|---|---|
| Rotation 90/180/270 | yes | **yes** (lossless, exact) | - |
| Small skew 5-20 degrees | yes | yes (interpolation only) | - |
| Perspective | **preferred** | approximate for flat cartons only | on curved packs |
| Glare | **only valid source** | - | overlays (real glare destroys data) |
| Blur (motion/defocus) | preferred | Gaussian approximates defocus | synthetic motion on renders |
| Low resolution / compression | yes | **yes** (downscale, JPEG recompress) | - |
| Foil / blister | **only** | - | foil textures |
| Curved surfaces (bottles, rolled strips) | **only** | - | warps of flat images |
| Background text / clutter | **preferred** | - | compositing |
| Adjacent glued labels (MFG/EXP/MRP) | yes | - | string-level tests (exist) are valid for the parser |
| S/5, O/0, I/1, B/8 | packs whose batch contains them | - | font renders (dot-matrix-style fonts are closer than Arial) |
| Truncated batch | yes (framing) | **yes** (crop through the batch line) | - |
| Batch on another face | **only** (photograph each face) | - | - |
| Embossed / inkjet dot-matrix / laser-etched | **only** | - | - |

Rules:
- RT conditions may be applied to fresh real photos (never to the spent ones).
- RC conditions need physical re-capture: the same pack under N controlled conditions. Ground truth is constant across shots, which makes this efficient.
- Re-captures of one pack are **correlated**. Report per pack (clustered), never as independent samples.
- AR conditions are regression and demo only.

### 3.E Dataset and matching safety

| Area | Existing tests [S] | Missing [R] |
|---|---|---|
| Exact matches | all 220 rows (`test_matching.py:145`) | pack-like wording variants (A3) |
| Near matches | `KNOWN_WRONG`, edit distance, short-key exact-only | pin the exposure counts: 842 short-key misses, 14 cross-landings |
| Look-alike characters | 38/157 both directions, serial 121, consistent misread (`test_look_alike_consistent_misread.py`) | sibling-misread tests per close pair (P10) |
| Product-name mismatch | batch only, wrong product (serial 4 text only) | an all-pairs matrix: each listed batch x every other row's text; same-generic pairs listed explicitly |
| Manufacturer mismatch | none | pin current behaviour (alerts); refer to owner |
| Background corroboration | none | product text supplied only by a second pack in the frame |
| Duplicate / conflicting records | no exact duplicates; only 38/157 confusable | a guard test that a future list with duplicates fails closed or collides (when multi-month lists arrive) |
| Integrity failures | missing, tampered, schema, BOM, row count (`test_dataset.py`, `test_pipeline.py:94-108`) | none critical |
| Missing / unreadable batch | not found, ambiguous, edge-cut, 2-character serials 24/26 | two batch labels in one photo |
| Metric tooling | `real_eval` D-026-aware | `evaluation.py` D-026 categories (F1) |

---

## 4. Recommended evaluation architecture
Five evidence categories (four requested, plus a human-factors category) and one hybrid. **Never pooled into one percentage.**

| Category | Proves | Cannot prove | Recording | Reporting | Contributes to an accuracy metric? |
|---|---|---|---|---|---|
| **C1 Real photos of ordinary packs** (fresh, human-labelled from the pack, pre-registered, dev/test split **by pack**) | Real batch-string reading, abstention mix, false alerts on non-listed packs, date reading, latency | Sensitivity to listed batches; any alert-path rate | Per-run folder (existing `real_eval` format) plus `label_source`; code commit, dataset hash and phone model | Exact / wrong / abstained with Wilson CIs; false-alert count with rule-of-three bound; per pack and per condition | **Yes**, for negative-side and reading metrics only, on the test split only |
| **C1b Controlled re-captures** (same packs, defined conditions) | Robustness per condition | Population rates | Condition code per image | Clustered per pack | Per-condition reading rates, labelled "controlled" |
| **C2 Synthetic / controlled fixtures** (renders, composites, physical test labels) | The chain works end to end including the alert path; regressions; sibling-misread frequency on controlled print | Real-world FN/FP or accuracy | `FIXTURE_` names, fixture manifest (type, listed serial, condition), visible watermark | "Fixture pass rate (n, type)" | **No** |
| **C3 Programmatic tests** (unit, integration, dataset-wide, injected passes) | Spec compliance exhaustively over the 220 rows | Anything about OCR | pytest | "N tests pass; 220/220 rows behave per spec" | **No** |
| **H Hybrid: real OCR text x programmatic batch** | Corroboration discrimination on real text | Batch reading | Script output per photo x row | Corroboration hit / spurious rates, labelled semi-synthetic | Separate metric, never merged |
| **C4 Independently verified real positives** (quarantined or recalled stock photos, if any) | Real alert-path behaviour | Rates (n will be tiny) | Same as C1, provenance of permission | Case studies with n | Only as "k of n cases", with an exact CI |
| **C5 Human-in-the-loop study** | Whether users catch planted misreads before confirming; comprehension of results | OCR accuracy | Consent, anonymised responses | Catch rate per confusable pair, with CI | Separate metric |

Statistical guidance:
- **[S]** With 0 false alerts in n negatives, the 95% upper bound is about 3/n (rule of three): 100 packs give ≤3%, 300 give ≤1%.
- **[S]** 30 positives with 27 correct give a Wilson interval of about 74-97% (`docs/EVALUATION.md`).
- Keep abstentions in denominators.

---

## 5. Test matrix
Categories: C1/C1b real, C2 fixture, C3 programmatic, H hybrid, C4 verified positive, C5 human. "Exists" means a current test covers it [S].

### Positive detection
| ID | Scenario | Input | Expected behaviour (current spec) | Cat. | Exists |
|---|---|---|---|---|---|
| P1 | Every listed row, listing wording | key plus listed name | Alert, except 38/157 Unable | C3 | yes (`test_matching.py:145`) |
| P2 | Every listed row, pack-like wording | key plus brand-led / composition-line / noisy text | Alert or Unable; never a clean negative | C3 | **no** |
| P3 | Listed batch, other product's text | key x 219 other rows' text | Never Alert, except same-generic rows (enumerate) | C3 | partial (serial 4 only) |
| P4 | Listed batch, same generic, different manufacturer legible | key plus other maker's name | **Currently Alert**; pin and refer to owner | C3 | **no** |
| P5 | Product text only from a background pack | passes where product lines come from a second pack | **Currently Alert**; pin and refer to owner | C3 | **no** |
| P6 | Listed batch, batch face only | key, no brand or ingredient | Unable (`identity_uncorroborated`) | C3 / C2 / C1b | partial |
| P7 | Short listed key (<6) | key plus one signal / two signals | Unable / Alert | C3 | yes |
| P8 | Serials 24, 26 (2 characters) | label lines | Never extracted, so Unable | C3 | yes |
| P9 | 38/157 collision | either spelling plus perfect text | Unable | C3 / C2 | yes |
| P10 | Sibling misread | pack shows an unlisted sibling, OCR yields the listed sibling | Per spec **Alert** (exposure); measure the frequency of engines producing the sibling on renders and physical labels | C3 (pin), C2 (rate) | **no** |
| P11 | Printed formatting variants | `TM5139` vs `TM 5139`, trailing comma, slashes | Alert | C3 | partial |
| P12 | Rendered fixtures, stratified listed rows | renders through the real engines | Alert or Unable, never a clean negative | C2 | 2 demo cases |
| P13 | Physical test label on an empty generic carton | photo | Same as P12; record misreads | C2 | **no** |
| P14 | Quarantined NSQ stock photo | photo | Alert or Unable | C4 | **no** |
| P15 | Typed listed batch plus matching product photo | manual entry | Alert, no confirmation needed | C3 | yes (`test_v2_manual_entry.py`) |

### Negatives
| ID | Scenario | Input | Expected | Cat. | Exists |
|---|---|---|---|---|---|
| N1 | Ordinary pack, readable unlisted batch | fresh photo, human label | Unable (`ocr_batch_unconfirmed`) offering the **exact** string; never Alert | C1 | **no (fresh)** |
| N2 | Same, OCR string wrong | fresh photo | Unable; counted as "wrong string offered" | C1 | **no** |
| N3 | Unlisted batch within 2 edits of a listed one | key | Unable (fuzzy) | C3 | yes |
| N4 | Consistent look-alike misread of an unlisted batch | injected passes | Unable until confirmed | C3 | yes |
| N5 | Confirmed true batch | manual confirm | No alert found, period wording, "batch checked" | C3 | yes |
| N6 | Confirmed wrong batch (user error) | manual confirm | No alert found (documented exposure) | C5 | **no** |
| N7 | Two packs / two batch labels in one photo | photo or injected passes | Unable (conflict) | C3 / C1 | partial |
| N8 | No batch on the visible face | photo | Unable (not found) | C1 | dev set |
| N9 | Corroboration discrimination | real `product_text` x 220 rows | Same-product hit rate; spurious rate | H | **no** |

### Expiry (production flag stays off; verdict tests patch it inside the test only)
| ID | Scenario | Input | Expected | Cat. | Exists |
|---|---|---|---|---|---|
| E1 | Clearly expired | real photo plus `today` after the printed month | Flag off: Undetermined note. Flag on (test): Expired only after batch confirmation; never hides an alert | C3 / C1 | boundary tests yes; real-photo clock injection **no** |
| E2 | Clearly unexpired | as above | Not expired | C3 / C1 | partial |
| E3 | Month boundary, timezone | injected dates | End-of-month rule | C3 | yes |
| E4 | Formats | strings | Parsed or unparseable per spec | C3 | yes |
| E5 | Day-level date | `15/06/2028` | Unparseable | C3 | yes |
| E6 | Unlabelled / single date / price nearby | lines | Not read; no guessing | C3 / C1 | partial |
| E7 | Single-pass year misread | one pass `06/2026`, true `06/2028` | **Currently accepted** (F8); pin it | C3 | **no** |
| E8 | Conflicting passes | two readings | Ambiguous, not used | C3 | yes |
| E9 | Expiry before manufacture | dates | Anomaly caveat | C3 | yes |
| E10 | Date-reading accuracy | fresh real photos | Exact / wrong / not read vs human label | C1 | **no** |
| E11 | Expired real packs (household, with permission) | photos | Reading only | C1 | **no** |

### OCR robustness (on fresh packs only; see 3.D for realism)
| ID | Condition | Method | Expected | Cat. |
|---|---|---|---|---|
| R1 | 90/180/270 rotation | RT | Same reading or abstention, never a different accepted batch | C1b |
| R2 | Skew 5-20 degrees | RC + RT | Same | C1b |
| R3 | Perspective | RC | Same | C1b |
| R4 | Glare over the batch | RC | Abstain (not found / ambiguous), never a wrong accepted batch | C1b |
| R5 | Blur | RC (+RT Gaussian) | Same | C1b |
| R6 | Low resolution / JPEG | RT | Same | C1b |
| R7 | Foil / blister | RC | Same | C1b |
| R8 | Curved bottle / rolled strip | RC | Same | C1b |
| R9 | Cluttered background, second pack | RC | No corroboration from the background (pins F3) | C1b |
| R10 | Glued adjacent labels | strings + RC | Cut or abstain | C3 + C1b |
| R11 | S/5, O/0, I/1, B/8 and 3/5, 6/8 digits | packs containing them; dot-matrix renders | Never silently substituted; disagreements abstain; measure consistent-misread frequency | C1b + C2 |
| R12 | Truncated batch | RT crop through the line | Edge rule: not used | C1b |
| R13 | Batch on another face | RC each face | Batch face: uncorroborated or awaiting confirmation; brand face: not found | C1b |
| R14 | Embossed / inkjet / laser print | RC | Record per print type | C1b |
| R15 | Low light | RC | Abstain rather than misread | C1b |

### Human factors
| ID | Scenario | Expected / measured | Cat. |
|---|---|---|---|
| H1 | Planted misreads (`HLA50019` vs a pack showing `HLAS0019`; 8/B, truncation) shown for confirmation | Catch rate per pair; time taken | C5 |
| H2 | Edit after ticking clears the confirmation | Cleared | C3 (exists) |
| H3 | Comprehension: what "Alert found", "No alert found" and "confirm" mean | Proportion interpreting correctly (not "safe", not "fake") | C5 |

---

## 6. Execution roadmap (priority order)

**Phase 0: no new data; hours to days**
1. Owner reviews this document and fixes the section-0 contradictions (documentation only, with approval).
2. Owner confirms the existing AI-read references against the physical packs, if still available (T003, T008, T009, T012, T018 first).
   - This turns the 20 dev photos into a human-labelled **regression** set.
   - They remain dev data, never test data.
3. Pre-register the evaluation plan: categories, label schema with `label_source`, split rule (by pack), frozen-commit rule and metric definitions. Commit it before collecting any new photo.

**Phase 1: programmatic (C3, H); no images; needs approval to add tests**

4. Add P2-P5, P10 (pin), E7 (pin), N7 and N9, and the exposure counts (842 / 14 / 45).
5. Make `medcheck/evaluation.py` D-026-aware: false alerts; batch string offered (exact / wrong / abstained); awaiting confirmation; clean negatives only from C5. Until then, retire its output from any report.

**Phase 2: fresh real negatives (C1, C1b)**

6. 60-100+ ordinary packs (pharmacy cooperation and household), with every relevant face photographed, using 2-3 phones including a low-end Android.
   - Two-person labelling from the pack.
   - Split by pack (for example 40% dev / 60% test).
   - Freeze the code before the test run, run it once, and report as is.
7. A subset of about 20 packs x 8 conditions for C1b.

**Phase 3: fixtures (C2); clearly labelled**

8. Renders for a stratified sample or all 220 rows through the real engines, including dot-matrix-style fonts and the sibling pairs.
9. Physical test labels on empty cartons for about 10-20 listed generics. Optionally, glyph-transplant composites. Report fixture pass rates only.

**Phase 4: human factors (C5)**

10. 10-20 volunteers with consent and planted misreads, before or at the summit (as a separate, consented station).

**Phase 5: opportunistic real positives (C4)**

11. Ask cooperating pharmacists or a drug-control contact for photographs of quarantined NSQ or recalled stock.

**Phase 6: owner decisions informed by the evidence**

12. Decisions on:
    - D-014 rewrite;
    - alert-side comparison prompt (F2);
    - conflicting-manufacturer rule (F3);
    - D-007 with the preconditions in section 7;
    - fresh held-out set policy.

---

## 7. Additional data and resources required
- Physical access to the 27 photographed packs (Phase 0).
- 60-100+ ordinary packs plus permission to photograph. Remove any patient labels: pharmacy-dispensed packs can carry names, and these are private data.
- 2-3 phone models; a loupe or magnifier; a simple labelling form.
- Two labellers independent of development (not the developer, not an AI).
- Empty cartons or strips of generics matching listed rows (e.g. paracetamol 500 mg, telmisartan 40 mg, metronidazole, calcium + D3, dexamethasone injection), a label printer, and a dot-matrix-style font.
- Volunteers and a consent form for C5.
- Optional: a pharmacist or drug-inspector contact (C4); guidance on handling and marking test packaging.
- Later CDSCO monthly lists, only if scope expansion is approved (out of scope now).
- The demo laptop, for timing on the actual hardware.

---

## 8. Bengaluru Tech Summit demonstration strategy

Principles:
- Every synthetic item is visibly synthetic **inside the camera frame**, so any visitor photo or screenshot carries the label.
- No accuracy percentage.
- The evidence is shown by category.

### Flows
1. **Ordinary medicine, live:** a real pack, the presenter's or a visitor's, with the visitor's photo never stored.
   - Show the batch, expiry and manufacturing fields and their provenance.
   - Show the "agreed by the OCR passes - not yet checked against the pack" label.
   - The visitor compares the number with the pack and ticks the confirmation.
   - The result is `No alert found` with the August 2026 period wording.
2. **NSQ-listed detection, controlled fixture:**
   - Use a card or empty carton with a large "TEST FIXTURE - NOT A REAL AFFECTED MEDICINE" banner and a real public batch from the CDSCO list with matching product text. Show `Alert found` and the matched official record.
   - Script: *"Affected batches are withdrawn, and we should not obtain them. The list is public, so we print a listed batch on a test card to prove the whole pipeline."*
3. **Safety, collision:** the 38/157 fixture (`BKBP02601` vs `BKBP O2601`) gives `Unable to verify`, because the two cannot be told apart.
4. **Safety, "spot the misread":**
   - Show the real `HLA50019` vs `HLAS0019` story.
   - Invite the visitor to compare a planted misread before confirming.
   - Explain that the app refuses false reassurance until a human checks.
   - If consented, this doubles as C5 data.
5. **Manual correction:** correct the misread and confirm. The result is labelled user-corrected, and editing clears the tick.
6. **Safe abstention:** a glare or blur photo of a real pack gives `Unable to verify` with the reason.

### Communication
- An **evidence board** with four columns: real photos, controlled fixtures, logic tests (343 tests; all 220 listed records), verified samples. Each column gives n, what it shows and what it does not.
- Framing:
  - *"MedCheck says 'unable to verify' rather than risk false reassurance."*
  - *"It checks one public CDSCO list (August 2026)."*
  - *"It is not a test of quality or authenticity."*
- Say: "checks the batch against the August 2026 CDSCO NSQ list"; "fixture"; "abstains when unsure".
- Avoid: "detects fake/spurious/unsafe medicines", "X% accurate", "verified safe", "real affected medicine".
- Prepare the honest answer to "How accurate is it?": no accuracy figure yet; here is what each kind of evidence shows; here is the plan.
- Practicalities:
  - Warm the engine before visitors arrive; a check takes about 5-11 s on the dev machine.
  - The app runs offline, so it needs no network.
  - Keep a recorded backup.
  - Name fixture files `FIXTURE_*`.
  - Never save visitor images.
- **[R]** A software "demo mode" banner would be a code change for the owner to decide on. The physical in-frame banner needs no code.

This framing does not weaken the project: refusing false reassurance, plus transparent evidence, is a stronger story for judges than an unverifiable percentage.

---

## 9. What must remain disabled or unchanged until further evidence exists
1. **`EXPIRY_POLICY_APPROVED = False` (D-007).** Proposed preconditions before approval:
   - an authoritative interpretation of month-only expiry;
   - a defined clock and timezone;
   - expiry agreement across 2 passes (as for batches);
   - user confirmation of the date before any `Expired` or "has not passed" wording;
   - C1 date-reading results (E10).
2. **D-026** (no clean negative without confirmation), and `Alert found` never delayed. Any alert-side prompt must not delay or suppress the alert.
3. **Strict agreement** (`MIN_AGREEING_OCR_PASSES = 2`), near-neighbour abstention (distance 2), confusable collision (38/157), corroboration rules and every UNCALIBRATED threshold. No tuning until a human-labelled dev set exists, and never on test data.
4. **The production dataset and its hashes.** Fixtures use real public rows; no synthetic rows in the app's data.
5. **No accuracy claims.** D-014 stays OPEN. The spent reserved photos are never reused for tuning or design choices. AI-read references are never scored as ground truth.
6. **Privacy rules, including at the summit:** no image persistence, no logging of OCR text, localhost only.
7. **`scripts/evaluate.py` metrics** are not reported until made D-026-aware.
8. **Synthetic, composited or fixture images** are never presented, captioned or shared as real photographs of affected medicines.

---

## 10. Owner decisions this assessment surfaces (not to be made by the assistant)
- Rewrite D-014 around categories C1-C5 (replacing 30 NSQ-positive photos).
- An alert-side comparison prompt (F2).
- A conflicting-manufacturer abstention rule (F3).
- Whether corroboration should exclude text outside the detected pack region (F3).
- D-007 preconditions (section 9).
- Ethics and handling rules for physical fixtures and composites.
- Whether to run a consented C5 station at the summit.
- The summit date, which sets how much of the roadmap is feasible.
