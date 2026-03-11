"""Tests for config module."""

import configparser
import os
import tempfile

import pytest

from s2text2s.config import Config, CharacterVoiceProfile, load_config


class TestDefaultConfig:
    def test_default_stt_hotkey(self):
        cfg = Config()
        assert cfg.stt_hotkey == "right ctrl"

    def test_default_tts_hotkey(self):
        cfg = Config()
        assert cfg.tts_hotkey == "right alt"

    def test_default_engine(self):
        cfg = Config()
        assert cfg.stt_engine == "google"

    def test_filler_words_not_empty(self):
        cfg = Config()
        assert len(cfg.filler_words) > 0

    def test_remove_fillers_true(self):
        cfg = Config()
        assert cfg.remove_fillers is True


class TestLoadConfig:
    def _write_cfg(self, content: str) -> str:
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".cfg", delete=False, encoding="utf-8"
        )
        f.write(content)
        f.close()
        return f.name

    def test_missing_file_returns_defaults(self):
        cfg = load_config("/nonexistent/path.cfg")
        assert cfg.stt_hotkey == "right ctrl"

    def test_override_hotkeys(self):
        path = self._write_cfg(
            "[hotkeys]\nstt_hotkey = right alt\ntts_hotkey = right ctrl\n"
        )
        try:
            cfg = load_config(path)
            assert cfg.stt_hotkey == "right alt"
            assert cfg.tts_hotkey == "right ctrl"
        finally:
            os.unlink(path)

    def test_override_tts_rate(self):
        path = self._write_cfg("[tts]\nrate = 200\n")
        try:
            cfg = load_config(path)
            assert cfg.tts_rate == 200
        finally:
            os.unlink(path)

    def test_override_stt_engine(self):
        path = self._write_cfg("[stt]\nengine = sphinx\n")
        try:
            cfg = load_config(path)
            assert cfg.stt_engine == "sphinx"
        finally:
            os.unlink(path)

    def test_override_filler_words(self):
        path = self._write_cfg("[cleanup]\nfiller_words = blah, duh, hmm\n")
        try:
            cfg = load_config(path)
            assert "blah" in cfg.filler_words
            assert "duh" in cfg.filler_words
        finally:
            os.unlink(path)

    def test_character_voice_profiles(self):
        path = self._write_cfg("[characters]\nalice = 20, 0.8, 1\n")
        try:
            cfg = load_config(path)
            assert "alice" in cfg.character_voices
            profile = cfg.character_voices["alice"]
            assert profile.rate_offset == 20
            assert profile.volume == pytest.approx(0.8)
            assert profile.voice_index == 1
        finally:
            os.unlink(path)
