# utils.py

import os
import uuid
import tempfile

def get_video_id(filepath: str) -> str:
    """Generate a short unique ID based on filename and UUID."""
    base = os.path.splitext(os.path.basename(filepath))[0]
    return f"{base}_{uuid.uuid4().hex[:6]}"

def ensure_temp_dir() -> str:
    """Ensure a temporary directory exists and return its path."""
    temp_dir = os.path.join(tempfile.gettempdir(), "clipsplitter")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir
