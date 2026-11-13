import base64
import json
import os
import time
from dataclasses import asdict, dataclass

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from src.collect import Device


@dataclass
class EncryptedPayload:
    encrypted_sync_key: str
    nones: str
    cipher_data: str

    def to_dict(self) -> dict:
        return {
            "encrypted_sync_key": self.encrypted_sync_key,
            "nones": self.nones,
            "cipher_data": self.cipher_data,
        }


def encrypt_payload(data: Device, public_key_pem: str) -> EncryptedPayload:
    dict_data = asdict(data)
    dict_data["timestamp"] = int(time.time())
    json_data = json.dumps(dict_data).encode("utf-8")

    aes_key = AESGCM.generate_key(bit_length=256)
    nones = os.urandom(12)

    aes_gcm = AESGCM(aes_key)
    cipher_data = aes_gcm.encrypt(nones, json_data, associated_data=None)

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
        nones=base64.b64encode(nones).decode("utf-8"),
        cipher_data=base64.b64encode(cipher_data).decode("utf-8"),
    )
