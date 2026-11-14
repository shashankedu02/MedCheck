"""Generate the SYNTHETIC test-fixture set used for the reproducible demonstration (rendered text, NOT photographs).

    python scripts/make_demo_images.py [output_dir]      # default: demo_images/  (git-ignored)

Every image carries a red in-frame banner "TEST FIXTURE - SYNTHETIC - NOT A REAL MEDICINE" at the top and bottom, so any
photo, print-out or screenshot of it stays labelled as test material. A manifest (fixtures_manifest.csv) is written next to
the images. Labels reuse PUBLIC values from the August 2026 CDSCO NSQ list so each outcome, including the NSQ-alert path,
can be shown without any affected medicine. Fixture results are never real-world evidence and are reported separately
(scripts/run_fixture_check.py); they say nothing about accuracy on real packs. The images can be printed and photographed
for a live demo; the banner must stay visible.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

FONTS = [r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/Library/Fonts/Arial.ttf"]
BOLD_FONTS = [r"C:\Windows\Fonts\arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/Library/Fonts/Arial Bold.ttf"]
BANNER = "TEST FIXTURE - SYNTHETIC - NOT A REAL MEDICINE"
FIXTURE_KIND = "SYNTHETIC_FIXTURE"

# filename -> (label lines, expected headline, listed serial expected to match (or None), why)
DEMO_SET: dict[str, tuple[list[str], str, int | None, str]] = {
    "FIXTURE_1_alert_found.png": (
        ["Linzotal 600", "Linezolid Tablets IP 600 mg", "B.No.: TG261185    Mfg: 05/2026", "Exp: 04/2028"],
        "Alert found", 4, "listed batch (serial 4) + matching product; the alert shows what to check on the pack"),
    "FIXTURE_2_alert_found_trailing_comma.png": (
        ["Telmisartan & Amlodipine Tablets IP", "B.No.: GTF2327C    Mfg: 10/2025", "Exp: 09/2027"],
        "Alert found", 150, "serial 150 (published batch ends with a comma; punctuation ignored)"),
    "FIXTURE_3_no_alert_after_confirmation.png": (
        ["Paracetamol Tablets IP 500 mg", "B.No.: ZX99001Q    Mfg: 01/2026", "Exp: 12/2028"],
        "Unable to verify", None,
        "batch not in the August 2026 list: 'No alert found' appears only after you confirm the batch against the pack"),
    "FIXTURE_4_unable_batch_alone.png": (
        ["Paracetamol Tablets IP 500 mg", "B.No.: TG261185    Mfg: 05/2026", "Exp: 04/2028"],
        "Unable to verify", None, "listed batch but the product does not match: batch alone never alerts"),
    "FIXTURE_5_unable_collision.png": (
        ["Bupivacaine Hydrochloride In Dextrose Injection USP", "B.No.: BKBP02601", "Mfg: 05/2026    Exp: 04/2028"],
        "Unable to verify", None, "serials 38 and 157 differ only by 0 vs O: cannot be told apart"),
    "FIXTURE_6_unable_no_batch.png": (
        ["Paracetamol Tablets IP 500 mg", "Store below 25 C", "Exp: 12/2028"],
        "Unable to verify", None, "no batch number could be read"),
    "FIXTURE_7_alert_listed_neighbour.png": (
        ["Paracetamol Tablets IP 500 mg", "B.No.: PAK-637    Mfg: 03/2025", "Exp: 02/2028"],
        "Alert found", 113,
        "serial 113; listed serial 118 (PAK-636) is one character away, so the alert warns that a single misread "
        "character could produce this match and asks for a character-by-character check"),
}


def _font(candidates: list[str], size: int):
    fp = next((p for p in candidates if Path(p).exists()), None)
    return ImageFont.truetype(fp, size) if fp else ImageFont.load_default()


def _render(lines: list[str]) -> Image.Image:
    font, bold = _font(FONTS, 46), _font(BOLD_FONTS or FONTS, 40)
    band = 70
    height = max(340, 40 + len(lines) * 76) + 2 * band + 40
    img = Image.new("RGB", (1300, height), "white")
    d = ImageDraw.Draw(img)
    for top in (20, height - band - 20):  # red banner inside the frame, top and bottom (not touching the edge)
        d.rectangle((20, top, 1280, top + band), fill=(200, 0, 0))
        d.text((40, top + 14), BANNER, font=bold, fill="white")
    y0 = 20 + band + 30
    for i, line in enumerate(lines):
        d.text((40, y0 + i * 76), line, font=font, fill="black")
    return img


def build(out_dir: Path) -> dict[str, tuple[str, str]]:
    """Render every fixture and write the manifest. Returns {filename: (expected headline, why)}."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "fixtures_manifest.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "kind", "expected_headline", "expected_listed_serial", "purpose"])
        for name, (lines, headline, serial, why) in DEMO_SET.items():
            _render(lines).save(out_dir / name, "PNG")
            w.writerow([name, FIXTURE_KIND, headline, serial if serial is not None else "", why])
    return {n: (h, why) for n, (_, h, _s, why) in DEMO_SET.items()}


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("demo_images")
    for name, (headline, why) in build(target).items():
        print(f"{target / name}: expect '{headline}' ({why})")
    print(f"manifest: {target / 'fixtures_manifest.csv'}  (all images are {FIXTURE_KIND}: test material, not photographs)")
