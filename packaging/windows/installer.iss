#ifndef Edition
  #error Edition must be defined as full or lite
#endif
#ifndef Architecture
  #error Architecture must be defined as arm64 or amd64
#endif
#ifndef AppVersion
  #error AppVersion must be defined
#endif
#ifndef SourceDir
  #error SourceDir must be defined
#endif
#ifndef OutputDir
  #error OutputDir must be defined
#endif
#ifndef IconFile
  #error IconFile must be defined
#endif

#define MyAppPublisher "Offline File Converter"

#if Edition == "full"
  #define MyAppName "Offline File Converter"
  #define MyAppId "{{7BEBE4C2-C5CF-4D7C-A88C-25F0E41392B3}"
  #define MyAppExeName "OfflineFileConverter.exe"
#else
  #define MyAppName "Offline File Converter Lite"
  #define MyAppId "{{D0FB40FE-359E-4C93-BE0C-A30F04148E3F}"
  #define MyAppExeName "OfflineFileConverterLite.exe"
#endif

#if Architecture == "arm64"
  #define MyArchitectureName "arm64"
  #define MyArchitecturesAllowed "arm64"
  #define MyArchitecturesInstallIn64BitMode "arm64"
  #define MyMinVersion "10.0.22000"
#else
  #define MyArchitectureName "amd64"
  #define MyArchitecturesAllowed "x64os"
  #define MyArchitecturesInstallIn64BitMode "x64os"
  #define MyMinVersion "10.0.17763"
#endif

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#AppVersion}
ArchitecturesAllowed={#MyArchitecturesAllowed}
ArchitecturesInstallIn64BitMode={#MyArchitecturesInstallIn64BitMode}
MinVersion={#MyMinVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=OfflineFileConverter-{#AppVersion}-{#Edition}-windows-{#MyArchitectureName}-setup
SetupIconFile={#IconFile}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные значки:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName}"; Flags: nowait postinstall skipifsilent
