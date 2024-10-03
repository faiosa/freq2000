import os
import sys


def get_user_data_dir():
    if sys.platform == "win32":
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
        )
        dir = winreg.QueryValueEx(key, "Local AppData")[0]
        return os.path.join(dir, "FrequencyTable")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/FrequencyTable")
    else:  # linux and other unix systems
        return os.path.expanduser("~/.frequencytable")


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS2
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.normpath(os.path.join(base_path, relative_path))
