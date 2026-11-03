"""LOGOS Veli İzin Dilekçesi masaüstü uygulaması - kabuk (LOGOS Disiplin ile aynı kalıp).

İki çalışma biçimi, tek arayüz (uygulama/arayuz.html):
  python -m uygulama.ana                  # pywebview penceresi (pip install pywebview)
  python -m uygulama.ana --tarayici 8767  # yerel sunucu; tarayıcıda http://127.0.0.1:8767 (geliştirme ve sınamalar)

Arayüz JS'i `api.cagir(ad, ...args)` ile konuşur: pencerede window.pywebview.api, tarayıcıda fetch('/api/ad').
Güvenlik Python'dadır, arayüzde değil: kasa kilitliyken veri okuyan ya da değiştiren her çağrı burada reddedilir.

Kasadaki veri: {okul, ayarlar, okul_logo, yil (etkin öğretim yılı), yillar {yıl: {ogrenciler, siniflar, izinler, belgeler, sayac, eokul}},
guvenlik, meta}. Yıl: dilekçeler ve öğrenci listesi öğretim yılına bağlı; "yeni yıl" eski yılı arşivde okunur bırakır.
"""
import argparse, base64, contextlib, datetime, functools, hashlib, json, os, re, sys, threading, time, traceback

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
from uygulama import kasa as K, yerel, surum, eokul as E, izin as IZ, ogrenci as OG, belge as BL, istatistik as IS, isgunu, gelistirici as GL

DENEME_HAKKI = 5        # art arda bu kadar yanlış şifreden sonra
BEKLEME_SN = 30         # bu kadar beklenir
KILIT_DAKIKA = 30       # varsayılan otomatik kilit; günde 20 dilekçe yazan idareci için uzun (Ayarlar'dan 5-60 dk ya da kapalı)
YAKINLIK = ('Anne', 'Baba', 'Vasi', 'Diğer')

VARSAYILAN_AYARLAR = {'kilit_dakika': KILIT_DAKIKA, 'onay_kutusu': True, 'onay_ad': '', 'onay_unvan': 'Müdür Yardımcısı',
                      'belge_mudur': '', 'belge_mudur_yrd': '', 'belge_burslu': '- / -', 'dilekce_konu': IZ.VARSAYILAN_KONU,
                      'dilekce_metin': IZ.VARSAYILAN_METIN, 'logo_goster': True, 'kayit_no_goster': True, 'kapali_gunler': [],
                      'sinir_ozursuz': 10, 'sinir_toplam': 30, 'fotograf': False, 'yazdirma': 'yazici'}


def yeni_veri(okul):
    yil = isgunu.ogretim_yili()
    return {'okul': {'ad': okul.get('ad', '').strip(), 'il': okul.get('il', '').strip(), 'ilce': okul.get('ilce', '').strip(),
                     'kurum_kodu': okul.get('kurum_kodu', '').strip()},
            'ayarlar': dict(VARSAYILAN_AYARLAR), 'okul_logo': None, 'yil': yil, 'yillar': {yil: yeni_yil_verisi()},
            'guvenlik': [], 'meta': {'uygulama': surum.SURUM, 'olusturma': time.strftime('%Y-%m-%d %H:%M:%S')}}


def yeni_yil_verisi():
    return {'ogrenciler': [], 'siniflar': {}, 'izinler': [], 'belgeler': [], 'sayac': {'izin': 0, 'belge': 0}, 'eokul': {}}


def _ayar_yaz(**k):
    try: yerel.yaz(**k)
    except OSError: pass


def disari(f=None, kilitsiz=False):
    """Arayüzden çağrılan işlev: hata kullanıcıya Türkçe ileti olarak döner, beklenmeyen hata günlüğe yazılır.
    Çağrılar sırayla koşar (`_is`); kilitsiz=True yalnız kullanıcıyı bekleyen işler için (dosya penceresi)."""
    if f is None: return lambda g: disari(g, kilitsiz)

    @functools.wraps(f)
    def sar(self, *a, **k):
        with (contextlib.nullcontext() if kilitsiz else self._is):
            try:
                return f(self, *a, **k)
            except K.Hata as e:
                return {'hata': str(e), 'kilit': isinstance(e, KilitliHata)}
            except (E.Hata, IZ.Hata, OG.Hata, BL.Hata, isgunu.Hata) as e:
                r = {'hata': str(e)}
                if getattr(e, 'alan', None): r['alan'] = e.alan
                return r
            except FileNotFoundError:
                return {'hata': 'Dosya bulunamadı'}
            except Exception as e:
                yerel.gunluk('HATA', f.__name__, hata_izi(e))
                return {'hata': f'Beklenmeyen bir hata oldu ({e.__class__.__name__}). İşlem yapılmadı; bir kez daha deneyin. Sürerse '
                                f'Ayarlar\'daki günlük dosyasını destek adresine gönderin (öğrenci bilgisi içermez).'}
    sar._disari = True
    return sar


class KilitliHata(K.Hata):
    pass


def hata_izi(e):
    """Günlük için hata izi: yalnız hata türü ve kod yerleri. Hatanın iletisi YAZILMAZ (içinde öğrenci adı olabilir)."""
    yer = ' < '.join(f'{os.path.basename(c.filename)}:{c.lineno} {c.name}' for c in reversed(traceback.extract_tb(e.__traceback__)))
    return f'{e.__class__.__name__} @ {yer}'


