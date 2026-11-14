from fastapi import Request, status
from fastapi.responses import JSONResponse

from src.core.exceptions import (
    DecryptionError,
    LicenseAlreadyActivatedError,
    LicenseExpiredError,
    LicenseInactiveError,
    LicenseNotFoundError,
    TimestampExpiredError,
)

EXCEPTION_MAP: dict[type[Exception], tuple[int, str]] = {
    DecryptionError: (status.HTTP_400_BAD_REQUEST, "Cannot decrypt payload"),
    LicenseNotFoundError: (status.HTTP_404_NOT_FOUND, "License not found"),
    LicenseExpiredError: (status.HTTP_403_FORBIDDEN, "License expired"),
    LicenseInactiveError: (status.HTTP_403_FORBIDDEN, "License inactive"),
    LicenseAlreadyActivatedError: (status.HTTP_409_CONFLICT, "Activation limit reached"),
    TimestampExpiredError: (status.HTTP_400_BAD_REQUEST, "Timestamp expired"),
}


def register_exception_handlers(app):
    def make_handler(st_code: int, msg: str):
        def error_handler(request: Request, exc: Exception):
            return JSONResponse(
                status_code=st_code,
                content={"detail": str(exc) or msg},
            )

        return error_handler

    for exc_class, (code, message) in EXCEPTION_MAP.items():
        app.add_exception_handler(exc_class, make_handler(code, message))
