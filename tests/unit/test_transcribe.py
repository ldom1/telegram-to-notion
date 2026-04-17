"""Tests for ``telegram_to_notion.transcribe``."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from telegram_to_notion.transcribe import transcribe_file


def test_transcribe_file_missing_path(tmp_path: Path) -> None:
    assert transcribe_file(tmp_path / "nope.ogg") is None


@patch("telegram_to_notion.transcribe.WhisperModel")
def test_transcribe_file_success(mock_model_cls: MagicMock, tmp_path: Path) -> None:
    wav = tmp_path / "x.wav"
    wav.write_bytes(b"RIFF")

    seg = MagicMock()
    seg.text = " salut "
    info = MagicMock(duration=2.5)
    instance = MagicMock()
    instance.transcribe.return_value = ([seg], info)
    mock_model_cls.return_value = instance

    out = transcribe_file(wav, language="fr", model_size="tiny")
    assert out == "salut"
    mock_model_cls.assert_called_once_with("tiny", device="cpu", compute_type="int8")
