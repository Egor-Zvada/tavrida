#!/usr/bin/env python3
import base64
import json
import os
import sys
import threading
import time
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
VK_SETTINGS_PATH = ROOT / "vk_settings.local.json"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env(ROOT / ".env")


CONFIG = {
    "api_key": os.getenv("API_KEY", os.getenv("LLM_API_KEY", "")),
    "models_url": os.getenv("MODELS_URL", "https://dev.egor-zvada.ru/api/models"),
    "messages_url": os.getenv("MESSAGES_URL", "https://dev.egor-zvada.ru/api/v1/messages"),
    "llm_base_url": os.getenv("LLM_BASE_URL", "https://dev.egor-zvada.ru/api").rstrip("/"),
    "llm_api_key": os.getenv("LLM_API_KEY", os.getenv("API_KEY", "")),
    "llm_model": os.getenv("LLM_MODEL", "deepseek-v4-flash"),
    "stt_base_url": os.getenv("STT_BASE_URL", "https://dev.egor-zvada.ru/api/v1").rstrip("/"),
    "stt_api_key": os.getenv("STT_API_KEY", os.getenv("API_KEY", "")),
    "stt_model": os.getenv("STT_MODEL", "whisper-1"),
    "tts_base_url": os.getenv("TTS_BASE_URL", "https://dev.egor-zvada.ru/api/v1").rstrip("/"),
    "tts_api_key": os.getenv("TTS_API_KEY", os.getenv("API_KEY", "")),
    "tts_model": os.getenv("TTS_MODEL", "tts-1"),
    "tts_voice": os.getenv("TTS_VOICE", "alloy"),
    "host": os.getenv("HOST", "127.0.0.1"),
    "port": int(os.getenv("PORT", "8080")),
}

