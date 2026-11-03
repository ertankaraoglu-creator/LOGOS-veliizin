"""Sınamalar için uydurma e-Okul raporları (gerçek PDF depoya girmez; CLAUDE.md "Veri ve güvenlik").

Gerçek "Genel Öğrenci Listesi"nin düzenini taklit eder (uygulama/eokul.py'nin okuduğu kadarıyla): başlıkta okul ve sınıf satırı,
sayfada dört öğrenci bloğu, her blok çerçeveli, solda fotoğraf yeri, altında ad soyad ve okul no, sağda iki sütun "Etiket : değer".
Kimlik bilgili liste de üretilir (T.C. kimlik no için). Okul, öğrenci, veli adları uydurmadır.

Kullanım: python -m sinama.eokul_ornek <klasör>   → 9A, 10B ve kimlik PDF'leri yazılır.
"""
import os, random, sys

OKUL = {'il': 'İzmir', 'ilce': 'Konak', 'ad': 'Çınar Mesleki Ve Teknik Anadolu Lisesi'}
ADLAR_K = ['AYŞE', 'ELİF', 'ZEYNEP', 'DEFNE', 'NEHİR', 'ECRİN', 'AZRA', 'MİRAY', 'EYLÜL', 'DUYGU', 'İREM', 'BUSE', 'NİSA', 'SUDE', 'ÖYKÜ', 'ÇİĞDEM']
ADLAR_E = ['AHMET', 'MEHMET', 'YUSUF', 'EMİR', 'KEREM', 'ARDA', 'ÇINAR', 'EGE', 'ÖMER', 'BERAT', 'UMUT', 'KAAN', 'ŞAHİN', 'İLKER', 'POYRAZ', 'TUNA']
SOYADLAR = ['YILMAZ', 'DEMİR', 'ÇELİK', 'ŞAHİN', 'ÖZTÜRK', 'AYDIN', 'KAYA', 'YILDIRIM', 'ARSLAN', 'DOĞAN', 'KILIÇ', 'ÇETİN', 'KURT', 'KOÇ', 'ÖZDEMİR',
            'ERSOY', 'GÜNEŞ', 'ACAR', 'İNCE', 'BULUT']
BABA = ['HASAN', 'HÜSEYİN', 'ALİ', 'MUSTAFA', 'İBRAHİM', 'OSMAN', 'RAMAZAN', 'HALİL', 'MURAT', 'SERKAN']
ANNE = ['FATMA', 'AYŞE', 'EMİNE', 'HATİCE', 'ZEYNEP', 'SEVİM', 'GÜLSÜM', 'NURAY', 'FİLİZ', 'SONGÜL']
YERLER = ['İZMİR', 'MANİSA', 'AYDIN', 'DENİZLİ', 'KONYA', 'VAN', 'DİYARBAKIR']

SINIFLAR = {'9A': {'baslik': 'AMP - 9. Sınıf / A Şubesi SAĞLIK HİZMETLERİ ALANI 2026-2027 I. Dönem', 'bas_no': 901},
            '10B': {'baslik': 'AMP - 10. Sınıf / B Şubesi HASTA VE YAŞLI HİZMETLERİ ALANI 2026-2027 I. Dönem', 'bas_no': 1001},
            'AL': {'baslik': '11. Sınıf / C Şubesi 2026-2027 I. Dönem', 'bas_no': 1101}}


def tc_uret(r):
    """Geçerli (denetim kuralına uyan) uydurma T.C. kimlik numarası."""
    d = [r.randint(1, 9)] + [r.randint(0, 9) for _ in range(8)]
    d.append((7 * sum(d[0:9:2]) - sum(d[1:8:2])) % 10)
    d.append(sum(d[:10]) % 10)
    return ''.join(map(str, d))


def ogrenciler(sinif, n=10, tohum=1):
    """Deterministik uydurma öğrenci listesi: [{no, ad, baba, anne, dogum 'gg/aa/yyyy', dogum_yeri, cinsiyet, velisi_kim, veli, tc}]."""
    r = random.Random(f'{sinif}-{tohum}'); bas = SINIFLAR[sinif]['bas_no']; out = []
    for i in range(n):
        kiz = r.random() < 0.55; ad = r.choice(ADLAR_K if kiz else ADLAR_E); soy = r.choice(SOYADLAR)
        if r.random() < 0.25: ad += ' ' + r.choice(ADLAR_K if kiz else ADLAR_E)       # göbek adı
        baba = r.choice(BABA); anne = r.choice(ANNE)
        velisi = r.choice(['Anne', 'Baba', 'Baba', 'Anne', 'Vasi', ''])
        if velisi == 'Anne': veli = f'{anne} {r.choice([soy, r.choice(SOYADLAR)])}'         # bazen başka soyadı (boşanmış veli)
        elif velisi == 'Baba': veli = f'{baba} {soy}'
        elif velisi == 'Vasi': veli = f'{r.choice(BABA)} {r.choice(SOYADLAR)}'
        else: veli = ''
        seviye = int(''.join(c for c in sinif if c.isdigit()) or 11)           # 9A → 9; AL → 11
        yil = 2026 - (seviye + 5) - r.randint(0, 1)
        out.append({'no': bas + i, 'ad': f'{ad} {soy}', 'baba': baba, 'anne': anne, 'dogum': f'{r.randint(1, 28):02d}/{r.randint(1, 12):02d}/{yil}',
                    'dogum_yeri': r.choice(YERLER), 'cinsiyet': 'Kız' if kiz else 'Erkek', 'velisi_kim': velisi, 'veli': veli, 'tc': tc_uret(r)})
    return out


def _font():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    k = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uygulama', 'fontlar')
    if 'LS' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('LS', os.path.join(k, 'LiberationSans-Regular.ttf')))
        pdfmetrics.registerFont(TTFont('LSB', os.path.join(k, 'LiberationSans-Bold.ttf')))


def _foto_resmi(r):
    """Renkli uydurma vesikalık (fotoğraf okuma sınaması için; boş fotoğraf yeri beyaz kalır)."""
    import io
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (120, 155), (r.randint(120, 220), r.randint(120, 220), r.randint(160, 240)))
    d = ImageDraw.Draw(im); d.ellipse((35, 25, 85, 80), fill=(235, 200, 170)); d.rectangle((25, 95, 95, 155), fill=(60, 80, 140))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=80); b.seek(0); return b


