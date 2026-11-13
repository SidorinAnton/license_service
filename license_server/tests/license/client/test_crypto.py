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
        encrypted_key_b64=encrypted_packet["encrypted_sync_key"],
        nonce_b64=encrypted_packet["nonce"],
        cipher_data_b64=encrypted_packet["cipher_data"],
    )
    assert decrypted_data["license_key"] == original_data["license_key"]
    assert decrypted_data["machine_id"] == original_data["machine_id"]


def test_decrypt_payload_invalid_tag_or_corrupted():
    original_data = {
        "license_key": "1234-1234-1234-1234",
        "machine_id": "crypto-test",
    }
    encrypted_packet = encrypt_test_payload(**original_data)

    raw_ciphertext = base64.b64decode(encrypted_packet["cipher_data"])
    corrupted_ciphertext = bytearray(raw_ciphertext)
    corrupted_ciphertext[0] ^= 0xFF
    corrupted_b64 = base64.b64encode(corrupted_ciphertext).decode("utf-8")

    with pytest.raises(ValueError) as exc_info:
        decrypt_payload(
            encrypted_key_b64=encrypted_packet["encrypted_sync_key"],
            nonce_b64=encrypted_packet["nonce"],
            cipher_data_b64=corrupted_b64,
        )
        assert "data integrity check failed" in str(exc_info.value)


def test_decrypt_payload_invalid_base64():
    with pytest.raises(ValueError) as exc_info:
        decrypt_payload(
            encrypted_key_b64="not-a-base64-string!@#$",
            nonce_b64="not-nonce",
            cipher_data_b64="not-cipher_data",
        )

        assert "Invalid Base64 encoding" in str(exc_info.value)
