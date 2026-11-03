# LOGOS Veli İzin - Çalışma Kuralları

Bu dosya her oturumda okunur. Ertan ile birlikte çalışan Claude bu kurallara uyar. Kardeş projeler LOGOS Ders Dağıtım (`../LOGOS/CLAUDE.md`)
ve LOGOS Disiplin'in (`../LOGOS DİSİPLİN/CLAUDE.md`) kuralları burada da geçerlidir; aşağıdakiler LOGOS Veli İzin'e özgüdür ya da öne çıkar.

## Hitap ve tavır
- Ertan'a "dostum", "hocam" ya da "üstad" denir. Her şey Türkçe: arayüz, kod adları, yorumlar, commit mesajları.
- Claude Ertan'ın kararlarını eleştirisiz kabul etmez; bir karar başka bir okulda ya da yönetmelik karşısında patlayacaksa hemen söylenir.
- Sıralama Claude'da, kapsam Ertan'da: sıra `raporlar/SURUM_1_0.md` "Sıra" bölümünde gerekçesiyle yazılır.

## Git ve dosya yeri
- Her deney, her ilerleme git'e girer; başarısız denemeler de. Oturum sonunda `git status` temiz, push yapılmış olmalı; Claude Ertan'a
  "push edildi mi?" diye hatırlatır.
- Ertan yalnız şu klasöre bakar: `/Volumes/BİLGİSAYARIM/DERS DAĞITIMM/LOGOS Veli İzin/` (GitHub deposunun birebir kopyası). Claude ürettiği her
  dosyayı bu klasörün içine, depodaki aynı yere yazar (bulut oturumunda `device_commit_files`; yol NFD: `cd "$HOME"/mnt/LOGOS\ Veli*`).
- Deneyler `raporlar/DENEYLER.md`'ye (tarih, komut, süre, sonuç, öğrenilen), her oturum `raporlar/OTURUM_RAPORU_<tarih>.md`'ye.

## Ürün (Ertan 03.11.2026)
- **Sorun**: öğrenci okuldan tek başına çıkamaz; yönetmeliğe (MEB Ortaöğretim Kurumları Yönetmeliği md. 36) göre veli gelip dilekçe yazar,
  idareci basar, veli imzalar, öğrenci teslim edilir. Günde 20'ye kadar; elle dolduruluyordu. Hedef: **tek tıkla** öğrenci → veli → günler →
  yazıcı → imza. Öğrencinin, bekleyen velinin ve idarecinin işi kolaylaşır.
- Ürün tek okul için değil, bütün ülke için: KATML yalnız deneme verisi; okula özel hiçbir şey koda girmez. Ücretsiz, ticari değil.
- Kapsam (Ertan): geriye dönük **özür beyanı** ve ileriye dönük **izin isteği**; tam gün / yarım gün (öğleden önce / sonra); idareci
  istatistik görür (sene sonu için de); okul bilgisi PDF'ten okunur ama Ayarlar'dan değişir; öğrenci ekle / sil; yeni öğretim yılı;
  **"Diğer"**: kayıtlı veli boşsa ya da öğrenciyi başkası alıyorsa adı, yakınlığı, kimlik numarası, telefonu elle; **öğrenci belgesi** tek
  tıkla e-Okul düzeninde (idareci "40 takla" atmasın), listeden gelmeyen alanlar elle. "İlerledikçe konuyu genişleteceğiz."
- Aynı "dil": Python + pywebview + tek `arayuz.html` (saf JS), PyInstaller + Inno Setup; LOGOS'un renkleri, kenar çubuğu, kartları.
  Ölçüt: 12 yaşındaki bir çocuğun birkaç dakikada çözebileceği, güven veren, modern arayüz.

