import importlib.resources
import json
import os
import sys
from pathlib import Path
from typing import Any

from platformdirs import user_data_dir

APP_NAME = "license_client"
APP_AUTHOR = None

LICENSE_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
LICENSE_PATH = LICENSE_DIR / "license.lic"


def save_license(data: dict[str, Any], path: Path = LICENSE_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # TODO завести эту штуку и на винде
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass

    return path


def load_license(path: Path = LICENSE_PATH) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"License file not found at {path}. Run `activate` first.")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise RuntimeError(f"Malformed license file at {path}: {e}")
    except PermissionError as e:
        raise RuntimeError(f"Permission denied to read license file at {path}: {e}")


def load_public_key(custom_path: str | None = None) -> str:
    key_path_str = custom_path or os.getenv("LICENSE_PUBLIC_KEY_PATH")
    if key_path_str:
        key_path = Path(key_path_str)
        if not key_path.exists():
            print(f"Error: Public key not found at specified path: {key_path}", file=sys.stderr)
            sys.exit(1)
        return key_path.read_text(encoding="utf-8")

    ref = importlib.resources.files("src").joinpath("config/public_key.pem")
    if ref.is_file():
        return ref.read_text(encoding="utf-8")

    print(
        "Error: Public key not found. Please provide it via --public-key option "
        "or set LICENSE_PUBLIC_KEY_PATH environment variable.",
        file=sys.stderr,
    )
    sys.exit(1)
