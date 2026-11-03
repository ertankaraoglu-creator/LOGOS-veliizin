"""Dilekçe mantığı (uygulama/izin.py, ogrenci.py, isgunu.py): python -m unittest sinama.izin_sina -v
Tarihler Kasım 2026'ya sabit (2-6 Kasım okul günleri, 7-8 hafta sonu, 16-20 Kasım ara tatil); dilekçe tarihi veriliyor, bugüne bağlı değil."""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from uygulama import izin as IZ, isgunu, ogrenci as OG

OGR = {'no': 902, 'ad': 'ÇİĞDEM DEMİR', 'baba': 'İBRAHİM', 'anne': 'EMİNE', 'veli': 'EMİNE YILDIRIM', 'velisi_kim': 'Anne', 'durum': 'aktif',
       'sinif': '9/A SAĞLIK HİZMETLERİ', 'veli_elle': {'ad': 'AYŞE KAYA', 'yakinlik': 'teyzesi', 'tel': '0532 123 45 67'}}


def izin(**k):
    d = {'ogrenci_no': 902, 'tarih': '2026-11-04', 'veli': {'ad': 'EMİNE YILDIRIM', 'yakinlik': 'Anne'}, 'gunler': {'2026-11-03': 'tam'},
         'neden_kodu': 'hastalik', 'neden': 'rahatsızlığı'}
    d.update(k); return d


class TakvimSina(unittest.TestCase):
    def test_okul_gunu(self):
        self.assertTrue(isgunu.okul_gunu(isgunu._gun('2026-11-03')))
        self.assertFalse(isgunu.okul_gunu(isgunu._gun('2026-11-07')))              # Cumartesi
        self.assertFalse(isgunu.okul_gunu(isgunu._gun('2026-10-29')))              # Cumhuriyet Bayramı
        self.assertFalse(isgunu.okul_gunu(isgunu._gun('2026-11-18')))              # ara tatil
        self.assertFalse(isgunu.okul_gunu(isgunu._gun('2026-07-15')))              # yaz
        self.assertEqual(isgunu.ogretim_yili('2026-10-30'), '2026-2027'); self.assertEqual(isgunu.ogretim_yili('2027-06-15'), '2026-2027')
        self.assertEqual(isgunu.ogretim_yili('2027-09-01'), '2027-2028')

    def test_kapali_gun(self):
        isgunu.ek_ayarla([{'bas': '2026-11-05', 'bit': '2026-11-05', 'ad': 'Kar tatili'}])
        try:
            self.assertFalse(isgunu.okul_gunu(isgunu._gun('2026-11-05'))); self.assertIn('Kar', isgunu.neden(isgunu._gun('2026-11-05')))
        finally: isgunu.ek_ayarla([])
        self.assertTrue(isgunu.okul_gunu(isgunu._gun('2026-11-05')))
        with self.assertRaises(isgunu.Hata): isgunu.ek_duzelt([{'bas': '2026-11-06', 'bit': '2026-11-05', 'ad': 'ters'}])


class MetinSina(unittest.TestCase):
    def test_sayilar(self):
        self.assertEqual(IZ.toplam_metni(1), '1 (bir) gün'); self.assertEqual(IZ.toplam_metni(0.5), 'yarım gün')
        self.assertEqual(IZ.toplam_metni(2.5), '2,5 (iki buçuk) gün'); self.assertEqual(IZ.toplam_metni(10), '10 (on) gün')
        self.assertEqual(IZ.sayi_metni(1.5), '1,5'); self.assertEqual(IZ.gun_sayisi_metni(0.5), 'yarım gün')
        self.assertEqual(IZ.tarih_uzun('2026-11-03'), '3 Kasım 2026'); self.assertEqual(IZ.tarih_uzun('2026-11-03', True), '3 Kasım 2026 Salı')
        self.assertEqual(IZ.tarih_kisa('2026-11-03'), '03.11.2026')

    def test_gruplar_ve_cumle(self):
        g = {'2026-11-02': 'tam', '2026-11-03': 'tam', '2026-11-04': 'tam'}
        self.assertEqual(IZ.tarihler_cumlesi(g), '2-4 Kasım 2026 tarihleri arasında'); self.assertEqual(IZ.toplam(g), 3)
        self.assertEqual(IZ.gunler_listesi(g), '2-4 Kasım 2026 (3 gün)')
        self.assertEqual(IZ.tarihler_cumlesi({'2026-11-03': 'once'}), '3 Kasım 2026 Salı günü öğleden önce')
        g = {'2026-11-06': 'tam', '2026-11-09': 'tam'}                                   # hafta sonu aradan çıkar, aralık sürer
        self.assertEqual(IZ.gruplar(g)[0]['n'], 2); self.assertEqual(IZ.tarihler_cumlesi(g), '6-9 Kasım 2026 tarihleri arasında')
        g = {'2026-11-13': 'tam', '2026-11-23': 'tam'}                                   # ara tatil arada: iki grup
        self.assertEqual(len(IZ.gruplar(g)), 2); self.assertIn(' ve ', IZ.tarihler_cumlesi(g)); self.assertTrue(IZ.tarihler_cumlesi(g).endswith('tarihlerinde'))
        g = {'2026-11-03': 'tam', '2026-11-04': 'sonra'}
        self.assertEqual(IZ.gunler_listesi(g), '3 Kasım 2026 Salı (1 gün); 4 Kasım 2026 Çarşamba, öğleden sonra (yarım gün)'); self.assertEqual(IZ.toplam(g), 1.5)

    def test_yon(self):
        self.assertEqual(IZ.yon({'2026-11-03': 'tam'}, '2026-11-04'), 'geriye'); self.assertEqual(IZ.yon({'2026-11-05': 'tam'}, '2026-11-04'), 'ileriye')
        self.assertEqual(IZ.yon({'2026-11-03': 'tam', '2026-11-05': 'tam'}, '2026-11-04'), 'karisik'); self.assertEqual(IZ.yon({'2026-11-04': 'tam'}, '2026-11-04'), 'bugun')

    def test_metin(self):
        d = IZ.duzelt(izin(gunler={'2026-11-02': 'tam', '2026-11-03': 'tam'}))
        m = IZ.metin(None, d, {'ad': 'ÇİĞDEM DEMİR', 'sinif_ad': '9/A', 'no': 902})
        self.assertIn('rahatsızlığı nedeniyle 2-3 Kasım 2026 tarihleri arasında toplam 2 (iki) gün süreyle', m); self.assertIn('36. maddesi', m)
        m = IZ.metin('{OGRENCI} ({SINIF}, {NO}) {TARIHLER}', d, {'ad': 'ÇİĞDEM DEMİR', 'sinif_ad': '9/A', 'no': 902})
        self.assertEqual(m, 'ÇİĞDEM DEMİR (9/A, 902) 2-3 Kasım 2026 tarihleri arasında')
        with self.assertRaises(IZ.Hata): IZ.metin_denetle('{YOK} nedeniyle {TARIHLER}')
        with self.assertRaises(IZ.Hata): IZ.metin_denetle('tarihsiz cümle')
        with self.assertRaises(IZ.Hata): IZ.metin_denetle('')


