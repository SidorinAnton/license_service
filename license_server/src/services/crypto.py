import base64
import json

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from src.core.config import settings


def load_private_key() -> bytes:
    with open(settings.PRIVATE_KEY_PATH, "rb") as f:
        return f.read()


def decrypt_payload(encrypted_key_b64: str, nones_b64: str, cipher_data_b64: str) -> dict:
    encrypted_key = base64.b64decode(encrypted_key_b64)
    nones = base64.b64decode(nones_b64)
    cipher_data = base64.b64decode(cipher_data_b64)

    private_key_pem = load_private_key()
    private_key = load_pem_private_key(private_key_pem, password=None)

    symmetric_key = private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    aes_gcm = AESGCM(symmetric_key)

    try:
        decrypted_data = aes_gcm.decrypt(nones, cipher_data, None)
    except InvalidTag:
        raise ValueError("Decryption failed: invalid tag or corrupted payload")

    decrypted_data = json.loads(decrypted_data.decode("utf-8"))
    return decrypted_data
