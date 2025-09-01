# utils.py

import os
import uuid
import tempfile

def get_video_id(filepath: str) -> str:
    """
    Generate a short unique ID for the video based on filename + UUID.
    """
    base = os.path.basename(filepath).split('.')[0]
    short = uuid.uuid4().hex[:8]
    return f"{base}_{short}"

def ensure_temp_dir() -> str:
    """
    Create a temporary directory for storing video files safely.
    """
    temp_dir = os.path.join(tempfile.gettempdir(), "clipsplitter_temp")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir
# utils placeholder
