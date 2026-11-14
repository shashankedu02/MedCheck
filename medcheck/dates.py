"""Month/year parsing and the (currently disabled) expiry verdict.

Supported printed formats (month-year only): MM/YYYY, MM-YYYY, MM.YYYY, MM/YY,
MM-YY, MM.YY, MMM YYYY, MMM-YY, MMMYYYY, and YYYY-MM. Day-level dates and
anything else are reported as unparseable instead of guessed.

Expiry verdict: `Expired` requires an owner-approved interpretation of month-only
dates (docs/EXPIRY_POLICY.md). While `policy_approved` is False the verdict is
always UNDETERMINED.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date

from .models import ExpiryAssessment, ExpiryOutcome

_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_abbr) if m}
_MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_name) if m})
_MONTHS["sept"] = 9  # common printed abbreviation

_NUMERIC = re.compile(r"^(\d{1,2})\s*[/\-. ]\s*(\d{4}|\d{2})$")
_ISO = re.compile(r"^(\d{4})\s*[/\-. ]\s*(\d{1,2})$")
_NAMED = re.compile(r"^([A-Za-z]{3,9})\.?\s*[/\-. ]?\s*(\d{4}|\d{2})$")


@dataclass(frozen=True)
class MonthYear:
    raw: str
    year: int
    month: int

    def __lt__(self, other: "MonthYear") -> bool:
        return (self.year, self.month) < (other.year, other.month)


def _year(token: str) -> int:
    y = int(token)
    return 2000 + y if len(token) == 2 else y


def parse_month_year(raw: str | None) -> MonthYear | None:
    """Return a MonthYear, or None when the text is not an explicitly supported month-year."""
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    month: int | None = None
    year: int | None = None
    if m := _NUMERIC.match(text):
        month, year = int(m.group(1)), _year(m.group(2))
    elif m := _ISO.match(text):
        year, month = int(m.group(1)), int(m.group(2))
    elif m := _NAMED.match(text):
        month, year = _MONTHS.get(m.group(1).lower()), _year(m.group(2))
    if month is None or year is None or not (1 <= month <= 12) or not (1990 <= year <= 2100):
        return None
    return MonthYear(raw=raw, year=year, month=month)


def assess_expiry(
    raw: str | None,
    today: date,
    policy_approved: bool,
) -> ExpiryAssessment:
    """Interpret a printed expiry. Never claims `EXPIRED` unless the policy is approved."""
    if raw is None or not raw.strip():
        return ExpiryAssessment(ExpiryOutcome.NOT_READ, raw, "Expiry date was not read from the image.")
    parsed = parse_month_year(raw)
    if parsed is None:
        return ExpiryAssessment(ExpiryOutcome.UNPARSEABLE, raw, "Printed expiry text is not in a supported month-year format.")
    shown = f"{parsed.month:02d}/{parsed.year}"
    if not policy_approved:
        return ExpiryAssessment(
            ExpiryOutcome.UNDETERMINED,
            raw,
            f"Printed expiry reads {shown}. How month-only expiry dates are interpreted has not been approved, so no expired/valid verdict is given.",
        )
    # Approved interpretation: valid through the last day of the printed month.
    last_day = date(parsed.year, parsed.month, calendar.monthrange(parsed.year, parsed.month)[1])
    if today > last_day:
        return ExpiryAssessment(ExpiryOutcome.EXPIRED, raw, f"Printed expiry {shown} is before today's date ({today.isoformat()}).")
    return ExpiryAssessment(ExpiryOutcome.NOT_EXPIRED, raw, f"Printed expiry {shown} has not passed.")


def manufacture_after_expiry(mfg_raw: str | None, exp_raw: str | None) -> bool:
    """True when both dates parse and expiry precedes manufacture (a source/read anomaly)."""
    mfg, exp = parse_month_year(mfg_raw), parse_month_year(exp_raw)
    return bool(mfg and exp and exp < mfg)
