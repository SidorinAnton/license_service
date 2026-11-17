import argparse
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from src.api import send_activation
from src.collect import get_device_data
from src.crypto import (
    encrypt_payload,
    is_license_key_valid,
    verify_activation_token,
)
from src.storage import LICENSE_PATH, load_license, load_public_key, save_license


def handle_activate(args: argparse.Namespace) -> None:
    if not is_license_key_valid(args.license_key):
        print(
            f"Error: Invalid license format: '{args.license_key}'. Expected format is XXXX-XXXX-XXXX-XXXX.",
            file=sys.stderr,
        )
        sys.exit(1)

    device_data = get_device_data(args.license_key)
    public_key_pem = load_public_key(args.public_key)
    payload = encrypt_payload(device_data, public_key_pem)

    if args.dry_run:
        print("[DRY RUN] Data from equipment:")
        print(json.dumps(asdict(device_data), indent=2))
        print(f"\n[DRY RUN] Payload that would be sent to the server on {args.server}:")
        print(json.dumps(payload.to_dict(), indent=2))
        sys.exit(0)

    try:
        result = send_activation(args.server, payload)
        print(f"Result from server: {result}")
    except RuntimeError as e:
        print(f"Activation failed: {e}", file=sys.stderr)
        sys.exit(1)

    activation_token = result.get("activation_token")
    if not activation_token:
        print("Error: server response does not contain activation_token", file=sys.stderr)
        sys.exit(1)

    try:
        token = verify_activation_token(
            activation_token=activation_token,
            public_key_pem=public_key_pem,
            expected_license_key=args.license_key,
        )
    except RuntimeError as e:
        print(f"Activation token verification failed: {e}", file=sys.stderr)
        sys.exit(1)

    license_data = {
        "activation_token": token.raw_token,
        "payload": token.raw_payload,
        "license_key": token.license_key,
        "fingerprint": token.fingerprint,
        "issued_at": token.issued_at,
        "expires_at": token.expires_at,
        "activated_at": int(datetime.now(UTC).timestamp()),
        "server": args.server,
    }
    path = save_license(license_data)
    print("Success!!")
    print(f"License was activated and saved into '{path}'")
    print(f"License expires at: {token.expires_at}")


def handle_verify(args: argparse.Namespace) -> None:
    path = Path(args.license_file) if args.license_file else LICENSE_PATH

    try:
        data = load_license(path)
    except RuntimeError as e:
        print(f"Verification failed: {e}", file=sys.stderr)
        sys.exit(1)

    activation_token = data.get("activation_token")
    if not activation_token:
        print(f"Verification failed: no activation_token in {path}", file=sys.stderr)
        sys.exit(1)

    public_key_pem = load_public_key(args.public_key)
    expected_license_key = args.license_key or data.get("license_key")

    try:
        token = verify_activation_token(
            activation_token=activation_token,
            public_key_pem=public_key_pem,
            expected_license_key=expected_license_key,
        )
    except RuntimeError as e:
        print(f"Verification failed: {e}", file=sys.stderr)
        sys.exit(1)

    if _is_expired(token.expires_at):
        print(f"Verification failed: license expired at {token.expires_at}", file=sys.stderr)
        sys.exit(2)

    print(f"License is valid. Key: {token.license_key}")
    print(f"Fingerprint: {token.fingerprint}")
    print(f"Issued at: {token.issued_at}")
    print(f"Expires at: {token.expires_at}")
    if args.json:
        print(json.dumps(token.raw_payload, indent=2, ensure_ascii=False))


def _parse_expires_at(value) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _is_expired(expires_at) -> bool:
    dt = _parse_expires_at(expires_at)
    return dt is not None and dt < datetime.now(UTC)
