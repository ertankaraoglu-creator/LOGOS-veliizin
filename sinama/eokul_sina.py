"""e-Okul raporlarının okunması ve birleştirilmesi (uydurma okul: sinama/eokul_ornek.py): python -m unittest sinama.eokul_sina -v"""
import os, shutil, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from uygulama import eokul as E
from sinama import eokul_ornek as EO


class EokulSina(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp(prefix='lv-eokul-'); cls.y = EO.uret(cls.d)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def test_baslik(self):
        b = E.baslik_coz('AMP - 9. Sınıf / A Şubesi SAĞLIK HİZMETLERİ ALANI 2026-2027 I. Dönem')
        self.assertEqual((b['sinif'], b['alan'], b['dal'], b['program'], b['yil'], b['donem']), ('9/A', 'SAĞLIK HİZMETLERİ', '', 'AMP', '2026-2027', 1))
        b = E.baslik_coz('ATP - 12. Sınıf / B Şubesi HASTA VE YAŞLI HİZMETLERİ ALANI YAŞLI BAKIMI DALI 2026-2027 II. Dönem')
        self.assertEqual((b['sinif'], b['alan'], b['dal'], b['donem']), ('12/B', 'HASTA VE YAŞLI HİZMETLERİ', 'YAŞLI BAKIMI', 2))
        b = E.baslik_coz('11. Sınıf / C Şubesi 2026-2027 I. Dönem')
        self.assertEqual((b['sinif'], b['alan'], b['program']), ('11/C', '', ''))
        self.assertIsNone(E.baslik_coz('Genel Öğrenci Listesi'))
        self.assertEqual(E.sinif_kisa('9/A', 'SAĞLIK HİZMETLERİ'), '9A-SH'); self.assertEqual(E.sinif_kisa('10/B', 'HASTA VE YAŞLI HİZMETLERİ'), '10B-HYH')
        self.assertEqual(E.sinif_kisa('11/C'), '11C')
        self.assertEqual(E.okul_coz('Konak / Çınar Mesleki Ve Teknik Anadolu Lisesi Müdürlüğü'), {'ilce': 'Konak', 'ad': 'Çınar Mesleki Ve Teknik Anadolu Lisesi'})

    def test_genel_liste(self):
        r = E.oku(self.y['9A'], fotograf=True)
        self.assertEqual((r['tur'], r['kullanilir'], r['sayfa']), ('genel', True, 3))
        self.assertEqual(r['okul'], {'ilce': 'Konak', 'ad': 'Çınar Mesleki Ve Teknik Anadolu Lisesi', 'il': 'İzmir'})
        self.assertEqual(r['sinif']['sinif'], '9/A'); self.assertEqual(r['uyarilar'], [])
        L = r['ogrenciler']; self.assertEqual(len(L), 10)
        beklenen = EO.ogrenciler('9A', 10)
        for o, b in zip(L, beklenen):
            self.assertEqual(o['no'], b['no']); self.assertEqual(o['ad'], b['ad']); self.assertEqual(o['baba'], b['baba']); self.assertEqual(o['anne'], b['anne'])
            g, a, y = b['dogum'].split('/'); self.assertEqual(o['dogum'], f'{y}-{a}-{g}')
            self.assertEqual(o['cinsiyet'], 'K' if b['cinsiyet'] == 'Kız' else 'E'); self.assertEqual(o['veli'], b['veli']); self.assertEqual(o['velisi_kim'], b['velisi_kim'])
            self.assertEqual(o['dogum_yeri'], b['dogum_yeri'])
        # fotoğraf: 905'inki boş bırakıldı
        self.assertTrue(all(o['foto'] for o in L if o['no'] != 905)); self.assertIsNone(next(o['foto'] for o in L if o['no'] == 905))
        self.assertTrue(L[0]['foto'].startswith('data:image/jpeg;base64,'))
        # fotoğraf istenmezse alınmaz
        r2 = E.oku(self.y['9A'], fotograf=False); self.assertTrue(all('foto' not in o for o in r2['ogrenciler']))
        # ev, gelir, ısınma gibi alanlar kasaya girmez
        self.assertFalse({'kiminle', 'gelir', 'isinma', 'kira'} & set(L[0]))

    def test_kimlik_listesi(self):
        r = E.oku(self.y['kimlik']); self.assertEqual((r['tur'], r['kullanilir']), ('kimlik', True))
        K = r['kimlik']; self.assertEqual(len(K), 20)
        for b in EO.ogrenciler('9A', 10): self.assertEqual(K[b['no']]['tc'], b['tc']); self.assertEqual(E.tc_denetle(b['tc']), b['tc'])

    def test_tc_denetle(self):
        self.assertEqual(E.tc_denetle(''), ''); self.assertEqual(E.tc_denetle(None), '')
        self.assertIsNone(E.tc_denetle('12345678901')); self.assertIsNone(E.tc_denetle('01234567890')); self.assertIsNone(E.tc_denetle('1234'))
        self.assertEqual(E.tc_denetle('100 000 001 46'), '10000000146')

    def test_birlestir(self):
        A = E.oku(self.y['9A'], fotograf=True); B = E.oku(self.y['10B']); K = E.oku(self.y['kimlik'])
        O, S, oz = E.birlestir([], [A, B, K])
        self.assertEqual((oz['yeni'], oz['guncellenen'], oz['ayrilan'], oz['tasinan'], oz['tc'], oz['foto']), (18, 0, 0, 0, 18, 9))
        self.assertEqual(sorted(S), ['10/B HASTA VE YAŞLI HİZMETLERİ', '9/A SAĞLIK HİZMETLERİ'])
        self.assertEqual(S['9/A SAĞLIK HİZMETLERİ']['kisa'], '9A-SH'); self.assertEqual(S['9/A SAĞLIK HİZMETLERİ']['sayi'], 10)
        o = next(x for x in O if x['no'] == 901); self.assertEqual(o['kaynak'], 'eokul'); self.assertEqual(o['durum'], 'aktif'); self.assertTrue(o['tc']); self.assertTrue(o['foto'])
        # elle girilenler yeniden aktarmada kalır; listeden çıkan 'ayrıldı' olur; başka sınıftakine dokunulmaz
        o['tc'] = '10000000146'; o['foto_donus'] = 90; o['veli_elle'] = {'ad': 'AYŞE KAYA', 'yakinlik': 'teyzesi', 'tel': ''}; o['not_'] = 'servis'
        A2 = dict(A, ogrenciler=[x for x in A['ogrenciler'] if x['no'] != 910])
        O2, S2, oz2 = E.birlestir(O, [A2])
        self.assertEqual((oz2['yeni'], oz2['guncellenen'], oz2['ayrilan']), (0, 9, 1))
        o2 = next(x for x in O2 if x['no'] == 901)
        self.assertEqual((o2['tc'], o2['foto_donus'], o2['veli_elle']['ad'], o2['not_']), ('10000000146', 90, 'AYŞE KAYA', 'servis'))
        self.assertEqual(next(x for x in O2 if x['no'] == 910)['durum'], 'ayrildi')
        self.assertEqual(next(x for x in O2 if x['no'] == 1001)['durum'], 'aktif')
        # numarası başka öğrenciye verilmiş eski kayıt ayrı numaraya taşınır
        A3 = dict(A, ogrenciler=[dict(x, ad='YENİ ÖĞRENCİ') if x['no'] == 902 else x for x in A['ogrenciler']])
        O3, _, oz3 = E.birlestir(O2, [A3])
        self.assertEqual(oz3['tasinan'], 1); self.assertTrue(any(x['no'] == '902-E' and x['durum'] == 'ayrildi' for x in O3))
        self.assertEqual(next(x for x in O3 if x['no'] == 902)['ad'], 'YENİ ÖĞRENCİ')
        # kimlik listesinde adı uyuşmayan atlanır
        K2 = dict(K, kimlik={901: dict(K['kimlik'][901], adsoyad='BAŞKA BİRİ', tc='10000000146')})
        O4, _, oz4 = E.birlestir(O3, [K2]); self.assertEqual(oz4['tc'], 0); self.assertTrue(oz4['uyarilar'])

    def test_taninmayan(self):
        from reportlab.pdfgen import canvas
        y = os.path.join(self.d, 'baska.pdf'); c = canvas.Canvas(y); c.drawString(100, 700, 'Toplanti tutanagi'); c.save()
        r = E.oku(y); self.assertFalse(r['kullanilir']); self.assertIn('tanınan', r['neden'])
        with open(os.path.join(self.d, 'bozuk.pdf'), 'w') as f: f.write('bu pdf değil')
        with self.assertRaises(E.Hata): E.oku(os.path.join(self.d, 'bozuk.pdf'))
        with self.assertRaises(E.Hata): E.oku(os.path.join(self.d, 'yok.pdf'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
