from datetime import datetime, timedelta

import pytest

from tests.license.factories import LicenseFactory


@pytest.fixture
def license_factory(db_session):
    LicenseFactory._meta.sqlalchemy_session = db_session
    yield LicenseFactory


@pytest.fixture
def sample_license(license_factory):
    return LicenseFactory(key="TEST-1234-ABCD-5678")


@pytest.fixture
def inactive_license(license_factory):
    return LicenseFactory(is_active=False)


@pytest.fixture
def expired_license(license_factory):
    return LicenseFactory(expires_at=datetime.now() - timedelta(days=1))
