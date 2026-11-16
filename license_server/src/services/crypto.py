import json
import logging
import zlib

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from src.core.config import settings
from src.core.exceptions import DecryptionError

logger = logging.getLogger(__name__)


def load_private_key() -> bytes:
    with open(settings.PRIVATE_KEY_PATH, "rb") as f:
        return f.read()


def decrypt_payload(encrypted_key: bytes, nonce: bytes, cipher_data: bytes) -> dict:
    private_key_pem = load_private_key()
    private_key = load_pem_private_key(private_key_pem, password=None)

    try:
        symmetric_key = private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except ValueError:
        logger.error("Failed to decrypt symmetric key using private RSA key (OAEP padding error)")
        raise DecryptionError("Failed to decrypt symmetric key")

    try:
        aes_gcm = AESGCM(symmetric_key)
        decrypted_data = aes_gcm.decrypt(nonce, cipher_data, None)
        return json.loads(decrypted_data.decode("utf-8"))
    except InvalidTag:
        logger.warning("Decryption security warning: Invalid AES-GCM tag")
        raise DecryptionError("Invalid tag or corrupted payload")
    except ValueError:
        logger.warning("Decryption failed: ValueError during AES-GCM payload decryption")
        raise DecryptionError("Failed to decrypt payload")


def calculate_checksum(parts: list[str]) -> str:
    base_str = "".join(parts[:3]).upper()
    # 1) calculate 32-bit checksum
    # 2) 0xFFFF -- 16-bit mask (0b1111_1111_1111_1111)
    # 3) crc & ffff = 16-bit crc
    crc = zlib.crc32(base_str.encode("utf-8")) & 0xFFFF
    # 4) 04X -- make crc in HEX (16-sys) and get 4 symbols
    return f"{crc:04X}"
