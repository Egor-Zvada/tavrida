const state = {
  config: null,
  activeDialogId: "ai",
  mediaRecorder: null,
  recordedChunks: [],
  messages: [
    {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "Привет. Я локальный демо-бот: пишите текстом или нажмите микрофон. Голос я распознаю в поле ввода, чтобы вы могли поправить текст перед отправкой.",
    },
  ],
};

const dialogs = [
  { id: "ai", title: "AI ассистент", preview: "OpenAI-compatible demo", time: "сейчас", initials: "AI" },
  { id: "support", title: "VK demo support", preview: "Локальный показ без доступа к VK", time: "10:31", initials: "VK" },
  { id: "ops", title: "LLM / STT / TTS", preview: "Ollama, Whisper, Speech API", time: "09:48", initials: "API" },
];

const els = {
  dialogList: document.querySelector("#dialogList"),
  dialogSearch: document.querySelector("#dialogSearch"),
  messages: document.querySelector("#messages"),
  input: document.querySelector("#messageInput"),
  send: document.querySelector("#sendButton"),
  record: document.querySelector("#recordButton"),
  ttsToggle: document.querySelector("#ttsToggle"),
  settingsButton: document.querySelector("#settingsButton"),
  settingsPanel: document.querySelector("#settingsPanel"),
  closeSettings: document.querySelector("#closeSettings"),
  modelInput: document.querySelector("#modelInput"),
  modelOptions: document.querySelector("#modelOptions"),
  temperatureInput: document.querySelector("#temperatureInput"),
  systemPrompt: document.querySelector("#systemPrompt"),
  endpointList: document.querySelector("#endpointList"),
};

const defaultSystemPrompt = "Ты дружелюбный русскоязычный ассистент VK-бота. Отвечай кратко, полезно и естественно для переписки.";

async function loadConfig() {
  const response = await fetch("/api/config");
  state.config = await response.json();
  els.modelInput.value = localStorage.getItem("llmModel") || state.config.llmModel || "";
  els.systemPrompt.value = localStorage.getItem("systemPrompt") || defaultSystemPrompt;
  renderEndpoints();
}

function renderEndpoints() {
  const cfg = state.config;
  els.endpointList.innerHTML = `
    <dl>
      <dt>LLM</dt><dd>${escapeHtml(cfg.llmBaseUrl)} · ${escapeHtml(cfg.llmModel)}</dd>
      <dt>STT</dt><dd>${escapeHtml(cfg.sttBaseUrl)} · ${escapeHtml(cfg.sttModel)}</dd>
      <dt>TTS</dt><dd>${escapeHtml(cfg.ttsBaseUrl)} · ${escapeHtml(cfg.ttsModel)}</dd>
    </dl>
  `;
}

function renderDialogs() {
  const query = els.dialogSearch.value.trim().toLowerCase();
  els.dialogList.innerHTML = "";
  dialogs
    .filter((dialog) => dialog.title.toLowerCase().includes(query) || dialog.preview.toLowerCase().includes(query))
    .forEach((dialog) => {
      const button = document.createElement("button");
      button.className = `dialog-item${dialog.id === state.activeDialogId ? " is-active" : ""}`;
      button.type = "button";
      button.innerHTML = `
        <div class="avatar">${escapeHtml(dialog.initials)}</div>
        <div>
          <strong class="dialog-title">${escapeHtml(dialog.title)}</strong>
          <span class="dialog-preview">${escapeHtml(dialog.preview)}</span>
        </div>
        <span class="dialog-time">${escapeHtml(dialog.time)}</span>
      `;
      button.addEventListener("click", () => {
        state.activeDialogId = dialog.id;
        renderDialogs();
      });
      els.dialogList.append(button);
    });
}

function renderMessages() {
  els.messages.innerHTML = "";
  state.messages.forEach((message) => {
    const item = document.createElement("article");
    item.className = `message ${message.role === "user" ? "out" : ""} ${message.role === "system" ? "system" : ""} ${message.loading ? "loading" : ""}`;
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = message.content;
    if (message.audioUrl) {
      const audio = document.createElement("audio");
      audio.className = "audio-reply";
      audio.controls = true;
      audio.src = message.audioUrl;
      bubble.append(audio);
    }
    item.append(bubble);
    els.messages.append(item);
  });
  els.messages.scrollTop = els.messages.scrollHeight;
}

function addMessage(role, content, extra = {}) {
  const message = { id: crypto.randomUUID(), role, content, ...extra };
  state.messages.push(message);
  renderMessages();
  return message;
}

function updateMessage(id, patch) {
  const message = state.messages.find((item) => item.id === id);
  if (!message) return;
  Object.assign(message, patch);
  renderMessages();
}

async function sendMessage() {
  const text = els.input.value.trim();
  if (!text) return;
  els.input.value = "";
  resizeInput();
  addMessage("user", text);
  await askAssistant();
}

