#define AppName "Plague's Blues Singer Genie"
#define AppVersion "0.1.1"
#define AppExe "PlaguesBluesSingerGenie.exe"
[Setup]
AppId={{BE126C53-2C23-4CC8-BC1B-FBFA92E22B9C}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\PlaguesBluesSingerGenie
DefaultGroupName={#AppName}
OutputDir=output
OutputBaseFilename=PlaguesBluesSingerGenie-Setup-{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
[Files]
Source: "..\dist\PlaguesBluesSingerGenie\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch Plague's Blues Singer Genie"; Flags: nowait postinstall skipifsilent
