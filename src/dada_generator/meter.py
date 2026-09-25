import re

FEET = {"iambic": "01", "trochaic": "10", "anapestic": "001", "dactylic": "100"}

_STRESS_RE = re.compile(r"[01x]+")
_SHORTHAND_RE = re.compile(r"([a-z]+)\s+(\d+)")


def parse_template(text: str) -> str:
    """Turn a stress string ("x101") or foot shorthand ("iambic 4") into a stress string."""
    spec = text.strip().lower()
    if _STRESS_RE.fullmatch(spec):
        return spec
    match = _SHORTHAND_RE.fullmatch(spec)
    if match:
        foot, count = match.group(1), int(match.group(2))
        if foot not in FEET:
            raise ValueError(f"unknown foot '{foot}' (expected one of: {', '.join(FEET)})")
        if count < 1:
            raise ValueError("foot count must be at least 1")
        return FEET[foot] * count
    raise ValueError(f"invalid meter '{text}': use a stress string of 0/1/x or '<foot> <count>'")


def mismatch(template: str, stress: str) -> int:
    """Count positions where both sides are definite (0/1) and disagree."""
    return sum(
        1
        for want, have in zip(template, stress, strict=True)
        if want in "01" and have in "01" and want != have
    )
