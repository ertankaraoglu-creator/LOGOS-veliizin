"""e-Okul raporlarından öğrenci listesi (LOGOS Disiplin'in eokul.py'sinden türetildi; aynı okuma yolu: pdfplumber, satır ve sütun
konumları).

Kullanılan raporlar (dosya adından değil içerikten tanınır, `tur_bul`):
  genel     Genel Öğrenci Listesi (e-Okul > Ortaöğretim Öğrenci İşlemleri > Yazdır > OOG01001R092; sınıf başına bir PDF).
            ESAS RAPOR. Başlıkta okul ("Konak / Konak Atatürk Mesleki Ve Teknik Anadolu Lisesi Müdürlüğü") ve sınıf
            ("AMP - 9. Sınıf / A Şubesi SAĞLIK HİZMETLERİ ALANI 2026-2027 I. Dönem"); her sayfada 4 öğrenci bloğu, blok "Baba Adı"
            satırıyla başlar; solda fotoğraf, altında ad soyad ve okul no; sağda iki sütun "Etiket : değer".
            Alınanlar (Ertan 03.11.2026): ad soyad, doğum tarihi, doğum yeri (öğrenci belgesi için), cinsiyet, baba ve anne adı,
            "Velisi Kim" ve "Veli Adı Soyadı" (dilekçeyi imzalayacak kişi), sınıf / alan / dal (başlıktan), isteğe bağlı fotoğraf.
            Okunmayanlar: ev, gelir, ısınma, hastalık, kardeş, okula geliş, devamsızlık; bu iş için gerekmez, kasaya girmez.
  kimlik    Fotoğraflı-Kimlik Bilgili Öğrenci Listesi: T.C. kimlik numarası (öğrenci belgesi için; genel listede yok).
            Sayfa başlığındaki şube güvenilmez (Disiplin'deki tespit): şube yalnız genel listeden.
Eşleştirme okul numarasıyla; ad soyad da tutmalı (boşluklar yok sayılır: e-Okul uzun adı satır sonunda kelimenin ortasından böler).
Gerçek e-Okul PDF'i depoya girmez; sınama `sinama/eokul_ornek.py`'nin uydurma okuluyla.
"""
import base64, datetime, io, os, re, unicodedata

TURLER = {'genel': 'Genel öğrenci listesi', 'kimlik': 'Kimlik bilgili öğrenci listesi', 'sube': 'Sınıf listesi',
          'yaptirim': 'Yaptırım listesi', 'ozel': 'Özel eğitim gereksinimli öğrenci listesi', 'kunye': 'Künye defteri'}
KULLANILMAYAN = {'sube': 'Sınıf listesinde veli ve doğum bilgisi yok; Genel Öğrenci Listesi yeterli',
                 'yaptirim': 'Disiplin bilgisi; bu programda kullanılmaz', 'ozel': 'Bu programda kullanılmaz',
                 'kunye': 'Nüfus kaydı; bu programda kullanılmaz'}
TARIH = re.compile(r'^(\d{2})/(\d{2})/(\d{4})$')
SUBE_BASLIK = re.compile(r'^(?:(?P<prog>[A-ZÇĞİÖŞÜ]{2,6})\s*-\s*)?(?P<sev>\d{1,2})\.\s*Sınıf\s*/\s*(?P<sube>[A-ZÇĞİÖŞÜ0-9]{1,3})\s*Şubesi'
                         r'\s*(?P<alan>.*?)\s*(?P<y1>\d{4})\s*-\s*(?P<y2>\d{4})\s*(?P<donem>I{1,3})\.\s*Dönem\s*$')
PROGRAM = {'AMP': 'Anadolu Meslek Programı', 'ATP': 'Anadolu Teknik Programı', 'AL': 'Anadolu Lisesi'}
KIMLIK_ETIKET = [('no', 'Öğrenci Numarası'), ('tc', 'T.C. Kimlik No'), ('sinif', 'Sınıfı/Şubesi'), ('adsoyad', 'Adı Soyadı'),
                 ('baba', 'Baba Adı'), ('anne', 'Anne Adı'), ('cinsiyet', 'Cinsiyeti'), ('dogum', 'Doğum Tarihi')]
