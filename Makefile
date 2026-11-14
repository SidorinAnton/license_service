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

test-client-cov:
	cd license_client && PYTHONPATH=. uv run pytest --cov=src --cov-report=term-missing --cov-report=html -v

test-server-cov:
	cd license_server && PYTHONPATH=. uv run pytest --cov=src --cov-report=term-missing --cov-report=html -v

test-all-cov: test-client-cov test-server-cov

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

ifeq (run-client,$(firstword $(MAKECMDGOALS)))
  RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(RUN_ARGS):;@:)
endif

run-client:
	$(eval CLIENT_KEY := $(or $(word 1,$(RUN_ARGS)),ABCD-1234-EFGH-5678))
	cd license_client && PYTHONPATH=. uv run python src/main.py $(CLIENT_KEY) http://localhost:8000/api/v1/client/activate

run-server:
	cd license_server && PYTHONPATH=. uv run uvicorn src.main:app --reload --port 8000

# ==========================================
# DATABASE SEEDING
# ==========================================
generate-license:
	cd license_server && PYTHONPATH=. uv run python src/generate_license.py
	docker exec -it license_postgres psql -U admin -d license_db -c "SELECT * FROM licenses;"

docker-generate-license:
	docker exec -it -e PYTHONPATH=. license_app uv run python src/generate_license.py
	docker exec -it license_postgres psql -U admin -d license_db -c "SELECT * FROM licenses;"

# ==========================================
# DOCKER COMPOSE
# ==========================================
docker-up:
	cd license_server && docker-compose -f docker-compose.dev.yaml up --build -d

docker-down:
	cd license_server && docker-compose -f docker-compose.dev.yaml down

docker-migrate:
	docker exec -it license_app uv run alembic upgrade head

docker-migrate-rollback:
	docker exec -it license_app uv run alembic downgrade -1

docker-run-tests:
	docker exec -it license_app uv run pytest -v
