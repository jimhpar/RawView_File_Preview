# RawView (v2.0.1)

**RawView** is an ultra-fast, zero-lag Windows desktop utility that shows hardware-accelerated preview popups and live video playback when hovering over design, graphics, documents, and media files in Windows Explorer, Desktop, and File Dialogs.

---

## 🚀 Features

- **⚡ Zero-Lag Hover Previews**: Instant (<15ms) preview popups on cursor hover with configurable dwell time (40ms–350ms).
- **🎬 Smooth Live Video Playback**: Instant muted looping video previews for **MP4, MKV, MOV, AVI, WMV, WebM, FLV, TS, 3GP** with live progress tracking and resolution badge.
- **🎨 Comprehensive Format Support**:
  - **PSD & PSB**: Adobe Photoshop files (instant composite & layer extraction)
  - **AI**: Adobe Illustrator files (PDF vector rasterization & full workspace previews)
  - **EPS**: Encapsulated PostScript (full artwork XMP canvas & binary TIFF previews)
  - **PDF**: Portable Document Format (vector rasterization)
  - **Camera RAW**: Ultra-fast embedded previews for DNG, CR2, CR3, NEF, ARW, RAF, ORF, RW2, and 10+ other formats
  - **TIFF & TIF**: Multi-page, 16-bit, and high-dynamic range images
  - **SVG & SVGZ**: Scalable Vector Graphics with GPU rasterization
- **💎 Glassmorphic Floating HUD**: Smooth fade-in animations, format badge color-coding, resolution, color mode, duration, and file size badges.
- **⚡ Multi-Tier Caching**:
  - **L1 In-Memory LRU Cache**: Sub-millisecond instant recall for active browsing
  - **L2 Persistent Disk Cache**: Compressed thumbnail storage with hash-based invalidation
- **🖱️ Interactive Controls**:
  - `Space`: Pin preview window or Play/Pause video
  - Mouse Wheel: Zoom in / zoom out (images & vectors)
  - `Ctrl + C`: Copy preview image to clipboard
  - `Ctrl + O` / Enter: Open file in default application
  - `Esc`: Close preview immediately
- **⚙️ System Tray & Settings**:
  - Modern spacious settings dialog with categorized format toggles (Graphics vs Videos)
  - Speed presets (Ultra-Fast 80ms, Fast 120ms, Relaxed 250ms)
  - Cache manager and Windows Boot Autostart
- **📦 Clean Installer**: Installs into `C:\Program Files\RawView` with Start Menu & Desktop shortcuts.

---

## 🛠️ Building the Installer

To compile the standalone `RawView_v2.0.1_Setup.exe` installer:

```bash
python build_release.py
```

The installer will be generated in `dist_installer/RawView_v2.0.1_Setup.exe`.
