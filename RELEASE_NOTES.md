# 🚀 RawView v3.1.2 Release Notes

**RawView v3.1.2** delivers a refined preview experience for **Office Documents** and **Adobe Video Projects**, strictly eliminating generic/inverted application icons in favor of true embedded slide media and rich Creative Cloud info cards with deep document metadata.

---

## 🌟 What's New in v3.1.2

### 🎯 1. Eliminated Generic Application Icon Fallbacks
* **Strict Visual Thumbnail Validation (`SIIGBF_THUMBNAILONLY`)**: Windows Shell image provider is now queried strictly for real visual page/slide thumbnails. Generic file association icons (such as upside-down Ae icons or blank paper icons) are blocked from display.
* **Embedded Slide & Document Media Extraction**: Office files (`.docx`, `.pptx`) automatically inspect embedded slide images and graphics if standalone thumbnails are not stored by Office.
* **High-Definition Creative Cloud & Office Cards**: When no visual thumbnail exists, RawView displays a dark branded overview card showing file name, sequence/document title, author, slide/sheet count, and file statistics.

---

# 🚀 RawView v3.1.1 Release Notes

### 📄 1. Microsoft Office & Document Previews
* **Microsoft Word (`.docx`, `.doc`, `.docm`, `.dotx`, `.dot`, `.rtf`)**: Zero-lag embedded OpenXML thumbnail extraction with page count, word count, document title, and author information.
* **Microsoft Excel (`.xlsx`, `.xls`, `.xlsm`, `.xlsb`, `.xltx`, `.csv`)**: Instant spreadsheet previews displaying workbook title, sheet names (`Summary`, `Revenue`, etc.), and structural metadata.
* **Microsoft PowerPoint (`.pptx`, `.ppt`, `.pptm`, `.ppsx`, `.potx`)**: Slide deck overview showing slide counts, presentation titles, and high-resolution slide thumbnails.

### 🎬 2. Adobe Video & Motion Graphics Projects
* **Adobe After Effects (`.aep`, `.aet`, `.aepx`)**: Hardware-accelerated shell thumbnail rendering with composition structure and file statistics.
* **Adobe Premiere Pro (`.prproj`, `.prset`)**: Compressed project header inspector extracting project version, active sequence names, and video format information.

### ⚙️ 3. Redesigned Scrollable Settings Hub
* **Categorized Format Preferences**: Dedicated control groups for **Graphics & Design**, **Microsoft Office & Documents**, **Adobe Video Projects**, and **Live Video Playback**.
* **Responsive Scroll Viewport**: Settings dialog now dynamically fits all monitor resolutions with smooth vertical scrolling and sticky action buttons.

---

# 🚀 RawView v2.0.5 Release Notes

### 📂 1. Comprehensive Windows 11 Multi-Tab Support
- **Full Tab Discovery**: Fixed an issue where open tabs sharing the same top-level Explorer window handle would cause non-primary tabs to fail resolution.
- **Unified Tab Candidate Search**: All folder paths belonging to open tabs in the active window are dynamically discovered and queried, guaranteeing instant previews regardless of which tab is active.

---

# 🚀 RawView v2.0.4 Release Notes

### ⚡ 1. Resilient Hover Dwell & Resolution Engine
- **Fixed Hover State Lock**: Resolved an issue where hover state checks could prevent subsequent files from triggering preview popups.
- **Position-Based Settle Detection**: Previews now resolve exactly once per settled cursor position, ensuring instant response across List, Details, Grid, Icons, and Desktop views while maintaining zero UI thread usage during dwell.

---

# 🚀 RawView v2.0.3 Release Notes

### 🎬 1. Ultra-Smooth 60 FPS Live Video Previews
- **Zero Event-Loop Starvation**: Fixed an issue where continuous 35ms UIAutomation and Shell COM queries during mouse dwell starved Qt's event loop, causing dropped frames and stuttering playback.
- **Hardware Direct3D Video Output**: Configured `QVideoWidget` with native opaque hardware paint modes without CSS rasterization bottlenecks.
- **Throttled Repaints & Layout Updates**: Throttled progress bar and timestamp updates to eliminate redundant CPU/GPU drop-shadow blur passes.
- **Sub-Millisecond Thumbnail Resolution**: Instant thumbnail cache lookups (~0.6ms) for immediate preview HUD display before seamless live video stream starts.

---

## 🚀 RawView v2.0.2 Release Notes

### 🎯 1. Fixed Blank Space / Folder Background Hover Bug
- **Precise Item Detection**: Resolved an issue where hovering the cursor over empty whitespace / background areas of a folder window in Windows Explorer would inadvertently trigger a preview if the folder name matched any file inside.
- **Strict Row Containment**: The hover engine now requires the cursor to be directly inside a valid file item (`ListItemControl`, `DataItemControl`, or `TreeItemControl`). Moving into blank background space immediately dismisses any active preview without ghosting or lingering previews.

---

### ⏳ 2. 7-Day Unlimited Free Trial Engine
- **100% Unrestricted Access**: All features (Photoshop PSD/PSB, Illustrator AI, EPS, PDF, Camera RAW, TIFF, SVG, Live Video Playback, Deep Zoom) are completely unlocked for the first 7 days.
- **Subtle Trial Countdown**: The footer cleanly displays `⏳ Trial: Xd left`.
- **Glassmorphic Pro Card (Day 8+)**: When the trial concludes, hovering over files displays an upgrade prompt with the customer's Machine Code, bKash payment info, and direct WhatsApp support launcher.

---

### 🔐 3. Hardware ID Machine-Locked 50 TK Offline Licensing
- **Windows MachineGuid Cryptography**: Automatically binds licenses to unique hardware machine codes (`RV-XXXX-XXXX-XXXX`).
- **HMAC-SHA256 Signatures**: Zero server dependency, 100% offline, zero-latency cryptographic verification.
- **Anti-Piracy**: A license key generated for one PC cannot be shared or used on any other machine.
- **Lifetime Pro**: Once activated, the license persists permanently across app updates and reboots.

---

### 💳 4. Direct bKash & WhatsApp Purchase Integration
- **bKash Personal (50 TK)**: `01756678087` with a 1-click **[📋 Copy bKash]** button.
- **WhatsApp Support**: `+1 (202) 780-6050` with a 1-click **[💬 Open WhatsApp]** button that opens WhatsApp with the customer's Machine Code pre-filled.
- **Settings Dialog Pro Section**: Clean 4-step guide for purchasing, copying codes, and activating license keys.

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

## 📦 Installer Package
- **Installer**: `dist_installer/RawView_v3.1.2_Setup.exe` (~122 MB)
- **Target OS**: Windows 10 & Windows 11 (64-bit)
- **Publisher**: BlackBox THC
