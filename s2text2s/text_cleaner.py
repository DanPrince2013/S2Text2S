"""
Text cleanup for speech-to-text output.

Handles:
- Filler-word removal (um, uh, you know …)
- Verbal punctuation («period», «comma», «new line» …)
- Capitalisation of sentence starts
- Repeated-word de-duplication
- Trailing punctuation normalisation
"""

import re
from typing import List

# ── Verbal punctuation ────────────────────────────────────────────────────────

_VERBAL_PUNCTUATION: List[tuple] = [
    # phrase                      replacement
    (r"\bnew paragraph\b",        "\n\n"),
    (r"\bnew line\b",             "\n"),
    (r"\bopen quote\b\s*",         '"'),
    (r"\s*\bclose quote\b",       '"'),
    (r"\bopen parenthes[ei]s\b",  "("),
    (r"\bclose parenthes[ei]s\b", ")"),
    (r"\bexclamation (?:point|mark)\b", "!"),
    (r"\bquestion mark\b",        "?"),
    (r"\bsemicolon\b",            ";"),
    (r"\bcolon\b",                ":"),
    (r"\bellipsis\b",             "..."),
    (r"\bdash\b",                 " — "),
    (r"\bhyphen\b",               "-"),
    (r"\bcomma\b",                ","),
    (r"\bperiod\b",               "."),
    (r"\bfull stop\b",            "."),
]

_VERBAL_PUNCT_COMPILED = [
    (re.compile(pat, re.IGNORECASE), repl)
    for pat, repl in _VERBAL_PUNCTUATION
]

# ── Default filler words ──────────────────────────────────────────────────────

_DEFAULT_FILLERS: List[str] = [
    "um", "uh", "you know", "like", "basically", "literally",
    "actually", "so like", "i mean",
]


def _build_filler_pattern(fillers: List[str]) -> re.Pattern:
    escaped = [re.escape(f) for f in sorted(fillers, key=len, reverse=True)]
    return re.compile(
        r"(?<!\w)(?:" + "|".join(escaped) + r")(?!\w),?\s*",
        re.IGNORECASE,
    )


def _apply_verbal_punctuation(text: str) -> str:
    for pattern, replacement in _VERBAL_PUNCT_COMPILED:
        # Remove any leading space before the punctuation mark
        text = pattern.sub(replacement, text)
    # Tidy up space before punctuation that was already in the string
    text = re.sub(r" +([.,!?;:])", r"\1", text)
    return text


def _remove_fillers(text: str, fillers: List[str]) -> str:
    if not fillers:
        return text
    pat = _build_filler_pattern(fillers)
    return pat.sub(" ", text)


def _deduplicate_words(text: str) -> str:
    """Remove immediately repeated words: 'the the cat' → 'the cat'."""
    return re.sub(r"\b(\w+)(\s+\1)+\b", r"\1", text, flags=re.IGNORECASE)


def _capitalise_sentences(text: str) -> str:
    """Capitalise the first letter of each sentence."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    result = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence:
            result.append(sentence[0].upper() + sentence[1:])
    return " ".join(result)


def _ensure_terminal_punctuation(text: str) -> str:
    """Add a period at the end if there is no terminal punctuation."""
    text = text.rstrip()
    if text and text[-1] not in ".!?":
        text += "."
    return text


def _collapse_whitespace(text: str) -> str:
    # Preserve deliberate newlines but collapse multiple spaces
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_transcript(
    text: str,
    fillers: List[str] | None = None,
    remove_fillers: bool = True,
) -> str:
    """
    Full pipeline: verbal punctuation → filler removal → dedup → capitalise →
    terminal punctuation → whitespace collapse.

    Parameters
    ----------
    text:
        Raw transcript from the STT engine.
    fillers:
        Override the default filler-word list.
    remove_fillers:
        Set to ``False`` to skip filler removal.
    """
    if not text:
        return ""

    text = _apply_verbal_punctuation(text)

    if remove_fillers:
        word_list = fillers if fillers is not None else _DEFAULT_FILLERS
        text = _remove_fillers(text, word_list)

    text = _deduplicate_words(text)
    text = _capitalise_sentences(text)
    text = _ensure_terminal_punctuation(text)
    text = _collapse_whitespace(text)

    return text
