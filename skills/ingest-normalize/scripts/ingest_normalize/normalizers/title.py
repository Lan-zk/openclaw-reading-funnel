"""Title normalization helpers."""

from __future__ import annotations

import re


WHITESPACE_RE = re.compile(r"\s+")


def normalize_title(title: str | None) -> str | None:
    if title is None:
        return None
    text = title.replace("\u3000", " ").strip()
    if not text:
        return None
    return WHITESPACE_RE.sub(" ", text)
