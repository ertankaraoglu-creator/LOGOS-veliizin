"""Açılış görselini (paket/acilis.png, 460x200) üretir: Windows'ta tek dosyalı paket açılırken birkaç saniye görünen pencere (PyInstaller Splash).
LOGOS Disiplin'inkiyle aynı düzen; yalnız uygulamanın adı değişir (03.11.2026: kopyada "Disiplin" yazıyordu, Ertan fark etti).
Kullanım: python paket/acilis_uret.py   (pakete girmez; derlemeden önce bir kez)
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
from uygulama import surum

W, H = 460, 200
UST, ALT = (30, 46, 102), (17, 26, 62)                 # LOGOS'un lacivert geçişi
FONT = os.path.join(KOK, 'uygulama', 'fontlar')


def uret(yol=os.path.join(KOK, 'paket', 'acilis.png'), alt_ad=None):
    alt_ad = alt_ad or surum.AD.replace('LOGOS', '').strip()            # 'Veli İzin'
    im = Image.new('RGB', (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / (H - 1); d.line([(0, y), (W, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(UST, ALT)))
    s = Image.open(os.path.join(KOK, 'paket', 'simge.png')).convert('RGBA').resize((112, 112), Image.LANCZOS)
    im.paste(s, (34, (H - 112) // 2), s)
    kalin = ImageFont.truetype(os.path.join(FONT, 'LiberationSans-Bold.ttf'), 31)
    duz = ImageFont.truetype(os.path.join(FONT, 'LiberationSans-Regular.ttf'), 16)
    kucuk = ImageFont.truetype(os.path.join(FONT, 'LiberationSans-Regular.ttf'), 12)
    d.text((169, 62), 'LOGOS', font=kalin, fill=(255, 255, 255))
    d.text((170, 100), alt_ad, font=duz, fill=(199, 210, 234))
    d.text((169, 133), 'Açılıyor, lütfen bekleyin…', font=kucuk, fill=(143, 157, 194))
    im.save(yol, optimize=True)
    return yol


if __name__ == '__main__':
    print(uret())