async function askAssistant() {
  const loading = addMessage("assistant", "Печатает", { loading: true });
  try {
    localStorage.setItem("llmModel", els.modelInput.value.trim());
    localStorage.setItem("systemPrompt", els.systemPrompt.value.trim());
    const messages = [
      { role: "system", content: els.systemPrompt.value.trim() || defaultSystemPrompt },
      ...state.messages
        .filter((message) => !message.loading && message.role !== "system")
        .slice(-16)
        .map((message) => ({
          role: message.role === "user" ? "user" : "assistant",
          content: message.content,
        })),
    ];
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: els.modelInput.value.trim() || state.config.llmModel,
        temperature: Number(els.temperatureInput.value || 0.6),
        max_tokens: 700,
        messages,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || "LLM request failed");
    const content = cleanAssistantContent(data.choices?.[0]?.message?.content) || "Пустой ответ от модели.";
    updateMessage(loading.id, { content, loading: false });
    if (els.ttsToggle.checked) {
      await attachSpeech(loading.id, content);
    }
  } catch (error) {
    updateMessage(loading.id, { content: `Ошибка: ${error.message}`, loading: false });
  }
}

async function attachSpeech(messageId, input) {
  try {
    const response = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || error.error || "TTS request failed");
    }
    const blob = await response.blob();
    const audioUrl = URL.createObjectURL(blob);
    updateMessage(messageId, { audioUrl });
  } catch (error) {
    addMessage("system", `TTS не сработал: ${error.message}`);
  }
}

async function toggleRecording() {
  if (state.mediaRecorder?.state === "recording") {
    state.mediaRecorder.stop();
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.recordedChunks = [];
    state.mediaRecorder = new MediaRecorder(stream);
    state.mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) state.recordedChunks.push(event.data);
    });
    state.mediaRecorder.addEventListener("stop", async () => {
      els.record.classList.remove("is-recording");
      stream.getTracks().forEach((track) => track.stop());
      await transcribeRecording();
    });
    state.mediaRecorder.start();
    els.record.classList.add("is-recording");
  } catch (error) {
    addMessage("system", `Микрофон недоступен: ${error.message}`);
  }
}

async function transcribeRecording() {
  const blob = new Blob(state.recordedChunks, { type: state.recordedChunks[0]?.type || "audio/webm" });
  if (!blob.size) return;
  const pending = addMessage("system", "Распознаю голосовое сообщение");
  try {
    const audio = await blobToDataUrl(blob);
    const response = await fetch("/api/transcribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ audio }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || "STT request failed");
    const text = (data.text || data.transcription || "").trim();
    updateMessage(pending.id, {
      content: text ? "Голос распознан. Текст можно отредактировать перед отправкой." : "STT вернул пустой текст",
    });
    if (text) {
      els.input.value = text;
      resizeInput();
      els.input.focus();
      els.input.setSelectionRange(text.length, text.length);
    }
  } catch (error) {
    updateMessage(pending.id, { content: `STT не сработал: ${error.message}` });
  }
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function resizeInput() {
  els.input.style.height = "auto";
  els.input.style.height = `${Math.min(140, Math.max(42, els.input.scrollHeight))}px`;
}

function cleanAssistantContent(value) {
  return String(value || "")
    .replace(/<think>[\s\S]*?<\/think>/gi, "")
    .replace(/<think>[\s\S]*/gi, "")
    .trim();
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}

function bindEvents() {
  els.send.addEventListener("click", sendMessage);
  els.record.addEventListener("click", toggleRecording);
  els.dialogSearch.addEventListener("input", renderDialogs);
  els.input.addEventListener("input", resizeInput);
  els.input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });
  els.settingsButton.addEventListener("click", () => els.settingsPanel.classList.add("is-open"));
  els.closeSettings.addEventListener("click", () => els.settingsPanel.classList.remove("is-open"));
}

async function init() {
  bindEvents();
  renderDialogs();
  renderMessages();
  await loadConfig();
  await loadModels();
}

async function loadModels() {
  try {
    const response = await fetch("/api/models");
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || "Models request failed");
    const models = normalizeModels(data);
    els.modelOptions.innerHTML = models
      .map((model) => `<option value="${escapeHtml(model)}"></option>`)
      .join("");
  } catch (error) {
    addMessage("system", `Список моделей не загрузился: ${error.message}`);
  }
}

function normalizeModels(data) {
  if (Array.isArray(data)) {
    return data.map((item) => String(item.id || item.name || item)).filter(Boolean);
  }
  if (Array.isArray(data.data)) {
    return data.data.map((item) => String(item.id || item.name || item)).filter(Boolean);
  }
  if (Array.isArray(data.models)) {
    return data.models.map((item) => String(item.id || item.name || item)).filter(Boolean);
  }
  return [];
}

init();