ETIKET = {'BABAADI': 'baba', 'ANNEADI': 'anne', 'DOĞUMTARİHİ': 'dogum', 'DOĞUMYERİ': 'dogum_yeri', 'CİNSİYETİ': 'cinsiyet',
          'VELİSİKİM': 'velisi_kim', 'VELİADISOYADI': 'veli'}
# Fotoğraf dikdörtgeni (pt, sayfa üstünden): blok üst kenarına göre. İki gerçek PDF'te ölçüldü (03.11.2026).
FOTO_X0, FOTO_X1, FOTO_UST, FOTO_BOY = 30.8, 127.5, 3.5, 124.8
BLOK_BOY = 159.5
FOTO_EN_YUKSEK = 300          # kasaya yazılan fotoğrafın en uzun kenarı (px)


class Hata(Exception):
    pass


# ------------------------------------------------------------------ yazı yardımcıları
def buyuk(s):
    """Türkçe büyük harf (i → İ, ı → I)."""
    return unicodedata.normalize('NFC', str(s or '')).replace('i', 'İ').replace('ı', 'I').upper()


def kucuk(s):
    return unicodedata.normalize('NFC', str(s or '')).replace('I', 'ı').replace('İ', 'i').lower()


def anahtar(s):
    """Ad karşılaştırması: büyük harf, boşluksuz."""
    return ''.join(buyuk(s).split())


def baslik_harf(s):
    """'AZRA AHSEN' → 'Azra Ahsen' (Türkçe)."""
    return ' '.join(buyuk(k[:1]) + kucuk(k[1:]) for k in str(s or '').split())


def _tarih(s):
    m = TARIH.match((s or '').strip())
    if not m: return None
    try: return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    except ValueError: return None


def _duz(s):
    return ' '.join(str(s or '').split())


# ------------------------------------------------------------------ PDF
def _ac(yol):
    try: import pdfplumber
    except ImportError: raise Hata('PDF okuyucu (pdfplumber) kurulu değil')
    try: return pdfplumber.open(yol)
    except FileNotFoundError: raise Hata('Dosya bulunamadı: ' + os.path.basename(yol))
    except Exception: raise Hata(os.path.basename(yol) + ' açılamadı: PDF değil ya da bozuk')


def tur_bul(pdf):
    """İlk sayfanın yazısından rapor türü ya da None."""
    m = anahtar(pdf.pages[0].extract_text(x_tolerance=1.5) or '') if pdf.pages else ''
    if 'YAPTIRIMLİSTESİ' in m: return 'yaptirim'
    if 'ÖZELEĞİTİMGEREKSİNİMLİ' in m: return 'ozel'
    if 'ÖĞRENCİKÜNYEDEFTERİ' in m: return 'kunye'
    if 'VELİSİKİM' in m or 'KİMİNLEOTURUYOR' in m: return 'genel'
    if 'ÖĞRENCİNUMARASI' in m and 'DOĞUMTARİHİ' in m: return 'kimlik'
    if 'SINIFLİSTESİ' in m and 'CİNSİYETİ' in m: return 'sube'
    return None


def _satirlar(sayfa, xt=1.5, yt=2.0):
    W = sayfa.extract_words(x_tolerance=xt, y_tolerance=yt, keep_blank_chars=False)
    satirlar = []
    for w in sorted(W, key=lambda w: (w['top'], w['x0'])):
        if satirlar and abs(satirlar[-1]['top'] - w['top']) <= yt: satirlar[-1]['w'].append(w)
        else: satirlar.append({'top': w['top'], 'w': [w]})
    for s in satirlar:
        s['w'].sort(key=lambda w: w['x0']); s['metin'] = ' '.join(w['text'] for w in s['w'])
    return satirlar


def _ayni_satir(W, w, tol=2.0):
    return sorted((x for x in W if abs(x['top'] - w['top']) <= tol), key=lambda x: x['x0'])


