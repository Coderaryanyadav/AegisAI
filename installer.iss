; Inno Setup Installation Script for Aegis Legal AI Suite (Windows)
; Download Inno Setup Compiler from: https://jrsoftware.org/isdl.php

[Setup]
AppName=Aegis Legal AI Suite
AppVersion=1.0.0
DefaultDirName={autopf}\AegisLegalAI
DefaultGroupName=Aegis Legal AI Suite
OutputDir=dist
OutputBaseFilename=AegisLegalAI_Setup
Compression=lzma
SolidCompression=yes
DisableProgramGroupPage=yes
; PrivilegesRequired=admin allows installing into Program Files directory
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\AegisLegalAI\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Aegis Legal AI"; Filename: "{app}\AegisLegalAI.exe"
Name: "{autodesktop}\Aegis Legal AI"; Filename: "{app}\AegisLegalAI.exe"; Tasks: desktopicon

[Run]
Description: "{cm:LaunchProgram,Aegis Legal AI}"; Filename: "{app}\AegisLegalAI.exe"; Flags: nowait postinstall skipifsilent
