; UI-for-ytdlp Windows installer (Inno Setup 6).
; CI/local: scripts/package-windows-installer.ps1

#ifndef MyAppVersion
  #define MyAppVersion "0.3.1"
#endif
#ifndef ReleaseDir
  #define ReleaseDir "..\..\dist"
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif

#define MyAppName "UI-for-ytdlp"
#define MyAppExeName "UI-for-ytdlp.exe"
#define MyAppPublisher "Jawerka"
#define MyAppUrl "https://github.com/Jawerka/shell-for-ytdlp"

[Setup]
AppId={{A7C3E9F2-4B1D-4E8A-9C5F-2D6B8A1E4F30}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppUrl}
AppSupportURL={#MyAppUrl}
AppUpdatesURL={#MyAppUrl}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=UI-for-ytdlp-{#MyAppVersion}-windows-x64-setup
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
CloseApplications=force

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#ReleaseDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
