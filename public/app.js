const state = {
  config: null,
  activeDialogId: localStorage.getItem("citypoliaActiveDialogId") || "ai",
  chatId: localStorage.getItem("citypoliaChatId") || `citypolia-demo-${crypto.randomUUID()}`,
  models: [],
  threads: {},
  mediaRecorder: null,
  recordedChunks: [],
};

const storageKey = "citypoliaThreadsV1";
const promptVersion = "citypolia-support-v1";
const modelVersion = "deepseek-v4-flash-v1";

const marketplaceLinks = [
  "Ozon: https://www.ozon.ru/search/?text=%D0%A1%D0%98%D0%A2%D0%98%D0%9F%D0%9E%D0%9B%D0%98%D0%AF",
  "Wildberries: https://www.wildberries.ru/catalog/0/search.aspx?search=%D0%A1%D0%98%D0%A2%D0%98%D0%9F%D0%9E%D0%9B%D0%98%D0%AF",
  "Яндекс Маркет: https://market.yandex.ru/search?text=%D0%A1%D0%98%D0%A2%D0%98%D0%9F%D0%9E%D0%9B%D0%98%D0%AF",
];

const defaultThreads = {
  ai: {
    id: "ai",
    title: "СитиГид",
    preview: "Помощник по СИТИПОЛИИ",
    time: "сейчас",
    initials: "СГ",
    bot: true,
    chatId: state.chatId,
    messages: [
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "Привет! Я СитиГид, помощник по настольной игре СИТИПОЛИЯ. Я могу рассказать об игре, помочь с правилами, провести подготовку к партии шаг за шагом и подсказать, где посмотреть игру на маркетплейсах. Отвечаю текстом и могу озвучивать ответы голосом. Напишите: \"подготовка\", \"краткие правила\", \"где купить\" или задайте свой вопрос.",
      },
    ],
  },
  support: {
    id: "support",
    title: "Подготовка к партии",
    preview: "Пошаговый сценарий",
    time: "10:31",
    initials: "П",
    bot: false,
    messages: [
      { id: crypto.randomUUID(), role: "assistant", content: "Начнем подготовку к партии. Шаг 1: положите игровое поле в центр стола, чтобы всем игрокам было удобно видеть клетки." },
      { id: crypto.randomUUID(), role: "assistant", content: "Когда сделаете, напишите \"готово\". СитиГид даст следующий шаг, а не завалит всем списком сразу." },
      { id: crypto.randomUUID(), role: "user", content: "готово" },
      { id: crypto.randomUUID(), role: "assistant", content: "Шаг 2: разделите карточки объектов/собственности и положите их рядом с полем. Напишите \"сделал\", и пойдем дальше." },
    ],
  },
  ops: {
    id: "ops",
    title: "Где купить",
    preview: "Ссылки на маркетплейсы",
    time: "09:48",
    initials: "₽",
    bot: false,
    messages: [
      { id: crypto.randomUUID(), role: "assistant", content: "СитиГид может дать ссылки на поиск СИТИПОЛИИ на маркетплейсах. Перед покупкой проверьте продавца, комплектацию и отзывы." },
      { id: crypto.randomUUID(), role: "assistant", content: marketplaceLinks.join("\n") },
    ],
  },
};

const els = {
  dialogList: document.querySelector("#dialogList"),
  dialogSearch: document.querySelector("#dialogSearch"),
  messages: document.querySelector("#messages"),
  input: document.querySelector("#messageInput"),
  send: document.querySelector("#sendButton"),
  record: document.querySelector("#recordButton"),
  clearChat: document.querySelector("#clearChatButton"),
  ttsToggle: document.querySelector("#ttsToggle"),
  settingsButton: document.querySelector("#settingsButton"),
  settingsPanel: document.querySelector("#settingsPanel"),
  closeSettings: document.querySelector("#closeSettings"),
  modelInput: document.querySelector("#modelInput"),
  modelOptions: document.querySelector("#modelOptions"),
  temperatureInput: document.querySelector("#temperatureInput"),
  systemPrompt: document.querySelector("#systemPrompt"),
  endpointList: document.querySelector("#endpointList"),
  vkEnabled: document.querySelector("#vkEnabled"),
  vkGroupId: document.querySelector("#vkGroupId"),
  vkToken: document.querySelector("#vkToken"),
  vkSecret: document.querySelector("#vkSecret"),
  vkConfirmation: document.querySelector("#vkConfirmation"),
  vkSendText: document.querySelector("#vkSendText"),
  vkSendVoice: document.querySelector("#vkSendVoice"),
  vkSaveButton: document.querySelector("#vkSaveButton"),
  vkCallbackBox: document.querySelector("#vkCallbackBox"),
};

