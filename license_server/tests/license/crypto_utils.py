import base64
import json
import os
import time

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from src.services.crypto import load_private_key


def encrypt_test_payload(
    license_key: str,
    machine_id="machine-1",
    os_system="Linux",
    os_release="abc",
    os_version="aaa",
    cpu_arch="bbb",
    cpu_cores=8,
    mac_address="ccc",
) -> dict[str, bytes]:
    raw_payload = {
        "license_key": license_key,
        "machine_id": machine_id,
        "os_system": os_system,
        "os_release": os_release,
        "os_version": os_version,
        "cpu_arch": cpu_arch,
        "cpu_cores": cpu_cores,
        "mac_address": mac_address,
        "timestamp": int(time.time()),
    }

    private_key_pem = load_private_key()
    private_key = load_pem_private_key(private_key_pem, password=None)
    public_key = private_key.public_key()

    aes_key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)

    aes_gcm = AESGCM(aes_key)
    json_data = json.dumps(raw_payload).encode("utf-8")
    cipher_data = aes_gcm.encrypt(nonce, json_data, None)

    encrypted_sync_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return {
        "encrypted_sync_key": encrypted_sync_key,
        "nonce": nonce,
        "cipher_data": cipher_data,
    }
