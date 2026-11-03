"""Veli izin dilekçesi: izin günleri, gün hesabı, dilekçe metinleri ve denetim (eski tek dosyalı HTML'deki mantık, Python'da).

Bir dilekçede günler {ISO tarih: 'tam' | 'once' | 'sonra'} tutulur (yarım gün öğleden önce / öğleden sonra). Hafta sonu, resmî
tatil, ara tatil ve okulun kapalı günleri izin günü sayılmaz (uygulama/isgunu.py). Geriye dönük (özür beyanı) ve ileriye dönük
(izin isteği) dilekçeler aynı belgedir: "Veli izin dilekçesi ve özür beyanı" (Ortaöğretim Kurumları Yönetmeliği md. 36).
Yönetmelik hatırlatması (kaydı engellemez): özür gününü izleyen 5 iş günü içinde veli beyanı.
"""
import datetime, re

from uygulama import isgunu

AYLAR = ('Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık')
GUNLER = isgunu.GUN_ADI
TURLER = {'tam': 'Tam gün', 'once': 'Yarım gün, öğleden önce', 'sonra': 'Yarım gün, öğleden sonra'}
YARIM = {'once': 'öğleden önce', 'sonra': 'öğleden sonra'}
# İzin nedenleri: (kod, ekrandaki ad, dilekçedeki ifade; "… nedeniyle" diye devam eder)
NEDENLER = [('hastalik', 'Hastalık', 'rahatsızlığı'), ('saglik', 'Sağlık kontrolü', 'hastanedeki muayene ve sağlık kontrolü'),
            ('aile', 'Aile zorunluluğu', 'ailevi zorunluluk'), ('cenaze', 'Cenaze', 'yakınının vefatı'),
            ('resmi', 'Resmî işlem', 'resmî kurumdaki işlemleri'), ('yol', 'Şehir dışı', 'ailece şehir dışına çıkılacak olması'),
            ('diger', 'Diğer', '')]
NEDEN_AD = {k: a for k, a, _ in NEDENLER}
NEDEN_METIN = {k: m for k, _, m in NEDENLER}
YAKINLIK = ('Anne', 'Baba', 'Vasi', 'Diğer')
BEYAN_IS_GUNU = 5                 # md. 36: özür gününü izleyen 5 iş günü
EN_COK_GUN = 60                   # bir dilekçede en çok gün (yanlışlıkla aylık seçime karşı)


class Hata(Exception):
    def __init__(self, ileti, alan=None):
        super().__init__(ileti); self.alan = alan


# ------------------------------------------------------------------ tarih yazımları
def _gun(t):
    return t if isinstance(t, datetime.date) else datetime.date.fromisoformat(str(t)[:10])


def tarih_uzun(t, gun_adi=False):
    """'2026-11-03' → '3 Kasım 2026' (gun_adi ile '3 Kasım 2026 Salı')."""
    d = _gun(t)
    return f'{d.day} {AYLAR[d.month - 1]} {d.year}' + (f' {GUNLER[d.weekday()]}' if gun_adi else '')


def tarih_kisa(t):
    d = _gun(t); return d.strftime('%d.%m.%Y')


def aralik_metni(a, b):
    """İki tarih aynıysa gün adıyla; aynı aydaysa '3-5 Kasım 2026'; aynı yıldaysa '30 Ekim - 2 Kasım 2026'."""
    if a == b: return tarih_uzun(a, True)
    x, y = _gun(a), _gun(b)
    if x.year != y.year: return f'{tarih_uzun(x)} - {tarih_uzun(y)}'
    if x.month != y.month: return f'{x.day} {AYLAR[x.month - 1]} - {tarih_uzun(y)}'
    return f'{x.day}-{tarih_uzun(y)}'


def sayi_metni(n):
    """Gün sayısı: 1 → '1', 2.5 → '2,5'."""
    n = float(n)
    return str(int(n)) if n == int(n) else str(n).replace('.', ',')


