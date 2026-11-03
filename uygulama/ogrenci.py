"""Öğrenci listesi: arama, veli adayları, elle ekleme ve düzeltme denetimi.

Kasadaki öğrenci (uygulama/eokul.py birlestir): {no, ad, baba, anne, dogum (ISO), dogum_yeri, cinsiyet 'K'|'E', velisi_kim, veli,
sinif (şube anahtarı: '9/A SAĞLIK HİZMETLERİ'), durum aktif|ayrildi, kaynak eokul|elle, tc, foto (data URL)|None, foto_donus 0|90|180|270,
veli_elle {ad, yakinlik, tel}|None, dal?, not_, ekleme, guncelleme}.
"""
import datetime, re, unicodedata

from uygulama import eokul as E

TR = str.maketrans('çğıöşüâîû', 'cgiosuaiu')
CINSIYET = {'K': 'Kız', 'E': 'Erkek'}


class Hata(Exception):
    def __init__(self, ileti, alan=None):
        super().__init__(ileti); self.alan = alan


def norm(s):
    """Arama anahtarı: Türkçe harfsiz küçük harf ('ÖZTÜRK' → 'ozturk'); "ozturk" yazınca ÖZTÜRK bulunsun."""
    return ' '.join(E.kucuk(unicodedata.normalize('NFC', str(s or ''))).translate(TR).split())


def soyad(o):
    return (o.get('ad') or '').split(' ')[-1] if o.get('ad') else ''


def ad_kisa(o):
    """'AYŞE MELEK ERSUBAŞI' → 'Ayşe Melek Ersubaşı'."""
    return E.baslik_harf(o.get('ad', ''))


def ara(ogrenciler, sorgu, en_cok=12, siniflar=None):
    """Ad, soyad ya da okul numarasıyla arama; puanlı. Yalnız aktif öğrenciler. Numara tam eşleşmesi en üstte."""
    toks = norm(sorgu).split()
    if not toks: return []
    out = []
    for o in ogrenciler:
        if o.get('durum') == 'ayrildi': continue
        n = norm(o['ad']); kelimeler = n.split(); puan = 0; ok = True
        for t in toks:
            if t.isdigit():
                no = str(o['no'])
                if no == t: puan += 100
                elif no.startswith(t): puan += 40
                else: ok = False; break
            elif any(k.startswith(t) for k in kelimeler): puan += 20 + (5 if kelimeler and kelimeler[0].startswith(t) else 0)
            elif len(t) >= 2 and t in n: puan += 8
            else: ok = False; break
        if ok: out.append((puan, o))
    out.sort(key=lambda x: (-x[0], x[1]['ad']))
    return [o for _, o in out[:en_cok]]


def veli_adaylari(o):
    """Dilekçeyi imzalayacak kişi için çipler: e-Okul'daki kayıtlı veli, sonra anne ve baba (soyadı öğrencininki varsayılır),
    sonra elle girilmiş veli. [{ad, yakinlik, kayitli, tel}]"""
    s = soyad(o); L = []
    def ekle(ad, yak, kayitli=False, tel=''):
        ad = ' '.join(str(ad or '').split())
        if ad and not any(E.anahtar(x['ad']) == E.anahtar(ad) for x in L): L.append({'ad': ad, 'yakinlik': yak, 'kayitli': kayitli, 'tel': tel})
    if o.get('veli'):
        yak = o.get('velisi_kim') or 'Velisi'
        ekle(o['veli'], yak if yak in ('Anne', 'Baba', 'Vasi') else ('Vasi' if 'vasi' in E.kucuk(yak) else 'Diğer'), True)
    var = {x['yakinlik'] for x in L}                      # kayıtlı veli anneyse türetilmiş "anne + öğrencinin soyadı" eklenmez
    if o.get('anne') and 'Anne' not in var: ekle(f"{o['anne']} {s}", 'Anne')
    if o.get('baba') and 'Baba' not in var: ekle(f"{o['baba']} {s}", 'Baba')
    ve = o.get('veli_elle')
    if ve and ve.get('ad'): ekle(ve['ad'], ve.get('yakinlik') or 'Diğer', False, ve.get('tel') or '')
    return L


