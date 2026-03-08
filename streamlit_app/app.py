# app.py — ClipSplitter Pro

import json
import os
from datetime import datetime
from pathlib import Path

import streamlit as st

from cliplogic import (
    ClipSplitterError,
    analyze_equal,
    analyze_scene,
    export_all_zip,
    export_clip,
    probe_video,
)
from utils import (
    ensure_temp_dir,
    get_video_id,
    safe_export_filename,
    save_uploaded_file,
)

st.set_page_config(page_title="ClipSplitter Pro", layout="wide")


def init_state() -> None:
    defaults = {
        "video_id": None,
        "video_path": None,
        "video_name": None,
        "video_meta": None,
        "segments": [],
        "settings": {
            "split_mode": "Equal length",
            "min_len": 10,
            "scene_threshold": 0.30,
            "export_format": "mp4",
            "resolution": "Original",
            "clip_naming": "clip_{index}",
        },
        "project_loaded": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_state() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_state()


def current_settings() -> dict:
    return st.session_state.get("settings", {})


def source_available() -> bool:
    path = st.session_state.get("video_path")
    return bool(path and os.path.exists(path))


def save_project_payload() -> dict:
    return {
        "project_version": 1,
        "saved_at": datetime.utcnow().isoformat() + "Z",
        "video_id": st.session_state.get("video_id"),
        "video_name": st.session_state.get("video_name"),
        "video_meta": st.session_state.get("video_meta"),
        "segments": st.session_state.get("segments", []),
        "settings": st.session_state.get("settings", {}),
        "note": (
            "Source video binary is not embedded in this project file. "
            "Re-upload the original source video when loading on a new machine/session."
        ),
    }


def load_project_payload(payload: dict) -> None:
    st.session_state["video_id"] = payload.get("video_id")
    st.session_state["video_name"] = payload.get("video_name")
    st.session_state["video_meta"] = payload.get("video_meta")
    st.session_state["segments"] = payload.get("segments", [])
    st.session_state["settings"] = payload.get("settings", st.session_state["settings"])
    st.session_state["project_loaded"] = True


def analyze_video() -> None:
    if not source_available():
        st.error("Upload a source video before analyzing.")
        return

    settings = current_settings()
    path = st.session_state["video_path"]

    try:
        if settings["split_mode"] == "Equal length":
            segments = analyze_equal(path, chunk_len=int(settings["min_len"]))
        else:
            segments = analyze_scene(
                path,
                threshold=float(settings["scene_threshold"]),
                min_len=int(settings["min_len"]),
            )

        if not segments:
            st.warning("No segments were found with the current settings.")
            st.session_state["segments"] = []
            return

        st.session_state["segments"] = segments
        st.success(f"Found {len(segments)} segments.")
    except ClipSplitterError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Unexpected analysis failure: {exc}")


def render_segment_card(index: int, seg: dict, export_format: str, resolution: str, clip_naming: str) -> None:
    start = float(seg["start"])
    end = float(seg["end"])
    duration = float(seg["duration"])

    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 2, 2])
        with c1:
            st.markdown(f"**Clip {index}**")
            st.caption(f"{start:.2f}s → {end:.2f}s")
            st.write(f"Duration: {duration:.2f}s")
        with c2:
            st.code(f"{start:.2f} - {end:.2f}", language="text")
        with c3:
            filename = safe_export_filename(
                clip_naming,
                index=index,
                ext=export_format,
            )

            if st.button(f"Export Clip {index}", key=f"export_{index}"):
                try:
                    out_path = export_clip(
                        filepath=st.session_state["video_path"],
                        start=start,
                        end=end,
                        video_id=st.session_state["video_id"],
                        fmt=export_format,
                        resolution=resolution,
                        filename=filename,
                    )
                    with open(out_path, "rb") as f:
                        st.download_button(
                            label=f"Download Clip {index}",
                            data=f.read(),
                            file_name=os.path.basename(out_path),
                            mime="video/mp4" if export_format == "mp4" else "video/webm",
                            key=f"download_{index}",
                        )
                except ClipSplitterError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"Export failed for Clip {index}: {exc}")


init_state()

