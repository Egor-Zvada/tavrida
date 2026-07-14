#!/usr/bin/env python3
import base64
import json
import mimetypes
import os
import sys
import time
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"


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
    "llm_base_url": os.getenv("LLM_BASE_URL", "http://185.74.228.13:11434/v1").rstrip("/"),
    "llm_api_key": os.getenv("LLM_API_KEY", "ollama"),
    "llm_model": os.getenv("LLM_MODEL", "gpt-oss:20b"),
    "stt_base_url": os.getenv("STT_BASE_URL", "http://185.74.228.13:11000/v1").rstrip("/"),
    "stt_api_key": os.getenv("STT_API_KEY", "M00nglow"),
    "stt_model": os.getenv("STT_MODEL", "whisper-1"),
    "tts_base_url": os.getenv("TTS_BASE_URL", "http://185.74.228.13:10000/v1").rstrip("/"),
    "tts_api_key": os.getenv("TTS_API_KEY", "M00nglow"),
    "tts_model": os.getenv("TTS_MODEL", "tts-1"),
    "tts_voice": os.getenv("TTS_VOICE", "alloy"),
    "host": os.getenv("HOST", "127.0.0.1"),
    "port": int(os.getenv("PORT", "8080")),
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


def bearer_headers(api_key):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def post_json(url, api_key, payload, timeout=120):
    body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, headers=bearer_headers(api_key), method="POST")
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        content_type = response.headers.get("Content-Type", "")
        return response.status, content_type, raw


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
        return super().do_GET()

    def do_POST(self):
        try:
            if self.path == "/api/chat":
                self.handle_chat()
            elif self.path == "/api/transcribe":
                self.handle_transcribe()
            elif self.path == "/api/tts":
                self.handle_tts()
            else:
                write_json(self, 404, {"error": "Unknown API route"})
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            write_json(self, error.code, {"error": "Provider HTTP error", "detail": detail})
        except (URLError, TimeoutError) as error:
            write_json(self, 502, {"error": "Provider connection error", "detail": str(error)})
        except Exception as error:
            write_json(self, 500, {"error": "Local server error", "detail": str(error)})

    def handle_chat(self):
        payload = read_json(self)
        messages = payload.get("messages") or []
        model = payload.get("model") or CONFIG["llm_model"]
        temperature = payload.get("temperature", 0.6)
        max_tokens = payload.get("max_tokens", 700)
        request_payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
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