def genel_liste(yol, sinif, n=10, fotograf=True, tohum=1, okul=None, bos_foto=()):
    """Genel Öğrenci Listesi PDF'i (uygulama/eokul.py genel_oku'nun beklediği düzen). bos_foto: fotoğrafı boş kalacak numaralar."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from uygulama import eokul as E
    _font(); okul = okul or OKUL; L = ogrenciler(sinif, n, tohum); r = random.Random(f'foto-{sinif}-{tohum}')
    c = canvas.Canvas(yol, pagesize=(595.3, 841.9)); H = 841.9
    def y(t): return H - t                                   # sayfa üstünden pt → ReportLab
    for sayfa in range(0, len(L), 4):
        c.setFont('LSB', 10); c.drawCentredString(297, y(30), 'T.C.'); c.drawCentredString(297, y(42), f"{E.buyuk(okul['il'])} VALİLİĞİ")
        c.drawCentredString(297, y(54), f"{okul['ilce']} / {okul['ad']} Müdürlüğü")
        c.setFont('LS', 9); c.drawCentredString(297, y(68), 'Genel Öğrenci Listesi'); c.drawCentredString(297, y(80), SINIFLAR[sinif]['baslik'])
        ust = 100.0
        for o in L[sayfa:sayfa + 4]:
            c.setLineWidth(.6); c.rect(25, y(ust + 155), 540, 155)
            if fotograf and o['no'] not in bos_foto:
                c.drawImage(ImageReader(_foto_resmi(r)), E.FOTO_X0, y(ust + E.FOTO_UST + E.FOTO_BOY), E.FOTO_X1 - E.FOTO_X0, E.FOTO_BOY)
            c.setFont('LSB', 8)
            parcalar = o['ad'].split(' ')                     # uzun ad iki satıra bölünür (gerçek rapor gibi)
            c.drawString(31, y(ust + 140), ' '.join(parcalar[:-1])); c.drawString(31, y(ust + 149), parcalar[-1])
            c.setFont('LS', 8); c.drawString(31, y(ust + 158 - 3), str(o['no']))
            sol = [('Baba Adı', o['baba']), ('Doğum Tarihi', o['dogum']), ('Cinsiyeti', o['cinsiyet']), ('Velisi Kim', o['velisi_kim']),
                   ('Kiminle Oturuyor', 'Ailesiyle'), ('Ev Kira mı?', 'Hayır'), ('Sürekli Hastalık', '')]
            sag = [('Anne Adı', o['anne']), ('Doğum Yeri', o['dogum_yeri']), ('Veli Adı Soyadı', o['veli']), ('Aile Gelir Durumu', 'Orta'),
                   ('Çalışıyor mu?', 'Hayır'), ('Ev Nasıl Isınıyor', 'Doğalgaz'), ('Okula Geliş', 'Yürüyerek')]
            for i, ((e1, v1), (e2, v2)) in enumerate(zip(sol, sag)):
                t = ust + 14 + i * 14
                c.drawString(140, y(t), f'{e1} : {v1}'); c.drawString(360, y(t), f'{e2} : {v2}')
            ust += 165
        c.setFont('LS', 7); c.drawString(25, y(820), '03/11/2026 09:30'); c.showPage()
    c.save(); return L


def kimlik_listesi(yol, siniflar=('9A', '10B'), n=10, tohum=1):
    """Fotoğraflı-Kimlik Bilgili Öğrenci Listesi: her öğrenci için etiket satırları (T.C. kimlik no buradan)."""
    from reportlab.pdfgen import canvas
    _font(); c = canvas.Canvas(yol, pagesize=(595.3, 841.9)); H = 841.9; t = 60; L = []
    c.setFont('LSB', 10); c.drawCentredString(297, H - 30, 'Fotoğraflı-Kimlik Bilgili Öğrenci Listesi'); c.setFont('LS', 8)
    for s in siniflar:
        for o in ogrenciler(s, n, tohum):
            L.append(o)
            satirlar = [('Öğrenci Numarası', o['no']), ('T.C. Kimlik No', o['tc']), ('Sınıfı/Şubesi', s), ('Adı Soyadı', o['ad']),
                        ('Baba Adı', o['baba']), ('Anne Adı', o['anne']), ('Cinsiyeti', o['cinsiyet']), ('Doğum Tarihi', o['dogum'])]
            if t > 760: c.showPage(); c.setFont('LS', 8); t = 40
            for e, v in satirlar:
                c.drawString(150, H - t, f'{e} : {v}'); t += 10
            t += 8
    c.showPage(); c.save(); return L


def uret(klasor, fotograf=True):
    """Sınamaların kullandığı takım: 9A (10 öğrenci), 10B (8), AL 11C (6), kimlik listesi (9A + 10B)."""
    os.makedirs(klasor, exist_ok=True)
    a = os.path.join(klasor, '9a.pdf'); b = os.path.join(klasor, '10b.pdf'); c = os.path.join(klasor, '11c.pdf'); k = os.path.join(klasor, 'kimlik.pdf')
    genel_liste(a, '9A', 10, fotograf, bos_foto=(905,)); genel_liste(b, '10B', 8, fotograf); genel_liste(c, 'AL', 6, fotograf)
    kimlik_listesi(k, ('9A', '10B'))
    return {'9A': a, '10B': b, 'AL': c, 'kimlik': k}


if __name__ == '__main__':
    print(uret(sys.argv[1] if len(sys.argv) > 1 else 'ornek'))
