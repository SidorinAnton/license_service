from pydantic import Base64Bytes, BaseModel, field_validator


class EncryptedActivationRequest(BaseModel):
    encrypted_sync_key: Base64Bytes
    nonce: Base64Bytes
    cipher_data: Base64Bytes


class DeviceDataSchema(BaseModel):
    license_key: str
    os_system: str | None = None
    os_release: str | None = None
    os_version: str | None = None
    cpu_arch: str | None = None
    cpu_cores: int | None = None
    mac_address: str | None = None
    machine_id: str
    timestamp: int

    @field_validator("license_key")
    @classmethod
    def normalize(cls, v: str) -> str:
        err_msg = "Invalid license key format. Expected format: XXXX-XXXX-XXXX-XXXX"

        parts = v.split("-")
        if len(parts) != 4:
            raise ValueError(err_msg)
        for part in parts:
            if len(part) != 4 or not part.isalnum():
                raise ValueError(err_msg)
        return v.upper()


class ActivationResponse(BaseModel):
    status: str
    message: str
