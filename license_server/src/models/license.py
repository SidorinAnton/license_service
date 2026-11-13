import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.core.database import Base


class LicenseModel(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now, nullable=False)

    activations = relationship("ActivationModel", back_populates="license", cascade="all, delete-orphan")


class ActivationModel(Base):
    __tablename__ = "activations"

    id = Column(Integer, primary_key=True, index=True)
    license_id = Column(Integer, ForeignKey("licenses.id"), nullable=False)

    machine_id = Column(String, index=True, nullable=False)
    os_system = Column(String, nullable=True)
    os_release = Column(String, nullable=True)
    os_version = Column(String, nullable=True)
    cpu_arch = Column(String, nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    mac_address = Column(String, nullable=True)

    activated_at = Column(DateTime, default=datetime.datetime.now, nullable=False)

    license = relationship("LicenseModel", back_populates="activations")
