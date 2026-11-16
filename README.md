# Сервис активации лицензий

[![CI](https://github.com/SidorinAnton/license_service/actions/workflows/ci.yml/badge.svg)](https://github.com/SidorinAnton/license_service/actions/workflows/ci.yml)
[![OS](https://img.shields.io/badge/OS-Linux%20%7C%20Windows%20%7C%20macOS-blue)](https://github.com/SidorinAnton/license_service/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
![Coverage](https://img.shields.io/badge/coverage-80%25-brightgreen.svg)

> **Цель**: необходимо реализовать MVP сервиса активаций лицензий.

## Архитектура

1. **Генерация ключей до запуска**: Заранее генерируется пара RSA-ключей. Публичный ключ распространяется с клиентом,
   приватный хранится в секрете на сервере
2. **Сбор данных клиентом**: Клиентский скрипт собирает информацию об устройстве
3. **Формирование запроса клиентом**:
    - Генерируется одноразовый симметричный ключ (`AES-256-GCM`)
    - Данные устройства и лицензионный ключ шифруются этим симметричным ключом вместе с временной меткой (`timestamp`)
    - Сам симметричный ключ шифруется публичным RSA-ключом
4. **Отправка**: На сервер отправляются данные вида `RSA(aes_key) + nonce + AES_GCM(data + timestamp)`
5. **Серверная обработка**: Сервер расшифровывает симметричный ключ приватным RSA-ключом, затем расшифровывает данные.
   Проверяется валидность лицензии, её срок действия и отсутствие конфликтов активации
6. **Ответ**: Клиент получает статус успешной активации или ошибку

Более подробная информация о клиенте и сервере [здесь](license_client%2FREADME.md) и [здесь](license_server%2FREADME.md)
соответственно.

## Что можно улучшить в будущем

1. **Система аутентификации и ключевые пары:** выпуск индивидуальных пар асимметричных ключей для каждой отдельной
   лицензии или клиента
2. **Продвинутое управление лицензиями:**
    - отзыв лицензий (revoke) и их принудительная блокировка
    - лимитирование устройств (схема "1 лицензия = N активных устройств")
    - полноценная админка
3. **Офлайн-активация**
4. **Гибкий Hardware Fingerprint:** более гибкая настройка фингерпринта (чтобы обновление системы не ломало активацию)
5. **Нотификация**
6. **Аудит-лог**

## Структура проекта

```text
.
├── .github/workflows/ci.yml       # Настройки CI/CD (линтинг, тесты)
├── .pre-commit-config.yaml        # Pre-commit хуки (безопасность, ruff)
├── ansible.cfg                    # Конфигурация Ansible для работы с vault
├── Makefile                       # Единая точка входа для сборки, тестов и запуска
├── README.md
│
├── license_client/                # Клиентское приложение (CLI)
│   ├── config/public_key.pem      # Публичный RSA-ключ
│   ├── src/                       # Исходный код (crypto, api, collect, main)
│   ├── tests/                     # Тесты клиента
│   ├── README.md
│   ├── pyproject.toml             # Зависимости клиента
│   └── uv.lock                    # Фиксированные зависимости
│
└── license_server/                # Серверная часть
    ├── config/private_key.pem     # Приватный RSA-ключ (зашифрован через Ansible Vault)
    ├── src/                       # Исходный код (api, core, models, schemas, services)
    ├── alembic/                   # Миграции базы данных
    ├── tests/                     # Тесты сервера
    ├── README.md
    ├── Dockerfile                 # Файл сборки бекенда
    ├── docker-compose.yaml        # Инфраструктура для прода (находится в разработке)
    ├── docker-compose.dev.yaml    # Инфраструктура для локальной разработки
    ├── .env.prod.example          # Пример переменных окружения для прода (находится в разработке)
    ├── .env.example               # Пример переменных окружения для локальной разработки
    ├── alembic.ini                # Настройки для миграций
    ├── pyproject.toml             # Зависимости сервера
    └── uv.lock                    # Фиксированные зависимости
```

## Быстрый старт

### 1. Предварительные требования

- Python 3.12+ и менеджер пакетов [`uv`](https://docs.astral.sh/uv/)
- Пре-коммит 
- Docker & Docker Compose (для запуска сервера)

### 2. Установка зависимостей

```shell
cd license_client && uv sync --dev
cd ../license_server && uv sync --dev
cd ..
```

### 3. Генерация ассиметричных ключей

Если папки `config` пусты или отсутствуют, генерируем ключи:

```shell
make generate-keys
```

*(Для демо-целей приватный ключ зашифрован через Ansible Vault. Пароль для
расшифровки: `830fb6c0-b3db-48fe-be8f-af97299d5134`. При необходимости нужно ~~(разбить стекло)~~
создать в корне файл `vault.txt`, положить туда этот ключ и использовать `make decrypt` и `make encrypt`).*

### 4. Запуск сервера через Docker (Рекомендуемый способ)

```shell
# Для демо!!!  (в реальном репозитории тут не будет ключа расшифровки)
echo '830fb6c0-b3db-48fe-be8f-af97299d5134' > vault.txt

# Поднимаем бек + бд
make docker-up  # Тут же произойдет decrypt и копирования .env

# Добавляем лицензии в БД (например, TEST-2026-KY01-D998)
make docker-generate-license

# Запускаем скрипт, чтобы активировать лицензию
make run-client TEST-2026-KY01-D998
make run-client TEST-2026-KY02-8822

# Останавливает бек и бд
make docker-down 
```

## Разработка и тестирование

Проект использует `Makefile` для единой точки входа:

```shell
make generate-keys             # Генерация публичного (на клиенте) и приватного (на сервере) ключа
make encrypt                   # Шифровка приватного ключа сервера через ansible-vault
make decrypt                   # Дешифровка приватного ключа сервера через ansible-vault

make lint-check                # Проверка кода через Ruff
make lint-fix                  # Автоматическое исправление и форматирование кода
make test-client               # Запуск тестов клиента через uv (нужен постгрес -- см make start-db)
make test-server               # Запуск тестов сервера через uv (нужен постгрес -- см make start-db)
make test-all                  # Запуск всех тестов (test-client + test-server)
make test-client-cov           # Аналогично test-client, но с покрытием
make test-server-cov           # Аналогично test-server, но с покрытием
make test-all-cov              # Запуск тестов с отчетом о покрытии (test-client-cov + test-server-cov)

make make-migration msg="..."  # Создание новой миграции (нужен постгрес -- см make start-db)
make migrate                   # Применение миграций Alembic (нужен постгрес -- см make start-db)
make migrate-rollback          # Откат миграции (нужен постгрес -- см make start-db)

make start-db                  # Отдельное поднятие конкретно постгреса в докере (без бэкенда)

make install-client            # Установка клиента на компьютер через uv
make run-client <license key>  # Запуск клиента через uv
make run-server                # Запуск сервера через uv

make generate-license          # Добавление отладочных лицензий в базу данных через uv
make docker-generate-license   # Добавление отладочных лицензий в базу данных через докер

make docker-up                 # Запуск базы данных и сервера через докер
make docker-down               # Остановка базы данных и сервера через докер
make docker-migrate            # Применение миграций в докере
make docker-migrate-rollback   # Откат миграций в докере
make docker-run-tests          # Запуск тестов через докер
```

### Pre-commit Хуки

В проекте настроен автоматический контроль качества при попытке сделать `git commit`:

1. **Проверка приватных ключей**: Блокирует коммит, если обнаруживается паттерн `-----BEGIN PRIVATE KEY-----`
2. **Линтинг**: Автоматически проверяет код через Ruff

Для активации хуков в локальном репозитории нужно выполнить команду:

```shell
pre-commit install
```
