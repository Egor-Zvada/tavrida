# Local VK-like LLM Bot Demo

Локальный демо-сервис чат-бота с интерфейсом, похожим на страницу диалогов VK.
Реальный доступ к VK не нужен: UI имитирует мессенджер, а backend проксирует OpenAI-compatible LLM, STT и TTS API.

## Возможности

- OpenAI-compatible LLM endpoint, включая Ollama `/v1/chat/completions`.
- Whisper/OpenAI-compatible STT endpoint `/v1/audio/transcriptions`.
- OpenAI-compatible TTS endpoint `/v1/audio/speech`.
- Локальный интерфейс диалогов с отправкой текста, записью голоса, редактированием STT-текста перед отправкой и аудиоответами.
- Локальное хранение истории диалогов в браузере через `localStorage`.
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

На указанном Ollama endpoint обнаружены модели `qwen2.5:3b`, `gpt-oss:20b` и `deepseek-r1:8b`.
По умолчанию включена `qwen2.5:3b`: она заметно быстрее на CPU и лучше подходит для русскоязычного VK-бота.
Если нужна другая модель, поменяйте `LLM_MODEL` в `.env` или в настройках интерфейса.

## Дальше

Когда появится доступ к VK, можно добавить отдельный адаптер для VK Bot API или Long Poll. Локальный UI и OpenAI-compatible адаптеры при этом останутся теми же.
