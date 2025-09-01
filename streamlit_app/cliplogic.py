# cliplogic.py

import ffmpeg
import os
import uuid
import tempfile
from typing import List, Dict

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
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt").name
    cmd = (
        ffmpeg
        .input(filepath)
        .filter("select", f"gt(scene\\,{threshold})")
        .output("nul", format="null", vf="showinfo")
        .global_args("-loglevel", "info")
        .global_args("-stats")
    )
    try:
        out, err = cmd.run(capture_stdout=True, capture_stderr=True)
        times = []
        for line in err.decode().splitlines():
            if "pts_time:" in line:
                t = float(line.split("pts_time:")[1].split()[0])
                times.append(round(t, 3))
        # Ensure beginning and end
        times = [0.0] + times + [get_duration(filepath)]
        # Convert to segments
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

def export_clip(filepath: str, start: float, end: float, video_id: str) -> str:
    outname = f"clip_{video_id}_{start:.2f}-{end:.2f}.mp4".replace(":", "-")
    outpath = os.path.join(tempfile.gettempdir(), outname)
    ffmpeg.input(filepath, ss=start, to=end).output(outpath, c="copy").run(overwrite_output=True)
    return outpath

def export_all_zip(filepath: str, segments: List[Dict], video_id: str) -> str:
    import zipfile
    zip_name = os.path.join(tempfile.gettempdir(), f"{video_id}_clips.zip")
    with zipfile.ZipFile(zip_name, "w") as zipf:
        for i, seg in enumerate(segments):
            path = export_clip(filepath, seg["start"], seg["end"], video_id)
            arcname = f"clip_{i+1:03d}_{seg['start']:.2f}-{seg['end']:.2f}.mp4"
            zipf.write(path, arcname)
            os.remove(path)
    return zip_name
