"""Şifreli kasa: öğrenci listesi, veli izin dilekçeleri ve öğrenci belgeleri tek dosyada (.lvk), şifreli. LOGOS Disiplin'in kasa.py'sinin
birebir kopyası (biçim adı ve uzantı farklı); iki kardeş uygulama aynı kasa düzenini paylaşır.

Neden: öğrenci adları, fotoğrafları, kimlik numaraları ve velilerin telefonları okulun hassas verisidir. Kasa dosyası kopyalansa, çalınsa, yanlışlıkla e-postayla
gitse bile şifre olmadan okunamaz. LOGOS Veli İzin hiçbir sunucuya veri göndermez; veri okuldan çıkmaz.

Yapı (dosya UTF-8 JSON; yalnız biçim bilgisi açık, okul adı dahil her şey şifreli):
  veri anahtarı (VA): rastgele 32 bayt; bütün veri AES-256-GCM ile bununla şifrelenir (önce zlib ile sıkıştırılır).
  VA üç kez sarılır: şifreden, okulun kurtarma anahtarından ve geliştiricinin tek kullanımlık kodundan türetilen anahtarlarla (scrypt).
  Şifre değişince yalnız sarım değişir, veri yeniden şifrelenmez. Şifre unutulunca kurtarma anahtarıyla açılır, yeni şifre konur.
  Kurtarma anahtarı da kaybolursa geliştiriciden kurtarma (gelistirici.py, Ertan 01.11.2026): kodu yalnız bu kasayı ve yalnız bir kez açar,
  okul Ayarlar'dan kapatabilir. Evrensel açma kodu yoktur: bütün kasaları açan tek bir şifre ya da kod uygulamada da geliştiricide de yok.
Yazma: önce yanına geçici dosya, sonra yer değiştirme (yarım yazılmış kasa olmaz); yazmadan önce eskisi yedeklere gider.
Çakışma: kasa açıldıktan sonra dosya başka bir yerden (ör. ağdaki ikinci bilgisayar) yazıldıysa üstüne yazılmaz (Cakisma).
"""
import base64, datetime, hashlib, hmac, json, os, secrets, shutil, time, unicodedata, uuid, zlib

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from uygulama import gelistirici as GL

BICIM = 'LOGOS-VeliIzin-Kasa'
BICIM_SURUM = 1
UZANTI = '.lvk'
# scrypt: bellek 128 * r * n bayt (n=2**16, r=8 → 64 MB), sıradan bir okul bilgisayarında ~0,3 sn. Değerler dosyaya yazılır:
# ileride artırılırsa eski kasalar kendi değerleriyle açılır, ilk şifre değişikliğinde yeni değere geçer.
SCRYPT = {'n': 2 ** 16, 'r': 8, 'p': 1}
SCRYPT_BELLEK = 256 * 1024 * 1024
YEDEK_KLASORU = 'yedekler'
YEDEK_EN_COK = 40             # en yeni 40 yedek kalır; ayrıca son 60 günün her gününün ilk yedeği (YEDEK_GUN)
YEDEK_GUN = 60
DENEME = 25                   # Windows'ta virüs tarayıcısı / dizin oluşturucu dosyayı bir an kilitler: 25 × 0,1 sn yeniden denenir
YEDEK_ARALIK_SN = 10 * 60     # aynı oturumda en çok 10 dakikada bir yedek (her tıklamada değil)
# Ekler (taranmış tutanak, ifade, savunma): kasanın yanındaki klasörde, her biri ayrı dosya, kasanın veri anahtarıyla AES-256-GCM.
# Kasaya yalnız kaydı (ad, tür, boyut) girer: kasa dosyası büyümez, her kayıtta yeniden şifrelenmez. Şifre değişince ekler yeniden
# şifrelenmez (veri anahtarı aynı). Silinen ek yedeklerden dönülebilsin diye EK_SILINEN_GUN gün '.silindi' olarak durur.
EK_KLASOR_UZANTI = '.ekler'
EK_UZANTI = '.lde'
EK_BASLIK = b'LDEK1'
EK_SILINEN_GUN = 60

# Kurtarma anahtarı: 20 rastgele bayt (160 bit) = 32 karakter, 4'lü 8 öbek. Crockford alfabesi: karışan harfler yok
# (I, L, O, U); elle yazarken yapılan I/L → 1, O → 0 karışıklığı düzeltilir.
ALFABE = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
KARISAN = {'I': '1', 'L': '1', 'O': '0'}


