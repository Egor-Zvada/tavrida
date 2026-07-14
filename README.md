# СитиГид: VK-like LLM Bot Demo

Локальный демо-сервис чат-бота поддержки для настольной игры СИТИПОЛИЯ.
UI имитирует VK Messenger, а backend проксирует OpenAI-compatible LLM, STT и TTS API.

Бот называется **СитиГид**. Он дружелюбно рассказывает об игре, помогает с правилами, проводит подготовку к партии по шагам и может подсказать ссылки на маркетплейсы.

## Возможности

- OpenAI-compatible LLM endpoint, включая Ollama `/v1/chat/completions`.
- Whisper/OpenAI-compatible STT endpoint `/v1/audio/transcriptions`.
- OpenAI-compatible TTS endpoint `/v1/audio/speech`.
- Локальный интерфейс диалогов с отправкой текста, записью голоса, редактированием STT-текста перед отправкой и аудиоответами.
- Локальное хранение истории диалогов в браузере через `localStorage`.
- Настройки VK Callback API из локальной панели настроек.
- Сценарий пошаговой подготовки к партии: бот ждет `готово` / `сделал` перед следующим шагом.
- Без прямых сравнений с чужими брендами в обычных ответах.
- Без внешних Python/npm зависимостей.

## Быстрый старт

```bash
cp .env.example .env
python3 server.py
```

Откройте:

```text
http://127.0.0.1:8080
```

## Конфигурация

По умолчанию используется HTTPS gateway без прямого IP:

```text
MODELS_URL=https://dev.egor-zvada.ru/api/models
LLM_BASE_URL=https://dev.egor-zvada.ru/api
STT_BASE_URL=https://dev.egor-zvada.ru/api/v1
TTS_BASE_URL=https://dev.egor-zvada.ru/api/v1
MESSAGES_URL=https://dev.egor-zvada.ru/api/v1/messages
```

Секретный ключ храните только в локальном `.env`:

```text
API_KEY=put-your-api-key-here
```

Через gateway доступны модели, включая `deepseek-v4-flash`, `deepseek-v4-pro`, `qwen2.5:3b` и `gpt-oss:20b`.
По умолчанию включена `deepseek-v4-flash`.
Если нужна другая модель, поменяйте `LLM_MODEL` в `.env` или в настройках интерфейса.

## Дальше

## VK Callback API

В панели настроек можно включить VK и заполнить:

```text
Group ID
Токен сообщества
Secret
Confirmation
```

Callback URL для VK показывается в интерфейсе. Для локальной машины его нужно открыть наружу через HTTPS-туннель или деплой.

Логика callback:

- `confirmation` возвращает строку подтверждения.
- `message_new` отвечает `ok` сразу, а обработку запускает в фоне.
- Текстовый вопрос уходит в LLM, затем бот отправляет текстовый ответ и, если включено, голосовое.
- Голосовое сообщение скачивается, распознается через STT, уходит в LLM, затем бот отвечает текстом и голосом.
- Если голос не распознан, бот отправляет текстовую ошибку.