CITYPOLIA_SYSTEM_PROMPT = """
Ты СитиГид, дружелюбный бот поддержки настольной игры СИТИПОЛИЯ.
Задача: помочь покупателю узнать об игре, быстро подготовиться к партии, разобраться с правилами и спокойно провести первую игру.

Тон: молодежный, дружелюбный, живой, уверенный и немного кринжовый в хорошем смысле. Пиши по-русски простыми фразами, без канцелярита. Можно использовать разговорные слова и легкие мемные обороты вроде "окей", "давай", "супер", "разрулим", "залетаем", "по шагам", "имба", "без паники", "сейчас будет база". Кринж допустим, даже желателен, но без грубости, токсичности, оскорблений и перегруза эмодзи. Не называй СИТИПОЛИЮ чужим брендом и не сравнивай напрямую с другими играми, если пользователь сам не спросил.

Что говорить об игре:
- СИТИПОЛИЯ — семейная экономическая настольная игра про город, сделки, собственность, аренду, деньги и решения игроков.
- Она подходит для дружеской или семейной партии, где игроки покупают объекты, получают доход, платят расходы и стараются прийти к победе.
- Используй правила ниже как источник истины. Если пользователь спрашивает про состав коробки, точные цены конкретных Компаний или текст конкретной карточки, а этих данных нет, не выдумывай: попроси фото/текст карточки или предложи посмотреть лист правил из коробки.

Стартовое поведение:
- Если пользователь здоровается или не знает, что спросить, представься: "Привет! Я СитиГид, помощник по СИТИПОЛИИ. Могу быстро объяснить правила, провести подготовку по шагам или помочь со спорной ситуацией."
- Предложи варианты: "подготовка", "краткие правила", "помоги с ситуацией", "где купить".

Подготовка к игре:
- Если пользователь пишет "подготовка", "начать игру", "подготовь к игре" или похожее, веди строго по одному шагу.
- После каждого шага спрашивай: "Напишите 'готово', и пойдем дальше."
- Если пользователь пишет "готово", "сделал", "дальше", продолжай следующий шаг.
- Не выдавай весь список разом, если пользователь не попросил.
- Если пользователь просит "все сразу", дай компактный список всех шагов.

Базовые шаги подготовки:
1. Перетасуйте карточки «Шанс» и положите оборотной стороной вверх на соответствующий участок поля.
2. Перетасуйте карточки «Казна» и положите оборотной стороной вверх на соответствующий участок поля.
3. Каждый игрок выбирает фишку и ставит ее на клетку «СТАРТ».
4. Назначьте Банкира. Если игроков больше 5, Банкир может ограничиться только этой ролью.
5. Банкир выдает каждому игроку 1500: 2 купюры по 500, 4 по 100, 1 по 50, 1 по 20, 2 по 10, 1 по 5, 5 по 1.
6. Банкир кладет 200 в КАССУ «ДЖЕКПОТ».
7. Первый игрок определяется броском кубиков: начинает тот, у кого больше всего очков. Дальше ходят по часовой стрелке.
8. Начинайте ход: бросок двух кубиков, движение по стрелке, выполнение действия клетки.

Важные правила:
- Банк хранит карточки прав собственности, Филиалы и Предприятия, выплачивает вознаграждения, выдает ссуды под залог Компаний, собирает налоги/штрафы/ссуды/проценты. Банк не банкротится.
- За штрафные ошибки во время хода: чужая фишка, внеочередной ход, кубики покинули поле — штраф 50.
- Дубль на кубиках дает обычный ход и повторный бросок. Три дубля подряд за один ход отправляют игрока в СИЗО.
- Проход через «СТАРТ» дает 200. Остановка прямо на «СТАРТ» дает 400.
- Свободную Компанию можно купить по цене клетки. Если игрок отказался, Банкир сразу выставляет ее на аукцион; отказавшийся игрок тоже может участвовать.
- На чужой Компании владелец может потребовать ренту до броска следующего игрока. По заложенной Компании рента не взимается.
- Если все Компании цветовой группы у одного игрока, рента удваивается, но не если хотя бы одна Компания группы заложена.
- Филиалы можно строить только при владении всей цветовой группой, равномерно, максимум 4 на Компанию. Предприятие ставится после 4 Филиалов.
- Залог Компании дает половину первоначальной стоимости. Для выкупа платится сумма залога плюс 10%. Перед залогом нужно продать Филиалы/Предприятия на этой Компании.
- СИЗО: выйти можно штрафом 50, карточкой освобождения или дублем в течение до трех ходов. После трех пропусков игрок выходит и платит 25 в Банк.
- Клетка «КВИЗ»: игрок сканирует QR-код, после старта есть 60 секунд. Правильный ответ дает 100 из Банка, неверный или просрочка — игрок платит 100 в Банк. Отказаться нельзя.
- Джекпот: перед игрой в кассе 200. На клетке «ДЖЕКПОТ» игрок может сделать ставку и бросить один кубик три раза. При проигрыше ставка остается в кассе; при двух семерках игрок забирает всю кассу.
- Банкротство: если игрок должен больше, чем может покрыть активами, он выбывает. При долге Банку имущество уходит Банку и Компании продаются с аукциона; при долге игроку активы получает кредитор по правилам банкротства.

Правила:
- Если пользователь просит краткие правила, дай 5-8 пунктов.
- Если спрашивает конкретную ситуацию, отвечай по ситуации и задавай один уточняющий вопрос, если не хватает данных.
- Если пользователь прислал голосовое, оно уже распознано STT; работай с распознанным текстом как с вопросом.

Покупка:
- Если пользователь спрашивает где купить, дай ссылки:
  Ozon: https://www.ozon.ru/search/?text=%D0%A1%D0%98%D0%A2%D0%98%D0%9F%D0%9E%D0%9B%D0%98%D0%AF
  Wildberries: https://www.wildberries.ru/catalog/0/search.aspx?search=%D0%A1%D0%98%D0%A2%D0%98%D0%9F%D0%9E%D0%9B%D0%98%D0%AF
  Яндекс Маркет: https://market.yandex.ru/search?text=%D0%A1%D0%98%D0%A2%D0%98%D0%9F%D0%9E%D0%9B%D0%98%D0%AF
  Скажи проверить продавца, комплектность и отзывы.

Ответы для VK:
- При первом контакте скажи, что умеешь отвечать текстом и голосом.
- Обычно сначала отвечай текстом. Голосовой ответ будет отправлен отдельным сообщением, если включен TTS.
""".strip()

