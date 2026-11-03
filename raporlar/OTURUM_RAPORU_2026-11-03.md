# Oturum raporu - 03.11.2026 (akşam, bulut oturumu)

## Ne istendi
Ertan'ın tek dosyalık "Veli İzin Dilekçesi 2026-2027" HTML'inden LOGOS ailesinin yeni üyesi: **LOGOS Veli İzin Dilekçesi**. Veli gelir,
idareci öğrenciyi seçer, veli adı gelir, günler işaretlenir, dilekçe yazıcıdan çıkar. Günde 20'ye kadar; elle dolduruluyordu.
Ek istekler: e-Okul PDF'lerinden öğrenci (ad, doğum tarihi, sınıf, no, alan / dal, anne baba; fotoğraf yalnız istenirse), okul bilgisi
PDF'ten ama Ayarlar'dan değişir, öğrenci ekle / sil, yeni öğretim yılı, sene sonu istatistiği, geriye ve ileriye dönük dilekçe,
tam / yarım gün, "Diğer" teslim alan kişi (kimlik no, telefon, yakınlık), tek tıkla **öğrenci belgesi** (e-Okul düzeni, eksikler elle).
Aynı dil: Python + pywebview + tek HTML, LOGOS teması. Veri yalnız idarecinin bilgisayarında.

## Ne yapıldı
- Disiplin'den kopya ve uyarlama: `kasa.py` (.lvk), `gelistirici.py` (Ertan'ın Mac'indeki kurtarma aracıyla uyumlu), `yerel.py`, `isgunu.py`,
  `tek_ornek.py`, fontlar, `veri/tatiller.json`, simge ve açılış görseli.
- Yeni: `eokul.py` (genel liste + kimlik listesi, fotoğraf kırpma, birleştirme), `ogrenci.py`, `izin.py`, `belge.py` (dilekçe PDF'i, öğrenci
  belgesi), `istatistik.py`, `ana.py` (Api: 60'a yakın çağrı), `arayuz.html` (kurulum, kilit, Dilekçe, Kayıtlar, Öğrenciler, İstatistik,
  Ayarlar, Hakkında).
- Sınamalar: `kasa_sina` (14), `eokul_sina` (6), `izin_sina` (12), `api_sina` (1 uzun akış), `ui_duman.py` (Playwright). Hepsi geçiyor.
- Belgeler: `CLAUDE.md`, `README.md`, `sinama/README.md`, `raporlar/SURUM_1_0.md`, `raporlar/DENEYLER.md`.

## Kararlar (Ertan)
- Ad: LOGOS Veli İzin Dilekçesi. Ücretsiz; bütün ülke için.
- Fotoğraf yalnız kullanıcı isterse (Öğrenciler › e-Okul'dan aktar'daki kutu; Ayarlar'da varsayılan).
- Kayıtlı veli boşsa ya da öğrenciyi başkası alıyorsa "Diğer": ad, yakınlık, kimlik no, telefon elle.
- Öğrenci belgesi e-Okul'daki belge gibi; listeden gelen alanlar otomatik, eksikler elle (kaydedilir).

## Claude'un kararları (Ertan'a söylendi / söylenecek)
- Veli çipleri: önce e-Okul'daki kayıtlı veli (74 öğrencinin 14'ünde soyadı öğrencininkinden farklı), sonra anne / baba türetmesi, sonra
  elle girilmiş veli.
- Uyarılar kaydı engellemez (aynı güne önceki dilekçe, 5 iş günü geçmiş özür beyanı md. 36, devamsızlık sınırı); idareci "yine de" der.
- Dilekçe cümlesi Ayarlar'dan değişir; `{TARIHLER}` zorunlu.
- Yazdırma önce doğrudan yazıcıya (Windows `startfile 'print'`), olmazsa PDF açılır; Ayarlar'dan "önce PDF açılsın" seçilebilir.
  Okul bilgisayarında denenmedi.
- Otomatik kilit 30 dk varsayılan (günde 20 dilekçe yazan idareci için), kapatılabilir.

## Sırada
`raporlar/SURUM_1_0.md` "Sıra": okulda deneme → paketleme → öğrenci belgesi düzeni → ince ayar.

## Git
İlk commit bu oturumda, Ertan'ın Mac'indeki `LOGOS Veli İzin` klasöründe. GitHub deposu 20:22'de açıldı (`ertankaraoglu-creator/LOGOS-veliizin`,
gizli): üç commit buluttan push edildi (Mac'teki commit'ler git paketiyle taşındı, kimlikler aynı), Mac'teki klasörün `origin`'i bu depo.

## Ek (20:03) - Ertan'ın ilk geri bildirimi
- Öğrenci belgesinin numarası yok; altındaki "LOGOS Veli İzin" kaldırıldı.
- İki nüshaya gerek yok. Yarım gün e-Okul'a 0,5 işleniyor (istatistik zaten böyle).
- Dilekçede "öğrencinin anne" → "öğrencinin annesi" / "babası" / "vasisi"; Diğer'de yazılan akrabalık da ekleniyor ("teyze" → "teyzesi").
  Elle girilmiş velinin yakınlığı ("teyzesi") seçim kutusunda Diğer + açıklama olarak açılıyor (önceden kutu boş kalıyordu).
- Sınamalar: `izin_sina.YakinlikSina`, `api_sina` (PDF'te "annesi", öğrenci belgesinde "LOGOS" yok), `ui_duman` (önizlemede "annesi"). Hepsi geçiyor.
- Soruldu: dilekçenin sağ altındaki program adı ve saat de kalksın mı? Cevap (20:08): kalsın; kayıt numarası da varsayılan açık, Ayarlar'dan kapatılabilir. Sınamaya eklendi.

## Ek (20:27-20:32) - okul logosu ve devamsızlık durumu
- İkisi de iskelette vardı (eski HTML'deki gibi); Ertan uygulamayı henüz açmadığı için görmemişti. Geliştirildi:
  - Devamsızlık: tablodaki tek satır yerine ayrı bölüm (Ertan: "bir nevi devamsızlık mektubu gibi"); idareci e-Okul'dan bakıp elle yazar
    (Ertan: "mantık bu"). Bu izinle birlikte toplam, sınırlar, kalan süre, "öğrendim" cümlesi (Claude'un önerisi; Ertan'a soruldu).
    Uyarılardaki çift sayım düzeltildi: geriye dönük günler e-Okul'da zaten var, yalnız dilekçe günü ve sonrası eklenir.
  - Logo: Ayarlar'da önizleme; arayüz logoyu her önizlemede yeniden istemiyor.
- Sınamalar: `izin_sina.DevamsizlikSina` (3), `api_sina` (bölümün PDF'teki yazıları, son devamsızlık önerisi, logo PDF'te resim ve gizleme,
  CSV sütunları), `ui_duman` (logo yükleme ve önizlemede görünmesi, devamsızlık bölümü, "Bunu yaz"). Hepsi geçiyor.
