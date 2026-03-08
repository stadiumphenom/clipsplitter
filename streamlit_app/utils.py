import os
import re
import tempfile
import uuid
from pathlib import Path


def get_video_id(filename: str) -> str:
    base = os.path.basename(filename)
    stem = Path(base).stem
    return f"{stem}_{uuid.uuid4().hex[:6]}"


def ensure_temp_dir() -> str:
    temp_dir = os.path.join(tempfile.gettempdir(), "clipsplitter")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def get_preview_dir() -> str:
    preview_dir = os.path.join(tempfile.gettempdir(), "clip_previews")
    os.makedirs(preview_dir, exist_ok=True)
    return preview_dir


def sanitize_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[^\w\-. ]+", "_", name)
    return name[:200] or f"file_{uuid.uuid4().hex[:6]}"


def safe_export_filename(template: str, index: int, ext: str) -> str:
    base = (template or "clip_{index}").replace("{index}", str(index)).strip()
    base = sanitize_filename(base)
    root, _existing_ext = os.path.splitext(base)
    return f"{root}.{ext}"


def save_uploaded_file(uploaded_file) -> str:
    temp_dir = ensure_temp_dir()
    safe_name = sanitize_filename(uploaded_file.name)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    out_path = os.path.join(temp_dir, unique_name)

    with open(out_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return out_path