class Api:
    """pywebview js_api nesnesi. Durum alt çizgili adlarda: pywebview alt çizgili adları taramaz (LOGOS A9 dersi)."""

    def __init__(self, kasa_yolu=None):
        self._is = threading.RLock()
        self._kasa = None
        self._yol = kasa_yolu or yerel.son_kasa()
        self._yanlis = 0; self._bekle_bitis = 0.0
        self._son_etkinlik = time.time(); self._oto_kilit = False
        self._pencere = None; self._bagli = False
        self._eokul = None          # okunmuş, henüz kasaya yazılmamış e-Okul aktarımı (kilitlenince silinir)
        threading.Thread(target=self._bekci, daemon=True).start()

    # ------------------------------------------------------------ iç
    def _acik(self):
        if not self._kasa or not self._kasa.acik: isgunu.ek_ayarla([]); raise KilitliHata('Kasa kilitli; önce şifreyle açın')
        isgunu.ek_ayarla((self._kasa.veri.get('ayarlar') or {}).get('kapali_gunler'))
        return self._kasa

    def _acildi(self):
        self._gelistirici_guncel()
        v = self._kasa.veri
        v.setdefault('ayarlar', {})
        for a, d in VARSAYILAN_AYARLAR.items(): v['ayarlar'].setdefault(a, d)       # eski kasaya yeni ayarlar
        if not v.get('yil'): v['yil'] = isgunu.ogretim_yili()
        v.setdefault('yillar', {}).setdefault(v['yil'], yeni_yil_verisi())

    def _dokun(self):
        self._son_etkinlik = time.time(); self._oto_kilit = False

    def _kilit_dakika(self):
        try: return int(self._kasa.veri['ayarlar'].get('kilit_dakika') or 0)
        except Exception: return KILIT_DAKIKA

    def _bekci(self):
        """Otomatik kilit: kullanıcı belirlenen süre boyunca hiçbir şey yapmazsa kasa kilitlenir (0: kapalı)."""
        while True:
            time.sleep(5)
            with self._is:
                k = self._kasa; dk = self._kilit_dakika()
                if k and k.acik and dk and time.time() - self._son_etkinlik > dk * 60:
                    k.kilitle(); self._eokul = None; self._oto_kilit = True; yerel.gunluk('otomatik kilit')

    def _okul(self):
        return dict(self._kasa.veri.get('okul') or {}) if self._kasa and self._kasa.acik else {}

    def _ayarlar(self):
        return dict(VARSAYILAN_AYARLAR, **(self._kasa.veri.get('ayarlar') or {}))

    def _yil(self):
        return self._kasa.veri.get('yil') or isgunu.ogretim_yili()

    def _Y(self, yil=None):
        """Yılın verisi (etkin yıl ya da istenen; yoksa boş)."""
        v = self._kasa.veri; y = yil or v.get('yil')
        return v.setdefault('yillar', {}).setdefault(y, yeni_yil_verisi())

    def _ogr(self, no, Y=None):
        Y = Y or self._Y()
        for o in Y['ogrenciler']:
            if str(o['no']) == str(no): return o
        raise K.Hata('Öğrenci bulunamadı')

    def _sinif(self, o, Y=None):
        Y = Y or self._Y(); s = (Y.get('siniflar') or {}).get(o.get('sinif'))
        if s: return dict(s)
        m = re.match(r'^(\d+)/(\S+)\s*(.*)$', o.get('sinif') or '')
        return {'anahtar': o.get('sinif', ''), 'sinif': f'{m.group(1)}/{m.group(2)}' if m else (o.get('sinif') or ''), 'seviye': int(m.group(1)) if m else None,
                'sube': m.group(2) if m else '', 'alan': m.group(3) if m else '', 'dal': o.get('dal') or '', 'program': '', 'program_ad': '',
                'kisa': E.sinif_kisa(f'{m.group(1)}/{m.group(2)}', m.group(3)) if m else (o.get('sinif') or '')}

    def _ogr_paket(self, o, Y=None):
        """Arayüze giden öğrenci: fotoğraf dahil, yıl içindeki izin sayısı ve toplam günle."""
        Y = Y or self._Y(); s = self._sinif(o, Y)
        izinler = [i for i in Y['izinler'] if str(i['ogrenci_no']) == str(o['no']) and not i.get('silindi')]
        return dict(o, sinif_ad=s['sinif'], sinif_kisa=s['kisa'], alan=s['alan'], dal=o.get('dal') or s.get('dal') or '', ad_kisa=OG.ad_kisa(o),
                    izin_sayisi=len(izinler), izin_gun=sum(float(i.get('toplam') or 0) for i in izinler), yas=OG.yas(o),
                    veli_adaylari=OG.veli_adaylari(o))

    # ------------------------------------------------------------ geliştiriciden kurtarma (gelistirici.py; Disiplin'deki gibi)
    @staticmethod
    def _gelistirici_kur(k, kaydet=True):
        o = k.veri.get('okul') or {}
        bilgi = {'okul': o.get('ad'), 'il': o.get('il'), 'ilce': o.get('ilce'), 'kurum_kodu': o.get('kurum_kodu')}
        k.veri.setdefault('ayarlar', {})['gelistirici_ozet'] = Api._gelistirici_ozet(k)
        return k.gelistirici_kur(bilgi, kaydet=kaydet)

    @staticmethod
    def _gelistirici_ozet(k):
        o = k.veri.get('okul') or {}
        bilgi = [o.get(a) or '' for a in ('ad', 'il', 'ilce', 'kurum_kodu')]
        return hashlib.sha256(json.dumps(bilgi, ensure_ascii=False).encode('utf-8')).hexdigest()[:16]

    def _gelistirici_guncel(self):
        k = self._kasa; a = k.veri.setdefault('ayarlar', {})
        try:
            if a.get('gelistirici_kurtarma') is False:
                if k.gelistirici_var: k.gelistirici_kapat()
                return
            if GL.acik_anahtar() is None: return
            if k.gelistirici_var and a.get('gelistirici_ozet') == self._gelistirici_ozet(k): return
            self._gelistirici_kur(k)
        except K.Hata as e:
            yerel.gunluk('geliştirici kurtarması güncellenemedi', e.__class__.__name__)

    @disari
    def kurtarma_istegi(self):
        if not os.path.exists(self._yol): raise K.Hata('Kasa dosyası bulunamadı')
        g = K.kurtarma_istegi(self._yol)
        if not g.get('istek'): return {'var': False, 'kapali': bool(g.get('kapali'))}
        e = GL.eposta(g['istek'])
        return {'var': True, 'istek': g['istek'], 'zaman': g.get('zaman'), 'eposta': surum.DESTEK_EPOSTA, 'konu': e['konu'], 'govde': e['govde'],
                'metin': f"Kime: {surum.DESTEK_EPOSTA}\nKonu: {e['konu']}\n\n{e['govde']}"}

    @disari
    def gelistirici_kurtarma(self, acik):
        k = self._acik(); self._dokun()
        k.veri.setdefault('ayarlar', {})['gelistirici_kurtarma'] = bool(acik)
        if acik: k.veri['ayarlar'].pop('gelistirici_ozet', None)
        self._gelistirici_guncel()
        if bool(acik) != k.gelistirici_var and GL.acik_anahtar() is not None: raise K.Hata('Kaydedilemedi; bir kez daha deneyin')
        return {'ok': True, 'kasa': k.bilgi(), 'ayarlar': self._ayarlar()}

    # ------------------------------------------------------------ açılış
    @disari
    def baslangic(self):
        var = os.path.exists(self._yol)
        if not self._bagli: self._bagli = True; yerel.gunluk('arayüz bağlandı', 'pencere' if self._pencere else 'tarayıcı', 'kasa var' if var else 'kasa yok')
        b = {'ad': surum.AD, 'tam_ad': surum.TAM_AD, 'surum': surum.SURUM, 'tarih': surum.TARIH, 'telif': surum.TELIF, 'destek': surum.DESTEK_EPOSTA,
             'site': surum.SITE, 'kasa_var': var, 'kasa_yolu': self._yol, 'kasa_adi': os.path.basename(self._yol), 'acik': bool(self._kasa and self._kasa.acik),
             'varsayilan_yol': yerel.varsayilan_kasa_yolu(), 'ogretim_yili': isgunu.ogretim_yili(), 'pencere': self._pencere is not None,
             'kayip_kasa': None if var else yerel.kayip_kasa(), 'bugun': isgunu.bugun().isoformat()}
        if var:
            try:
                h = K.baslik_oku(self._yol); b['yazilma'] = (h.get('veri') or {}).get('yazilma')
            except K.Hata as e:
                b['kasa_hata'] = str(e)
        return b

    @disari
    def durum(self):
        acik = bool(self._kasa and self._kasa.acik); dk = self._kilit_dakika() if acik else 0
        return {'acik': acik, 'oto_kilit': self._oto_kilit and not acik,
                'kalan_sn': max(0, int(dk * 60 - (time.time() - self._son_etkinlik))) if acik and dk else 0}

    @disari(kilitsiz=True)
    def kirli(self, acik):
        if self._pencere is not None: self._pencere.confirm_close = bool(acik)
        return {'ok': True}

    @disari
    def etkinlik(self):
        if self._kasa and self._kasa.acik: self._dokun()
        return {'ok': True}

    # ------------------------------------------------------------ kurulum
    @disari
    def sifre_sina(self, sifre, kurum_kodu=None):
        K.sifre_denetle(sifre, kurum_kodu); return {'ok': True}

    @disari
    def kasa_olustur(self, okul, sifre, yol=None):
        """İlk kurulum: yeni kasa. Kurtarma anahtarını bir kez döner; hiçbir yere yazılmaz."""
        okul = okul or {}
        if not (okul.get('ad') or '').strip(): raise K.Hata('Okulun adını yazın')
        yol = yol or self._yol
        k, kurtarma = K.Kasa.olustur(yol, sifre, yeni_veri(okul), okul.get('kurum_kodu'))
        self._kasa = k; self._yol = yol; self._yanlis = 0; self._dokun()
        _ayar_yaz(son_kasa=yol); yerel.gunluk('kasa oluşturuldu')
        self._acildi()
        return {'ok': True, 'kurtarma': kurtarma, 'okul': self._okul()}

    @disari
    def okul_bilgisi_pdften(self, yollar):
        """Kurulumda: ilk PDF'in başlığından okul adı, il, ilçe (kasa yokken de çalışır; kasaya bir şey yazmaz)."""
        for y in yollar or []:
            try:
                r = E.oku(str(y).strip().strip('"'))
                if r.get('okul'): return {'ok': True, 'okul': r['okul']}
            except E.Hata: continue
        return {'ok': False}

    # ------------------------------------------------------------ kilit
    @disari
    def kilit_ac(self, sifre):
        kalan = self._bekle_bitis - time.time()
        if kalan > 0: return {'hata': f'Çok fazla yanlış deneme. {int(kalan) + 1} saniye sonra yeniden deneyin', 'bekle': int(kalan) + 1}
        try:
            self._kasa = K.Kasa.ac(self._yol, sifre)
        except K.SifreYanlis:
            self._yanlis += 1; yerel.gunluk('yanlış şifre')
            if self._yanlis >= DENEME_HAKKI:
                self._yanlis = 0; self._bekle_bitis = time.time() + BEKLEME_SN
                return {'hata': f'Şifre yanlış. {BEKLEME_SN} saniye bekleyin', 'bekle': BEKLEME_SN}
            return {'hata': f'Şifre yanlış (kalan deneme: {DENEME_HAKKI - self._yanlis})'}
        self._yanlis = 0; self._dokun(); _ayar_yaz(son_kasa=self._yol); yerel.gunluk('kasa açıldı'); self._acildi()
        return {'ok': True, 'okul': self._okul()}

    @disari
    def kurtarma_ile_ac(self, anahtar, yeni_sifre):
        kalan = self._bekle_bitis - time.time()
        if kalan > 0: return {'hata': f'{int(kalan) + 1} saniye sonra yeniden deneyin', 'bekle': int(kalan) + 1}
        okunur = K.kurtarma_duzelt(anahtar)
        K.sifre_denetle(yeni_sifre)
        gelistirici = False
        try:
            k = K.Kasa.kurtarma_ile_ac(self._yol, okunur)
        except K.SifreYanlis:
            try:
                k = K.Kasa.gelistirici_ile_ac(self._yol, okunur); gelistirici = True
            except K.SifreYanlis:
                self._yanlis += 1
                if self._yanlis >= DENEME_HAKKI: self._yanlis = 0; self._bekle_bitis = time.time() + BEKLEME_SN
                raise K.SifreYanlis('Bu, kasanın kurtarma anahtarı da değil, geliştiricinin verdiği geçerli bir kod da. '
                                    'Geliştiricinin kodu bir kez kullanılır; yeniden gerekirse yeni bir istek gönderin.')
        kod = (k.veri.get('okul') or {}).get('kurum_kodu')
        K.sifre_denetle(yeni_sifre, kod)
        if gelistirici:
            k.veri.setdefault('guvenlik', []).append({'zaman': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 'olay': 'gelistirici_kodu'})
            self._gelistirici_kur(k, kaydet=False)
        k.sifre_degistir(yeni_sifre, kod)
        self._kasa = k; self._yanlis = 0; self._dokun(); _ayar_yaz(son_kasa=self._yol)
        yerel.gunluk('geliştiricinin koduyla açıldı, yeni şifre' if gelistirici else 'kurtarma anahtarıyla açıldı, yeni şifre')
        self._acildi()
        return {'ok': True, 'okul': self._okul(), 'gelistirici': gelistirici}

    @disari
    def kilitle(self):
        if self._kasa: self._kasa.kilitle()
        self._eokul = None; self._oto_kilit = False; isgunu.ek_ayarla([])
        return {'ok': True}

    # ------------------------------------------------------------ okul, ayarlar, yıl
    @disari
    def ozet(self):
        """Ana Sayfa ve her sayfanın başı: okul, ayarlar, yıl, sayılar, kasa bilgisi."""
        k = self._acik(); self._dokun(); v = k.veri; Y = self._Y(); yil = self._yil()
        bugun = isgunu.bugun().isoformat(); izinler = [i for i in Y['izinler'] if not i.get('silindi')]
        return {'okul': self._okul(), 'ayarlar': self._ayarlar(), 'kasa': k.bilgi(), 'yil': yil, 'yillar': sorted(v.get('yillar') or {}, reverse=True),
                'takvim_yili': isgunu.ogretim_yili(), 'bugun': bugun, 'logo': bool(v.get('okul_logo')),
                'guvenlik': (v.get('guvenlik') or [])[-5:], 'gelistirici_anahtar': GL.acik_anahtar() is not None,
                'sayilar': {'ogrenci': sum(1 for o in Y['ogrenciler'] if o.get('durum') != 'ayrildi'), 'sinif': len(Y.get('siniflar') or {}),
                            'izin': len(izinler), 'izin_bugun': sum(1 for i in izinler if i.get('tarih') == bugun),
                            'gun': sum(float(i.get('toplam') or 0) for i in izinler), 'belge': sum(1 for b in Y['belgeler'] if not b.get('silindi'))},
                'eokul': Y.get('eokul') or {}, 'takvim': self._takvim_paket(), 'nedenler': [{'kod': k2, 'ad': a, 'metin': m} for k2, a, m in IZ.NEDENLER],
                'yakinlik': list(YAKINLIK)}

    def _takvim_paket(self):
        try: return isgunu.takvim_ozet(self._yil())
        except Exception: return None

    @disari
    def takvim_ay(self, yil, ay):
        """Takvim çizimi için ayın günleri: {gun: {okul: bool, neden}}; okul günü olmayanlar işaretli."""
        self._acik()
        y, a = int(yil), int(ay); ilk = datetime.date(y, a, 1); out = {}
        d = ilk
        while d.month == a:
            okul = isgunu.okul_gunu(d)
            out[d.isoformat()] = {'okul': okul, 'neden': None if okul else (isgunu.neden(d) or ('Hafta sonu' if d.weekday() >= 5 else 'Okul günü değil'))}
            d += datetime.timedelta(days=1)
        return {'gunler': out}

    @disari
    def okul_kaydet(self, okul):
        k = self._acik(); self._dokun()
        o = k.veri.setdefault('okul', {})
        for a in ('ad', 'il', 'ilce', 'kurum_kodu'):
            if a in (okul or {}): o[a] = str(okul[a] or '').strip()
        if not o.get('ad'): raise K.Hata('Okulun adı boş olamaz')
        k.kaydet(); self._gelistirici_guncel()
        return {'ok': True, 'okul': self._okul(), 'kasa': k.bilgi()}

    @disari
    def ayar_kaydet(self, ayarlar):
        """Ayarlar sayfası: yalnız bilinen anahtarlar, denetimle."""
        k = self._acik(); self._dokun(); a = k.veri.setdefault('ayarlar', {})
        g = ayarlar or {}
        if 'dilekce_metin' in g: a['dilekce_metin'] = IZ.metin_denetle(g['dilekce_metin'])
        for ad in ('onay_ad', 'onay_unvan', 'belge_mudur', 'belge_mudur_yrd', 'belge_burslu', 'dilekce_konu'):
            if ad in g: a[ad] = ' '.join(str(g[ad] or '').split())[:120]
        for ad in ('onay_kutusu', 'logo_goster', 'kayit_no_goster', 'fotograf'):
            if ad in g: a[ad] = bool(g[ad])
        for ad in ('sinir_ozursuz', 'sinir_toplam'):
            if ad in g:
                try: a[ad] = max(1, min(200, int(g[ad])))
                except (TypeError, ValueError): raise K.Hata('Devamsızlık sınırı sayı olmalı')
        if 'kilit_dakika' in g:
            d = int(g['kilit_dakika'])
            if d not in (0, 5, 10, 15, 30, 60): raise K.Hata('Geçersiz kilit süresi')
            a['kilit_dakika'] = d
        if 'yazdirma' in g and g['yazdirma'] in ('yazici', 'ac'): a['yazdirma'] = g['yazdirma']
        if 'kapali_gunler' in g: a['kapali_gunler'] = isgunu.ek_duzelt(g['kapali_gunler'] or [])
        k.kaydet()
        return {'ok': True, 'ayarlar': self._ayarlar(), 'kasa': k.bilgi()}

    @disari
    def sifre_degistir(self, eski, yeni):
        k = self._acik(); self._dokun()
        if not k.sifre_dogru(eski): raise K.Hata('Şimdiki şifre yanlış')
        k.sifre_degistir(yeni, self._okul().get('kurum_kodu'))
        return {'ok': True}

    @disari
    def kurtarma_yenile(self, sifre):
        k = self._acik(); self._dokun()
        if not k.sifre_dogru(sifre): raise K.Hata('Şifre yanlış')
        return {'ok': True, 'kurtarma': k.kurtarma_yenile()}

    @disari
    def okul_logo(self):
        k = self._acik(); return {'logo': k.veri.get('okul_logo')}

    @disari
    def okul_logo_yukle(self, veri):
        """data URL (PNG / JPEG); uzun kenar 480 px'e küçültülür."""
        k = self._acik(); self._dokun()
        k.veri['okul_logo'] = _resim_hazirla(veri, 480); k.kaydet()
        return {'ok': True}

    @disari
    def okul_logo_kaldir(self):
        k = self._acik(); self._dokun(); k.veri['okul_logo'] = None; k.kaydet(); return {'ok': True}

    @disari
    def yeni_yil(self, yil, ogrencileri_tasi=False):
        """Yeni öğretim yılı açar ve etkin yıl yapar; eski yıl arşivde okunur kalır (Kayıtlar ve İstatistik'te seçilebilir)."""
        k = self._acik(); self._dokun(); v = k.veri
        if not re.match(r'^\d{4}-\d{4}$', str(yil)) or int(yil[5:]) != int(yil[:4]) + 1: raise K.Hata('Öğretim yılı "2027-2028" biçiminde olmalı')
        if yil in (v.get('yillar') or {}): raise K.Hata(f'{yil} yılı zaten var')
        Y = yeni_yil_verisi()
        if ogrencileri_tasi:
            eski = self._Y()
            Y['ogrenciler'] = [dict(o, sinif='', not_='Önceki yıldan taşındı; sınıfı yeni listeyle gelecek') for o in eski['ogrenciler'] if o.get('durum') != 'ayrildi']
        v['yillar'][yil] = Y; v['yil'] = yil; k.kaydet(); yerel.gunluk('yeni yıl', yil)
        return {'ok': True, 'yil': yil}

    @disari
    def yil_sec(self, yil):
        """Etkin yılı değiştirir (eski yıla dönüp dilekçe yazmak gerekirse)."""
        k = self._acik(); self._dokun()
        if yil not in (k.veri.get('yillar') or {}): raise K.Hata('Böyle bir yıl yok')
        k.veri['yil'] = yil; k.kaydet(); return {'ok': True, 'yil': yil}

    # ------------------------------------------------------------ öğrenciler: e-Okul'dan aktarma
    @disari(kilitsiz=True)
    def dosya_sec(self, tur='pdf', coklu=True):
        """Pencerede sistemin dosya penceresi (kasa kilitliyken de: kurulumda okul bilgisi PDF'ten). Tarayıcı kipinde yollar elle yazılır."""
        if not self._pencere: return {'tarayici': True}
        import webview
        FD = getattr(webview, 'FileDialog', None)
        turler = ('PDF dosyası (*.pdf)', 'Bütün dosyalar (*.*)') if tur == 'pdf' else ('Resim (*.png;*.jpg;*.jpeg)', 'Bütün dosyalar (*.*)')
        r = self._pencere.create_file_dialog(FD.OPEN if FD else webview.OPEN_DIALOG, allow_multiple=bool(coklu), file_types=turler)
        self._dokun()
        return {'yollar': [r] if isinstance(r, str) else list(r or [])}

    @disari(kilitsiz=True)
    def eokul_sec(self):
        self._acik(); self._dokun()
        return self.dosya_sec('pdf', True)

    @disari
    def resim_oku(self, yol):
        """Pencerede seçilen resim dosyasını data URL olarak döner (logo, fotoğraf)."""
        self._acik(); self._dokun()
        import mimetypes
        yol = str(yol).strip().strip('"'); tur = mimetypes.guess_type(yol)[0] or 'image/png'
        with open(yol, 'rb') as f: ham = f.read()
        if len(ham) > 15_000_000: raise K.Hata('Resim çok büyük (15 MB sınırı)')
        return {'veri': f'data:{tur};base64,' + base64.b64encode(ham).decode('ascii')}

    @disari
    def eokul_oku(self, yollar, fotograf=None):
        """Seçilen PDF'leri okur, kasaya yazmadan ne geleceğini söyler. Okunan bellekte bekler (eokul_aktar)."""
        k = self._acik(); self._dokun()
        fotograf = self._ayarlar().get('fotograf') if fotograf is None else bool(fotograf)
        yollar = [str(y).strip().strip('"') for y in (yollar or []) if str(y).strip()]
        if not yollar: raise K.Hata('PDF seçilmedi')
        raporlar = []
        for y in yollar:
            try: raporlar.append(E.oku(y, fotograf))
            except E.Hata as e:
                raporlar.append({'dosya': os.path.basename(y), 'tur': None, 'tur_ad': 'Okunamadı', 'sayfa': 0, 'kullanilir': False, 'neden': str(e)})
            except Exception as e:
                yerel.gunluk('e-Okul okunamadı', hata_izi(e))
                raporlar.append({'dosya': os.path.basename(y), 'tur': None, 'tur_ad': 'Okunamadı', 'sayfa': 0, 'kullanilir': False,
                                 'neden': f'Bu PDF beklenen e-Okul düzeninde okunamadı ({e.__class__.__name__}). Raporu e-Okul\'dan yeniden alıp deneyin.'})
        Y = self._Y()
        ogrenciler, siniflar, ozet = E.birlestir(Y['ogrenciler'], [r for r in raporlar if r.get('kullanilir')])
        self._eokul = {'raporlar': raporlar, 'ogrenciler': ogrenciler, 'siniflar': siniflar, 'ozet': ozet, 'zaman': time.time()}
        okul_oneri = next((r['okul'] for r in raporlar if r.get('okul')), None)
        return {'ok': True, 'ozet': ozet, 'siniflar': sorted(siniflar.values(), key=lambda s: (s['seviye'], s['sube'], s['alan'])),
                'raporlar': [{'dosya': r['dosya'], 'tur_ad': r['tur_ad'], 'sayfa': r.get('sayfa', 0), 'kullanilir': r.get('kullanilir'), 'neden': r.get('neden'),
                              'sinif': (r.get('sinif') or {}).get('sinif'), 'alan': (r.get('sinif') or {}).get('alan'), 'n': len(r.get('ogrenciler') or r.get('kimlik') or []),
                              'uyarilar': r.get('uyarilar') or []} for r in raporlar],
                'okul_oneri': okul_oneri, 'tehlike': ozet['ayrilan'] >= 10 or ozet['tasinan'] >= 3}

    @disari
    def eokul_aktar(self, onay=False):
        """Okunanı kasaya yazar."""
        k = self._acik(); self._dokun()
        if not self._eokul: raise K.Hata('Önce PDF okutun')
        oz = self._eokul['ozet']
        if (oz['ayrilan'] >= 10 or oz['tasinan'] >= 3) and not onay:
            return {'onay_gerek': True, 'ozet': oz}
        Y = self._Y()
        Y['ogrenciler'] = self._eokul['ogrenciler']
        S = Y.setdefault('siniflar', {}); S.update(self._eokul['siniflar'])
        Y['eokul'] = {'aktarma': time.strftime('%Y-%m-%d %H:%M'), 'raporlar': [{'dosya': r['dosya'], 'tur': r.get('tur'), 'sinif': (r.get('sinif') or {}).get('sinif')}
                                                                               for r in self._eokul['raporlar'] if r.get('kullanilir')], 'ozet': oz}
        self._eokul = None; k.kaydet(); yerel.gunluk('e-Okul aktarıldı', oz['yeni'], oz['guncellenen'], oz['ayrilan'])
        return {'ok': True, 'ozet': oz}

    # ------------------------------------------------------------ öğrenciler
    @disari
    def ogrenciler(self, yil=None):
        k = self._acik(); self._dokun(); Y = self._Y(yil); S = Y.get('siniflar') or {}
        L = []
        for o in sorted(Y['ogrenciler'], key=lambda o: (OG.sinif_sirasi(o.get('sinif')), str(o['no']).zfill(6))):
            s = self._sinif(o, Y)
            L.append({'no': o['no'], 'ad': o['ad'], 'ad_kisa': OG.ad_kisa(o), 'sinif': o.get('sinif'), 'sinif_ad': s['sinif'], 'sinif_kisa': s['kisa'],
                      'cinsiyet': o.get('cinsiyet'), 'durum': o.get('durum'), 'kaynak': o.get('kaynak'), 'veli': o.get('veli'), 'velisi_kim': o.get('velisi_kim'),
                      'foto_var': bool(o.get('foto')), 'tc_var': bool(o.get('tc'))})
        siniflar = sorted(S.values(), key=lambda s: (s['seviye'], s['sube'], s['alan']))
        return {'ogrenciler': L, 'siniflar': siniflar, 'eokul': Y.get('eokul') or {}}

    @disari
    def ogrenci(self, no):
        self._acik(); self._dokun()
        return {'ogrenci': self._ogr_paket(self._ogr(no))}

    @disari
    def ara(self, sorgu):
        self._acik(); self._dokun(); Y = self._Y()
        return {'sonuc': [self._ogr_paket(o, Y) | {'foto': None} for o in OG.ara(Y['ogrenciler'], sorgu)]}

    @disari
    def ogrenci_kaydet(self, g, eski_no=None):
        """Elle ekleme (eski_no None) ya da düzeltme."""
        k = self._acik(); self._dokun(); Y = self._Y()
        g = dict(g or {}, eski_no=eski_no)
        d = OG.duzelt(g, [o for o in Y['ogrenciler'] if eski_no is None or str(o['no']) != str(eski_no)], Y.get('siniflar') or {})
        simdi = datetime.datetime.now().isoformat(timespec='seconds')
        if eski_no is None:
            o = dict(d, foto=None, foto_donus=0, durum='aktif', kaynak='elle', ekleme=simdi, guncelleme=simdi); Y['ogrenciler'].append(o)
        else:
            o = self._ogr(eski_no, Y)
            if str(o['no']) != str(d['no']):                      # numara değişti: izinler ve belgeler yeni numaraya
                for i in Y['izinler']:
                    if str(i['ogrenci_no']) == str(o['no']): i['ogrenci_no'] = d['no']
                for b in Y['belgeler']:
                    if str(b['ogrenci_no']) == str(o['no']): b['ogrenci_no'] = d['no']
            o.update(d); o['guncelleme'] = simdi
            if o.get('kaynak') == 'eokul': o['kaynak'] = 'eokul+elle'
        k.kaydet()
        return {'ok': True, 'ogrenci': self._ogr_paket(o, Y)}

    @disari
    def ogrenci_sil(self, no, onay=False):
        """Dilekçesi olan öğrenci silinmez, 'ayrıldı' yapılır (kayıtlar adsız kalmasın)."""
        k = self._acik(); self._dokun(); Y = self._Y(); o = self._ogr(no, Y)
        kayit = any(str(i['ogrenci_no']) == str(no) for i in Y['izinler']) or any(str(b['ogrenci_no']) == str(no) for b in Y['belgeler'])
        if kayit:
            o['durum'] = 'ayrildi'; o['guncelleme'] = datetime.datetime.now().isoformat(timespec='seconds'); k.kaydet()
            return {'ok': True, 'ayrildi': True}
        Y['ogrenciler'] = [x for x in Y['ogrenciler'] if str(x['no']) != str(no)]; k.kaydet()
        return {'ok': True, 'silindi': True}

    @disari
    def ogrenci_durum(self, no, durum):
        k = self._acik(); self._dokun(); o = self._ogr(no)
        if durum not in ('aktif', 'ayrildi'): raise K.Hata('Geçersiz durum')
        o['durum'] = durum; k.kaydet(); return {'ok': True}

    @disari
    def foto_dondur(self, no):
        k = self._acik(); self._dokun(); o = self._ogr(no)
        if not o.get('foto'): raise K.Hata('Bu öğrencinin fotoğrafı yok')
        o['foto_donus'] = (int(o.get('foto_donus') or 0) + 90) % 360; k.kaydet()
        return {'ok': True, 'foto_donus': o['foto_donus']}

    @disari
    def foto_yukle(self, no, veri):
        k = self._acik(); self._dokun(); o = self._ogr(no)
        o['foto'] = _resim_hazirla(veri, E.FOTO_EN_YUKSEK); o['foto_donus'] = 0; k.kaydet(); return {'ok': True}

    @disari
    def foto_kaldir(self, no):
        k = self._acik(); self._dokun(); o = self._ogr(no); o['foto'] = None; o['foto_donus'] = 0; k.kaydet(); return {'ok': True}

    # ------------------------------------------------------------ dilekçe
    def _izin_hazirla(self, izin):
        Y = self._Y(); d = IZ.duzelt(izin); o = self._ogr(d['ogrenci_no'], Y); s = self._sinif(o, Y); a = self._ayarlar()
        onceki = [i for i in Y['izinler'] if str(i['ogrenci_no']) == str(o['no']) and not i.get('silindi') and i.get('id') != izin.get('id')]
        metin = IZ.metin(a.get('dilekce_metin'), d, {'ad': o['ad'], 'sinif': s['sinif'], 'no': o['no']})
        return d, o, s, {'metin': metin, 'tarihler': IZ.tarihler_cumlesi(d['gunler']), 'toplam_metni': IZ.toplam_metni(d['toplam']),
                         'gunler_listesi': IZ.gunler_listesi(d['gunler']), 'gruplar': IZ.gruplar(d['gunler']), 'toplam': d['toplam'],
                         'uyarilar': IZ.uyarilar(d, onceki, {'ozursuz': a.get('sinir_ozursuz'), 'toplam': a.get('sinir_toplam')}),
                         'yon': d['yon'], 'antet': BL.antet(self._okul(), hitap=True), 'konu': a.get('dilekce_konu') or IZ.VARSAYILAN_KONU,
                         'tarih_uzun': IZ.tarih_uzun(d['tarih']), 'ogrenci': self._ogr_paket(o, Y) | {'foto': None}}

    @disari
    def izin_onizle(self, izin):
        """Form her değiştiğinde: denetim, dilekçe metni ve uyarılar (kaydetmez). Eksik alanda {hata, alan} döner."""
        self._acik(); self._dokun()
        d, o, s, p = self._izin_hazirla(izin)
        return {'ok': True, **p}

    @disari
    def izin_kaydet(self, izin, yazdir=True):
        """Kaydeder, PDF'i yazar, isterse yazdırır. Var olan kayıt (izin.id) güncellenir: aynı kayıt no, yeni PDF."""
        k = self._acik(); self._dokun(); Y = self._Y(); yil = self._yil()
        d, o, s, p = self._izin_hazirla(izin)
        if p['uyarilar'] and not izin.get('uyarilari_gordum'): return {'uyari_gerek': True, 'uyarilar': p['uyarilar']}
        simdi = datetime.datetime.now().isoformat(timespec='seconds')
        kayit = next((i for i in Y['izinler'] if i.get('id') == izin.get('id')), None) if izin.get('id') else None
        if kayit is None:
            Y['sayac']['izin'] = Y['sayac'].get('izin', 0) + 1
            kayit = {'id': f'{yil}-{Y["sayac"]["izin"]:04d}-{int(time.time())}', 'no': Y['sayac']['izin'], 'olusturma': simdi}
            Y['izinler'].insert(0, kayit)
        kayit.update(d); kayit['guncelleme'] = simdi; kayit['yil'] = yil
        kayit['ogrenci'] = {'no': o['no'], 'ad': o['ad'], 'sinif': o.get('sinif'), 'sinif_kisa': s['kisa']}      # o günkü kopya
        kayit['no_metni'] = self._kayit_no(kayit['no'], yil)
        yol = self._dilekce_pdf(kayit, o, s)
        k.kaydet()
        sonuc = {'ok': True, 'id': kayit['id'], 'no': kayit['no'], 'no_metni': kayit['no_metni'], 'pdf': yol, 'uyarilar': p['uyarilar']}
        if yazdir: sonuc['yazdirma'] = self._yazdir(yol)
        return sonuc

    def _kayit_no(self, n, yil):
        return f"{yil[:4]}-{yil[-2:]}/{n:04d}"

    def _dilekce_pdf(self, kayit, o, s):
        yol = os.path.join(BL.klasor(kayit['yil']), 'Dilekçeler', BL.dosya_adi(f"{kayit['no']:04d} {o['no']} {OG.ad_kisa(o)} {kayit['tarih']}") + '.pdf')
        BL.dilekce(yol, self._okul(), self._ayarlar(), kayit, o, s, self._kasa.veri.get('okul_logo'))
        return yol

    def _yazdir(self, yol):
        if self._ayarlar().get('yazdirma') == 'ac':
            BL.ac(yol); return 'acildi'
        return BL.yazdir(yol)

    @disari
    def izin_yazdir(self, id):
        """Kayıtlar'dan yeniden yazdırma: PDF yoksa yeniden üretilir."""
        k = self._acik(); self._dokun(); Y = self._Y(); kayit = next((i for i in Y['izinler'] if i.get('id') == id), None)
        if not kayit: raise K.Hata('Kayıt bulunamadı')
        o = self._ogr(kayit['ogrenci_no'], Y); s = self._sinif(o, Y)
        yol = self._dilekce_pdf(kayit, o, s)
        return {'ok': True, 'pdf': yol, 'yazdirma': self._yazdir(yol)}

    @disari
    def izin_ac(self, id):
        """PDF'i sistemin okuyucusunda açar (yazdırmadan bakmak için)."""
        self._acik(); self._dokun(); Y = self._Y(); kayit = next((i for i in Y['izinler'] if i.get('id') == id), None)
        if not kayit: raise K.Hata('Kayıt bulunamadı')
        o = self._ogr(kayit['ogrenci_no'], Y); s = self._sinif(o, Y)
        yol = self._dilekce_pdf(kayit, o, s)
        if self._pencere is not None: BL.ac(yol)
        return {'ok': True, 'pdf': yol}

    @disari
    def izinler(self, yil=None, sorgu='', sinif='', ay=''):
        self._acik(); self._dokun(); Y = self._Y(yil); q = OG.norm(sorgu)
        L = []
        for i in Y['izinler']:
            if i.get('silindi'): continue
            og = i.get('ogrenci') or {}
            if sinif and og.get('sinif_kisa') != sinif: continue
            if ay and not (i.get('tarih') or '').startswith(ay): continue
            v = i.get('veli') or {}
            if q and q not in OG.norm(f"{og.get('ad', '')} {og.get('no', '')} {v.get('ad', '')} {v.get('yakinlik', '')} {v.get('yakinlik_aciklama', '')} {i.get('neden', '')}"): continue
            L.append({'id': i['id'], 'no': i['no'], 'no_metni': i.get('no_metni'), 'tarih': i['tarih'], 'tarih_kisa': IZ.tarih_kisa(i['tarih']),
                      'ogrenci': og, 'veli': i.get('veli'), 'neden': i.get('neden'), 'neden_kodu': i.get('neden_kodu'), 'gunler': i.get('gunler'),
                      'gunler_listesi': IZ.gunler_listesi(i.get('gunler') or {}), 'toplam': i.get('toplam'), 'toplam_metni': IZ.sayi_metni(i.get('toplam') or 0), 'yon': i.get('yon')})
        siniflar = sorted({(i.get('ogrenci') or {}).get('sinif_kisa') for i in Y['izinler'] if not i.get('silindi') and (i.get('ogrenci') or {}).get('sinif_kisa')})
        aylar = sorted({(i.get('tarih') or '')[:7] for i in Y['izinler'] if not i.get('silindi')}, reverse=True)
        return {'izinler': L, 'siniflar': siniflar, 'aylar': aylar, 'yil': yil or self._yil()}

    @disari
    def izin(self, id):
        self._acik(); self._dokun(); Y = self._Y(); kayit = next((i for i in Y['izinler'] if i.get('id') == id), None)
        if not kayit: raise K.Hata('Kayıt bulunamadı')
        return {'izin': kayit}

    @disari
    def izin_sil(self, id):
        k = self._acik(); self._dokun(); Y = self._Y()
        n = len(Y['izinler']); Y['izinler'] = [i for i in Y['izinler'] if i.get('id') != id]
        if len(Y['izinler']) == n: raise K.Hata('Kayıt bulunamadı')
        k.kaydet(); return {'ok': True}

    # ------------------------------------------------------------ öğrenci belgesi
    @disari
    def ogrenci_belgesi(self, no, kisi=None, yazdir=True, kaydet_alanlar=True):
        """Tek tıkla öğrenci belgesi. kisi: elle tamamlanan alanlar {tc, dogum_yeri, dal, burslu}; kaydet_alanlar ile öğrenciye yazılır."""
        k = self._acik(); self._dokun(); Y = self._Y(); yil = self._yil(); o = self._ogr(no, Y); s = self._sinif(o, Y); a = self._ayarlar()
        kisi = dict(kisi or {})
        if 'tc' in kisi:
            t = E.tc_denetle(kisi['tc'])
            if t is None: raise K.Hata('T.C. kimlik numarası 11 haneli ve geçerli olmalı')
            kisi['tc'] = t
        for ad in ('dogum_yeri', 'dal'):
            if ad in kisi: kisi[ad] = E.buyuk(' '.join(str(kisi[ad] or '').split()))[:80] if ad == 'dogum_yeri' else ' '.join(str(kisi[ad] or '').split())[:80]
        if 'burslu' in kisi: kisi['burslu'] = ' '.join(str(kisi['burslu'] or '').split())[:30]
        eksik = [ad for ad in ('tc', 'dogum_yeri', 'dogum', 'baba', 'anne') if not (kisi.get(ad) or o.get(ad))]
        if eksik and not kisi.get('eksikleri_gordum'):
            return {'eksik': eksik, 'ogrenci': self._ogr_paket(o, Y) | {'foto': None}}
        if kaydet_alanlar:
            for ad in ('tc', 'dogum_yeri', 'dal'):
                if kisi.get(ad): o[ad] = kisi[ad]
        tarih = isgunu.bugun().isoformat()
        Y['sayac']['belge'] = Y['sayac'].get('belge', 0) + 1
        b = {'id': f'{yil}-B{Y["sayac"]["belge"]:04d}-{int(time.time())}', 'no': Y['sayac']['belge'], 'tur': 'ogrenci_belgesi', 'tarih': tarih,
             'ogrenci_no': o['no'], 'ogrenci': {'no': o['no'], 'ad': o['ad'], 'sinif_kisa': s['kisa']}, 'olusturma': datetime.datetime.now().isoformat(timespec='seconds')}
        Y['belgeler'].insert(0, b)
        yol = os.path.join(BL.klasor(yil), 'Öğrenci belgeleri', BL.dosya_adi(f"{b['no']:04d} {o['no']} {OG.ad_kisa(o)} {tarih}") + '.pdf')
        BL.ogrenci_belgesi(yol, self._okul(), a, o, s, tarih, kisi)
        k.kaydet()
        sonuc = {'ok': True, 'id': b['id'], 'pdf': yol}
        if yazdir: sonuc['yazdirma'] = self._yazdir(yol)
        return sonuc

    @disari
    def belgeler(self, yil=None):
        self._acik(); self._dokun(); Y = self._Y(yil)
        return {'belgeler': [b for b in Y['belgeler'] if not b.get('silindi')]}

    @disari
    def belge_sil(self, id):
        k = self._acik(); self._dokun(); Y = self._Y()
        Y['belgeler'] = [b for b in Y['belgeler'] if b.get('id') != id]; k.kaydet(); return {'ok': True}

    # ------------------------------------------------------------ istatistik ve belgeler klasörü
    @disari
    def istatistik(self, yil=None):
        self._acik(); self._dokun(); yil = yil or self._yil()
        return {'ok': True, **IS.hesapla(self._Y(yil), yil, isgunu.bugun())}

    @disari
    def istatistik_csv(self, yil=None):
        self._acik(); self._dokun(); yil = yil or self._yil()
        yol = os.path.join(BL.klasor(yil), BL.dosya_adi(f'Veli izin kayıtları {yil} ({isgunu.bugun().isoformat()})') + '.csv')
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, 'w', encoding='utf-8', newline='') as f: f.write(IS.csv_metni(self._Y(yil), yil))
        if self._pencere is not None: BL.ac(yol)
        return {'ok': True, 'dosya': yol}

    @disari
    def belgeleri_sil(self):
        self._acik(); self._dokun(); return {'ok': True, 'silinen': BL.belgeleri_sil()}

    @disari
    def belge_klasoru_ac(self):
        self._acik(); self._dokun(); k = BL.klasor(); os.makedirs(k, exist_ok=True)
        if self._pencere is not None: BL.ac(k)
        return {'ok': True, 'klasor': k}

    # ------------------------------------------------------------ hakkında
    @disari(kilitsiz=True)
    def hakkinda(self):
        return {'ad': surum.AD, 'tam_ad': surum.TAM_AD, 'surum': surum.SURUM, 'tarih': surum.TARIH, 'gelistirici': surum.GELISTIRICI, 'telif': surum.TELIF,
                'site': surum.SITE, 'destek': surum.DESTEK_EPOSTA, 'gunluk': os.path.join(yerel.ayar_klasoru(), yerel.GUNLUK), 'belgeler': BL.klasor()}

    @disari(kilitsiz=True)
    def dis_ac(self, ne):
        """Hakkında: site ya da destek e-postası (adres arayüzden alınmaz)."""
        import webbrowser
        adres = {'site': surum.SITE, 'eposta': 'mailto:' + surum.DESTEK_EPOSTA, 'indir': surum.INDIRME_SAYFASI}.get(ne)
        if not adres: raise K.Hata('Bilinmeyen adres')
        webbrowser.open(adres); return {'ok': True}


