import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi


PREFERRED_LANGUAGES = ["en", "ur", "hi", "ar"]


def _clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = text.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    return re.sub(r"\s+", " ", text).strip()


def _normalize_segments(items):
    result = []
    for item in items or []:
        if isinstance(item, dict):
            text = item.get("text", "")
            start = item.get("start", 0)
            duration = item.get("duration", 0)
        else:
            text = getattr(item, "text", "")
            start = getattr(item, "start", 0)
            duration = getattr(item, "duration", 0)

        text = _clean_text(str(text))
        if not text:
            continue
        try:
            start = float(start or 0)
            duration = float(duration or 0)
        except (TypeError, ValueError):
            start, duration = 0.0, 0.0

        result.append({
            "start": start,
            "end": start + max(duration, 0.0),
            "text": text,
        })

    if not result:
        raise RuntimeError("The transcript is empty.")
    return result


def _parse_timestamp(value: str) -> float:
    value = value.strip().replace(",", ".")
    parts = value.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    return float(parts[0])


def _parse_vtt_or_srt(path: Path):
    raw = path.read_text(encoding="utf-8-sig", errors="ignore")
    blocks = re.split(r"\n\s*\n", raw)
    segments = []

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing_index = next(
            (i for i, line in enumerate(lines) if "-->" in line), None
        )
        if timing_index is None:
            continue

        timing = lines[timing_index]
        match = re.search(
            r"(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})\s*-->\s*"
            r"(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})",
            timing,
        )
        if not match:
            continue

        text = _clean_text(" ".join(lines[timing_index + 1:]))
        if not text:
            continue

        try:
            start = _parse_timestamp(match.group(1))
            end = _parse_timestamp(match.group(2))
        except ValueError:
            continue

        segments.append({"start": start, "end": end, "text": text})

    if not segments:
        raise RuntimeError("Subtitle file was found but contained no usable text.")
    return segments


def _captions_from_youtube_api(video_id: str):
    api = YouTubeTranscriptApi()
    errors = []

    # Try preferred languages first. New versions of youtube-transcript-api
    # accept languages= on fetch(); if a provider rejects it, try the plain call.
    try:
        fetched = api.fetch(video_id, languages=PREFERRED_LANGUAGES)
        return _normalize_segments(fetched)
    except Exception as exc:
        errors.append(f"YouTube captions: {exc}")

    try:
        fetched = api.fetch(video_id)
        return _normalize_segments(fetched)
    except Exception as exc:
        errors.append(f"Default captions: {exc}")

    raise RuntimeError(" | ".join(errors))


def _captions_from_ytdlp(video_id: str):
    with tempfile.TemporaryDirectory(prefix="truthclick_subs_") as tmp:
        outtmpl = str(Path(tmp) / "%(id)s.%(ext)s")
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [
                "en", "en.*", "ur", "ur.*", "hi", "hi.*", "ar", "ar.*"
            ],
            "subtitlesformat": "vtt/best",
            "outtmpl": outtmpl,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
        except Exception as exc:
            raise RuntimeError(f"yt-dlp subtitles failed: {exc}") from exc

        candidates = sorted(Path(tmp).glob("*.vtt")) + sorted(Path(tmp).glob("*.srt"))
        if not candidates:
            raise RuntimeError("yt-dlp found no downloadable subtitle track.")

        # Prefer English, then Urdu/Hindi/Arabic, then any available track.
        def rank(p):
            name = p.name.lower()
            if ".en." in name or ".en-" in name:
                return 0
            if ".ur." in name or ".ur-" in name:
                return 1
            if ".hi." in name or ".hi-" in name:
                return 2
            if ".ar." in name or ".ar-" in name:
                return 3
            return 4

        return _parse_vtt_or_srt(sorted(candidates, key=rank)[0])


def _find_downloaded_audio(directory: Path):
    candidates = [
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in {
            ".webm", ".m4a", ".mp4", ".mp3", ".ogg", ".wav", ".flac", ".mpeg", ".mpga"
        }
    ]
    if not candidates:
        raise RuntimeError("Audio download completed but no audio file was produced.")
    return max(candidates, key=lambda p: p.stat().st_size)


def _compress_with_ffmpeg(source: Path, target: Path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None

    command = [
        ffmpeg, "-y", "-i", str(source),
        "-vn", "-ac", "1", "-ar", "16000",
        "-b:a", "32k", str(target)
    ]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
            check=False,
        )
    except Exception:
        return None

    if completed.returncode == 0 and target.exists() and target.stat().st_size > 0:
        return target
    return None


