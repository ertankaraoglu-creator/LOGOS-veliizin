"""dersdagitim.com/veli-izin sayfasının görselleri (LOGOS Disiplin'deki deneyler/site_ekran.py gibi). Yalnız uydurma okulla:
"Deneme Mesleki ve Teknik Anadolu Lisesi", sinama/eokul_ornek.py'nin uydurma öğrencileri, uydurma logo ve idareci adları.

    python deneyler/site_ekran.py <LOGOS deposunun site klasörü>      # site/ekran/veli-izin-*.webp ve site/medya/veli-izin-paylas.jpg

Ekranlar 1360 × 768 (Disiplin'inkiler gibi); belgeler PDF'ten çizilir. Gerekenler: playwright, pdftoppm (poppler), Pillow.
"""
import base64, datetime, io, os, random, subprocess, sys, tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
from sinama import ui_ortak as U, eokul_ornek as EO

OKUL = {'il': 'İzmir', 'ilce': 'Konak', 'ad': 'Deneme Mesleki Ve Teknik Anadolu Lisesi'}
MUDUR, MUDUR_YRD = 'Kemal Aydın', 'Selin Yıldız'          # uydurma
W, H = 1360, 768


def logo_veri():
    """Uydurma okul logosu: halka, ortada kitap ve yıldız."""
    from PIL import Image, ImageDraw
    im = Image.new('RGBA', (400, 400), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((8, 8, 392, 392), fill=(18, 58, 130, 255)); d.ellipse((40, 40, 360, 360), fill=(255, 255, 255, 255))
    d.ellipse((58, 58, 342, 342), outline=(18, 58, 130, 255), width=10)
    d.polygon([(110, 250), (200, 220), (200, 300), (110, 320)], fill=(238, 106, 38, 255))
    d.polygon([(290, 250), (200, 220), (200, 300), (290, 320)], fill=(27, 154, 107, 255))
    import math
    yildiz = [(200 + (62 if i % 2 == 0 else 26) * math.sin(i * math.pi / 5), 150 - (62 if i % 2 == 0 else 26) * math.cos(i * math.pi / 5)) for i in range(10)]
    d.polygon(yildiz, fill=(239, 173, 29, 255))
    b = io.BytesIO(); im.save(b, 'PNG'); return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


def okul_gunleri(bas, bit):
    from uygulama import isgunu
    d = datetime.date.fromisoformat(bas); son = datetime.date.fromisoformat(bit); out = []
    while d <= son:
        if isgunu.okul_gunu(d): out.append(d)
        d += datetime.timedelta(days=1)
    return out


def kur(S):
    """Kasayı uygulamanın kendi çağrılarıyla kurar (sunucu açılmadan, aynı ayar klasöründe)."""
    os.environ['LV_AYAR_KLASORU'] = S.klasor; os.environ['LV_SINAMA'] = '1'
    from uygulama import ana, isgunu
    A = ana.Api(S.kasa)
    A.kasa_olustur(dict(OKUL, kurum_kodu=''), U.SIFRE)
    k = os.path.join(S.klasor, 'ornek'); os.makedirs(k, exist_ok=True)
    yollar = []
    for sinif, n in (('9A', 10), ('10B', 8), ('AL', 6)):
        y = os.path.join(k, f'{sinif}.pdf'); EO.genel_liste(y, sinif, n, True, okul=OKUL); yollar.append(y)
    ky = os.path.join(k, 'kimlik.pdf'); EO.kimlik_listesi(ky, ('9A', '10B', 'AL'), 10); yollar.append(ky)
    A.eokul_oku(yollar, True); A.eokul_aktar(True)
    A.okul_logo_yukle(logo_veri())
    A.ayar_kaydet({'onay_ad': MUDUR_YRD, 'belge_mudur': MUDUR, 'belge_mudur_yrd': MUDUR_YRD, 'kilit_dakika': 0})
    r = random.Random(2026); L = A.ogrenciler()['ogrenciler']; nedenler = A.ozet()['nedenler']
    agirlik = {'hastalik': 9, 'saglik': 6, 'aile': 4, 'cenaze': 1, 'resmi': 2, 'yol': 2, 'diger': 1}
    gunler = okul_gunleri('2026-09-10', (isgunu.bugun() - datetime.timedelta(days=1)).isoformat())
    for i in range(30):
        o = r.choice(L); oa = A.ogrenci(o['no'])['ogrenci']; g = r.choice(gunler[:-1])
        uzun = r.random() < 0.3; secim = [g]
        if uzun:
            j = gunler.index(g); secim = gunler[j:j + r.choice([2, 2, 3, 4])]
        tur = 'tam' if r.random() < 0.75 else r.choice(['once', 'sonra'])
        gun = {d.isoformat(): (tur if len(secim) == 1 else 'tam') for d in secim}
        n = r.choices(nedenler, weights=[agirlik.get(x['kod'], 1) for x in nedenler])[0]
        aday = oa['veli_adaylari'][0] if oa['veli_adaylari'] else {'ad': 'Ayşe Kaya', 'yakinlik': 'Diğer'}
        veli = {'ad': aday['ad'], 'yakinlik': aday['yakinlik'] if aday['yakinlik'] in ('Anne', 'Baba', 'Vasi') else 'Diğer',
                'yakinlik_aciklama': '' if aday['yakinlik'] in ('Anne', 'Baba', 'Vasi') else 'teyzesi', 'kayitli': bool(aday.get('kayitli'))}
        if r.random() < 0.25:                                    # ileriye dönük izin isteği: dilekçe günlerden önce yazılır
            tarih = secim[0] - datetime.timedelta(days=r.choice([1, 2, 3]))
            while not isgunu.okul_gunu(tarih): tarih -= datetime.timedelta(days=1)
        else:
            tarih = max(secim[-1], g) + datetime.timedelta(days=r.choice([0, 0, 1, 1, 2]))
            while not isgunu.okul_gunu(tarih) and tarih < isgunu.bugun(): tarih += datetime.timedelta(days=1)
        dev = {'ozurlu': str(r.choice([0, 1, 2, 3.5, 4, 6])).replace('.', ','), 'ozursuz': str(r.choice([0, 0.5, 1, 2]))} if r.random() < 0.4 else None
        A.izin_kaydet({'ogrenci_no': o['no'], 'tarih': tarih.isoformat(), 'veli': veli, 'gunler': gun, 'neden_kodu': n['kod'], 'neden': n['metin'],
                       'devamsizlik': dev, 'uyarilari_gordum': True}, yazdir=False)
    ileri = [d for d in okul_gunleri(isgunu.bugun().isoformat(), (isgunu.bugun() + datetime.timedelta(days=21)).isoformat()) if d > isgunu.bugun()]
    for i, (no, gun, kod) in enumerate(((L[4]['no'], {ileri[1].isoformat(): 'tam'}, 'saglik'), (L[12]['no'], {ileri[3].isoformat(): 'once'}, 'resmi'),
                                        (L[20]['no'], {ileri[5].isoformat(): 'tam', ileri[6].isoformat(): 'tam'}, 'aile'))):
        n = next(x for x in nedenler if x['kod'] == kod); oa = A.ogrenci(no)['ogrenci']; aday = oa['veli_adaylari'][0]
        A.izin_kaydet({'ogrenci_no': no, 'tarih': (isgunu.bugun() - datetime.timedelta(days=i)).isoformat(),
                       'veli': {'ad': aday['ad'], 'yakinlik': aday['yakinlik'] if aday['yakinlik'] in ('Anne', 'Baba', 'Vasi') else 'Diğer', 'kayitli': True},
                       'gunler': gun, 'neden_kodu': kod, 'neden': n['metin'], 'uyarilari_gordum': True}, yazdir=False)
    for no in (902, 903):                                          # görüntüdeki kimlik numarası gerçek bir kişininki olamasın: herkesin bildiği deneme numarası
        g = A.ogrenci(no)['ogrenci']; g['tc'] = '10000000146'; assert not A.ogrenci_kaydet(g, no).get('hata')
    for no in [x['no'] for x in L[:5]]: A.ogrenci_belgesi(no, {'eksikleri_gordum': True}, yazdir=False)
    return A


def webp(png, yol, en=None):
    from PIL import Image
    im = Image.open(png).convert('RGB')
    if en and im.width > en: im = im.resize((en, round(im.height * en / im.width)), Image.LANCZOS)
    im.save(yol, 'WEBP', quality=86, method=6); return im.size


def temizle(sayfa):
    sayfa.evaluate("document.getElementById('toasts').innerHTML = ''")
    sayfa.mouse.move(W - 5, H - 5); sayfa.wait_for_timeout(350)


def main(site):
    ekran = os.path.join(site, 'ekran'); medya = os.path.join(site, 'medya'); gecici = tempfile.mkdtemp(prefix='lv-site-')
    from playwright.sync_api import sync_playwright
    S = U.Sunucu(); A = kur(S)
    # belgelerin görüntüsü: bir dilekçe (devamsızlıklı, ileriye dönük gün de) ve bir öğrenci belgesi
    from uygulama import isgunu
    bugun = isgunu.bugun(); ileri = [d for d in okul_gunleri(bugun.isoformat(), (bugun + datetime.timedelta(days=14)).isoformat()) if d > bugun][:2]
    r = A.izin_kaydet({'ogrenci_no': 903, 'tarih': bugun.isoformat(), 'veli': {'ad': 'NURAY ERSOY', 'yakinlik': 'Anne', 'kayitli': True},
                       'gunler': {ileri[0].isoformat(): 'tam', ileri[1].isoformat(): 'once'}, 'neden_kodu': 'saglik',
                       'neden': 'hastanedeki muayene ve sağlık kontrolü', 'devamsizlik': {'ozurlu': '3', 'ozursuz': '1'}, 'uyarilari_gordum': True}, yazdir=False)
    b = A.ogrenci_belgesi(903, {'eksikleri_gordum': True}, yazdir=False)
    for pdf, ad in ((r['pdf'], 'veli-izin-dilekce-kagit'), (b['pdf'], 'veli-izin-belge-kagit')):
        subprocess.run(['pdftoppm', '-r', '150', '-png', '-singlefile', pdf, os.path.join(gecici, ad)], check=True)
        print(ad, webp(os.path.join(gecici, ad + '.png'), os.path.join(ekran, ad + '.webp'), 1000))
    A.izin_sil(r['id'])
    with S, sync_playwright() as pw:
        b_ = pw.chromium.launch(args=['--lang=tr-TR'], env=dict(os.environ, LANG='tr_TR.UTF-8', LANGUAGE='tr'))   # tarih kutusu GG.AA.YYYY
        sayfa = b_.new_context(viewport={'width': W, 'height': H}, locale='tr-TR', device_scale_factor=1).new_page()
        sayfa.goto(S.adres); U.kilit_ac(sayfa)

        def al(ad):
            temizle(sayfa); p = os.path.join(gecici, ad + '.png'); sayfa.screenshot(path=p); print(ad, webp(p, os.path.join(ekran, ad + '.webp')))

        # 1. arama: Türkçe harfsiz yazınca öğrenciler sınıflarıyla
        sayfa.click('aside button[data-sayfa=dilekce]'); sayfa.fill('#q', 'celik'); sayfa.wait_for_selector('#sonuclar .snc')
        sayfa.wait_for_function("document.getElementById('kgLogo') && document.getElementById('kgLogo').style.visibility !== 'hidden'")
        al('veli-izin-arama')
        # 2. dilekçe: öğrenci, kayıtlı veli, iki gün (biri yarım), neden, devamsızlık; önizleme yanda, logolu
        sayfa.fill('#q', '902'); sayfa.wait_for_selector('#sonuclar .snc:has-text("902")'); sayfa.keyboard.press('Enter'); sayfa.wait_for_selector('#dkKalan:not([hidden])')
        gecmis = [d for d in okul_gunleri((bugun - datetime.timedelta(days=14)).isoformat(), (bugun - datetime.timedelta(days=1)).isoformat())]
        gecmis = [gecmis[-4], gecmis[-2]]                            # arada bir okul günü: iki ayrı satır (tam gün ve yarım gün)
        for d in gecmis:
            from sinama.ui_duman import takvime_git
            takvime_git(sayfa, d); sayfa.click(f'button.gun[data-d="{d.isoformat()}"]'); sayfa.wait_for_timeout(250)
        sayfa.wait_for_selector('.donem'); sayfa.locator('.donem select').last.select_option('once')
        sayfa.click('#nedenler >> text=Sağlık kontrolü')
        sayfa.click('#devBox summary'); sayfa.fill('#dOz', '4,5'); sayfa.fill('#dOzs', '1')
        sayfa.wait_for_selector('#kagit .kg-dev'); sayfa.wait_for_function("document.getElementById('kgLogo') && document.getElementById('kgLogo').src.startsWith('data:')")
        sayfa.evaluate("document.getElementById('sayfaAlan').scrollTop = 0"); al('veli-izin-dilekce')
        sayfa.evaluate("document.querySelector('#dkKalan .takvim').scrollIntoView({block: 'start'}); document.getElementById('sayfaAlan').scrollTop -= 125")
        al('veli-izin-takvim')
        # 3. kayıtlar, 4. istatistik
        sayfa.evaluate("KIRLI = false"); sayfa.click('aside button[data-sayfa=kayitlar]'); sayfa.wait_for_selector('#kyTablo table'); al('veli-izin-kayitlar')
        sayfa.click('aside button[data-sayfa=istatistik]'); sayfa.wait_for_selector('#isIcerik .sayi'); al('veli-izin-istatistik')
        # 5. öğrenci penceresi (fotoğraf, e-Okul'dan gelenler)
        sayfa.click('aside button[data-sayfa=ogrenciler]'); sayfa.wait_for_selector('#ogTablo table')
        sayfa.evaluate("document.getElementById('eoYollar').hidden = true")
        sayfa.click('#ogTablo tbody tr:has-text("902")'); sayfa.wait_for_selector('#opAd'); al('veli-izin-ogrenci')
        sayfa.keyboard.press('Escape')
        b_.close()
    paylas(os.path.join(ekran, 'veli-izin-dilekce.webp'), os.path.join(medya, 'veli-izin-paylas.jpg'))


def paylas(ekran_yolu, yol):
    """Paylaşım görseli (og:image, 1200 × 630): lacivert sahne, simge, ad, tek cümle, ekranın bir parçası."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new('RGB', (1200, 630)); d = ImageDraw.Draw(im)
    for y in range(630):
        t = y / 629; d.line([(0, y), (1200, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip((30, 46, 102), (14, 22, 54))))
    e = Image.open(ekran_yolu).convert('RGB'); e = e.resize((760, round(e.height * 760 / e.width)), Image.LANCZOS)
    maske = Image.new('L', e.size, 0); ImageDraw.Draw(maske).rounded_rectangle((0, 0, e.width, e.height), 18, fill=255)
    im.paste(e, (500, 150), maske)
    s = Image.open(os.path.join(KOK, 'paket', 'simge.png')).convert('RGBA').resize((96, 96), Image.LANCZOS); im.paste(s, (64, 64), s)
    F = os.path.join(KOK, 'uygulama', 'fontlar')
    kalin = lambda n: ImageFont.truetype(os.path.join(F, 'LiberationSans-Bold.ttf'), n)
    duz = lambda n: ImageFont.truetype(os.path.join(F, 'LiberationSans-Regular.ttf'), n)
    d.text((180, 72), 'LOGOS', font=kalin(50), fill=(255, 255, 255)); d.text((182, 128), 'Veli İzin', font=duz(30), fill=(199, 210, 234))
    for i, s_ in enumerate(('Veli izin dilekçesi', 'tek tıkla yazıcıdan.')): d.text((64, 230 + i * 56), s_, font=kalin(44), fill=(255, 255, 255))
    for i, s_ in enumerate(('Öğrenci belgesi, devamsızlık,', 'kayıtlar ve istatistik.', 'Tamamen ücretsiz.')):
        d.text((64, 370 + i * 40), s_, font=duz(28), fill=(199, 210, 234) if i < 2 else (239, 173, 29))
    im.save(yol, 'JPEG', quality=88, optimize=True); print('paylaş', yol)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(KOK, '..', 'logos', 'site'))
