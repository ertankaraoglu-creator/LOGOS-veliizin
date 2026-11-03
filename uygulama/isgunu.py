"""İş günü ve okul günü hesabı (veri/tatiller.json + okulun kendi kapalı günleri).

Yönetmelikteki süreler iş günüyle: kurulun karar süresi 10 iş günü (192/3), itiraz 5 iş günü (169/3), tedbir 10 iş günü (175).
İş günü sayılmayanlar: hafta sonu, resmî tatiller, MEB çalışma takvimindeki ara tatiller ve yarıyıl tatili (Ertan, 15.10.2026:
"ara tatil iş günü sayılmaz", "yarıyıl da sayılmaz"), okulun kapalı olduğu günler (kar tatili, valilik kararı; Ayarlar'dan).
Yarım günler (28 Ekim öğleden sonra, arifeler) iş günüdür.

Okul günü (uzaklaştırma cezası "okulun açık olduğu sürede" uygulanır, 172/1-a): iş günü ve ders yılının içinde (yaz tatili değil).

Dosyada dini bayramları ya da çalışma takvimi olmayan yıla düşen hesapta `eksik` döner (ne eksik olduğu, kısa metin): arayüz
"programda yok, kontrol edin" der; yeni yıl gelince tatiller.json'a eklenir.
"""
import datetime, json, os

from uygulama import veri as VR

_veri = None
_ek = {}                 # okulun kapalı günleri {'2026-12-14': 'Kar tatili'}: açık kasanın ayarlarından (ek_ayarla)
GUN_ADI = ('Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar')
EK_EN_COK = 60           # okulun kapalı gün kaydı (aralık) sayısı
EK_ARALIK_EN_COK = 120   # bir kaydın en çok gün sayısı


class Hata(Exception):
    def __init__(self, ileti, alan=None):
        super().__init__(ileti); self.alan = alan


def veri():
    global _veri
    if _veri is None:
        with open(os.path.join(VR.kok(), 'veri', 'tatiller.json'), encoding='utf-8') as f: _veri = json.load(f)
    return _veri


def bugun():
    """Bugün. Sınamada LV_BUGUN (ISO) ile başka gün verilebilir (yalnız öğretim yılı ve istatistik için; tarih denetimleri gerçek günle)."""
    t = os.environ.get('LV_BUGUN')
    if not t and os.environ.get('LV_BUGUN_DOSYASI'):                  # arayüz sınaması sunucu çalışırken günü değiştirebilsin
        try:
            with open(os.environ['LV_BUGUN_DOSYASI'], encoding='utf-8') as f: t = f.read().strip()
        except OSError: t = None
    return datetime.date.fromisoformat(t) if t else datetime.date.today()


def ogretim_yili(t=None):
    """Takvimden öğretim yılı (Ertan 30.10.2026: "program takvimi takip etsin, Eylül'de yeni yılı anlasın"): eğitim öğretim yılı
    1 Eylül'de başlar (öğretmenlerin mesleki çalışması), 31 Ağustos'ta biter. '2026-10-30' → '2026-2027'; '2027-06-15' → '2026-2027';
    t verilmezse bugün. Okunamayan tarihte bugünün yılı."""
    try: d = _gun(t) if t else bugun()
    except (ValueError, TypeError): d = bugun()
    y = d.year if d.month >= 9 else d.year - 1
    return f'{y}-{y + 1}'


def _gun(t):
    return t if isinstance(t, datetime.date) else datetime.date.fromisoformat(str(t)[:10])


def _araliktaki(bas, bit):
    d, b = _gun(bas), _gun(bit)
    while d <= b:
        yield d; d += datetime.timedelta(days=1)


# ------------------------------------------------------------------ okulun kapalı günleri (kasa ayarı)
def ek_duzelt(L):
    """Ayarlar'dan gelen [{bas, bit, ad}] → denetlenmiş liste (Hata(alan='kapali/<i>'))."""
    S = []
    for i, x in enumerate(L or []):
        x = x or {}; alan = f'kapali/{i}'
        if not (x.get('bas') or x.get('bit') or x.get('ad')): continue
        try: bas = _gun(x.get('bas')); bit = _gun(x.get('bit') or x.get('bas'))
        except ValueError: raise Hata('Kapalı günün tarihini girin', alan)
        if bit < bas: raise Hata('Bitiş başlangıçtan önce olamaz', alan)
        if (bit - bas).days >= EK_ARALIK_EN_COK: raise Hata(f'Bir kayıt en çok {EK_ARALIK_EN_COK} gün olabilir', alan)
        ad = ' '.join(str(x.get('ad') or '').split())[:60]
        if not ad: raise Hata('Neden kapalı olduğunu yazın (ör. kar tatili, valilik kararı)', alan)
        S.append({'bas': bas.isoformat(), 'bit': bit.isoformat(), 'ad': ad})
    if len(S) > EK_EN_COK: raise Hata(f'En çok {EK_EN_COK} kayıt girilebilir', 'kapali')
    return sorted(S, key=lambda x: x['bas'])