def _asr_with_groq(video_id: str, api_key: str):
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is required for the audio transcription fallback.")

    from groq import Groq

    with tempfile.TemporaryDirectory(prefix="truthclick_audio_") as tmp:
        tmp_path = Path(tmp)
        output_template = str(tmp_path / "%(id)s.%(ext)s")

        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            # Prefer a small audio-only stream. This avoids downloading video.
            "format": "worstaudio/worst",
            "outtmpl": output_template,
        }

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(
                    f"https://www.youtube.com/watch?v={video_id}",
                    download=True,
                )
        except Exception as exc:
            raise RuntimeError(f"Could not download audio for speech-to-text: {exc}") from exc

        audio_path = _find_downloaded_audio(tmp_path)

        # Groq's free-tier upload limit is 25 MB. Compress when possible.
        if audio_path.stat().st_size > 24 * 1024 * 1024:
            compressed = _compress_with_ffmpeg(
                audio_path, tmp_path / "truthclick_audio.mp3"
            )
            if compressed:
                audio_path = compressed

        client = Groq(api_key=api_key)

        # For small local files, upload directly and request segment timestamps.
        if audio_path.stat().st_size <= 24 * 1024 * 1024:
            try:
                with open(audio_path, "rb") as audio_file:
                    response = client.audio.transcriptions.create(
                        file=(audio_path.name, audio_file.read()),
                        model="whisper-large-v3-turbo",
                        response_format="verbose_json",
                        timestamp_granularities=["segment"],
                        temperature=0.0,
                    )
            except Exception as exc:
                raise RuntimeError(f"Groq speech-to-text failed: {exc}") from exc

            segments = getattr(response, "segments", None)
            if segments:
                normalized = []
                for seg in segments:
                    if isinstance(seg, dict):
                        start, end, text = (
                            seg.get("start", 0), seg.get("end", 0), seg.get("text", "")
                        )
                    else:
                        start = getattr(seg, "start", 0)
                        end = getattr(seg, "end", 0)
                        text = getattr(seg, "text", "")
                    text = _clean_text(str(text))
                    if text:
                        normalized.append({
                            "start": float(start or 0),
                            "end": float(end or 0),
                            "text": text,
                        })
                if normalized:
                    return normalized

            text = _clean_text(str(getattr(response, "text", "") or ""))
            if text:
                return [{"start": 0.0, "end": 0.0, "text": text}]

            raise RuntimeError("Groq returned an empty speech-to-text result.")

        # Last-resort URL mode for accounts that allow larger remote audio.
        # yt-dlp exposes a signed media URL; Groq can fetch public audio URLs.
        media_url = None
        try:
            formats = info.get("formats") or []
            audio_formats = [
                f for f in formats
                if f.get("url") and (
                    f.get("acodec") not in (None, "none")
                )
            ]
            if audio_formats:
                media_url = audio_formats[-1]["url"]
        except Exception:
            media_url = None

        if media_url:
            try:
                response = client.audio.transcriptions.create(
                    url=media_url,
                    model="whisper-large-v3-turbo",
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                    temperature=0.0,
                )
                segments = getattr(response, "segments", None)
                if segments:
                    normalized = []
                    for seg in segments:
                        if isinstance(seg, dict):
                            start, end, text = seg.get("start", 0), seg.get("end", 0), seg.get("text", "")
                        else:
                            start = getattr(seg, "start", 0)
                            end = getattr(seg, "end", 0)
                            text = getattr(seg, "text", "")
                        text = _clean_text(str(text))
                        if text:
                            normalized.append({
                                "start": float(start or 0),
                                "end": float(end or 0),
                                "text": text,
                            })
                    if normalized:
                        return normalized
            except Exception as exc:
                raise RuntimeError(
                    "The video's audio is larger than the direct upload limit and "
                    f"the remote audio fallback failed: {exc}"
                ) from exc

        raise RuntimeError(
            "The video's audio is larger than the Groq upload limit. "
            "Install ffmpeg so TruthClick can compress and transcribe longer videos."
        )


def get_transcript(video_id: str, api_key: str | None = None) -> list[dict]:
    """
    Retrieve a timestamped transcript using this fallback order:
      1. youtube-transcript-api
      2. yt-dlp subtitle tracks
      3. Groq Whisper speech-to-text from downloaded audio

    The final ASR fallback is what allows videos with no captions to be analyzed.
    """
    failures = []

    try:
        return _captions_from_youtube_api(video_id)
    except Exception as exc:
        failures.append(str(exc))

    try:
        return _captions_from_ytdlp(video_id)
    except Exception as exc:
        failures.append(str(exc))

    if api_key:
        try:
            return _asr_with_groq(video_id, api_key)
        except Exception as exc:
            failures.append(str(exc))
    else:
        failures.append("GROQ_API_KEY is unavailable for the audio transcription fallback.")

    raise RuntimeError(
        "No usable captions were available, and the audio transcription fallback "
        "could not produce a transcript. Details: " + " | ".join(failures)
    )


def build_chunks(segments: list[dict], max_chars: int = 7000) -> list[dict]:
    chunks = []
    cur = []
    count = 0

    for segment in segments:
        if cur and count + len(segment["text"]) > max_chars:
            chunks.append({
                "start": cur[0]["start"],
                "end": cur[-1]["end"],
                "text": " ".join(item["text"] for item in cur),
            })
            cur = []
            count = 0

        cur.append(segment)
        count += len(segment["text"])

    if cur:
        chunks.append({
            "start": cur[0]["start"],
            "end": cur[-1]["end"],
            "text": " ".join(item["text"] for item in cur),
        })

    return chunks
