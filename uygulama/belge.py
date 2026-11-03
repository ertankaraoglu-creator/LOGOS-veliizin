"""Belgeler (PDF, ReportLab; yazı tipi Liberation Sans): veli izin dilekçesi ve öğrenci belgesi. Yazdırma.

Belgeler bu bilgisayarda ŞİFRESİZ PDF olarak `Belgeler/<yıl>/` klasörüne yazılır (yazdırmak için; LOGOS Disiplin'deki düzen); Ayarlar'dan
silinir. Kasaya PDF yazılmaz. "Kaydet ve yazdır" PDF'i varsayılan yazıcıya gönderir (`yazdir`); gönderilemezse PDF'i açar.

Dilekçe: eski tek dosyalı HTML'deki kağıt düzeni: logo, antet (T.C. / KAYMAKAMLIK ya da VALİLİK / … Müdürlüğüne), sağda tarih, Konu,
dilekçe cümlesi, bilgi tablosu, dilekçeyi verenin imzası, okul idaresinin onay kutusu, altta kayıt no.
Öğrenci belgesi: e-Okul'un "Öğrenci Belgesi" düzeni (Ertan 03.11.2026): antet, ÖĞRENCİ BELGESİ, alanlar, sağda fotoğraf, iki cümle,
müdür yardımcısı ve okul müdürü imzaları.
"""
import base64, datetime, io, os, re, subprocess, sys, time
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from uygulama import eokul as E, izin as IZ, ogrenci as OG, yerel, surum

FONT, FONT_B = 'LiberationSans', 'LiberationSans-Bold'
GRI = colors.HexColor('#6b7280'); CIZGI = colors.HexColor('#9ca3af'); ACIK = colors.HexColor('#f1f1f1')
_hazir = False


class Hata(Exception):
    """Kullanıcıya gösterilecek Türkçe hata (belge yazılamadı)."""


def fontlar():
    global _hazir
    if _hazir: return
    k = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fontlar')
    pdfmetrics.registerFont(TTFont(FONT, os.path.join(k, 'LiberationSans-Regular.ttf')))
    pdfmetrics.registerFont(TTFont(FONT_B, os.path.join(k, 'LiberationSans-Bold.ttf')))
    pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT_B, italic=FONT, boldItalic=FONT_B)
    _hazir = True


def st(boy=11, kalin=False, hiza=TA_LEFT, girinti=0, satir=None, renk=colors.black, once=0, sonra=0):
    return ParagraphStyle('s', fontName=FONT_B if kalin else FONT, fontSize=boy, leading=satir or boy * 1.35, alignment=hiza,
                          firstLineIndent=girinti, textColor=renk, spaceBefore=once, spaceAfter=sonra)


def e(s):
    return escape(str(s or ''))


def antet(okul, hitap=False):
    """['T.C.', 'KONAK KAYMAKAMLIĞI', 'Konak Atatürk Mesleki ve Teknik Anadolu Lisesi Müdürlüğüne'] (hitap) ya da MÜDÜRLÜĞÜ.
    LOGOS Ders Dağıtım ve Disiplin'deki kural: ilçe varsa ve Merkez değilse KAYMAKAMLIĞI, yoksa VALİLİĞİ."""
    il, ilce, ad = (okul.get('il') or '').strip(), (okul.get('ilce') or '').strip(), (okul.get('ad') or '').strip()
    B = E.buyuk
    idari = f'{B(ilce)} KAYMAKAMLIĞI' if ilce and B(ilce) != 'MERKEZ' else (f'{B(il)} VALİLİĞİ' if il else '')
    ad = okul_adi(okul)
    md = (ad + ' Müdürlüğüne') if hitap else (B(ad) + ' MÜDÜRLÜĞÜ')
    return [s for s in ('T.C.', idari, md) if s]


def okul_adi(okul):
    """Okulun adı başlık harfleriyle, 'Müdürlüğü' eki atılmış, 'Ve' küçük: 'Konak Atatürk Mesleki ve Teknik Anadolu Lisesi'."""
    ad = re.sub(r'\s+Müdürlüğü(ne)?$', '', (okul.get('ad') or '').strip(), flags=re.I)
    return re.sub(r'\b(Ve|İle)\b', lambda m: m.group(1).lower() if m.group(1) == 'Ve' else 'ile', E.baslik_harf(ad))


