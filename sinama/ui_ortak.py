"""Arayüz sınamalarının ortak parçası: tarayıcı kipinde sunucu, geçici kasa, Playwright sayfası, ekran görüntüsü.

Her arayüz sınaması `python sinama/ui_<ad>.py [ekran_klasoru]` ile koşar; klasör verilirse adımların görüntüsü oraya yazılır.
Sunucu LV_AYAR_KLASORU ile geçici klasöre yazar (gerçek kasaya dokunmaz); kapanınca klasör silinir.
"""
import os, shutil, socket, subprocess, sys, tempfile, time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
SIFRE = '2468'


def bos_kapi():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


class Sunucu:
    """with Sunucu() as s: s.adres ..."""
    def __init__(self, kasa_var=False, bugun=None):
        self.klasor = tempfile.mkdtemp(prefix='lv-ui-'); self.kapi = bos_kapi(); self.adres = f'http://127.0.0.1:{self.kapi}'
        self.kasa = os.path.join(self.klasor, 'sinama.lvk'); self.bugun = bugun; self.p = None

    def __enter__(self):
        env = dict(os.environ, LV_AYAR_KLASORU=self.klasor, LV_SINAMA='1', PYTHONIOENCODING='utf-8')
        if self.bugun: env['LV_BUGUN'] = self.bugun
        self.p = subprocess.Popen([sys.executable, '-m', 'uygulama.ana', '--tarayici', str(self.kapi), '--kasa', self.kasa], cwd=KOK, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for _ in range(100):
            try: socket.create_connection(('127.0.0.1', self.kapi), timeout=.2).close(); return self
            except OSError: time.sleep(.1)
        raise RuntimeError('sunucu açılmadı: ' + (self.p.stdout.read().decode('utf-8', 'replace') if self.p.stdout else ''))

    def __exit__(self, *a):
        if self.p: self.p.kill(); self.p.wait()
        shutil.rmtree(self.klasor, ignore_errors=True)

    def ornek_pdfler(self, fotograf=True):
        from sinama import eokul_ornek
        return eokul_ornek.uret(os.path.join(self.klasor, 'ornek'), fotograf)


class Ekran:
    def __init__(self, klasor=None):
        self.klasor = klasor; self.n = 0
        if klasor: os.makedirs(klasor, exist_ok=True)

    def al(self, sayfa, ad):
        if not self.klasor: return
        self.n += 1; sayfa.screenshot(path=os.path.join(self.klasor, f'{self.n:02d}-{ad}.png'), full_page=False)


def tarayici(pw, genis=1360, yuksek=860):
    b = pw.chromium.launch(); ctx = b.new_context(viewport={'width': genis, 'height': yuksek}, locale='tr-TR', device_scale_factor=1)
    sayfa = ctx.new_page(); hatalar = []
    sayfa.on('pageerror', lambda e: hatalar.append(str(e)))
    sayfa.on('console', lambda m: hatalar.append(m.text) if m.type == 'error' else None)
    sayfa._hatalar = hatalar
    return b, sayfa


def kurulum(sayfa, ekran, pdf_yolu=None, okul_ad='Çınar Mesleki ve Teknik Anadolu Lisesi'):
    """İlk açılış: dört adım, kasa kurulur, kurtarma anahtarı döner."""
    sayfa.wait_for_selector('#kurulum:not([hidden])')
    ekran.al(sayfa, 'kurulum-hos-geldiniz')
    sayfa.click('text=Başlayalım')
    if pdf_yolu:
        sayfa.click('text=e-Okul PDF\'inden doldur')
        sayfa.fill('#kPdfYolInput', pdf_yolu); sayfa.click('#kPdfYol button')
        sayfa.wait_for_function("document.getElementById('kOkulAd').value.length > 5")
    else:
        sayfa.fill('#kOkulAd', okul_ad); sayfa.fill('#kIlce', 'Konak')
    ekran.al(sayfa, 'kurulum-okul')
    sayfa.click('text=Devam')
    sayfa.fill('#kSifre', SIFRE); sayfa.fill('#kSifre2', SIFRE)
    ekran.al(sayfa, 'kurulum-sifre')
    sayfa.click('#kKur')
    sayfa.wait_for_selector('#kAnahtar:not(:empty)')
    anahtar = sayfa.get_attribute('#kAnahtar', 'data-k')
    ekran.al(sayfa, 'kurulum-anahtar')
    sayfa.check('#kOnay'); sayfa.click('#kBitir')
    sayfa.wait_for_selector('#ana:not([hidden])')
    return anahtar


def kilit_ac(sayfa, sifre=SIFRE):
    sayfa.wait_for_selector('#kilit:not([hidden])'); sayfa.fill('#kltSifre', sifre); sayfa.click('#kltAc')
    sayfa.wait_for_selector('#ana:not([hidden])')


def eokul_aktar(sayfa, ekran, yollar, fotograf=True):
    sayfa.click('aside button[data-sayfa=ogrenciler]')
    sayfa.wait_for_selector('#eoYollar:not([hidden])')
    sayfa.fill('#eoYolMetin', '\n'.join(yollar))
    if fotograf: sayfa.check('#eoFoto')
    else: sayfa.uncheck('#eoFoto')
    sayfa.click('#eoSec')
    sayfa.wait_for_selector('#eoSonuc table', timeout=60000)
    ekran.al(sayfa, 'eokul-okundu')
    sayfa.click('#eoSonuc button:has-text("Kasaya yaz")')
    sayfa.wait_for_selector('#ogTablo table')
    ekran.al(sayfa, 'ogrenciler')


def hatalari_denetle(sayfa):
    h = [x for x in sayfa._hatalar if 'favicon' not in x]
    assert not h, 'tarayıcı hataları: ' + ' | '.join(h)