def _etiket(satir, *sozcukler):
    """Satırda art arda gelen etiket sözcüklerinin ilki ve sonuncusu ya da None."""
    n = len(sozcukler)
    for i in range(len(satir) - n + 1):
        if all(satir[i + j]['text'] == sozcukler[j] for j in range(n)): return satir[i], satir[i + n - 1]
    return None


# ------------------------------------------------------------------ başlık
def baslik_coz(metin):
    """'AMP - 9. Sınıf / A Şubesi SAĞLIK HİZMETLERİ ALANI 2026-2027 I. Dönem' → sınıf bilgisi ya da None."""
    m = SUBE_BASLIK.match(_duz(metin))
    if not m: return None
    alan_metni = buyuk(m.group('alan')); alan = dal = ''
    if alan_metni:
        i = alan_metni.find('ALANI')
        if i >= 0:
            alan = _duz(alan_metni[:i]); kalan = _duz(alan_metni[i + 5:]).lstrip('-/,: ')
            j = kalan.find('DALI'); dal = _duz(kalan[:j] if j >= 0 else kalan)
        else: alan = alan_metni
    sev, sube = int(m.group('sev')), m.group('sube')
    return {'program': m.group('prog') or '', 'program_ad': PROGRAM.get(m.group('prog') or '', ''), 'seviye': sev, 'sube': sube,
            'sinif': f'{sev}/{sube}', 'alan': alan, 'dal': dal, 'yil': f"{m.group('y1')}-{m.group('y2')}", 'donem': len(m.group('donem'))}


def sinif_anahtari(b):
    """Meslek lisesinde aynı adlı iki şube olabilir (9/A Sağlık, 9/A Hasta ve Yaşlı): anahtar şube + alan (Disiplin'deki gibi)."""
    return f"{b['sinif']} {b['alan']}".strip()


def alan_kisa(alan):
    """'HASTA VE YAŞLI HİZMETLERİ' → 'HYH' (ekranda '9A-HYH'; LOGOS'taki kısa yazım)."""
    k = [p for p in buyuk(alan).replace('-', ' ').split() if p not in ('VE', 'İLE', 'ALANI')]
    return ''.join(p[0] for p in k)[:5]


def sinif_kisa(sinif, alan=''):
    """'9/A' + alan → '9A-HYH'; alan yoksa '9A'."""
    s = sinif.replace('/', '')
    return f'{s}-{alan_kisa(alan)}' if alan else s


def okul_coz(metin):
    """'Konak / Konak Atatürk Mesleki Ve Teknik Anadolu Lisesi Müdürlüğü' → {ilce, ad}."""
    m = re.match(r'^(.+?)\s*/\s*(.+?)\s*Müdürlüğü\s*$', _duz(metin), re.I)
    return {'ilce': _duz(m.group(1)), 'ad': _duz(m.group(2))} if m else None


# ------------------------------------------------------------------ Genel öğrenci listesi
def _bloklar(sayfa, W, sol_x):
    """Sayfadaki öğrenci bloklarının üst kenarları (pt, sayfa üstünden). Önce çizilen dikdörtgenlerden, yoksa 'Baba Adı' satırından."""
    kutular = sorted(r['top'] for r in sayfa.rects if r['x1'] - r['x0'] > 400 and r['bottom'] - r['top'] > 100)
    if kutular: return kutular
    return sorted(w['top'] - 7.5 for w in W if w['text'] == 'Baba' and abs(w['x0'] - sol_x) < 3
                  and _etiket(_ayni_satir(W, w), 'Baba', 'Adı'))


def _foto(sayfa, ust, olcek=2.0):
    """Bloğun fotoğrafı: sayfa kırpılıp çizilir; JPEG, en uzun kenar FOTO_EN_YUKSEK px; data URL ya da None."""
    try:
        from PIL import Image
        kutu = (FOTO_X0, ust + FOTO_UST, FOTO_X1, ust + FOTO_UST + FOTO_BOY)
        im = sayfa.crop(kutu).to_image(resolution=72 * olcek).original.convert('RGB')
        if im.getextrema() == ((255, 255), (255, 255), (255, 255)): return None            # boş fotoğraf yeri
        im.thumbnail((FOTO_EN_YUKSEK, FOTO_EN_YUKSEK))
        b = io.BytesIO(); im.save(b, 'JPEG', quality=82, optimize=True)
        return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode('ascii')
    except Exception:
        return None


