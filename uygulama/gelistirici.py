"""Geliştiriciden kurtarma (Ertan 01.11.2026 03:47: "32 haneli güvenlikli bir kurtarma kodu olsun; şifresini unutana göndereyim, o da kendi
yeni şifresini belirlesin; benim gönderdiğim kodla bir daha kurtarma yapılamasın").

Neden önceden hazırlanmış bir kod listesi değil: uygulamanın kodu denetleyebilmesi için liste uygulamanın içinde durmalıydı. exe'yi açan
herkes listeyi bulur, listedeki her kod bütün okulların kasasını açardı.

Yapı: her kasada ayrı, tek kullanımlık bir sır R (32 karakter; okulun kurtarma anahtarıyla aynı biçim). Kasa veri anahtarını R'yle de sarar
(kasa.py, rol 'gelistirici'). R, kasanın kimliği ve okulun adı geliştiricinin X25519 açık anahtarına şifrelenip kasanın açık başlığına
"kurtarma isteği" olarak yazılır. Kasa kilitliyken istek gösterilir, okul onu e-postayla geliştiriciye gönderir; geliştirici gizli anahtarıyla
(yalnız kendi bilgisayarında: arac/kurtarma_kodu.py) okulu ve R'yi görür, R'yi okula gönderir. R kullanılınca kasa yeni R ve yeni istek
üretir: eski kod bir daha açmaz. R yalnız kendi kasasını açar; geliştirici kasa dosyasını görmez, R dosya olmadan bir şey açmaz.
Okul Ayarlar'dan kapatabilir (o zaman sarım ve istek başlıktan silinir).
Bilinen sınır: kurtarmadan önce alınmış yedekler eski R'yle açılır (eski şifreyle de açıldıkları gibi).

Şifreleme: ECIES (geçici X25519 + HKDF-SHA256 + AES-256-GCM).
İstek: sürüm (1) | geçici açık anahtar (32) | AES-GCM[R (20) | kasa kimliği (16) | bilgi JSON], Crockford base32, 4'lü öbekler.
"""
import binascii, json, os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

SURUM = 1
# Geliştiricinin (Ertan) açık anahtarı. Gizli anahtarı yalnız Ertan'ın Mac'inde: /Volumes/BİLGİSAYARIM/DERS DAĞITIMM/LOGOS-DISIPLIN-KURTARMA
# (depoda değil). Sınamada LV_GELISTIRICI_ACIK_ANAHTAR (boş: özellik kapalı).
ACIK_ANAHTAR = '1137c4c3bde302746562762683c7bfc13db4cf043ae692d87f4b6d8adfb82761'
BILGI_HKDF = b'LOGOS-Disiplin kurtarma istegi 1'
ALFABE = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
KARISAN = {'I': '1', 'L': '1', 'O': '0'}
SINIR = '-----'
BAS = '----- KURTARMA İSTEĞİ (değiştirmeden gönderin) -----'
SON = '----- İSTEĞİN SONU -----'


class Hata(Exception):
    pass


# ------------------------------------------------------------------ base32 (Crockford)
def b32(bayt):
    n = len(bayt); c = -(-n * 8 // 5)
    sayi = int.from_bytes(bayt, 'big') << (c * 5 - n * 8)
    return ''.join(ALFABE[(sayi >> (5 * (c - 1 - i))) & 31] for i in range(c))


def b32c(metin):
    s = [KARISAN.get(ch, ch) for ch in str(metin or '').upper()]
    s = [ch for ch in s if ch in ALFABE]
    c = len(s); n = c * 5 // 8
    if not c: return b''
    sayi = 0
    for ch in s: sayi = (sayi << 5) | ALFABE.index(ch)
    return (sayi >> (c * 5 - n * 8)).to_bytes(n, 'big')


def obekle(s, n=4, satir=8):
    """'ABCD-EFGH-… ' satır başına 8 öbek (e-postada satırlar kırılmasın)."""
    o = [s[i:i + n] for i in range(0, len(s), n)]
    return '\n'.join('-'.join(o[i:i + satir]) for i in range(0, len(o), satir))


# ------------------------------------------------------------------ anahtarlar
def acik_anahtar():
    """Uygulamanın kullandığı açık anahtar (X25519PublicKey) ya da None (özellik kapalı)."""
    h = os.environ.get('LV_GELISTIRICI_ACIK_ANAHTAR')
    h = ACIK_ANAHTAR if h is None else h.strip()
    if not h: return None
    try: return X25519PublicKey.from_public_bytes(binascii.unhexlify(h))
    except (ValueError, binascii.Error): return None


def _acik_bayt(acik):
    return acik.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def anahtar_uret():
    """(gizli anahtar hex, açık anahtar hex). Yalnız geliştiricinin aracı çağırır."""
    g = X25519PrivateKey.generate()
    gb = g.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    return gb.hex(), _acik_bayt(g.public_key()).hex()


def gizli_anahtar(hex_metin):
    try: return X25519PrivateKey.from_private_bytes(binascii.unhexlify(hex_metin.strip()))
    except (ValueError, binascii.Error): raise Hata('Gizli anahtar okunamadı')


def _turet(paylasilan, gecici, acik):
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=gecici + acik, info=BILGI_HKDF).derive(paylasilan)


