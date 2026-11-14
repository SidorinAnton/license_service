from fastapi import HTTPException, status
from pydantic import ValidationError

from src.schemas.license import DeviceDataSchema, EncryptedActivationRequest
from src.services.crypto import decrypt_payload


def get_verified_activation_data(raw_request: EncryptedActivationRequest) -> DeviceDataSchema:
    decrypted_dict = decrypt_payload(
        encrypted_key=raw_request.encrypted_sync_key,
        nonce=raw_request.nonce,
        cipher_data=raw_request.cipher_data,
    )
    try:
        return DeviceDataSchema(**decrypted_dict)
    except ValidationError as e:
        # detail = [
        #     {"field": ".".join(map(str, err["loc"])), "message": err["msg"]}
        #     for err in e.errors(include_context=False, include_url=False)
        # ]
        # raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=e.errors(include_context=False, include_url=False)
        )
