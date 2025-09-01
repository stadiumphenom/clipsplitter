# 📘 ClipSplitter — Architecture & Value Overview

## 🚀 What It Does
ClipSplitter allows users to upload full-length videos and instantly split them into smaller mini-clips using either:

- **Equal-length** segments (e.g. every 5s)
- **Scene-based** detection (FFmpeg scene threshold)

Clips can be downloaded:
- Individually (`clip_001.mp4`, `clip_002.mp4`, ...)
- Or bundled as a `.zip`

---

## 🧱 Architecture Diagram

```mermaid
graph LR
    A[User Uploads Video] --> B[Temp Directory Created]
    B --> C[Video Analyzed]
    C --> D1[Equal Chunking]
    C --> D2[Scene Detection]
    D1 --> E[Segments Listed]
    D2 --> E
    E --> F[Export (Individual or ZIP)]
