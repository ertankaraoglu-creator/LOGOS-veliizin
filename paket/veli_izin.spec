# -*- mode: python ; coding: utf-8 -*-
"""LOGOS Veli İzin paketi (PyInstaller 6; LOGOS Disiplin'in disiplin.spec'inden): Windows'ta tek LOGOS-Veli-Izin.exe, Linux'ta (deneme) tek dosya.

Kullanım (depo kökünden):  pip install -r requirements.txt pyinstaller && pyinstaller --noconfirm paket/veli_izin.spec
(ya da python paket/derle.py: derler, duman sınamasından geçirir, dağıtım adıyla koyar)

Pakete giren: uygulama/ (Python modülleri), uygulama/arayuz.html, uygulama/fontlar (belgelerin yazı tipi), veri/tatiller.json.
Girmeyen: sinama/, raporlar/, gizli/ (gerçek veri asla), kasa dosyaları.
"""
import os, sys, platform
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

KOK = os.path.dirname(SPECPATH)
sys.path.insert(0, KOK)

SISTEM = platform.system()
SIMGE = os.path.join(KOK, 'paket', 'simge.png')

a = Analysis(
    [os.path.join(KOK, 'paket', 'veli_izin.py')],
    pathex=[KOK],
    binaries=[],
    datas=[(os.path.join(KOK, 'uygulama', 'arayuz.html'), 'uygulama'),
           (os.path.join(KOK, 'uygulama', 'fontlar'), os.path.join('uygulama', 'fontlar')),
           (os.path.join(KOK, 'veri', 'tatiller.json'), 'veri')]
          + collect_data_files('pdfplumber') + collect_data_files('pypdfium2'),
    hiddenimports=collect_submodules('uygulama') + collect_submodules('reportlab') + ['cryptography.hazmat.primitives.ciphers.aead',
                   'cryptography.hazmat.primitives.kdf.scrypt', 'pdfplumber', 'pdfminer', 'pypdfium2'],
    # pypdfium2 KALIR (Disiplin'de atılıyordu): e-Okul listesinden fotoğraf kırpmak sayfayı resme çevirir (eokul._foto, to_image)
    excludes=['tkinter', 'matplotlib', 'IPython', 'notebook', 'pytest', 'playwright', 'numpy', 'pandas'],
    noarchive=False,
)
# Paket küçülsün (sohbete gönderme sınırı 30 MiB). Atılanlar uygulamada hiç yüklenmiyor: Pillow'un AVIF / WebP / renk profili / yazı tipi
# eklentileri (logo ve fotoğraf yalnız PNG / JPEG; reportlab yazı tipini kendisi okur), pdfminer'ın Çince / Japonca / Korece tabloları.
ATILAN = ('_avif', '_webp.', '_imagingcms', '_imagingft')
a.binaries = [b for b in a.binaries if not any(x in b[0] for x in ATILAN)]
a.datas = [d for d in a.datas if not d[0].replace('\\', '/').startswith('pdfminer/cmap/')]
pyz = PYZ(a.pure)
# Tek dosya açılırken (birkaç saniye) hemen bir açılış görseli: kullanıcı "açılmadı" sanıp ikinci kez çift tıklamasın.
# Pencere görününce kapanır (uygulama/ana.py _acilis_kapat).
ACILIS = [Splash(os.path.join(KOK, 'paket', 'acilis.png'), binaries=a.binaries, datas=a.datas, text_pos=None, always_on_top=False)] if SISTEM == 'Windows' else []
exe = EXE(pyz, a.scripts, a.binaries, a.datas, *ACILIS, *[x.binaries for x in ACILIS], [], name='LOGOS-Veli-Izin',
          console=(SISTEM != 'Windows'), icon=SIMGE, upx=False, version=None)
