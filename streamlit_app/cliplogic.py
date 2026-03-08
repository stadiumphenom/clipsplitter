import os
import tempfile
import uuid
import zipfile
from typing import Dict, List, Optional

import ffmpeg


class ClipSplitterError(Exception):
    """Application-level error for clean UI messaging."""


def _null_output_target() -> str:
    return "NUL" if os.name == "nt" else "/dev/null"


def _run_ffmpeg(stream) -> None:
    try:
        stream.run(capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
        raise ClipSplitterError(f"FFmpeg failed: {stderr}") from exc


def probe_video(filepath: str) -> Dict:
    if not os.path.exists(filepath):
        raise ClipSplitterError("Source video file not found.")

    try:
        probe = ffmpeg.probe(filepath)
        format_info = probe.get("format", {})
        streams = probe.get("streams", [])
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})

        return {
            "duration": float(format_info.get("duration", 0.0)),
            "format_name": format_info.get("format_name", "unknown"),
            "width": int(video_stream.get("width", 0) or 0),
            "height": int(video_stream.get("height", 0) or 0),
        }
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
        raise ClipSplitterError(f"Could not read video metadata: {stderr}") from exc
    except Exception as exc:
        raise ClipSplitterError(f"Could not read video metadata: {exc}") from exc


def get_duration(filepath: str) -> float:
    meta = probe_video(filepath)
    duration = float(meta.get("duration", 0.0))
    if duration <= 0:
        raise ClipSplitterError("Video duration is zero or unavailable.")
    return duration


def analyze_equal(filepath: str, chunk_len: int = 5) -> List[Dict]:
    if chunk_len <= 0:
        raise ClipSplitterError("Chunk length must be greater than zero.")

    duration = get_duration(filepath)
    chunks: List[Dict] = []
    cursor = 0.0
    clip_id = 1

    while cursor < duration:
        end = min(cursor + chunk_len, duration)
        chunks.append(
            {
                "id": clip_id,
                "start": round(cursor, 3),
                "end": round(end, 3),
                "duration": round(end - cursor, 3),
            }
        )
        cursor = end
        clip_id += 1

    return chunks


def analyze_scene(filepath: str, threshold: float = 0.3, min_len: int = 3) -> List[Dict]:
    if min_len <= 0:
        raise ClipSplitterError("Minimum segment length must be greater than zero.")

    if not (0.0 < threshold <= 1.0):
        raise ClipSplitterError("Scene threshold must be between 0 and 1.")

    duration = get_duration(filepath)

    try:
        stream = (
            ffmpeg
            .input(filepath)
            .filter("select", f"gt(scene\\,{threshold})")
            .output(_null_output_target(), format="null", vf="showinfo")
            .global_args("-hide_banner", "-loglevel", "info", "-stats")
        )
        out, err = stream.run(capture_stdout=True, capture_stderr=True)

        scene_times: List[float] = []
        for line in err.decode("utf-8", errors="ignore").splitlines():
            if "pts_time:" in line:
                try:
                    t = float(line.split("pts_time:")[1].split()[0])
                    if 0.0 < t < duration:
                        scene_times.append(round(t, 3))
                except (ValueError, IndexError):
                    continue

        deduped = sorted(set(scene_times))
        times = [0.0] + deduped + [duration]

        segments: List[Dict] = []
        for i in range(len(times) - 1):
            start = times[i]
            end = times[i + 1]
            if (end - start) >= min_len:
                segments.append(
                    {
                        "id": i + 1,
                        "start": round(start, 3),
                        "end": round(end, 3),
                        "duration": round(end - start, 3),
                    }
                )

        return segments
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
        raise ClipSplitterError(f"Scene detection failed: {stderr}") from exc
    except Exception as exc:
        raise ClipSplitterError(f"Scene detection failed: {exc}") from exc


def _apply_resolution(stream, resolution: str):
    if resolution == "720p":
        return stream.filter("scale", 1280, 720, force_original_aspect_ratio="decrease")
    if resolution == "1080p":
        return stream.filter("scale", 1920, 1080, force_original_aspect_ratio="decrease")
    return stream


def export_clip(
    filepath: str,
    start: float,
    end: float,
    video_id: str,
    fmt: str = "mp4",
    resolution: str = "Original",
    filename: Optional[str] = None,
) -> str:
    if end <= start:
        raise ClipSplitterError("Clip end time must be greater than start time.")

    if not os.path.exists(filepath):
        raise ClipSplitterError("Source video file not found.")

    fmt = fmt.lower().strip()
    if fmt not in {"mp4", "webm"}:
        raise ClipSplitterError("Export format must be mp4 or webm.")

    clip_uuid = uuid.uuid4().hex[:8]
    ext = fmt

    if not filename:
        filename = f"clip_{video_id}_{start:.2f}-{end:.2f}_{clip_uuid}.{ext}"
    else:
        root, _old_ext = os.path.splitext(filename)
        filename = f"{root}.{ext}"

    outpath = os.path.join(tempfile.gettempdir(), filename)

    try:
        inp = ffmpeg.input(filepath, ss=max(0, start), to=end)
        video = _apply_resolution(inp.video, resolution)
        audio = inp.audio

        if fmt == "mp4":
            stream = ffmpeg.output(
                video,
                audio,
                outpath,
                vcodec="libx264",
                acodec="aac",
                movflags="+faststart",
            )
        else:
            stream = ffmpeg.output(
                video,
                audio,
                outpath,
                vcodec="libvpx-vp9",
                acodec="libopus",
            )

        _run_ffmpeg(stream.global_args("-y"))
        return outpath
    except ClipSplitterError:
        raise
    except Exception as exc:
        raise ClipSplitterError(f"Export failed: {exc}") from exc


def export_all_zip(
    filepath: str,
    segments: List[Dict],
    video_id: str,
    fmt: str = "mp4",
    resolution: str = "Original",
    naming_template: str = "clip_{index}",
) -> str:
    if not segments:
        raise ClipSplitterError("No segments available to export.")

    zip_name = os.path.join(tempfile.gettempdir(), f"{video_id}_clips.zip")
    temp_paths: List[str] = []

    try:
        with zipfile.ZipFile(zip_name, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
            for i, seg in enumerate(segments, start=1):
                base_name = naming_template.replace("{index}", str(i)).strip() or f"clip_{i}"
                root, _old_ext = os.path.splitext(base_name)
                arcname = f"{root}.{fmt}"

                path = export_clip(
                    filepath=filepath,
                    start=float(seg["start"]),
                    end=float(seg["end"]),
                    video_id=video_id,
                    fmt=fmt,
                    resolution=resolution,
                    filename=f"{root}_{uuid.uuid4().hex[:6]}.{fmt}",
                )
                temp_paths.append(path)
                zipf.write(path, arcname=arcname)

        return zip_name
    except ClipSplitterError:
        raise
    except Exception as exc:
        raise ClipSplitterError(f"Bulk export failed: {exc}") from exc
    finally:
        for path in temp_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