class Hata(Exception):
    """Kullanıcıya gösterilecek Türkçe hata."""


class SifreYanlis(Hata):
    pass


class Bozuk(Hata):
    pass


class Cakisma(Hata):
    pass


# ------------------------------------------------------------------ yardımcılar
def _b64(b):
    return base64.b64encode(b).decode('ascii')


def _b64c(s):
    try: return base64.b64decode(s.encode('ascii'), validate=True)
    except Exception: raise Bozuk('Kasa dosyası bozuk (kodlama)')


def _zaman():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _turet(gizli, tuz, kdf):
    """Şifreden ya da kurtarma anahtarından 32 baytlık sarma anahtarı (scrypt)."""
    return hashlib.scrypt(gizli.encode('utf-8'), salt=tuz, n=kdf['n'], r=kdf['r'], p=kdf['p'], maxmem=SCRYPT_BELLEK, dklen=32)


def _aad(kimlik, rol):
    """Şifreli parçayı bu kasaya ve rolüne bağlar: başka kasadan ya da başka alandan taşınmış parça açılmaz."""
    return f'{BICIM}|{kimlik}|{rol}'.encode('utf-8')


def sifre_duzelt(sifre):
    """Şifre olduğu gibi kullanılır; yalnız Unicode biçimi tekleştirilir (Mac ile Windows'ta 'ş' aynı bayt olsun)."""
    return unicodedata.normalize('NFC', str(sifre if sifre is not None else ''))


def sifre_denetle(sifre, kurum_kodu=None):
    """Yeni şifre kuralları (Ertan 01.11.2026: "4 basamaklı rakam yapabilmeliyiz; çok da güvenlik kasmamak lazım; okullarda yalnızca
    müdür yardımcısının kullandığı bir uygulamada yeterli; isteyen 10 haneli karışık şifre de yapabilir"): en az 4 karakter (4 haneli
    rakam olur), hepsi aynı karakter olmasın (0000), okulun kurum kodu ya da onun bir parçası olmasın (herkesin bildiği sayı).
    Bilinen sınır: kısa rakam şifre bilgisayarın başına oturanı durdurur; kasa dosyasını kopyalayıp deneyen biri 4 haneliyi saatler
    içinde bulur (scrypt'le bile on bin deneme). Uzun şifre isteyen yazar; kurallar onu da kabul eder."""
    s = sifre_duzelt(sifre)
    if len(s) < 4: raise Hata('Şifre en az 4 karakter olmalı (4 haneli bir rakam olabilir)')
    if len(set(s)) < 2: raise Hata('Şifre tek bir karakterin tekrarı olmasın (0000 gibi)')
    kod = ''.join(ch for ch in str(kurum_kodu or '') if ch.isdigit())
    if len(kod) >= 4 and (kod in s or s in kod): raise Hata('Şifre okulun kurum kodu ya da onun bir parçası olamaz: o kodu herkes biliyor')
    return s


def kurtarma_uret():
    """Yeni kurtarma anahtarı: 'ABCD-EFGH-…' (8 öbek)."""
    sayi = int.from_bytes(secrets.token_bytes(20), 'big'); h = []
    for _ in range(32): h.append(ALFABE[sayi & 31]); sayi >>= 5
    s = ''.join(reversed(h))
    return '-'.join(s[i:i + 4] for i in range(0, 32, 4))


def kurtarma_duzelt(anahtar):
    """Kullanıcının yazdığı kurtarma anahtarı: boşluk, tire, küçük harf ve karışan harfler düzeltilir; 32 karakter değilse Hata."""
    s = ''.join(ch for ch in str(anahtar or '').upper() if ch.isalnum())
    s = ''.join(KARISAN.get(ch, ch) for ch in s)
    if len(s) != 32 or any(ch not in ALFABE for ch in s):
        raise Hata('Kurtarma anahtarı 32 karakterdir (ör. 7K2M-…); yazdırdığınız kağıttaki gibi girin')
    return '-'.join(s[i:i + 4] for i in range(0, 32, 4))


def _israrla(is_, *a):
    """Dosya işi; Windows'taki kısa kilitlerde (PermissionError) biraz bekleyip yeniden dener."""
    for i in range(DENEME):
        try: return is_(*a)
        except PermissionError:
            if i == DENEME - 1: raise
            time.sleep(0.1)


def _json_oku(yol):
    with open(yol, encoding='utf-8') as f: return json.load(f)