def yazi(n):
    b = ['', 'bir', 'iki', 'üç', 'dört', 'beş', 'altı', 'yedi', 'sekiz', 'dokuz']
    o = ['', 'on', 'yirmi', 'otuz', 'kırk', 'elli', 'altmış', 'yetmiş', 'seksen', 'doksan']
    n = int(n)
    if n == 0: return 'sıfır'
    if n >= 100: return str(n)
    return (o[n // 10] + ' ' + b[n % 10]).strip()


def toplam_metni(t):
    """Dilekçe cümlesi için: 0.5 → 'yarım gün', 2.5 → '2,5 (iki buçuk) gün', 3 → '3 (üç) gün'."""
    t = float(t)
    if t == 0.5: return 'yarım gün'
    tam, yarim = int(t), t % 1 != 0
    return f'{sayi_metni(t)} ({yazi(tam)}{" buçuk" if yarim else ""}) gün'


def gun_sayisi_metni(n):
    n = float(n)
    return 'yarım gün' if n == 0.5 else f'{sayi_metni(n)} gün'


# ------------------------------------------------------------------ günler
def gun_duzelt(gunler):
    """Arayüzden gelen {tarih: tür}: tarihler ISO, türler bilinen; okul günü olmayan tarih reddedilir. Sıralı sözlük döner."""
    if not isinstance(gunler, dict) or not gunler: raise Hata('Takvimden en az bir izin günü seçin.', 'gunler')
    if len(gunler) > EN_COK_GUN: raise Hata(f'Bir dilekçede en çok {EN_COK_GUN} gün seçilebilir.', 'gunler')
    out = {}
    for k in sorted(gunler):
        try: d = _gun(k)
        except (ValueError, TypeError): raise Hata(f'Geçersiz tarih: {k}', 'gunler')
        t = gunler[k] if gunler[k] in TURLER else 'tam'
        if not isgunu.okul_gunu(d):
            raise Hata(f'{tarih_uzun(d, True)} okul günü değil ({isgunu.neden(d) or "hafta sonu / tatil"}).', 'gunler')
        out[d.isoformat()] = t
    return out


def gun_degeri(t):
    return 1.0 if t == 'tam' else 0.5


def toplam(gunler):
    return sum(gun_degeri(t) for t in gunler.values())


def gruplar(gunler):
    """Art arda gelen aynı türdeki okul günleri bir aralık: [{'a', 'b', 't', 'n'}]. İki gün arasında 4 takvim gününden çok boşluk
    varsa (ara tatil) ayrı grup."""
    out = []
    for k in sorted(gunler):
        t = gunler[k]; son = out[-1] if out else None
        if son and son['t'] == t and isgunu.sonraki_okul_gunu(son['b']) == k and (_gun(k) - _gun(son['b'])).days <= 4:
            son['b'] = k; son['n'] += 1
        else:
            out.append({'a': k, 'b': k, 't': t, 'n': 1})
    for g in out: g['gun'] = g['n'] * gun_degeri(g['t'])
    return out


def tarihler_cumlesi(gunler):
    """Dilekçe cümlesindeki tarih parçası: '3 Kasım 2026 Salı günü öğleden önce' / '3-5 Kasım 2026 tarihleri arasında' /
    '3-5 Kasım 2026 ve 9 Kasım 2026 Pazartesi (öğleden sonra) tarihlerinde'."""
    G = gruplar(gunler)
    if not G: return ''
    if len(G) == 1:
        g = G[0]; y = YARIM.get(g['t'], '')
        if g['a'] == g['b']: return f"{tarih_uzun(g['a'], True)} günü" + (f' {y}' if y else '')
        return f"{aralik_metni(g['a'], g['b'])} tarihleri arasında" + (f' ({y})' if y else '')
    parca = [aralik_metni(g['a'], g['b']) + (f" ({YARIM[g['t']]})" if g['t'] in YARIM else '') for g in G]
    return ', '.join(parca[:-1]) + ' ve ' + parca[-1] + ' tarihlerinde'


def gunler_listesi(gunler):
    """Tabloda ve kayıt listesinde: '3-5 Kasım 2026 (3 gün); 9 Kasım 2026 Pazartesi, öğleden sonra (yarım gün)'."""
    return '; '.join(aralik_metni(g['a'], g['b']) + (f", {YARIM[g['t']]}" if g['t'] in YARIM else '') + f" ({gun_sayisi_metni(g['gun'])})"
                     for g in gruplar(gunler))


def yon(gunler, tarih):
    """Dilekçe tarihine göre: 'geriye' (özür beyanı: bütün günler dilekçe tarihinden önce), 'ileriye', ya da 'karisik'."""
    t = _gun(tarih); once = [k for k in gunler if _gun(k) < t]; sonra = [k for k in gunler if _gun(k) > t]
    if once and not sonra: return 'geriye'
    if sonra and not once: return 'ileriye'
    return 'karisik' if once and sonra else 'bugun'


def is_gunu_farki(a, b):
    """a'dan b'ye (a hariç, b dahil) iş günü sayısı."""
    n = 0; d = _gun(a); b = _gun(b)
    while d < b:
        d += datetime.timedelta(days=1)
        if isgunu.is_gunu(d): n += 1
    return n


# ------------------------------------------------------------------ dilekçe metni
VARSAYILAN_METIN = ("Velisi bulunduğum, aşağıda bilgileri yazılı öğrencimin {NEDEN} nedeniyle {TARIHLER} toplam {TOPLAM} süreyle, "
                    "Millî Eğitim Bakanlığı Ortaöğretim Kurumları Yönetmeliği'nin 36. maddesi kapsamında izinli sayılması hususunda "
                    "gereğini arz ederim.")
VARSAYILAN_KONU = 'Veli izin dilekçesi ve özür beyanı'
YER_TUTUCU = ('NEDEN', 'TARIHLER', 'TOPLAM', 'OGRENCI', 'SINIF', 'NO')


def metin_denetle(kalip):
    k = str(kalip or '').strip()
    if not k: raise Hata('Dilekçe cümlesi boş olamaz.', 'metin')
    for y in re.findall(r'\{([A-Za-zÇĞİÖŞÜçğıöşü_]+)\}', k):
        if y not in YER_TUTUCU: raise Hata(f'Bilinmeyen yer tutucu: {{{y}}}. Kullanılabilenler: ' + ', '.join('{' + x + '}' for x in YER_TUTUCU), 'metin')
    if '{TARIHLER}' not in k: raise Hata('Dilekçe cümlesinde izin günlerinin yazılacağı {TARIHLER} bulunmalı.', 'metin')
    return k


def metin(kalip, izin, ogrenci):
    """Yer tutucuları doldurur (düz metin; belge kalın yazacağı parçaları kendisi işaretler)."""
    gunler = izin['gunler']
    degerler = {'NEDEN': izin.get('neden') or '', 'TARIHLER': tarihler_cumlesi(gunler), 'TOPLAM': toplam_metni(toplam(gunler)),
                'OGRENCI': ogrenci.get('ad', ''), 'SINIF': ogrenci.get('sinif_ad') or ogrenci.get('sinif', ''), 'NO': str(ogrenci.get('no', ''))}
    return re.sub(r'\{([A-Z]+)\}', lambda m: degerler.get(m.group(1), m.group(0)), kalip or VARSAYILAN_METIN)


# ------------------------------------------------------------------ denetim
def duzelt(izin):
    """Arayüzden gelen dilekçeyi denetler ve kasaya yazılacak biçime getirir. Engelleyen hata Hata(ileti, alan)."""
    if not isinstance(izin, dict): raise Hata('Dilekçe verisi eksik.')
    no = izin.get('ogrenci_no')
    if no in (None, ''): raise Hata('Önce öğrenciyi seçin.', 'ogrenci')
    veli = izin.get('veli') or {}
    ad = ' '.join(str(veli.get('ad') or '').split())
    if len(ad) < 3: raise Hata('Dilekçeyi veren kişinin adını soyadını yazın.', 'veli_ad')
    yak = str(veli.get('yakinlik') or '').strip() or 'Velisi'
    if yak == 'Diğer':
        yak_aciklama = ' '.join(str(veli.get('yakinlik_aciklama') or '').split())
        if not yak_aciklama: raise Hata('Öğrenciye yakınlığını yazın (ör. ablası, dedesi).', 'veli_yakinlik')
    else: yak_aciklama = ''
    tc = ''.join(str(veli.get('tc') or '').split())
    if tc:
        from uygulama import eokul
        if eokul.tc_denetle(tc) is None: raise Hata('Kimlik numarası 11 haneli olmalı ve geçerli bir numara olmalı.', 'veli_tc')
    tel = tel_duzelt(veli.get('tel'))
    gunler = gun_duzelt(izin.get('gunler'))
    neden_kodu = izin.get('neden_kodu') if izin.get('neden_kodu') in NEDEN_METIN else 'diger'
    neden = ' '.join(str(izin.get('neden') or '').split())
    if not neden: raise Hata('İzin nedenini yazın.', 'neden')
    try: tarih = _gun(izin.get('tarih') or isgunu.bugun()).isoformat()
    except (ValueError, TypeError): raise Hata('Dilekçe tarihi okunamadı.', 'tarih')
    return {'ogrenci_no': no, 'tarih': tarih, 'veli': {'ad': ad, 'yakinlik': yak, 'yakinlik_aciklama': yak_aciklama, 'tc': tc, 'tel': tel,
                                                        'kayitli': bool(veli.get('kayitli'))},
            'gunler': gunler, 'toplam': toplam(gunler), 'neden_kodu': neden_kodu, 'neden': neden[:200], 'yon': yon(gunler, tarih),
            'devamsizlik': _devamsizlik(izin.get('devamsizlik'))}


def _devamsizlik(d):
    """İsteğe bağlı: dilekçeye yazılacak devamsızlık durumu {'ozurlu': 4.5, 'ozursuz': 2} ya da None."""
    if not isinstance(d, dict): return None
    out = {}
    for k in ('ozurlu', 'ozursuz'):
        v = str(d.get(k) or '').replace(',', '.').strip()
        if not v: continue
        try: out[k] = round(float(v), 1)
        except ValueError: raise Hata('Devamsızlık gün sayısı sayı olmalı (ör. 4,5).', 'devamsizlik')
    return out or None


def tel_duzelt(t):
    """'5321234567' → '0532 123 45 67'; boş → ''. 10 ya da 11 haneli değilse olduğu gibi (yurt dışı numara olabilir)."""
    s = re.sub(r'\D', '', str(t or ''))
    if s.startswith('90') and len(s) == 12: s = s[2:]
    if len(s) == 10: s = '0' + s
    if len(s) == 11 and s[0] == '0': return f'{s[:4]} {s[4:7]} {s[7:9]} {s[9:]}'
    return ' '.join(str(t or '').split())[:20]


def uyarilar(izin, onceki, sinirlar=None):
    """Kaydı engellemeyen uyarılar: aynı güne önceki dilekçe, 5 iş günü geçmiş özür beyanı, devamsızlık sınırı."""
    U = []
    cakisan = sorted({k for o in onceki for k in izin['gunler'] if k in (o.get('gunler') or {})})
    if cakisan: U.append('Bu öğrenci için ' + ', '.join(tarih_uzun(k) for k in cakisan) + ' gününe daha önce dilekçe kaydedilmiş.')
    ilk = min(izin['gunler']); t = izin['tarih']
    if ilk < t and is_gunu_farki(ilk, t) > BEYAN_IS_GUNU:
        U.append(f'{tarih_uzun(ilk)} üzerinden {BEYAN_IS_GUNU} iş gününden çok geçmiş. Yönetmeliğe göre veli beyanı, özür gününü izleyen '
                 f'{BEYAN_IS_GUNU} iş günü içinde verilir (md. 36).')
    d = izin.get('devamsizlik'); s = sinirlar or {}
    if d:
        ozurlu, ozursuz, tpl = d.get('ozurlu', 0), d.get('ozursuz', 0), izin['toplam']
        if s.get('ozursuz') and ozursuz >= s['ozursuz']: U.append(f"Özürsüz devamsızlık {sayi_metni(ozursuz)} gün, sınır {s['ozursuz']} gün.")
        if s.get('toplam'):
            hepsi = ozurlu + ozursuz + tpl
            if hepsi > s['toplam']: U.append(f"Bu izinle birlikte toplam devamsızlık {sayi_metni(hepsi)} güne çıkıyor, sınır {s['toplam']} gün.")
            elif hepsi >= s['toplam'] - 5: U.append(f"Bu izinle birlikte toplam {sayi_metni(hepsi)} gün; {s['toplam']} gün sınırına {sayi_metni(s['toplam'] - hepsi)} gün kaldı.")
    return U
