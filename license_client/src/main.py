import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from src.api import send_activation
from src.collect import get_device_data
from src.crypto import encrypt_payload

__version__ = "1.0.0"


def is_license_key_valid(license_key: str) -> bool:
    parts = license_key.split("-")
    if len(parts) != 4:
        return False
    for part in parts:
        if len(part) != 4 or not part.isalnum():
            return False
    return True


def load_public_key() -> str:
    key_path = Path(__file__).parent.parent / "config" / "public_key.pem"
    if not key_path.exists():
        print(f"Error: Public key not found at {key_path}. Did you run 'make keys'?", file=sys.stderr)
        sys.exit(1)
    return key_path.read_text(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collects equipment data and registers it with the license service")
    parser.add_argument("--version", action="version", version=f"License client {__version__}")
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Perform a dry run: collect data, encrypt it and print payload without sending it to the server",
    )
    parser.add_argument("license_key", help="License number in the format XXXX-XXXX-XXXX-XXXX")
    parser.add_argument("server", help="License server URL (ex: https://localhost:8000)")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not is_license_key_valid(args.license_key):
        print(
            f"Error: Invalid license format: '{args.license_key}'. Expected format is XXXX-XXXX-XXXX-XXXX.",
            file=sys.stderr,
        )
        sys.exit(1)

    device_data = get_device_data(args.license_key)
    public_key_pem = load_public_key()
    payload = encrypt_payload(device_data, public_key_pem)

    if args.dry_run:
        print("[DRY RUN] Data from equipment:")
        print(json.dumps(asdict(device_data), indent=2))
        print(f"\n[DRY RUN] Payload that would be sent to the server on {args.server}:")
        print(json.dumps(payload.to_dict(), indent=2))
        sys.exit(0)

    try:
        result = send_activation(args.server, payload)
        print("Success:", result)
    except RuntimeError as e:
        print(f"Activation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