def klasor(yil=None):
    k = os.path.join(yerel.ayar_klasoru(), 'Belgeler')
    return os.path.join(k, str(yil)) if yil else k


def dosya_adi(s):
    return re.sub(r'[\\/:*?"<>|]+', '-', ' '.join(str(s).split()))[:120].strip(' .')


def _foto(o, w_mm, h_mm):
    """Öğrencinin fotoğrafı (data URL) → ReportLab Image; döndürme uygulanır. Yoksa None."""
    d = o.get('foto')
    if not d or ',' not in d: return None
    try:
        from PIL import Image as PI
        im = PI.open(io.BytesIO(base64.b64decode(d.split(',', 1)[1]))).convert('RGB')
        don = int(o.get('foto_donus') or 0) % 360
        if don: im = im.rotate(-don, expand=True)
        b = io.BytesIO(); im.save(b, 'JPEG', quality=88); b.seek(0)
        return Image(b, width=w_mm * mm, height=h_mm * mm)
    except Exception:
        return None


def _kaydet(doc, akis, gecici, yol, alt):
    try:
        doc.build(akis, onFirstPage=alt, onLaterPages=alt)
    except Exception:
        _sil(gecici); raise
    for i in range(20):                                         # Windows: PDF okuyucuda açık dosyanın yerine yazılamaz
        try:
            os.replace(gecici, yol); return
        except PermissionError:
            if i == 19:
                _sil(gecici); raise Hata('Belge yazılamadı: aynı belge şu an bir PDF okuyucuda açık. Onu kapatıp yeniden deneyin.')
            time.sleep(0.1)


def _sil(y):
    try: os.remove(y)
    except OSError: pass


# ------------------------------------------------------------------ veli izin dilekçesi
def dilekce(yol, okul, ayarlar, kayit, ogrenci, sinif, logo=None):
    """kayit: izin.duzelt çıktısı + no (kayıt numarası, 'YYYY-YY/0001'). ogrenci: kasadaki öğrenci. sinif: {sinif, alan, dal, kisa}.
    ayarlar: {dilekce_metin, dilekce_konu, onay_kutusu, onay_ad, onay_unvan, logo_goster, kayit_no_goster}."""
    fontlar(); os.makedirs(os.path.dirname(yol), exist_ok=True)
    gecici = yol + '.yaziliyor'
    doc = SimpleDocTemplate(gecici, pagesize=A4, leftMargin=22 * mm, rightMargin=20 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title='Veli izin dilekçesi', author=surum.AD, subject=okul.get('ad') or '')
    G = A4[0] - 42 * mm
    A = antet(okul, hitap=True)
    ust = [[_logo(logo, ayarlar), Paragraph('<br/>'.join(e(s) for s in A[:-1]), st(12.5, True, TA_CENTER, satir=17)),
            Paragraph(IZ.tarih_uzun(kayit['tarih']), st(11, hiza=TA_RIGHT))]]
    T = Table(ust, colWidths=[30 * mm, G - 70 * mm, 40 * mm])
    T.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                           ('TOPPADDING', (0, 0), (-1, -1), 0)]))
    akis = [T, Paragraph(e(A[-1]), st(12.5, True, TA_CENTER)), Spacer(1, 10 * mm)]
    akis.append(Paragraph(f"<b>Konu:</b> {e(ayarlar.get('dilekce_konu') or IZ.VARSAYILAN_KONU)}", st(12)))
    akis.append(Spacer(1, 6 * mm))
    # dilekçe cümlesi: tarih ve toplam kalın
    metin = e(IZ.metin(ayarlar.get('dilekce_metin') or IZ.VARSAYILAN_METIN, kayit, {'ad': ogrenci['ad'], 'sinif': sinif.get('sinif', ''), 'no': ogrenci['no']}))
    for parca in (IZ.tarihler_cumlesi(kayit['gunler']), IZ.toplam_metni(kayit['toplam'])):
        if parca: metin = metin.replace(e(parca), f'<b>{e(parca)}</b>', 1)
    akis.append(Paragraph(metin, st(12, hiza=TA_JUSTIFY, girinti=12.5 * mm, satir=18)))
    akis.append(Spacer(1, 8 * mm))
    # bilgi tablosu
    v = kayit['veli']; yak = IZ.yakinlik_metni(v.get('yakinlik'), v.get('yakinlik_aciklama'))
    alan_dal = sinif.get('alan', '') + (f" / {sinif.get('dal')}" if sinif.get('dal') else '')
    satirlar = [[('k', 'Adı soyadı'), ('v', ogrenci['ad']), ('k', 'Okul no'), ('v', str(ogrenci['no']))],
                [('k', 'Sınıfı'), ('v', sinif.get('sinif', '')), ('k', 'Alanı'), ('v', E.baslik_harf(alan_dal) if alan_dal else '-')],
                [('k', 'Baba adı'), ('v', ogrenci.get('baba') or '-'), ('k', 'Anne adı'), ('v', ogrenci.get('anne') or '-')],
                [('k', 'İzin günleri'), ('v3', IZ.gunler_listesi(kayit['gunler']) + (f". Toplam <b>{IZ.gun_sayisi_metni(kayit['toplam'])}</b>" if len(IZ.gruplar(kayit['gunler'])) > 1 else ''))]]
    d = kayit.get('devamsizlik')
    if d:
        satirlar.append([('k', 'Devamsızlık durumu'), ('v3', f"Bugüne kadar {IZ.sayi_metni(d.get('ozurlu', 0))} gün özürlü, {IZ.sayi_metni(d.get('ozursuz', 0))} gün özürsüz devamsızlığı vardır.")])
    veren = f"{e(v['ad'])} (öğrencinin {e(yak)})"
    if v.get('tc'): veren += f", T.C. kimlik no {e(v['tc'])}"
    if v.get('tel'): veren += f", tel. {e(v['tel'])}"
    satirlar.append([('k', 'Dilekçeyi veren'), ('v3', veren)])
    H, sty = [], [('GRID', (0, 0), (-1, -1), 0.6, colors.HexColor('#555555')), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                  ('LEFTPADDING', (0, 0), (-1, -1), 2.6 * mm), ('RIGHTPADDING', (0, 0), (-1, -1), 2.6 * mm),
                  ('TOPPADDING', (0, 0), (-1, -1), 1.6 * mm), ('BOTTOMPADDING', (0, 0), (-1, -1), 1.6 * mm)]
    for i, r in enumerate(satirlar):
        row = []
        for j, (t, x) in enumerate(r):
            if t == 'k':
                row.append(Paragraph(e(x), st(11, True, satir=14))); sty.append(('BACKGROUND', (j, i), (j, i), ACIK))
            else: row.append(Paragraph(x if t == 'v3' and ('<b>' in x or '&' in x) else (x if t == 'v3' else e(x)), st(11, satir=14)))
        if len(r) == 2: sty.append(('SPAN', (1, i), (3, i)))
        while len(row) < 4: row.append('')
        H.append(row)
    T = Table(H, colWidths=[G * .27, G * .33, G * .17, G * .23]); T.setStyle(TableStyle(sty))
    akis += [T, Spacer(1, 12 * mm)]
    # imza
    tel = Paragraph(f"Telefon: {e(v['tel'])}" if v.get('tel') else '', st(11))
    imza = Table([[Paragraph('İmza', st(9, renk=GRI))], [Paragraph(f"<b>{e(v['ad'])}</b>", st(11.5, hiza=TA_CENTER))],
                  [Paragraph(f'Öğrencinin {e(yak)}', st(11, hiza=TA_CENTER))]], colWidths=[64 * mm])
    imza.setStyle(TableStyle([('LINEBELOW', (0, 0), (0, 0), 0.7, colors.black), ('BOTTOMPADDING', (0, 0), (0, 0), 14 * mm),
                              ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 1), (-1, -1), 1)]))
    T = Table([[tel, imza]], colWidths=[G - 64 * mm, 64 * mm]); T.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'BOTTOM'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
    akis.append(T)
    if ayarlar.get('onay_kutusu', True):
        sol = [Paragraph('<b>Okul idaresi</b>', st(11)), Paragraph('Öğrencinin yukarıda belirtilen günlerde izinli sayılması uygundur.', st(10.5, satir=14)),
               Spacer(1, 4 * mm), Paragraph('Tarih: ...... / ...... / 20......', st(10.5))]
        sag = [Spacer(1, 13 * mm), Paragraph(e(ayarlar.get('onay_ad') or '') or '&nbsp;', st(11, True, TA_CENTER)), Paragraph(e(ayarlar.get('onay_unvan') or 'Müdür Yardımcısı'), st(10.5, hiza=TA_CENTER))]
        T = Table([[sol, sag]], colWidths=[G - 62 * mm, 62 * mm])
        T.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 0.7, colors.HexColor('#555555')), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('TOPPADDING', (0, 0), (-1, -1), 3.5 * mm), ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5 * mm), ('LEFTPADDING', (0, 0), (-1, -1), 4 * mm), ('RIGHTPADDING', (0, 0), (-1, -1), 4 * mm)]))
        akis += [Spacer(1, 12 * mm), KeepTogether([T])]
    kayit_no = kayit.get('no_metni') if ayarlar.get('kayit_no_goster', True) else ''

    def alt(c, d):
        c.saveState(); c.setFont(FONT, 7.5); c.setFillColor(GRI)
        if kayit_no: c.drawString(22 * mm, 9 * mm, f'Kayıt no: {kayit_no}')
        c.drawRightString(A4[0] - 20 * mm, 9 * mm, f'{surum.AD} · {time.strftime("%d.%m.%Y %H:%M")}'); c.restoreState()
    _kaydet(doc, akis, gecici, yol, alt)
    return yol


