import base64
import json
import logging

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from src.core.config import settings
from src.core.exceptions import DecryptionError
from src.schemas.license import ActivationTokenPayload

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


def sign_activation_token(token_payload: ActivationTokenPayload) -> str:
    private_key_pem = load_private_key()
    private_key = load_pem_private_key(private_key_pem, password=None)

    payload_bytes = token_payload.model_dump_json(exclude_unset=True).encode("utf-8")

    signature = private_key.sign(
        payload_bytes,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

    packet = {
        "payload": base64.b64encode(payload_bytes).decode("utf-8"),
        "signature": base64.b64encode(signature).decode("utf-8"),
    }
    return base64.b64encode(json.dumps(packet).encode("utf-8")).decode("utf-8")
