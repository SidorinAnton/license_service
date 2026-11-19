from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from src.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class LicenseModel(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    max_activations = Column(Integer, nullable=False, default=1, server_default="1")
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    activations = relationship("ActivationModel", back_populates="license", cascade="all, delete-orphan")


class ActivationModel(Base):
    __tablename__ = "activations"

    id = Column(Integer, primary_key=True, index=True)
    license_id = Column(Integer, ForeignKey("licenses.id"), nullable=False)
    fingerprint = Column(String, index=True, nullable=False)

    os_system = Column(String, nullable=False)
    os_release = Column(String, nullable=False)
    os_version = Column(String, nullable=False)
    cpu_arch = Column(String, nullable=False)
    cpu_cores = Column(Integer, nullable=False)

    activated_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    license = relationship("LicenseModel", back_populates="activations")

    __table_args__ = (UniqueConstraint("license_id", "fingerprint", name="uq_license_fingerprint"),)
