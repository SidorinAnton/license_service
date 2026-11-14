class LicenseServiceError(Exception):
    pass


class LicenseNotFoundError(LicenseServiceError):
    pass


class LicenseExpiredError(LicenseServiceError):
    pass


class LicenseInactiveError(LicenseServiceError):
    pass


class LicenseAlreadyActivatedError(LicenseServiceError):
    pass


class TimestampExpiredError(LicenseServiceError):
    pass


class CryptoError(Exception):
    pass


class DecryptionError(CryptoError):
    pass
