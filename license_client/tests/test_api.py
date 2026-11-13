import pytest
import requests

from src.api import send_activation
from src.crypto import EncryptedPayload


def test_send_activation_success(mocker):
    mock_post = mocker.patch("src.api.requests.post")

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "active", "expires_at": "2027-01-01"}
    mock_post.return_value = mock_response

    payload = EncryptedPayload(encrypted_sync_key="key", nonce="nonce", cipher_data="data")

    result = send_activation("http://localhost:8000/api/v1/activate", payload)

    assert result["status"] == "active"
    mock_post.assert_called_once_with(
        "http://localhost:8000/api/v1/activate",
        json=payload.to_dict(),
        timeout=10.0,
    )


def test_send_activation_http_error(mocker):
    mock_post = mocker.patch("src.api.requests.post")

    mock_response = mocker.MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"detail": "Invalid or expired license key"}

    http_error = requests.exceptions.HTTPError(response=mock_response)
    mock_response.raise_for_status.side_effect = http_error
    mock_post.return_value = mock_response

    with pytest.raises(RuntimeError) as exc_info:
        send_activation(
            "http://localhost:8000/api/v1/activate",
            EncryptedPayload(encrypted_sync_key="key", nonce="nonce", cipher_data="data"),
        )

        assert "Server error (400)" in str(exc_info.value)


def test_send_activation_network_error(mocker):
    mock_post = mocker.patch("src.api.requests.post")

    mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

    with pytest.raises(RuntimeError) as exc_info:
        send_activation(
            "http://localhost:8000/api/v1/activate",
            EncryptedPayload(encrypted_sync_key="key", nonce="nonce", cipher_data="data"),
        )

        assert "Network error" in str(exc_info.value)
        assert "Connection refused" in str(exc_info.value)
