"""Tests for text_cleaner module."""

import pytest

from s2text2s.text_cleaner import (
    _apply_verbal_punctuation,
    _capitalise_sentences,
    _deduplicate_words,
    _ensure_terminal_punctuation,
    _remove_fillers,
    clean_transcript,
)


# ── Verbal punctuation ────────────────────────────────────────────────────────

class TestVerbalPunctuation:
    def test_period(self):
        assert _apply_verbal_punctuation("hello period world") == "hello. world"

    def test_comma(self):
        assert _apply_verbal_punctuation("one comma two") == "one, two"

    def test_question_mark(self):
        result = _apply_verbal_punctuation("is this right question mark")
        assert "?" in result

    def test_exclamation_point(self):
        result = _apply_verbal_punctuation("wow exclamation point")
        assert "!" in result

    def test_new_line(self):
        result = _apply_verbal_punctuation("first new line second")
        assert "\n" in result

    def test_new_paragraph(self):
        result = _apply_verbal_punctuation("para one new paragraph para two")
        assert "\n\n" in result

    def test_open_close_quote(self):
        result = _apply_verbal_punctuation('open quote hello close quote')
        assert '"hello"' in result

    def test_no_space_before_punctuation(self):
        # Existing punctuation in the string should not gain an extra space
        text = "hello , world"
        result = _apply_verbal_punctuation(text)
        assert " ," not in result

    def test_multiple_verbal_punctuation(self):
        text = "hello comma world period"
        result = _apply_verbal_punctuation(text)
        assert result == "hello, world."

    def test_case_insensitive(self):
        assert "." in _apply_verbal_punctuation("done Period")
        assert "." in _apply_verbal_punctuation("done PERIOD")


# ── Filler removal ────────────────────────────────────────────────────────────

class TestFillerRemoval:
    FILLERS = ["um", "uh", "you know", "like", "basically"]

    def test_removes_um(self):
        result = _remove_fillers("um I think so", self.FILLERS)
        assert "um" not in result.lower()

    def test_removes_uh(self):
        result = _remove_fillers("uh that's correct", self.FILLERS)
        assert result.strip().lower().startswith("that")

    def test_removes_multi_word_filler(self):
        result = _remove_fillers("you know what I mean", self.FILLERS)
        assert "you know" not in result.lower()

    def test_preserves_content_words(self):
        result = _remove_fillers("the cat sat on the mat", self.FILLERS)
        assert "cat" in result and "mat" in result

    def test_filler_at_end(self):
        result = _remove_fillers("I agree um", self.FILLERS)
        assert result.strip().lower() in ("i agree", "i agree.")

    def test_multiple_fillers(self):
        result = _remove_fillers("um uh I basically like think so", self.FILLERS)
        assert "um" not in result.lower()
        assert "uh" not in result.lower()
        assert "basically" not in result.lower()
        assert "think so" in result.lower()

    def test_word_boundary(self):
        # "umbrella" must NOT be stripped even though it starts with "um"
        result = _remove_fillers("I have an umbrella", self.FILLERS)
        assert "umbrella" in result


# ── Deduplication ─────────────────────────────────────────────────────────────

class TestDeduplication:
    def test_double_word(self):
        result = _deduplicate_words("the the cat sat")
        assert "the the" not in result
        assert "the cat" in result

    def test_triple_word(self):
        result = _deduplicate_words("very very very good")
        assert "very very" not in result
        assert "good" in result

    def test_no_dup(self):
        text = "the quick brown fox"
        assert _deduplicate_words(text) == text

    def test_case_insensitive_dup(self):
        result = _deduplicate_words("The the cat")
        assert result.lower().count("the") == 1


# ── Capitalisation ────────────────────────────────────────────────────────────

class TestCapitalisation:
    def test_capitalises_first_word(self):
        result = _capitalise_sentences("hello world.")
        assert result[0].isupper()

    def test_capitalises_after_period(self):
        result = _capitalise_sentences("first sentence. second sentence.")
        assert "Second" in result

    def test_capitalises_after_exclamation(self):
        result = _capitalise_sentences("wow! that is great.")
        assert "That" in result

    def test_capitalises_after_question(self):
        result = _capitalise_sentences("are you sure? yes i am.")
        assert "Yes" in result


# ── Terminal punctuation ──────────────────────────────────────────────────────

class TestTerminalPunctuation:
    def test_adds_period_when_missing(self):
        result = _ensure_terminal_punctuation("hello world")
        assert result.endswith(".")

    def test_preserves_period(self):
        result = _ensure_terminal_punctuation("hello world.")
        assert result.endswith(".")
        assert result.count(".") == 1

    def test_preserves_question_mark(self):
        result = _ensure_terminal_punctuation("are you sure?")
        assert result.endswith("?")

    def test_preserves_exclamation(self):
        result = _ensure_terminal_punctuation("great!")
        assert result.endswith("!")


# ── Full pipeline ─────────────────────────────────────────────────────────────

class TestCleanTranscript:
    def test_empty_string(self):
        assert clean_transcript("") == ""

    def test_basic_cleanup(self):
        result = clean_transcript("um hello world period")
        assert "um" not in result.lower()
        assert result[0].isupper()
        assert "." in result

    def test_full_sentence(self):
        raw = "um i wanted to say hello comma how are you question mark"
        result = clean_transcript(raw)
        assert "," in result
        assert "?" in result
        assert "um" not in result.lower()
        assert result[0].isupper()

    def test_verbal_punctuation_and_fillers(self):
        raw = "basically uh the answer is yes period"
        result = clean_transcript(raw)
        assert "basically" not in result.lower()
        assert "uh" not in result.lower()
        assert result.endswith(".")
        assert "yes" in result.lower()

    def test_no_filler_removal_flag(self):
        raw = "um hello world"
        result = clean_transcript(raw, remove_fillers=False)
        assert "um" in result.lower()

    def test_custom_fillers(self):
        raw = "blah blah hello world"
        result = clean_transcript(raw, fillers=["blah"], remove_fillers=True)
        assert "blah" not in result.lower()

    def test_preserves_newlines_from_new_line(self):
        raw = "first new line second"
        result = clean_transcript(raw)
        assert "\n" in result

    def test_dedup_applied(self):
        result = clean_transcript("the the cat sat")
        assert result.lower().count("the") == 1
