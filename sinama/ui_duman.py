"""Arayüz duman sınaması: bütün iş akışı tarayıcı kipinde.
kurulum (PDF'ten okul bilgisi) → e-Okul aktarma (fotoğraflı) → dilekçe (arama, veli çipi, takvim, yarım gün, "Diğer" kişi, uyarı penceresi,
kaydet) → Kayıtlar (aç, yeniden yazdır, sil) → öğrenci belgesi (eksik alan penceresi) → İstatistik → Ayarlar (dilekçe cümlesi, kapalı gün,
logo) → kilitle → şifreyle aç → kurtarma anahtarıyla aç.

python sinama/ui_duman.py [ekran_klasoru]
"""
import datetime, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sinama import ui_ortak as U
from playwright.sync_api import sync_playwright, expect


def okul_gunu(d):
    from uygulama import isgunu
    return isgunu.okul_gunu(d)


def son_okul_gunleri(n, bitis=None):
    """Bugünden (dahil değil) geriye n okul günü, eskiden yeniye."""
    d = bitis or datetime.date.today(); out = []
    while len(out) < n:
        d -= datetime.timedelta(days=1)
        if okul_gunu(d): out.append(d)
    return sorted(out)


AYLAR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']


def takvime_git(sayfa, g):
    """Takvimi g'nin ayına götürür (önceki / sonraki ay okları)."""
    for _ in range(24):
        ad, yil = sayfa.locator('#tkBaslik').inner_text().split()
        simdi = int(yil) * 12 + AYLAR.index(ad); hedef = g.year * 12 + g.month - 1
        if simdi == hedef: break
        sayfa.click('.tk-nav[aria-label="Önceki ay"]' if hedef < simdi else '.tk-nav[aria-label="Sonraki ay"]')
        sayfa.wait_for_function(f"document.getElementById('tkBaslik').textContent !== '{ad} {yil}'")
    sayfa.wait_for_selector(f'.gun[data-d="{g.isoformat()}"], span.gun', state='attached')


def sinif_secenegi(sayfa, kisa):
    """Sınıf süzgecinde kısa adı verilen şubenin değeri ('9A-SH (10)' → anahtar)."""
    for v, t in sayfa.evaluate("[...document.querySelectorAll('#ogSinif option')].map(o => [o.value, o.textContent])"):
        if t.startswith(kisa + ' ') or t.startswith(kisa + '-'): return v
    raise AssertionError('sınıf seçeneği yok: ' + kisa)