const defaultSystemPrompt = `Ты СитиГид, дружелюбный бот поддержки настольной игры СИТИПОЛИЯ.
Задача: помочь покупателю узнать об игре, быстро подготовиться к партии, разобраться с правилами и спокойно провести первую игру.

Тон: теплый, уверенный, короткий. Пиши по-русски. Не называй СИТИПОЛИЮ чужим брендом и не сравнивай напрямую с другими играми, если пользователь сам не спросил.

Что говорить об игре:
- СИТИПОЛИЯ — семейная экономическая настольная игра про город, сделки, собственность, аренду, деньги и решения игроков.
- Она подходит для дружеской или семейной партии, где игроки покупают объекты, получают доход, платят расходы и стараются прийти к победе.
- Если пользователь спрашивает точные правила, номиналы денег, состав коробки или спорные ситуации, а данных не хватает, не выдумывай. Скажи: "посмотрите памятку/лист правил из коробки" или попроси фото/текст правила.

Стартовое поведение:
- Если пользователь здоровается или не знает, что спросить, представься: "Привет! Я СитиГид, помощник по СИТИПОЛИИ. Могу рассказать об игре, помочь с правилами или провести подготовку к партии шаг за шагом."
- Предложи варианты: "подготовка", "краткие правила", "помоги с ситуацией", "где купить".

Подготовка к игре:
- Если пользователь пишет "подготовка", "начать игру", "подготовь к игре" или похожее, веди строго по одному шагу.
- После каждого шага спрашивай: "Напишите 'готово', и пойдем дальше."
- Если пользователь пишет "готово", "сделал", "дальше", продолжай следующий шаг.
- Не выдавай весь список разом, если пользователь не попросил.
- Если пользователь просит "все сразу", дай компактный список всех шагов.

Базовые шаги подготовки:
1. Положите игровое поле в центр стола, чтобы всем было удобно видеть клетки.
2. Разделите карточки объектов/собственности и положите их рядом с полем.
3. Перемешайте карточки событий/шансов, если они есть в вашем комплекте, и положите стопкой рубашкой вверх.
4. Выберите фишки игроков и поставьте их на стартовую клетку.
5. Выберите банкира или ответственного за банк.
6. Разложите деньги по номиналам в банк. Стартовую сумму выдайте по памятке из коробки; если памятки нет под рукой, попроси пользователя написать номиналы и количество денег в комплекте.
7. Определите первого игрока: броском кубика или договоренностью.
8. Начинайте ход: бросок кубика, движение, выполнение действия клетки.

Правила:
- Если пользователь просит краткие правила, дай 5-8 пунктов.
- Если спрашивает конкретную ситуацию, отвечай по ситуации и задавай один уточняющий вопрос, если не хватает данных.
- Если пользователь прислал голосовое, оно уже распознано STT; работай с распознанным текстом как с вопросом.

Покупка:
- Если пользователь спрашивает где купить, дай ссылки:
  ${marketplaceLinks.join("\n  ")}
  Скажи проверить продавца, комплектность и отзывы.

Ответы для VK:
- При первом контакте скажи, что умеешь отвечать текстом и голосом.
- Обычно сначала отвечай текстом. Голосовой ответ будет отправлен отдельным сообщением, если включен TTS.`;
localStorage.setItem("citypoliaChatId", state.chatId);
if (localStorage.getItem("systemPromptVersion") !== promptVersion) {
  localStorage.setItem("systemPrompt", defaultSystemPrompt);
  localStorage.setItem("systemPromptVersion", promptVersion);
}
if (localStorage.getItem("modelVersion") !== modelVersion) {
  localStorage.setItem("llmModel", "deepseek-v4-flash");
  localStorage.setItem("modelVersion", modelVersion);
}
state.threads = loadThreads();

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
  Object.values(state.threads)
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
        localStorage.setItem("citypoliaActiveDialogId", state.activeDialogId);
        renderChatHeader();
        renderDialogs();
        renderMessages({ forceBottom: true });
      });
      els.dialogList.append(button);
    });
}

function renderChatHeader() {
  const thread = getActiveThread();
  document.querySelector("#chatName").textContent = thread.title;
  document.querySelector("#chatStatus").textContent = thread.bot
    ? "Помощник СИТИПОЛИИ: правила, подготовка, покупки"
    : "Фейковая переписка для демо";
  document.querySelector(".bot-avatar").textContent = thread.initials;
}

