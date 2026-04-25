[Setup]
AppName=ChatOff AI
AppVersion=1.0
DefaultDirName={autopf}\ChatOff AI
DefaultGroupName=ChatOff AI
OutputDir=C:\Users\USER\ChatOff\Installer
OutputBaseFilename=ChatOff_Setup
Compression=lzma
SolidCompression=yes
; Run as normal user so it can install Ollama to the user's AppData safely
PrivilegesRequired=lowest

[Files]
; This takes your app.exe and renames it to ChatOff.exe during install
Source: "C:\Users\USER\ChatOff\dist\app.exe"; DestDir: "{app}"; DestName: "ChatOff.exe"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\ChatOff AI"; Filename: "{app}\ChatOff.exe"
Name: "{autodesktop}\ChatOff AI"; Filename: "{app}\ChatOff.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
; Step 1: Download the Ollama Installer directly from the website in the background
Filename: "powershell.exe"; Parameters: "-WindowStyle Hidden -Command ""Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile '{tmp}\OllamaSetup.exe'"""; StatusMsg: "Downloading Ollama AI Engine..."; Flags: runhidden waituntilterminated

; Step 2: Run the Ollama Installer and wait for the friend to click through it
Filename: "{tmp}\OllamaSetup.exe"; StatusMsg: "Installing Ollama... Please complete the Ollama setup window if it appears."; Flags: waituntilterminated shellexec

; Step 3: Use Ollama to download the Llama3 model
Filename: "{localappdata}\Programs\Ollama\ollama.exe"; Parameters: "pull llama3"; StatusMsg: "Downloading AI Model (llama3). This may take a few minutes..."; Flags: waituntilterminated

; Step 4: Add the launch checkbox at the very end
Filename: "{app}\ChatOff.exe"; Description: "Launch ChatOff AI"; Flags: nowait postinstall skipifsilent
