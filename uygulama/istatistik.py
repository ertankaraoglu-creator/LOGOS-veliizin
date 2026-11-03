"""Yılın sayıları: dilekçeler, izin günleri, sınıflara ve nedenlere göre dağılım, en çok izin alan öğrenciler, aylar, teslim alanlar,
geriye / ileriye dönük, tam / yarım gün; verilen öğrenci belgeleri. Kayda bir şey yazmaz. Sene sonu raporu için tablolar da buradan.
"""
import datetime

from uygulama import izin as IZ, eokul as E, ogrenci as OG

AY_KISA = ('Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara')


def _ay_sirasi(yil):
    """Öğretim yılının ayları Eylül'den Ağustos'a: [('2026-09', 'Eyl 2026'), ...]."""
    y = int(str(yil)[:4]); out = []
    for i in range(12):
        m = (9 + i - 1) % 12 + 1; yy = y if m >= 9 else y + 1
        out.append((f'{yy}-{m:02d}', f'{AY_KISA[m - 1]} {yy}'))
    return out


def hesapla(yil_verisi, yil, bugun=None):
    """yil_verisi: {ogrenciler, siniflar, izinler, belgeler}. Dönüş sayılar ve sıralı listeler (arayüz grafikleri çizer)."""
    L = [i for i in yil_verisi.get('izinler') or [] if not i.get('silindi')]
    O = {o['no']: o for o in yil_verisi.get('ogrenciler') or []}
    S = yil_verisi.get('siniflar') or {}
    bugun = bugun or datetime.date.today(); ay = bugun.strftime('%Y-%m')
    toplam_gun = sum(float(i.get('toplam') or 0) for i in L)
    def ogr(i): return O.get(i['ogrenci_no']) or i.get('ogrenci') or {}
    def sinif_kisa(i):
        o = ogr(i); sk = o.get('sinif') or (i.get('ogrenci') or {}).get('sinif') or ''
        return (S.get(sk) or {}).get('kisa') or sk or '?'
    sinif_gun, neden_say, ogr_gun, ogr_say, ay_say, ay_gun, kim_say = {}, {}, {}, {}, {}, {}, {}
    yon = {'geriye': 0, 'ileriye': 0, 'karisik': 0, 'bugun': 0}; tur = {'tam': 0, 'yarim': 0}
    for i in L:
        g = float(i.get('toplam') or 0); sk = sinif_kisa(i)
        sinif_gun[sk] = sinif_gun.get(sk, 0) + g
        n = IZ.NEDEN_AD.get(i.get('neden_kodu'), 'Diğer'); neden_say[n] = neden_say.get(n, 0) + 1
        k = i['ogrenci_no']; ogr_gun[k] = ogr_gun.get(k, 0) + g; ogr_say[k] = ogr_say.get(k, 0) + 1
        a = (i.get('tarih') or '')[:7]; ay_say[a] = ay_say.get(a, 0) + 1; ay_gun[a] = ay_gun.get(a, 0) + g
        v = i.get('veli') or {}; kim = v.get('yakinlik') or 'Velisi'
        kim_say[kim] = kim_say.get(kim, 0) + 1
        yon[i.get('yon') or IZ.yon(i['gunler'], i['tarih'])] += 1
        for t in (i.get('gunler') or {}).values(): tur['tam' if t == 'tam' else 'yarim'] += 1
    en_cok = sorted(ogr_gun.items(), key=lambda x: (-x[1], str(x[0])))[:10]
    belgeler = [b for b in yil_verisi.get('belgeler') or [] if not b.get('silindi')]
    aylar = _ay_sirasi(yil)
    return {'yil': yil, 'dilekce': len(L), 'gun': toplam_gun, 'ogrenci': len(ogr_say), 'bu_ay': sum(1 for i in L if (i.get('tarih') or '').startswith(ay)),
            'ogrenci_belgesi': len(belgeler), 'ogrenci_belgesi_bu_ay': sum(1 for b in belgeler if (b.get('tarih') or '').startswith(ay)),
            'aktif_ogrenci': sum(1 for o in O.values() if o.get('durum') != 'ayrildi'),
            'siniflar': sorted(sinif_gun.items(), key=lambda x: (-x[1], x[0])),
            'nedenler': sorted(neden_say.items(), key=lambda x: (-x[1], x[0])),
            'en_cok': [{'no': k, 'ad': OG.ad_kisa(O.get(k) or {}) or str(k), 'sinif': (S.get((O.get(k) or {}).get('sinif')) or {}).get('kisa', ''),
                        'gun': g, 'dilekce': ogr_say.get(k, 0)} for k, g in en_cok],
            'aylar': [{'ay': a, 'ad': ad, 'dilekce': ay_say.get(a, 0), 'gun': ay_gun.get(a, 0)} for a, ad in aylar],
            'teslim_alan': sorted(kim_say.items(), key=lambda x: (-x[1], x[0])), 'yon': yon, 'tur': tur,
            'ortalama': round(toplam_gun / len(L), 2) if L else 0}


def csv_metni(yil_verisi, yil):
    """Kayıtların dökümü (Türkçe Excel: ';' ve UTF-8 BOM)."""
    L = [i for i in yil_verisi.get('izinler') or [] if not i.get('silindi')]
    O = {o['no']: o for o in yil_verisi.get('ogrenciler') or []}; S = yil_verisi.get('siniflar') or {}
    satirlar = [['Kayıt no', 'Dilekçe tarihi', 'Okul no', 'Öğrenci', 'Sınıf', 'Dilekçeyi veren', 'Yakınlığı', 'Telefon', 'Neden', 'İzin günleri', 'Gün', 'Yön', 'Özürlü (dilekçe günü)', 'Özürsüz (dilekçe günü)']]
    for i in sorted(L, key=lambda x: x.get('no') or 0):
        o = O.get(i['ogrenci_no']) or i.get('ogrenci') or {}; v = i.get('veli') or {}
        yak = v.get('yakinlik') or ''; yak = yak + (f" ({v.get('yakinlik_aciklama')})" if v.get('yakinlik_aciklama') else '')
        satirlar.append([i.get('no'), IZ.tarih_kisa(i['tarih']), i['ogrenci_no'], o.get('ad', ''), (S.get(o.get('sinif')) or {}).get('kisa') or o.get('sinif', ''),
                         v.get('ad', ''), yak, v.get('tel', ''), i.get('neden', ''), IZ.gunler_listesi(i.get('gunler') or {}), IZ.sayi_metni(i.get('toplam') or 0),
                         {'geriye': 'Özür beyanı', 'ileriye': 'İzin isteği'}.get(i.get('yon'), 'Karışık'),
                         *((IZ.sayi_metni((i.get('devamsizlik') or {}).get(k) or 0) if i.get('devamsizlik') else '') for k in ('ozurlu', 'ozursuz'))])
    def h(c): return '"' + str(c if c is not None else '').replace('"', '""') + '"'
    return '﻿' + '\r\n'.join(';'.join(h(c) for c in r) for r in satirlar)
