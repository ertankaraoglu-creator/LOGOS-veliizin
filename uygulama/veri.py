"""Programla gelen veri dosyaları (`veri/`): tatiller ve MEB çalışma takvimi (`tatiller.json`, LOGOS Disiplin'den) ve izin nedenleri.

Kaynak kökü paketli uygulamada PyInstaller'ın açtığı klasör, kaynaktan çalışırken depo kökü.
"""
import json, os, sys

_onbellek = {}


def kok():
    return getattr(sys, '_MEIPASS', None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def yukle(ad):
    """veri/<ad>.json (bir kez okunur)."""
    if ad not in _onbellek:
        with open(os.path.join(kok(), 'veri', ad + '.json'), encoding='utf-8') as f: _onbellek[ad] = json.load(f)
    return _onbellek[ad]
