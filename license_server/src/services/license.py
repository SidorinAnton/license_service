from datetime import datetime

from sqlalchemy.orm import Session

from src.models.license import ActivationModel, LicenseModel
from src.schemas.license import DeviceDataSchema


def activate_device_service(db: Session, device_data: DeviceDataSchema):
    license_obj = db.query(LicenseModel).filter(LicenseModel.key == device_data.license_key).first()

    if license_obj is None:
        raise ValueError("License key not found")

    if not license_obj.is_active:
        raise ValueError("License key is deactivated")

    if license_obj.expires_at and license_obj.expires_at < datetime.now():
        raise ValueError("License key has expired")

    existing_activation = db.query(ActivationModel).filter(ActivationModel.license_id == license_obj.id).first()

    if existing_activation:
        if existing_activation.machine_id == device_data.machine_id:
            return {"status": "already_activated", "message": "Device is already registered for this license"}
        raise ValueError("License is already used")

    new_activation = ActivationModel(
        license_id=license_obj.id,
        machine_id=device_data.machine_id,
        os_system=device_data.os_system,
        os_release=device_data.os_release,
        os_version=device_data.os_version,
        cpu_arch=device_data.cpu_arch,
        cpu_cores=device_data.cpu_cores,
        mac_address=device_data.mac_address,
    )

    db.add(new_activation)
    db.commit()

    return {
        "status": "success",
        "message": "License successfully activated on this device",
    }
