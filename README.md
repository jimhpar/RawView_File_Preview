# RawView (v4.1.2)

**RawView** is an ultra-fast, zero-lag Windows desktop utility that shows hardware-accelerated preview popups, multi-page document navigation, live video playback, and **permanent Windows Explorer folder grid thumbnails with native app icon overlay badges** for design, graphics, documents, Microsoft Office files, media projects, and camera RAW images.

---

## 🚀 Features

- **🔄 Right-Click "Refresh Thumbnail" Context Menu (NEW in v4.1.2)**:
  - **Single File Refresh**: Right-click any supported file (`.psd`, `.ai`, `.eps`, `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.raw`, etc.) and select **"Refresh Thumbnail"** to instantly purge its cache and trigger Windows Explorer to redraw the thumbnail.
  - **Active Folder Refresh**: Right-click empty background space or any folder without selecting a file and click **"Refresh All Thumbnails in Folder"** to invalidate and regenerate thumbnails for every item in that directory.
  - **Status HUD Notification**: Displays a sleek, floating on-screen HUD toast badge confirming thumbnail refresh completion.
- **🏷️ Reliable App Icon Overlay Badges System-Wide (NEW in v4.1.2)**:
  - **Automatic Windows Explorer Configuration**: Automatically enables Windows `ShowTypeOverlay` registry setting across machines, guaranteeing that application overlay badges (`Ps`, `Ai`, `W`, `P`, `PDF`) render consistently in the bottom-right corner of all thumbnails.
  - **Settings Dialog Toggle**: Interactive checkbox in Preferences (`Display App Icon Badges on Thumbnails`) to easily enable or disable overlay badges on demand.
- **⚡ Zero-Click Instant Hover Preview Engine (NEW in v4.1.2)**:
  - **Multiline Filename Wrapping**: Resolves multiline filename wrapping (`\r\n`) in Explorer icon/grid views without requiring a mouse click on the file first.
  - **Windows 11 `UIItemsView` Support**: Leverages `ValuePattern` extraction for `System.ItemNameDisplay` controls in modern Windows 11 File Explorer.
  - **Active Tab Resolution**: Extracts the active tab title directly from `win32gui.GetWindowText` to eliminate wrong-tab mismatches in multi-tab Explorer windows.
  - **Progressive Dwell Retries**: Automatically retries resolution over consecutive timer ticks so hover triggers immediately without needing to re-enter or click.
- **🔐 Digitally Signed Software (Authenticode - NEW in v4.1.2)**:
  - **Code Signing**: All binaries (`RawView.exe`, `RawViewThumbnailProvider.dll`, and `RawView_v4.1.2_Setup.exe`) are digitally signed with Authenticode certificates.
  - **Automated Root Installation**: Installer automatically configures the trusted certificate store for smooth, warning-free installation.
- **🖼️ Permanent Windows Explorer Folder Grid Thumbnails & App Badges**:
  - **Direct Folder Previews**: Renders high-definition artwork thumbnails directly inside Windows Explorer folders for `.psd`, `.ai`, `.eps`, `.pdf`, `.docx`, `.doc`, `.pptx`, `.ppt`, `.xlsx`, `.xls`, `.raw`, `.cr2`, `.cr3`, `.nef`, `.arw`, `.dng`, `.svg`.
  - **Native App Type Overlay Badges**: Displays crisp application overlay badges (`Ps`, `Ai`, `W`, `P`, `PDF`) in the bottom-right corner of thumbnails.
  - **Always-Active 24/7 Service**: Folder thumbnail generation remains permanently active even when hover preview is toggled off (`Ctrl + \``).
  - **3-Tier Resilient Architecture**: Ultra-fast disk cache (<1ms), Live Named Pipe IPC (<10ms), and standalone headless worker fallback.
  - **Cache Refresh Button**: Single-click utility in Settings to rebuild and refresh Windows Explorer thumbnail caches.
- **📦 Zero-Lag Archive File Previews (ZIP, RAR, 7-Zip, TAR - NEW in v4.1.0)**:
  - **Zero-Extraction Inspection**: Hover over `.zip`, `.rar`, `.7z`, `.tar`, `.gz`, `.tgz`, `.bz2` to instantly view a structured directory tree without decompressing or extracting the archive.
  - **Smart Type Icons & Metadata**: Displays contextual file icons (📁 folder, 🖼️ design, 📄 document, 🎬 media, ⚙️ code), formatted individual sizes, date modified, total file/folder count, and uncompressed size ratio.
  - **Format-Themed Aesthetic Badges**: Distinct glowing badges and glassmorphic headers tailored for ZIP (Amber), RAR (Fuchsia), and 7-Zip (Cyan).
- **⚡ Zero-Lag Hover Previews**: Instant (<15ms) preview popups on cursor hover with configurable dwell time (40ms–350ms).
- **📑 Multi-Page Thumbnail Sidebar (PDF & Word)**:
  - **Visual Left Sidebar**: Displays miniature page preview thumbnails for all pages (`Page 1`, `Page 2`, `Page 3`...).
  - **Space to Pin & Browse**: Press `Space` to pin the preview window, then click any page thumbnail card to view that page immediately.
  - **Keyboard Navigation**: Navigate smoothly between document pages using `Down` / `Up` or `PageDown` / `PageUp`.