class DuzeltSina(unittest.TestCase):
    def test_duzelt(self):
        d = IZ.duzelt(izin(veli={'ad': ' Ayşe  Kaya ', 'yakinlik': 'Diğer', 'yakinlik_aciklama': 'teyzesi', 'tel': '5321234567', 'tc': '10000000146'},
                           gunler={'2026-11-03': 'tam', '2026-11-02': 'sonra'}, devamsizlik={'ozurlu': '4,5', 'ozursuz': '2'}))
        self.assertEqual(d['veli'], {'ad': 'Ayşe Kaya', 'yakinlik': 'Diğer', 'yakinlik_aciklama': 'teyzesi', 'tc': '10000000146', 'tel': '0532 123 45 67', 'kayitli': False})
        self.assertEqual(list(d['gunler']), ['2026-11-02', '2026-11-03']); self.assertEqual(d['toplam'], 1.5); self.assertEqual(d['yon'], 'geriye')
        self.assertEqual(d['devamsizlik'], {'ozurlu': 4.5, 'ozursuz': 2.0})
        self.assertEqual(IZ.tel_duzelt('+90 532 123 45 67'), '0532 123 45 67'); self.assertEqual(IZ.tel_duzelt(''), '')

    def test_hatalar(self):
        for k, alan in ((dict(veli={'ad': 'A', 'yakinlik': 'Anne'}), 'veli_ad'), (dict(veli={'ad': 'Ayşe Kaya', 'yakinlik': 'Diğer'}), 'veli_yakinlik'),
                        (dict(veli={'ad': 'Ayşe Kaya', 'yakinlik': 'Anne', 'tc': '123'}), 'veli_tc'), (dict(gunler={}), 'gunler'),
                        (dict(gunler={'2026-11-07': 'tam'}), 'gunler'), (dict(gunler={'2026-11-18': 'tam'}), 'gunler'), (dict(gunler={'abc': 'tam'}), 'gunler'),
                        (dict(neden='  '), 'neden'), (dict(tarih='dün'), 'tarih'), (dict(devamsizlik={'ozurlu': 'çok'}), 'devamsizlik'), (dict(ogrenci_no=None), 'ogrenci')):
            with self.assertRaises(IZ.Hata, msg=str(k)) as c: IZ.duzelt(izin(**k))
            self.assertEqual(c.exception.alan, alan, str(k))
        with self.assertRaises(IZ.Hata): IZ.duzelt(izin(gunler={f'2026-{m:02d}-{g:02d}': 'tam' for m in (10, 11, 12, 1, 2, 3) for g in range(1, 29)}))

    def test_uyarilar(self):
        d = IZ.duzelt(izin())
        self.assertEqual(IZ.uyarilar(d, [], {'ozursuz': 10, 'toplam': 30}), [])
        u = IZ.uyarilar(d, [{'gunler': {'2026-11-03': 'tam'}}], {})
        self.assertEqual(len(u), 1); self.assertIn('3 Kasım 2026', u[0]); self.assertIn('daha önce', u[0])
        d = IZ.duzelt(izin(gunler={'2026-10-05': 'tam'}, tarih='2026-11-04'))                 # 5 iş gününden çok geçmiş özür beyanı
        self.assertTrue(any('md. 36' in x for x in IZ.uyarilar(d, [])))
        d = IZ.duzelt(izin(gunler={'2026-10-28': 'tam'}, tarih='2026-11-04'))                 # bayram ve hafta sonu sayılmaz: 5 iş günü
        self.assertEqual(IZ.uyarilar(d, []), [])
        d = IZ.duzelt(izin(devamsizlik={'ozurlu': '20', 'ozursuz': '10'}))
        u = IZ.uyarilar(d, [], {'ozursuz': 10, 'toplam': 30})
        self.assertEqual(len(u), 2); self.assertIn('Özürsüz', u[0]); self.assertIn('31 güne', u[1])


