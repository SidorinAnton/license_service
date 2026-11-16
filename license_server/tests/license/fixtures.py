from datetime import datetime, timedelta

import pytest

from tests.license.factories import LicenseFactory


@pytest.fixture
def license_factory(db_session):
    LicenseFactory._meta.sqlalchemy_session = db_session
    try:
        yield LicenseFactory
    finally:
        LicenseFactory._meta.sqlalchemy_session = None


@pytest.fixture
def sample_license(license_factory):
    return license_factory(key="TEST-1234-ABCD-4CE4")


@pytest.fixture
def multi_activation_license(license_factory):
    return license_factory(key="TEST-5678-ABCD-C91A", max_activations=3)


@pytest.fixture
def inactive_license(license_factory):
    return license_factory(is_active=False)


@pytest.fixture
def expired_license(license_factory):
    return license_factory(expires_at=datetime.now() - timedelta(days=1))
