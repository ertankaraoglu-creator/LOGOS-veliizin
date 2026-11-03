# LOGOS Veli İzin 1.0 yol haritası

Kapsam Ertan'ın (03.11.2026), sıra Claude'un; gerekçeler "Sıra" bölümünde.

## 0.1.0 iskelet (03.11.2026, bulutta yazıldı) - bitti
- Şifreli kasa, geliştiriciden kurtarma, yerel ayarlar, iş günü (Disiplin'den).
- e-Okul Genel Öğrenci Listesi ve Kimlik Bilgili Liste okuma (pdfplumber), fotoğraf isteğe bağlı, birleştirme.
- Dilekçe: öğrenci arama, veli adayları ("Diğer" kişi), takvim (okul günleri, yarım gün), neden, devamsızlık, canlı önizleme, uyarılar,
  kayıt no, PDF, yazdırma; Kayıtlar; öğrenci belgesi (e-Okul düzeni, eksik alanlar); İstatistik ve CSV; Ayarlar; yeni yıl; kilit.
- Sınamalar: kasa, e-Okul, izin, Api, arayüz dumanı.

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

## Açık sorular (Ertan'a)
- Öğrenci belgesinin numarası (e-Okul'daki "Belge No" nasıl veriliyor; LOGOS kendi sayacını mı yazsın, boş mu bıraksın?).
- Dilekçenin veliye bir kopyası veriliyor mu (iki nüsha basılsın mı)?
- Yarım gün dilekçelerde e-Okul'a devamsızlık nasıl işleniyor (yarım gün = 0,5 mi)? İstatistik buna göre.
- Kimlik numarası olmayan okullar (kimlik listesi yüklenmezse) için öğrenci belgesinde elle doldurma yeter mi?
