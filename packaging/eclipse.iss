; Eclipse Windows installer (Inno Setup 6). Built by .github/workflows/windows-installer.yml.
; Installs Eclipse into a folder on the Desktop and puts an Eclipse shortcut on the Desktop.
#define AppName "Eclipse"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{6B0E4C1A-6E2B-4C7E-9A8E-3C11F5E00001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Eclipse
DefaultDirName={userdesktop}\Eclipse
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist-installer
OutputBaseFilename=EclipseSetup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\Eclipse.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "ollama"; Description: "Install Ollama (runs the AI model locally) if it is missing"; GroupDescription: "Extras:"
Name: "tune"; Description: "Tune Ollama for an 8 GB GPU (one model in VRAM, small context cache)"; GroupDescription: "Extras:"

[Files]
Source: "..\dist\Eclipse\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{userdesktop}\Eclipse"; Filename: "{app}\Eclipse.exe"; IconFilename: "{app}\Eclipse.exe"; Comment: "Eclipse - local AI dev workbench"
Name: "{userprograms}\Eclipse"; Filename: "{app}\Eclipse.exe"

[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "OLLAMA_MAX_LOADED_MODELS"; ValueData: "1"; Tasks: tune
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "OLLAMA_NUM_PARALLEL"; ValueData: "1"; Tasks: tune
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "OLLAMA_FLASH_ATTENTION"; ValueData: "1"; Tasks: tune
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "OLLAMA_KV_CACHE_TYPE"; ValueData: "q4_0"; Tasks: tune

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {{ winget install -e --id Ollama.Ollama --accept-source-agreements --accept-package-agreements }"""; StatusMsg: "Installing Ollama..."; Flags: runhidden waituntilterminated; Tasks: ollama
Filename: "{app}\Eclipse.exe"; Description: "Start Eclipse"; Flags: nowait postinstall skipifsilent
