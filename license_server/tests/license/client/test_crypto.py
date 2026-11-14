import base64

import pytest

from src.services.crypto import decrypt_payload
from tests.license.crypto_utils import encrypt_test_payload


def test_decrypt_payload_success():
    original_data = {
        "license_key": "1234-1234-1234-1234",
        "machine_id": "crypto-test",
    }
    encrypted_packet = encrypt_test_payload(**original_data)

    decrypted_data = decrypt_payload(
        encrypted_key=encrypted_packet["encrypted_sync_key"],
        nonce=encrypted_packet["nonce"],
        cipher_data=encrypted_packet["cipher_data"],
    )
    assert decrypted_data["license_key"] == original_data["license_key"]
    assert decrypted_data["machine_id"] == original_data["machine_id"]


def test_decrypt_payload_invalid_tag_or_corrupted():
    original_data = {
        "license_key": "1234-1234-1234-1234",
        "machine_id": "crypto-test",
    }
    encrypted_packet = encrypt_test_payload(**original_data)

    corrupted_ciphertext = bytearray(encrypted_packet["cipher_data"])
    corrupted_ciphertext[0] ^= 0xFF
    corrupted_b64 = corrupted_ciphertext

    with pytest.raises(ValueError) as exc_info:
        decrypt_payload(
            encrypted_key=encrypted_packet["encrypted_sync_key"],
            nonce=encrypted_packet["nonce"],
            cipher_data=corrupted_b64,
        )
        assert "data integrity check failed" in str(exc_info.value)


def test_decrypt_payload_invalid_base64(client):
    with pytest.raises(ValueError) as exc_info:
        decrypt_payload(
            encrypted_key=b"not-a-base64-string!@#$",
            nonce=b"not-nonce",
            cipher_data=b"not-cipher_data",
        )

        assert "Invalid Base64 encoding" in str(exc_info.value)
