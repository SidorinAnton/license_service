import logging
from datetime import UTC, datetime, timedelta

from src.core.database import SessionLocal
from src.core.utils import calculate_checksum
from src.models.license import LicenseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_licenses():
    db = SessionLocal()
    try:
        created_count = 0

        for i in range(1, 11):
            part1 = "TEST"
            part2 = "2026"
            part3 = f"KY{i:02d}"

            checksum = calculate_checksum([part1, part2, part3])
            key = f"{part1}-{part2}-{part3}-{checksum}"

            existing_license = db.query(LicenseModel).filter_by(key=key).first()
            if existing_license:
                continue

            test_license = LicenseModel(
                key=key,
                is_active=(i < 8),
                expires_at=datetime.now(UTC) + timedelta(days=30 * i),
                max_activations=3 if i == 3 else 1,
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