- **🇧🇩 Authentic Bengali Font & SutonnyMJ/Bijoy Engine**:
  - **Automatic Bijoy to Unicode**: Completely resolves broken/garbled ASCII letters in legacy SutonnyMJ Word documents into clean, authentic Bengali text.
  - **Full Conjunct & Modifier Support**: Accurately maps complex conjuncts, pre-kars, post-kars, and ref (`র্`).
  - **Windows Bengali Typography Stack**: Native font fallbacks (`Kalpurush`, `SolaimanLipi`, `Nikosh`, `Nirmala UI`, `Vrinda`).
- **🎬 Smart Linked Video & Footage Playback**:
  - **After Effects & Premiere Pro (`.aep`, `.prproj`)**: Automatically discovers matching rendered/exported MP4/MOV videos and linked timeline footage clips to play instant hardware-accelerated live video on hover!
  - **Motion Graphics Typography Showcase**: Automatically visualizes text layers, composition names, and project properties when projects have no external video footage.
- **📄 Native In-Document Microsoft Office & Document Previews**:
  - **Word (`.docx`, `.doc`, `.rtf`, `.docm`, `.dotx`)**: True in-document multi-page rendering showing actual formatted headings, paragraphs, and tables on a clean A4 document page canvas.
  - **Excel (`.xlsx`, `.xls`, `.csv`, `.xlsm`, `.xlsb`)**: Authentic spreadsheet grid view displaying rows, columns, cell data, A-B-C coordinates, 1-2-3 row numbers, and bottom sheet tabs.
  - **PowerPoint (`.pptx`, `.ppt`, `.pptm`)**: 16:9 widescreen slide canvas displaying slide title, subtitle, and bullet points.
- **🎨 Comprehensive Graphics & Design Support (Modern & Legacy)**:
  - **PSD & PSB**: Adobe Photoshop files (instant composite & layer extraction)
  - **AI (Modern & Legacy v1–v8)**: Adobe Illustrator files (vector-first rasterization at 300 DPI, binary EPS header TIFF extraction for legacy versions, full workspace fallback, and branded overview cards)
  - **EPS**: Encapsulated PostScript (full artwork XMP canvas & binary TIFF previews)
  - **PDF**: Portable Document Format (vector rasterization with multi-page thumbnail sidebar)
  - **Camera RAW**: Ultra-fast embedded previews for DNG, CR2, CR3, NEF, ARW, RAF, ORF, RW2, and 10+ other formats
  - **TIFF & TIF**: Multi-page, 16-bit, and high-dynamic range images
  - **SVG & SVGZ**: Scalable Vector Graphics with GPU rasterization
- **🖼️ Standard & Web Images (Optional, Off by Default)**:
  - **JPEG, PNG, WebP, GIF, ICO, BMP**: Full EXIF orientation, alpha transparency checkerboard, downsampled large photos, and frame count inspection.
  - **User-Controlled**: Unchecked by default in settings so you only preview them when enabled.
- **🎬 Smooth Live Video Playback**: Instant muted looping video previews for **MP4, MKV, MOV, AVI, WMV, WebM, FLV, TS, 3GP** with live progress tracking and resolution badge.
- **📂 Multi-Tab & Blank Space Isolation**: Intelligent cursor containment prevents phantom previews when hovering over empty space or switching between multiple Explorer tabs.
- **⏳ 7-Day Free Unlimited Trial**: Unrestricted access to 100% of all features and formats.
- **🔐 Hardware ID Offline Pro Licensing**: Machine-locked cryptographic activation with zero server dependency.
- **💎 Glassmorphic Floating HUD**: Smooth fade-in animations, format badge color-coding, resolution, color mode, duration, and file size badges.
- **⚡ Multi-Tier Caching**:
  - **L1 In-Memory LRU Cache**: Sub-millisecond instant recall for active browsing
  - **L2 Persistent Disk Cache**: Compressed thumbnail storage with hash-based invalidation
- **⌨️ Interactive Shortcuts & Controls**:
  - `Ctrl + \``: Toggle hover preview **On / Off** globally (system-wide hotkey)
  - `Space`: Pin preview window on screen or Play/Pause live video
  - `Mouse Wheel`: Zoom in / zoom out (50% to 800% for images & documents)
  - `Left-Click + Drag`: Pan smoothly across zoomed canvas
  - `Double-Click`: Reset zoom and pan to 100% default fit
  - `Ctrl + C`: Copy full-resolution preview image to Windows clipboard
  - `Ctrl + O` or `Enter`: Open file in default application
  - `Esc`: Close and dismiss preview immediately
  - `Mouse Hover Away`: Auto-dismiss preview on cursor leave (when unpinned)
- **⚙️ Dual-Tabbed Settings Hub**:
  - `⚙️ Preferences`: Pro license activation, responsiveness slider, autostart toggle, and categorized format checkboxes with crisp vector checkmarks (`✓`)
  - `⌨️ Shortcuts & Controls`: Visual reference cards explaining every shortcut and control
- **📦 Clean Installer**: Installs into `C:\Program Files\RawView` with "Start RawView on Windows boot" pre-checked by default.

---

## 🛠️ Building the Installer

To compile the standalone `RawView_v4.1.2_Setup.exe` installer:

```bash
python build_release.py
```

The installer will be generated and digitally signed in `dist_installer/RawView_v4.1.2_Setup.exe`.

---

## 🔐 Code Signing

RawView release builds are digitally signed with Authenticode certificates. The automated build pipeline in `build_release.py` automatically attaches verified Authenticode signatures to all binaries (`RawView.exe`, `RawViewThumbnailProvider.dll`, and `RawView_v4.1.2_Setup.exe`). The installer automatically provisions the trusted certificate store to guarantee seamless, warning-free installation.
