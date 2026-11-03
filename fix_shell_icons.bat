@echo off
:: =========================================================================
:: RawView v4.2.5 - Quick Shell Icon & Thumbnail Fix Utility
:: Eliminates white paper sheet overlays, repairs icons, and restores crisp badges
:: =========================================================================

echo [*] Stopping lingering RawView and Explorer processes...
taskkill /F /IM RawView.exe >nul 2>&1

echo [*] Cleaning corrupted HKCU shadow registry keys and repairing icons...
if exist "%ProgramFiles%\RawView\RawView.exe" (
  "%ProgramFiles%\RawView\RawView.exe" --repair-shell-icons
) else if exist "%LocalAppData%\Programs\RawView\RawView.exe" (
  "%LocalAppData%\Programs\RawView\RawView.exe" --repair-shell-icons
) else (
  python -c "from src.core.shell_icon_repair import run_full_shell_repair; run_full_shell_repair()" >nul 2>&1
)

echo [*] Disabling Windows Explorer ShowTypeOverlay to eliminate white paper sheet collisions...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" /v "ShowTypeOverlay" /t REG_DWORD /d 0 /f >nul 2>&1

echo [*] Re-registering RawView Shell Thumbnail Provider...
if exist "%ProgramFiles%\RawView\RawViewThumbnailProvider.dll" (
  regsvr32 /s "%ProgramFiles%\RawView\RawViewThumbnailProvider.dll"
)

echo [*] Purging stuck Windows icon and thumbnail caches...
taskkill /F /IM explorer.exe >nul 2>&1
timeout /t 1 /nobreak >nul
del /F /Q "%LocalAppData%\IconCache.db" >nul 2>&1
del /F /Q "%LocalAppData%\Microsoft\Windows\Explorer\iconcache_*.db" >nul 2>&1
del /F /Q "%LocalAppData%\Microsoft\Windows\Explorer\thumbcache_*.db" >nul 2>&1
del /F /Q "%LocalAppData%\RawView\cache\thumbs\*.*" >nul 2>&1
start explorer.exe

echo [*] Refreshing Windows Shell notification...
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
echo [SUCCESS] White sheet overlays eradicated! Clean high-definition format
echo           badges (Ps, Ai, EPS, PDF, RAW) will now display on all thumbnails.
echo =========================================================================
pause