def _resim_hazirla(veri, en_uzun):
    """data URL → JPEG / PNG data URL, uzun kenar en_uzun px (saydam kenar PNG'de korunur)."""
    try:
        import io
        from PIL import Image
        if not isinstance(veri, str) or ',' not in veri: raise ValueError
        ham = base64.b64decode(veri.split(',', 1)[1])
        im = Image.open(io.BytesIO(ham)); im.load()
        saydam = im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info)
        im = im.convert('RGBA' if saydam else 'RGB')
        if saydam:
            bbox = im.getbbox()
            if bbox: im = im.crop(bbox)
        im.thumbnail((en_uzun, en_uzun))
        b = io.BytesIO()
        if saydam: im.save(b, 'PNG', optimize=True); tur = 'image/png'
        else: im.save(b, 'JPEG', quality=86, optimize=True); tur = 'image/jpeg'
        return f'data:{tur};base64,' + base64.b64encode(b.getvalue()).decode('ascii')
    except Exception:
        raise K.Hata('Resim okunamadı (PNG ya da JPEG olmalı)')


# ------------------------------------------------------------------ pencere ve tarayıcı kipi
def arayuz_yolu():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arayuz.html')


def _acilis_kapat():
    try:
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass


PENCERE_DILI = {'global.quitConfirmation': f'Kaydetmediğiniz bir değişiklik var. {surum.AD} kapatılırsa bu değişiklik kaybolur. Yine de kapatılsın mı?',
                'global.ok': 'Tamam', 'global.quit': 'Kapat', 'global.cancel': 'Vazgeç', 'global.saveFile': 'Dosyayı kaydet',
                'windows.fileFilter.allFiles': 'Bütün dosyalar', 'windows.fileFilter.otherFiles': 'Öteki dosya türleri'}
