import time

import pytest

from src.core.exceptions import (
    LicenseActivationLimitReachedError,
    LicenseAlreadyActivatedError,
    LicenseExpiredError,
    LicenseInactiveError,
    LicenseNotFoundError,
)
from src.models.license import ActivationModel
from src.schemas.license import DeviceDataSchema
from src.services.license import activate_device_service, generate_device_fingerprint
from tests.license.factories import LicenseFactory


def get_device_data(license_key, machine_id="machine-1") -> DeviceDataSchema:
    return DeviceDataSchema(
        license_key=license_key,
        machine_id=machine_id,
        disk_serial_number="aaa",
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

    with pytest.raises(LicenseAlreadyActivatedError, match="This license has already been activated"):
        activate_device_service(db=db_session, device_data=device_data)

    assert (
        db_session.query(ActivationModel)
        .filter_by(license_id=sample_license.id, machine_id=device_data.machine_id)
        .count()
        == 1
    )


def test_activate_license_idempotent_when_limit_reached(db_session, multi_activation_license):
    key = multi_activation_license.key
    for i in range(3):
        activate_device_service(db=db_session, device_data=get_device_data(key, f"machine-{i}"))

    with pytest.raises(LicenseAlreadyActivatedError, match="This license has already been activated"):
        activate_device_service(db=db_session, device_data=get_device_data(key, "machine-1"))

    assert db_session.query(ActivationModel).filter_by(license_id=multi_activation_license.id).count() == 3


def test_activate_license_not_found(db_session):
    device_data = get_device_data("1111-1111-1111-BA9F")
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


def test_activate_license_limit_reached_default_one(db_session, sample_license):
    device_data_1 = get_device_data(sample_license.key, "machine-1")
    device_data_2 = get_device_data(sample_license.key, "machine-2")

    activate_device_service(db=db_session, device_data=device_data_1)
    with pytest.raises(LicenseActivationLimitReachedError, match="Activation limit reached for this license"):
        activate_device_service(db=db_session, device_data=device_data_2)


def test_activate_license_multiple_activations_allowed(db_session, multi_activation_license):
    key = multi_activation_license.key

    for i in range(3):
        result = activate_device_service(db=db_session, device_data=get_device_data(key, f"machine-{i}"))
        assert result["status"] == "success"

    activations = db_session.query(ActivationModel).filter_by(license_id=multi_activation_license.id).all()
    assert len(activations) == 3
    assert {a.machine_id for a in activations} == {"machine-0", "machine-1", "machine-2"}

    with pytest.raises(LicenseActivationLimitReachedError, match="Activation limit reached for this license"):
        activate_device_service(db=db_session, device_data=get_device_data(key, "machine-3"))

    assert db_session.query(ActivationModel).filter_by(license_id=multi_activation_license.id).count() == 3


def test_activate_different_licenses_same_machine(db_session):
    LicenseFactory._meta.sqlalchemy_session = db_session
    license_1 = LicenseFactory(key="AAAA-AAAA-AAAA-4366")
    license_2 = LicenseFactory(key="BBBB-BBBB-BBBB-769F")

    result_1 = activate_device_service(db=db_session, device_data=get_device_data(license_1.key, machine_id="id"))
    result_2 = activate_device_service(db=db_session, device_data=get_device_data(license_2.key, machine_id="id"))

    assert result_1["status"] == "success"
    assert result_2["status"] == "success"

    activations = db_session.query(ActivationModel).filter_by(machine_id="id").all()

    assert len(activations) == 2
    assert {act.license.key for act in activations} == {"AAAA-AAAA-AAAA-4366", "BBBB-BBBB-BBBB-769F"}


def test_generate_device_fingerprint_consistency():
    device_data_1 = get_device_data("XXXX-XXXX-XXXX-E4C2", machine_id="machine-A")
    device_data_2 = get_device_data("XXXX-XXXX-XXXX-E4C2", machine_id="machine-A")
    device_data_3 = get_device_data("XXXX-XXXX-XXXX-E4C2", machine_id="machine-B")

    fp_1 = generate_device_fingerprint(device_data_1)
    fp_2 = generate_device_fingerprint(device_data_2)
    fp_3 = generate_device_fingerprint(device_data_3)

    assert fp_1 == fp_2
    assert fp_1 != fp_3


def test_integrity_error_not_in_unique_key_fingerprint(db_session, sample_license):
    data = get_device_data(sample_license.key, machine_id="")
    data.machine_id = None
