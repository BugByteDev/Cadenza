[Setup]
AppId=CadenzaLocalComposer
AppName=Cadenza
AppVersion=0.4.0
DefaultDirName={localappdata}\Programs\Cadenza
DefaultGroupName=Cadenza
PrivilegesRequired=lowest
OutputDir=..\build
OutputBaseFilename=Cadenza-Windows-x64-Setup
SetupIconFile=..\dist\assets\icon.ico
UninstallDisplayIcon={app}\Cadenza.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
[Files]
Source: "..\build\package\Cadenza\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Cadenza"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\Launch Cadenza.vbs"""; IconFilename: "{app}\Cadenza.exe"
Name: "{autodesktop}\Cadenza"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\Launch Cadenza.vbs"""; IconFilename: "{app}\Cadenza.exe"
[Run]
Filename: "{sys}\wscript.exe"; Parameters: """{app}\Launch Cadenza.vbs"""; Description: "Launch Cadenza"; Flags: nowait postinstall skipifsilent
