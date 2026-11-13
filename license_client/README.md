# Клиент сервиса активаций лицензий

CLI-скрипт, который:

1) принимает от пользователя номер лицензии (формат XXXX-XXXX-XXXX-XXXX)
2) собирает информацию об аппаратной и программной части устройства
3) отправляет шифрованные данные на сервер, чтобы зарегистрировать лицензию

Данные, которые пытается собрать скрипт:

- ОС, её сборка и версия
- CPU: архитектура и количество ядер
- MAC-адрес
- Идентификатор машины (Machine ID)
    - На Linux это обычно `/etc/machine-id`
    - на Windows -- `MachineGuid` в реестре
    - на macOS -- `IOPlatformUUID`

Клиент запускается с 2 аргументами -- номер лицензии и адрес сервера. Также можно запустить `dry-run`.

В ходе работы скрипт:

1) собирает данные
2) генерирует симметричный ключ (AES-GCM)
3) шифрует симметричным ключом данные из п.1
4) публичным ключом шифрует ключ из п.2
5) отправляет это на сервер, где происходит дешифрация и регистрация лицензии

---

## Структура

```text
license_client/
├── config/             # Публичный RSA ключ для подписи синхронного ключа (public_key.pem)
├── src/
│   ├── api.py          # функции для HTTP запроса к серверу 
│   ├── collect.py      # функции для сбора инфы об устройстве
│   ├── crypto.py       # функции для шифрования полученных данных (AES-256-GCM + RSA)
│   └── main.py         # точка входа (CLI + argparse)
├── tests/
├── Dockerfile
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

### 3. Запустить без докера

```shell
# Без отправки на сервер
PYTHONPATH=. uv run python src/main.py --dry-run ABCD-1234-EFGH-5678 http://localhost:8000

# Полноценный запуск
PYTHONPATH=. uv run python src/main.py ABCD-1234-EFGH-5678 http://localhost:8000
```

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


