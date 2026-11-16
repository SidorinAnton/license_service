import base64
import json
import os
import time
import zlib
from dataclasses import asdict, dataclass

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from src.collect import Device


@dataclass
class EncryptedPayload:
    encrypted_sync_key: str
    nonce: str
    cipher_data: str

    def to_dict(self) -> dict:
        return {
            "encrypted_sync_key": self.encrypted_sync_key,
            "nonce": self.nonce,
            "cipher_data": self.cipher_data,
        }


def encrypt_payload(data: Device, public_key_pem: str) -> EncryptedPayload:
    dict_data = asdict(data)
    dict_data["timestamp"] = int(time.time())
    json_data = json.dumps(dict_data).encode("utf-8")

    aes_key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)

    aes_gcm = AESGCM(aes_key)
    cipher_data = aes_gcm.encrypt(nonce, json_data, associated_data=None)

    public_key = load_pem_public_key(public_key_pem.encode("utf-8"))
    encrypted_aes_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    return EncryptedPayload(
        encrypted_sync_key=base64.b64encode(encrypted_aes_key).decode("utf-8"),
        nonce=base64.b64encode(nonce).decode("utf-8"),
        cipher_data=base64.b64encode(cipher_data).decode("utf-8"),
    )


def calculate_checksum(parts: list[str]) -> str:
    base_str = "".join(parts[:3]).upper()
    # 1) calculate 32-bit checksum
    # 2) 0xFFFF -- 16-bit mask (0b1111_1111_1111_1111)
    # 3) crc & ffff = 16-bit crc
    crc = zlib.crc32(base_str.encode("utf-8")) & 0xFFFF
    # 4) 04X -- make crc in HEX (16-sys) and get 4 symbols
    return f"{crc:04X}"


def is_license_key_valid(license_key: str) -> bool:
    parts = license_key.split("-")
    if len(parts) != 4:
        return False
    for part in parts:
        if len(part) != 4 or not part.isalnum():
            return False

    try:
        int(parts[3], 16)
    except ValueError:
        return False

    expected_checksum = calculate_checksum(parts)
    return parts[3].upper() == expected_checksum
