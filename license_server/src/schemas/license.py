from pydantic import BaseModel, field_validator


class EncryptedActivationRequest(BaseModel):
    encrypted_sync_key: str
    nones: str
    cipher_data: str


class DeviceDataSchema(BaseModel):
    license_key: str
    os_system: str
    os_release: str
    os_version: str
    cpu_arch: str
    cpu_cores: int
    mac_address: str | None = None
    machine_id: str

    @field_validator("license_key")
    @classmethod
    def case_insensitive_license_format(cls, v: str) -> str:
        err_msg = "Invalid license key format. Expected format: XXXX-XXXX-XXXX-XXXX"

        parts = v.split("-")
        if len(parts) != 4:
            raise ValueError(err_msg)
        for part in parts:
            if len(part) != 4 or not part.isalnum():
                raise ValueError(err_msg)
        return v


class ActivationResponse(BaseModel):
    status: str
    message: str
