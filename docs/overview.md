# 📘 ClipSplitter Pro — Architecture & Product Overview

## 🚀 What It Does

ClipSplitter Pro is a lightweight local video utility that helps users split long-form videos into smaller exportable clips.

Users can process a source video using:

- **Equal-length splitting** for predictable chunking
- **Basic scene detection** using FFmpeg threshold-based analysis

Generated clips can then be exported:

- individually
- or bundled together as a `.zip`

---

## ✅ Current Core Workflow

1. User uploads a source video
2. Video is saved to a temporary working directory
3. The app analyzes the video using the selected split mode
4. Clip segments are listed with start/end timestamps
5. User exports clips one-by-one or as a ZIP archive

---

## 🧱 Architecture Diagram

```mermaid
graph LR
    A[User Uploads Video] --> B[Temporary File Saved]
    B --> C[Video Metadata Probed]
    C --> D1[Equal-Length Analysis]
    C --> D2[Scene Detection Analysis]
    D1 --> E[Segments Generated]
    D2 --> E
    E --> F[Export Individual Clips]
    E --> G[Export ZIP Bundle]
