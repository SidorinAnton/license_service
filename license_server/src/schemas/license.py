import re

from pydantic import Base64Bytes, BaseModel, field_validator

from src.services.crypto import calculate_checksum


class EncryptedActivationRequest(BaseModel):
    encrypted_sync_key: Base64Bytes
    nonce: Base64Bytes
    cipher_data: Base64Bytes


class DeviceDataSchema(BaseModel):
    license_key: str
    os_system: str
    os_release: str
    os_version: str
    cpu_arch: str
    cpu_cores: int
    mac_address: str | None
    machine_id: str | None
    disk_serial_number: str | None
    timestamp: int

    @field_validator("license_key")
    @classmethod
    def normalize(cls, v: str) -> str:
        err_msg = "Invalid license key format. Expected format: XXXX-XXXX-XXXX-XXXX"

        parts = v.upper().split("-")
        if len(parts) != 4:
            raise ValueError(err_msg)

        pattern = re.compile(r'^[A-Z0-9]{4}$')
        for part in parts:
            if len(part) != 4 or not pattern.match(part):
                raise ValueError(err_msg)

        try:
            int(parts[3], 16)
        except ValueError:
            raise ValueError("Invalid license key checksum")

        expected_checksum = calculate_checksum(parts)
        if parts[3].upper() != expected_checksum:
            raise ValueError("Invalid license key checksum")

        return v.upper()


class ActivationResponse(BaseModel):
    status: str
    message: str