# ------------------------------------------------------------------ istek
def istek_yap(kod, kimlik, bilgi, acik=None):
    """Kasanın kurtarma isteği (metin). kod: 32 karakterlik R ('ABCD-…'); kimlik: kasanın kimliği (32 hex); bilgi: {okul, il, ilce, kurum_kodu}."""
    acik = acik or acik_anahtar()
    if acik is None: raise Hata('Geliştiricinin açık anahtarı yok')
    r = b32c(kod)
    if len(r) != 20: raise Hata('Kod 32 karakter olmalı')
    g = X25519PrivateKey.generate(); gecici = _acik_bayt(g.public_key()); ab = _acik_bayt(acik)
    anahtar = _turet(g.exchange(acik), gecici, ab)
    govde = r + bytes.fromhex(kimlik) + json.dumps({k: v for k, v in (bilgi or {}).items() if v}, ensure_ascii=False,
                                                   separators=(',', ':')).encode('utf-8')
    sifreli = AESGCM(anahtar).encrypt(bytes(12), govde, bytes([SURUM]) + gecici)     # anahtar tek kullanımlık: sabit nonce güvenli
    return obekle(b32(bytes([SURUM]) + gecici + sifreli))


def istek_ayikla(metin):
    """E-postadan yapıştırılan metinden istek: iki '-----' satırı arası (varsa; alıntı işareti '>' de olur), yoksa bütün metin."""
    t = str(metin or '')
    satirlar = t.splitlines(); sinir = [i for i, s in enumerate(satirlar) if s.lstrip('> \t').startswith(SINIR)]
    if len(sinir) >= 2: t = '\n'.join(satirlar[sinir[0] + 1:sinir[1]])
    elif len(sinir) == 1: t = '\n'.join(satirlar[sinir[0] + 1:])
    return b32c(t)


def istek_coz(metin, gizli):
    """Geliştiricinin aracı: {kod ('ABCD-…'), kimlik, bilgi}. Bozuk ya da başka anahtara ait istekte Hata."""
    b = istek_ayikla(metin)
    if len(b) < 1 + 32 + 16 + 36 or b[0] != SURUM: raise Hata('Bu bir LOGOS Veli İzin kurtarma isteği değil ya da eksik kopyalanmış')
    gecici = b[1:33]
    try:
        anahtar = _turet(gizli.exchange(X25519PublicKey.from_public_bytes(gecici)), gecici, _acik_bayt(gizli.public_key()))
        govde = AESGCM(anahtar).decrypt(bytes(12), b[33:], bytes([SURUM]) + gecici)
    except Exception:
        raise Hata('İstek açılamadı: eksik ya da yanlış kopyalanmış (e-postadaki bütün bloğu kopyalayın) ya da başka bir anahtara ait')
    kod = b32(govde[:20]); kod = '-'.join(kod[i:i + 4] for i in range(0, 32, 4))
    try: bilgi = json.loads(govde[36:].decode('utf-8') or '{}')
    except ValueError: bilgi = {}
    return {'kod': kod, 'kimlik': govde[20:36].hex(), 'bilgi': bilgi}


def eposta(istek):
    """Okulun geliştiriciye göndereceği e-posta (konu, gövde). Kasa kilitli: okulun adını uygulama bilmez, okul yazar."""
    govde = ('Merhaba,\n\nLOGOS Veli İzin\'in şifresini ve kurtarma anahtarını kaybettik. Kurtarma isteğimiz aşağıdadır.\n\n'
             'Okulun adı:\nAdınız soyadınız ve göreviniz:\nOkulun telefonu:\n\n'
             f'{BAS}\n{istek}\n{SON}\n')
    return {'konu': 'LOGOS Veli İzin kurtarma isteği', 'govde': govde}


def yanit(kod, bilgi):
    """Geliştiricinin okula yanıtı (panoya)."""
    okul = (bilgi or {}).get('okul') or 'okulunuz'
    return (f'Merhaba,\n\n{okul} için LOGOS Veli İzin kurtarma kodunuz:\n\n{kod}\n\n'
            'LOGOS Veli İzin\'in kilit ekranında "Şifremi unuttum"a basın, bu kodu kurtarma anahtarı kutusuna yazın ve yeni şifrenizi '
            'belirleyin. Kod yalnız sizin kasanızı ve yalnız bir kez açar.\n\nKasa açılınca Ayarlar › Kilit ve kurtarma › '
            'Yeni kurtarma anahtarı ile yeni bir kurtarma anahtarı alıp yazdırmanızı öneririm.\n')
