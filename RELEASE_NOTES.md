# 🚀 RawView v2.0.1 Release Notes

**RawView v2.0.1** is a major feature and performance release that introduces **Instant Live Video Hover Playback**, resolves **EPS artboard-clipping for full-workspace artworks**, fixes **Settings dialog typography**, and enhances **Windows Explorer hidden-extension disambiguation**.

---

## 🌟 What's New & Key Highlights

### 🎬 1. Instant Live Video Hover Playback
- **Zero-Lag Hover Playback**: Hovering the cursor over any supported video file in Windows Explorer, Desktop, or open/save file dialogs instantly plays a smooth, hardware-accelerated looping preview.
- **Muted Looping Audio**: Video audio is muted by default to ensure unobtrusive background browsing.
- **Supported Formats**: `.mp4`, `.mkv`, `.mov`, `.avi`, `.wmv`, `.webm`, `.flv`, `.m4v`, `.ts`, `.3gp`, `.mpg`, `.mpeg`.
- **Live Video Player HUD**:
  - Micro progress bar indicating real-time playback position.
  - Video duration and current playback time display (`0:12 / 1:45`).
  - Resolution badge (e.g., `1920 × 1080 px`, `4K`, `720p`).
  - Color-coded format badges (`MP4`, `MKV`, `MOV`, `AVI`, `WEBM`).
- **Interactive Controls**: Press `Space` to pin the preview and toggle Play / Pause.
- **Zero Resource Leakage**: Hardware video decoding pipelines and audio resources are immediately released on unhover/dismiss.

---

### 🎨 2. Uncropped EPS Full Artwork Preview Fix
- **Full Workspace Preservation**: Fixed an issue where Adobe Illustrator EPS files with graphics extending outside the artboard (e.g., sportswear jersey sleeves, print layout dies, title splashes) had their edges cropped by the embedded TIFF preview.
- **XMP Canvas Extraction**: Prioritizes the unclipped **XMP Full Workspace Canvas** (`<xmpGImg:image>`) to ensure 100% of the vector drawing is visible.
- **Dynamic Aspect Ratio Fitting**: The preview HUD dynamically auto-fits wide graphics (e.g., 2.5:1 ratio jerseys) and tall posters without clipping or distortion.

---

### 🔍 3. Intelligent File Hover & Extension Disambiguation
- **Hidden Extension Resolution**: When Windows Explorer hides file extensions, RawView now cross-references row `Type` descriptions (*e.g., "PDF Document", "Encapsulated PostScript", "MP4 Video"*) and file sizes to accurately open the correct preview when identically named files reside in the same folder.
- **Active Explorer COM Binding**: Resolves current folder paths and focused items directly from the active Explorer window for pinpoint accuracy.
- **Tighter Row Boundaries**: Reduced vertical hover bounding box buffer to 4px for instant switching between adjacent rows in Details view.

---

### ⚙️ 4. Settings Dialog Typography & UI Redesign
- **Fixed Text Squishing Bug**: Resolved a CSS styling issue where checkbox text labels were vertically compressed and illegible.
- **Expanded Layout**: Increased dialog dimensions to `540 × 680 px` for optimal readability and spacing.
- **Categorized Format Selection**:
  - **Graphics & Design Formats**: PSD, PSB, AI, EPS, PDF, TIFF, SVG, Camera RAW
  - **Live Video Formats**: MP4, MKV, MOV, AVI, WebM, WMV, FLV, TS
- **Hover Responsiveness Slider**: Configurable settle dwell times (40ms – 350ms).
- **Cache Management**: One-click thumbnail cache size inspection and clearing.

---

## ⌨️ Keyboard & Mouse Controls

| Action | Control | Description |
| :--- | :--- | :--- |
| **Pin Preview** | `Space` | Keeps the preview window open even when cursor moves away |
| **Play / Pause Video** | `Space` *(when pinned)* | Toggles live video playback |
| **Zoom In / Out** | `Mouse Wheel` | Smoothly zooms images and vector graphics from 50% to 800% |
| **Pan Image** | `Left-Click + Drag` | Moves the zoomed image within the viewport |
| **Reset View** | `Double-Click` | Resets zoom and pan back to 100% fitted size |
| **Copy Image** | `Ctrl + C` | Copies high-resolution preview image to Windows Clipboard |
| **Open File** | `Ctrl + O` / `Enter` | Launches the file in its default desktop application |
| **Close Preview** | `Esc` | Immediately dismisses the preview HUD |

---

## 📦 Downloads & Verification

| Asset | Details | Direct Link |
| :--- | :--- | :--- |
| **Setup Installer** | Standalone 64-bit Windows Setup (~121.95 MB) | `RawView_v2.0.1_Setup.exe` |
| **Publisher** | BlackBox THC | Certified Release |
| **Source Code** | Git branch `main` | [GitHub Repository](https://github.com/jimhpar/RawView_File_Preview) |

---

## 🛠️ System Requirements
- **OS**: Windows 10 / Windows 11 (64-bit)
- **Architecture**: x86_64 / x64
- **Dependencies**: None (self-contained standalone executable)