with st.sidebar:
    st.title("ClipSplitter Pro")
    st.caption("Split long videos into usable clips fast.")

    if st.button("Clear All"):
        reset_state()
        st.rerun()

    st.markdown("### Project")
    can_save = bool(st.session_state.get("segments"))
    if can_save:
        payload = save_project_payload()
        filename = f"clipsplitter_project_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        st.download_button(
            "Download Project JSON",
            data=json.dumps(payload, indent=2).encode("utf-8"),
            file_name=filename,
            mime="application/json",
        )

    project_file = st.file_uploader("Load Project JSON", type=["json"], key="project_uploader")
    if project_file is not None:
        try:
            payload = json.load(project_file)
            load_project_payload(payload)
            st.success("Project loaded.")
            if not source_available():
                st.info("Re-upload the original source video to analyze/export clips in this session.")
        except Exception as exc:
            st.error(f"Failed to load project JSON: {exc}")

st.title("🎬 ClipSplitter")
st.write("Upload a source video, split it by equal length or basic scene detection, then export clips individually or as a ZIP.")

uploaded_file = st.file_uploader("Upload a video", type=["mp4", "mov", "webm", "mkv"], key="video_uploader")

if uploaded_file is not None:
    try:
        ensure_temp_dir()
        saved_path = save_uploaded_file(uploaded_file)
        video_id = get_video_id(uploaded_file.name)

        st.session_state["video_id"] = video_id
        st.session_state["video_path"] = saved_path
        st.session_state["video_name"] = uploaded_file.name
        st.session_state["segments"] = []

        meta = probe_video(saved_path)
        st.session_state["video_meta"] = meta

        st.success(f"Uploaded: {uploaded_file.name}")
    except ClipSplitterError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Upload failed: {exc}")

if source_available():
    st.subheader("Source Video")
    st.video(st.session_state["video_path"])

    meta = st.session_state.get("video_meta") or {}
    if meta:
        c1, c2, c3 = st.columns(3)
        c1.metric("Duration", f"{meta.get('duration', 0):.2f}s")
        c2.metric("Resolution", f"{meta.get('width', '?')}×{meta.get('height', '?')}")
        c3.metric("Format", meta.get("format_name", "unknown"))

st.markdown("### Clipping Options")
saved_settings = current_settings()

split_mode = st.selectbox(
    "Split Mode",
    ["Equal length", "Scene detection"],
    index=0 if saved_settings["split_mode"] == "Equal length" else 1,
)

min_len = st.slider(
    "Minimum Segment Length (seconds)",
    min_value=1,
    max_value=300,
    value=int(saved_settings["min_len"]),
)

scene_threshold = saved_settings.get("scene_threshold", 0.30)
if split_mode == "Scene detection":
    st.caption("Scene detection is a basic beta feature and may vary by source video.")
    scene_threshold = st.slider(
        "Scene Detection Threshold",
        min_value=0.05,
        max_value=1.00,
        value=float(saved_settings.get("scene_threshold", 0.30)),
        step=0.05,
    )

st.markdown("### Export Settings")
export_format = st.selectbox(
    "Format",
    ["mp4", "webm"],
    index=0 if saved_settings["export_format"] == "mp4" else 1,
)

resolution = st.selectbox(
    "Resolution",
    ["Original", "720p", "1080p"],
    index=["Original", "720p", "1080p"].index(saved_settings["resolution"]),
)

clip_naming = st.text_input(
    "Clip Naming Template",
    value=saved_settings.get("clip_naming", "clip_{index}"),
    help="Use {index}. Extension is added automatically.",
)

st.session_state["settings"] = {
    "split_mode": split_mode,
    "min_len": int(min_len),
    "scene_threshold": float(scene_threshold),
    "export_format": export_format,
    "resolution": resolution,
    "clip_naming": clip_naming.strip() or "clip_{index}",
}

analyze_disabled = not source_available()
if st.button("Analyze", disabled=analyze_disabled):
    analyze_video()

segments = st.session_state.get("segments", [])
if segments:
    st.subheader("Segments")

    for i, seg in enumerate(segments, start=1):
        render_segment_card(
            index=i,
            seg=seg,
            export_format=export_format,
            resolution=resolution,
            clip_naming=clip_naming,
        )

    if st.button("Export All as ZIP"):
        try:
            zip_path = export_all_zip(
                filepath=st.session_state["video_path"],
                segments=segments,
                video_id=st.session_state["video_id"],
                fmt=export_format,
                resolution=resolution,
                naming_template=clip_naming,
            )
            with open(zip_path, "rb") as zf:
                st.download_button(
                    "Download ZIP",
                    data=zf.read(),
                    file_name=f"{st.session_state['video_id']}_clips.zip",
                    mime="application/zip",
                )
        except ClipSplitterError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Export all failed: {exc}")
