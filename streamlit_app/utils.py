# utils.py

import os
import uuid
import tempfile

def get_video_id(filepath):
    """Generate a short unique ID based on filename and UUID."""
    base = os.path.basename(filepath)
    return f"{base.split('.')[0]}_{uuid.uuid4().hex[:6]}"

def ensure_temp_dir():
    """Ensure a temporary directory exists and return its path."""
    temp_dir = os.path.join(tempfile.gettempdir(), "clipsplitter")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir
