# Сервис активаций лицензий

[![CI](https://github.com/SidorinAnton/license_service/actions/workflows/ci.yml/badge.svg)](https://github.com/SidorinAnton/license_service/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
![Coverage](https://img.shields.io/badge/coverage-80%25-brightgreen.svg)

Цель: необходимо реализовать MVP сервиса активаций лицензий.

## Архитектура

1. Заранее генерируем публичный и приватный ключ -- на клиенте публичный, на сервере -- приватный
2. Запускаем клиента на устройстве
   `PYTHONPATH=. uv run python src/main.py ABCD-1234-EFGH-5678 https://server:8000/api/v1/client/activate`
3. Скрипт собирает информацию об устройстве:
    - **os_system** -- какая ОС (линукс, винда ...)
    - **os_release** -- сборка ОС (6.8.0-147-generic)
    - **os_version** -- версия ОС (#147-Ubuntu SMP PREEMPT_DYNAMIC)
    - **cpu_arch** -- архитектура процессора (x86_64)
    - **cpu_cores** -- количество ядер
    - **mac_address** -- МАС адрес
    - **machine_id** -- уникальный идентификатор устройства
4. На клиенте генерируем одноразовый синхронный симметричный ключ (`AES-GCM`)
   Шифруем им полученные из п.2 данные вместе с лицензией -- `aes-gcm(license_key + data + timestamp)`.
   В результате алгоритма получаем также `Auth Tag`, который по сути можно назвать хеш-суммой.
   Изменение любого бита приведет к невозможности расшифровки
5. Из п.0 на клиенте у нас есть публичный ключ. Им мы шифруем сгенерированный в п.3 симметричный ключ.
   В результате на сервер идет запрос вида `pub(aes-gcm-key) + nonce + данные из п.3`
6. На сервере запрос приходит в апишку `/api/v1/client/activate`. Там происходит расшифровка ключа и данных
7. После проверки лицензии, если ключ и данные успешно добавились, в ответ возвращается успешный статус

## Структура проекта

```text
.
├── ansible.cfg                          # Конфигурация Ansible
├── license_client/                      # Клиентское приложение (CLI-тул)
│   ├── config/
│   │   └── public_key.pem               # Публичный RSA-ключ для шифрования
│   ├── src/                             # Исходный код клиента (crypto, api, collect)
│   ├── tests/
│   ├── pyproject.toml
│   └── uv.lock
├── license_server/                      # Серверная часть 
│   ├── alembic/                         # Миграции базы данных
│   ├── config/
│   │   └── private_key.pem              # Приватный RSA-ключ для дешифрования
│   ├── src/
│   │   ├── api/v1/                      # API роутеры и зависимости
│   │   ├── core/                        # Конфиги, база данных, логирование
│   │   ├── models/                      # Модели
│   │   ├── schemas/                     # Схемы
│   │   └── services/                    # Логика (криптография, лицензии)
│   ├── tests/
│   ├── docker-compose.yaml              # Production конфигурация
│   ├── docker-compose.dev.yaml          # Development конфигурация
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── uv.lock
├── Makefile                             # Единая точка входа для сборки, линтинга и тестов
├── .pre-commit-config.yaml              # Хуки контроля качества кода и безопасности
└── README.md
```

## Инструкция

### 1. Предварительные требования

- Python 3.12+
- `uv` ([ссылка](https://docs.astral.sh/uv/))
- Docker & Docker Compose

После установки uv, нужно выполнить следующую команду и на клиенте, и на сервере.

```shell
uv sync --dev
```

### 2. Ключи

Если нету папок `config` (или они пустые), то нужно выполнить:

```shell
make keys
```

Если же они есть, то приватный ключ зашифрован ансиблом. Расшифровать можно через `make decrypt`, однако для этого нужно
файл `vault.txt` в конре проекта.

Для ДЕМО в этом файле хранится значение `830fb6c0-b3db-48fe-be8f-af97299d5134`.

### 3. Pre-commit Хуки

В проекте настроен автоматический контроль качества при попытке сделать `git commit`:

1. **Проверка приватных ключей**: Блокирует коммит, если в обнаруживается паттерн `-----BEGIN PRIVATE KEY-----`
2. **Линтинг**: Автоматически проверяет код через Ruff

Для активации хуков в локальном репозитории:

```bash
pre-commit install
```

### 4. Запуск клиента и сервера

**Сервер**:

- можно запустить через uv:
  `cd license_server && PYTHONPATH=. uv run uvicorn src.main:app --reload --port 8000`
- это же `make run-server`
- а также можно через docker-compose: `make docker-up`

После запуска сервера необходимо сгенерировать тестовые сертификаты (таблица `licenses`).
Делается также либо через python (`make generate-license`), либо в докере (`docker-generate-license`).

**Клиент**:

- можно запустить через uv:
  `cd license_client && PYTHONPATH=. uv run python src/main.py ABCD-1234-EFGH-5678 http://localhost:8000/api/v1/client/activate`
- оно же `make run-client`
- можно через uv установить, а потом запустить: `make install-client`

Самый простой вариант:

```shell
make docker-up  # Поднимаем бек + бд
make docker-generate-license  # Добвляем лицензии
make run-client TEST-2026-KKEY-00..  # Запускаем скрипт, чтобы активировать лицензию
make docker-down  # Останавливает бек и бд
```

