import concurrent.futures
import hashlib
import hmac
import threading
import time
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.core.exceptions import (
    LicenseActivationLimitReachedError,
    LicenseAlreadyActivatedError,
    LicenseExpiredError,
    LicenseInactiveError,
    LicenseNotFoundError,
)
from src.models.license import ActivationModel, LicenseModel
from src.schemas.license import ActivationTokenPayload, DeviceDataSchema
from src.services.crypto import sign_activation_token
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

    activations = db_session.query(ActivationModel).filter_by(license_id=sample_license.id).all()

    raw_fp = generate_device_fingerprint(device_data).encode("utf-8")
    expected_db_fp = hmac.new(
        key=settings.LICENSE_SALT.encode("utf-8"),
        msg=raw_fp,
        digestmod=hashlib.sha256,
    ).hexdigest()
    expected_client_fp = hashlib.sha256(raw_fp).hexdigest()

    assert activations[0].fingerprint == expected_db_fp
    assert activations[0].os_system == device_data.os_system

    token_payload = ActivationTokenPayload(
        license_key=sample_license.key,
        fingerprint=expected_client_fp,
        expires_at=sample_license.expires_at,
        issued_at=int(activations[0].activated_at.timestamp()),
    )

    assert result == {
        "status": "success",
        "message": "License successfully activated on this device",
        "activation_token": sign_activation_token(token_payload),
    }
    assert len(activations) == 1


def test_activate_license_same_key_and_device(db_session, sample_license):
    device_data = get_device_data(sample_license.key)
    activate_device_service(db=db_session, device_data=device_data)

    with pytest.raises(LicenseAlreadyActivatedError, match="This license has already been activated"):
        activate_device_service(db=db_session, device_data=device_data)

    assert db_session.query(ActivationModel).filter_by(license_id=sample_license.id).count() == 1


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

    expected_fingerprints = set()
    for i in range(3):
        data = get_device_data(key, f"machine-{i}")
        result = activate_device_service(db=db_session, device_data=data)
        assert result["status"] == "success"

        expected_fingerprints.add(
            hmac.new(
                key=settings.LICENSE_SALT.encode("utf-8"),
                msg=generate_device_fingerprint(data).encode("utf-8"),
                digestmod=hashlib.sha256,
            ).hexdigest()
        )

    activations = db_session.query(ActivationModel).filter_by(license_id=multi_activation_license.id).all()
    assert len(activations) == 3
    assert {a.fingerprint for a in activations} == expected_fingerprints

    with pytest.raises(LicenseActivationLimitReachedError, match="Activation limit reached for this license"):
        activate_device_service(db=db_session, device_data=get_device_data(key, "machine-3"))

    assert db_session.query(ActivationModel).filter_by(license_id=multi_activation_license.id).count() == 3


def test_activate_different_licenses_same_machine(db_session):
    LicenseFactory._meta.sqlalchemy_session = db_session
    license_1 = LicenseFactory(key="AAAA-AAAA-AAAA-4366")
    license_2 = LicenseFactory(key="BBBB-BBBB-BBBB-769F")

    data = get_device_data("XXXX-XXXX-XXXX-E4C2", "id")
    fingerprint = hmac.new(
        key=settings.LICENSE_SALT.encode("utf-8"),
        msg=generate_device_fingerprint(data).encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    result_1 = activate_device_service(db=db_session, device_data=get_device_data(license_1.key, machine_id="id"))
    result_2 = activate_device_service(db=db_session, device_data=get_device_data(license_2.key, machine_id="id"))

    assert result_1["status"] == "success"
    assert result_2["status"] == "success"

    activations = db_session.query(ActivationModel).filter_by(fingerprint=fingerprint).all()

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


def test_integrity_error_not_in_unique_key_fingerprint(setup_database):
    Session = sessionmaker(bind=setup_database, autocommit=False, autoflush=False)
    with Session() as session:
        lic = LicenseModel(
            key="XXXX-XXXX-XXXX-E4C2",
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            max_activations=1,
        )
        session.add(lic)
        session.commit()
        license_key = lic.key

    data = get_device_data(license_key, machine_id="")
    data.os_system = None

    with Session() as session, pytest.raises(IntegrityError):
        activate_device_service(db=session, device_data=data)


def test_concurrent_race_activation_different_device(setup_database):
    n = 50
    Session = sessionmaker(bind=setup_database, autocommit=False, autoflush=False)
    barrier = threading.Barrier(n)

    with Session() as session:
        lic = LicenseModel(
            key="XXXX-XXXX-YYYY-E847",
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            max_activations=1,
        )
        session.add(lic)
        session.commit()
        license_id = lic.id
        license_key = lic.key

    def worker(i: int) -> tuple[str, int]:
        data = DeviceDataSchema(
            license_key=license_key,
            machine_id=f"race-{i}",
            disk_serial_number="aaa",
            os_system="Linux",
            os_release="",
            os_version="",
            cpu_arch="",
            cpu_cores=8,
            mac_address="",
            timestamp=int(time.time()),
        )

        with Session() as session:
            barrier.wait(timeout=5)
            try:
                activate_device_service(db=session, device_data=data)
                return "ok", i
            except LicenseActivationLimitReachedError:
                session.rollback()
                return "limit", i

    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
        results = list(pool.map(worker, range(n)))

    with Session() as session:
        count = session.query(ActivationModel).filter_by(license_id=license_id).count()

    ok = [r for r in results if r[0] == "ok"]
    limited = [r for r in results if r[0] == "limit"]
    assert len(ok) == 1, f"expected exactly 1 success, got {results}"
    assert len(limited) == n - 1
    assert count == 1


def test_concurrent_race_activation_same_device(setup_database):
    n = 50
    Session = sessionmaker(bind=setup_database, autocommit=False, autoflush=False)
    barrier = threading.Barrier(n)

    with Session() as session:
        lic = LicenseModel(
            key="XXXX-YYYY-YYYY-1978",
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            max_activations=1,
        )
        session.add(lic)
        session.commit()
        license_id = lic.id
        license_key = lic.key

    def worker(i: int) -> tuple[str, int]:
        data = DeviceDataSchema(
            license_key=license_key,
            machine_id="race",
            disk_serial_number="aaa",
            os_system="Linux",
            os_release="",
            os_version="",
            cpu_arch="",
            cpu_cores=8,
            mac_address="",
            timestamp=int(time.time()),
        )

        with Session() as session:
            barrier.wait(timeout=5)
            try:
                activate_device_service(db=session, device_data=data)
                return "ok", i
            except LicenseAlreadyActivatedError:
                session.rollback()
                return "limit", i

    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
        results = list(pool.map(worker, range(n)))

    with Session() as session:
        count = session.query(ActivationModel).filter_by(license_id=license_id).count()

    ok = [r for r in results if r[0] == "ok"]
    limited = [r for r in results if r[0] == "limit"]
    assert len(ok) == 1, f"expected exactly 1 success, got {results}"
    assert len(limited) == n - 1
    assert count == 1