DEFAULT_VK_SETTINGS = {
    "enabled": False,
    "groupId": "",
    "token": "",
    "secret": "",
    "confirmation": "",
    "apiVersion": "5.199",
    "sendText": True,
    "sendVoice": True,
    "model": CONFIG["llm_model"],
    "systemPrompt": CITYPOLIA_SYSTEM_PROMPT,
    "systemPromptVersion": "citypolia-youth-tone-v3",
}


def read_json(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    data = handler.rfile.read(length)
    return json.loads(data.decode("utf-8"))


def write_json(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def write_text(handler, status, text):
    body = str(text).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def bearer_headers(api_key):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def load_vk_settings():
    if not VK_SETTINGS_PATH.exists():
        return dict(DEFAULT_VK_SETTINGS)
    try:
        saved = json.loads(VK_SETTINGS_PATH.read_text(encoding="utf-8"))
        settings = {**DEFAULT_VK_SETTINGS, **saved}
        prompt = settings.get("systemPrompt", "")
        if (
            saved.get("systemPromptVersion") != DEFAULT_VK_SETTINGS["systemPromptVersion"]
            and "Ты СитиГид" in prompt
            and "Клетка «КВИЗ»" not in prompt
        ):
            settings["systemPrompt"] = CITYPOLIA_SYSTEM_PROMPT
            settings["systemPromptVersion"] = DEFAULT_VK_SETTINGS["systemPromptVersion"]
        return settings
    except Exception:
        return dict(DEFAULT_VK_SETTINGS)


def save_vk_settings(payload):
    current = load_vk_settings()
    next_settings = {**current}
    for key in DEFAULT_VK_SETTINGS:
        if key == "token" and payload.get("token", "") == "":
            continue
        if key in payload:
            next_settings[key] = payload[key]
    VK_SETTINGS_PATH.write_text(json.dumps(next_settings, ensure_ascii=False, indent=2), encoding="utf-8")
    return next_settings


def public_vk_settings(settings):
    return {
        "enabled": bool(settings.get("enabled")),
        "groupId": settings.get("groupId", ""),
        "tokenPresent": bool(settings.get("token")),
        "secret": settings.get("secret", ""),
        "confirmation": settings.get("confirmation", ""),
        "apiVersion": settings.get("apiVersion", DEFAULT_VK_SETTINGS["apiVersion"]),
        "sendText": bool(settings.get("sendText", True)),
        "sendVoice": bool(settings.get("sendVoice", True)),
        "model": settings.get("model", CONFIG["llm_model"]),
        "systemPrompt": settings.get("systemPrompt", DEFAULT_VK_SETTINGS["systemPrompt"]),
        "systemPromptVersion": settings.get("systemPromptVersion", DEFAULT_VK_SETTINGS["systemPromptVersion"]),
        "callbackPath": "/api/vk/callback",
    }


def get_binary(url, timeout=60):
    request = Request(url, headers={"User-Agent": "VKDemoBot/0.1"}, method="GET")
    with urlopen(request, timeout=timeout) as response:
        return response.headers.get("Content-Type", "application/octet-stream"), response.read()


def get_raw(url, api_key, timeout=30):
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(url, headers=headers, method="GET")
    with urlopen(request, timeout=timeout) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read()


def post_json(url, api_key, payload, timeout=120):
    body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, headers=bearer_headers(api_key), method="POST")
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        content_type = response.headers.get("Content-Type", "")
        return response.status, content_type, raw


def post_form(url, fields, timeout=60):
    body = urlencode(fields).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read()


def post_multipart(url, api_key, fields, files, timeout=120):
    boundary = "----codex-vk-demo-" + uuid.uuid4().hex
    chunks = []

    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")

    for name, file_info in files.items():
        filename, content_type, data = file_info
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(
            (
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode()
        )
        chunks.append(data)
        chunks.append(b"\r\n")

    chunks.append(f"--{boundary}--\r\n".encode())
    body = b"".join(chunks)
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(url, data=body, headers=headers, method="POST")
    with urlopen(request, timeout=timeout) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read()


def decode_audio_data(data_url):
    if "," in data_url and data_url.startswith("data:"):
        meta, encoded = data_url.split(",", 1)
        mime = meta[5:].split(";")[0] or "audio/webm"
    else:
        encoded = data_url
        mime = "audio/webm"
    return mime, base64.b64decode(encoded)


def extension_for_mime(mime):
    if "wav" in mime:
        return ".wav"
    if "mpeg" in mime or "mp3" in mime:
        return ".mp3"
    if "mp4" in mime:
        return ".m4a"
    if "ogg" in mime:
        return ".ogg"
    return ".webm"


def safe_chat_id(value):
    raw = str(value or "").strip()
    if not raw:
        return "local-demo-chat"
    allowed = []
    for char in raw[:80]:
        if char.isalnum() or char in "-_":
            allowed.append(char)
        else:
            allowed.append("-")
    return "".join(allowed) or "local-demo-chat"


def call_llm(messages, model, chat_id, system_prompt):
    payload = {
        "model": model or CONFIG["llm_model"],
        "chat_id": safe_chat_id(chat_id),
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "temperature": 0.4,
        "max_tokens": 1200,
        "keep_alive": "30m",
        "stream": False,
    }
    _, _, raw = post_json(CONFIG["llm_base_url"] + "/chat/completions", CONFIG["llm_api_key"], payload)
    data = json.loads(raw.decode("utf-8"))
    return clean_assistant_text(data.get("choices", [{}])[0].get("message", {}).get("content", ""))


def clean_assistant_text(text):
    value = str(text or "")
    lower = value.lower()
    while "<think>" in lower:
        start = lower.find("<think>")
        end = lower.find("</think>", start)
        if end == -1:
            value = value[:start]
            break
        value = value[:start] + value[end + len("</think>"):]
        lower = value.lower()
    return value.strip()


def transcribe_audio_bytes(data, mime):
    ext = extension_for_mime(mime)
    _, _, raw = post_multipart(
        CONFIG["stt_base_url"] + "/audio/transcriptions",
        CONFIG["stt_api_key"],
        {"model": CONFIG["stt_model"]},
        {"file": (f"vk-voice-{int(time.time())}{ext}", mime, data)},
    )
    result = json.loads(raw.decode("utf-8"))
    return str(result.get("text") or result.get("transcription") or "").strip()


def synthesize_speech(text):
    payload = {
        "model": CONFIG["tts_model"],
        "voice": CONFIG["tts_voice"],
        "input": text,
    }
    _, content_type, raw = post_json(CONFIG["tts_base_url"] + "/audio/speech", CONFIG["tts_api_key"], payload)
    return content_type or "audio/mpeg", raw


def vk_api(settings, method, fields):
    token = settings.get("token")
    if not token:
        raise RuntimeError("VK token is not configured")
    payload = {
        **fields,
        "access_token": token,
        "v": settings.get("apiVersion") or DEFAULT_VK_SETTINGS["apiVersion"],
    }
    _, _, raw = post_form(f"https://api.vk.com/method/{method}", payload)
    data = json.loads(raw.decode("utf-8"))
    if "error" in data:
        raise RuntimeError(data["error"].get("error_msg", "VK API error"))
    return data.get("response")


def vk_send_text(settings, peer_id, message):
    return vk_api(
        settings,
        "messages.send",
        {
            "peer_id": peer_id,
            "random_id": int(time.time() * 1000),
            "message": message,
        },
    )


def vk_send_voice(settings, peer_id, text):
    mime, audio = synthesize_speech(text)
    upload = vk_api(settings, "docs.getMessagesUploadServer", {"type": "audio_message", "peer_id": peer_id})
    upload_url = upload.get("upload_url")
    if not upload_url:
        raise RuntimeError("VK did not return upload_url")
    ext = extension_for_mime(mime)
    _, _, raw = post_multipart(upload_url, "", {}, {"file": (f"answer{ext}", mime, audio)})
    uploaded = json.loads(raw.decode("utf-8"))
    saved = vk_api(settings, "docs.save", {"file": uploaded.get("file", "")})
    doc = (saved.get("audio_message") or saved.get("doc") or saved.get("docs", [{}])[0])
    owner_id = doc.get("owner_id")
    doc_id = doc.get("id")
    access_key = doc.get("access_key")
    attachment = f"doc{owner_id}_{doc_id}"
    if access_key:
        attachment += f"_{access_key}"
    return vk_api(
        settings,
        "messages.send",
        {
            "peer_id": peer_id,
            "random_id": int(time.time() * 1000) + 1,
            "attachment": attachment,
        },
    )


def extract_vk_voice_url(message):
    for attachment in message.get("attachments", []) or []:
        kind = attachment.get("type")
        payload = attachment.get(kind, {}) if kind else {}
        if kind == "audio_message":
            return payload.get("link_mp3") or payload.get("link_ogg")
    return ""


def process_vk_message(event, settings):
    message = (event.get("object") or {}).get("message") or event.get("object") or {}
    peer_id = message.get("peer_id")
    if not peer_id:
        return
    text = str(message.get("text") or "").strip()
    voice_url = extract_vk_voice_url(message)
    if voice_url:
        try:
            mime, data = get_binary(voice_url)
            text = transcribe_audio_bytes(data, mime)
        except Exception:
            vk_send_text(settings, peer_id, "Не получилось распознать голосовое сообщение. Напишите текстом, пожалуйста.")
            return
        if not text:
            vk_send_text(settings, peer_id, "Не получилось распознать голосовое сообщение. Напишите текстом, пожалуйста.")
            return
    if not text:
        vk_send_text(settings, peer_id, "Я отвечаю на текстовые и голосовые сообщения. Задайте вопрос текстом или голосом.")
        return
    answer = call_llm(
        [{"role": "user", "content": text}],
        settings.get("model") or CONFIG["llm_model"],
        f"vk-peer-{peer_id}-{uuid.uuid4().hex[:8]}",
        settings.get("systemPrompt") or DEFAULT_VK_SETTINGS["systemPrompt"],
    )
    if not answer:
        answer = "Не смог подготовить ответ. Попробуйте переформулировать вопрос."
    if settings.get("sendText", True):
        vk_send_text(settings, peer_id, answer)
    if settings.get("sendVoice", True):
        try:
            vk_send_voice(settings, peer_id, answer)
        except Exception as error:
            sys.stderr.write(f"VK voice reply failed: {error}\n")


class Handler(SimpleHTTPRequestHandler):
    server_version = "VKDemoBot/0.1"

    def translate_path(self, path):
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path == "/":
            return str(PUBLIC / "index.html")
        return str(PUBLIC / path.lstrip("/"))

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def do_GET(self):
        if self.path == "/api/config":
            public_config = {
                "modelsUrl": CONFIG["models_url"],
                "llmBaseUrl": CONFIG["llm_base_url"],
                "llmModel": CONFIG["llm_model"],
                "sttBaseUrl": CONFIG["stt_base_url"],
                "sttModel": CONFIG["stt_model"],
                "ttsBaseUrl": CONFIG["tts_base_url"],
                "ttsModel": CONFIG["tts_model"],
                "ttsVoice": CONFIG["tts_voice"],
            }
            write_json(self, 200, public_config)
            return
        if self.path == "/api/models":
            self.handle_models()
            return
        if self.path == "/api/vk/settings":
            write_json(self, 200, public_vk_settings(load_vk_settings()))
            return
        return super().do_GET()

    def do_POST(self):
        try:
            if self.path == "/api/chat":
                self.handle_chat()
            elif self.path == "/api/transcribe":
                self.handle_transcribe()
            elif self.path == "/api/tts":
                self.handle_tts()
            elif self.path == "/api/messages":
                self.handle_messages()
            elif self.path == "/api/vk/settings":
                self.handle_vk_settings()
            elif self.path == "/api/vk/callback":
                self.handle_vk_callback()
            else:
                write_json(self, 404, {"error": "Unknown API route"})
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            write_json(self, error.code, {"error": "Provider HTTP error", "detail": detail})
        except (URLError, TimeoutError) as error:
            write_json(self, 502, {"error": "Provider connection error", "detail": str(error)})
        except Exception as error:
            write_json(self, 500, {"error": "Local server error", "detail": str(error)})

    def handle_models(self):
        status, content_type, raw = get_raw(CONFIG["models_url"], CONFIG["api_key"])
        self.send_response(status)
        self.send_header("Content-Type", content_type or "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def handle_chat(self):
        payload = read_json(self)
        messages = payload.get("messages") or []
        model = payload.get("model") or CONFIG["llm_model"]
        temperature = payload.get("temperature", 0.6)
        max_tokens = payload.get("max_tokens", 1200)
        request_payload = {
            "model": model,
            "chat_id": safe_chat_id(payload.get("chat_id")),
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "keep_alive": payload.get("keep_alive", "30m"),
            "stream": False,
        }
        status, content_type, raw = post_json(
            CONFIG["llm_base_url"] + "/chat/completions",
            CONFIG["llm_api_key"],
            request_payload,
        )
        self.send_response(status)
        self.send_header("Content-Type", content_type or "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def handle_transcribe(self):
        payload = read_json(self)
        audio_data = payload.get("audio")
        if not audio_data:
            write_json(self, 400, {"error": "Missing audio"})
            return
        mime, data = decode_audio_data(audio_data)
        ext = extension_for_mime(mime)
        status, content_type, raw = post_multipart(
            CONFIG["stt_base_url"] + "/audio/transcriptions",
            CONFIG["stt_api_key"],
            {"model": payload.get("model") or CONFIG["stt_model"]},
            {"file": (f"voice-{int(time.time())}{ext}", mime, data)},
        )
        self.send_response(status)
        self.send_header("Content-Type", content_type or "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def handle_tts(self):
        payload = read_json(self)
        text = (payload.get("input") or "").strip()
        if not text:
            write_json(self, 400, {"error": "Missing input"})
            return
        request_payload = {
            "model": payload.get("model") or CONFIG["tts_model"],
            "voice": payload.get("voice") or CONFIG["tts_voice"],
            "input": text,
        }
        status, content_type, raw = post_json(
            CONFIG["tts_base_url"] + "/audio/speech",
            CONFIG["tts_api_key"],
            request_payload,
        )
        self.send_response(status)
        self.send_header("Content-Type", content_type or "audio/mpeg")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def handle_messages(self):
        payload = read_json(self)
        status, content_type, raw = post_json(CONFIG["messages_url"], CONFIG["api_key"], payload)
        self.send_response(status)
        self.send_header("Content-Type", content_type or "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def handle_vk_settings(self):
        payload = read_json(self)
        settings = save_vk_settings(payload)
        write_json(self, 200, public_vk_settings(settings))

    def handle_vk_callback(self):
        payload = read_json(self)
        settings = load_vk_settings()
        if payload.get("type") == "confirmation":
            write_text(self, 200, settings.get("confirmation", ""))
            return
        if not settings.get("enabled"):
            write_text(self, 200, "ok")
            return
        secret = settings.get("secret")
        if secret and payload.get("secret") != secret:
            write_text(self, 200, "ok")
            return
        if payload.get("type") == "message_new":
            threading.Thread(target=process_vk_message, args=(payload, settings), daemon=True).start()
        write_text(self, 200, "ok")


def main():
    if not PUBLIC.exists():
        raise SystemExit("Missing public/ directory")
    server = ThreadingHTTPServer((CONFIG["host"], CONFIG["port"]), Handler)
    print(f"VK demo bot is running at http://{CONFIG['host']}:{CONFIG['port']}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
