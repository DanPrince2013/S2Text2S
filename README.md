# S2Text2S

> **Speak → Text → Speak** — a Windows productivity tool that lets you dictate
> into any text field and read highlighted text aloud, with special character-voice
> detection for AI-generated scripts and stories.

---

## Features

| Feature | Hotkey | Description |
|---|---|---|
| **Dictate (Speech → Text)** | Hold **Right Ctrl** | Speak while holding the key; release to transcribe, clean up and paste the text at your cursor |
| **Read aloud (Text → Speech)** | Tap **Right Alt** | Reads whatever text you have highlighted, using SAPI5 voices |
| **Stop reading** | **Escape** | Stops any ongoing text-to-speech |

### Speech-to-text pipeline
1. Raw transcript from Google / Azure / offline (CMU Sphinx)
2. Verbal punctuation conversion: say *"comma"*, *"period"*, *"question mark"*, *"new line"*, etc.
3. Filler-word removal: *um*, *uh*, *you know*, *like*, …
4. Repeated-word de-duplication
5. Sentence capitalisation
6. Paste into the focused text field via the system clipboard

### Text-to-speech with character voices
When reading text aloud the engine automatically detects dialogue and switches
voice profiles for each character:

- **Script format** — `CHARACTER_NAME: dialogue`
- **Novel format A** — `"dialogue," said Character`
- **Novel format B** — `Character replied "dialogue"`

Each character consistently receives a unique rate/volume/voice combination
derived from their name.  When multiple SAPI5 voices are installed they are
cycled across characters.

---

## Requirements

- Windows 10 or later (SAPI5 is required for multi-voice TTS)
- Python 3.10 or later
- Internet connection for Google Speech Recognition (default)  
  *— or use Azure / offline Sphinx (see Configuration)*

---

## Quick start

```bat
REM 1. Install dependencies (once)
setup.bat

REM 2. Run  (must be Administrator for global hotkeys)
run.bat
```

> **Administrator required** — the `keyboard` library needs elevated privileges
> to intercept global hotkeys on modern Windows.

---

## Configuration

Create a file called `s2text2s.cfg` in the same folder as `main.py`.  All
sections and keys are optional; omitted values fall back to the defaults shown.

```ini
[hotkeys]
stt_hotkey = right ctrl     ; hold to record
tts_hotkey = right alt      ; tap to read selection

[stt]
engine     = google          ; google | azure | sphinx
azure_key  =                 ; required for Azure engine
azure_region = eastus

[tts]
rate               = 180     ; words per minute (narrator baseline)
volume             = 0.9     ; 0.0 – 1.0
detect_characters  = true

[cleanup]
remove_fillers = true
; comma-separated list (overrides the built-in list):
; filler_words = um, uh, you know, like

[characters]
; name = rate_offset, volume, voice_index
; e.g. give Alice a faster, quieter voice on voice slot 1:
alice = 20, 0.8, 1
```

---

## Project layout

```
S2Text2S/
├── main.py                  Entry point
├── s2text2s/
│   ├── app.py               Application controller (wires everything together)
│   ├── config.py            Configuration loader
│   ├── audio_recorder.py    Microphone capture (sounddevice)
│   ├── speech_to_text.py    STT wrapper (SpeechRecognition)
│   ├── text_cleaner.py      Transcript cleanup pipeline
│   ├── text_to_speech.py    TTS + character-voice detection (pyttsx3)
│   ├── text_injector.py     Clipboard-based text injection
│   ├── hotkey_manager.py    Global hotkey registration
│   └── notifications.py     Desktop toast notifications
├── tests/
│   ├── test_config.py
│   ├── test_text_cleaner.py
│   └── test_text_to_speech.py
├── requirements.txt
├── setup.bat
└── run.bat
```

---

## Running the tests

```bat
pip install pytest
pytest tests/ -v
```

---

## Supported verbal punctuation commands

Say these words out loud while dictating and they will be converted:

| Say | Inserts |
|---|---|
| *period* / *full stop* | `.` |
| *comma* | `,` |
| *question mark* | `?` |
| *exclamation point* / *exclamation mark* | `!` |
| *new line* | `\n` |
| *new paragraph* | `\n\n` |
| *open quote* | `"` |
| *close quote* | `"` |
| *colon* | `:` |
| *semicolon* | `;` |
| *dash* | ` — ` |
| *hyphen* | `-` |
| *ellipsis* | `...` |
| *open parenthesis* | `(` |
| *close parenthesis* | `)` |
