import base64
import json
import time

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.crypto import EncryptedPayload, encrypt_payload, verify_activation_token
from tests.conftest import sign_token


def decrypt_payload_on_server(encrypted: EncryptedPayload, private_key_pem: str) -> dict:
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
    )
    # Получаем симметричный AES ключ
    aes_key = private_key.decrypt(
        base64.b64decode(encrypted.encrypted_sync_key),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    # Расшифровываем пэйлоад через AES-GCM
    aes_gcm = AESGCM(aes_key)
    decrypted_data_bytes = aes_gcm.decrypt(
        base64.b64decode(encrypted.nonce), base64.b64decode(encrypted.cipher_data), associated_data=None
    )
    return json.loads(decrypted_data_bytes.decode("utf-8"))


def test_encrypt_and_decrypt_success(rsa_key_pair, device_data):
    priv_pem, pub_pem = rsa_key_pair

    encrypted = encrypt_payload(device_data, pub_pem)
    assert isinstance(encrypted, EncryptedPayload)

    decrypted_data = decrypt_payload_on_server(encrypted, priv_pem)

    assert decrypted_data["license_key"] == device_data.license_key
    assert decrypted_data["os_system"] == device_data.os_system
    assert decrypted_data["cpu_cores"] == device_data.cpu_cores
    assert decrypted_data["machine_id"] == device_data.machine_id
    assert "timestamp" in decrypted_data
    assert isinstance(decrypted_data["timestamp"], int)
    assert decrypted_data["timestamp"] <= int(time.time())


def test_encryption_hashsum_fails(rsa_key_pair, device_data):
    priv_pem, pub_pem = rsa_key_pair

    encrypted = encrypt_payload(device_data, pub_pem)

    cipher_bytes = list(encrypted.cipher_data)
    cipher_bytes[0] = "A" if cipher_bytes[0] != "A" else "B"
    encrypted.cipher_data = "".join(cipher_bytes)

    with pytest.raises(InvalidTag):
        decrypt_payload_on_server(encrypted, priv_pem)


def test_verify_token_ok(rsa_key_pair):
    priv_pem, pub_pem = rsa_key_pair
    payload = {
        "license_key": "ABCD-1234-EFGH-B6B6",
        "fingerprint": "aaaa",
        "expires_at": "2027-01-01",
        "issued_at": 1700000000,
    }
    activation_token = sign_token(payload, priv_pem)
    token = verify_activation_token(activation_token, pub_pem, "ABCD-1234-EFGH-B6B6")
    assert token.license_key == "ABCD-1234-EFGH-B6B6"
    assert token.fingerprint == "aaaa"
    assert token.expires_at == "2027-01-01"
    assert token.issued_at == 1700000000
    assert token.raw_payload == payload
    assert token.raw_token == activation_token


def test_verify_token_tampered(rsa_key_pair):
    priv_pem, pub_pem = rsa_key_pair
    payload = {
        "license_key": "ABCD-1234-EFGH-B6B6",
        "fingerprint": "fp123",
        "expires_at": None,
        "issued_at": 1,
    }
    activation_token = sign_token(payload, priv_pem)

    # подменяем payload внутри пакета
    packet = json.loads(base64.b64decode(activation_token))
    packet["payload"] = base64.b64encode(json.dumps({**payload, "expires_at": "2099-01-01"}).encode()).decode()
    bad = base64.b64encode(json.dumps(packet).encode()).decode()

    with pytest.raises(RuntimeError, match="Activation token signature is invalid"):
        verify_activation_token(bad, pub_pem, "ABCD-1234-EFGH-B6B6")
