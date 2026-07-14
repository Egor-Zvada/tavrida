# Local VK-like LLM Bot Demo

Локальный демо-сервис чат-бота с интерфейсом, похожим на страницу диалогов VK.
Реальный доступ к VK не нужен: UI имитирует мессенджер, а backend проксирует OpenAI-compatible LLM, STT и TTS API.

## Возможности

- OpenAI-compatible LLM endpoint, включая Ollama `/v1/chat/completions`.
- Whisper/OpenAI-compatible STT endpoint `/v1/audio/transcriptions`.
- OpenAI-compatible TTS endpoint `/v1/audio/speech`.
- Локальный интерфейс диалогов с отправкой текста, записью голоса, редактированием STT-текста перед отправкой и аудиоответами.
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

По умолчанию используются переданные локальные сервисы:

```text
LLM_BASE_URL=http://185.74.228.13:11434/v1
STT_BASE_URL=http://185.74.228.13:11000/v1
TTS_BASE_URL=http://185.74.228.13:10000/v1
STT_API_KEY=M00nglow
TTS_API_KEY=M00nglow
```

На указанном Ollama endpoint обнаружены модели `gpt-oss:20b` и `deepseek-r1:8b`.
По умолчанию включена `gpt-oss:20b`.
Если нужна другая модель, поменяйте `LLM_MODEL` в `.env` или в настройках интерфейса.

## Дальше

Когда появится доступ к VK, можно добавить отдельный адаптер для VK Bot API или Long Poll. Локальный UI и OpenAI-compatible адаптеры при этом останутся теми же.
