; Inno Setup Script for RawView v4.1.2
; Installs into C:\Program Files\RawView with Windows Boot Autostart, Code Signing Trust & Context Menus

#define MyAppName "RawView"
#define MyAppVersion "4.1.2"
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
CloseApplications=yes
CloseApplicationsFilter=RawView.exe
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "autostart"; Description: "&Start RawView automatically when Windows boots"; GroupDescription: "Startup Options:"; Flags: checkedonce
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\RawView\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\RawView\RawViewThumbnailProvider.dll"; DestDir: "{app}"; Flags: ignoreversion regserver restartreplace
Source: "..\assets\app_icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\checkmark.svg"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\certs\RawView_RootCA.cer"; DestDir: "{app}\certs"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\app_icon.ico"; Tasks: desktopicon

[Registry]
; Autostart with Windows Registry entry
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "RawView"; ValueData: """{app}\{#MyAppExeName}"" --minimized"; Flags: uninsdeletevalue; Tasks: autostart

; Enable App Badges (Ps, Ai, PDF icon overlay) on thumbnails in Windows Explorer
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"; ValueType: dword; ValueName: "ShowTypeOverlay"; ValueData: "1"; Flags: uninsneveruninstall

; Windows Explorer Context Menu: Refresh Thumbnails on Directory Background
Root: HKLM; Subkey: "Software\Classes\Directory\Background\shell\RawViewRefreshFolderThumbs"; ValueType: string; ValueData: "Refresh Thumbnails"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Classes\Directory\Background\shell\RawViewRefreshFolderThumbs"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\assets\app_icon.ico"""; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Classes\Directory\Background\shell\RawViewRefreshFolderThumbs\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" --refresh-folder ""%V"""; Flags: uninsdeletekey

; Windows Explorer Context Menu: Refresh Thumbnails on Directory Item
Root: HKLM; Subkey: "Software\Classes\Directory\shell\RawViewRefreshFolderThumbs"; ValueType: string; ValueData: "Refresh Thumbnails"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Classes\Directory\shell\RawViewRefreshFolderThumbs"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\assets\app_icon.ico"""; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Classes\Directory\shell\RawViewRefreshFolderThumbs\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" --refresh-folder ""%1"""; Flags: uninsdeletekey

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[Code]
// Terminate running RawView process before starting uninstall
function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/F /IM RawView.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(250);
  Result := True;
end;

// Terminate running RawView process before starting install/upgrade
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/F /IM RawView.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(250);
  Result := True;
end;

// Lifecycle handler for installation steps
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  CertPath: String;
begin
  if CurStep = ssInstall then
  begin
    Exec('taskkill.exe', '/F /IM RawView.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Sleep(300);
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
  end;
end;