def genel_oku(pdf, fotograf=False):
    """{'okul': {il, ilce, ad} | None, 'sinif': {...} | None, 'ogrenciler': [...], 'uyarilar': [...]}.
    Öğrenci: {no, ad, baba, anne, dogum (ISO), dogum_yeri, cinsiyet 'K'|'E', velisi_kim, veli, foto?}"""
    sonuc = []; uyarilar = []; atlanan = 0; okul = None; il = ''; sinif = None; sinif_basliklari = set()
    for sayfa in pdf.pages:
        W = sayfa.extract_words(x_tolerance=1.5)
        for s in _satirlar(sayfa):
            if s['top'] > 90: break
            if not sinif:
                b = baslik_coz(s['metin'])
                if b: sinif = b
            else:
                b = baslik_coz(s['metin'])
                if b: sinif_basliklari.add(b['sinif'])
            if not okul: okul = okul_coz(s['metin'])
            if not il and buyuk(s['metin']).endswith('VALİLİĞİ'): il = baslik_harf(_duz(s['metin'])[:-len('VALİLİĞİ')].strip())
        babalar = [b for b in (_etiket(_ayni_satir(W, w), 'Baba', 'Adı') for w in W if w['text'] == 'Baba') if b]
        if not babalar: continue
        sol_x = min(b[0]['x0'] for b in babalar)                           # etiket sütunu; solu fotoğraf, ad, no
        ustler = _bloklar(sayfa, W, sol_x)
        for i, ust in enumerate(ustler):
            alt = ustler[i + 1] if i + 1 < len(ustler) else ust + BLOK_BOY + 8
            blok = [w for w in W if ust <= w['top'] < alt]
            if not blok: continue
            sag_x = None
            anne = next((b for b in (_etiket(_ayni_satir(blok, w), 'Anne', 'Adı') for w in blok if w['text'] == 'Anne') if b), None)
            if anne: sag_x = anne[0]['x0']
            sol = sorted((w for w in blok if w['x1'] < sol_x - 2), key=lambda w: (round(w['top']), w['x0']))
            no = next((w['text'] for w in sol if w['text'].isdigit()), None)
            ad = _duz(' '.join(w['text'] for w in sol if not w['text'].isdigit()))
            if not no or not ad: atlanan += 1; continue
            o = {'no': int(no), 'ad': buyuk(ad), 'baba': '', 'anne': '', 'dogum': None, 'dogum_yeri': '', 'cinsiyet': '', 'velisi_kim': '', 'veli': ''}
            S = {}
            for w in blok:
                if w['x0'] >= sol_x - 3: S.setdefault(round(w['top']), []).append(w)
            gorulen = set()
            for top in sorted(S):
                if top in gorulen: continue
                satir = sorted((w for t in (top - 1, top, top + 1) for w in S.get(t, [])), key=lambda w: w['x0'])
                gorulen.update((top - 1, top, top + 1))
                parcalar = ([w for w in satir if sag_x is None or w['x1'] < sag_x - 2], [w for w in satir if sag_x is not None and w['x0'] >= sag_x - 2])
                for parca in parcalar:
                    metin = ' '.join(w['text'] for w in parca)
                    if ':' not in metin: continue
                    et, deger = metin.split(':', 1)
                    a = ETIKET.get(re.sub(r'[^A-ZÇĞİÖŞÜ]', '', buyuk(et)))
                    if not a: continue
                    deger = _duz(deger)
                    if a == 'dogum': o[a] = _tarih(deger)
                    elif a == 'cinsiyet': o[a] = 'K' if buyuk(deger).startswith('K') else ('E' if buyuk(deger).startswith('E') else '')
                    elif a in ('baba', 'anne', 'veli', 'dogum_yeri'): o[a] = buyuk(deger)[:80]
                    else: o[a] = baslik_harf(deger)[:40]
            if fotograf: o['foto'] = _foto(sayfa, ust)
            sonuc.append(o)
    if atlanan: uyarilar.append(f'{atlanan} öğrencinin bloğu okunamadı (adı ya da numarası bulunamadı); atlandı')
    if sinif and sinif_basliklari - {sinif['sinif']}:
        uyarilar.append('Dosyada birden çok sınıf başlığı var: ' + ', '.join(sorted(sinif_basliklari)))
    if not sinif: uyarilar.append('Sınıf başlığı okunamadı; öğrenciler sınıfsız kaldı')
    gorulen = {}
    for o in sonuc:
        if o['no'] in gorulen: uyarilar.append(f"Okul no {o['no']} iki kez geçiyor: {gorulen[o['no']]} ve {o['ad']}")
        gorulen[o['no']] = o['ad']
    return {'okul': dict(okul or {}, il=il) if (okul or il) else None, 'sinif': sinif, 'ogrenciler': sonuc, 'uyarilar': uyarilar}


