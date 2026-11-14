import base64
import time

import pytest

from src.schemas.license import DeviceDataSchema
from src.services.license import activate_device_service
from tests.license.crypto_utils import encrypt_test_payload


def get_device_data(license_key, machine_id="machine-1") -> DeviceDataSchema:
    return DeviceDataSchema(
        license_key=license_key,
        machine_id=machine_id,
        os_system="Linux",
        os_release="",
        os_version="",
        cpu_arch="",
        cpu_cores=8,
        mac_address="",
        timestamp=int(time.time()),
    )


def test_activate_endpoint_success(client, sample_license):
    data = encrypt_test_payload(sample_license.key)
    payload = {
        "encrypted_sync_key": base64.b64encode(data["encrypted_sync_key"]).decode("utf-8"),
        "nonce": base64.b64encode(data["nonce"]).decode("utf-8"),
        "cipher_data": base64.b64encode(data["cipher_data"]).decode("utf-8"),
    }

    response = client.post("/api/v1/client/activate", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "License successfully activated on this device"}


def test_activate_endpoint_invalid_key_format(client):
    data = encrypt_test_payload("aaa-111-")
    payload = {
        "encrypted_sync_key": base64.b64encode(data["encrypted_sync_key"]).decode("utf-8"),
        "nonce": base64.b64encode(data["nonce"]).decode("utf-8"),
        "cipher_data": base64.b64encode(data["cipher_data"]).decode("utf-8"),
    }

    response = client.post("/api/v1/client/activate", json=payload)
    assert response.status_code == 400
    assert "Invalid license key format" in response.json()["detail"]


def test_activate_license_success(db_session, sample_license):
    device_data = get_device_data(sample_license.key)
    result = activate_device_service(db=db_session, device_data=device_data)
    assert result == {
        "status": "success",
        "message": "License successfully activated on this device",
    }


def test_activate_license_same_key_and_device(db_session, sample_license):
    device_data = get_device_data(sample_license.key)
    activate_device_service(db=db_session, device_data=device_data)
    result = activate_device_service(db=db_session, device_data=device_data)
    assert result == {"status": "already_activated", "message": "Device is already registered for this license"}


def test_activate_license_not_found(db_session):
    device_data = get_device_data("1111-1111-1111-1111")
    with pytest.raises(ValueError) as e:
        activate_device_service(db=db_session, device_data=device_data)
        assert str(e) == "License key not found"


def test_activate_license_inactive(db_session, inactive_license):
    device_data = get_device_data(inactive_license.key)
    with pytest.raises(ValueError) as e:
        activate_device_service(db=db_session, device_data=device_data)
        assert str(e) == "License key is deactivated"


def test_activate_license_expired(db_session, expired_license):
    device_data = get_device_data(expired_license.key)
    with pytest.raises(ValueError) as e:
        activate_device_service(db=db_session, device_data=device_data)
        assert str(e) == "License key is expired"


def test_activate_license_limit_exceeded(db_session, sample_license):
    device_data_1 = get_device_data(sample_license.key, "machine-1")
    device_data_2 = get_device_data(sample_license.key, "machine-2")
    activate_device_service(db=db_session, device_data=device_data_1)
    with pytest.raises(ValueError) as e:
        activate_device_service(db=db_session, device_data=device_data_2)
        assert str(e) == "License is already used"
