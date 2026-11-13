# Generate RSA (private -> server, public -> client)
keys:
	@mkdir -p license_server/config license_client/config
	openssl genrsa -out license_server/config/private_key.pem 2048
	openssl rsa -in license_server/config/private_key.pem -pubout -out license_client/config/public_key.pem

encrypt:
	ansible-vault encrypt license_server/config/private_key.pem

decrypt:
	ansible-vault decrypt license_server/config/private_key.pem


# Styles
lint-check:
	cd license_client && uv run ruff check .
	cd license_server && uv run ruff check .

lint-fix:
	cd license_client && uv run ruff check --fix . && uv run ruff format .
	cd license_server && uv run ruff check --fix . && uv run ruff format .

# Tests
test-client:
	cd license_client && PYTHONPATH=. uv run pytest -v


# Install client
install-client:
	cd license_client && uv pip install -e .
	cd license_client && uv tool install .

# Run
run-client:
	cd license_client && PYTHONPATH=. uv run python src/main.py ABCD-1234-EFGH-5678 https://localhost:8000