WEBVIEW2_ADRES = 'https://go.microsoft.com/fwlink/p/?LinkId=2124703'


def _webview2_var():
    if sys.platform != 'win32': return True
    try:
        from webview.platforms import winforms
        if getattr(winforms, 'is_chromium', True): return True
    except Exception:
        return True
    yerel.gunluk('WebView2 yok: pencere açılmadı')
    try:
        import ctypes
        r = ctypes.windll.user32.MessageBoxW(None, f'{surum.AD} bu bilgisayarda "Microsoft Edge WebView2" bileşenini istiyor; bileşen bulunamadı.\n\n'
                                                   f'Tamam\'a basınca Microsoft\'un indirme sayfası açılır. Kurduktan sonra {surum.AD}\'i yeniden açın.', surum.AD, 0x41)
        if r == 1: os.startfile(WEBVIEW2_ADRES)
    except Exception:
        pass
    return False


def pencere(api):
    import webview
    from uygulama import tek_ornek
    if getattr(sys, 'frozen', False) and not tek_ornek.kilit_al():
        _acilis_kapat(); tek_ornek.one_getir(); yerel.gunluk('ikinci açılış: açık pencere öne getirildi'); return
    if not _webview2_var(): return
    w = webview.create_window(tek_ornek.BASLIK, arayuz_yolu(), js_api=api, width=1320, height=840, min_size=(1000, 640),
                              maximized=True, text_select=True, confirm_close=False)
    api._pencere = w
    w.events.shown += _acilis_kapat
    webview.start(localization=PENCERE_DILI)


