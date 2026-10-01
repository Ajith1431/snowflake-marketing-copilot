"""Load API keys from environment variables, falling back to a gitignored .env at the repo root."""

import os
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _load_dotenv():
    if not _ENV_FILE.exists():
        return
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            name, value = line.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip().strip("'\""))


_load_dotenv()


def get_secret(name, required=True):
    value = os.environ.get(name, "")
    if required and not value:
        raise SystemExit(f"{name} is not set. Add it to {_ENV_FILE} or export it as an environment variable.")
    return value