def _logo(logo, ayarlar):
    if not logo or not ayarlar.get('logo_goster', True): return ''
    try:
        b = io.BytesIO(base64.b64decode(logo.split(',', 1)[1])); return Image(b, width=20 * mm, height=20 * mm, kind='proportional')
    except Exception:
        return ''


# ------------------------------------------------------------------ öğrenci belgesi
def ogrenci_belgesi(yol, okul, ayarlar, ogrenci, sinif, tarih, kisi=None):
    """e-Okul'un Öğrenci Belgesi düzeni. kisi: alanları elle tamamlanmış kopya (tc, dogum_yeri, burslu, dal...). ayarlar:
    {belge_mudur, belge_mudur_yrd, belge_burslu ('- / -'), belge_metin}."""
    fontlar(); os.makedirs(os.path.dirname(yol), exist_ok=True)
    o = dict(ogrenci, **(kisi or {})); gecici = yol + '.yaziliyor'
    doc = SimpleDocTemplate(gecici, pagesize=A4, leftMargin=22 * mm, rightMargin=20 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title='Öğrenci belgesi', author=surum.AD, subject=okul.get('ad') or '')
    G = A4[0] - 42 * mm
    okul_kisa = okul_adi(okul); il = E.buyuk(okul.get('il') or '')
    satir2 = f'{il} VALİLİĞİ' if il else ''
    satir3 = (f"{E.baslik_harf(okul['ilce'])} / " if okul.get('ilce') else '') + f'{okul_kisa} Müdürlüğü'
    akis = [Paragraph('<br/>'.join(f'<b>{e(x)}</b>' for x in ('T.C.', satir2, satir3) if x), st(11, hiza=TA_CENTER, satir=15)),
            Spacer(1, 18 * mm), Paragraph('<b>ÖĞRENCİ BELGESİ</b>', st(12.5, hiza=TA_CENTER)), Spacer(1, 12 * mm)]
    okul_ad = E.buyuk(okul_kisa)
    if sinif.get('program_ad'): okul_ad += f" ({sinif['program_ad']})"
    alan_dal = sinif.get('alan', '')
    if o.get('dal') or sinif.get('dal'): alan_dal += f" ALANI / {E.baslik_harf(o.get('dal') or sinif.get('dal'))}"
    elif alan_dal: alan_dal += ' ALANI'
    sinif_metni = f"{sinif.get('program') + ' - ' if sinif.get('program') else ''}{sinif.get('seviye', '')}. Sınıf / {sinif.get('sube', '')} Şubesi" if sinif.get('seviye') else sinif.get('sinif', '')
    alanlar = [('Öğrencinin Adı Soyadı', o['ad']), ('T.C. Kimlik Numarası', o.get('tc') or ''), ('Baba Adı', o.get('baba') or ''),
               ('Anne Adı', o.get('anne') or ''), ('Doğum Yeri', o.get('dogum_yeri') or ''), ('Doğum Tarihi', IZ.tarih_kisa(o['dogum']).replace('.', '/') if o.get('dogum') else ''),
               ('Okulu', okul_ad), ('Alanı/Dalı', alan_dal or '-'), ('Sınıfı', sinif_metni), ('Numarası', str(o['no'])),
               ('Öğrenci Belgesinin Alındığı Tarih', IZ.tarih_kisa(tarih).replace('.', '/')), ('Burslu / Yatılı', o.get('burslu') or ayarlar.get('belge_burslu') or '- / -')]
    V = [[Paragraph(e(k), st(9.5, satir=13)), Paragraph(': ' + (e(v) if v else '<font color="#9ca3af">…………………</font>'), st(9.5, satir=13))] for k, v in alanlar]
    T = Table(V, colWidths=[54 * mm, G - 54 * mm - 48 * mm])
    T.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 2.2 * mm), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.2 * mm)]))
    foto = _foto(o, 36, 46) or Table([['']], colWidths=[36 * mm], rowHeights=[46 * mm], style=[('BOX', (0, 0), (-1, -1), 0.4, CIZGI)])
    D = Table([[T, foto]], colWidths=[G - 48 * mm, 48 * mm])
    D.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    akis += [D, Spacer(1, 16 * mm)]
    cocuk = 'kızı' if o.get('cinsiyet') == 'K' else ('oğlu' if o.get('cinsiyet') == 'E' else 'çocuğu')
    kalip = ayarlar.get('belge_metin') or 'Yukarıda açık kimliği yazılı {BABA} {COCUK} {OGRENCI} okulumuzun devamlı öğrencisidir.'
    c1 = kalip.replace('{BABA}', o.get('baba') or '…………').replace('{COCUK}', cocuk).replace('{OGRENCI}', o['ad'])
    akis += [Paragraph(e(c1), st(10.5, satir=15)), Spacer(1, 4 * mm),
             Paragraph(e(ayarlar.get('belge_metin2') or 'Bu belge öğrencinin isteği üzerine düzenlenerek kendisine verilmiştir.'), st(10.5, satir=15)), Spacer(1, 26 * mm)]
    imz = Table([[Paragraph(f"{e(E.buyuk(ayarlar.get('belge_mudur_yrd') or ''))}<br/>MÜDÜR YARDIMCISI", st(10, hiza=TA_CENTER, satir=14)),
                  Paragraph(f"{e(E.buyuk(ayarlar.get('belge_mudur') or ''))}<br/>OKUL MÜDÜRÜ", st(10, hiza=TA_CENTER, satir=14))]], colWidths=[G / 2, G / 2])
    akis.append(KeepTogether([imz]))

    def alt(c, d):                                              # resmî belge: altında program adı yazmaz (Ertan 03.11.2026)
        pass
    _kaydet(doc, akis, gecici, yol, alt)
    return yol


