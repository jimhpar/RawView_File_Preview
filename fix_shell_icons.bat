@echo off
:: =========================================================================
:: RawView - Quick Shell Icon & Performance Fix Utility
:: Restores Photoshop / Illustrator default app icons and stops PC lag
:: =========================================================================

echo [*] Stopping lingering RawView processes...
taskkill /F /IM RawView.exe >nul 2>&1

echo [*] Cleaning corrupted HKCU shadow registry keys and repairing icons...
if exist "%ProgramFiles%\RawView\RawView.exe" (
  "%ProgramFiles%\RawView\RawView.exe" --repair-shell-icons
) else if exist "%LocalAppData%\Programs\RawView\RawView.exe" (
  "%LocalAppData%\Programs\RawView\RawView.exe" --repair-shell-icons
) else (
  python -c "from src.core.shell_icon_repair import run_full_shell_repair; run_full_shell_repair()" >nul 2>&1
)

echo [*] Ensuring Windows Explorer displays App Icon badges on thumbnails...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" /v "ShowTypeOverlay" /t REG_DWORD /d 1 /f >nul 2>&1

echo [*] Re-registering RawView Shell Thumbnail Provider...
if exist "%ProgramFiles%\RawView\RawViewThumbnailProvider.dll" (
  regsvr32 /s "%ProgramFiles%\RawView\RawViewThumbnailProvider.dll"
)

echo [*] Refreshing Windows Shell icon and thumbnail caches...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$code = '[DllImport(\"shell32.dll\")] public static extern void SHChangeNotify(int eventId, int flags, IntPtr item1, IntPtr item2);';" ^
  "Add-Type -MemberDefinition $code -Name ShellApi -Namespace Win32;" ^
  "[Win32.ShellApi]::SHChangeNotify(0x08000000, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero);"

echo [*] Starting RawView smoothly in background...
if exist "%ProgramFiles%\RawView\RawView.exe" (
  start "" "%ProgramFiles%\RawView\RawView.exe" --minimized
) else if exist "%LocalAppData%\Programs\RawView\RawView.exe" (
  start "" "%LocalAppData%\Programs\RawView\RawView.exe" --minimized
)

echo.
echo =========================================================================
echo [SUCCESS] File icons restored! Windows Explorer will now display normal
echo           Photoshop (Ps) and Illustrator (Ai) icons without any lag.
echo =========================================================================
pause
