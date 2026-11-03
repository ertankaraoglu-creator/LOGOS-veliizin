# LOGOS Veli İzin 1.0 yol haritası

Kapsam Ertan'ın (03.11.2026), sıra Claude'un; gerekçeler "Sıra" bölümünde.

## 0.1.0 iskelet (03.11.2026, bulutta yazıldı) - bitti
- Şifreli kasa, geliştiriciden kurtarma, yerel ayarlar, iş günü (Disiplin'den).
- e-Okul Genel Öğrenci Listesi ve Kimlik Bilgili Liste okuma (pdfplumber), fotoğraf isteğe bağlı, birleştirme.
- Dilekçe: öğrenci arama, veli adayları ("Diğer" kişi), takvim (okul günleri, yarım gün), neden, devamsızlık, canlı önizleme, uyarılar,
  kayıt no, PDF, yazdırma; Kayıtlar; öğrenci belgesi (e-Okul düzeni, eksik alanlar); İstatistik ve CSV; Ayarlar; yeni yıl; kilit.
- Sınamalar: kasa, e-Okul, izin, Api, arayüz dumanı.

## 0.1.1 (03.11.2026 akşam) - bitti
- Devamsızlık durumu dilekçede ayrı bölüm ("devamsızlık mektubu gibi"): dilekçe tarihi itibarıyla, bu izinle birlikte toplam, sınırlar ve kalan
  süre, velinin "öğrendim" cümlesi; son dilekçedeki sayılar önerilir.
- Okul logosu Ayarlar'da önizlemeli; dilekçenin sol üstünde.

## 0.1.1 paket (03.11.2026, 20:39 Ertan: "yayınlayalım, yanımdaki PC ile deneyeceğim")
- `paket/` ve GitHub derlemesi (Disiplin'in kalıbı); Linux'ta deneme derlemesi duman sınamasından geçti (D4). Windows paketi `yayin` dalıyla.
- Windows: v0.1.1 yayınlandı (GitHub Releases; ikinci derlemede bütün sınamalar geçti, D5). Ertan'ın PC'sinde deneme sırada.

## 1.0.0 (03.11.2026, Ertan 21:11: "sürümü 1.0.0 yaparak yayınlayalım")
- Ertan 0.1.1'i yanındaki PC'de inceledi ("güzel görünüyor"). İki düzeltme: açılış görselinde "LOGOS Disiplin" yazıyordu (yeni görsel,
  `acilis_uret.py`); fareyle üstüne gelince kutucuklar öne çıkıp maviye döner. Sürüm 1.0.0; aşağıdaki sıra 1.x'e kalır.

## Sıra
1. **Okulda deneme (Ertan)**: gerçek PDF'lerle aktarma, bir günün dilekçeleri, yazıcıya doğrudan gönderme (Windows'ta `startfile(... 'print')`
   okulun PDF okuyucusuna bağlı; olmazsa "önce PDF açılsın" ayarı). Bulguları `raporlar/DENEYLER.md`'ye.
   Gerekçe: dilekçe akışı günde 20 kez işleyecek; yazdırma yolu ve gerçek PDF düzeni ancak okulda görülür.
2. **Paketleme** (`paket/`): `veli_izin.spec`, `derle.py`, `duman.py`, `kurulum.iss`, GitHub derlemesi (`paket` dalı) - Disiplin'in
   kalıbıyla. Gerekçe: Ertan'ın eski PC'de ve okulda denemesi için exe gerek.
3. **Öğrenci belgesi düzeni** gerçek belgeyle yan yana karşılaştırma (Ertan'ın örneği); müdür / müdür yardımcısı imza satırları, burslu / yatılı,
   program adı; e-Okul'daki belge numarası biçimi.
4. Dilekçe ince ayar: dilekçe cümlesinin okuldan okula farkı (Ayarlar'daki kalıp yeter mi), onay kutusu metni, logo yeri.
5. İstatistik: sene sonu PDF raporu (Disiplin'deki `yil_sonu` gibi), aylık grafikler.
6. Hakkında › açık kaynak listesi (Disiplin'deki `acik_kaynak.py`), sürüm notları, kurulumda `AppCopyright`.
7. Mac paketi.

## Cevaplanan sorular (Ertan 03.11.2026, 20:03)
- Öğrenci belgesinin numarası yok: belgeye numara yazılmaz (Kayıtlar'daki "Sıra" yalnız LOGOS'un kendi listesi).
- Dilekçe tek nüsha basılır.
- Yarım gün e-Okul'a 0,5 gün işlenir: istatistik ve CSV böyle sayıyor (`izin.gun_degeri`).
- Öğrenci belgesinin altında program adı yazmaz (kaldırıldı).
- Dilekçede yakınlık iyelik ekiyle: "öğrencinin annesi / babası / vasisi" (`izin.yakinlik_metni`; Diğer'de "teyze" → "teyzesi").
- Dilekçenin sağ altındaki "LOGOS Veli İzin · tarih saat" kalır; sol alttaki kayıt numarası varsayılan olarak açık, Ayarlar'dan kapatılabilir (20:08).

## Açık sorular (Ertan'a)
- Kimlik numarası olmayan okullar (kimlik listesi yüklenmezse) için öğrenci belgesinde elle doldurma yeter mi?
