import json
from pathlib import Path

_PATH = Path(__file__).parent / "config.json"


def load_config():
    with open(_PATH, encoding="utf-8") as f:
        return json.load(f)


CFG = load_config()   # loaded once, imported wherever it's needed