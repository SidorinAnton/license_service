import hashlib
import logging
import time
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.exceptions import (
    LicenseAlreadyActivatedError,
    LicenseExpiredError,
    LicenseInactiveError,
    LicenseNotFoundError,
    TimestampExpiredError,
)
from src.models.license import ActivationModel, LicenseModel
from src.schemas.license import DeviceDataSchema

logger = logging.getLogger(__name__)

TIMESTAMP_TTL = 300


def generate_device_fingerprint(device_data: DeviceDataSchema) -> str:
    raw_str = (
        f"{device_data.machine_id}-{device_data.os_system or ''}-{device_data.os_release or ''}-"
        f"{device_data.os_version or ''}-{device_data.cpu_arch or ''}-{device_data.cpu_cores or ''}-"
        f"{device_data.mac_address or ''}-{settings.LICENSE_SALT}"
    )
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


def activate_device_service(db: Session, device_data: DeviceDataSchema):
    logger.info(
        "Processing activation request for license: %s -- (machine_id: %s)",
        device_data.license_key,
        device_data.machine_id
    )

    if abs(int(time.time()) - device_data.timestamp) > TIMESTAMP_TTL:
        raise TimestampExpiredError("Payload expired or invalid timestamp")

    license_obj = db.query(LicenseModel).filter(LicenseModel.key == device_data.license_key).first()

    if license_obj is None:
        logger.warning("License key %s not found in database", device_data.license_key)
        raise LicenseNotFoundError("License key not found")

    if not license_obj.is_active:
        logger.warning("Attempt to activate inactive license ID: %s", license_obj.id)
        raise LicenseInactiveError("License key is deactivated")

    if license_obj.expires_at and license_obj.expires_at < datetime.now():
        logger.warning("Attempt to activate expired license ID: %s", license_obj.id)
        raise LicenseExpiredError("License key has expired")

    fingerprint = generate_device_fingerprint(device_data)
    existing_activation = db.query(ActivationModel).filter(ActivationModel.license_id == license_obj.id).first()

    if existing_activation:
        if existing_activation.fingerprint == fingerprint:
            logger.info("Idempotent activation: device already registered for license ID: %s", license_obj.id)
            return {"status": "already_activated", "message": "Device is already registered for this license"}

        logger.warning("Activation conflict: license ID %s is already used by another device", license_obj.id)
        raise LicenseAlreadyActivatedError("License is already used")

    new_activation = ActivationModel(
        license_id=license_obj.id,
        fingerprint=fingerprint,
        machine_id=device_data.machine_id,
        os_system=device_data.os_system,
        os_release=device_data.os_release,
        os_version=device_data.os_version,
        cpu_arch=device_data.cpu_arch,
        cpu_cores=device_data.cpu_cores,
        mac_address=device_data.mac_address,
    )

    db.add(new_activation)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.info("IntegrityError caught (race condition handled) for license ID: %s", license_obj.id)
        return {"status": "already_activated", "message": "Device is already registered for this license"}

    logger.info("Successfully activated license ID %s for fingerprint prefix: %s...", license_obj.id, fingerprint[:8])
    return {
        "status": "success",
        "message": "License successfully activated on this device",
    }
