"""Bu bilgisayara ait ayarlar ve kasanın varsayılan yeri (LOGOS Disiplin'deki gibi).

Kasa varsayılan olarak bulut eşitlemesine girmeyen uygulama klasöründe durur: Windows'ta Belgeler çoğu zaman OneDrive'a
eşitlenir, oraya koymak "veri okuldan çıkmaz" sözünü bozardı. Kullanıcı isterse başka bir yer seçer (ör. USB).
  Windows: %LOCALAPPDATA%\\LOGOS Veli İzin      Mac: ~/Library/Application Support/LOGOS Veli İzin      Linux: ~/.local/share/logos-veli-izin
Sınamalar LV_AYAR_KLASORU ile kendi geçici klasörlerini verir.
"""
import json, os, sys, time

KASA_ADI = 'Veli İzin Kasası.lvk'


def ayar_klasoru():
    y = os.environ.get('LV_AYAR_KLASORU')
    if not y:
        if sys.platform.startswith('win'):
            y = os.path.join(os.environ.get('LOCALAPPDATA') or os.path.expanduser('~\\AppData\\Local'), 'LOGOS Veli İzin')
        elif sys.platform == 'darwin':
            y = os.path.expanduser('~/Library/Application Support/LOGOS Veli İzin')
        else:
            y = os.path.join(os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share'), 'logos-veli-izin')
    os.makedirs(y, exist_ok=True)
    return y


def varsayilan_kasa_yolu():
    return os.path.join(ayar_klasoru(), 'Kasa', KASA_ADI)


def _yol():
    return os.path.join(ayar_klasoru(), 'ayarlar.json')


def oku():
    try:
        with open(_yol(), encoding='utf-8') as f: d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def yaz(**degisen):
    d = oku(); d.update(degisen)
    gecici = _yol() + '.yaziliyor'
    with open(gecici, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(gecici, _yol())
    return d


def son_kasa():
    """Son açılan kasanın yolu; yoksa ya da dosya silinmişse varsayılan yer."""
    y = oku().get('son_kasa')
    return y if y and os.path.exists(y) else varsayilan_kasa_yolu()


def kayip_kasa():
    """Hatırlanan kasa artık yerinde değilse (USB çıkarıldı, ağ sürücüsü bağlı değil) onun yolu; yoksa None."""
    y = oku().get('son_kasa')
    return y if y and not os.path.exists(y) and os.path.abspath(y) != os.path.abspath(varsayilan_kasa_yolu()) else None


GUNLUK = 'gunluk.txt'
GUNLUK_EN_COK = 1024 * 1024


def gunluk(*s):
    """Destek için olay günlüğü (bu bilgisayarın ayar klasöründe). Şifre, kurtarma anahtarı, öğrenci ve veli bilgisi YAZILMAZ:
    yalnız ne olduğu (açıldı, kilitlendi, hata). 1 MB'ı geçince bir öncekinin yerine geçer (gunluk.1.txt)."""
    try:
        y = os.path.join(ayar_klasoru(), GUNLUK)
        if os.path.exists(y) and os.path.getsize(y) > GUNLUK_EN_COK: os.replace(y, y.replace('.txt', '.1.txt'))
        with open(y, 'a', encoding='utf-8') as f: f.write(time.strftime('[%Y-%m-%d %H:%M:%S] ') + ' '.join(str(x) for x in s) + '\n')
    except OSError:
        pass
