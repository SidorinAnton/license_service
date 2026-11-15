# Сервер сервиса (Backend-сервис) активаций лицензий

Бекенд сервиса активации лицензий.

## API Контракт

Сервер принимает `POST`-запросы на эндпоинт `/api/v1/client/activations`

**Тело запроса (JSON):**

```json
{
  "encrypted_sync_key": "<base64 строка: AES-ключ, зашифрованный RSA>",
  "nonce": "<base64 строка: вектор инициализации для AES-GCM>",
  "cipher_data": "<base64 строка: зашифрованные данные + timestamp>"
}
```

**Процесс обработки:**

1. Дешифрация `encrypted_sync_key` с помощью приватного RSA-ключа из папки `config/`
2. Дешифрация `cipher_data` с использованием полученного симметричного AES-ключа
3. Валидация формата данных и `timestamp`
4. Проверка в БД: существование лицензии, её статус (`is_active`) и срок действия (`expires_at`)
5. Сохранение записи в таблицу `activations` и возврат ответа.

**Успешный ответ:**

```json
{
  "status": "success",
  "message": "License successfully activated on this device"
}
```

**Ошибки**

| HTTP-код                   | `detail` (пример)                                                   |
|----------------------------|---------------------------------------------------------------------|
| `400 Bad Request`          | `Failed to decrypt symmetric key`                                   |
| `400 Bad Request`          | `Invalid tag or corrupted payload`                                  |
| `400 Bad Request`          | `Payload expired or invalid timestamp`                              |
| `403 Forbidden`            | `License key is deactivated`                                        |
| `403 Forbidden`            | `License key has expired`                                           |
| `404 Not Found`            | `License key not found`                                             |
| `409 Conflict`             | `License is already used`                                           |
| `422 Unprocessable Entity` | `Invalid license key format. Expected format: XXXX-XXXX-XXXX-XXXX`  |
| `422 Unprocessable Entity` | `Field required` (для `encrypted_sync_key`, `nonce`, `cipher_data`) |

**Пример ответа с ошибкой:**

```json
{
  "detail": "License is already used"
}
```

**Пример ответа с ошибкой валидации (422):**

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": [
        "license_key"
      ],
      "msg": "Value error, Invalid license key format. Expected format: XXXX-XXXX-XXXX-XXXX",
      "input": "aaa-111-"
    }
  ]
}
```

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

## Разработка и запуск

### 1. Установка зависимостей

```shell
uv sync --dev
```

### 2. Подготовка окружения

Копируем `.env.example` в `.env` и при необходимости корректируем параметры (особенно `DATABASE_URL` для локальной
разработки без Docker).

```shell
cp .env.example .env
```

Смотрим, что в папке `config/` присутствует файл `private_key.pem`. Если нет, генерируем его из корня проекта
командой `make generate-keys`.

### 3. Запуск

**Вариант А: Через uv (без Docker)**

```shell
# Важно, чтоб PostgreSQL был запущен и доступен по DATABASE_URL из .env -- в этом случае localhost
uv run alembic upgrade head          # Применить миграции
uv run uvicorn src.main:app --reload --port 8000
```

**Вариант Б: Через Docker Compose (Рекомендуется)**

```shell
# Из корня проекта:
make docker-up
```

### 4. Документация API

После запуска сервера интерактивная документация Swagger UI доступна по адресу:  
👉 [http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Работа с базой данных

Из корня:

```shell
# Создать новую миграцию после изменения моделей:
make make-migration msg="Описание изменений"

# Применить миграции:
make migrate

# Откатить последнюю миграцию:
make migrate-rollback
```

*(Для генерации тестовых данных используйте `make docker-generate-license`)*

## Тестирование

Сервер использует `pytest` с фикстурами для изолированного тестирования БД (создается и удаляется тестовая
БД `test_license_db`).

Тоже нужно проверить, что постгрес поднят.

```shell
# Запуск тестов
PYTHONPATH=. uv run pytest -v

# Запуск с отчетом о покрытии
PYTHONPATH=. uv run pytest --cov=src --cov-report=term-missing -v
```
