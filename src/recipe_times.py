"""Recipe time conversion between Mealie's two time formats.

Mealie v3.29+ stores each recipe time as a duration in seconds (`prepTimeSeconds`,
`performTimeSeconds`, `totalTimeSeconds`). The legacy text fields (`prepTime`, ...) are
kept only for values that aren't a duration, like "overnight". Its upgrade migration
moved every parseable text time into the seconds field and blanked the text.

Reading: `add_readable_times` fills each text field from its seconds field, so callers
always read one human-readable value per time ("1 hour 30 minutes") whichever format
Mealie stored it in.

Writing: `parse_duration` turns text into seconds using the same rule as the migration —
the WHOLE value must be a duration — except that a bare number ("45") is rejected rather
than assumed to be minutes, because it's ambiguous ("3" meaning hours was read as minutes).
"""

import re
from typing import Any, Dict, Optional

TIME_FIELDS = ("prepTime", "performTime", "totalTime")

# Largest first; a value's components must appear in this order, each at most once.
UNIT_SECONDS = {"day": 86400, "hour": 3600, "minute": 60, "second": 1}

UNIT_WORDS = {
    "d": "day", "day": "day", "days": "day",
    "h": "hour", "hr": "hour", "hrs": "hour", "hour": "hour", "hours": "hour",
    "m": "minute", "min": "minute", "mins": "minute", "minute": "minute", "minutes": "minute",
    "s": "second", "sec": "second", "secs": "second", "second": "second", "seconds": "second",
}

_NUMBER = r"\d+(?:\.\d+)?"
_UNIT = "|".join(sorted(UNIT_WORDS, key=len, reverse=True))  # longest first: "minutes" before "m"
# The unit must end at a space, a digit ("1h30m") or the end of the value.
_COMPONENT = re.compile(rf"\s*({_NUMBER})\s*({_UNIT})(?=\s|\d|$)")
_ISO = re.compile(rf"P(?:({_NUMBER})D)?(?:T(?:({_NUMBER})H)?(?:({_NUMBER})M)?(?:({_NUMBER})S)?)?")


class BareNumberError(ValueError):
    """A time given as a number with no unit, e.g. "45"."""


def parse_duration(value: Optional[str]) -> Optional[int]:
    """Seconds for a duration string, or None if the value isn't (entirely) a duration.

    Accepts unit words and abbreviations ("1 hour 30 minutes", "90 min", "1.5 hrs") and
    ISO 8601 ("PT1H30M"). Returns 0 for a zero duration ("0 minutes"), which callers treat
    as no time. Raises BareNumberError for a number with no unit.
    """
    if value is None or not (text := value.strip()):
        return None
    if re.fullmatch(_NUMBER, text):
        raise BareNumberError(
            f'time "{value}" has no unit — use e.g. "{text} minutes" or "{text} hours"'
        )

    iso = _ISO.fullmatch(text.upper())
    if iso and any(iso.groups()):
        units = ("day", "hour", "minute", "second")
        return _to_seconds(sum(float(n) * UNIT_SECONDS[u] for n, u in zip(iso.groups(), units) if n))

    # Allow "1 hour and 30 minutes" / "1 hour, 30 minutes"
    text = re.sub(r"\s*(,|\band\b)\s*", " ", text.lower())
    total = 0.0
    seen: list[str] = []
    pos = 0
    order = list(UNIT_SECONDS)
    while pos < len(text):
        m = _COMPONENT.match(text, pos)
        if not m:
            return None
        unit = UNIT_WORDS[m.group(2)]
        if seen and order.index(unit) <= order.index(seen[-1]):
            return None
        seen.append(unit)
        total += float(m.group(1)) * UNIT_SECONDS[unit]
        pos = m.end()
        if not text[pos:].strip():
            break
    return _to_seconds(total) if seen else None


def _to_seconds(total: float) -> Optional[int]:
    # A fractional second (e.g. "0.5 seconds") isn't a meaningful recipe duration.
    return int(total) if total == int(total) else None


def format_duration(seconds: int) -> str:
    """Readable English duration: 5400 -> "1 hour 30 minutes"."""
    parts = []
    for unit, size in UNIT_SECONDS.items():
        n, seconds = divmod(seconds, size)
        if n:
            parts.append(f"{n} {unit}{'' if n == 1 else 's'}")
    return " ".join(parts)


def add_readable_times(recipe: Dict[str, Any]) -> Dict[str, Any]:
    """Fill prepTime/performTime/totalTime with readable text from the seconds fields.

    A text-only value (e.g. "overnight") is left as Mealie stored it. Modifies and
    returns the dict; the seconds fields are left in place.
    """
    if not isinstance(recipe, dict):
        return recipe
    for field in TIME_FIELDS:
        seconds = recipe.get(f"{field}Seconds")
        if seconds:
            recipe[field] = format_duration(int(seconds))
    return recipe
