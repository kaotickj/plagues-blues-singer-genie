#define AppName "Plague's Music Studio"
#define AppVersion "0.3.2"
#define AppExe "PlaguesMusicStudio.exe"
[Setup]
AppId={{BE126C53-2C23-4CC8-BC1B-FBFA92E22B9C}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\PlaguesMusicStudio
DefaultGroupName={#AppName}
OutputDir=output
OutputBaseFilename=PlaguesMusicStudio-Setup-{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
[Files]
Source: "..\dist\PlaguesMusicStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch Plague's Music Studio"; Flags: nowait postinstall skipifsilent