def main(ekran_klasoru=None):
    ekran = U.Ekran(ekran_klasoru)
    with U.Sunucu() as S, sync_playwright() as pw:
        pdfler = S.ornek_pdfler(); b, sayfa = U.tarayici(pw)
        sayfa.goto(S.adres)
        anahtar = U.kurulum(sayfa, ekran, pdf_yolu=pdfler['9A'])
        assert re.fullmatch(r'[A-Z0-9]{4}(-[A-Z0-9]{4}){7}', anahtar), anahtar
        expect(sayfa.locator('#ustOkul')).to_have_text('Çınar Mesleki Ve Teknik Anadolu Lisesi')
        # kurulumdan sonra Öğrenciler sayfası açılır
        expect(sayfa.locator('#baslik')).to_have_text('Öğrenciler')
        U.eokul_aktar(sayfa, ekran, [pdfler['9A'], pdfler['10B'], pdfler['AL'], pdfler['kimlik']])
        expect(sayfa.locator('#ogAlt')).to_contain_text('24 öğrenci, 3 şube')
        assert sayfa.locator('#ogTablo tbody tr').count() == 24
        assert sayfa.locator('#ogTablo >> text=kimlik no').count() == 18, sayfa.locator('#ogTablo >> text=kimlik no').count()
        assert sayfa.locator('#ogTablo >> text=foto').count() == 23

        # ---- öğrenci penceresi: fotoğraf döndür, not yaz, kaydet
        sayfa.click('#ogTablo tbody tr:has-text("901")')
        sayfa.wait_for_selector('#opAd'); expect(sayfa.locator('#opAd')).to_have_value('POYRAZ ARSLAN')
        sayfa.click('#modal button:text-is("Döndür")'); sayfa.wait_for_function("document.getElementById('opFoto').style.transform.includes('90')")
        sayfa.fill('#opNot', 'Servisle gelir'); sayfa.click('#modal button:text-is("Kaydet")'); sayfa.wait_for_selector('#modal', state='hidden')

        # ---- dilekçe: ara (Türkçe harfsiz), seç
        sayfa.click('aside button[data-sayfa=dilekce]')
        sayfa.fill('#q', 'cigdem'); sayfa.wait_for_selector('#sonuclar .snc')
        expect(sayfa.locator('#sonuclar .snc').first).to_contain_text('ÇİĞDEM DEMİR')
        sayfa.keyboard.press('Enter'); sayfa.wait_for_selector('#dkKalan:not([hidden])')
        expect(sayfa.locator('#dkOgr .ad')).to_have_text('ÇİĞDEM DEMİR')
        # kayıtlı veli ilk çip ve seçili: EMİNE YILDIRIM (anne, soyadı farklı); türetilmiş anne eklenmez, baba eklenir
        cipler = sayfa.locator('#veliCipler .cip').all_inner_texts()
        assert cipler[0].endswith('EMİNE YILDIRIM') and 'kayıtlı' in cipler[0], cipler
        assert not any('EMİNE DEMİR' in c for c in cipler), cipler
        assert any('İBRAHİM DEMİR' in c for c in cipler), cipler
        expect(sayfa.locator('#vAd')).to_have_value('EMİNE YILDIRIM')
        ekran.al(sayfa, 'dilekce-ogrenci')
        # gün seç: son iki okul günü (geriye dönük: özür beyanı), ikincisi öğleden sonra yarım
        g1, g2 = son_okul_gunleri(2)
        for g in (g1, g2):
            takvime_git(sayfa, g); sayfa.click(f'button.gun[data-d="{g.isoformat()}"]')
        sayfa.wait_for_selector('.donem')
        expect(sayfa.locator('#gunToplam')).to_have_text('toplam 2 gün')
        if (g2 - g1).days == 1: sayfa.select_option('.donem select', 'sonra'); expect(sayfa.locator('#gunToplam')).to_have_text('toplam 1 gün')
        else: sayfa.locator('.donem select').nth(1).select_option('sonra'); expect(sayfa.locator('#gunToplam')).to_have_text('toplam 1,5 gün')
        sayfa.click('#nedenler >> text=Cenaze')
        sayfa.wait_for_function("document.querySelector('#kagit .kg-metin') && document.querySelector('#kagit .kg-metin').textContent.includes('vefat')")
        ekran.al(sayfa, 'dilekce-takvim')
        # kaydet (yazdırmadan)
        sayfa.click('.eylemler button:text-is("Kaydet")')
        sayfa.wait_for_selector('.toast:has-text("Kaydedildi")')
        expect(sayfa.locator('#dkOzet')).to_contain_text('Kayıt 2026-27/0001')
        expect(sayfa.locator('#kayitSay')).to_have_text('1')
        ekran.al(sayfa, 'dilekce-kaydedildi')

        # ---- ikinci dilekçe: aynı öğrenci, aynı gün → uyarı penceresi; "Diğer" kişi; kaydet ve yazdır (tarayıcıda PDF açılmaz)
        sayfa.click('text=Yeni dilekçe'); sayfa.wait_for_selector('#dkSec:not([hidden])')
        sayfa.fill('#q', '902'); sayfa.wait_for_selector('#sonuclar .snc'); sayfa.keyboard.press('Enter'); sayfa.wait_for_selector('#dkKalan:not([hidden])')
        sayfa.click('#veliCipler >> text=Diğer'); sayfa.fill('#vAd', 'Ayşe Kaya'); sayfa.fill('#vYakAc', 'teyzesi'); sayfa.fill('#vTel', '05321234567'); sayfa.fill('#vTc', '10000000146')
        takvime_git(sayfa, g2); sayfa.click(f'button.gun[data-d="{g2.isoformat()}"]'); sayfa.wait_for_selector('.donem')
        sayfa.wait_for_selector('#gunUyari .uyari-kutu')
        expect(sayfa.locator('#gunUyari')).to_contain_text('daha önce dilekçe')
        sayfa.click('#btnYazdir')
        sayfa.wait_for_selector('#mdEvet'); ekran.al(sayfa, 'dilekce-uyari'); sayfa.click('#mdEvet')
        sayfa.wait_for_selector('.toast:has-text("0002")')
        expect(sayfa.locator('#kagit')).to_contain_text('öğrencinin teyzesi')
        expect(sayfa.locator('#kagit')).to_contain_text('0532 123 45 67')

        # ---- kayıtlar
        sayfa.click('aside button[data-sayfa=kayitlar]'); sayfa.wait_for_selector('#kyTablo table')
        assert sayfa.locator('#kyTablo tbody tr').count() == 2
        expect(sayfa.locator('#kySayilar')).to_contain_text('Dilekçe')
        sayfa.fill('#kyQ', 'teyze'); sayfa.wait_for_function("document.querySelectorAll('#kyTablo tbody tr').length === 1")
        sayfa.fill('#kyQ', ''); sayfa.wait_for_function("document.querySelectorAll('#kyTablo tbody tr').length === 2")
        ekran.al(sayfa, 'kayitlar')
        sayfa.click('#kyTablo tbody tr:nth-child(2) button:text-is("Aç")'); sayfa.wait_for_selector('#dkKalan:not([hidden])')
        expect(sayfa.locator('#dkOzet')).to_contain_text('Kayıt 2026-27/0001, kayıtlı')
        expect(sayfa.locator('#vAd')).to_have_value('EMİNE YILDIRIM')
        sayfa.click('aside button[data-sayfa=kayitlar]'); sayfa.wait_for_selector('#kyTablo table')
        sayfa.click('#kyTablo tbody tr:nth-child(1) button:text-is("Sil")'); sayfa.click('#mdEvet')
        sayfa.wait_for_function("document.querySelectorAll('#kyTablo tbody tr').length === 1")

        # ---- öğrenci belgesi: 11/C'nin kimlik numarası yok → eksik penceresi → T.C. yaz → belge
        sayfa.click('aside button[data-sayfa=ogrenciler]'); sayfa.wait_for_selector('#ogTablo table')
        sayfa.select_option('#ogSinif', sinif_secenegi(sayfa, '11C'))
        sayfa.click('#ogTablo tbody tr:first-child button:text-is("Belge")')
        sayfa.wait_for_selector('#bTc'); ekran.al(sayfa, 'belge-eksik')
        sayfa.fill('#bTc', '10000000146'); sayfa.click('#bYaz')
        sayfa.wait_for_selector('.toast:has-text("Öğrenci belgesi")')
        sayfa.click('#ogTablo tbody tr:first-child'); sayfa.wait_for_selector('#opTc'); expect(sayfa.locator('#opTc')).to_have_value('10000000146')
        sayfa.click('#modal button:text-is("Vazgeç")')
        # 9A'lı öğrencinin her şeyi var → doğrudan belge
        sayfa.select_option('#ogSinif', sinif_secenegi(sayfa, '9A'))
        sayfa.click('#ogTablo tbody tr:first-child button:text-is("Belge")')
        sayfa.wait_for_selector('.toast:has-text("Öğrenci belgesi")')
        sayfa.click('aside button[data-sayfa=kayitlar]'); sayfa.wait_for_selector('#kyBelgeler table')
        assert sayfa.locator('#kyBelgeler tbody tr').count() == 2

        # ---- istatistik
        sayfa.click('aside button[data-sayfa=istatistik]'); sayfa.wait_for_selector('#isIcerik .sayi')
        expect(sayfa.locator('#isIcerik .sayi').first).to_contain_text('1')
        ekran.al(sayfa, 'istatistik')

        # ---- ayarlar
        sayfa.click('aside button[data-sayfa=ayarlar]'); sayfa.wait_for_selector('#aKonu')
        sayfa.fill('#aKonu', 'İzin dilekçesi'); sayfa.press('#aKonu', 'Tab')
        sayfa.wait_for_function("fetch('/api/ozet', {method: 'POST', body: '[]'}).then(r => r.json()).then(j => j.ayarlar.dilekce_konu === 'İzin dilekçesi')")
        sayfa.fill('#aMetin', 'Bozuk cümle'); sayfa.press('#aMetin', 'Tab')
        sayfa.wait_for_selector('.toast.err')                     # yer tutucular eksik: reddedilir, eski cümle kalır
        sayfa.click('button:text-is("Gün ekle")'); sayfa.wait_for_selector('#aKapali input[type=date]')
        ekran.al(sayfa, 'ayarlar')
        # ---- kilitle, şifreyle aç
        sayfa.click('aside .kilitle'); sayfa.wait_for_selector('#kilit:not([hidden])')
        sayfa.fill('#kltSifre', '0000'); sayfa.click('#kltAc'); sayfa.wait_for_selector('#kltIleti:has-text("yanlış")')
        ekran.al(sayfa, 'kilit')
        U.kilit_ac(sayfa)
        expect(sayfa.locator('#kayitSay')).to_have_text('1')
        # ---- kurtarma anahtarıyla aç, yeni şifre
        sayfa.click('aside .kilitle'); sayfa.wait_for_selector('#kilit:not([hidden])')
        sayfa.click('text=Şifremi unuttum'); sayfa.fill('#kltAnahtar', anahtar); sayfa.fill('#kltYeni', '1357')
        sayfa.click('text=Aç ve şifreyi değiştir'); sayfa.wait_for_selector('#ana:not([hidden])')
        sayfa.click('aside .kilitle'); U.kilit_ac(sayfa, '1357')
        # ---- Hakkında
        sayfa.click('#hakkindaDugme'); sayfa.wait_for_selector('#modal:not([hidden]) >> text=Gizlilik beyanı'); ekran.al(sayfa, 'hakkinda')
        sayfa.keyboard.press('Escape'); sayfa.wait_for_selector('#modal', state='hidden')
        U.hatalari_denetle(sayfa)
        b.close()
    print('ui_duman: geçti')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
