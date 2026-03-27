"""Language normalization helpers."""

from __future__ import annotations


def fill_language(
    explicit_language: str | None,
    default_language: str | None = None,
    title: str | None = None,
    summary: str | None = None,
) -> str | None:
    if explicit_language:
        return explicit_language.lower()
    if default_language:
        return default_language.lower()
    probe = f"{title or ''} {summary or ''}".strip()
    if not probe:
        return None
    if any("\u4e00" <= char <= "\u9fff" for char in probe):
        return "zh"
    if any(char.isalpha() for char in probe):
        return "en"
    return None
