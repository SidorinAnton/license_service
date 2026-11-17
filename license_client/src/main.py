import argparse

__version__ = "1.1.0"

from src.commands import handle_activate, handle_verify


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="License client: activate and verify a license.",
    )
    parser.add_argument("--version", action="version", version=f"License client {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    parser_activate = sub.add_parser("activate", help="Activate license on this device")
    parser_activate.add_argument("license_key", help="License number in the format XXXX-XXXX-XXXX-XXXX")
    parser_activate.add_argument("server", help="License server URL (ex: https://localhost:8000)")
    parser_activate.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Collect and encrypt data, print payload, do not send",
    )
    parser_activate.add_argument(
        "--public-key", "-k", type=str, default=None, help="Path to custom public RSA key (.pem)"
    )
    parser_activate.set_defaults(func=handle_activate)

    parser_verify = sub.add_parser("verify", help="Verify saved license")
    parser_verify.add_argument(
        "--license-file", "-f", type=str, default=None, help="Path to license.lic (default: platform data dir)"
    )
    parser_verify.add_argument(
        "--license-key", type=str, default=None, help="Expected license key (optional, defaults to stored one)"
    )
    parser_verify.add_argument(
        "--public-key", "-k", type=str, default=None, help="Path to custom public RSA key (.pem)"
    )
    parser_verify.add_argument("--json", action="store_true", help="Print payload as JSON")
    parser_verify.set_defaults(func=handle_verify)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
