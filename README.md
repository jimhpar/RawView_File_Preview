# RawView (v1.0.13)

**RawView** is an ultra-fast, zero-lag Windows desktop utility that shows hardware-accelerated preview popups when hovering over design and graphics files in Windows Explorer, Desktop, and File Dialogs.

---

## 🚀 Features

- **⚡ Zero-Lag Hover Previews**: Instant (<15ms) preview popups on cursor hover with configurable dwell time (80ms–300ms).
- **🎨 Comprehensive Format Support**:
  - **PSD & PSB**: Adobe Photoshop files (instant composite & layer extraction)
  - **AI**: Adobe Illustrator files (PDF vector rasterization & XMP workspace previews)
  - **EPS**: Encapsulated PostScript (binary header TIFF previews & vector cards)
  - **PDF**: Portable Document Format (vector rasterization)
  - **Camera RAW**: Ultra-fast embedded previews for DNG, CR2, CR3, NEF, ARW, RAF, ORF, RW2, and 10+ other formats
  - **TIFF & TIF**: Multi-page, 16-bit, and high-dynamic range images
  - **SVG & SVGZ**: Scalable Vector Graphics with GPU rasterization
- **💎 Glassmorphic Floating HUD**: Smooth fade-in animations, format badge color-coding, resolution, color mode, and file size badges.
- **⚡ Multi-Tier Caching**:
  - **L1 In-Memory LRU Cache**: Sub-millisecond instant recall for active browsing
  - **L2 Persistent Disk Cache**: Compressed thumbnail storage with hash-based invalidation
- **🖱️ Interactive Controls**:
  - `Space`: Pin preview window so you can move cursor into it
  - Mouse Wheel: Zoom in / zoom out
  - `Ctrl + C`: Copy preview image to clipboard
  - `Ctrl + O` / Enter: Open file in default application
  - `Esc`: Close preview immediately
- **⚙️ System Tray & Settings**:
  - Enable/disable hover previews on the fly
  - Speed presets (Ultra-Fast 80ms, Fast 150ms, Relaxed 280ms)
  - Format selection & cache manager
- **🔌 Windows Boot Autostart**: Starts silently in the System Tray on Windows startup.
- **📦 Clean Installer**: Installs into `C:\Program Files\RawView` with Start Menu & Desktop shortcuts.

---

## 🛠️ Building the Installer

To compile the standalone `RawView_v1.0.13_Setup.exe` installer:

```bash
python build_release.py
```

The installer will be generated in `dist_installer/RawView_v1.0.13_Setup.exe`.
