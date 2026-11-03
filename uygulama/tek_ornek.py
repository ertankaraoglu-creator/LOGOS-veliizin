"""LOGOS Veli İzin'in tek örneği (LOGOS A81'den). Windows'ta tek dosyalı paket birkaç saniyede açılır; kullanıcı "açılmadı" sanıp
bir kez daha çift tıklarsa iki pencere aynı kasayı yazardı (biri ötekinin kaydını ezer). İkinci açılış birinciyi öne getirir ve çıkar.

Windows: adlı mutex (`Local\\LOGOS-Veli-Izin`); ikinci süreçte ERROR_ALREADY_EXISTS. Birincinin penceresi başlığından bulunur.
Mac / Linux: ayar klasöründe kilit dosyası (flock). Kaynaktan çalışırken (sınamalar, tarayıcı kipi) kilit yok.
"""
import os, sys, time

from uygulama import surum

BASLIK = surum.AD          # pywebview penceresinin başlığı (uygulama/ana.py pencere)
_tutulan = []              # kilidin nesnesi süreç boyunca yaşasın


def kilit_al(ad='LOGOS-Veli-Izin'):
    """True: ilk örnek (ya da kilit gerekmiyor). False: başka bir LOGOS Veli İzin açık; çağıran çıkmalı."""
    if sys.platform == 'win32': return _windows_kilit(ad)
    return _dosya_kilit(ad)


def _windows_kilit(ad):
    import ctypes
    k = ctypes.windll.kernel32
    k.CreateMutexW.restype = ctypes.c_void_p
    h = k.CreateMutexW(None, False, f'Local\\{ad}')
    if not h: return True
    if k.GetLastError() == 183:      # ERROR_ALREADY_EXISTS
        k.CloseHandle(ctypes.c_void_p(h)); return False
    _tutulan.append(h); return True


def _dosya_kilit(ad):
    try:
        import fcntl
        from uygulama import yerel
        f = open(os.path.join(yerel.ayar_klasoru(), f'{ad}.kilit'), 'w')
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _tutulan.append(f); return True
    except BlockingIOError:
        return False
    except Exception:
        return True


def one_getir(bekle=12.0):
    """Windows: açık pencereyi bulup öne getirir (birinci örnek daha açılıyorsa en çok `bekle` sn bekler)."""
    if sys.platform != 'win32': return False
    import ctypes
    u = ctypes.windll.user32; son = time.time() + bekle
    while True:
        h = u.FindWindowW(None, BASLIK)
        if h:
            u.ShowWindow(h, 9); u.SetForegroundWindow(h); return True
        if time.time() > son: return False
        time.sleep(0.4)
