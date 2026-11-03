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

## D3 - 03.11.2026 - Arayüz dumanı (Playwright, tarayıcı kipi)
- Komut: `python sinama/ui_duman.py /tmp/lv_ekran` (~25 sn).
- Bulunan hatalar: `onclick="f(${JSON.stringify(no)})"` çift tırnak özniteliği bozuyordu (satır tıklaması çalışmıyordu) → tek tırnak + esc;
  `text=Kasaya yaz` seçicisi "Kasaya yazılacak" metnine de uyuyordu → `button:has-text`; veli çipi seçilince takvim yeniden çizilip tıklama
  kayboluyordu → veli ve neden kendi parçasını çizer (`veliCiz`, `nedenCiz`); sayfa kayınca önizleme görünmüyordu → kağıt yapışkan (sticky)
  ve yüksekliğe göre ölçekli; kayıt araması "teyzesi"ni bulmuyordu → yakınlık da aranır; dilekçe cümlesinde `{TARIHLER}` zorunlu kılındı.
- Öğrenilen: headless Chromium'da toast zamanlayıcıları gecikebiliyor → toast ömrü CSS animasyonuyla, en çok 3 toast.
