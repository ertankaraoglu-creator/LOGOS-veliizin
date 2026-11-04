"""Paketin duman sınaması: derlenmiş LOGOS Veli İzin'i (tek dosya) açar ve bütün iş akışını paketin içinde dener.

    python paket/duman.py dist/LOGOS-Veli-Izin[.exe] [--surum 0.1.1] [--pencere]

Tarayıcı kipi (geçici ayar klasörü, LV_SINAMA: yazıcıya gönderilmez, PDF açılmaz): sürüm → kasa → e-Okul (uydurma okulun PDF'leri,
fotoğraflı: pypdfium2 pakette mi) → öğrenci arama → okul logosu → dilekçe (devamsızlık bölümü, kayıt no) → yeniden yazdır → öğrenci
belgesi → istatistik ve CSV → kilit, yanlış şifre, doğru şifre → kasada açık veri yok.
--pencere (Windows): pencere açılır, arayüz Python'a bağlanır (WebView2), ikinci açılış birinciyi öne getirip çıkar, pencere kapanır.
Gerçek öğrenci verisi kullanılmaz (sinama/eokul_ornek.py).
"""
import argparse, base64, datetime, io, json, os, shutil, socket, subprocess, sys, tempfile, time, urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
SIFRE = '2468'


def bos_kapi():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def ortam(klasor, **ek):
    e = dict(os.environ, LV_AYAR_KLASORU=klasor, LV_SINAMA='1', PYTHONIOENCODING='utf-8')
    e.pop('LV_PENCERE_SINA', None); e.update(ek); return e


