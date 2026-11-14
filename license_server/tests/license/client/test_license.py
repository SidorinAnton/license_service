import time

import pytest

from src.core.exceptions import (
    LicenseAlreadyActivatedError,
    LicenseExpiredError,
    LicenseInactiveError,
    LicenseNotFoundError,
)
from src.models.license import ActivationModel
from src.schemas.license import DeviceDataSchema
from src.services.license import activate_device_service
from tests.license.factories import LicenseFactory


def get_device_data(license_key, machine_id="machine-1") -> DeviceDataSchema:
    return DeviceDataSchema(
        license_key=license_key,
        machine_id=machine_id,
        os_system="Linux",
        os_release="",
        os_version="",
        cpu_arch="",
        cpu_cores=8,
        mac_address="",
        timestamp=int(time.time()),
    )


def test_activate_license_success(db_session, sample_license):
    device_data = get_device_data(sample_license.key)
    result = activate_device_service(db=db_session, device_data=device_data)

    assert result == {
        "status": "success",
        "message": "License successfully activated on this device",
    }

    activations = db_session.query(ActivationModel).filter_by(license_id=sample_license.id).all()

    assert len(activations) == 1
    assert activations[0].machine_id == device_data.machine_id
    assert activations[0].os_system == device_data.os_system


def test_activate_license_same_key_and_device(db_session, sample_license):
    device_data = get_device_data(sample_license.key)
    activate_device_service(db=db_session, device_data=device_data)
    result = activate_device_service(db=db_session, device_data=device_data)
    assert result == {"status": "already_activated", "message": "Device is already registered for this license"}
    assert (
        db_session.query(ActivationModel)
        .filter_by(license_id=sample_license.id, machine_id=device_data.machine_id)
        .count()
        == 1
    )


def test_activate_license_not_found(db_session):
    device_data = get_device_data("1111-1111-1111-1111")
    with pytest.raises(LicenseNotFoundError, match="License key not found"):
        activate_device_service(db=db_session, device_data=device_data)


def test_activate_license_inactive(db_session, inactive_license):
    device_data = get_device_data(inactive_license.key)
    with pytest.raises(LicenseInactiveError, match="License key is deactivated"):
        activate_device_service(db=db_session, device_data=device_data)


def test_activate_license_expired(db_session, expired_license):
    device_data = get_device_data(expired_license.key)
    with pytest.raises(LicenseExpiredError, match="License key has expired"):
        activate_device_service(db=db_session, device_data=device_data)


def test_activate_license_limit_exceeded(db_session, sample_license):
    device_data_1 = get_device_data(sample_license.key, "machine-1")
    device_data_2 = get_device_data(sample_license.key, "machine-2")
    activate_device_service(db=db_session, device_data=device_data_1)
    with pytest.raises(LicenseAlreadyActivatedError, match="License is already used"):
        activate_device_service(db=db_session, device_data=device_data_2)


def test_activate_different_licenses_same_machine(
    db_session,
):
    LicenseFactory._meta.sqlalchemy_session = db_session
    license_1 = LicenseFactory(key="AAAA-AAAA-AAAA-AAAA")
    license_2 = LicenseFactory(key="BBBB-BBBB-BBBB-BBBB")

    result_1 = activate_device_service(db=db_session, device_data=get_device_data(license_1.key, machine_id="id"))
    result_2 = activate_device_service(db=db_session, device_data=get_device_data(license_2.key, machine_id="id"))

    assert result_1["status"] == "success"
    assert result_2["status"] == "success"

    activations = db_session.query(ActivationModel).filter_by(machine_id="id").all()

    assert len(activations) == 2
    assert {act.license.key for act in activations} == {"AAAA-AAAA-AAAA-AAAA", "BBBB-BBBB-BBBB-BBBB"}
