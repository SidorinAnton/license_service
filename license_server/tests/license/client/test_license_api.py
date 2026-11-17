import base64
import time

from src.models.license import ActivationModel
from src.schemas.license import ActivationTokenPayload, DeviceDataSchema
from src.services.crypto import sign_activation_token
from src.services.license import generate_device_fingerprint
from tests.license.crypto_utils import build_http_payload, encrypt_test_payload


def test_activate_endpoint_success(client, db_session, sample_license):
    data = encrypt_test_payload(
        license_key=sample_license.key,
        machine_id="aaa",
        disk_serial_number="ggg",
        os_system="bbb",
        os_release="ccc",
        os_version="ddd",
        cpu_arch="eee",
        cpu_cores=8,
        mac_address="fff",
    )

    response = client.post("/api/v1/client/activations", json=build_http_payload(data))
    assert response.status_code == 200

    act = db_session.query(ActivationModel).filter_by(license_id=sample_license.id, machine_id="aaa").one()

    token_payload = ActivationTokenPayload(
        license_key=sample_license.key,
        fingerprint=act.fingerprint,
        expires_at=sample_license.expires_at,
        issued_at=int(act.activated_at.timestamp()),
    )

    assert response.json() == {
        "status": "success",
        "message": "License successfully activated on this device",
        "activation_token": sign_activation_token(token_payload),
    }
    assert act.license_id == sample_license.id
    assert act.machine_id == "aaa"
    assert act.fingerprint == generate_device_fingerprint(
        DeviceDataSchema(
            license_key=sample_license.key,
            machine_id="aaa",
            disk_serial_number="ggg",
            os_system="bbb",
            os_release="ccc",
            os_version="ddd",
            cpu_arch="eee",
            cpu_cores=8,
            mac_address="fff",
            timestamp=int(time.time()),
        )
    )


def test_activate_endpoint_idempotent(client, db_session, sample_license):
    data = build_http_payload(encrypt_test_payload(sample_license.key, machine_id="same-machine"))
    response_1 = client.post("/api/v1/client/activations", json=data)
    assert response_1.status_code == 200

    act = db_session.query(ActivationModel).filter_by(license_id=sample_license.id).first()
    token_payload = ActivationTokenPayload(
        license_key=sample_license.key,
        fingerprint=act.fingerprint,
        expires_at=sample_license.expires_at,
        issued_at=int(act.activated_at.timestamp()),
    )
    assert response_1.json() == {
        "status": "success",
        "message": "License successfully activated on this device",
        "activation_token": sign_activation_token(token_payload),
    }

    response_2 = client.post("/api/v1/client/activations", json=data)
    assert response_2.status_code == 409
    assert response_2.json() == {"detail": "This license has already been activated"}

    act = db_session.query(ActivationModel).filter_by(license_id=sample_license.id).all()
    assert len(act) == 1


def test_activate_endpoint_invalid_key_format(client):
    data = encrypt_test_payload("aaa-111-")

    response = client.post("/api/v1/client/activations", json=build_http_payload(data))

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "input": "aaa-111-",
                "loc": ["license_key"],
                "msg": "Value error, Invalid license key format. Expected format: XXXX-XXXX-XXXX-XXXX",
                "type": "value_error",
            }
        ]
    }


def test_activate_endpoint_expired_timestamp(client, sample_license):
    old_ts = int(time.time()) - 3600  # 1 час назад
    data = encrypt_test_payload(sample_license.key, timestamp=old_ts)

    response = client.post("/api/v1/client/activations", json=build_http_payload(data))

    assert response.status_code == 400
    assert response.json() == {"detail": "Payload expired or invalid timestamp"}


def test_activate_endpoint_incorrect_ciphertext(client):
    raw_payload = {"encrypted_sync_key": "!!!", "nonce": "!!!", "cipher_data": "!!!"}
    response = client.post("/api/v1/client/activations", json=raw_payload)
    assert response.status_code == 400
    assert response.json() == {"detail": "Failed to decrypt symmetric key"}


def test_activate_endpoint_corrupted_ciphertext(client, sample_license):
    data = encrypt_test_payload(sample_license.key)
    payload = build_http_payload(data)

    # норм RSA-ключ, но испорченный cipher_data
    corrupted = bytearray(data["cipher_data"])
    corrupted[0] ^= 0xFF
    payload["cipher_data"] = base64.b64encode(bytes(corrupted)).decode()

    response = client.post("/api/v1/client/activations", json=payload)
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid tag or corrupted payload"}


def test_activate_endpoint_empty(client):
    raw_payload = {}
    response = client.post("/api/v1/client/activations", json=raw_payload)
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {"input": {}, "loc": ["body", "encrypted_sync_key"], "msg": "Field required", "type": "missing"},
            {"input": {}, "loc": ["body", "nonce"], "msg": "Field required", "type": "missing"},
            {"input": {}, "loc": ["body", "cipher_data"], "msg": "Field required", "type": "missing"},
        ]
    }


def test_activate_endpoint_license_not_found(client):
    data = encrypt_test_payload("1111-1111-1111-BA9F")
    request = client.post("/api/v1/client/activations", json=build_http_payload(data))
    assert request.status_code == 404
    assert request.json() == {"detail": "License key not found"}


def test_activate_endpoint_inactive(client, inactive_license):
    data = encrypt_test_payload(inactive_license.key)
    request = client.post("/api/v1/client/activations", json=build_http_payload(data))
    assert request.status_code == 403
    assert request.json() == {"detail": "License key is deactivated"}


def test_activate_endpoint_expired_license(client, expired_license):
    data = encrypt_test_payload(expired_license.key)
    request = client.post("/api/v1/client/activations", json=build_http_payload(data))
    assert request.status_code == 403
    assert request.json() == {"detail": "License key has expired"}


def test_activate_endpoint_limit_exceeded(client, sample_license):
    data1 = encrypt_test_payload(sample_license.key, machine_id="m-1")
    request_1 = client.post("/api/v1/client/activations", json=build_http_payload(data1))
    assert request_1.status_code == 200
    assert request_1.json()["status"] == "success"

    data2 = encrypt_test_payload(sample_license.key, machine_id="m-2")
    request_2 = client.post("/api/v1/client/activations", json=build_http_payload(data2))
    assert request_2.status_code == 409
    assert request_2.json() == {"detail": "Activation limit reached for this license"}


def test_activate_endpoint_multiple_activations(client, db_session, multi_activation_license):
    for i in range(3):
        data = encrypt_test_payload(multi_activation_license.key, machine_id=f"m-{i}")
        response = client.post("/api/v1/client/activations", json=build_http_payload(data))
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    assert db_session.query(ActivationModel).filter_by(license_id=multi_activation_license.id).count() == 3

    data4 = encrypt_test_payload(multi_activation_license.key, machine_id="m-3")
    response4 = client.post("/api/v1/client/activations", json=build_http_payload(data4))
    assert response4.status_code == 409
    assert response4.json() == {"detail": "Activation limit reached for this license"}


def test_activate_endpoint_idempotent_when_limit_reached(client, db_session, multi_activation_license):
    for i in range(3):
        data = encrypt_test_payload(multi_activation_license.key, machine_id=f"m-{i}")
        assert client.post("/api/v1/client/activations", json=build_http_payload(data)).status_code == 200

    repeat = encrypt_test_payload(multi_activation_license.key, machine_id="m-1")
    response = client.post("/api/v1/client/activations", json=build_http_payload(repeat))
    assert response.status_code == 409
    assert response.json() == {"detail": "This license has already been activated"}