def baslik_oku(yol):
    """Kasanın açık kısmı (biçim, kimlik, yazılma zamanı). Kasa değilse Bozuk."""
    try:
        b = _israrla(_json_oku, yol)
    except FileNotFoundError: raise
    except (OSError, ValueError): raise Bozuk('Bu dosya bir LOGOS Veli İzin kasası değil ya da bozuk')
    if not isinstance(b, dict) or b.get('bicim') != BICIM: raise Bozuk('Bu dosya bir LOGOS Veli İzin kasası değil')
    if int(b.get('surum') or 0) > BICIM_SURUM:
        raise Hata('Bu kasa LOGOS Veli İzin\'in daha yeni bir sürümüyle yazılmış; programı güncelleyin')
    for k in ('kimlik', 'kdf', 'anahtarlar', 'veri'):
        if k not in b: raise Bozuk('Kasa dosyası eksik (' + k + ')')
    return b


# ------------------------------------------------------------------ kasa
class Kasa:
    """Açık kasa: veri (dict) bellekte, veri anahtarı bellekte. kilitle() ikisini de bırakır."""

    def __init__(self, yol, baslik, va, veri):
        self.yol = yol; self.baslik = baslik; self._va = va; self.veri = veri
        self._sayac = int(baslik['veri'].get('sayac') or 0)
        self._son_yedek = 0.0

    # -------------------------------------------------------------- kurma ve açma
    @classmethod
    def olustur(cls, yol, sifre, veri, kurum_kodu=None):
        """Yeni kasa yazar. (Kasa, kurtarma anahtarı) döner; kurtarma anahtarı yalnız burada görünür, hiçbir yere yazılmaz."""
        s = sifre_denetle(sifre, kurum_kodu)
        if os.path.exists(yol): raise Hata('Bu konumda zaten bir kasa var')
        os.makedirs(os.path.dirname(os.path.abspath(yol)), exist_ok=True)
        kimlik = uuid.uuid4().hex; va = AESGCM.generate_key(256); kurtarma = kurtarma_uret()
        b = {'bicim': BICIM, 'surum': BICIM_SURUM, 'kimlik': kimlik, 'olusturma': _zaman(), 'kdf': {'tur': 'scrypt', **SCRYPT},
             'anahtarlar': {}, 'veri': {'sayac': 0}}
        b['anahtarlar']['sifre'] = cls._sar(va, s, b, 'sifre')
        b['anahtarlar']['kurtarma'] = cls._sar(va, kurtarma, b, 'kurtarma')
        k = cls(yol, b, va, veri)
        k._yaz()
        return k, kurtarma

    @staticmethod
    def _sar(va, gizli, b, rol):
        tuz = secrets.token_bytes(16); nonce = secrets.token_bytes(12)
        ka = _turet(gizli, tuz, b['kdf'])
        return {'tuz': _b64(tuz), 'nonce': _b64(nonce), 'sarili': _b64(AESGCM(ka).encrypt(nonce, va, _aad(b['kimlik'], 'anahtar:' + rol)))}

    @staticmethod
    def _coz_sarim(b, gizli, rol):
        a = (b.get('anahtarlar') or {}).get(rol)
        if not a: raise Bozuk('Kasa dosyası eksik (anahtar)')
        ka = _turet(gizli, _b64c(a['tuz']), b['kdf'])
        try: return AESGCM(ka).decrypt(_b64c(a['nonce']), _b64c(a['sarili']), _aad(b['kimlik'], 'anahtar:' + rol))
        except Exception: return None

    @classmethod
    def _ac(cls, yol, gizli, rol):
        b = baslik_oku(yol)
        va = cls._coz_sarim(b, gizli, rol)
        if va is None:
            raise SifreYanlis({'sifre': 'Şifre yanlış', 'kurtarma': 'Kurtarma anahtarı bu kasaya ait değil'}.get(
                rol, 'Kod bu kasaya ait değil ya da daha önce kullanıldı'))
        v = b['veri']
        try:
            ham = AESGCM(va).decrypt(_b64c(v['nonce']), _b64c(v['sifreli']), _aad(b['kimlik'], 'veri'))
            veri = json.loads(zlib.decompress(ham).decode('utf-8'))
        except Exception:
            raise Bozuk('Kasa açıldı ama veri bozuk; en son yedeği açmayı deneyin')
        return cls(yol, b, va, veri)

    @classmethod
    def ac(cls, yol, sifre):
        return cls._ac(yol, sifre_duzelt(sifre), 'sifre')

    @classmethod
    def kurtarma_ile_ac(cls, yol, anahtar):
        return cls._ac(yol, kurtarma_duzelt(anahtar), 'kurtarma')

    @classmethod
    def gelistirici_ile_ac(cls, yol, kod):
        """Geliştiricinin verdiği tek kullanımlık kodla açar. Açan hemen gelistirici_kur ile yeni kod üretmeli (eskisi ölsün)."""
        if 'gelistirici' not in (baslik_oku(yol).get('anahtarlar') or {}):
            raise SifreYanlis('Bu kasada geliştiriciden kurtarma kapalı')
        return cls._ac(yol, kurtarma_duzelt(kod), 'gelistirici')

    # -------------------------------------------------------------- durum
    @property
    def acik(self):
        return self._va is not None

    def kilitle(self):
        """Veri anahtarı ve veri bellekten bırakılır (Python bayt dizisini silemez; başvuruyu bırakırız)."""
        self._va = None; self.veri = None

    def _gerek(self):
        if not self.acik: raise Hata('Kasa kilitli')

    # -------------------------------------------------------------- yazma
    def kaydet(self):
        """Bellekteki veriyi diske yazar. Yazılamazsa (dosya kilitli, disk dolu) bellekteki veri diskteki son hâline döner ve Hata:
        ekranda görünen ile kasadaki hiçbir zaman ayrışmaz (yoksa kaydedilmemiş değişiklik kilitlenince kaybolurdu)."""
        self._gerek()
        try: disk = baslik_oku(self.yol)
        except FileNotFoundError: disk = None
        if disk is not None and (disk.get('kimlik') != self.baslik['kimlik'] or int(disk['veri'].get('sayac') or 0) != self._sayac):
            raise Cakisma('Kasa siz açtıktan sonra başka bir yerden değişmiş (ör. ağdaki başka bir bilgisayar). Üstüne yazılmadı: '
                          'kasayı kapatıp yeniden açın')
        try: self._yedekle()
        except OSError: pass                                     # yedek alınamadı diye kayıt durmaz (bir sonrakinde yeniden denenir)
        try:
            self._yaz()
        except OSError as e:
            self._diskten_geri()
            raise Hata(f'Kaydedilemedi: kasa dosyasına yazılamadı ({e.__class__.__name__}). Son değişiklik geri alındı; bir kez daha deneyin. '
                       f'Sürerse virüs tarayıcısının ya da bulut eşitlemesinin dosyayı tutup tutmadığına bakın.')

    def _yaz(self):
        """Yeni başlık önce geçici dosyaya, sonra tek adımda asıl dosyanın yerine. Sayaç ve başlık ancak yazma başarılı olunca değişir."""
        nonce = secrets.token_bytes(12)
        ham = zlib.compress(json.dumps(self.veri, ensure_ascii=False, separators=(',', ':')).encode('utf-8'), 6)
        sayac = self._sayac + 1
        b = dict(self.baslik, veri={'nonce': _b64(nonce), 'sifreli': _b64(AESGCM(self._va).encrypt(nonce, ham, _aad(self.baslik['kimlik'], 'veri'))),
                                    'sayac': sayac, 'yazilma': _zaman()})
        gecici = self.yol + '.yaziliyor'

        def yaz():
            with open(gecici, 'w', encoding='utf-8') as f:
                json.dump(b, f, ensure_ascii=False, indent=1)
                f.flush(); os.fsync(f.fileno())
        _israrla(yaz)
        _israrla(os.replace, gecici, self.yol)
        self.baslik = b; self._sayac = sayac

    def _diskten_geri(self):
        """Yazma başarısız: veri ve başlık diskteki son hâline döner (aynı veri anahtarıyla). Disk de okunamazsa bellekteki kalır."""
        try:
            b = baslik_oku(self.yol); v = b['veri']
            ham = AESGCM(self._va).decrypt(_b64c(v['nonce']), _b64c(v['sifreli']), _aad(b['kimlik'], 'veri'))
            self.veri = json.loads(zlib.decompress(ham).decode('utf-8')); self.baslik = b; self._sayac = int(v.get('sayac') or 0)
        except Exception:
            pass

    def _yedekle(self, zorla=False):
        """Diskteki (bir önceki) kasayı yedekler klasörüne kopyalar. Yedek de şifrelidir (aynı dosya)."""
        if not os.path.exists(self.yol): return None
        if not zorla and time.time() - self._son_yedek < YEDEK_ARALIK_SN: return None
        kl = os.path.join(os.path.dirname(os.path.abspath(self.yol)), YEDEK_KLASORU); os.makedirs(kl, exist_ok=True)
        kok = os.path.splitext(os.path.basename(self.yol))[0]
        hedef = os.path.join(kl, f"{kok}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}{UZANTI}")
        _israrla(shutil.copy2, self.yol, hedef); self._son_yedek = time.time()
        eski = sorted(x for x in os.listdir(kl) if x.startswith(kok + '-') and x.endswith(UZANTI))
        kalsin = set(eski[-YEDEK_EN_COK:]); gunler = {}
        for x in eski:                                            # her günün ilk yedeği (son YEDEK_GUN gün)
            gun = x[len(kok) + 1:len(kok) + 9]
            gunler.setdefault(gun, x)
        kalsin |= set(sorted(gunler.values())[-YEDEK_GUN:])
        for x in eski:
            if x in kalsin: continue
            try: os.remove(os.path.join(kl, x))
            except OSError: pass
        return hedef

    # -------------------------------------------------------------- şifre ve kurtarma
    def sifre_dogru(self, sifre):
        """Açık kasada şifre sınaması (şifre değiştirme, kurtarma anahtarını yenileme gibi işlemlerden önce)."""
        self._gerek()
        va = self._coz_sarim(self.baslik, sifre_duzelt(sifre), 'sifre')
        return va is not None and hmac.compare_digest(va, self._va)

    def sifre_degistir(self, yeni, kurum_kodu=None):
        """Yeni şifreyle yeniden sarar: veri yeniden şifrelenmez, kurtarma anahtarı aynı kalır."""
        self._gerek(); s = sifre_denetle(yeni, kurum_kodu)
        self.baslik['anahtarlar']['sifre'] = self._sar(self._va, s, self.baslik, 'sifre')
        self.kaydet()

    def kurtarma_yenile(self):
        """Yeni kurtarma anahtarı (eskisi artık açmaz). Yeni anahtarı döner."""
        self._gerek(); k = kurtarma_uret()
        self.baslik['anahtarlar']['kurtarma'] = self._sar(self._va, k, self.baslik, 'kurtarma')
        self.kaydet()
        return k

    # -------------------------------------------------------------- geliştiriciden kurtarma (gelistirici.py)
    @property
    def gelistirici_var(self):
        return 'gelistirici' in (self.baslik.get('anahtarlar') or {})

    def gelistirici_kur(self, bilgi, kaydet=True):
        """Yeni tek kullanımlık kod ve kurtarma isteği; eski kod o anda geçersiz. Geliştiricinin açık anahtarı yoksa bir şey yapmaz (False)."""
        self._gerek(); acik = GL.acik_anahtar()
        if acik is None: return False
        kod = kurtarma_uret()
        self.baslik['anahtarlar']['gelistirici'] = self._sar(self._va, kod, self.baslik, 'gelistirici')
        self.baslik['gelistirici'] = {'istek': GL.istek_yap(kod, self.baslik['kimlik'], bilgi, acik), 'zaman': _zaman()}
        if kaydet: self.kaydet()
        return True

    def gelistirici_kapat(self):
        """Okul istemiyor: sarım ve istek başlıktan silinir (yalnız 'kapalı' bilgisi kalır: kilit ekranı doğru söylesin)."""
        self._gerek(); self.baslik['anahtarlar'].pop('gelistirici', None)
        self.baslik['gelistirici'] = {'kapali': True, 'zaman': _zaman()}
        self.kaydet()

    # -------------------------------------------------------------- ekler (taranmış belgeler)
    def ek_klasoru(self):
        """Kasanın yanındaki ek klasörü: 'Veli İzin Kasası.lvk' → 'Veli İzin Kasası.ekler'. Kasa taşınırsa klasör de taşınır."""
        return os.path.splitext(os.path.abspath(self.yol))[0] + EK_KLASOR_UZANTI

    def _ek_yolu(self, kimlik, silindi=False):
        if not isinstance(kimlik, str) or len(kimlik) != 24 or any(c not in '0123456789abcdef' for c in kimlik):
            raise Hata('Ek bulunamadı')
        return os.path.join(self.ek_klasoru(), kimlik + EK_UZANTI + ('.silindi' if silindi else ''))

    def ek_yaz(self, bayt):
        """Taranmış belgeyi kasanın veri anahtarıyla şifreleyip ek klasörüne yazar; kimliğini döner. Dosya adı rastgele (içinde
        öğrenci adı yok); içerik bu kasaya ve bu kimliğe bağlı (başka kasadan ya da başka ek yerine taşınmış dosya açılmaz)."""
        self._gerek(); kimlik = secrets.token_hex(12); nonce = secrets.token_bytes(12)
        govde = EK_BASLIK + nonce + AESGCM(self._va).encrypt(nonce, bytes(bayt), _aad(self.baslik['kimlik'], 'ek:' + kimlik))
        os.makedirs(self.ek_klasoru(), exist_ok=True)
        hedef = self._ek_yolu(kimlik); gecici = hedef + '.yaziliyor'

        def yaz():
            with open(gecici, 'wb') as f:
                f.write(govde); f.flush(); os.fsync(f.fileno())
        try:
            _israrla(yaz); _israrla(os.replace, gecici, hedef)
        except OSError as e:
            try: os.remove(gecici)
            except OSError: pass
            raise Hata(f'Ek kaydedilemedi ({e.__class__.__name__}): diskte yer ya da klasöre yazma izni olmayabilir')
        return kimlik

    def ek_oku(self, kimlik):
        """Şifresi çözülmüş baytlar. Silinmiş (yedekten dönülen kayıtta kalmış) ek de okunur."""
        self._gerek()
        yol = self._ek_yolu(kimlik)
        if not os.path.exists(yol) and os.path.exists(self._ek_yolu(kimlik, True)): yol = self._ek_yolu(kimlik, True)
        def oku():
            with open(yol, 'rb') as f: return f.read()
        try:
            b = _israrla(oku)
        except FileNotFoundError:
            raise Hata('Ekin dosyası bulunamadı (kasa başka yere taşındıysa yanındaki ".ekler" klasörü de taşınmalı)')
        if not b.startswith(EK_BASLIK): raise Bozuk('Ek dosyası bozuk')
        n = len(EK_BASLIK)
        try: return AESGCM(self._va).decrypt(b[n:n + 12], b[n + 12:], _aad(self.baslik['kimlik'], 'ek:' + kimlik))
        except Exception: raise Bozuk('Ek dosyası bu kasaya ait değil ya da bozuk')

    def ek_sil(self, kimlik):
        """Ek hemen silinmez, '.silindi' olur: kasa yedeğinden dönülürse yine açılır. EK_SILINEN_GUN sonra ek_temizle siler."""
        self._gerek(); yol = self._ek_yolu(kimlik)
        if os.path.exists(yol):
            try: _israrla(os.replace, yol, self._ek_yolu(kimlik, True)); os.utime(self._ek_yolu(kimlik, True))
            except OSError: pass

    def ek_temizle(self):
        """Silineli EK_SILINEN_GUN günden eski ekler diskten de gider."""
        kl = self.ek_klasoru(); sinir = time.time() - EK_SILINEN_GUN * 86400
        if not os.path.isdir(kl): return 0
        n = 0
        for x in os.listdir(kl):
            y = os.path.join(kl, x)
            try:
                if x.endswith('.silindi') and os.path.getmtime(y) < sinir: os.remove(y); n += 1
                elif x.endswith('.yaziliyor') and os.path.getmtime(y) < time.time() - 3600: os.remove(y)
            except OSError: pass
        return n

    def bilgi(self):
        """Arayüzde gösterilecek açık bilgiler (şifre gerektirmez)."""
        v = self.baslik.get('veri') or {}
        return {'yol': self.yol, 'ad': os.path.basename(self.yol), 'klasor': os.path.dirname(os.path.abspath(self.yol)),
                'olusturma': self.baslik.get('olusturma'), 'yazilma': v.get('yazilma'), 'sayac': v.get('sayac'),
                'yedek_klasoru': os.path.join(os.path.dirname(os.path.abspath(self.yol)), YEDEK_KLASORU),
                'ek_klasoru': os.path.splitext(os.path.abspath(self.yol))[0] + EK_KLASOR_UZANTI,
                'gelistirici': self.gelistirici_var}


def kurtarma_istegi(yol):
    """Kasanın açık başlığındaki kurtarma isteği (kasa kilitliyken): {istek, zaman} | {kapali, zaman} | {} (eski kasa)."""
    g = baslik_oku(yol).get('gelistirici')
    return dict(g) if isinstance(g, dict) else {}
