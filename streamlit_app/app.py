# streamlit_app/app.py

import streamlit as st
from cliplogic import analyze_equal, analyze_scene, export_clip, export_all_zip
from utils import get_video_id, ensure_temp_dir
import tempfile, os

st.set_page_config(page_title="ClipSplitter", layout="wide")
st.markdown("""
<style>
    .css-1d391kg { background-color: #fdfdfd !important; }
    .sidebar .sidebar-content { background: #111 !important; color: white; }
    .css-1d391kg h1 { color: #111 }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://placehold.co/120x120?text=🎬", width=120)
    st.markdown("## ClipSplitter Pro Edition")
    st.markdown("Built for creators & editors.")
    theme = st.radio("Theme", ["Light", "Dark"], horizontal=True)
    if theme == "Dark":
        st.markdown('<style>body{background-color:#111;color:white;}</style>', unsafe_allow_html=True)

st.title("🎬 ClipSplitter")

st.markdown("Upload a video, choose how you want to split it, and download your clips.")

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

    st.success(f"Video uploaded! ID: {video_id}")

    split_mode = st.selectbox("Split mode", ["Equal length", "Scene detection"])
    min_len = st.slider("Minimum segment length (seconds)", 1, 60, 5)

    if st.button("Analyze"):
        if split_mode == "Equal length":
            segments = analyze_equal(video_path, chunk_len=min_len)
        else:
            segments = analyze_scene(video_path, threshold=0.3, min_len=min_len)

        st.session_state["segments"] = segments
        st.success(f"Found {len(segments)} segments")

if "segments" in st.session_state:
    st.subheader("Segments")
    for i, seg in enumerate(st.session_state["segments"]):
        st.write(f"Clip {i+1}: {seg['start']:.2f}s to {seg['end']:.2f}s")
        if st.button(f"Export Clip {i+1}", key=f"export_{i}"):
            path = export_clip(
                st.session_state["video_path"],
                seg['start'],
                seg['end'],
                st.session_state["video_id"]
            )
            with open(path, "rb") as f:
                st.download_button(f"Download Clip {i+1}", f, file_name=os.path.basename(path))

    if st.button("Export All as ZIP"):
        zip_path = export_all_zip(
            st.session_state["video_path"],
            st.session_state["segments"],
            st.session_state["video_id"]
        )
        with open(zip_path, "rb") as z:
            st.download_button("Download ZIP", z, file_name="clips.zip")
        try:
            os.remove(st.session_state["video_path"])
        except:
            pass
# app.py placeholder
