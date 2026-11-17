import base64
import json
import time

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.collect import Device
from src.crypto import EncryptedPayload, encrypt_payload, verify_activation_token


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


def decrypt_payload_on_server(encrypted: EncryptedPayload, private_key_pem: str) -> dict:
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
    )
    # Получаем симметричный AES ключ
    aes_key = private_key.decrypt(
        base64.b64decode(encrypted.encrypted_sync_key),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    # Расшифровываем пэйлоад через AES-GCM
    aes_gcm = AESGCM(aes_key)
    decrypted_data_bytes = aes_gcm.decrypt(
        base64.b64decode(encrypted.nonce), base64.b64decode(encrypted.cipher_data), associated_data=None
    )
    return json.loads(decrypted_data_bytes.decode("utf-8"))


def sign_token(payload: dict, private_pem: str) -> str:
    payload_bytes = json.dumps(payload).encode("utf-8")
    private_key = serialization.load_pem_private_key(private_pem.encode(), password=None)
    signature = private_key.sign(payload_bytes, padding.PKCS1v15(), hashes.SHA256())
    packet = {
        "payload": base64.b64encode(payload_bytes).decode(),
        "signature": base64.b64encode(signature).decode(),
    }
    return base64.b64encode(json.dumps(packet).encode()).decode()


def test_encrypt_and_decrypt_success(rsa_key_pair, device_data):
    priv_pem, pub_pem = rsa_key_pair

    encrypted = encrypt_payload(device_data, pub_pem)
    assert isinstance(encrypted, EncryptedPayload)

    decrypted_data = decrypt_payload_on_server(encrypted, priv_pem)

    assert decrypted_data["license_key"] == device_data.license_key
    assert decrypted_data["os_system"] == device_data.os_system
    assert decrypted_data["cpu_cores"] == device_data.cpu_cores
    assert decrypted_data["machine_id"] == device_data.machine_id
    assert "timestamp" in decrypted_data
    assert isinstance(decrypted_data["timestamp"], int)
    assert decrypted_data["timestamp"] <= int(time.time())


def test_encryption_hashsum_fails(rsa_key_pair, device_data):
    priv_pem, pub_pem = rsa_key_pair

    encrypted = encrypt_payload(device_data, pub_pem)

    cipher_bytes = list(encrypted.cipher_data)
    cipher_bytes[0] = "A" if cipher_bytes[0] != "A" else "B"
    encrypted.cipher_data = "".join(cipher_bytes)

    with pytest.raises(InvalidTag):
        decrypt_payload_on_server(encrypted, priv_pem)


def test_verify_token_ok(rsa_key_pair):
    priv_pem, pub_pem = rsa_key_pair
    payload = {
        "license_key": "ABCD-1234-EFGH-B6B6",
        "fingerprint": "aaaa",
        "expires_at": "2027-01-01",
        "issued_at": 1700000000,
    }
    activation_token = sign_token(payload, priv_pem)
    token = verify_activation_token(activation_token, pub_pem, "ABCD-1234-EFGH-B6B6")
    assert token.license_key == "ABCD-1234-EFGH-B6B6"
    assert token.fingerprint == "aaaa"
    assert token.expires_at == "2027-01-01"
    assert token.issued_at == 1700000000
    assert token.raw_payload == payload
    assert token.raw_token == activation_token


def test_verify_token_tampered(rsa_key_pair):
    priv_pem, pub_pem = rsa_key_pair
    payload = {
        "license_key": "ABCD-1234-EFGH-B6B6",
        "fingerprint": "fp123",
        "expires_at": None,
        "issued_at": 1,
    }
    activation_token = sign_token(payload, priv_pem)

    # подменяем payload внутри пакета
    packet = json.loads(base64.b64decode(activation_token))
    packet["payload"] = base64.b64encode(json.dumps({**payload, "expires_at": "2099-01-01"}).encode()).decode()
    bad = base64.b64encode(json.dumps(packet).encode()).decode()

    with pytest.raises(RuntimeError, match="Activation token signature is invalid"):
        verify_activation_token(bad, pub_pem, "ABCD-1234-EFGH-B6B6")
