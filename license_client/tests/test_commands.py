import argparse
import json
from datetime import UTC, datetime, timedelta

import pytest

from src.collect import Device, calculate_device_fingerprint
from src.commands import _parse_expires_at, handle_activate, handle_verify
from tests.conftest import sign_token


def test_parse_expires_at():
    assert _parse_expires_at(None) is None
    assert _parse_expires_at(1700000000) == datetime.fromtimestamp(1700000000, tz=UTC)
    assert _parse_expires_at("2027-01-01T00:00:00+00:00") == datetime(2027, 1, 1, tzinfo=UTC)
    assert _parse_expires_at("invalid-date-string") is None
    assert _parse_expires_at([1, 2, 3]) is None


def test_handle_activate_invalid_key_format(capsys):
    args = argparse.Namespace(license_key="INVALID-KEY", server="http://localhost:8000", dry_run=False, public_key=None)

    with pytest.raises(SystemExit) as exc_info:
        handle_activate(args)

    assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "Invalid license format" in captured.err


def test_handle_activate_server_runtime_error(mocker, rsa_key_pair):
    _, pub_pem = rsa_key_pair
    mocker.patch("src.commands.load_public_key", return_value=pub_pem)
    mocker.patch("src.commands.send_activation", side_effect=RuntimeError("Network error: timeout"))

    args = argparse.Namespace(
        license_key="ABCD-1234-EFGH-B6B6", server="http://localhost:8000", dry_run=False, public_key=None
    )
    with pytest.raises(SystemExit) as exc_info:
        handle_activate(args)

    assert exc_info.value.code == 1


def test_handle_activate_server_response_no_token(mocker, rsa_key_pair):
    _, pub_pem = rsa_key_pair
    mocker.patch("src.commands.load_public_key", return_value=pub_pem)
    mocker.patch("src.commands.send_activation", return_value={"status": "success"})

    args = argparse.Namespace(
        license_key="ABCD-1234-EFGH-B6B6", server="http://localhost:8000", dry_run=False, public_key=None
    )
    with pytest.raises(SystemExit) as exc_info:
        handle_activate(args)

    assert exc_info.value.code == 1


def test_handle_activate_dry_run(mocker, rsa_key_pair, capsys):
    _, pub_pem = rsa_key_pair
    mocker.patch("src.commands.load_public_key", return_value=pub_pem)

    args = argparse.Namespace(
        license_key="ABCD-1234-EFGH-B6B6",
        server="http://localhost:8000",
        dry_run=True,
        public_key=None,
    )

    with pytest.raises(SystemExit) as exc_info:
        handle_activate(args)

    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "[DRY RUN] Data from equipment" in captured.out
    assert "[DRY RUN] Payload that would be sent to the server" in captured.out


def test_handle_activate_success_flow(mocker, rsa_key_pair, tmp_path):
    priv_pem, pub_pem = rsa_key_pair
    mocker.patch("src.commands.load_public_key", return_value=pub_pem)

    token_payload = {
        "license_key": "ABCD-1234-EFGH-B6B6",
        "fingerprint": "abc123fp",
        "expires_at": "2029-01-01T00:00:00",
        "issued_at": int(datetime.now(UTC).timestamp()),
    }
    valid_token_str = sign_token(token_payload, priv_pem)

    mocker.patch("src.commands.send_activation", return_value={"activation_token": valid_token_str})
    mock_save = mocker.patch("src.commands.save_license", return_value=tmp_path / "license.lic")

    args = argparse.Namespace(
        license_key="ABCD-1234-EFGH-B6B6", server="http://localhost:8000", dry_run=False, public_key=None
    )
    handle_activate(args)
    mock_save.assert_called_once()


def test_handle_activate_token_verification_failed(mocker, rsa_key_pair):
    _, pub_pem = rsa_key_pair
    mocker.patch("src.commands.load_public_key", return_value=pub_pem)
    mocker.patch("src.commands.send_activation", return_value={"activation_token": "malformed_token_string"})

    args = argparse.Namespace(
        license_key="ABCD-1234-EFGH-B6B6",
        server="http://localhost:8000",
        dry_run=False,
        public_key=None,
    )

    with pytest.raises(SystemExit) as exc_info:
        handle_activate(args)

    assert exc_info.value.code == 1


def test_handle_verify_success(mocker, rsa_key_pair, tmp_path):
    priv_pem, pub_pem = rsa_key_pair
    lic_file = tmp_path / "license.lic"

    mock_device = Device(
        license_key="ABCD-1234-EFGH-B6B6",
        os_system="Linux",
        os_release="6.8.0-147-generic",
        os_version="#147-Ubuntu SMP PREEMPT_DYNAMIC",
        cpu_arch="x86_64",
        cpu_cores=8,
        mac_address="00:00:00:00:00:00",
        machine_id="abcdefghijklmnopqrstuwvxyz123456",
        disk_serial_number="ABCDEFGHIJKLMNO",
    )
    mocker.patch("src.commands.get_device_data", return_value=mock_device)

    expected_fingerprint = calculate_device_fingerprint(mock_device)

    token_payload = {
        "license_key": "ABCD-1234-EFGH-B6B6",
        "fingerprint": expected_fingerprint,
        "expires_at": (datetime.now(UTC) + timedelta(days=10)).isoformat(),
        "issued_at": int(datetime.now(UTC).timestamp()),
    }
    valid_token_str = sign_token(token_payload, priv_pem)

    license_data = {
        "activation_token": valid_token_str,
        "payload": token_payload,
        "license_key": "ABCD-1234-EFGH-B6B6",
        "fingerprint": expected_fingerprint,
    }
    lic_file.write_text(json.dumps(license_data), encoding="utf-8")

    mocker.patch("src.commands.load_public_key", return_value=pub_pem)

    args = argparse.Namespace(license_file=str(lic_file), license_key=None, public_key=None, json=True)
    handle_verify(args)


