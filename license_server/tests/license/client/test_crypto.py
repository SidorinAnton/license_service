import base64
import json
import os
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.core.exceptions import DecryptionError
from src.schemas.license import ActivationTokenPayload
from src.services.crypto import decrypt_payload, load_private_key, sign_activation_token
from tests.license.crypto_utils import encrypt_test_payload


def test_decrypt_payload_success():
    original_data = {
        "license_key": "1111-1111-1111-BA9F",
        "machine_id": "aaa",
        "os_system": "aaa",
        "os_release": "aaa",
        "os_version": "aaa",
        "cpu_arch": "aaa",
        "cpu_cores": 1,
        "mac_address": "aaa",
    }
    encrypted_packet = encrypt_test_payload(**original_data)

    decrypted_data = decrypt_payload(
        encrypted_key=encrypted_packet["encrypted_sync_key"],
        nonce=encrypted_packet["nonce"],
        cipher_data=encrypted_packet["cipher_data"],
    )
    assert decrypted_data["license_key"] == "1111-1111-1111-BA9F"
    assert decrypted_data["machine_id"] == "aaa"
    assert decrypted_data["os_system"] == "aaa"
    assert decrypted_data["os_release"] == "aaa"
    assert decrypted_data["os_version"] == "aaa"
    assert decrypted_data["cpu_arch"] == "aaa"
    assert decrypted_data["cpu_cores"] == 1
    assert decrypted_data["mac_address"] == "aaa"
    assert isinstance(decrypted_data["timestamp"], int)
    assert decrypted_data["timestamp"] > 0


def test_decrypt_payload_invalid_tag_or_corrupted():
    original_data = {
        "license_key": "1111-1111-1111-BA9F",
        "machine_id": "crypto-test",
    }
    encrypted_packet = encrypt_test_payload(**original_data)

    corrupted_cipher_data = bytearray(encrypted_packet["cipher_data"])
    corrupted_cipher_data[0] ^= 0xFF

    with pytest.raises(DecryptionError, match="Invalid tag or corrupted payload"):
        decrypt_payload(
            encrypted_key=encrypted_packet["encrypted_sync_key"],
            nonce=encrypted_packet["nonce"],
            cipher_data=bytes(corrupted_cipher_data),
        )


@pytest.mark.parametrize(
    "bad_field,expected_msg",
    [
        ("encrypted_sync_key", "Failed to decrypt symmetric key"),
        ("nonce", "Invalid tag or corrupted payload"),
        ("cipher_data", "Invalid tag or corrupted payload"),
    ],
)
def test_decrypt_payload_invalid_fields(bad_field, expected_msg):
    data = encrypt_test_payload("1111-1111-1111-BA9F")
    data[bad_field] = b"!@#$ not base64"
    with pytest.raises(DecryptionError, match=expected_msg):
        decrypt_payload(encrypted_key=data["encrypted_sync_key"], nonce=data["nonce"], cipher_data=data["cipher_data"])


def test_decrypt_payload_wrong_nonce_length():
    data = encrypt_test_payload("1111-1111-1111-BA9F")
    with pytest.raises(DecryptionError, match="Failed to decrypt payload"):
        decrypt_payload(
            encrypted_key=data["encrypted_sync_key"],
            nonce=b"1",
            cipher_data=data["cipher_data"],
        )


def test_decrypt_payload_another_nonce():
    data = encrypt_test_payload("1111-1111-1111-BA9F")
    with pytest.raises(DecryptionError, match="Invalid tag or corrupted payload"):
        decrypt_payload(
            encrypted_key=data["encrypted_sync_key"],
            nonce=os.urandom(12),
            cipher_data=data["cipher_data"],
        )


def test_decrypt_payload_wrong_private_key():
    other_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_public = other_private.public_key()

    aes_key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    cipher_data = AESGCM(aes_key).encrypt(nonce, json.dumps({"x": 1}).encode(), None)

    encrypted_key = other_public.encrypt(
        aes_key,
        padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )

    with pytest.raises(DecryptionError, match="Failed to decrypt symmetric key"):
        decrypt_payload(encrypted_key=encrypted_key, nonce=nonce, cipher_data=cipher_data)


def test_sign_activation_token_success():
    payload = ActivationTokenPayload(
        license_key="TEST-1234-ABCD-4CE4",
        fingerprint="dummy_fingerprint_hash_123",
        expires_at=datetime(2027, 1, 1, 0, 0, 0, tzinfo=UTC),
        issued_at=1700000000,
    )

    token_str = sign_activation_token(payload)
    assert isinstance(token_str, str)
    assert len(token_str) > 0

    decoded_packet = json.loads(base64.b64decode(token_str).decode("utf-8"))
    assert "payload" in decoded_packet
    assert "signature" in decoded_packet

    payload_bytes = base64.b64decode(decoded_packet["payload"])
    signature_bytes = base64.b64decode(decoded_packet["signature"])

    private_key = load_private_key()
    public_key = private_key.public_key()

    public_key.verify(
        signature_bytes,
        payload_bytes,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

    data = json.loads(payload_bytes.decode("utf-8"))
    assert data["license_key"] == "TEST-1234-ABCD-4CE4"
    assert data["fingerprint"] == "dummy_fingerprint_hash_123"
    assert data["issued_at"] == 1700000000
    assert "2027-01-01" in data["expires_at"]
