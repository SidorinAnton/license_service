import subprocess
import sys

import pytest

from src.main import is_license_key_valid


@pytest.mark.parametrize(
    "key, expected",
    [
        ("ABCD-1234-EFGH-5678", True),
        ("1234-ABCD-5678-WXYZ", True),
        ("abcd-1234-efgh-5678", True),
        ("ABC-1234-EFGH-5678", False),
        ("ABCD-123-EFGH-5678", False),
        ("ABCD-1234-EFGH-5678-9999", False),
        ("ABCD-1234-EFGH-567!", False),
        ("", False),
    ],
)
def test_license_key_validation(key, expected):
    assert is_license_key_valid(key) is expected


def test_cli_success():
    result = subprocess.run(
        [sys.executable, "src/main.py", "-d", "ABCD-1234-EFGH-5678", "http://localhost:8000"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "[DRY RUN] Data from equipment" in result.stdout
    assert "[DRY RUN] Payload that would be sent to the server" in result.stdout


def test_real_cli_help():
    result = subprocess.run(
        [sys.executable, "src/main.py", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Collects equipment data" in result.stdout


def test_real_cli_invalid_key():
    result = subprocess.run(
        [sys.executable, "src/main.py", "INVALID-KEY", "http://localhost:8000"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Invalid license format" in result.stderr


def test_real_cli_invalid_server():
    result = subprocess.run(
        [sys.executable, "src/main.py", "ABCD-1234-EFGH-5678", "lolkek"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Activation failed" in result.stderr
