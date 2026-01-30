; Inno Setup Script for Endpoint Security Agent
; Requires Inno Setup 6+: https://jrsoftware.org/isdl.php

#define MyAppName "Endpoint Security Agent"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Your Company"
#define MyAppURL "https://github.com/Sid8050/SystemScheduler"
#define MyAppExeName "EndpointSecurityAgent.exe"

[Setup]
AppId={{8B5E2F3A-1C4D-4E6F-9A8B-0C2D4E6F8A9B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\EndpointSecurity
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=EndpointSecuritySetup
SetupIconFile=assets\shield.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible

; Silent install parameters
; /DASHBOARD_URL=https://your-server:8000

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main executables from PyInstaller dist
Source: "..\dist\EndpointSecurityAgent.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\EndpointSecurityTray.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\RequestUpload.exe"; DestDir: "{app}"; Flags: ignoreversion

; Configuration
Source: "..\config\default_config.yaml"; DestDir: "{commonappdata}\EndpointSecurity"; DestName: "config.yaml"; Flags: onlyifdoesntexist

; Assets
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Request Upload Permission"; Filename: "{app}\RequestUpload.exe"; IconFilename: "{app}\assets\upload.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Request Upload"; Filename: "{app}\RequestUpload.exe"; IconFilename: "{app}\assets\upload.ico"; Tasks: desktopicon

[Run]
; Install and start the Windows service
Filename: "{app}\EndpointSecurityAgent.exe"; Parameters: "install"; StatusMsg: "Installing service..."; Flags: runhidden waituntilterminated
Filename: "{app}\EndpointSecurityAgent.exe"; Parameters: "start"; StatusMsg: "Starting service..."; Flags: runhidden waituntilterminated
; Start system tray (runs at user login)
Filename: "{app}\EndpointSecurityTray.exe"; Description: "Launch system tray"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Stop and uninstall service
Filename: "{app}\EndpointSecurityAgent.exe"; Parameters: "stop"; Flags: runhidden waituntilterminated
Filename: "{app}\EndpointSecurityAgent.exe"; Parameters: "uninstall"; Flags: runhidden waituntilterminated

[Registry]
; Auto-start tray at login
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "EndpointSecurityTray"; ValueData: """{app}\EndpointSecurityTray.exe"""; Flags: uninsdeletevalue

; Store installation path
Root: HKLM; Subkey: "Software\EndpointSecurity"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey

[Code]
var
  DashboardURLPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  // Custom page for dashboard URL
  DashboardURLPage := CreateInputQueryPage(wpSelectDir,
    'Dashboard Configuration', 'Enter the dashboard server URL',
    'Please enter the URL of your Endpoint Security Dashboard server:');
  DashboardURLPage.Add('Dashboard URL:', False);
  DashboardURLPage.Values[0] := 'http://localhost:8000';
end;

function GetDashboardURL(Param: String): String;
begin
  Result := DashboardURLPage.Values[0];
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigPath: String;
  ConfigContent: AnsiString;
begin
  if CurStep = ssPostInstall then
  begin
    // Update config with dashboard URL
    ConfigPath := ExpandConstant('{commonappdata}\EndpointSecurity\config.yaml');
    if LoadStringFromFile(ConfigPath, ConfigContent) then
    begin
      StringChangeEx(ConfigContent, 'http://localhost:8000', DashboardURLPage.Values[0], True);
      SaveStringToFile(ConfigPath, ConfigContent, False);
    end;
  end;
end;

// Handle command line parameters for silent install
function InitializeSetup(): Boolean;
var
  DashboardURL: String;
begin
  Result := True;

  // Check for /DASHBOARD_URL parameter
  if ParamStr(1) <> '' then
  begin
    DashboardURL := GetCmdTail();
    // Parse out DASHBOARD_URL if present
    if Pos('/DASHBOARD_URL=', UpperCase(DashboardURL)) > 0 then
    begin
      // Will be handled in CurStepChanged
    end;
  end;
end;