def paket_gunlugu():
    if not getattr(sys, 'frozen', False): return
    try:
        y = os.path.join(yerel.ayar_klasoru(), 'logos-veli-izin.log')
        if os.path.exists(y) and os.path.getsize(y) > 2_000_000: os.replace(y, y + '.eski')
        f = open(y, 'a', encoding='utf-8', buffering=1)
        f.write(f"\n---- {surum.AD} {surum.SURUM} başladı {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        sys.stdout = sys.stderr = f
    except OSError:
        if sys.stdout is None: sys.stdout = sys.stderr = open(os.devnull, 'w')


def tarayici(api, port):
    """Geliştirme ve sınama kipi: yalnız bu bilgisayardan (127.0.0.1) erişilir."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    adlar = {a for a in dir(Api) if not a.startswith('_') and getattr(getattr(Api, a), '_disari', False)}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def _gonder(self, kod, govde, tur):
            self.send_response(kod); self.send_header('Content-Type', tur); self.send_header('Cache-Control', 'no-store')
            self.end_headers(); self.wfile.write(govde)

        def do_GET(self):
            if self.path not in ('/', '/index.html'): return self._gonder(404, b'yok', 'text/plain')
            with open(arayuz_yolu(), encoding='utf-8') as f: s = f.read()
            s = s.replace('</head>', '<script>window.LV_TARAYICI = true</script></head>', 1)
            self._gonder(200, s.encode('utf-8'), 'text/html; charset=utf-8')

        def _yerel_mi(self):
            izin = {f'127.0.0.1:{port}', f'localhost:{port}'}
            o = self.headers.get('Origin')
            return self.headers.get('Host') in izin and (not o or o.split('//', 1)[-1] in izin)

        def do_POST(self):
            ad = self.path.rsplit('/', 1)[-1]
            if not self._yerel_mi(): return self._gonder(403, b'{}', 'application/json')
            if not self.path.startswith('/api/') or ad not in adlar: return self._gonder(404, b'{}', 'application/json')
            n = int(self.headers.get('Content-Length') or 0)
            try: args = json.loads(self.rfile.read(n) or b'[]')
            except ValueError: args = []
            r = getattr(api, ad)(*args)
            self._gonder(200, json.dumps(r, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')

    s = ThreadingHTTPServer(('127.0.0.1', port), H)
    print(f'{surum.AD} {surum.SURUM}: http://127.0.0.1:{port}', flush=True)
    s.serve_forever()


def main(argv=None):
    p = argparse.ArgumentParser(prog='LOGOS Veli İzin')
    p.add_argument('--tarayici', type=int, default=None, help='port; pencere yerine yerel sunucu')
    p.add_argument('--kasa', default=None, help='kasa dosyası (varsayılan: son açılan ya da uygulama klasörü)')
    p.add_argument('--surum', action='store_true')
    a, _ = p.parse_known_args(argv)
    if a.surum: print(surum.SURUM); return
    paket_gunlugu()
    api = Api(a.kasa)
    yerel.gunluk(f'{surum.AD} {surum.SURUM} başladı', sys.platform, 'paket' if getattr(sys, 'frozen', False) else 'kaynak', 'tarayıcı' if a.tarayici else 'pencere')
    try:
        if a.tarayici: _acilis_kapat(); tarayici(api, a.tarayici)
        else: pencere(api)
    except Exception:
        yerel.gunluk('AÇILIŞ HATASI', traceback.format_exc()); raise


if __name__ == '__main__':
    main()
