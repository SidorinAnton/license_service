import os

import pytest

from src.storage import load_license, load_public_key, save_license


def test_save_and_load_license(tmp_path):
    lic_path = tmp_path / "subdir" / "license.lic"
    data = {"license_key": "ABCD-1234-EFGH-B6B6"}

    saved_path = save_license(data, path=lic_path)
    assert saved_path == lic_path
    assert lic_path.exists()

    loaded_data = load_license(lic_path)
    assert loaded_data == data


def test_load_license_not_found(tmp_path):
    missing_path = tmp_path / "nonexistent.lic"
    with pytest.raises(RuntimeError, match="License file not found"):
        load_license(missing_path)


def test_load_license_malformed(tmp_path):
    bad_path = tmp_path / "bad.lic"
    bad_path.write_text("{ malformed json", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Malformed license file"):
        load_license(bad_path)


def test_load_public_key_custom_path(tmp_path):
    key_file = tmp_path / "public_key.pem"
    key_content = "-----BEGIN PUBLIC KEY-----\nTESTKEY\n-----END PUBLIC KEY-----"
    key_file.write_text(key_content, encoding="utf-8")

    assert load_public_key(str(key_file)) == key_content


def test_load_public_key_env(tmp_path, mocker):
    key_file = tmp_path / "public_key_env.pem"
    key_content = "-----BEGIN PUBLIC KEY-----\nENVKEY\n-----END PUBLIC KEY-----"
    key_file.write_text(key_content, encoding="utf-8")

    mocker.patch.dict(os.environ, {"LICENSE_PUBLIC_KEY_PATH": str(key_file)})
    assert load_public_key() == key_content


def test_load_public_key_not_found():
    with pytest.raises(SystemExit) as exc_info:
        load_public_key("nonexistent_path.pem")

    assert exc_info.value.code == 1


def test_save_license_sets_secure_permissions_unix(tmp_path):
    lic_path = tmp_path / "license.lic"
    data = {"license_key": "ABCD-1234-EFGH-B6B6"}

    save_license(data, path=lic_path)
    assert lic_path.exists()

    if os.name != "nt":
        file_mode = os.stat(lic_path).st_mode & 0o777
        assert file_mode == 0o600