# ------------------------------------------------------------------ Kimlik bilgili öğrenci listesi (T.C. kimlik no)
def kimlik_oku(pdf, fotograf=False):
    """{'kimlik': {no: {adsoyad, tc, baba, anne, cinsiyet, dogum}}, 'uyarilar': []}. Sınıf okunur ama alınmaz (başlık güvenilmez)."""
    sonuc = {}; kayit = None
    desen = [(a, re.compile(r'^' + re.escape(e) + r'\.*\s*:\s*(.*)$')) for a, e in KIMLIK_ETIKET]
    for sayfa in pdf.pages:
        for s in _satirlar(sayfa):
            for alan, d in desen:
                m = d.match(s['metin'])
                if not m: continue
                v = m.group(1).strip()
                if alan == 'no':
                    kayit = None
                    if v.isdigit(): kayit = sonuc.setdefault(int(v), {})
                elif kayit is not None and alan != 'sinif' and v:
                    kayit[alan] = _tarih(v) if alan == 'dogum' else (v if alan == 'tc' else buyuk(v))
                break
    return {'kimlik': sonuc, 'uyarilar': []}


OKUYUCU = {'genel': genel_oku, 'kimlik': kimlik_oku}


def oku(yol, fotograf=False):
    """Bir PDF: {'dosya', 'tur', 'tur_ad', 'sayfa', 'kullanilir', 'neden'?, ...okunan}."""
    with _ac(yol) as pdf:
        tur = tur_bul(pdf)
        r = {'dosya': os.path.basename(yol), 'tur': tur, 'tur_ad': TURLER.get(tur, 'Tanınmayan rapor'), 'sayfa': len(pdf.pages),
             'kullanilir': tur in OKUYUCU}
        if tur in OKUYUCU: r.update(OKUYUCU[tur](pdf, fotograf))
        elif tur in KULLANILMAYAN: r['neden'] = KULLANILMAYAN[tur]
        else: r['neden'] = 'Bu PDF tanınan e-Okul raporlarından biri değil'
    return r


def tc_denetle(tc):
    """T.C. kimlik numarası: 11 hane, ilk hane 0 değil, 10. ve 11. hane denetim kuralı. Boş geçerli (bilinmiyor)."""
    t = ''.join(str(tc or '').split())
    if not t: return ''
    if not (t.isdigit() and len(t) == 11 and t[0] != '0'): return None
    d = [int(c) for c in t]
    if (7 * sum(d[0:9:2]) - sum(d[1:8:2])) % 10 != d[9]: return None
    if sum(d[:10]) % 10 != d[10]: return None
    return t


