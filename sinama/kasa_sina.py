"""Şifreli kasanın sınaması (arayüzsüz): python -m unittest sinama.kasa_sina -v

Kasa LOGOS Veli İzin'in temelidir: buradaki her sınama geçmeden arayüze geçilmez.
"""
import json, os, shutil, sys, tempfile, time, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from uygulama import kasa as K

VERI = {'okul': {'ad': 'Çınar Mesleki ve Teknik Anadolu Lisesi', 'il': 'İzmir', 'ilce': 'Bornova', 'kurum_kodu': '123456'},
        'yil': '2026-2027', 'yillar': {'2026-2027': {'ogrenciler': [{'ad': 'DENİZ YILDIRIMLAR', 'no': 101}], 'izinler': []}}, 'olaylar': []}
SIFRE = 'Kurul2026ş'


class KasaSina(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix='lv-kasa-'); self.yol = os.path.join(self.d, 'okul.lvk')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_olustur_ac(self):
        k, kurt = K.Kasa.olustur(self.yol, SIFRE, VERI, '123456')
        self.assertTrue(os.path.exists(self.yol)); self.assertEqual(len(kurt), 39)
        k2 = K.Kasa.ac(self.yol, SIFRE)
        self.assertEqual(k2.veri, VERI)

    def test_dosyada_acik_veri_yok(self):
        """Okul adı, öğrenci adı, şifre, kurtarma anahtarı dosyada açık yazıyla geçmez."""
        k, kurt = K.Kasa.olustur(self.yol, SIFRE, VERI, '123456')
        ham = open(self.yol, encoding='utf-8').read()
        for s in ('Çınar', 'Yıldırımlar', 'Deniz', 'Bornova', '123456', SIFRE, kurt, kurt.replace('-', '')):
            self.assertNotIn(s, ham, s)
        b = json.loads(ham); self.assertEqual(b['bicim'], K.BICIM)

    def test_yanlis_sifre(self):
        K.Kasa.olustur(self.yol, SIFRE, VERI)
        with self.assertRaises(K.SifreYanlis): K.Kasa.ac(self.yol, 'Kurul2026s')     # ş yerine s
        with self.assertRaises(K.SifreYanlis): K.Kasa.ac(self.yol, '')

    def test_unicode_bicim(self):
        """Mac (NFD) ile Windows'ta (NFC) yazılan 'ş' aynı şifre sayılır."""
        import unicodedata
        K.Kasa.olustur(self.yol, SIFRE, VERI)
        self.assertEqual(K.Kasa.ac(self.yol, unicodedata.normalize('NFD', SIFRE)).veri, VERI)

    def test_kurtarma(self):
        k, kurt = K.Kasa.olustur(self.yol, SIFRE, VERI)
        # elle yazılmış hâli: küçük harf, boşluklu, tiresiz
        k2 = K.Kasa.kurtarma_ile_ac(self.yol, kurt.lower().replace('-', ' '))
        self.assertEqual(k2.veri, VERI)
        k2.sifre_degistir('YeniSifre99')
        with self.assertRaises(K.SifreYanlis): K.Kasa.ac(self.yol, SIFRE)
        self.assertEqual(K.Kasa.ac(self.yol, 'YeniSifre99').veri, VERI)
        self.assertEqual(K.Kasa.kurtarma_ile_ac(self.yol, kurt).veri, VERI)      # kurtarma anahtarı aynı kaldı

    def test_kurtarma_karisan_harfler(self):
        """O → 0, I/L → 1 düzeltilir; alfabe dışı ya da eksik anahtar Hata."""
        self.assertEqual(K.kurtarma_duzelt('o' * 32), '-'.join(['0000'] * 8))
        self.assertEqual(K.kurtarma_duzelt('I' * 16 + 'l' * 16), '-'.join(['1111'] * 8))
        with self.assertRaises(K.Hata): K.kurtarma_duzelt('ABC')
        with self.assertRaises(K.Hata): K.kurtarma_duzelt('U' * 32)

    def test_baska_kasanin_anahtari(self):
        K.Kasa.olustur(self.yol, SIFRE, VERI)
        yol2 = os.path.join(self.d, 'iki.lvk'); _, kurt2 = K.Kasa.olustur(yol2, SIFRE, VERI)
        with self.assertRaises(K.SifreYanlis): K.Kasa.kurtarma_ile_ac(self.yol, kurt2)

    def test_kurtarma_yenile(self):
        k, kurt = K.Kasa.olustur(self.yol, SIFRE, VERI)
        yeni = k.kurtarma_yenile()
        with self.assertRaises(K.SifreYanlis): K.Kasa.kurtarma_ile_ac(self.yol, kurt)
        self.assertEqual(K.Kasa.kurtarma_ile_ac(self.yol, yeni).veri, VERI)

    def test_sifre_kurallari(self):
        # 01.11.2026'dan beri: en az 4 karakter (4 haneli rakam olur), hepsi aynı olmasın, kurum kodu ya da parçası olmasın
        for s, ok in (('258', False), ('2580', True), ('0000', False), ('aaaa', False), ('1234', False), ('3456', False), ('12345678', False),
                      ('Okul123456x', False), ('kisa1', True), ('sadeceharf', True), ('aaaa1111', True), ('Kurul2026ş', True), ('Çınar 2026', True)):
            if ok: K.sifre_denetle(s, '123456')
            else:
                with self.assertRaises(K.Hata, msg=s): K.sifre_denetle(s, '123456')
        with self.assertRaises(K.Hata): K.Kasa.olustur(self.yol, '765432', VERI, '765432')

    def test_degisiklik_ve_yedek(self):
        k, _ = K.Kasa.olustur(self.yol, SIFRE, VERI)
        k.veri['olaylar'].append({'id': 1}); k.kaydet()
        yk = os.path.join(self.d, K.YEDEK_KLASORU)
        self.assertEqual(len(os.listdir(yk)), 1)          # ilk kayıtta bir önceki hâl yedeklendi
        k.veri['olaylar'].append({'id': 2}); k.kaydet()
        self.assertEqual(len(os.listdir(yk)), 1)          # 10 dakika dolmadan yeni yedek yok
        self.assertEqual(K.Kasa.ac(self.yol, SIFRE).veri['olaylar'], [{'id': 1}, {'id': 2}])
        eski = K.Kasa.ac(os.path.join(yk, os.listdir(yk)[0]), SIFRE)         # yedek de aynı şifreyle açılır
        self.assertEqual(eski.veri['olaylar'], [])
        self.assertFalse(any(x.endswith('.yaziliyor') for x in os.listdir(self.d)))

    def test_cakisma(self):
        """Aynı kasa iki yerde açık: ikincisi yazdıktan sonra birincisinin yazması reddedilir (veri kaybı yok)."""
        K.Kasa.olustur(self.yol, SIFRE, VERI)
        a = K.Kasa.ac(self.yol, SIFRE); b = K.Kasa.ac(self.yol, SIFRE)
        b.veri['olaylar'].append({'id': 'b'}); b.kaydet()
        a.veri['olaylar'].append({'id': 'a'})
        with self.assertRaises(K.Cakisma): a.kaydet()
        self.assertEqual(K.Kasa.ac(self.yol, SIFRE).veri['olaylar'], [{'id': 'b'}])

    def test_bozuk(self):
        K.Kasa.olustur(self.yol, SIFRE, VERI)
        b = json.load(open(self.yol, encoding='utf-8'))
        s = bytearray(K._b64c(b['veri']['sifreli'])); s[5] ^= 1; b['veri']['sifreli'] = K._b64(bytes(s))
        json.dump(b, open(self.yol, 'w', encoding='utf-8'))
        with self.assertRaises(K.Bozuk): K.Kasa.ac(self.yol, SIFRE)
        open(self.yol, 'w').write('merhaba')
        with self.assertRaises(K.Bozuk): K.Kasa.ac(self.yol, SIFRE)

    def test_kilitle(self):
        k, _ = K.Kasa.olustur(self.yol, SIFRE, VERI); k.kilitle()
        self.assertFalse(k.acik); self.assertIsNone(k.veri)
        with self.assertRaises(K.Hata): k.kaydet()

    def test_sure(self):
        """Açma süresi makul (okul bilgisayarı için ~1 sn'nin altı hedef; burada ölçülür, sınır gevşek)."""
        K.Kasa.olustur(self.yol, SIFRE, VERI)
        t = time.time(); K.Kasa.ac(self.yol, SIFRE); s = time.time() - t
        print(f'\n  açma süresi: {s:.2f} sn')
        self.assertLess(s, 5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
