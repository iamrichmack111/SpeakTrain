import os
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path


LANGUAGE_CODES = {"spanish": "es", "arabic": "ar"}


def capability_status():
    return {
        "piper": bool(shutil.which("piper")) and bool(os.getenv("PIPER_MODEL_ES") or os.getenv("PIPER_MODEL_AR")),
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "whisper": _whisper_available(),
    }


def _whisper_available():
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


@lru_cache(maxsize=1)
def _model():
    from faster_whisper import WhisperModel
    model_name = os.getenv("WHISPER_MODEL", "base")
    return WhisperModel(model_name, device="cpu", compute_type="int8")


def transcribe(upload, language, expected_text=None):
    if not _whisper_available():
        raise RuntimeError("faster-whisper is not installed")
    suffix = Path(upload.filename or "recording.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        upload.save(handle.name)
        source = handle.name
    try:
        segments, _info = _model().transcribe(
            source,
            language=LANGUAGE_CODES.get(language),
            beam_size=5,
            initial_prompt=expected_text or None,
            condition_on_previous_text=False,
            vad_filter=True,
        )
        captured = list(segments)
        text = " ".join(segment.text.strip() for segment in captured).strip()
        speech_seconds = sum(max(0.0, segment.end - segment.start) for segment in captured)
        return {"text": text, "speech_seconds": round(speech_seconds, 3)}
    finally:
        Path(source).unlink(missing_ok=True)


def generate_piper_audio(text, language, destination):
    model_env = "PIPER_MODEL_ES" if language == "spanish" else "PIPER_MODEL_AR"
    model = os.getenv(model_env)
    if not shutil.which("piper") or not model:
        return False
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["piper", "--model", model, "--output_file", str(destination)],
        input=text,
        text=True,
        capture_output=True,
        timeout=45,
        check=False,
    )
    return result.returncode == 0 and destination.exists()
