# app.py — ClipSplitter Pro

import os
import json
import tempfile
import streamlit as st
from datetime import datetime

from cliplogic import analyze_equal, analyze_scene, export_clip, export_all_zip
from utils import get_video_id, ensure_temp_dir

# --- CONFIG ---
st.set_page_config(page_title="ClipSplitter Pro", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://placehold.co/120x120?text=🎬", width=120)
    st.title("ClipSplitter Pro")
    theme = st.radio("Theme", ["Light", "Dark"], horizontal=True)
    if theme == "Dark":
        st.markdown('<style>body{background-color:#111;color:white;}</style>', unsafe_allow_html=True)

    st.markdown("### 📁 Project")
    if st.button("💾 Save Project"):
        if "video_path" in st.session_state and "segments" in st.session_state:
            project_data = {
                "video_id": st.session_state.get("video_id"),
                "video_path": st.session_state.get("video_path"),
                "segments": st.session_state.get("segments"),
                "settings": st.session_state.get("settings", {})
            }
            filename = f"clipsplitter_project_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, "w") as f:
                json.dump(project_data, f, indent=2)
            with open(filename, "rb") as f:
                st.download_button("📥 Download Project JSON", f, file_name=filename)

    project_file = st.file_uploader("📂 Load Project JSON", type="json")
    if project_file:
        loaded = json.load(project_file)
        st.session_state["video_id"] = loaded.get("video_id")
        st.session_state["video_path"] = loaded.get("video_path")
        st.session_state["segments"] = loaded.get("segments")
        st.session_state["settings"] = loaded.get("settings", {})
        st.success("✅ Project loaded.")

# --- MAIN UI ---
st.title("🎬 ClipSplitter")
st.markdown("Upload a video, analyze scenes or duration, and export professional-grade clips.")

if st.button("Clear All"):
    st.session_state.clear()
    st.experimental_rerun()

video_file = st.file_uploader("Upload a video", type=["mp4", "mov", "webm"])

if video_file:
    temp_dir = ensure_temp_dir()
    video_path = os.path.join(temp_dir, video_file.name)
    with open(video_path, "wb") as f:
        f.write(video_file.read())

    video_id = get_video_id(video_path)
    st.session_state["video_id"] = video_id
    st.session_state["video_path"] = video_path
    st.success(f"📼 Uploaded! Video ID: {video_id}")

# --- SETTINGS ---
st.markdown("### ✂️ Clipping Options")
split_mode = st.selectbox("Split Mode", ["Equal length", "Scene detection"])
min_len = st.slider("Minimum Segment Length (seconds)", 1, 60, 5)

st.markdown("### ⚙️ Export Settings")
export_format = st.selectbox("Format", ["mp4", "webm"])
resolution = st.selectbox("Resolution", ["Original", "720p", "1080p"])
clip_naming = st.text_input("Clip Naming Template", value="clip_{index}.mp4")

# Save settings to session
st.session_state["settings"] = {
    "split_mode": split_mode,
    "min_len": min_len,
    "export_format": export_format,
    "resolution": resolution,
    "clip_naming": clip_naming,
}

# --- ANALYZE ---
if st.button("Analyze"):
    if "video_path" in st.session_state:
        path = st.session_state["video_path"]
        if split_mode == "Equal length":
            segments = analyze_equal(path, chunk_len=min_len)
        else:
            segments = analyze_scene(path, threshold=0.3, min_len=min_len)

        st.session_state["segments"] = segments
        st.success(f"🔍 Found {len(segments)} segments.")
    else:
        st.error("⚠️ No video uploaded.")

# --- DISPLAY SEGMENTS ---
if "segments" in st.session_state:
    st.subheader("🧩 Segments")

    for i, seg in enumerate(st.session_state["segments"]):
        st.markdown(f"**Clip {i+1}**: `{seg['start']:.2f}s → {seg['end']:.2f}s`")
        if st.button(f"Export Clip {i+1}", key=f"export_{i}"):
            path = export_clip(
                st.session_state["video_path"],
                seg["start"],
                seg["end"],
                st.session_state["video_id"],
                export_format,
                resolution,
                clip_naming.replace("{index}", str(i + 1))
            )
            with open(path, "rb") as f:
                st.download_button("⬇ Download Clip", f, file_name=os.path.basename(path))

    # --- EXPORT ALL ---
    if st.button("📦 Export All as ZIP"):
        zip_path = export_all_zip(
            st.session_state["video_path"],
            st.session_state["segments"],
            st.session_state["video_id"],
            export_format,
            resolution,
            clip_naming
        )
        with open(zip_path, "rb") as zf:
            st.download_button("⬇ Download ZIP", zf, file_name="clips.zip")

        export_to_local(zip_path)  # Save in ./exports
        st.success("✅ Export saved locally.")

# End of file