function renderMessages(options = {}) {
  const shouldStickToBottom = options.forceBottom || isMessagesNearBottom();
  const thread = getActiveThread();
  els.messages.innerHTML = "";
  thread.messages.forEach((message) => {
    const item = document.createElement("article");
    item.className = `message ${message.role === "user" ? "out" : ""} ${message.role === "system" ? "system" : ""} ${message.loading ? "loading" : ""}`;
    const bubble = document.createElement("div");
    bubble.className = `bubble${message.audioUrl ? " has-audio" : ""}`;
    const text = document.createElement("div");
    text.className = "message-text";
    text.textContent = message.content;
    bubble.append(text);
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
  if (shouldStickToBottom) {
    scrollMessagesToBottom();
  }
}

function addMessage(role, content, extra = {}) {
  const message = { id: crypto.randomUUID(), role, content, ...extra };
  getActiveThread().messages.push(message);
  touchActiveThread(content);
  saveThreads();
  renderDialogs();
  renderMessages();
  return message;
}

function updateMessage(id, patch) {
  const thread = getActiveThread();
  const message = thread.messages.find((item) => item.id === id);
  if (!message) return;
  Object.assign(message, patch);
  touchActiveThread(message.content);
  saveThreads();
  renderDialogs();
  renderMessages();
}

async function sendMessage() {
  const text = els.input.value.trim();
  if (!text) return;
  els.input.value = "";
  resizeInput();
  addMessage("user", text);
  if (getActiveThread().bot) {
    await askAssistant();
  } else {
    addMessage("assistant", "Это фейковая переписка. Для живого ответа СитиГида откройте чат \"СитиГид\".");
  }
}

async function askAssistant() {
  const loading = addMessage("assistant", "Печатает", { loading: true });
  try {
    localStorage.setItem("llmModel", els.modelInput.value.trim());
    localStorage.setItem("systemPrompt", els.systemPrompt.value.trim());
    const messages = [
      { role: "system", content: els.systemPrompt.value.trim() || defaultSystemPrompt },
      ...getActiveThread().messages
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
        model: getSelectedModel(),
        chat_id: getActiveThread().chatId || state.chatId,
        temperature: Number(els.temperatureInput.value || 0.6),
        max_tokens: 220,
        keep_alive: "30m",
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
    updateMessage(loading.id, { content: `Ошибка LLM: ${formatProviderError(error.message)}`, loading: false });
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
  scrollMessagesToBottom();
}

function isMessagesNearBottom() {
  if (!els.messages.scrollHeight || els.messages.scrollHeight <= els.messages.clientHeight) {
    return true;
  }
  const distance = els.messages.scrollHeight - els.messages.scrollTop - els.messages.clientHeight;
  return distance < 96;
}

function scrollMessagesToBottom() {
  requestAnimationFrame(() => {
    els.messages.scrollTop = els.messages.scrollHeight;
  });
}

function cleanAssistantContent(value) {
  return String(value || "")
    .replace(/<think>[\s\S]*?<\/think>/gi, "")
    .replace(/<think>[\s\S]*/gi, "")
    .trim();
}

function formatProviderError(message) {
  if (message.includes("Model not found")) {
    return "модель не найдена. Я сбросил выбор модели, попробуйте отправить сообщение еще раз.";
  }
  if (message.includes("Insufficient Balance")) {
    return "у провайдера модели недостаточно баланса. Пополните баланс или временно выберите другую модель.";
  }
  if (message.includes("permission to access this resource")) {
    return "OpenWebUI отклонил chat_id или права API-ключа. Обновите страницу и попробуйте снова.";
  }
  if (message.includes("startswith")) {
    return "OpenWebUI v0.9.5 упал из-за отсутствующего chat_id. Обновите страницу, чтобы загрузить фикс.";
  }
  return message;
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
  els.clearChat.addEventListener("click", clearActiveChat);
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
  els.vkSaveButton.addEventListener("click", saveVkSettings);
}

async function init() {
  if (!state.threads[state.activeDialogId]) {
    state.activeDialogId = "ai";
  }
  bindEvents();
  renderChatHeader();
  renderDialogs();
  renderMessages({ forceBottom: true });
  await loadConfig();
  await loadVkSettings();
  await loadModels();
}

async function loadVkSettings() {
  try {
    const response = await fetch("/api/vk/settings");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "VK settings request failed");
    els.vkEnabled.checked = Boolean(data.enabled);
    els.vkGroupId.value = data.groupId || "";
    els.vkSecret.value = data.secret || "";
    els.vkConfirmation.value = data.confirmation || "";
    els.vkSendText.checked = data.sendText !== false;
    els.vkSendVoice.checked = data.sendVoice !== false;
    renderVkCallback(data);
  } catch (error) {
    els.vkCallbackBox.textContent = `VK настройки не загрузились: ${error.message}`;
  }
}

async function saveVkSettings() {
  els.vkSaveButton.disabled = true;
  try {
    const response = await fetch("/api/vk/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        enabled: els.vkEnabled.checked,
        groupId: els.vkGroupId.value.trim(),
        token: els.vkToken.value.trim(),
        secret: els.vkSecret.value.trim(),
        confirmation: els.vkConfirmation.value.trim(),
        sendText: els.vkSendText.checked,
        sendVoice: els.vkSendVoice.checked,
        model: getSelectedModel(),
        systemPrompt: els.systemPrompt.value.trim() || defaultSystemPrompt,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "VK settings save failed");
    els.vkToken.value = "";
    renderVkCallback(data, "VK настройки сохранены.");
  } catch (error) {
    els.vkCallbackBox.textContent = `VK настройки не сохранились: ${error.message}`;
  } finally {
    els.vkSaveButton.disabled = false;
  }
}

function renderVkCallback(data, prefix = "") {
  const callbackUrl = `${location.origin}${data.callbackPath || "/api/vk/callback"}`;
  const tokenState = data.tokenPresent ? "токен сохранен" : "токен не задан";
  els.vkCallbackBox.textContent = `${prefix ? `${prefix} ` : ""}Callback: ${callbackUrl}. ${tokenState}.`;
}

async function loadModels() {
  try {
    const response = await fetch("/api/models");
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || "Models request failed");
    const models = normalizeModels(data);
    state.models = models;
    els.modelOptions.innerHTML = models
      .map((model) => `<option value="${escapeHtml(model)}"></option>`)
      .join("");
    syncSelectedModel();
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

function syncSelectedModel() {
  const saved = localStorage.getItem("llmModel");
  const fallback = state.config?.llmModel || "deepseek-v4-flash";
  const next = state.models.includes(saved) ? saved : fallback;
  els.modelInput.value = state.models.includes(next) ? next : (state.models[0] || next);
  localStorage.setItem("llmModel", els.modelInput.value);
}

function getSelectedModel() {
  const requested = els.modelInput.value.trim();
  if (state.models.length && !state.models.includes(requested)) {
    syncSelectedModel();
  }
  return els.modelInput.value.trim() || state.config.llmModel;
}

function loadThreads() {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || "null");
    if (!saved || typeof saved !== "object") {
      return clone(defaultThreads);
    }
    const merged = clone(defaultThreads);
    for (const [id, thread] of Object.entries(saved)) {
      if (thread && Array.isArray(thread.messages)) {
        merged[id] = { ...merged[id], ...thread };
      }
    }
    return merged;
  } catch {
    return clone(defaultThreads);
  }
}

function saveThreads() {
  const snapshot = clone(state.threads);
  for (const thread of Object.values(snapshot)) {
    thread.messages = thread.messages
      .filter((message) => !message.loading)
      .slice(-80)
      .map((message) => ({ ...message, audioUrl: undefined }));
  }
  localStorage.setItem(storageKey, JSON.stringify(snapshot));
}

function getActiveThread() {
  return state.threads[state.activeDialogId] || state.threads.ai;
}

function clearActiveChat() {
  const activeId = state.activeDialogId;
  const current = getActiveThread();
  const confirmed = confirm(`Очистить сообщения в чате "${current.title}"?`);
  if (!confirmed) return;
  const fresh = clone(defaultThreads[activeId] || defaultThreads.ai);
  state.threads[activeId] = {
    ...current,
    preview: fresh.preview,
    time: "сейчас",
    messages: fresh.messages,
    chatId: activeId === "ai" ? `citypolia-demo-${crypto.randomUUID()}` : current.chatId,
  };
  if (activeId === "ai") {
    state.chatId = state.threads[activeId].chatId;
    localStorage.setItem("citypoliaChatId", state.chatId);
  }
  saveThreads();
  renderChatHeader();
  renderDialogs();
  renderMessages({ forceBottom: true });
}

function touchActiveThread(preview) {
  const thread = getActiveThread();
  thread.preview = String(preview || "").replace(/\s+/g, " ").trim().slice(0, 80) || thread.preview;
  thread.time = new Date().toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

init();
