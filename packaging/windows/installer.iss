; Inno Setup script for NoRefund — per-user install, no admin rights required.
;
; Build (on Windows, after `pyinstaller packaging/norefund.spec` has produced
; dist/NoRefund/NoRefund.exe):
;   iscc packaging/windows/installer.iss
;
; Output: packaging/windows/dist/NoRefund-Setup-<version>.exe

#define MyAppName "NoRefund"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "PhantomVK"
#define MyAppExeName "NoRefund.exe"
#define MyDistDir "..\..\dist\NoRefund"

[Setup]
AppId={{6C6A6F5E-6E1C-4B7A-9B7B-8B5E7E7C0F1A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=NoRefund-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