def duzelt(g, mevcut=None, siniflar=None):
    """Elle eklenen ya da düzeltilen öğrenci: denetler, kasaya yazılacak alanları döner (ötekilere dokunmaz)."""
    if not isinstance(g, dict): raise Hata('Öğrenci bilgisi eksik.')
    ad = E.buyuk(' '.join(str(g.get('ad') or '').split()))
    if len(ad.split()) < 2: raise Hata('Adı ve soyadı birlikte yazın.', 'ad')
    try: no = int(str(g.get('no')).strip())
    except (TypeError, ValueError): raise Hata('Okul numarası sayı olmalı.', 'no')
    if no <= 0: raise Hata('Okul numarası sayı olmalı.', 'no')
    eski = str(g.get('eski_no')) if g.get('eski_no') not in (None, '') else None      # düzeltmede öğrencinin kendi numarası çakışma değil
    for o in mevcut or []:
        if str(o.get('no')) == str(no) and str(o.get('no')) != eski: raise Hata(f"{no} numarası {o['ad']} adlı öğrencide kayıtlı.", 'no')
    tc = E.tc_denetle(g.get('tc'))
    if tc is None: raise Hata('T.C. kimlik numarası 11 haneli ve geçerli olmalı (boş bırakılabilir).', 'tc')
    dogum = None
    if str(g.get('dogum') or '').strip():
        try: dogum = datetime.date.fromisoformat(str(g['dogum'])[:10]).isoformat()
        except ValueError: raise Hata('Doğum tarihi okunamadı.', 'dogum')
    cins = str(g.get('cinsiyet') or '').strip().upper()[:1]
    if cins and cins not in CINSIYET: raise Hata('Cinsiyet K ya da E olmalı.', 'cinsiyet')
    sinif = str(g.get('sinif') or '').strip()
    if siniflar is not None and sinif and sinif not in siniflar: raise Hata('Sınıf listede yok; önce sınıfı e-Okul listesinden aktarın ya da Ayarlar\'dan ekleyin.', 'sinif')
    if not sinif: raise Hata('Sınıfını seçin.', 'sinif')
    out = {'no': no, 'ad': ad, 'tc': tc, 'baba': E.buyuk(' '.join(str(g.get('baba') or '').split()))[:60],
           'anne': E.buyuk(' '.join(str(g.get('anne') or '').split()))[:60], 'dogum': dogum,
           'dogum_yeri': E.buyuk(' '.join(str(g.get('dogum_yeri') or '').split()))[:60], 'cinsiyet': cins, 'sinif': sinif,
           'dal': ' '.join(str(g.get('dal') or '').split())[:80], 'velisi_kim': ' '.join(str(g.get('velisi_kim') or '').split())[:30],
           'veli': E.buyuk(' '.join(str(g.get('veli') or '').split()))[:80], 'not_': ' '.join(str(g.get('not_') or '').split())[:200]}
    ve = g.get('veli_elle')
    if isinstance(ve, dict) and ' '.join(str(ve.get('ad') or '').split()):
        from uygulama import izin
        out['veli_elle'] = {'ad': ' '.join(str(ve.get('ad')).split())[:80], 'yakinlik': str(ve.get('yakinlik') or 'Diğer')[:30],
                            'tel': izin.tel_duzelt(ve.get('tel'))}
    else: out['veli_elle'] = None
    return out


def yas(o, bugun=None):
    if not o.get('dogum'): return None
    d = datetime.date.fromisoformat(o['dogum']); b = bugun or datetime.date.today()
    return b.year - d.year - ((b.month, b.day) < (d.month, d.day))


def sinif_sirasi(anahtar):
    """'10/B HASTA VE YAŞLI HİZMETLERİ' → (10, 'B', alan) sıralama için."""
    m = re.match(r'^(\d+)/(\S+)\s*(.*)$', anahtar or '')
    return (int(m.group(1)), m.group(2), m.group(3)) if m else (99, anahtar or '', '')
