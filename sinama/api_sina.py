"""Api baştan sona (arayüzsüz, kasa gerçek): python -m unittest sinama.api_sina -v
kasa kur → e-Okul aktar (uydurma PDF'ler) → dilekçe (uyarı, kayıt no, PDF içeriği) → yeniden yazdır, sil → öğrenci belgesi (eksik alan,
PDF içeriği) → istatistik ve CSV → kilit (kilitliyken red) → kurtarma anahtarı → kasada ve günlükte açık veri yok."""
import datetime, json, os, shutil, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SIFRE = '2468'


def pdf_metni(yol):
    import pdfplumber
    with pdfplumber.open(yol) as p: return '\n'.join((s.extract_text(x_tolerance=1.5) or '') for s in p.pages)


def okul_gunleri(n, bitis=None):
    from uygulama import isgunu
    d = bitis or isgunu.bugun(); out = []
    while len(out) < n:
        d -= datetime.timedelta(days=1)
        if isgunu.okul_gunu(d): out.append(d.isoformat())
    return sorted(out)


class ApiSina(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp(prefix='lv-api-'); os.environ['LV_AYAR_KLASORU'] = cls.d; os.environ['LV_SINAMA'] = '1'
        from uygulama import ana, yerel
        from sinama import eokul_ornek
        cls.ana = ana; cls.yerel = yerel; cls.pdf = eokul_ornek.uret(os.path.join(cls.d, 'ornek'))
        cls.api = ana.Api(os.path.join(cls.d, 'sinama.lvk'))

    @classmethod
    def tearDownClass(cls):
        os.environ.pop('LV_AYAR_KLASORU', None); shutil.rmtree(cls.d, ignore_errors=True)

    def test_akis(self):
        A = self.api
        b = A.baslangic(); self.assertFalse(b['kasa_var']); self.assertFalse(b['acik'])
        self.assertIn('hata', A.ozet()); self.assertTrue(A.ozet().get('kilit'))                         # kasa yokken her veri çağrısı reddedilir
        # ---- kurulum
        self.assertEqual(A.okul_bilgisi_pdften([self.pdf['9A']])['okul']['ad'], 'Çınar Mesleki Ve Teknik Anadolu Lisesi')
        self.assertIn('hata', A.kasa_olustur({'ad': 'Çınar MTAL', 'il': 'İzmir', 'ilce': 'Konak', 'kurum_kodu': '123456'}, '1234'))     # kurum kodunun parçası
        r = A.kasa_olustur({'ad': 'Çınar Mesleki Ve Teknik Anadolu Lisesi', 'il': 'İzmir', 'ilce': 'Konak', 'kurum_kodu': '123456'}, SIFRE)
        self.assertTrue(r.get('ok'), r); kurtarma = r['kurtarma']; self.assertEqual(len(kurtarma), 39)
        oz = A.ozet(); self.assertEqual(oz['yil'], self.ana.isgunu.ogretim_yili()); self.assertEqual(oz['sayilar']['ogrenci'], 0)
        # ---- e-Okul
        r = A.eokul_oku([self.pdf['9A'], self.pdf['10B'], self.pdf['AL'], self.pdf['kimlik'], os.path.join(self.d, 'yok.pdf')], True)
        self.assertEqual(r['ozet']['yeni'], 24); self.assertEqual(r['ozet']['tc'], 18); self.assertEqual(r['ozet']['foto'], 23)
        self.assertEqual([x['kullanilir'] for x in r['raporlar']], [True, True, True, True, False]); self.assertFalse(r['tehlike'])
        self.assertTrue(A.eokul_aktar()['ok'])
        L = A.ogrenciler(); self.assertEqual(len(L['ogrenciler']), 24); self.assertEqual([s['kisa'] for s in L['siniflar']], ['9A-SH', '10B-HYH', '11C'])
        o = A.ogrenci(902)['ogrenci']; self.assertEqual(o['sinif_kisa'], '9A-SH'); self.assertTrue(o['foto']); self.assertTrue(o['tc'])
        self.assertEqual(o['veli_adaylari'][0]['ad'], 'EMİNE YILDIRIM')
        self.assertEqual([x['no'] for x in A.ara('cigdem')['sonuc']], [902]); self.assertIsNone(A.ara('902')['sonuc'][0]['foto'])     # aramada fotoğraf taşınmaz
        # ---- elle öğrenci, fotoğraf
        r = A.ogrenci_kaydet({'ad': 'Nakil Gelen', 'no': '950', 'sinif': '9/A SAĞLIK HİZMETLERİ', 'cinsiyet': 'K', 'baba': 'Ali', 'anne': 'Ayşe', 'dogum': '2011-01-01'})
        self.assertEqual(r['ogrenci']['ad'], 'NAKİL GELEN'); self.assertEqual(r['ogrenci']['kaynak'], 'elle')
        self.assertIn('hata', A.ogrenci_kaydet({'ad': 'Başka Biri', 'no': '950', 'sinif': '9/A SAĞLIK HİZMETLERİ'}))
        self.assertEqual(A.foto_dondur(902)['foto_donus'], 90); self.assertEqual(A.foto_dondur(902)['foto_donus'], 180)
        self.assertTrue(A.ogrenci_sil(950)['silindi'])
        # ---- dilekçe
        g1, g2 = okul_gunleri(2); bugun = self.ana.isgunu.bugun().isoformat()
        izin = {'ogrenci_no': 902, 'tarih': bugun, 'veli': {'ad': 'EMİNE YILDIRIM', 'yakinlik': 'Anne', 'kayitli': True}, 'gunler': {g1: 'tam', g2: 'sonra'},
                'neden_kodu': 'cenaze', 'neden': 'yakınının vefatı', 'devamsizlik': {'ozurlu': '3', 'ozursuz': '1'}}
        p = A.izin_onizle(izin); self.assertEqual(p['devamsizlik']['ozet']['toplam'], 4); self.assertIsNone(A.izin_onizle(dict(izin, devamsizlik=None))['devamsizlik'])
        self.assertEqual(p['toplam'], 1.5); self.assertIn('yakınının vefatı nedeniyle', p['metin']); self.assertEqual(p['uyarilar'], [])
        self.assertEqual(p['antet'][-1], 'Çınar Mesleki ve Teknik Anadolu Lisesi Müdürlüğüne')
        self.assertEqual(A.izin_onizle(dict(izin, veli={'ad': 'X'}))['alan'], 'veli_ad')
        r = A.izin_kaydet(izin, yazdir=False)
        self.assertTrue(r['no_metni'].endswith('/0001'), r); self.assertTrue(os.path.exists(r['pdf'])); id1 = r['id']
        m = pdf_metni(r['pdf'])
        for s in ('KONAK KAYMAKAMLIĞI', 'ÇİĞDEM DEMİR', '902', 'EMİNE YILDIRIM', 'yakınının vefatı', '1,5 (bir buçuk) gün', '36. maddesi', 'Okul idaresi', 'Kayıt no', 'Devamsızlık durumu (', 'tarihi itibarıyla', 'Özürlü Özürsüz Toplam', '3 gün 1 gün 4 gün',
                  'sınırlara kalan süre', 'devamsızlık durumunu öğrendim'):
            self.assertIn(s, m, s)
        self.assertNotIn('None', m)
        self.assertIn('LOGOS Veli İzin', m); self.assertIn('Kayıt no', m); self.assertTrue(A.ozet()['ayarlar']['kayit_no_goster'])     # Ertan 20:08: ikisi de kalır, kayıt no varsayılan açık
        self.assertIn('(öğrencinin annesi)', m); self.assertIn('Öğrencinin annesi', m); self.assertNotIn('öğrencinin anne)', m)
        # aynı güne ikinci dilekçe: önce uyarı, uyarılar görüldü deyince kayıt
        izin2 = dict(izin, veli={'ad': 'Ayşe Kaya', 'yakinlik': 'Diğer', 'yakinlik_aciklama': 'teyzesi', 'tel': '5321234567', 'tc': '10000000146'}, gunler={g2: 'tam'}, devamsizlik=None)
        r = A.izin_kaydet(izin2, yazdir=False); self.assertTrue(r['uyari_gerek']); self.assertIn('daha önce', r['uyarilar'][0])
        r = A.izin_kaydet(dict(izin2, uyarilari_gordum=True), yazdir=False); self.assertTrue(r['no_metni'].endswith('/0002')); id2 = r['id']
        m = pdf_metni(r['pdf']); self.assertIn('Ayşe Kaya', m); self.assertIn('Öğrencinin teyzesi', m); self.assertIn('0532 123 45 67', m); self.assertIn('10000000146', m)
        # var olan kaydı güncelleme: aynı numara
        r = A.izin_kaydet(dict(izin, id=id1, neden='hastaneye yatışı', uyarilari_gordum=True), yazdir=False); self.assertTrue(r['no_metni'].endswith('/0001'))
        self.assertEqual(A.izin(id1)['izin']['neden'], 'hastaneye yatışı'); self.assertEqual(len(A.izinler()['izinler']), 2)
        self.assertEqual(len(A.izinler(sorgu='teyze')['izinler']), 1); self.assertEqual(len(A.izinler(sinif='9A-SH')['izinler']), 2); self.assertEqual(len(A.izinler(sinif='10B-HYH')['izinler']), 0)
        self.assertTrue(A.izin_yazdir(id2)['pdf']); self.assertTrue(A.izin_sil(id2)['ok']); self.assertIn('hata', A.izin(id2))
        sd = A.ogrenci(902)['ogrenci']['son_devamsizlik']; self.assertEqual((sd['ozurlu'], sd['ozursuz']), (3, 1))                   # bir sonraki dilekçede öneri
        self.assertEqual(A.ogrenci(902)['ogrenci']['izin_sayisi'], 1); self.assertEqual(A.ozet()['sayilar']['izin'], 1)
        # ---- okul logosu: dilekçenin sol üstüne basılır, Ayarlar'dan gizlenir
        import base64, io, pdfplumber
        from PIL import Image
        b = io.BytesIO(); Image.new('RGBA', (300, 200), (200, 30, 30, 255)).save(b, 'PNG')
        self.assertIn('hata', A.okul_logo_yukle('data:image/png;base64,QUJD'))
        self.assertTrue(A.okul_logo_yukle('data:image/png;base64,' + base64.b64encode(b.getvalue()).decode())['ok']); self.assertTrue(A.ozet()['logo'])
        self.assertTrue(A.okul_logo()['logo'].startswith('data:image/png;base64,'))
        def resim_say(y):
            with pdfplumber.open(y) as pp: return len(pp.pages[0].images)
        self.assertEqual(resim_say(A.izin_yazdir(id1)['pdf']), 1)
        A.ayar_kaydet({'logo_goster': False}); self.assertEqual(resim_say(A.izin_yazdir(id1)['pdf']), 0); A.ayar_kaydet({'logo_goster': True})
        # ---- yazdırma önizlemesi (Ertan 04.11.2026: doğrudan yazdırmada kağıt A4 yatay çıkıyordu; "ön izleme çıksa, sonra yazdır desek")
        import base64, io
        from PIL import Image
        self.assertEqual(A.ayar_kaydet({})['ayarlar']['yazdirma'], 'onizle')                                    # yeni kasada varsayılan
        r = A.izin_yazdir(id1); self.assertEqual(r['yazdirma'], 'onizle'); self.assertEqual(len(r['onizleme']), 1)
        im = Image.open(io.BytesIO(base64.b64decode(r['onizleme'][0].split(',', 1)[1]))); w, h = im.size
        self.assertGreater(h, w); self.assertAlmostEqual(w / h, 210 / 297, places=2); self.assertGreaterEqual(w, 2400)   # A4 dikey, 300 dpi
        self.assertTrue(A.pdf_ac(r['pdf'])['ok'])
        for y in (A._yol, os.path.join(self.d, 'yok.pdf'), self.pdf['9A'], ''): self.assertIn('hata', A.pdf_ac(y), y)          # yalnız Belgeler'deki PDF
        A.ayar_kaydet({'yazdirma': 'yazici'}); r = A.izin_yazdir(id1); self.assertEqual(r['yazdirma'], 'sinama'); self.assertNotIn('onizleme', r)
        A.ayar_kaydet({'yazdirma': 'ac'}); self.assertEqual(A.izin_yazdir(id1)['yazdirma'], 'acildi')
        self.assertEqual(A.ayar_kaydet({'yazdirma': 'baska'})['ayarlar']['yazdirma'], 'ac')
        b = A.ogrenci_belgesi(901, {}, yazdir=True)
        A.ayar_kaydet({'yazdirma': 'yazici'}); A._kasa.veri['meta'].pop('onizleme_goc', None); A._kasa.kaydet()   # 1.0.0'ın kasası
        A.kilitle(); A.kilit_ac(SIFRE); self.assertEqual(A.ayar_kaydet({})['ayarlar']['yazdirma'], 'onizle')      # bir kez önizlemeye geçer
        A.ayar_kaydet({'yazdirma': 'yazici'}); A.kilitle(); A.kilit_ac(SIFRE)
        self.assertEqual(A.ayar_kaydet({})['ayarlar']['yazdirma'], 'yazici')                                   # sonra seçilen kalır
        A.ayar_kaydet({'yazdirma': 'onizle'})
        r = A.ogrenci_belgesi(901, {}, yazdir=True); self.assertEqual(r['yazdirma'], 'onizle'); self.assertEqual(len(r['onizleme']), 1)
        A.belge_sil(b['id']); A.belge_sil(r['id'])
        # ---- öğrenci belgesi
        r = A.ogrenci_belgesi(1101, {}, yazdir=False); self.assertEqual(r['eksik'], ['tc'])                     # 11/C kimlik listesinde yok
        self.assertIn('hata', A.ogrenci_belgesi(1101, {'tc': '123', 'eksikleri_gordum': True}, yazdir=False))
        r = A.ogrenci_belgesi(1101, {'tc': '10000000146', 'eksikleri_gordum': True}, yazdir=False); self.assertTrue(r['ok'])
        self.assertEqual(A.ogrenci(1101)['ogrenci']['tc'], '10000000146')                                      # elle yazılan kimlik no öğrenciye kaydedildi
        m = pdf_metni(r['pdf']); o = A.ogrenci(1101)['ogrenci']
        for s in ('ÖĞRENCİ BELGESİ', 'İZMİR VALİLİĞİ', o['ad'], '10000000146', '11. Sınıf / C Şubesi', 'OKUL MÜDÜRÜ', 'MÜDÜR YARDIMCISI'): self.assertIn(s, m, s)
        self.assertNotIn('LOGOS', m)                                                                           # resmî belgede program adı yok
        A.ayar_kaydet({'kayit_no_goster': False}); m = pdf_metni(A.izin_yazdir(id1)['pdf']); self.assertNotIn('Kayıt no', m); self.assertIn('LOGOS Veli İzin', m)
        A.ayar_kaydet({'kayit_no_goster': True})
        r = A.ogrenci_belgesi(901, {}, yazdir=False); self.assertTrue(r['ok']); self.assertEqual(len(A.belgeler()['belgeler']), 2)
        self.assertTrue(A.ogrenci_sil(901)['ayrildi'])                                                         # belgesi olan öğrenci silinmez, ayrıldı olur
        # ---- istatistik
        i = A.istatistik(); self.assertEqual((i['dilekce'], i['gun'], i['ogrenci'], i['ogrenci_belgesi']), (1, 1.5, 1, 2))
        self.assertEqual(i['en_cok'][0]['no'], 902); self.assertEqual(i['siniflar'][0], ['9A-SH', 1.5] if isinstance(i['siniflar'][0], list) else ('9A-SH', 1.5))
        c = A.istatistik_csv(); self.assertTrue(os.path.exists(c['dosya']))
        with open(c['dosya'], encoding='utf-8-sig') as f: csv = f.read()
        self.assertIn('ÇİĞDEM DEMİR', csv); self.assertIn(';', csv); self.assertIn('Özürlü (dilekçe günü)', csv)
        # ---- ayarlar
        self.assertIn('hata', A.ayar_kaydet({'dilekce_metin': 'tarihsiz'})); self.assertIn('hata', A.ayar_kaydet({'kilit_dakika': 7}))
        self.assertEqual(A.ayar_kaydet({'onay_ad': 'Ertan K.', 'kilit_dakika': 0, 'kapali_gunler': [{'bas': g1, 'bit': g1, 'ad': 'Kar'}]})['ayarlar']['onay_ad'], 'Ertan K.')
        self.assertFalse(A.takvim_ay(int(g1[:4]), int(g1[5:7]))['gunler'][g1]['okul'])
        A.ayar_kaydet({'kapali_gunler': []})
        self.assertIn('hata', A.yeni_yil('abc')); y = A.ozet()['yil']; yeni = f'{int(y[:4]) + 1}-{int(y[:4]) + 2}'
        self.assertEqual(A.yeni_yil(yeni, True)['yil'], yeni); self.assertEqual(A.ozet()['yil'], yeni); self.assertEqual(A.ozet()['sayilar']['izin'], 0)
        self.assertEqual(A.ozet()['sayilar']['ogrenci'], 23); self.assertEqual(A.istatistik(y)['dilekce'], 1)
        self.assertTrue(A.yil_sec(y)['ok'])
        # ---- kilit
        self.assertTrue(A.kilitle()['ok']); r = A.ozet(); self.assertTrue(r.get('kilit'))
        self.assertIn('hata', A.izin_kaydet(izin)); self.assertIn('hata', A.ogrenciler())
        self.assertIn('hata', A.kilit_ac('0000')); self.assertTrue(A.kilit_ac(SIFRE)['ok']); self.assertEqual(A.ozet()['sayilar']['izin'], 1)
        A.kilitle(); self.assertTrue(A.kurtarma_ile_ac(kurtarma.lower(), '1357')['ok']); A.kilitle(); self.assertIn('hata', A.kilit_ac(SIFRE)); self.assertTrue(A.kilit_ac('1357')['ok'])
        self.assertTrue(A.hakkinda()['belgeler'])
        # ---- kasa dosyasında ve günlükte açık veri yok
        with open(A._yol, encoding='utf-8') as f: ham = f.read()
        for s in ('ÇİĞDEM', 'DEMİR', 'EMİNE', '10000000146', 'Kaya', SIFRE, '1357'): self.assertNotIn(s, ham, s)
        gunluk = os.path.join(self.d, self.yerel.GUNLUK)
        if os.path.exists(gunluk):
            with open(gunluk, encoding='utf-8') as f: g = f.read()
            for s in ('ÇİĞDEM', 'DEMİR', 'EMİNE', '10000000146'): self.assertNotIn(s, g, s)


if __name__ == '__main__':
    unittest.main(verbosity=2)