class Paket:
    def __init__(self, exe, klasor):
        self.exe, self.klasor, self.kapi = exe, klasor, bos_kapi(); self.p = None

    def __enter__(self):
        self.p = subprocess.Popen([self.exe, '--tarayici', str(self.kapi), '--kasa', os.path.join(self.klasor, 'duman.lvk')], env=ortam(self.klasor),
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        son = time.time() + 120                                         # tek dosya ilk açılışta geçici klasöre açılır
        while time.time() < son:
            if self.p.poll() is not None: raise SystemExit(f'paket açılır açılmaz kapandı (çıkış {self.p.returncode}); günlük: {self.gunluk()}')
            try: socket.create_connection(('127.0.0.1', self.kapi), timeout=.5).close(); return self
            except OSError: time.sleep(.5)
        raise SystemExit('paket 120 sn içinde açılmadı; günlük: ' + self.gunluk())

    def __exit__(self, *a):
        kapat(self.p)

    def gunluk(self):
        try:
            with open(os.path.join(self.klasor, 'gunluk.txt'), encoding='utf-8') as f: return f.read()[-2000:]
        except OSError: return '(yok)'

    def __call__(self, ad, *args):
        r = urllib.request.Request(f'http://127.0.0.1:{self.kapi}/api/{ad}', data=json.dumps(args).encode(), method='POST',
                                   headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(r, timeout=120) as y: return json.loads(y.read())


def kapat(p):
    """Paketi bütünüyle kapatır. Windows'ta tek dosyalı exe bir alt süreç açar: yalnız üsttekini öldürmek alttakini (exe'yi tutan) bırakır,
    kaldırıcı dosyayı silemez (03.11.2026 GitHub derlemesi). Süreç ağacı taskkill /T ile kapanır."""
    if not p or p.poll() is not None: return
    if sys.platform == 'win32': subprocess.run(['taskkill', '/F', '/T', '/PID', str(p.pid)], capture_output=True)
    else: p.kill()
    try: p.wait(15)
    except subprocess.TimeoutExpired: pass


def iyi(kosul, ne):
    if not kosul:
        if os.environ.get('GITHUB_ACTIONS'): print(f'::error title=Duman sınaması::{ne}', flush=True)
        raise SystemExit('DUMAN BAŞARISIZ: ' + ne)
    print('  tamam:', ne, flush=True)


def pdf_metni(yol):
    try: import pdfplumber
    except ImportError: return None
    with pdfplumber.open(yol) as p: return '\n'.join((s.extract_text(x_tolerance=1.5) or '') for s in p.pages), sum(len(s.images) for s in p.pages)


def okul_gunleri(n, bugun):
    """Bugünden geriye n okul günü (dilekçe geriye dönük)."""
    from uygulama import isgunu
    d = bugun; out = []
    while len(out) < n:
        d -= datetime.timedelta(days=1)
        if isgunu.okul_gunu(d): out.append(d.isoformat())
    return sorted(out)


def tarayici_sinamasi(exe, surum):
    from sinama import eokul_ornek
    from uygulama import isgunu
    k = tempfile.mkdtemp(prefix='lv-duman-')
    try:
        pdf = eokul_ornek.uret(os.path.join(k, 'ornek'), True)
        with Paket(exe, k) as A:
            b = A('baslangic'); iyi(not b.get('kasa_var') and (not surum or b.get('surum') == surum), f"açıldı, sürüm {b.get('surum')}, kasa yok")
            r = A('kasa_olustur', {'ad': 'Çınar Mesleki Ve Teknik Anadolu Lisesi', 'il': 'İzmir', 'ilce': 'Konak', 'kurum_kodu': '123456'}, SIFRE)
            iyi(r.get('ok') and len(r.get('kurtarma') or '') == 39, 'kasa kuruldu, kurtarma anahtarı verildi'); kurtarma = r['kurtarma']
            r = A('eokul_oku', [pdf['9A'], pdf['10B'], pdf['AL'], pdf['kimlik']], True)
            iyi(r.get('ok') and r['ozet']['yeni'] == 24 and r['ozet']['foto'] == 23 and r['ozet']['tc'] == 18, f"e-Okul okundu: {r.get('ozet') or r}")
            iyi(A('eokul_aktar').get('ok'), 'kasaya aktarıldı')
            iyi([x['no'] for x in A('ara', 'cigdem')['sonuc']] == [902], 'Türkçe harfsiz arama')
            o = A('ogrenci', 902)['ogrenci']; iyi(o['foto'] and o['foto'].startswith('data:image/jpeg'), 'fotoğraf paketin içinde kırpıldı')
            from PIL import Image
            bb = io.BytesIO(); Image.new('RGBA', (200, 200), (20, 60, 160, 255)).save(bb, 'PNG')
            iyi(A('okul_logo_yukle', 'data:image/png;base64,' + base64.b64encode(bb.getvalue()).decode()).get('ok'), 'okul logosu yüklendi')
            bugun = isgunu.bugun(); g = okul_gunleri(2, bugun)
            izin = {'ogrenci_no': 902, 'tarih': bugun.isoformat(), 'veli': {'ad': 'EMİNE YILDIRIM', 'yakinlik': 'Anne', 'kayitli': True},
                    'gunler': {g[0]: 'tam', g[1]: 'sonra'}, 'neden_kodu': 'hastalik', 'neden': 'rahatsızlığı',
                    'devamsizlik': {'ozurlu': '4,5', 'ozursuz': '2'}, 'uyarilari_gordum': True}
            r = A('izin_kaydet', izin, True); iyi(r.get('ok') and r['no_metni'].endswith('/0001') and os.path.exists(r['pdf']), f"dilekçe {r.get('no_metni')} yazıldı")
            iyi(r.get('yazdirma') == 'acildi', 'varsayılan: önce PDF açılır (sınamada program açılmaz)')
            A('ayar_kaydet', {'yazdirma': 'yazici'}); iyi(A('izin_yazdir', r['id']).get('yazdirma') == 'sinama', 'doğrudan yazdırma seçeneği (sınamada yazıcıya gitmez)')
            A('ayar_kaydet', {'yazdirma': 'ac'})
            m = pdf_metni(r['pdf'])
            if m:
                t, resim = m
                for s in ('ÇİĞDEM DEMİR', 'öğrencinin annesi', 'Devamsızlık durumu', 'öğrendim', 'Kayıt no', 'LOGOS Veli İzin', '36. maddesi'): iyi(s in t, f'dilekçede "{s}"')
                iyi(resim == 1, 'dilekçede okul logosu')
            iyi(A('izin_yazdir', r['id']).get('ok'), 'kayıttan yeniden yazdırıldı')
            r = A('ogrenci_belgesi', 1101, {}, True); iyi(r.get('eksik') == ['tc'], 'öğrenci belgesi: eksik kimlik no soruldu')
            r = A('ogrenci_belgesi', 1101, {'tc': '10000000146', 'eksikleri_gordum': True}, True); iyi(r.get('ok') and os.path.exists(r['pdf']), 'öğrenci belgesi yazıldı')
            m = pdf_metni(r['pdf'])
            if m: iyi('ÖĞRENCİ BELGESİ' in m[0] and '10000000146' in m[0] and 'LOGOS' not in m[0], 'öğrenci belgesinin içeriği')
            i = A('istatistik'); iyi(i.get('dilekce') == 1 and i.get('gun') == 1.5 and i.get('ogrenci_belgesi') == 1, 'istatistik')
            iyi(os.path.exists(A('istatistik_csv')['dosya']), 'Excel dökümü')
            iyi(A('kilitle').get('ok') and A('ozet').get('kilit'), 'kilitlendi, veri çağrısı reddedildi')
            iyi('hata' in A('kilit_ac', '0000'), 'yanlış şifre reddedildi')
            iyi(A('kilit_ac', SIFRE).get('ok') and A('ozet')['sayilar']['izin'] == 1, 'şifreyle açıldı, kayıt yerinde')
            A('kilitle'); iyi(A('kurtarma_ile_ac', kurtarma, '1357').get('ok'), 'kurtarma anahtarıyla açıldı')
        with open(os.path.join(k, 'duman.lvk'), encoding='utf-8') as f: ham = f.read()
        iyi(not any(s in ham for s in ('ÇİĞDEM', 'EMİNE', '10000000146', 'Çınar')), 'kasa dosyasında açık veri yok')
        with open(os.path.join(k, 'gunluk.txt'), encoding='utf-8') as f: gl = f.read()
        iyi(not any(s in gl for s in ('ÇİĞDEM', 'EMİNE', '10000000146')), 'günlükte öğrenci bilgisi yok')
    finally:
        shutil.rmtree(k, ignore_errors=True)


def pencere_sinamasi(exe):
    k = tempfile.mkdtemp(prefix='lv-pencere-'); isaret = os.path.join(k, 'baglandi.txt')
    try:
        p = subprocess.Popen([exe], env=ortam(k, LV_PENCERE_SINA=isaret, LV_PENCERE_SINA_SURE='12'))
        son = time.time() + 150
        while not os.path.exists(isaret):
            if p.poll() is not None: raise SystemExit(f'DUMAN BAŞARISIZ: pencere açılmadan çıktı ({p.returncode})')
            if time.time() > son: kapat(p); raise SystemExit('DUMAN BAŞARISIZ: arayüz 150 sn içinde Python\'a bağlanmadı (WebView2?)')
            time.sleep(.5)
        iyi(True, 'pencere açıldı, arayüz Python\'a bağlandı')
        t = time.time(); ikinci = subprocess.run([exe], env=ortam(k), timeout=60)
        iyi(ikinci.returncode == 0 and time.time() - t < 40 and p.poll() is None, 'ikinci açılış birinciyi öne getirip çıktı')
        try: p.wait(60)
        except subprocess.TimeoutExpired: kapat(p); raise SystemExit('DUMAN BAŞARISIZ: pencere kapanmadı')
        iyi(p.returncode == 0, 'pencere kapandı')
    finally:
        shutil.rmtree(k, ignore_errors=True)


def main():
    a = argparse.ArgumentParser(); a.add_argument('exe'); a.add_argument('--surum'); a.add_argument('--pencere', action='store_true')
    a = a.parse_args(); exe = os.path.abspath(a.exe)
    print('duman sınaması:', exe, flush=True)
    tarayici_sinamasi(exe, a.surum)
    if a.pencere: pencere_sinamasi(exe)
    print('duman sınaması: TAMAM', flush=True)


if __name__ == '__main__':
    main()
