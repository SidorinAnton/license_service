import logging
import re


class SecureFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.patterns = [
            (re.compile(r'(password|secret|key|token)=["\']?([^"\'\s]+)["\']?', re.IGNORECASE), r"\1=***REDACTED***"),
            (
                re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----"),
                "***PRIVATE_KEY_REDACTED***",
            ),
            (re.compile(r"\b[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}\b"), "****-****-****-****"),
        ]

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)

        for pattern, replacement in self.patterns:
            message = pattern.sub(replacement, message)

        return message


def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(SecureFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [handler]
