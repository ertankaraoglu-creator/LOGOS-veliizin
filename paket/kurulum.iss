; LOGOS Veli İzin Windows kurulum paketi: LOGOS-Veli-Izin-kurulum.exe (Inno Setup 6; LOGOS A9e'den). paket/derle.py çağırır.
; Kullanıcı başına kurulum (yönetici şifresi gerekmez): %LOCALAPPDATA%\Programs\LOGOS Veli İzin\LOGOS-Veli-Izin.exe; Başlat menüsü
; kısayolu, isteğe bağlı masaüstü kısayolu, Uygulamalar listesinde kaldırma.
; Veli İzin kasası ve belgeler %LOCALAPPDATA%\LOGOS Veli İzin klasöründedir: kaldırmada SİLİNMEZ (okulun öğrenci listesi ve dilekçe kayıtları).
; Dosya UTF-8 (BOM'lu): Inno Setup Türkçe harfleri ancak böyle doğru okur.

#ifndef SURUM
  #error SURUM tanimli degil: ISCC /DSURUM=0.6.0 ...
#endif
#ifndef KIMLIK
  #error KIMLIK tanimli degil
#endif
#ifndef KAYNAK
  #define KAYNAK "..\dist\dagitim"
#endif
#ifndef SIMGE
  #define SIMGE "..\build\simge.ico"
#endif
#ifndef DESTEK
  #define DESTEK "logosddu@gmail.com"
#endif

[Setup]
AppId={{{#KIMLIK}}
AppName=LOGOS Veli İzin
AppVersion={#SURUM}
AppVerName=LOGOS Veli İzin {#SURUM}
AppPublisher=LOGOS
AppCopyright=© 2026 Ertan Karaoğlu
AppPublisherURL=https://dersdagitim.com
AppContact={#DESTEK}
VersionInfoVersion={#SURUM}.0
VersionInfoProductName=LOGOS Veli İzin
VersionInfoDescription=LOGOS Veli İzin kurulumu
VersionInfoCopyright=© 2026 Ertan Karaoğlu
DefaultDirName={localappdata}\Programs\LOGOS Veli İzin
DisableProgramGroupPage=yes
DefaultGroupName=LOGOS Veli İzin
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=LOGOS-Veli-Izin-kurulum
SetupIconFile={#SIMGE}
UninstallDisplayIcon={app}\LOGOS-Veli-Izin.exe
UninstallDisplayName=LOGOS Veli İzin
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ShowLanguageDialog=no

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "masaustu"; Description: "Masaüstüne LOGOS Veli İzin kısayolu koy"; GroupDescription: "Kısayollar:"

[Files]
Source: "{#KAYNAK}\LOGOS-Veli-Izin.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\LOGOS Veli İzin"; Filename: "{app}\LOGOS-Veli-Izin.exe"; Comment: "Veli izin dilekçesi ve öğrenci belgesi"
Name: "{autodesktop}\LOGOS Veli İzin"; Filename: "{app}\LOGOS-Veli-Izin.exe"; Comment: "Veli izin dilekçesi ve öğrenci belgesi"; Tasks: masaustu

[Run]
Filename: "{app}\LOGOS-Veli-Izin.exe"; Description: "LOGOS Veli İzin'i şimdi aç"; Flags: nowait postinstall skipifsilent
