import datetime
import logging

from src.core.database import SessionLocal
from src.models.license import LicenseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_licenses():
    db = SessionLocal()
    try:
        created_count = 0

        for i in range(1, 11):
            key = f"TEST-2026-KKEY-{i:04d}"

            existing_license = db.query(LicenseModel).filter_by(key=key).first()
            if existing_license:
                continue

            test_license = LicenseModel(
                key=key,
                is_active=(i % 2 == 0),  # Четные активные, нечетные выключенные
                expires_at=datetime.datetime.now() + datetime.timedelta(days=30 * i),
            )

            db.add(test_license)
            created_count += 1

        db.commit()
        logger.info(f"Successfully added {created_count} new test licenses to the database.")

    except RuntimeError as e:
        db.rollback()
        logger.error(f"Failed to seed database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Starting batch database...")
    generate_licenses()
    logger.info("Seeding finished.")
