"""Small text storage for saves and settings: a file per key on desktop, the
browser's localStorage in the web build. Failures are reported and ignored,
so the game still runs where nothing can be stored (private browsing)."""

import os
import sys

WEB = sys.platform == "emscripten"
_PREFIX = "contour-colony:"


def _path(key):
    base = os.environ.get("CONTOUR_COLONY_HOME") or os.path.join(os.path.expanduser("~"), ".contour_colony")
    return os.path.join(base, f"{key}.json")


def save_text(key, text):
    try:
        if WEB:
            import platform
            platform.window.localStorage.setItem(_PREFIX + key, text)
        else:
            path = _path(key)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, path)   # never leave a half-written save
        return True
    except Exception as exc:
        print("storage: could not save", key, exc)
        return False


def load_text(key):
    try:
        if WEB:
            import platform
            value = platform.window.localStorage.getItem(_PREFIX + key)
            return str(value) if value is not None and str(value) not in ("", "null", "None") else None
        with open(_path(key), encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def delete(key):
    try:
        if WEB:
            import platform
            platform.window.localStorage.removeItem(_PREFIX + key)
        elif os.path.exists(_path(key)):
            os.remove(_path(key))
    except Exception as exc:
        print("storage: could not delete", key, exc)
