"""Generate a small SYNTHETIC demo set (rendered text, not real photographs).

    python scripts/make_demo_images.py [output_dir]      # default: demo_images/

The labels reuse public values from the August 2026 dataset so each outcome can be demonstrated.
They show how the software behaves; they say nothing about accuracy on real packs.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

FONTS = [r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/Library/Fonts/Arial.ttf"]

# filename -> (label lines, expected headline, why)
DEMO_SET: dict[str, tuple[list[str], str, str]] = {
    "1_alert_found.png": (
        ["Linzotal 600", "Linezolid Tablets IP 600 mg", "B.No.: TG261185    Mfg: 05/2026", "Exp: 04/2028"],
        "Alert found", "listed batch (serial 4) + matching product"),
    "2_alert_found_trailing_comma.png": (
        ["Telmisartan & Amlodipine Tablets IP", "B.No.: GTF2327C    Mfg: 10/2025", "Exp: 09/2027"],
        "Alert found", "serial 150 (published batch ends with a comma; punctuation ignored)"),
    "3_no_alert_found.png": (
        ["Paracetamol Tablets IP 500 mg", "B.No.: ZX99001Q    Mfg: 01/2026", "Exp: 12/2028"],
        "No alert found", "batch is not in the August 2026 list"),
    "4_unable_batch_alone.png": (
        ["Paracetamol Tablets IP 500 mg", "B.No.: TG261185    Mfg: 05/2026", "Exp: 04/2028"],
        "Unable to verify", "listed batch but the product does not match: batch alone never alerts"),
    "5_unable_collision.png": (
        ["Bupivacaine Hydrochloride In Dextrose Injection USP", "B.No.: BKBP02601", "Mfg: 05/2026    Exp: 04/2028"],
        "Unable to verify", "serials 38 and 157 differ only by 0 vs O: cannot be told apart"),
    "6_unable_no_batch.png": (
        ["Paracetamol Tablets IP 500 mg", "Store below 25 C", "Exp: 12/2028"],
        "Unable to verify", "no batch number could be read"),
}


def _render(lines: list[str]) -> Image.Image:
    fp = next((p for p in FONTS if Path(p).exists()), None)
    font = ImageFont.truetype(fp, 46) if fp else ImageFont.load_default()
    img = Image.new("RGB", (1300, max(340, 40 + len(lines) * 76)), "white")
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        d.text((30, 25 + i * 76), line, font=font, fill="black")
    return img


def build(out_dir: Path) -> dict[str, tuple[str, str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, (lines, _, _) in DEMO_SET.items():
        _render(lines).save(out_dir / name, "PNG")
    return {n: (h, why) for n, (_, h, why) in DEMO_SET.items()}


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("demo_images")
    for name, (headline, why) in build(target).items():
        print(f"{target / name}: expect '{headline}' ({why})")