class OgrenciSina(unittest.TestCase):
    def test_ara(self):
        L = [OGR, {'no': 1001, 'ad': 'EMİR ŞAHİN', 'durum': 'aktif'}, {'no': 910, 'ad': 'ÖYKÜ DEMİR', 'durum': 'ayrildi'}]
        self.assertEqual([o['no'] for o in OG.ara(L, 'cigdem')], [902]); self.assertEqual([o['no'] for o in OG.ara(L, 'DEMİR')], [902])     # ayrılan çıkmaz
        self.assertEqual([o['no'] for o in OG.ara(L, '90')], [902]); self.assertEqual([o['no'] for o in OG.ara(L, 'sahin 1001')], [1001])
        self.assertEqual(OG.ara(L, 'yok'), []); self.assertEqual(OG.ara(L, ''), [])
        self.assertEqual(OG.norm('ÖZTÜRK Işıl'), 'ozturk isil')

    def test_veli_adaylari(self):
        A = OG.veli_adaylari(OGR)
        self.assertEqual([(a['ad'], a['yakinlik'], a['kayitli']) for a in A],
                         [('EMİNE YILDIRIM', 'Anne', True), ('İBRAHİM DEMİR', 'Baba', False), ('AYŞE KAYA', 'teyzesi', False)])
        self.assertEqual(A[2]['tel'], '0532 123 45 67')
        A = OG.veli_adaylari({'no': 1, 'ad': 'EMİR ŞAHİN', 'baba': 'HALİL', 'anne': 'NURAY', 'veli': '', 'velisi_kim': ''})
        self.assertEqual([a['ad'] for a in A], ['NURAY ŞAHİN', 'HALİL ŞAHİN'])
        A = OG.veli_adaylari({'no': 1, 'ad': 'EMİR ŞAHİN', 'baba': 'HALİL', 'anne': 'NURAY', 'veli': 'KEMAL ÖZ', 'velisi_kim': 'Vasi'})
        self.assertEqual([(a['ad'], a['yakinlik']) for a in A], [('KEMAL ÖZ', 'Vasi'), ('NURAY ŞAHİN', 'Anne'), ('HALİL ŞAHİN', 'Baba')])

    def test_duzelt(self):
        S = {'9/A SAĞLIK HİZMETLERİ': {}}
        d = OG.duzelt({'ad': 'ali veli', 'no': '77', 'tc': '', 'cinsiyet': 'e', 'sinif': '9/A SAĞLIK HİZMETLERİ', 'dogum': '2011-05-01', 'baba': 'can'}, [OGR], S)
        self.assertEqual((d['ad'], d['no'], d['cinsiyet'], d['baba'], d['dogum']), ('ALİ VELİ', 77, 'E', 'CAN', '2011-05-01'))
        for g, alan in (({'ad': 'Ali', 'no': '77', 'sinif': '9/A SAĞLIK HİZMETLERİ'}, 'ad'), ({'ad': 'Ali Veli', 'no': 'x', 'sinif': '9/A SAĞLIK HİZMETLERİ'}, 'no'),
                        ({'ad': 'Ali Veli', 'no': '902', 'sinif': '9/A SAĞLIK HİZMETLERİ'}, 'no'), ({'ad': 'Ali Veli', 'no': '77', 'tc': '1', 'sinif': '9/A SAĞLIK HİZMETLERİ'}, 'tc'),
                        ({'ad': 'Ali Veli', 'no': '77', 'sinif': '10/Z'}, 'sinif'), ({'ad': 'Ali Veli', 'no': '77', 'sinif': ''}, 'sinif'),
                        ({'ad': 'Ali Veli', 'no': '77', 'sinif': '9/A SAĞLIK HİZMETLERİ', 'dogum': '31.02.2011'}, 'dogum')):
            with self.assertRaises(OG.Hata, msg=str(g)) as c: OG.duzelt(g, [OGR], S)
            self.assertEqual(c.exception.alan, alan, str(g))
        d = OG.duzelt({'ad': 'Çiğdem Demir', 'no': '902', 'eski_no': '902', 'sinif': '9/A SAĞLIK HİZMETLERİ'}, [OGR], S)     # kendi numarası çakışma değil
        self.assertEqual(d['no'], 902)


if __name__ == '__main__':
    unittest.main(verbosity=2)
