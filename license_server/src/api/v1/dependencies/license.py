from fastapi import HTTPException

from src.schemas.license import DeviceDataSchema, EncryptedActivationRequest
from src.services.crypto import decrypt_payload


def get_verified_activation_data(raw_request: EncryptedActivationRequest) -> DeviceDataSchema:
    try:
        decrypted_dict = decrypt_payload(
            encrypted_key_b64=raw_request.encrypted_sync_key,
            nonce_b64=raw_request.nonce,
            cipher_data_b64=raw_request.cipher_data,
        )
        return DeviceDataSchema(**decrypted_dict)
    except RuntimeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Decryption or validation failed: {e!s}",
        )
