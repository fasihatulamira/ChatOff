#define MyAppSource "."

[Setup]
AppName=ChatOff AI
AppVersion=2.2
DefaultDirName={autopf}\ChatOff AI
DefaultGroupName=ChatOff AI
OutputDir=Installer
OutputBaseFilename=ChatOff_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
Source: "{#MyAppSource}\dist\app.exe"; DestDir: "{app}"; DestName: "ChatOff.exe"; Flags: ignoreversion
Source: "{#MyAppSource}\.env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyAppSource}\schema.sql"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyAppSource}\SETUP.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyAppSource}\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\ChatOff AI"; Filename: "{app}\ChatOff.exe"
Name: "{autoprograms}\ChatOff Setup Guide"; Filename: "{app}\SETUP.txt"
Name: "{autodesktop}\ChatOff AI"; Filename: "{app}\ChatOff.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "powershell.exe"; Parameters: "-WindowStyle Hidden -Command ""Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile '{tmp}\OllamaSetup.exe'"""; StatusMsg: "Downloading Ollama..."; Flags: runhidden waituntilterminated
Filename: "{tmp}\OllamaSetup.exe"; StatusMsg: "Installing Ollama..."; Flags: waituntilterminated shellexec
Filename: "{localappdata}\Programs\Ollama\ollama.exe"; Parameters: "pull llama3.2:3b"; StatusMsg: "Downloading llama3.2:3b..."; Flags: waituntilterminated
Filename: "{localappdata}\Programs\Ollama\ollama.exe"; Parameters: "pull nomic-embed-text"; StatusMsg: "Downloading nomic-embed-text..."; Flags: waituntilterminated
Filename: "powershell.exe"; Parameters: "-Command ""if (-not (Test-Path '{app}\.env')) {{ Copy-Item '{app}\.env.example' '{app}\.env' }}"""; StatusMsg: "Creating .env..."; Flags: runhidden waituntilterminated
Filename: "{app}\ChatOff.exe"; Description: "Launch ChatOff AI"; Flags: nowait postinstall skipifsilent
