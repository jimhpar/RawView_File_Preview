; Inno Setup Script for RawView v4.2.5
; Installs into C:\Program Files\RawView with Windows Boot Autostart, Code Signing Trust & Context Menus

#define MyAppName "RawView"
#define MyAppVersion "4.2.5"
#define MyAppPublisher "BlackBox THC"
#define MyAppURL "https://github.com/jimhpar/RawView_File_Preview"
#define MyAppExeName "RawView.exe"

[Setup]
AppId={{9C89B1F2-3B45-4E87-8A1C-7F1C99011E2A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoCopyright=Copyright (C) {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist_installer
OutputBaseFilename=RawView_v{#MyAppVersion}_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UsePreviousAppDir=yes
UsePreviousTasks=no
DisableDirPage=auto
DisableProgramGroupPage=auto
UninstallDisplayIcon={app}\{#MyAppExeName}
UpdateUninstallLogAppName=yes
CloseApplications=no
RestartApplications=no
AlwaysRestart=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "autostart"; Description: "&Start RawView automatically when Windows boots"; GroupDescription: "Startup Options:"; Flags: checkedonce
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\RawView\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "RawViewThumbnailProvider.dll"
Source: "..\dist\RawView\RawViewThumbnailProvider.dll"; DestDir: "{app}"; Flags: ignoreversion regserver uninsrestartdelete
Source: "..\assets\app_icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\checkmark.svg"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\ps_badge.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\ai_badge.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\certs\RawView_RootCA.cer"; DestDir: "{app}\certs"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"
Name: "{group}\{#MyAppName} Settings"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--settings"; IconFilename: "{app}\assets\app_icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"; Tasks: desktopicon

[Registry]
; Autostart with Windows Registry entry
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "RawView"; ValueData: """{app}\{#MyAppExeName}"" --minimized"; Flags: uninsdeletevalue; Tasks: autostart

; Disable Windows Explorer ShowTypeOverlay to prevent white paper sheet icon collisions (RawView burns clean high-DPI badges directly)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"; ValueType: dword; ValueName: "ShowTypeOverlay"; ValueData: "0"

; Set DisableProcessIsolation=1: REQUIRED by Windows Explorer to execute IInitializeWithFile and IInitializeWithItem
Root: HKLM; Subkey: "Software\Classes\CLSID\{{78FDF5BA-0E57-4B06-8230-1340EE5EA83B}"; ValueType: dword; ValueName: "DisableProcessIsolation"; ValueData: "1"
Root: HKCU; Subkey: "Software\Classes\CLSID\{{78FDF5BA-0E57-4B06-8230-1340EE5EA83B}"; ValueType: dword; ValueName: "DisableProcessIsolation"; ValueData: "1"

; Windows Explorer Context Menu: Refresh Thumbnails on Directory Background
Root: HKLM; Subkey: "Software\Classes\Directory\Background\shell\RawViewRefreshFolderThumbs"; ValueType: string; ValueData: "Refresh Thumbnails"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Classes\Directory\Background\shell\RawViewRefreshFolderThumbs"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\assets\app_icon.ico"""; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Classes\Directory\Background\shell\RawViewRefreshFolderThumbs\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" --refresh-folder ""%V"""; Flags: uninsdeletekey

; Windows Explorer Context Menu: Refresh Thumbnails on Directory Item
Root: HKLM; Subkey: "Software\Classes\Directory\shell\RawViewRefreshFolderThumbs"; ValueType: string; ValueData: "Refresh Thumbnails"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Classes\Directory\shell\RawViewRefreshFolderThumbs"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\assets\app_icon.ico"""; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Classes\Directory\shell\RawViewRefreshFolderThumbs\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" --refresh-folder ""%1"""; Flags: uninsdeletekey

; Windows Explorer Context Menu: RawView Settings on Directory Background
Root: HKLM; Subkey: "Software\Classes\Directory\Background\shell\RawViewSettings"; ValueType: string; ValueData: "RawView Settings"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Classes\Directory\Background\shell\RawViewSettings"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\assets\app_icon.ico"""; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Classes\Directory\Background\shell\RawViewSettings\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" --settings"; Flags: uninsdeletekey

; Windows Explorer Context Menu: RawView Settings on Directory Item
Root: HKLM; Subkey: "Software\Classes\Directory\shell\RawViewSettings"; ValueType: string; ValueData: "RawView Settings"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Classes\Directory\shell\RawViewSettings"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\assets\app_icon.ico"""; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Classes\Directory\shell\RawViewSettings\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" --settings"; Flags: uninsdeletekey

[Run]
; Auto-repair shell icons and associations in logged-in user context
Filename: "{app}\{#MyAppExeName}"; Parameters: "--repair-shell-icons"; Flags: runhidden runasoriginaluser waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[Code]
const
  MOVEFILE_REPLACE_EXISTING = $1;
  MOVEFILE_DELAY_UNTIL_REBOOT = $4;

function MoveFileEx(lpExistingFileName, lpNewFileName: String; dwFlags: DWORD): Boolean;
  external 'MoveFileExW@kernel32.dll stdcall';

// Terminate running processes before starting uninstall
function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
  DllPath: String;
begin
  Exec('taskkill.exe', '/F /T /IM RawView.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill.exe', '/F /IM dllhost.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  DllPath := ExpandConstant('{app}\RawViewThumbnailProvider.dll');
  if FileExists(DllPath) then
  begin
    Exec('regsvr32.exe', '/u /s "' + DllPath + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec('taskkill.exe', '/F /IM explorer.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Sleep(800);
    Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -Command "if (-not (Get-Process -Name explorer -ErrorAction SilentlyContinue)) { Start-Process explorer.exe }"', '', SW_HIDE, ewNoWait, ResultCode);
  end;
  Sleep(500);
  Result := True;
end;

// Terminate running processes before starting install/upgrade
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/F /T /IM RawView.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill.exe', '/F /IM dllhost.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(600);
  Result := True;
end;

// Guarantee NO restart prompt is ever shown by Inno Setup
function NeedRestart(): Boolean;
begin
  Result := False;
end;

// Lifecycle handler for installation steps
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  CertPath: String;
  DllPath: String;
  OldDllPath: String;
begin
  if CurStep = ssInstall then
  begin
    // Force terminate process tree and give OS time to unmap shared runtime DLLs
    Exec('taskkill.exe', '/F /T /IM RawView.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec('taskkill.exe', '/F /IM dllhost.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Sleep(800);
    
    // If upgrading an existing installation, rename existing DLL to .old so the new DLL can be written immediately
    DllPath := ExpandConstant('{app}\RawViewThumbnailProvider.dll');
    if FileExists(DllPath) then
    begin
      Exec('regsvr32.exe', '/u /s "' + DllPath + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      OldDllPath := DllPath + '.old';
      if FileExists(OldDllPath) then
      begin
        DeleteFile(OldDllPath);
      end;
      // Rename currently mapped DLL to .old (succeeds even if file is locked by Explorer/dllhost!)
      MoveFileEx(DllPath, OldDllPath, MOVEFILE_REPLACE_EXISTING);
      // Schedule .old file to be deleted automatically
      MoveFileEx(OldDllPath, '', MOVEFILE_DELAY_UNTIL_REBOOT);
    end;
  end
  else if CurStep = ssPostInstall then
  begin
    // Install Code Signing Root Certificate into Windows Trusted Root & TrustedPublisher
    CertPath := ExpandConstant('{app}\certs\RawView_RootCA.cer');
    if FileExists(CertPath) then
    begin
      Exec('certutil.exe', '-addstore -f "Root" "' + CertPath + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Exec('certutil.exe', '-addstore -f "TrustedPublisher" "' + CertPath + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    end;

    // Configure ShowTypeOverlay=0 in user profile to prevent white sheet overlay collisions, purge old non-uniform thumb cache & trigger Explorer refresh via PowerShell
    Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -Command "Set-ItemProperty -Path ''HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced'' -Name ''ShowTypeOverlay'' -Value 0 -Type DWord -ErrorAction SilentlyContinue; Remove-Item -Path \"\"$env:LOCALAPPDATA\RawView\cache\thumbs\*\"\" -Force -Recurse -ErrorAction SilentlyContinue; $c=''[DllImport(\""shell32.dll\"")] public static extern void SHChangeNotify(int e, int f, IntPtr a, IntPtr b);''; Add-Type -MemberDefinition $c -Name S -Namespace W; [W.S]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero);"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    // Refresh Windows Explorer seamlessly so newly registered DLL is loaded IMMEDIATELY without PC restart
    Exec('taskkill.exe', '/F /IM explorer.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec('taskkill.exe', '/F /IM dllhost.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Sleep(1000);
    Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -Command "Start-Process explorer.exe"', '', SW_HIDE, ewNoWait, ResultCode);
  end;
end;
