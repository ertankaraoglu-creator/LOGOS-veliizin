# Sınamalar

Her değişiklikten sonra hepsi koşulur. Okul, öğrenci ve veli adları uydurmadır (`eokul_ornek.py`); gerçek veri kullanılmaz.

| Dosya | Ne sınar | Komut |
|---|---|---|
| `kasa_sina.py` | Şifreli kasa (Disiplin'den): oluşturma, açma, yanlış şifre, Unicode, kurtarma anahtarı, şifre kuralları, yedek, çakışma, bozuk dosya, dosyada açık veri olmaması | `python -m unittest sinama.kasa_sina -v` |
| `eokul_sina.py` | e-Okul: sınıf başlığı (AMP / ATP / düz lise, alan, dal), okul satırı, genel liste (bütün alanlar, fotoğraf isteğe bağlı, boş fotoğraf), kimlik listesi, T.C. denetimi, birleştirme (elle girilenler kalır, ayrılan, numara taşıma, uyuşmayan kimlik), tanınmayan ve bozuk PDF | `python -m unittest sinama.eokul_sina -v` |
| `izin_sina.py` | Takvim (hafta sonu, bayram, ara tatil, yaz, kapalı gün), sayı ve tarih metinleri, gruplar ve dilekçe cümlesi, yön, metin kalıbı ve yer tutucular, denetim (alanıyla), uyarılar (aynı gün, 5 iş günü, devamsızlık sınırı; geçmiş gün iki kez sayılmaz), devamsızlık bölümü (dilekçe tarihi itibarıyla, bu izinle birlikte, sınır ve kalan, aşım), öğrenci arama, veli adayları, elle öğrenci denetimi | `python -m unittest sinama.izin_sina -v` |
| `api_sina.py` | Api baştan sona: kurulum, e-Okul aktarma, elle öğrenci, fotoğraf döndürme, dilekçe (önizleme, uyarı, kayıt no, PDF içeriği, güncelleme, süzgeçler, silme), devamsızlık bölümü ve son devamsızlık önerisi, okul logosu (PDF'te resim, gizleme), öğrenci belgesi (eksik alan, PDF içeriği), istatistik ve CSV, ayarlar, yeni yıl, kilit ve kurtarma, kasada ve günlükte açık veri yok | `python -m unittest sinama.api_sina -v` |
| `ui_duman.py` | Arayüz (Playwright, tarayıcı kipi): kurulum (PDF'ten okul), aktarma, okul logosu (dosya seçme, önizleme, dilekçede), öğrenci penceresi, arama, veli çipleri, takvim ve yarım gün, önizleme, devamsızlık bölümü ve "Bunu yaz", kaydet, uyarı penceresi, "Diğer" kişi, Kayıtlar (ara, aç, sil), öğrenci belgesi (eksik alan), İstatistik, Ayarlar, kilit, kurtarma anahtarı, Hakkında | `python sinama/ui_duman.py [ekran_klasoru]` |

Hepsi: `python -W ignore -m unittest sinama.kasa_sina sinama.eokul_sina sinama.izin_sina sinama.api_sina -v && python sinama/ui_duman.py`

Tarayıcı kipi kendi kasasını `LV_AYAR_KLASORU` ile geçici klasörde açar; bilgisayardaki gerçek kasaya dokunmaz. `LV_SINAMA=1` yazıcıya
göndermez, PDF açmaz. Uydurma PDF'ler elle de üretilebilir: `python -m sinama.eokul_ornek <klasör>`.