def test_handle_verify_expired(mocker, rsa_key_pair, tmp_path):
    priv_pem, pub_pem = rsa_key_pair
    lic_file = tmp_path / "license.lic"

    mock_device = Device(
        license_key="ABCD-1234-EFGH-B6B6",
        os_system="Linux",
        os_release="6.8.0-147-generic",
        os_version="#147-Ubuntu SMP PREEMPT_DYNAMIC",
        cpu_arch="x86_64",
        cpu_cores=8,
        mac_address="00:00:00:00:00:00",
        machine_id="abcdefghijklmnopqrstuwvxyz123456",
        disk_serial_number="ABCDEFGHIJKLMNO",
    )
    mocker.patch("src.commands.get_device_data", return_value=mock_device)

    expected_fingerprint = calculate_device_fingerprint(mock_device)

    token_payload = {
        "license_key": "ABCD-1234-EFGH-B6B6",
        "fingerprint": expected_fingerprint,  # ← ИСПРАВЛЕНО
        "expires_at": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        "issued_at": int(datetime.now(UTC).timestamp() - 86400),
    }
    valid_token_str = sign_token(token_payload, priv_pem)

    license_data = {
        "activation_token": valid_token_str,
        "payload": token_payload,
        "license_key": "ABCD-1234-EFGH-B6B6",
        "fingerprint": expected_fingerprint,
    }
    lic_file.write_text(json.dumps(license_data), encoding="utf-8")

    mocker.patch("src.commands.load_public_key", return_value=pub_pem)

    args = argparse.Namespace(license_file=str(lic_file), license_key=None, public_key=None, json=False)

    with pytest.raises(SystemExit) as exc_info:
        handle_verify(args)

    assert exc_info.value.code == 2


def test_handle_verify_not_same_device(mocker, rsa_key_pair, tmp_path, capsys):
    priv_pem, pub_pem = rsa_key_pair
    lic_file = tmp_path / "license.lic"

    issued_device = Device(
        license_key="ABCD-1234-EFGH-B6B6",
        os_system="Linux",
        os_release="6.8.0-147-generic",
        os_version="#147-Ubuntu SMP PREEMPT_DYNAMIC",
        cpu_arch="x86_64",
        cpu_cores=8,
        mac_address="00:00:00:00:00:00",
        machine_id="from_same_machine",
        disk_serial_number="ABCDEFGHIJKLMNO",
    )
    expected_fingerprint = calculate_device_fingerprint(issued_device)

    current_device = Device(
        license_key="ABCD-1234-EFGH-B6B6",
        os_system="Linux",
        os_release="6.8.0-147-generic",
        os_version="#147-Ubuntu SMP PREEMPT_DYNAMIC",
        cpu_arch="x86_64",
        cpu_cores=8,
        mac_address="00:00:00:00:00:00",
        machine_id="from_another_machine",
        disk_serial_number="ABCDEFGHIJKLMNO",
    )
    mocker.patch("src.commands.get_device_data", return_value=current_device)
    mocker.patch("src.commands.load_public_key", return_value=pub_pem)

    token_payload = {
        "license_key": "ABCD-1234-EFGH-B6B6",
        "fingerprint": expected_fingerprint,
        "expires_at": (datetime.now(UTC) + timedelta(days=10)).isoformat(),
        "issued_at": int(datetime.now(UTC).timestamp()),
    }
    valid_token_str = sign_token(token_payload, priv_pem)

    license_data = {
        "activation_token": valid_token_str,
        "payload": token_payload,
        "license_key": "ABCD-1234-EFGH-B6B6",
        "fingerprint": expected_fingerprint,
    }
    lic_file.write_text(json.dumps(license_data), encoding="utf-8")

    args = argparse.Namespace(license_file=str(lic_file), license_key=None, public_key=None, json=False)

    with pytest.raises(SystemExit) as exc_info:
        handle_verify(args)

    assert exc_info.value.code == 1
    assert "not bound to this device" in capsys.readouterr().err


def test_handle_verify_no_activation_token(tmp_path):
    lic_file = tmp_path / "empty_token.lic"
    lic_file.write_text('{"license_key": "ABCD-1234-EFGH-B6B6"}', encoding="utf-8")

    args = argparse.Namespace(
        license_file=str(lic_file),
        license_key=None,
        public_key=None,
        json=False,
    )

    with pytest.raises(SystemExit) as exc_info:
        handle_verify(args)

    assert exc_info.value.code == 1


def test_handle_verify_permission_denied(mocker, tmp_path):
    lic_file = tmp_path / "license.lic"
    lic_file.write_text("data")

    mocker.patch("json.loads", side_effect=PermissionError("Access denied"))

    args = argparse.Namespace(license_file=str(lic_file), license_key=None, public_key=None, json=False)

    with pytest.raises(SystemExit) as exc_info:
        handle_verify(args)

    assert exc_info.value.code == 1