# ------------------------------------------------------------------ birleştirme
def birlestir(mevcut, raporlar, yil=None):
    """Okunan raporları kasadaki öğrenci listesiyle birleştirir; (öğrenciler, sınıflar, özet) döner, hiçbir şeyi yerinde değiştirmez.
    Kural: okul numarası aynı ve adı uyuşan öğrenci güncellenir (e-Okul'dan gelen alanlar); elle girilen alanlar (tc, foto_donus,
    not) ve elle düzenlenmiş veli korunur. Rapordaki sınıfın kasadaki öğrencileri raporda yoksa 'ayrildi' olur; başka sınıftaki
    öğrencilere dokunulmaz. Aynı numarayı başka öğrenci taşıyorsa eski kayıt 'no-E' biçiminde ayrı numaraya taşınır."""
    O = {o['no']: dict(o) for o in (mevcut or [])}
    siniflar = {}; ozet = {'yeni': 0, 'guncellenen': 0, 'ayrilan': 0, 'tasinan': 0, 'tc': 0, 'foto': 0, 'uyarilar': []}
    simdi = datetime.datetime.now().isoformat(timespec='seconds')
    for r in raporlar:
        if r.get('tur') == 'genel' and r.get('sinif'):
            b = r['sinif']; sk = sinif_anahtari(b)
            siniflar[sk] = {'anahtar': sk, 'sinif': b['sinif'], 'seviye': b['seviye'], 'sube': b['sube'], 'alan': b['alan'], 'dal': b['dal'],
                            'program': b['program'], 'program_ad': b['program_ad'], 'kisa': sinif_kisa(b['sinif'], b['alan']), 'sayi': 0}
            gelen = set()
            for g in r['ogrenciler']:
                no = g['no']; gelen.add(no)
                e = O.get(no)
                if e and anahtar(e['ad']) != anahtar(g['ad']) and e.get('durum') != 'ayrildi':
                    yeni_no = _eski_no(no, O); e2 = dict(e, no=yeni_no, durum='ayrildi', not_=f"Okul no {no} başka öğrenciye verildi ({simdi[:10]})")
                    O[yeni_no] = e2; e = None; ozet['tasinan'] += 1
                if e is None:
                    e = {'no': no, 'ad': g['ad'], 'tc': '', 'foto': None, 'foto_donus': 0, 'veli_elle': None, 'not_': '', 'ekleme': simdi}
                    ozet['yeni'] += 1
                else: ozet['guncellenen'] += 1
                e.update({'ad': g['ad'], 'baba': g['baba'], 'anne': g['anne'], 'dogum': g['dogum'], 'dogum_yeri': g['dogum_yeri'],
                          'cinsiyet': g['cinsiyet'], 'velisi_kim': g['velisi_kim'], 'veli': g['veli'], 'sinif': sk, 'durum': 'aktif',
                          'kaynak': 'eokul', 'guncelleme': simdi})
                if g.get('foto'): e['foto'] = g['foto']; e['foto_donus'] = e.get('foto_donus') or 0; ozet['foto'] += 1
                O[no] = e
            for no, e in O.items():
                if e.get('sinif') == sk and no not in gelen and e.get('durum') != 'ayrildi':
                    e['durum'] = 'ayrildi'; e['guncelleme'] = simdi; ozet['ayrilan'] += 1
        elif r.get('tur') == 'kimlik':
            for no, k in r['kimlik'].items():
                e = O.get(no)
                if not e: continue
                if anahtar(e['ad']) != anahtar(k.get('adsoyad', '')):
                    ozet['uyarilar'].append(f"Kimlik listesinde {no} numaralı öğrencinin adı ({k.get('adsoyad')}) kasadakiyle ({e['ad']}) uyuşmuyor; atlandı"); continue
                if k.get('tc') and tc_denetle(k['tc']): e['tc'] = tc_denetle(k['tc']); ozet['tc'] += 1
                for a in ('baba', 'anne', 'dogum'):
                    if not e.get(a) and k.get(a): e[a] = k[a]
                if not e.get('cinsiyet') and k.get('cinsiyet'): e['cinsiyet'] = 'K' if k['cinsiyet'].startswith('K') else 'E'
    for e in O.values():
        if e.get('sinif') in siniflar and e.get('durum') == 'aktif': siniflar[e['sinif']]['sayi'] += 1
    return list(O.values()), siniflar, ozet


def _eski_no(no, kullanilan):
    for i in range(1, 100):
        aday = f'{no}-E{i if i > 1 else ""}'
        if aday not in kullanilan: return aday
    return f'{no}-E99'
