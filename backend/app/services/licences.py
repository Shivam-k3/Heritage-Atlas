"""Licence normalisation for dataset acquisition. Reuse rules live in docs/DATASET.md."""

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_ALLOWED_RE = re.compile(
    r"^(cc0|cc[- ]by(?:[- ]sa)?(?:[- ]\d+(?:\.\d+)?)?|public domain|pd(?:\b|-)|no restrictions?)\b",
    re.IGNORECASE,
)


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = html.unescape(_TAG_RE.sub(" ", value))
    return _SPACE_RE.sub(" ", text).strip()


def normalise_licence(raw: str | None) -> str:
    text = clean_text(raw)
    if not text:
        return ""
    match = re.match(r"(cc[- ]by[- ]sa[- ]\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if match:
        return match.group(1).replace("-", " ").upper().replace("CC BY SA", "CC BY-SA")
    match = re.match(r"(cc[- ]by[- ]\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if match:
        return match.group(1).replace("-", " ").upper().replace("CC BY ", "CC BY ")
    match = re.match(r"(cc0[- ]?\d*(?:\.\d+)?)", text, re.IGNORECASE)
    if match:
        return "CC0"
    if re.search(r"public domain|\bPD\b", text, re.IGNORECASE):
        return "Public domain"
    return text


def is_reusable(licence: str) -> bool:
    value = normalise_licence(licence)
    if not value or re.search(r"non[- ]free|fair use|copyright", value, re.IGNORECASE):
        return False
    return bool(_ALLOWED_RE.match(value))
