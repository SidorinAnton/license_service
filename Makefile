# ==========================================
# KEYS
# ==========================================
# Generate RSA (private -> server, public -> client)
keys:
	@mkdir -p license_server/config license_client/config
	openssl genrsa -out license_server/config/private_key.pem 2048
	openssl rsa -in license_server/config/private_key.pem -pubout -out license_client/config/public_key.pem

encrypt:
	ansible-vault encrypt license_server/config/private_key.pem

decrypt:
	ansible-vault decrypt license_server/config/private_key.pem


# ==========================================
# LINT
# ==========================================
lint-check:
	cd license_client && uv run ruff check .
	cd license_server && uv run ruff check .

lint-fix:
	cd license_client && uv run ruff check --fix . && uv run ruff format .
	cd license_server && uv run ruff check --fix . && uv run ruff format .

# ==========================================
# TESTS
# ==========================================
test-client:
	cd license_client && PYTHONPATH=. uv run pytest -v

test-server:
	cd license_server && PYTHONPATH=. uv run pytest -v

test-all: test-client test-server


# ==========================================
# MIGRATIONS (Server)
# ==========================================
make-migration:
	cd license_server && uv run alembic revision --autogenerate -m "$(msg)"

migrate:
	cd license_server && uv run alembic upgrade head

migrate-rollback:
	cd license_server && uv run alembic downgrade -1


# ==========================================
# RUN
# ==========================================
install-client:
	cd license_client && uv pip install -e .
	cd license_client && uv tool install .

run-client:
	cd license_client && PYTHONPATH=. uv run python src/main.py ABCD-1234-EFGH-5678 https://localhost:8000/api/v1/client/activate


run-server:
	cd license_server && PYTHONPATH=. uv run uvicorn src.main:app --reload --port 8000


# ==========================================
# DOCKER COMPOSE
# ==========================================
docker-up:
	cd license_server && docker-compose -f docker-compose.dev.yaml up --build -d

docker-down:
	cd license_server && docker-compose -f docker-compose.dev.yaml down

docker-migrate:
	cd license_server && docker exec -it license_app uv run alembic upgrade head

docker-migrate-rollback:
	cd license_server && docker exec -it license_app uv run alembic downgrade -1