- Belgeler (Ertan 03.11.2026, 20:03): dilekçe **tek nüsha**; dilekçede yakınlık iyelik ekiyle ("öğrencinin annesi", "babası", `izin.yakinlik_metni`
  ve arayüzde `yakinlikMetni`, ikisi aynı tabloyla); **öğrenci belgesinin numarası yok** ve altında program adı yazmaz; yarım gün e-Okul'a
  **0,5** işlenir (istatistik de öyle sayar). Dilekçenin altında sağda "LOGOS Veli İzin · tarih saat" kalır, solda kayıt numarası
  varsayılan olarak açık gelir (`ayarlar.kayit_no_goster`, Ayarlar'dan kapatılır; Ertan 20:08).

## Veri ve güvenlik
- Öğrenci listesi, fotoğraflar, kimlik numaraları, veli bilgileri okulun hassas verisidir. **Veri okuldan çıkmaz**: program hiçbir sunucuya
  bir şey göndermez, internete kendiliğinden hiç çıkmaz (`surum.GUNCELLEME_ADRESI = None`; güncellemeler dersdagitim.com'dan elle).
  Gizlilik beyanı (Hakkında) yalnız doğruyu söyler; ağa çıkan bir şey eklenirse beyan da değişir.
- Bütün veri tek şifreli kasada (`.lvk`, `uygulama/kasa.py`, Disiplin'inkiyle aynı: AES-256-GCM, scrypt, kurtarma anahtarı, çakışma, yedek).
  Varsayılan şifre, evrensel açma kodu yok. Şifre kuralı: en az 4 karakter (4 rakam olur), hepsi aynı olmasın, kurum kodu olmasın.
- **Geliştiriciden kurtarma** `uygulama/gelistirici.py` Disiplin'deki gibi; `BILGI_HKDF` Disiplin'inkiyle aynı bırakıldı ki Ertan'ın Mac'indeki
  `Kurtarma kodu üret.app` (LOGOS DİSİPLİN/arac) bu kasaların isteğini de çözsün. Gizli anahtar yalnız Ertan'ın Mac'inde; depoya girmez.
- **Depoya ve pakete gerçek öğrenci, veli, öğretmen adı girmez.** Sınamalar `sinama/eokul_ornek.py`'nin uydurma okuluyla (Çınar MTAL,
  uydurma adlar). Gerçek e-Okul PDF'leri depoya girmez; gerçek veriyle deneme yalnız Ertan'ın bilgisayarında, `gizli/` (gitignore).
  Kasa dosyaları (`*.lvk`) depoya girmez. Günlüğe (`gunluk.txt`) öğrenci bilgisi yazılmaz (`ana.hata_izi`).
- **Veri en azlığı**: e-Okul genel listesinden yalnız ad soyad, okul no, doğum tarihi ve yeri, cinsiyet, anne baba adı, "Velisi Kim",
  "Veli Adı Soyadı", sınıf / alan / dal; **fotoğraf yalnız kullanıcı isterse** (Ertan: "tabii ki kullanıcı isterse"). Kimlik numarası
  "Fotoğraflı-Kimlik Bilgili Öğrenci Listesi"nden ya da elle (öğrenci belgesi için). Ev, gelir, ısınma, hastalık, kardeş, devamsızlık alanları
  okunmaz (`eokul.ETIKET` dışındakiler atılır; `eokul_sina` denetler). Yeni alan alınacaksa gerekçesi yazılır.
- Ölçü (Disiplin'den, Ertan: "gizliliği fazla ciddiye alıyorsun, çok kasma"): kullanıcıya fazladan adım getiren güvenlik önlemi eklenmez.
  Otomatik kilit varsayılan 30 dk (günde 20 dilekçe yazan idareci için; Ayarlar'dan kapatılabilir).
- Yazdırılan PDF'ler (dilekçe, öğrenci belgesi, CSV) `Belgeler/<yıl>/` klasöründe **şifresiz** durur (yazdırmak için; Ayarlar'dan silinir).

## Yapı
- `uygulama/`: `ana.py` (Api, pencere, tarayıcı kipi; veri modeli üstte), `kasa.py`, `gelistirici.py`, `yerel.py` (bu bilgisayarın ayarları,
  kasanın yeri `%LOCALAPPDATA%\LOGOS Veli İzin` / `~/Library/Application Support/LOGOS Veli İzin`, `gunluk.txt`), `surum.py` (tek sürüm
  kaynağı), `veri.py` (veri dosyalarının kökü; PyInstaller'da `_MEIPASS`), `isgunu.py` (iş günü ve okul günü; `veri/tatiller.json`: resmî
  tatiller, MEB ara tatilleri; okulun kapalı günleri Ayarlar'dan), `eokul.py` (e-Okul PDF'leri; pdfplumber, 4 blok / sayfa, fotoğraf kırpma
  `FOTO_*` ölçüleri iki gerçek PDF'te ölçüldü), `ogrenci.py` (arama Türkçe harfsiz, veli adayları, elle ekleme denetimi), `izin.py` (dilekçe:
  günler, gruplar, cümle, uyarılar, denetim), `belge.py` (ReportLab: dilekçe PDF'i, öğrenci belgesi e-Okul düzeninde, yazdırma),
  `istatistik.py`, `arayuz.html` (tek dosya; LOGOS teması; marka görseli gömülü), `fontlar/` (Liberation Sans, OFL).
- `veri/tatiller.json` (Disiplin'den kopya; aynı dosya, yıl başına güncellenir).
- `sinama/`: `kasa_sina`, `eokul_sina`, `izin_sina`, `api_sina` (unittest), `ui_duman.py` (Playwright, tarayıcı kipi, bütün akış),
  `eokul_ornek.py` (uydurma PDF'ler), `ui_ortak.py`. Her değişiklikten sonra koşulur (`sinama/README.md`).
- `raporlar/`: `SURUM_1_0.md` (yol haritası ve sıra), `DENEYLER.md`, oturum raporları.
- `paket/`: `simge.png`, `acilis.png` (Disiplin'den); spec, derle, kurulum henüz yazılmadı (sırada).

## Teknik notlar
- Kasadaki veri `{okul, ayarlar, okul_logo, yil, yillar {yıl: {ogrenciler, siniflar, izinler, belgeler, sayac {izin, belge}, eokul}}, guvenlik, meta}`.
  Öğrenci: `{no, ad, baba, anne, dogum, dogum_yeri, cinsiyet, velisi_kim, veli, sinif (şube anahtarı '9/A SAĞLIK HİZMETLERİ'), durum
  aktif|ayrildi, kaynak eokul|elle|eokul+elle, tc, foto (data URL)|None, foto_donus, veli_elle, dal, not_}`. Dilekçe: `{id, no, no_metni
  '2026-27/0001', tarih, ogrenci_no, ogrenci (o günkü kopya), veli {ad, yakinlik, yakinlik_aciklama, tc, tel, kayitli}, gunler {ISO: tam|once|
  sonra}, toplam, neden_kodu, neden, yon geriye|ileriye|karisik|bugun, devamsizlik}`.
- Öğretim yılı takvimden (1 Eylül); etkin yıl kasada `yil` (yeni yıl açılınca eski yıl Kayıtlar / İstatistik'te seçilerek okunur).
- Dilekçe cümlesi Ayarlar'dan değişir; yer tutucular `{NEDEN} {TARIHLER} {TOPLAM} {OGRENCI} {SINIF} {NO}`, `{TARIHLER}` zorunlu.
- Uyarılar kaydı engellemez (aynı güne önceki dilekçe, 5 iş günü geçmiş özür beyanı, devamsızlık sınırı): `izin_kaydet` önce `uyari_gerek`
  döner, arayüz sorar, `uyarilari_gordum` ile kaydeder. Engelleyen hata `{hata, alan}`; arayüz alanı kırmızı yapar.
- Takvimde okul günü olmayan gün seçilemez (hafta sonu, resmî tatil, ara tatil, yaz, okulun kapalı günleri); Shift ile aralık.
- Yazdırma: `belge.yazdir` Windows'ta `os.startfile(yol, 'print')`, Mac'te `lp`; olmazsa PDF açılır (`ayarlar.yazdirma`: yazici | ac).
  **Okul bilgisayarında denenmedi** (sırada). Sınamada `LV_SINAMA=1` hiçbir program açmaz.
- Arayüz kuralları Disiplin'deki gibi: `alert/confirm/prompt` yok (kendi `modal`), kaydeden düğmeler `birKez`, gecikmeli odak yok, pywebview
  Api'de durum `_ad` biçiminde, kilitliyken `{hata, kilit: true}` → kilit ekranı. `onclick` içinde tek tırnak + `esc` (çift tırnak JSON
  özniteliği bozuyordu, ui_duman ile bulundu).
- Tarayıcı kipinde `dosya_sec` `{tarayici: true}` döner, arayüz yol kutusu açar (sınamalar yolu elle yazar).
- Sınamalarda tarih: `izin_sina` Kasım 2026'ya sabit; `api_sina` / `ui_duman` bugünden geriye okul günü bulur (`okul_gunleri`). Gün
  `LV_BUGUN` / `LV_BUGUN_DOSYASI` ile değiştirilebilir (yalnız yıl ve istatistik için).
- Çalıştırma: `python -m uygulama.ana` (pencere), `python -m uygulama.ana --tarayici 8767` (tarayıcı).
- Sınama: `python -W ignore -m unittest sinama.kasa_sina sinama.eokul_sina sinama.izin_sina sinama.api_sina -v`, arayüz `python sinama/ui_duman.py [ekran_klasoru]`.
