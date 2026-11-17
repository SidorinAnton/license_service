# Клиент сервиса активаций лицензий

CLI-скрипт:

1. принимает от пользователя номер лицензии (формат XXXX-XXXX-XXXX-XXXX)
2. собирает информацию об аппаратной и программной части устройства
3. отправляет шифрованные данные на сервер, чтобы зарегистрировать лицензию
4. после ответа от сервера сохраняет активационный токен с данными в файл `license.lic`

Кроме этого скрипт можно запустить в `verify`. Тогда он вместо похода на сервер попробует прочитать и проверить
файл `license.lic`.

## Собираемые данные

- **ОС**: название, сборка и версия
- **CPU**: архитектура и количество яде
- **Сеть**: MAC-адрес основного интерфейса
- **Уникальный идентификатор устройства (Machine ID)**:
    - Linux: `/etc/machine-id`
    - Windows: `MachineGuid`
    - macOS: `IOPlatformUUID`
- **Диск**: серийный номер диска

Пример собираемых данных:

```json
{
  "license_key": "ABCD-1234-EFGH-B6B6",
  "os_system": "Linux",
  "os_release": "6.8.0-147-generic",
  "os_version": "#147-Ubuntu SMP PREEMPT_DYNAMIC Thu Sep 24 11:33:16 UTC 2026",
  "cpu_arch": "x86_64",
  "cpu_cores": 8,
  "mac_address": "00:00:00:00:00:00",
  "machine_id": "abcdefghijklmnop1234567890abcdef",
  "disk_serial_number": "ABCDEFGHIJKLMNO"
}
```

В ходе работы скрипт:

1. собирает данные устройства и добавляет к ним текущий `timestamp`
2. генерируется одноразовый симметричный ключ (`AES-256-GCM`)
3. этим симметричным ключом шифрует данные из п.1 (что гарантирует целостность и конфиденциальность, включая Auth Tag)
4. симметричный ключ шифруется публичным RSA-ключом (алгоритм OAEP с SHA-256)
5. на сервер отправляется только зашифрованный ключ, nonce и зашифрованные данные

Пример отправляемых данных на сервер:

```json
{
  "encrypted_sync_key": "CXKd3a+I4EX49hmB79hkAx5cuFMWWFg7D2twgqs5wWJHDf3f...",
  "nonce": "nTj6IK46ePBEzIU/",
  "cipher_data": "AqJabG2LTJkdM49iihlLJglEZCSAfGfNDxZ6QnrgDqNp1pSNHHvqzk6..."
}
```

Пример сохраненного токена (файла `license.lic`)

```json
{
  "activation_token": "eyJwYXlsb2FkIjogImV5SnNhV05sYm5ObFgydGxlU0k2SWxSRlUxUXRNakF5Tmkx...",
  "payload": {
    "license_key": "TEST-2026-KY03-B8B4",
    "fingerprint": "f2043f2142bb9dbf2b...",
    "expires_at": "2027-02-15T02:19:19.480987Z",
    "issued_at": 1794882472
  },
  "license_key": "TEST-2026-KY03-B8B4",
  "fingerprint": "f2043f2142bb9dbf2b...",
  "issued_at": 1794882472,
  "expires_at": "2027-02-15T02:19:19.480987Z",
  "activated_at": 1794882472,
  "server": "http://localhost:8000/api/v1/client/activations"
}
```

## Структура

```text
license_client/
├── src/
│   ├── config/         # Публичный RSA ключ для подписи синхронного ключа (public_key.pem)
│   ├── api.py          # HTTP-запросы к серверу активации
│   ├── collect.py      # Сбор информации об устройстве
│   ├── crypto.py       # Логика шифрования (AES-256-GCM + RSA)
│   ├── commands.py     # Обработки активации и верификации
│   ├── storage.py      # Обработка файлов (pub.pem, license.lic)
│   └── main.py         # Точка входа (argparse)
├── tests/
├── pyproject.toml
└── uv.lock 
```

## Запуск

### 1. Установка зависимостей

Должен быть установлен [`uv`](https://docs.astral.sh/uv/).

```shell
uv sync --dev
```

### 2. Подготовка ключей

Если файл `config/public_key.pem` отсутствует, его надо сгенерировать из корня проекта:

```shell
make generate-keys
```

### 3. Использование CLI

#### activate

**Проверка формата и сухой прогон (без отправки на сервер):**
Полезно для отладки и проверки того, какие именно данные будут отправлены

```shell
PYTHONPATH=. uv run python src/main.py activate --dry-run ABCD-1234-EFGH-B6B6 http://localhost:8000/api/v1/client/activations
```

**Полноценная активация:**

```shell
PYTHONPATH=. uv run python src/main.py activate ABCD-1234-EFGH-B6B6 http://localhost:8000/api/v1/client/activations
```

*(Альтернативно, из корня проекта можно использовать: `make run-client-activation <LICENSE_KEY>`)*

#### verify

После активации скрипт создаст файл `license.lic`. Его можно проверить выполнив команду:

```shell
PYTHONPATH=. uv run python src/main.py verify
```

## Тесты и линтеры

```shell
# Запуск тестов
PYTHONPATH=. uv run pytest -v

# Проверка стиля кода
uv run ruff check .

# Автоматическое исправление и форматирование
uv run ruff check --fix . && uv run ruff format .
```

Все эти команды также доступны через `Makefile` в корне проекта (`make test-client`, `make lint-fix`).
