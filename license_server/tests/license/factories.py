import random
import string
import zlib
from datetime import datetime, timedelta

import factory

from src.models.license import ActivationModel, LicenseModel


def generate_valid_license_key() -> str:
    parts = ["".join(random.choices(string.ascii_uppercase + string.digits, k=4)).upper() for _ in range(3)]

    crc = zlib.crc32("".join(parts).encode("utf-8")) & 0xFFFF
    checksum = f"{crc:04X}"

    parts.append(checksum)
    return "-".join(parts)


class SQLAlchemyModelFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        abstract = True


class LicenseFactory(SQLAlchemyModelFactory):
    class Meta:
        model = LicenseModel
        sqlalchemy_session_persistence = "commit"

    key = factory.LazyFunction(generate_valid_license_key)
    is_active = True
    expires_at = factory.LazyFunction(lambda: datetime.now() + timedelta(days=30))
    max_activations = 1


class ActivationFactory(SQLAlchemyModelFactory):
    class Meta:
        model = ActivationModel
        sqlalchemy_session_persistence = "commit"

    license = factory.SubFactory(LicenseFactory)
    fingerprint = factory.Faker("sha256")
    machine_id = factory.Faker("uuid4")
    os_system = "Linux"
    cpu_cores = 8