# ------------------------------------------------------------------ yazdırma ve açma
def yazdir(yol):
    """PDF'i varsayılan yazıcıya gönderir. Dönüş: 'yazici' (gönderildi), 'acildi' (gönderilemedi, PDF açıldı) ya da Hata.
    Sınamada (LV_SINAMA) hiçbir program açılmaz."""
    if os.environ.get('LV_SINAMA'): return 'sinama'
    if sys.platform == 'win32':
        try:
            os.startfile(yol, 'print'); return 'yazici'                     # ilişkili programın "Yazdır" eylemi (Adobe, Edge çoğu kurulumda)
        except OSError:
            ac(yol); return 'acildi'
    if sys.platform == 'darwin' or sys.platform.startswith('linux'):
        try:
            subprocess.run(['lp', yol], check=True, capture_output=True, timeout=20); return 'yazici'
        except Exception:
            ac(yol); return 'acildi'
    ac(yol); return 'acildi'


def ac(yol):
    if os.environ.get('LV_SINAMA'): return
    try:
        if sys.platform == 'win32': os.startfile(yol)
        elif sys.platform == 'darwin': subprocess.Popen(['open', yol])
        else: subprocess.Popen(['xdg-open', yol])
    except Exception:
        raise Hata('Belge açılamadı: ' + os.path.basename(yol))


def belgeleri_sil(yil=None):
    """Belgeler klasörünü boşaltır (yıl verilirse yalnız o yıl); silinen dosya sayısı."""
    import shutil
    k = klasor(yil); n = 0
    if os.path.isdir(k):
        for kok, _, dosyalar in os.walk(k): n += len(dosyalar)
        shutil.rmtree(k, ignore_errors=True)
    return n