def ek_ayarla(L):
    """Açık kasanın kapalı günleri bu modülün hesaplarına girer (Api her çağrıda ayarlar; kasa kilitlenince boşalır)."""
    global _ek
    _ek = {d.isoformat(): x['ad'] for x in L or [] for d in _araliktaki(x['bas'], x['bit'])}


# ------------------------------------------------------------------ çalışma takvimi
def takvim(d):
    """d'nin düştüğü öğretim yılının MEB çalışma takvimi (dosyada yoksa None). Öğretim yılı 1 Eylül - 31 Ağustos."""
    d = _gun(d); y = d.year if d.month >= 9 else d.year - 1
    return veri().get('okul_takvimi', {}).get(f'{y}-{y + 1}')


def tatil(d):
    """Gün iş günü değilse sebebi (resmî tatil, ara tatil / yarıyıl, okulun kapalı günü), değilse None. Hafta sonu ayrı."""
    d = _gun(d); v = veri()
    r = v['sabit'].get(d.strftime('%m-%d')) or (v['dini'].get(str(d.year)) or {}).get(d.isoformat())
    if r: return r
    t = takvim(d)
    for a in (t or {}).get('tatiller') or []:
        if a['bas'] <= d.isoformat() <= a['bit']: return a['ad']
    return _ek.get(d.isoformat())


def is_gunu(d):
    d = _gun(d)
    return d.weekday() < 5 and not tatil(d)


def okul_gunu(d):
    """Okulun açık olduğu gün: iş günü ve ders yılının içinde (takvim dosyada yoksa yalnız iş günü)."""
    d = _gun(d); t = takvim(d)
    if t and not t['baslangic'] <= d.isoformat() <= t['bitis']: return False
    return is_gunu(d)


def neden(d):
    """Okul günü değilse kullanıcıya söylenecek sebep: 'Cumartesi', 'Cumhuriyet Bayramı', 'yaz tatili' …"""
    d = _gun(d)
    if d.weekday() >= 5: return GUN_ADI[d.weekday()]
    t = tatil(d)
    if t: return t
    tk = takvim(d)
    if tk and d.isoformat() < tk['baslangic']: return 'ders yılı başlamadı'
    if tk and d.isoformat() > tk['bitis']: return 'yaz tatili'
    return None


def _eksik(d):
    """d için dosyada eksik olan bilgi (kısa metin) ya da None."""
    if str(d.year) not in veri()['dini']: return f'{d.year} yılının bayram tarihleri'
    if not takvim(d):
        y = d.year if d.month >= 9 else d.year - 1
        return f'{y}-{y + 1} öğretim yılının çalışma takvimi (ara tatiller)'
    return None


def ekle(bas, n):
    """bas tarihinden sonraki n. iş günü (bas sayılmaz): 'tebliği izleyen 5 iş günü' → ekle(tebliğ, 5).
    Dönüş (tarih, eksik): eksik, hesaba giren ama dosyada olmayan bilgi (yoksa None)."""
    d = _gun(bas); eksik = None; kalan_ = n
    while kalan_:
        d += datetime.timedelta(days=1)
        eksik = eksik or _eksik(d)
        if is_gunu(d): kalan_ -= 1
    return d, eksik


def kalan(son, bugun=None):
    """Son güne kadar kalan iş günü (bugün sayılmaz; son gün sayılır). Geçtiyse eksi."""
    b = bugun or datetime.date.today(); s = _gun(son)
    if s < b:
        return -sum(1 for i in range((b - s).days) if is_gunu(s + datetime.timedelta(days=i + 1)))
    return sum(1 for i in range((s - b).days) if is_gunu(b + datetime.timedelta(days=i + 1)))


def okul_gunleri(bas, n, en_cok=400):
    """bas tarihinden (dahil) başlayarak art arda n okul günü (uzaklaştırma önerisi). Dönüş (günler, eksik)."""
    d = _gun(bas); L = []; eksik = None
    for _ in range(en_cok):
        eksik = eksik or _eksik(d)
        if okul_gunu(d): L.append(d.isoformat())
        if len(L) == n: break
        d += datetime.timedelta(days=1)
    return L, eksik


def sonraki_okul_gunu(d):
    """d'den sonraki ilk okul günü (d sayılmaz)."""
    L, _ = okul_gunleri(_gun(d) + datetime.timedelta(days=1), 1)
    return L[0] if L else None


def gun_metni(t):
    """'2026-10-21' → '21.10.2026 Çarşamba'."""
    d = _gun(t)
    return f'{d.strftime("%d.%m.%Y")} {GUN_ADI[d.weekday()]}'


def takvim_ozet(yil):
    """Arayüz için: öğretim yılının MEB takvimi (ders yılı, ara tatiller, yarıyıl) ve kaynağı."""
    t = veri().get('okul_takvimi', {}).get(yil)
    return dict(t, yil=yil) if t else None
