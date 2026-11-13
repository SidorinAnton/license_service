import requests

from src.crypto import EncryptedPayload


def send_activation(url: str, payload: EncryptedPayload) -> dict:
    try:
        response = requests.post(url, json=payload.to_dict(), timeout=10.0)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Server error ({e.response.status_code}): {e.response.text}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error: failed to connect to server at {url}. Details: {e}")
