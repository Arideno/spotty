import json
import os
import tempfile
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "spotty"
CONFIG_FILE = CONFIG_DIR / "config.json"
TOKEN_FILE = CONFIG_DIR / "tokens.json"

_DEFAULTS = {
    "redirect_uri": "http://127.0.0.1:8888/callback",
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return {**_DEFAULTS, **json.loads(CONFIG_FILE.read_text())}
    return dict(_DEFAULTS)


def save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    payload = json.dumps(data, indent=2).encode()
    fd, tmp = tempfile.mkstemp(dir=CONFIG_DIR, prefix=".cfg.")
    try:
        os.write(fd, payload)
        os.close(fd)
        os.chmod(tmp, 0o600)
        os.replace(tmp, CONFIG_FILE)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def get(key: str) -> str | None:
    return load_config().get(key)
