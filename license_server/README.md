# Сервер сервиса (Backend-сервис) активаций лицензий

Бекенд сервиса активации лицензий.

Принимает `POST` запрос на `https://<domain>:8000/api/v1/client/activate`.

Данные:

- encrypted_sync_key -- зашифрованный AES-ключ (шифруется открытым ключом клиента)
- nones --
- cipher_data -- зашифрованные симметричным (как раз AES-ключом) данные

В процессе обрботки запроса происходит:

1) Дешифрация AES ключа -- в папке config находится **секретный** приватный ключ
2) Полученным в результате симметричным ключом осуществляется дешифрация cipher_data.
   Данные в результате представлены следующим образом:
    - license_key
    - os_system
    - os_release
    - os_version
    - cpu_arch
    - cpu_cores
    - mac_address
    - machine_id
3) Далее делается запрос в БД:
    - Существует ли такая лицензия (таблица licenses)
    - Если существует, то доступна ли она
    - Активирована ли она
4) Если все хорошо, то в БД создается запись, а клиенту возвращается ответ вида:

 ```json
 {
  "status": "success",
  "message": "License successfully activated on this device"
}
 ```

---

## Структура

```text
license_server/
├── alembic/                 # Миграции базы данных
├── config/                  # Приватный RSA ключ для расшифровки синхронного ключа (public_key.pem)
├── src/
│   ├── api/v1/              # API эндпоинты, роутеры и зависимости
│   ├── core/                # Конфигурация, настройки и подключение к БД
│   ├── models/              # SQLAlchemy модели (License, Activation)
│   ├── schemas/             # Pydantic схемы для валидации данных
│   └── services/            # Логика (лицензии, криптография)
├── tests/
├── Dockerfile
├── docker-compose.dev.yaml  # Инфраструктура для разработки
└── pyproject.toml
```

---

## Установка

Если нет uv, его надо установить ([ссылка](https://docs.astral.sh/uv/)).
Например:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 1. Установить зависимости

```shell
uv sync --dev
```

### 2. Ключи

Если нету папки `config` (или она пустая), то нужно выйти на папку назад и выполнить:

```shell
make keys
```

Так у нас создадутся публичный ключ здесь (`license_client/config/public_key.pem`)
и приватный ключ на сервере (`license_server/config/private_key.pem`).

### 3. Запуск

С докером:

```shell
docker compose -f docker-compose.dev.yaml up --build
```

Без докера:

```shell
uv run uvicorn src.main:app --reload --port 8000
```

Сервер будет доступен по адресу: `http://localhost:8000`

Swagger UI -- `http://localhost:8000/docs`

---

## Запуск тестов и линтеров

```shell
PYTHONPATH=. uv run pytest -v
```

```shell
# Проверить
uv run ruff check .

# Поправить
uv run ruff check --fix . && uv run ruff format .
```

На самом деле эти же команды собраны в том же Makefile, что и генерация ключей.
Т.е. можно выйти на папку назад и сделать:

```shell
make lint-check
make lint-fix
make test-client
```
