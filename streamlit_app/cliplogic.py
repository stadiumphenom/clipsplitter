import ffmpeg
import os
import uuid
import tempfile
import zipfile
from typing import List, Dict, Optional

def get_duration(filepath: str) -> float:
    probe = ffmpeg.probe(filepath)
    return float(probe["format"]["duration"])

def analyze_equal(filepath: str, chunk_len: int = 5) -> List[Dict]:
    duration = get_duration(filepath)
    chunks = []
    cursor = 0.0
    id = 1
    while cursor < duration:
        end = min(cursor + chunk_len, duration)
        chunks.append({
            "id": id,
            "start": round(cursor, 3),
            "end": round(end, 3),
            "duration": round(end - cursor, 3),
        })
        cursor = end
        id += 1
    return chunks

def analyze_scene(filepath: str, threshold: float = 0.3, min_len: int = 3) -> List[Dict]:
    try:
        out, err = (
            ffmpeg
            .input(filepath)
            .filter("select", f"gt(scene\\,{threshold})")
            .output("nul", format="null", vf="showinfo")
            .global_args("-loglevel", "info")
            .global_args("-stats")
            .run(capture_stdout=True, capture_stderr=True)
        )
        times = []
        for line in err.decode().splitlines():
            if "pts_time:" in line:
                t = float(line.split("pts_time:")[1].split()[0])
                times.append(round(t, 3))
        times = [0.0] + times + [get_duration(filepath)]
        segments = []
        for i in range(len(times) - 1):
            start = times[i]
            end = times[i+1]
            if end - start >= min_len:
                segments.append({
                    "id": i+1,
                    "start": start,
                    "end": end,
                    "duration": round(end - start, 3)
                })
        return segments
    except Exception as e:
        print("Scene detection failed:", e)
        return []

def export_clip(
    filepath: str,
    start: float,
    end: float,
    video_id: str,
    fmt: str = "mp4",
    resolution: str = "Original",
    filename: Optional[str] = None
) -> str:
    ext = fmt.lower()
    if not filename:
        filename = f"clip_{video_id}_{start:.2f}-{end:.2f}.{ext}".replace(":", "-")

    outpath = os.path.join(tempfile.gettempdir(), filename)

    stream = ffmpeg.input(filepath, ss=start, to=end)

    if resolution == "720p":
        stream = stream.output(outpath, s='1280x720')
    elif resolution == "1080p":
        stream = stream.output(outpath, s='1920x1080')
    else:
        stream = stream.output(outpath)

    stream = stream.global_args("-y")  # overwrite
    stream.run()
    return outpath

def export_all_zip(
    filepath: str,
    segments: List[Dict],
    video_id: str,
    fmt: str = "mp4",
    resolution: str = "Original",
    naming_template: str = "clip_{index}.mp4"
) -> str:
    zip_name = os.path.join(tempfile.gettempdir(), f"{video_id}_clips.zip")
    with zipfile.ZipFile(zip_name, "w") as zipf:
        for i, seg in enumerate(segments):
            filename = naming_template.replace("{index}", str(i + 1))
            path = export_clip(filepath, seg["start"], seg["end"], video_id, fmt, resolution, filename)
            zipf.write(path, arcname=filename)
            os.remove(path)
    return zip_name
