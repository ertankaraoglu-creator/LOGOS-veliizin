# Deneyler

Tarih, komut, süre, sonuç, öğrenilen. Gerçek veriyle yapılanlar yalnız sayılarla yazılır (ad yok).

## D1 - 03.11.2026 - e-Okul Genel Öğrenci Listesi'nin düzeni (bulut, iki gerçek PDF)
- Komut: pdfplumber ile kelimeler ve dikdörtgenler; Node'da pdf.js denemesi (canvas çizimi `CanvasFillRule` hatasıyla düştü, bırakıldı).
- Sonuç: sayfada 4 blok, her blok çerçeveli (genişlik > 400 pt, yükseklik ~155 pt), blok "Baba Adı" satırıyla başlar; solda fotoğraf
  (x 30,8-127,5 pt; üstten blok + 3,5 pt; 124,8 pt yüksek), altında ad soyad (uzun ad kelime ortasından bölünebiliyor) ve okul no; sağda iki
  sütun "Etiket : değer" (':' bazen değere yapışık). Başlık: "AMP - 9. Sınıf / A Şubesi SAĞLIK HİZMETLERİ ALANI 2026-2027 I. Dönem".
- İki gerçek PDF: 50 + 24 öğrenci, hepsi okundu, uyarı yok; fotoğraflar kırpıldı (JPEG ~10 KB, en uzun kenar 300 px). Bazı fotoğraflar
  e-Okul'da yatık: öğrenci penceresine "Döndür" kondu (`foto_donus`).
- Öğrenilen: "Veli Adı Soyadı" kayıtlı velinin adı; 74 öğrencinin 14'ünde veli soyadı öğrencininkinden farklı → veli çipleri kayıtlı veliyi
  önce gösterir, "anne + öğrenci soyadı" türetmesi yalnız kayıtlı veli o yakınlık değilse.

## D2 - 03.11.2026 - Uydurma PDF üretici (sinama/eokul_ornek.py)
- Komut: `python -m sinama.eokul_ornek /tmp/lv_ornek` (ReportLab; 9A 10, 10B 8, 11C 6 öğrenci, kimlik listesi 20).
- Sonuç: `eokul.oku` üçünü de 'genel', kimlik listesini 'kimlik' tanıdı; bütün alanlar beklenenle aynı; boş bırakılan fotoğraf None.
- Öğrenilen: gerçek düzeni taklit için çerçeve dikdörtgeni şart (`_bloklar` önce dikdörtgenlere bakıyor).

## D6 - 03.11.2026 - Bir kez çıkan sınama başarısızlığı
- Birim sınamaları 1.0.0 değişikliklerinden hemen sonra bir kez "FAILED (failures=1)" verdi (çıktı kaydedilmemişti); ardından 9 koşuda hep geçti.
- Hangisi olduğu bilinmiyor. Aday: `kasa_sina.test_sure` (açma süresi < 5 sn, yük altında). Bir daha çıkarsa çıktı `/tmp/birim_*.txt`'ye alınır.

## D5 - 03.11.2026 - İlk Windows derlemesi (GitHub, windows-latest)
- Sonuç: derleme ve paketin duman sınaması (pencere dahil) geçti: `LOGOS-Veli-Izin.exe` 27,8 MB, kurulum 29,4 MB (ikisi de sohbete
  gönderilebilir, sınır 30 MiB). "Kurulum paketini sına" adımı düştü; Actions günlüğü buluttan okunamıyor, yalnız "exit code 1".
- Tahmin: duman sınaması paketi `kill()` ile kapatıyordu; Windows'ta tek dosyalı exe alt süreç açar, alttaki exe'yi tutar, kaldırıcı
  silemez. Düzeltme: `taskkill /F /T` (süreç ağacı); adım üçe bölündü, her hata `::error` açıklaması olarak görünür; kurulum klasörü yolu
  (Türkçe İ) betikte yazılmaz, kaldırma kaydından (`InstallLocation`) okunur.

## D4 - 03.11.2026 - Linux deneme paketi (bulut)
- Komut: `python3 paket/derle.py --kurulum-yok` (PyInstaller 6, Python 3.13; ~1,5 dk).
- Sonuç: `LOGOS-Veli-Izin-linux` 36,6 MB; duman sınamasının 29 denetimi geçti (fotoğraf kırpma pakette, logo PDF'te, kasada açık veri yok).
- Öğrenilen: Disiplin'in spec'i pypdfium2'yi atıyordu; burada fotoğraf için gerekli, kaldı (Windows exe'si Disiplin'inkinden ~5 MB büyük olabilir).

## D3 - 03.11.2026 - Arayüz dumanı (Playwright, tarayıcı kipi)
- Komut: `python sinama/ui_duman.py /tmp/lv_ekran` (~25 sn).
- Bulunan hatalar: `onclick="f(${JSON.stringify(no)})"` çift tırnak özniteliği bozuyordu (satır tıklaması çalışmıyordu) → tek tırnak + esc;
  `text=Kasaya yaz` seçicisi "Kasaya yazılacak" metnine de uyuyordu → `button:has-text`; veli çipi seçilince takvim yeniden çizilip tıklama
  kayboluyordu → veli ve neden kendi parçasını çizer (`veliCiz`, `nedenCiz`); sayfa kayınca önizleme görünmüyordu → kağıt yapışkan (sticky)
  ve yüksekliğe göre ölçekli; kayıt araması "teyzesi"ni bulmuyordu → yakınlık da aranır; dilekçe cümlesinde `{TARIHLER}` zorunlu kılındı.
- Öğrenilen: headless Chromium'da toast zamanlayıcıları gecikebiliyor → toast ömrü CSS animasyonuyla, en çok 3 toast.
