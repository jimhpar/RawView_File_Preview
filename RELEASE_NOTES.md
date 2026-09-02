# 🚀 RawView v2.0.2 Release Notes

**RawView v2.0.2** brings a critical fix for **Windows Explorer Blank Space Hover Filtering**, introduces the **7-Day Unlimited Free Trial Engine**, integrates **Offline Hardware ID Machine-Locked 50 TK Pro Licensing**, and adds direct **bKash & WhatsApp Purchase Support**.

---

## 🌟 What's New in v2.0.2

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
- **Installer**: `dist_installer/RawView_v2.0.2_Setup.exe` (~121.95 MB)
- **Target OS**: Windows 10 & Windows 11 (64-bit)
- **Publisher**: BlackBox THC
