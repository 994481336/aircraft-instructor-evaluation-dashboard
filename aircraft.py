from __future__ import annotations

import re


def canonical_model(raw_model: object, family: object = "未识别") -> str:
    """Create a model-level grouping while keeping the source model untouched."""
    raw = str(raw_model).strip()
    family_text = str(family).strip()
    compact = re.sub(r"[\s_\-－—]+", "", raw.upper())
    if compact in {"", "NAN", "NONE", "<NA>", "未识别机型", "空客", "波音", "国产民机", "AIRBUS", "BOEING", "ARJ"}:
        return f"{family_text}（机型未明确）"

    compact = re.sub(r"^(?:波音|BOEING|空客|AIRBUS)", "", compact)
    # B738 is a common export abbreviation for the B737-800.
    if compact in {"B738", "738"} and (family_text == "波音" or compact.startswith("B")):
        return "B737"
    match = re.fullmatch(r"B?(737|747|757|767|777|787)[A-Z\d]*", compact)
    if match and (family_text == "波音" or compact.startswith("B")):
        return f"B{match.group(1)}"
    match = re.fullmatch(r"A?(318|319|320|321|330|340|350|380)[A-Z\d]*", compact)
    if match and (family_text == "空客" or compact.startswith("A")):
        return f"A{match.group(1)}"
    match = re.fullmatch(r"C(909|919)[A-Z\d]*", compact)
    if match:
        return f"C{match.group(1)}"
    if compact == "ARJ21":
        return "ARJ21"
    # An unfamiliar source value remains visible rather than being guessed.
    return raw
