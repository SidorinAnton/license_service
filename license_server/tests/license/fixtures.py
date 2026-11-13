from datetime import datetime, timedelta

import pytest

from tests.license.factories import LicenseFactory


@pytest.fixture
def sample_license(db_session):
    LicenseFactory._meta.sqlalchemy_session = db_session
    return LicenseFactory(key="TEST-1234-ABCD-5678")


@pytest.fixture
def inactive_license(db_session):
    LicenseFactory._meta.sqlalchemy_session = db_session
    return LicenseFactory(is_active=False)


@pytest.fixture
def expired_license(db_session):
    LicenseFactory._meta.sqlalchemy_session = db_session
    return LicenseFactory(expires_at=datetime.now() - timedelta(days=1))
