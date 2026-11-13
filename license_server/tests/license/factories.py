from datetime import datetime, timedelta

import factory

from src.models.license import ActivationModel, LicenseModel


class SQLAlchemyModelFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        abstract = True


class LicenseFactory(SQLAlchemyModelFactory):
    class Meta:
        model = LicenseModel
        sqlalchemy_session_persistence = "commit"

    key = factory.Faker("bothify", text="????-????-????-????", letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    is_active = True
    expires_at = factory.LazyFunction(lambda: datetime.now() + timedelta(days=30))


class ActivationFactory(SQLAlchemyModelFactory):
    class Meta:
        model = ActivationModel
        sqlalchemy_session_persistence = "commit"

    license = factory.SubFactory(LicenseFactory)
    machine_id = factory.Faker("uuid4")
    os_system = "Linux"
    cpu_cores = 8
