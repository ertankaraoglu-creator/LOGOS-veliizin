"""LOGOS Veli İzin Dilekçesi'nin sürümü: tek kaynak (LOGOS Disiplin ve LOGOS Ders Dağıtım'daki gibi).

Kasa dosyasının meta.uygulama'sı, arayüzdeki sürüm yazısı ve paketin adı buradan okur. Yeni sürümde yalnız burası değişir.
"""
AD = 'LOGOS Veli İzin'
TAM_AD = 'LOGOS Veli İzin Dilekçesi'
SURUM = '1.0.1'
TARIH = '04.11.2026'
GELISTIRICI = 'Ertan Karaoğlu'
TELIF = '© 2026 Ertan Karaoğlu'
SITE = 'https://dersdagitim.com'            # öteki LOGOS uygulamaları (Hakkında; kurulumda AppPublisherURL)
DESTEK_EPOSTA = 'logosddu@gmail.com'
KURULUM_KIMLIGI = '8B2D4F61-7C3E-4A9B-9D15-2E6F8A0C4B7D'     # Inno Setup AppId: değişmez (güncellemede aynı uygulama sayılır)
# Program kendiliğinden internete çıkmaz (Disiplin'deki karar, Ertan 30.10.2026: bütün güncellemeler dersdagitim.com'dan).
GUNCELLEME_ADRESI = None
INDIRME_SAYFASI = 'https://dersdagitim.com/veli-izin'


def parcala(s):
    """'0.7.10' -> (0, 7, 10); sayı olmayan parça 0."""
    return tuple(int(p) if p.isdigit() else 0 for p in str(s).strip().lstrip('vV').split('.'))


def daha_yeni(aday, simdiki=SURUM):
    """aday sürüm şimdikinden yeni mi (0.7.10 > 0.7.9; eksik parça 0)."""
    a, b = parcala(aday), parcala(simdiki); n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) > b + (0,) * (n - len(b))
