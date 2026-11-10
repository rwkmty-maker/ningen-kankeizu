# -*- coding: utf-8 -*-
import os
import webbrowser
import subprocess
import winreg


def open_url_securely(url):
    """
    Google Chromeがあればシークレットモードかつアプリモードで開く。
    なければデフォルトブラウザで開く。
    """
    if not url:
        return
    
    chrome_path = None
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as key:
            chrome_path = winreg.QueryValue(key, None)
    except (OSError, FileNotFoundError, PermissionError) as e:
        pass

    if chrome_path and os.path.exists(chrome_path):
        try:
            subprocess.Popen([chrome_path, '--incognito', '--new-window', f'--app={url}'])
            return
        except (OSError, subprocess.SubprocessError) as e:
            pass
    
    try:
        webbrowser.open(url)
    except Exception as e:
        pass
