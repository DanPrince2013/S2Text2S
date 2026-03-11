"""Tests for text_to_speech module — character detection logic."""

import pytest

from s2text2s.text_to_speech import (
    NARRATOR,
    _Segment,
    _profile_for_character,
    parse_segments,
)


# ── Script-format detection ───────────────────────────────────────────────────

class TestScriptFormatParsing:
    def test_simple_script(self):
        text = "ALICE: Hello there.\nBOB: Hi Alice."
        segments = parse_segments(text)
        assert len(segments) == 2
        assert segments[0].character == "alice"
        assert "Hello" in segments[0].text
        assert segments[1].character == "bob"

    def test_script_with_stage_direction(self):
        text = "ALICE (whispering): Come here.\nBOB: What?"
        segments = parse_segments(text)
        assert segments[0].character == "alice"
        assert segments[1].character == "bob"

    def test_script_with_narrator_line(self):
        text = "The lights dim.\nALICE: It's dark in here."
        segments = parse_segments(text)
        chars = [s.character for s in segments]
        assert NARRATOR in chars
        assert "alice" in chars

    def test_multiword_character_name(self):
        text = "THE WIZARD: Your destiny awaits.\nYOUNG HERO: I'm ready."
        segments = parse_segments(text)
        assert segments[0].character == "the wizard"
        assert segments[1].character == "young hero"


# ── Novel-format detection ────────────────────────────────────────────────────

class TestNovelFormatParsing:
    def test_novel_format_a(self):
        text = '"Hello there," said Alice.'
        segments = parse_segments(text)
        assert any(s.character == "alice" for s in segments)
        assert any("Hello" in s.text for s in segments)

    def test_novel_format_b(self):
        text = 'Bob replied "I understand completely."'
        segments = parse_segments(text)
        assert any(s.character == "bob" for s in segments)

    def test_multiple_characters(self):
        text = (
            '"Where are you going?" asked Alice. '
            'Bob answered "To the market."'
        )
        segments = parse_segments(text)
        chars = {s.character for s in segments}
        assert "alice" in chars
        assert "bob" in chars

    def test_narrator_between_dialogue(self):
        text = (
            'The door opened. '
            '"Come in," said Alice. '
            'The room was cold. '
            'Bob muttered "It\'s freezing in here."'
        )
        segments = parse_segments(text)
        chars = [s.character for s in segments]
        assert NARRATOR in chars
        assert "alice" in chars
        assert "bob" in chars

    def test_narrator_text_only(self):
        text = "The sun rose slowly over the hills."
        segments = parse_segments(text)
        assert len(segments) == 1
        assert segments[0].character == NARRATOR

    def test_various_speech_verbs(self):
        verbs = ["asked", "replied", "whispered", "shouted", "exclaimed", "muttered"]
        for verb in verbs:
            text = f'"Hello," {verb} Alice.'
            segments = parse_segments(text)
            assert any(s.character == "alice" for s in segments), \
                f"Failed for verb: {verb}"

    def test_empty_text(self):
        segments = parse_segments("")
        assert segments == []

    def test_no_empty_segments(self):
        text = '"Hi," said Alice.'
        segments = parse_segments(text)
        assert all(s.text.strip() for s in segments)


# ── Voice profile assignment ──────────────────────────────────────────────────

class TestVoiceProfileAssignment:
    def test_same_name_same_profile(self):
        p1 = _profile_for_character("alice", 3)
        p2 = _profile_for_character("alice", 3)
        assert p1.rate_offset == p2.rate_offset
        assert p1.volume == p2.volume

    def test_different_names_different_profiles(self):
        # It's highly unlikely two different names hash to identical profiles
        profiles = [
            _profile_for_character(name, 4)
            for name in ["alice", "bob", "charlie", "diana"]
        ]
        rate_offsets = [p.rate_offset for p in profiles]
        # At least two should differ
        assert len(set(rate_offsets)) > 1

    def test_rate_offset_in_range(self):
        for name in ["alice", "bob", "charlie", "dave", "eve"]:
            p = _profile_for_character(name, 3)
            assert -50 <= p.rate_offset <= 50

    def test_volume_in_range(self):
        for name in ["alice", "bob", "charlie", "dave", "eve"]:
            p = _profile_for_character(name, 3)
            assert 0.0 <= p.volume <= 1.0

    def test_user_override(self):
        from s2text2s.text_to_speech import VoiceProfile

        override = {"alice": VoiceProfile(rate_offset=99, volume=0.5, voice_index=2)}
        p = _profile_for_character("alice", 3, user_profiles=override)
        assert p.rate_offset == 99
        assert p.volume == 0.5

    def test_voice_index_in_range(self):
        for n_voices in [1, 2, 5, 10]:
            p = _profile_for_character("alice", n_voices)
            assert 0 <= p.voice_index < n_voices

    def test_zero_voices_no_error(self):
        p = _profile_for_character("alice", 0)
        assert p.voice_index == 0
