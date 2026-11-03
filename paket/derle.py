"""LOGOS Veli İzin paketini derler, duman sınamasından geçirir ve dağıtım adıyla koyar (LOGOS paket/derle.py'nin sadesi).

Kullanım (depo kökünden; Windows'ta ya da Linux'ta):
    pip install -r requirements.txt pyinstaller pillow
    python paket/derle.py                 # derle + duman sınaması + dağıtım (+ Windows'ta kurulum paketi, Inno Setup varsa)
    python paket/derle.py --sinama-yok --kurulum-yok
Çıktı dist/dagitim/:
    Windows: LOGOS-Veli-Izin.exe           tek dosya; kurulum gerekmez, çift tıkla açılır
             LOGOS-Veli-Izin-kurulum.exe   kurulum paketi (Inno Setup): Başlat menüsü, masaüstü kısayolu, Uygulamalar'da kaldırma
    Linux:   LOGOS-Veli-Izin-linux         yalnız deneme (tarayıcı kipiyle sınama)
GitHub derlemesi (.github/workflows/paket.yml) aynı betiği koşar.
"""
import argparse, hashlib, os, platform, shutil, subprocess, sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
from uygulama.surum import SURUM, DESTEK_EPOSTA, KURULUM_KIMLIGI

SISTEM = platform.system()


def kos(komut, ad, cwd=KOK):
    p = subprocess.Popen(komut, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', cwd=cwd)
    satirlar = []
    for s in p.stdout:
        print(s, end='', flush=True); satirlar.append(s.rstrip())
    if p.wait() != 0: hata(ad, satirlar, p.returncode)


def hata(ad, satirlar, kod=1):
    """GitHub derlemesinde son satırlar açıklama (annotation) olur: günlük okunamasa da sebep görünsün."""
    if os.environ.get('GITHUB_ACTIONS'):
        son = '\n'.join(x for x in satirlar if 'INFO:' not in x)[-10000:]
        for i, parca in enumerate([son[j:j + 3500] for j in range(0, len(son), 3500)] or ['(çıktı yok)'], 1):
            print(f'::error title={ad} başarısız ({i})::' + parca.replace('%', '%25').replace('\r', '').replace('\n', '%0A'), flush=True)
    raise SystemExit(f'{ad} başarısız (çıkış {kod})')


def derle(dist):
    kos([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--distpath', dist, '--workpath', os.path.join(KOK, 'build'),
         os.path.join(KOK, 'paket', 'veli_izin.spec')], 'PyInstaller')
    return os.path.join(dist, 'LOGOS-Veli-Izin.exe' if SISTEM == 'Windows' else 'LOGOS-Veli-Izin')


def ozet(yol):
    h = hashlib.sha256(open(yol, 'rb').read()).hexdigest()
    m = f'{os.path.basename(yol)}: LOGOS Veli İzin {SURUM}, {os.path.getsize(yol) / 1e6:.1f} MB, sha256 {h}'
    print('dağıtım:', m, flush=True)
    if os.environ.get('GITHUB_ACTIONS'): print(f'::notice title=Paket::{m}', flush=True)


def iscc_yolu():
    adaylar = [shutil.which('ISCC')] + [os.path.join(os.environ.get(k, ''), 'Inno Setup 6', 'ISCC.exe')
                                         for k in ('ProgramFiles(x86)', 'ProgramFiles', 'LOCALAPPDATA')]
    return next((y for y in adaylar if y and os.path.exists(y)), None)


def kurulum_paketi(tek, hedef):
    if SISTEM != 'Windows': return None
    iscc = iscc_yolu()
    if not iscc:
        if os.environ.get('GITHUB_ACTIONS'): hata('kurulum paketi', ['Inno Setup (ISCC.exe) bulunamadı'])
        print('Inno Setup yok: kurulum paketi atlandı', flush=True); return None
    from PIL import Image
    ico = os.path.join(KOK, 'build', 'simge.ico'); os.makedirs(os.path.dirname(ico), exist_ok=True)
    Image.open(os.path.join(KOK, 'paket', 'simge.png')).convert('RGBA').save(ico, sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    kos([iscc, f'/DSURUM={SURUM}', f'/DKIMLIK={KURULUM_KIMLIGI}', f'/DDESTEK={DESTEK_EPOSTA}', f'/DKAYNAK={hedef}', f'/DSIMGE={ico}',
         f'/O{hedef}', os.path.join(KOK, 'paket', 'kurulum.iss')], 'Inno Setup')
    y = os.path.join(hedef, 'LOGOS-Veli-Izin-kurulum.exe')
    if not os.path.exists(y): hata('kurulum paketi', [f'{y} oluşmadı'])
    ozet(y); return y


def main():
    a = argparse.ArgumentParser(description='LOGOS Veli İzin paketini derler')
    a.add_argument('--sinama-yok', action='store_true'); a.add_argument('--kurulum-yok', action='store_true'); a.add_argument('--dist')
    a = a.parse_args()
    dist = os.path.abspath(a.dist or os.path.join(KOK, 'dist'))
    paket = derle(dist)
    if not a.sinama_yok:
        ek = ['--pencere'] if os.environ.get('LV_PENCERE_DENE') else []
        kos([sys.executable, os.path.join(KOK, 'paket', 'duman.py'), paket, '--surum', SURUM] + ek, 'duman sınaması')
    hedef = os.path.join(dist, 'dagitim'); os.makedirs(hedef, exist_ok=True)
    tek = os.path.join(hedef, 'LOGOS-Veli-Izin.exe' if SISTEM == 'Windows' else 'LOGOS-Veli-Izin-linux')
    shutil.copy2(paket, tek); ozet(tek)
    if not a.kurulum_yok: kurulum_paketi(tek, hedef)


if __name__ == '__main__':
    main()
