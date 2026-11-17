import base64
import json

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from src.collect import Device


def sign_token(payload: dict, private_pem: str) -> str:
    payload_bytes = json.dumps(payload).encode("utf-8")
    private_key = serialization.load_pem_private_key(private_pem.encode(), password=None)
    signature = private_key.sign(payload_bytes, padding.PKCS1v15(), hashes.SHA256())
    packet = {
        "payload": base64.b64encode(payload_bytes).decode(),
        "signature": base64.b64encode(signature).decode(),
    }
    return base64.b64encode(json.dumps(packet).encode()).decode()


@pytest.fixture
def rsa_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()

    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    return priv_pem, pub_pem


@pytest.fixture
def device_data():
    return Device(
        license_key="ABCD-1234-EFGH-B6B6",
        os_system="Linux",
        os_release="6.8.0-147-generic",
        os_version="#147-Ubuntu SMP PREEMPT_DYNAMIC",
        cpu_arch="x86_64",
        cpu_cores=8,
        mac_address="00:00:00:00:00:00",
        machine_id="abcdefghijklmnopqrstuwvxyz123456",
        disk_serial_number="ABCDEFGHIJKLMNO",
    )
