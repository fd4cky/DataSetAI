const authUser = JSON.parse(document.getElementById("auth-user-data").textContent);

const body = document.body;
const currentPage = body.dataset.page;
const currentRoomId = body.dataset.roomId ? Number(body.dataset.roomId) : null;

const roleLabels = {
  customer: "Заказчик",
  annotator: "Исполнитель",
  unknown: "Неизвестная роль",
};

const membershipLabels = {
  owner: "Владелец",
  invited: "Приглашен",
  joined: "В комнате",
};

const taskStatusLabels = {
  pending: "Ожидает разметки",
  in_progress: "В работе",
  submitted: "Отправлена",
};

const datasetModeLabels = {
  demo: "Demo JSON",
  json: "JSON",
  image: "Фото",
  video: "Видео",
};

const sourceTypeLabels = {
  text: "JSON / текст",
  image: "Фото",
  video: "Видео",
};

const labelColorPool = [
  "#FF6B6B",
  "#4ECDC4",
  "#FFD166",
  "#118AB2",
  "#EF476F",
  "#06D6A0",
  "#F78C6B",
  "#9B5DE5",
];

const state = {
  user: authUser,
  currentTask: null,
  roomDashboard: null,
  theme: document.documentElement.dataset.theme || "light",
  pageRefresh: () => {},
};

const globalElements = {
  globalFlash: document.getElementById("global-flash"),
  themeToggle: document.getElementById("theme-toggle"),
};

function applyTheme(theme) {
  state.theme = theme;
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem("datasetai-theme", theme);
  } catch (error) {
    // no-op for restricted environments
  }

  if (globalElements.themeToggle) {
    const nextTheme = theme === "dark" ? "light" : "dark";
    globalElements.themeToggle.checked = theme === "dark";
    globalElements.themeToggle.setAttribute("aria-label", `Переключить на ${nextTheme === "dark" ? "тёмную" : "светлую"} тему`);
    globalElements.themeToggle.setAttribute("title", `Переключить на ${nextTheme === "dark" ? "тёмную" : "светлую"} тему`);
  }
}

function initThemeToggle() {
  applyTheme(state.theme);
  globalElements.themeToggle?.addEventListener("change", (event) => {
    applyTheme(event.target.checked ? "dark" : "light");
  });
}

function translateRole(role) {
  return roleLabels[role] || role;
}

function translateMembership(status) {
  return membershipLabels[status] || status;
}

function translateTaskStatus(status) {
  return taskStatusLabels[status] || status;
}

function translateDatasetMode(mode) {
  return datasetModeLabels[mode] || mode;
}

function translateSourceType(sourceType) {
  return sourceTypeLabels[sourceType] || sourceType;
}

function pickRandomLabelColor() {
  const color = labelColorPool[Math.floor(Math.random() * labelColorPool.length)];
  return color;
}

function formatPercent(value) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function formatDate(value) {
  if (!value) {
    return "Не задан";
  }
  return new Date(value).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function showFlash(message, type = "success") {
  globalElements.globalFlash.textContent = message;
  globalElements.globalFlash.className = `global-flash global-flash--${type}`;
  globalElements.globalFlash.classList.remove("hidden");
}

function clearFlash() {
  globalElements.globalFlash.className = "global-flash hidden";
  globalElements.globalFlash.textContent = "";
}

function formatApiError(data, fallbackStatus) {
  if (!data) {
    return `HTTP ${fallbackStatus}`;
  }

  if (typeof data.detail === "string" && data.detail.trim()) {
    return data.detail;
  }

  if (Array.isArray(data)) {
    return data.join(", ");
  }

  if (typeof data === "object") {
    const messages = [];
    Object.entries(data).forEach(([key, value]) => {
      const fieldName = key === "non_field_errors" ? "Ошибка" : key;
      if (Array.isArray(value)) {
        messages.push(`${fieldName}: ${value.join(", ")}`);
      } else if (typeof value === "string") {
        messages.push(`${fieldName}: ${value}`);
      }
    });
    if (messages.length) {
      return messages.join(" | ");
    }
  }

  return `HTTP ${fallbackStatus}`;
}

async function api(path, options = {}) {
  if (!state.user) {
    throw new Error("Сначала войди в аккаунт.");
  }

  const headers = {
    "X-User-Id": String(state.user.id),
    ...(options.headers || {}),
  };
  const requestOptions = {
    method: options.method || "GET",
    headers,
  };

  if (options.formData) {
    requestOptions.body = options.formData;
  } else if (options.body !== undefined) {
    requestOptions.headers["Content-Type"] = "application/json";
    requestOptions.body = JSON.stringify(options.body);
  }

  const response = await fetch(path, requestOptions);
  const contentType = response.headers.get("content-type") || "";

  if (response.status === 204) {
    return null;
  }

  let data = null;
  const text = await response.text();
  if (text) {
    try {
      if (contentType.includes("application/json")) {
        data = JSON.parse(text);
      } else if (text.includes("<!DOCTYPE html") || text.includes("<html")) {
        data = {
          detail: "Сервер вернул HTML-ошибку вместо JSON. Обычно это значит, что backend упал или не применены миграции. Выполни: python manage.py migrate",
        };
      } else {
        data = { detail: text };
      }
    } catch (error) {
      data = { detail: "Не удалось прочитать ответ API." };
    }
  }

  if (!response.ok) {
    throw new Error(formatApiError(data, response.status));
  }

  return data;
}

function renderMetricCards(container, metrics) {
  container.innerHTML = metrics
    .map((metric) => `
      <article class="metric-card">
        <span>${metric.label}</span>
        <strong>${metric.value}</strong>
      </article>
    `)
    .join("");
}

function renderSummaryRows(container, rows) {
  container.innerHTML = rows
    .map((row) => `
      <div class="summary-row">
        <span>${row.label}</span>
        <strong>${row.value}</strong>
      </div>
    `)
    .join("");
}

function parseDateString(dateString) {
  const [year, month, day] = dateString.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

function formatUtcDate(date) {
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatMonthLabel(dateString) {
  return new Intl.DateTimeFormat("ru-RU", { month: "short", timeZone: "UTC" })
    .format(parseDateString(dateString))
    .replace(".", "");
}

function shiftDateString(dateString, days) {
  const date = parseDateString(dateString);
  date.setUTCDate(date.getUTCDate() + days);
  return formatUtcDate(date);
}

function formatWeeksLabel(count) {
  const mod10 = count % 10;
  const mod100 = count % 100;

  if (mod10 === 1 && mod100 !== 11) {
    return "неделю";
  }

  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return "недели";
  }

  return "недель";
}

function buildActivityMonthLabels(series) {
  const labels = [];
  let previousMonthKey = null;

  series.forEach((item, index) => {
    const date = parseDateString(item.date);
    const monthKey = `${date.getUTCFullYear()}-${date.getUTCMonth()}`;
    if (monthKey === previousMonthKey) {
      return;
    }

    const weekIndex = Math.floor(index / 7);
    if (labels.length && labels[labels.length - 1].weekIndex === weekIndex) {
      labels[labels.length - 1] = {
        label: formatMonthLabel(item.date),
        weekIndex,
      };
    } else {
      labels.push({
        label: formatMonthLabel(item.date),
        weekIndex,
      });
    }

    previousMonthKey = monthKey;
  });

  return labels;
}

function buildCalendarSeries(series, targetWeekCount = 52) {
  const totalDays = targetWeekCount * 7;
  const seriesByDate = new Map(series.map((item) => [item.date, item.count]));
  const lastDate = series[series.length - 1]?.date;

  if (!lastDate) {
    return [];
  }

  const firstDate = shiftDateString(lastDate, -(totalDays - 1));

  return Array.from({ length: totalDays }, (_, index) => {
    const date = shiftDateString(firstDate, index);
    return {
      date,
      count: seriesByDate.get(date) || 0,
    };
  });
}

function renderActivity(container, series) {
  if (!container) {
    return;
  }

  if (!series?.length) {
    container.innerHTML = '<div class="empty-card">Активность пока отсутствует.</div>';
    return;
  }

  const targetWeekCount = 52;
  const calendarSeries = buildCalendarSeries(series, targetWeekCount);
  const maxCount = Math.max(...calendarSeries.map((item) => item.count), 0);
  const calendarWidth = targetWeekCount * 14 + (targetWeekCount - 1) * 4 + 24;
  const monthLabels = buildActivityMonthLabels(calendarSeries);
  container.innerHTML = `
    <div class="activity-board__calendar" style="width: ${calendarWidth}px; max-width: 100%;">
      <div class="activity-board__months" style="grid-template-columns: repeat(${targetWeekCount}, 14px);">
        ${monthLabels
          .map(
            (item) =>
              `<span class="activity-board__month" style="grid-column: ${item.weekIndex + 1};">${item.label}</span>`
          )
          .join("")}
      </div>
      <div class="activity-board__grid" style="grid-template-columns: repeat(${targetWeekCount}, 14px);">
        ${calendarSeries
          .map((item) => {
            let level = 0;
            if (item.count > 0 && maxCount > 0) {
              const ratio = item.count / maxCount;
              level = ratio < 0.34 ? 1 : ratio < 0.67 ? 2 : 3;
            }

            return `<div class="activity-board__cell" data-level="${level}" title="${item.date}: ${item.count}"></div>`;
          })
          .join("")}
      </div>
    </div>
    <div class="activity-board__legend">Интенсивность активности за последние ${targetWeekCount} ${formatWeeksLabel(targetWeekCount)}</div>
  `;
}

function initGlobalHeader() {
  initThemeToggle();
  if (state.user) {
    state.pageRefresh();
  }
}

function initRoomsPage() {
  const grid = document.getElementById("rooms-grid");
  const empty = document.getElementById("rooms-grid-empty");
  const roomIdInput = document.getElementById("rooms-room-id");
  const passwordInput = document.getElementById("rooms-room-password");
  const enterBtn = document.getElementById("rooms-enter-btn");
  const createLink = document.getElementById("rooms-create-link");

  function updateEnterButtonState() {
    const isReady = roomIdInput.value.trim();
    enterBtn.disabled = !isReady;
    enterBtn.classList.toggle("btn--primary", isReady);
    enterBtn.classList.toggle("btn--muted", !isReady);
  }

  async function loadRooms() {
    if (!state.user) {
      return;
    }

    const [ownedRooms, memberRooms] = await Promise.all([api("/api/v1/rooms/"), api("/api/v1/me/rooms/")]);
    const roomMap = new Map();
    [...ownedRooms, ...memberRooms].forEach((room) => {
      if (!roomMap.has(room.id)) {
        roomMap.set(room.id, room);
      }
    });
    const rooms = Array.from(roomMap.values());

    if (!rooms?.length) {
      grid.innerHTML = "";
      empty.classList.remove("hidden");
      return;
    }

    empty.classList.add("hidden");
    grid.innerHTML = rooms
      .map(
        (room) => `
          <article class="room-card" data-room-id="${room.id}">
            <div>
              <div class="room-card__id">Комната #${room.id}</div>
              <div class="room-card__title">${room.title}</div>
              <div class="room-card__meta">${room.description || "Описание пока не добавлено."}</div>
            </div>
            <div class="room-card__footer">
              <div>ID: ${room.id}</div>
              <div>Статус: ${translateMembership(room.membership_status || "owner")}</div>
              <div>Роль в комнате: ${room.membership_status === "owner" ? "Заказчик" : "Исполнитель"}</div>
              <div>Прогресс: ${formatPercent(room.progress_percent)}</div>
              <div>Задачи: ${room.completed_tasks}/${room.total_tasks}</div>
              <div>Пароль: ${room.has_password ? "есть" : "не задан"}</div>
            </div>
          </article>
        `
      )
      .join("");

    grid.querySelectorAll("[data-room-id]").forEach((card) => {
      card.addEventListener("click", () => {
        roomIdInput.value = card.dataset.roomId;
        updateEnterButtonState();
        window.location.href = `/rooms/${card.dataset.roomId}/`;
      });
    });
  }

  roomIdInput?.addEventListener("input", updateEnterButtonState);
  passwordInput?.addEventListener("input", updateEnterButtonState);

  enterBtn?.addEventListener("click", async () => {
    clearFlash();
    try {
      const response = await api("/api/v1/rooms/access/", {
        method: "POST",
        body: {
          room_id: Number(roomIdInput.value),
          password: passwordInput.value,
        },
      });
      window.location.href = response.redirect_url;
    } catch (error) {
      showFlash(error.message, "error");
    }
  });

  state.pageRefresh = async () => {
    updateEnterButtonState();
    try {
      await loadRooms();
    } catch (error) {
      showFlash(error.message, "error");
    }
  };
}

function initProfilePage() {
  const metrics = document.getElementById("profile-metrics");
  const summary = document.getElementById("profile-summary");
  const activity = document.getElementById("profile-activity");

  state.pageRefresh = async () => {
    if (!state.user) {
      return;
    }

    try {
      const profile = await api("/api/v1/me/profile/");
      renderMetricCards(metrics, [
        { label: "Доступные комнаты", value: profile.overview.accessible_rooms_count },
        { label: "Создано комнат", value: profile.overview.created_rooms_count },
        { label: "Размечено", value: profile.overview.completed_tasks },
        { label: "В работе", value: profile.overview.in_progress_tasks },
      ]);

      renderSummaryRows(summary, [
        { label: "Пользователь", value: `#${profile.id} ${profile.username}` },
        { label: "Создано комнат", value: profile.overview.created_rooms_count },
        { label: "Комнат как исполнителю", value: profile.overview.joined_rooms_count },
        { label: "Приглашения / доступы", value: profile.overview.invitations_count },
      ]);
      renderActivity(activity, profile.activity);
    } catch (error) {
      showFlash(error.message, "error");
    }
  };
}

function readImageMetadata(file) {
  return new Promise((resolve, reject) => {
    const objectUrl = URL.createObjectURL(file);
    const image = new Image();

    image.onload = () => {
      URL.revokeObjectURL(objectUrl);
      resolve({
        name: file.name,
        width: image.naturalWidth,
        height: image.naturalHeight,
      });
    };
    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error(`Не удалось прочитать изображение ${file.name}.`));
    };
    image.src = objectUrl;
  });
}

function readVideoMetadata(file) {
  return new Promise((resolve, reject) => {
    const objectUrl = URL.createObjectURL(file);
    const video = document.createElement("video");
    video.preload = "metadata";

    video.onloadedmetadata = () => {
      URL.revokeObjectURL(objectUrl);
      resolve({
        name: file.name,
        width: video.videoWidth,
        height: video.videoHeight,
        duration: Number(video.duration.toFixed(3)),
        frame_rate: 25,
      });
    };
    video.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error(`Не удалось прочитать видео ${file.name}.`));
    };
    video.src = objectUrl;
  });
}

async function buildMediaManifest(files, datasetMode) {
  if (datasetMode === "image") {
    return Promise.all(files.map((file) => readImageMetadata(file)));
  }
  if (datasetMode === "video") {
    return Promise.all(files.map((file) => readVideoMetadata(file)));
  }
  return [];
}

function summarizeSelectedFiles(files) {
  if (!files.length) {
    return "Файлы пока не выбраны.";
  }
  if (files.length === 1) {
    return `Выбран файл: ${files[0].name}`;
  }
  const preview = files.slice(0, 3).map((file) => file.name).join(", ");
  const suffix = files.length > 3 ? ` и еще ${files.length - 3}` : "";
  return `Выбрано ${files.length} файлов: ${preview}${suffix}`;
}

function initRoomCreatePage() {
  const form = document.getElementById("room-create-form");
  const datasetModeSelect = document.getElementById("dataset-mode-select");
  const datasetFilesInput = document.getElementById("dataset-files-input");
  const datasetUploadHint = document.getElementById("dataset-upload-hint");
  const datasetFilesSummary = document.getElementById("dataset-files-summary");
  const testTaskCountField = document.getElementById("test-task-count-field");
  const labelEditorSection = document.getElementById("label-editor-section");
  const labelEditorList = document.getElementById("label-editor-list");
  const addLabelBtn = document.getElementById("add-label-btn");
  const crossValidationToggle = document.getElementById("cross-validation-enabled");
  const crossValidationCountInput = document.getElementById("cross-validation-count");
  const crossValidationThresholdInput = document.getElementById("cross-validation-threshold");

  const datasetModeConfig = {
    demo: {
      hint: "Для demo-режима будет создан встроенный набор текстовых задач без загрузки файлов.",
      accept: "",
      multiple: false,
      usesFiles: false,
      usesLabels: false,
    },
    json: {
      hint: "Загрузи один JSON-файл. Каждый элемент массива будет создан как отдельная задача.",
      accept: ".json,application/json",
      multiple: false,
      usesFiles: true,
      usesLabels: false,
    },
    image: {
      hint: "Загрузи набор фотографий. Для каждой фотографии будет создана отдельная задача с bbox-разметкой.",
      accept: "image/*",
      multiple: true,
      usesFiles: true,
      usesLabels: true,
    },
    video: {
      hint: "Загрузи набор видеороликов. Каждое видео будет автоматически разбито на кадры, и каждый кадр станет отдельной задачей как обычное фото.",
      accept: "video/*",
      multiple: true,
      usesFiles: true,
      usesLabels: true,
    },
  };

  function buildLabelRow(name = "", color = pickRandomLabelColor()) {
    const row = document.createElement("div");
    row.className = "label-editor-row";
    row.innerHTML = `
      <label class="field">
        <span>Лейбл</span>
        <input class="label-editor-row__name" type="text" placeholder="Например, car" value="${name}">
      </label>
      <label class="field field--color">
        <span>Цвет</span>
        <input class="label-editor-row__color" type="color" value="${color}">
      </label>
      <button class="btn btn--muted btn--compact" type="button">Убрать</button>
    `;

    row.querySelector("button")?.addEventListener("click", () => {
      row.remove();
    });

    return row;
  }

  function ensureInitialLabelRow() {
    if (!labelEditorList.children.length) {
      labelEditorList.appendChild(buildLabelRow());
    }
  }

  function collectLabels() {
    return Array.from(labelEditorList.querySelectorAll(".label-editor-row"))
      .map((row) => ({
        name: row.querySelector(".label-editor-row__name")?.value.trim() || "",
        color: row.querySelector(".label-editor-row__color")?.value || pickRandomLabelColor(),
      }))
      .filter((item) => item.name);
  }

  function syncDatasetMode() {
    const datasetMode = datasetModeSelect?.value || "demo";
    const config = datasetModeConfig[datasetMode];

    datasetUploadHint.textContent = config.hint;
    datasetFilesInput.disabled = !config.usesFiles;
    datasetFilesInput.accept = config.accept;
    datasetFilesInput.multiple = config.multiple;
    if (!config.usesFiles) {
      datasetFilesInput.value = "";
    }
    datasetFilesSummary.textContent = summarizeSelectedFiles(Array.from(datasetFilesInput.files || []));
    testTaskCountField.classList.toggle("hidden", datasetMode !== "demo");
    labelEditorSection.classList.toggle("hidden", !config.usesLabels);
    if (config.usesLabels) {
      ensureInitialLabelRow();
    }
  }

  function syncCrossValidationSettings() {
    const enabled = Boolean(crossValidationToggle?.checked);
    if (crossValidationCountInput) {
      crossValidationCountInput.disabled = !enabled;
    }
    if (crossValidationThresholdInput) {
      crossValidationThresholdInput.disabled = !enabled;
    }
  }

  datasetModeSelect?.addEventListener("change", syncDatasetMode);
  crossValidationToggle?.addEventListener("change", syncCrossValidationSettings);
  datasetFilesInput?.addEventListener("change", () => {
    datasetFilesSummary.textContent = summarizeSelectedFiles(Array.from(datasetFilesInput.files || []));
  });
  addLabelBtn?.addEventListener("click", () => {
    labelEditorList.appendChild(buildLabelRow());
  });

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFlash();

    const rawFormData = new FormData(form);
    const datasetMode = (rawFormData.get("dataset_mode") || "demo").toString();
    const datasetFiles = Array.from(datasetFilesInput.files || []);
    const annotatorIds = (rawFormData.get("annotator_ids") || "")
      .toString()
      .split(",")
      .map((item) => Number(item.trim()))
      .filter((item) => Number.isInteger(item) && item > 0);
    const deadlineValue = rawFormData.get("deadline");
    const labels = collectLabels();
    const crossValidationEnabled = Boolean(crossValidationToggle?.checked);
    const crossValidationCount = Number(rawFormData.get("cross_validation_annotators_count") || 1);

    if (datasetMode !== "demo" && !datasetFiles.length) {
      showFlash("Загрузи файл или набор файлов для выбранного типа датасета.", "error");
      return;
    }

    if ((datasetMode === "image" || datasetMode === "video") && !labels.length) {
      showFlash("Добавь хотя бы один лейбл для фото или видео.", "error");
      return;
    }

    if (crossValidationEnabled && crossValidationCount < 2) {
      showFlash("Для перекрестной разметки укажи минимум двух независимых исполнителей.", "error");
      return;
    }

    let mediaManifest = [];
    try {
      mediaManifest = await buildMediaManifest(datasetFiles, datasetMode);
    } catch (error) {
      showFlash(error.message, "error");
      return;
    }

    const payload = new FormData();
    payload.append("title", rawFormData.get("title") || "");
    payload.append("description", rawFormData.get("description") || "");
    payload.append("password", rawFormData.get("password") || "");
    payload.append("dataset_mode", datasetMode);
    payload.append("dataset_label", rawFormData.get("dataset_label") || "Тестовый датасет");
    payload.append("test_task_count", String(Number(rawFormData.get("test_task_count") || 12)));
    payload.append("cross_validation_enabled", crossValidationEnabled ? "true" : "false");
    payload.append(
      "cross_validation_annotators_count",
      String(Number(rawFormData.get("cross_validation_annotators_count") || 1))
    );
    payload.append(
      "cross_validation_similarity_threshold",
      String(Number(rawFormData.get("cross_validation_similarity_threshold") || 80))
    );
    annotatorIds.forEach((annotatorId) => {
      payload.append("annotator_ids", String(annotatorId));
    });
    datasetFiles.forEach((file) => {
      payload.append("dataset_files", file);
    });

    if (deadlineValue) {
      payload.append("deadline", new Date(deadlineValue.toString()).toISOString());
    }
    if (labels.length) {
      payload.append("labels", JSON.stringify(labels));
    }
    if (mediaManifest.length) {
      payload.append("media_manifest", JSON.stringify(mediaManifest));
    }

    try {
      const room = await api("/api/v1/rooms/", {
        method: "POST",
        formData: payload,
      });
      showFlash(`Комната #${room.id} создана. Переходим к ней.`, "success");
      window.setTimeout(() => {
        window.location.href = `/rooms/${room.id}/`;
      }, 700);
    } catch (error) {
      showFlash(error.message, "error");
    }
  });

  syncDatasetMode();
  syncCrossValidationSettings();

  state.pageRefresh = async () => {
    syncDatasetMode();
    syncCrossValidationSettings();
  };
}

function renderCurrentTask(taskBox, task) {
  if (!task) {
    taskBox.className = "empty-card";
    taskBox.textContent = "Задача пока не выбрана.";
    return;
  }

  const meta = [
    `Статус: ${translateTaskStatus(task.status)}`,
    `Тип: ${translateSourceType(task.source_type)}`,
  ];
  if (task.source_name) {
    meta.push(`Файл: ${task.source_name}`);
  }
  if (task.input_payload?.width && task.input_payload?.height) {
    meta.push(`Размер: ${task.input_payload.width} × ${task.input_payload.height}`);
  }

  taskBox.className = "task-box";
  taskBox.innerHTML = `
    <strong>Задача #${task.id}</strong>
    ${meta.map((item) => `<div>${item}</div>`).join("")}
    <pre class="payload-preview">${JSON.stringify(task.input_payload, null, 2)}</pre>
  `;
}

function renderCustomerAnnotatorDetail(container, activityContainer, annotator) {
  if (!annotator) {
    container.className = "empty-card";
    container.textContent = "Выбери исполнителя в списке слева.";
    activityContainer.innerHTML = "";
    return;
  }

  container.className = "summary-stack";
  renderSummaryRows(container, [
    { label: "Исполнитель", value: `#${annotator.user_id} ${annotator.username}` },
    { label: "Статус", value: translateMembership(annotator.status) },
    { label: "Выполнено", value: annotator.completed_tasks },
    { label: "В работе", value: annotator.in_progress_tasks },
    { label: "Осталось", value: annotator.remaining_tasks },
    { label: "Прогресс", value: formatPercent(annotator.progress_percent) },
  ]);
  renderActivity(activityContainer, annotator.activity);
}

function renderRoomDashboardHeader(title, subtitle, roomHeaderMeta, roomMetrics, dashboard) {
  title.textContent = dashboard.room.title;
  subtitle.textContent = dashboard.room.description || "Описание для этой комнаты пока не заполнено.";
  roomHeaderMeta.innerHTML = `
    <div class="summary-stack room-header-meta__stack">
      <div class="summary-row"><span>ID комнаты</span><strong>#${dashboard.room.id}</strong></div>
      <div class="summary-row"><span>Датасет</span><strong>${dashboard.room.dataset_label || "Тестовый датасет"}</strong></div>
      <div class="summary-row"><span>Тип</span><strong>${translateDatasetMode(dashboard.room.dataset_type)}</strong></div>
      <div class="summary-row"><span>Дедлайн</span><strong>${formatDate(dashboard.room.deadline)}</strong></div>
      <div class="summary-row"><span>Доступ</span><strong>${dashboard.room.has_password ? "С паролем" : "Без пароля"}</strong></div>
      ${
        dashboard.actor.role === "customer"
          ? '<button id="detail-delete-room-btn" class="btn btn--danger room-header-meta__delete" type="button">Удалить комнату</button>'
          : ""
      }
    </div>
  `;

  renderMetricCards(roomMetrics, [
    { label: "Всего задач", value: dashboard.overview.total_tasks },
    { label: "Выполнено", value: dashboard.overview.completed_tasks },
    { label: "Осталось", value: dashboard.overview.remaining_tasks },
    { label: "Готовность", value: formatPercent(dashboard.overview.progress_percent) },
  ]);
}

function renderAnnotatorOverview(summaryContainer, activityContainer, dashboard) {
  renderSummaryRows(summaryContainer, [
    { label: "Роль в комнате", value: translateRole(dashboard.actor.role) },
    { label: "Выполнено мной", value: dashboard.annotator_stats.completed_tasks },
    { label: "В работе", value: dashboard.annotator_stats.in_progress_tasks },
    { label: "Осталось", value: dashboard.annotator_stats.remaining_tasks },
    { label: "Мой прогресс", value: formatPercent(dashboard.annotator_stats.progress_percent) },
  ]);
  renderActivity(activityContainer, dashboard.annotator_stats.activity);
}

function renderEmptyTaskBox(taskBox, message) {
  taskBox.className = "empty-card";
  taskBox.textContent = message;
}

function renderStaticLabels(container, labels) {
  if (!container) {
    return;
  }

  if (!labels?.length) {
    container.innerHTML = '<div class="empty-card">Лейблы для этой комнаты пока не заданы.</div>';
    return;
  }

  container.innerHTML = labels
    .map(
      (label) => `
        <span class="label-chip label-chip--static" style="--label-color: ${label.color}">
          <i></i>
          <span>${label.name}</span>
        </span>
      `
    )
    .join("");
}

async function downloadRoomExport(roomId, exportFormat) {
  const response = await fetch(`/api/v1/rooms/${roomId}/export/?export_format=${encodeURIComponent(exportFormat)}`, {
    method: "GET",
    headers: {
      "X-User-Id": String(state.user.id),
    },
  });

  if (!response.ok) {
    const text = await response.text();
    let data = null;
    try {
      data = JSON.parse(text);
    } catch (error) {
      data = { detail: text || `HTTP ${response.status}` };
    }
    throw new Error(data?.detail || `HTTP ${response.status}`);
  }

  const disposition = response.headers.get("content-disposition") || "";
  const filenameMatch = disposition.match(/filename="([^"]+)"/i);
  const filename = filenameMatch?.[1] || `room-${roomId}-${exportFormat}`;
  const blob = await response.blob();
  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(blobUrl);
}

function initRoomDetailPage() {
  if (!currentRoomId) {
    showFlash("Не удалось определить ID комнаты из URL.", "error");
    state.pageRefresh = async () => {};
    return;
  }

  const title = document.getElementById("room-title");
  const subtitle = document.getElementById("room-subtitle");
  const roomHeaderMeta = document.getElementById("room-header-meta");
  const roomMetrics = document.getElementById("room-metrics");
  const annotatorWorkspace = document.getElementById("annotator-workspace");
  const customerWorkspace = document.getElementById("customer-workspace");
  const annotatorSummary = document.getElementById("annotator-summary");
  const annotatorActivity = document.getElementById("annotator-activity");
  const workBtn = document.getElementById("detail-work-btn");
  const workNote = document.getElementById("detail-work-note");
  const annotatorsList = document.getElementById("annotators-list");
  const annotatorDetailPanel = document.getElementById("annotator-detail-panel");
  const annotatorDetailActivity = document.getElementById("annotator-detail-activity");
  const inviteForm = document.getElementById("detail-invite-form");
  const inviteUserIdInput = document.getElementById("detail-invite-user-id");
  const customerLabels = document.getElementById("customer-labels");
  const exportFormatSelect = document.getElementById("detail-export-format");
  const exportBtn = document.getElementById("detail-export-btn");

  function bindDeleteRoomButton() {
    const deleteRoomBtn = document.getElementById("detail-delete-room-btn");
    deleteRoomBtn?.addEventListener("click", async () => {
      clearFlash();
      const shouldDelete = window.confirm(
        "Удалить комнату? Это действие удалит саму комнату, задачи, участников и результаты разметки без возможности восстановления."
      );
      if (!shouldDelete) {
        return;
      }

      try {
        await api(`/api/v1/rooms/${currentRoomId}/`, { method: "DELETE" });
        window.location.href = "/rooms/";
      } catch (error) {
        showFlash(error.message, "error");
      }
    });
  }

  function updateAnnotatorWorkAction(dashboard) {
    const membershipStatus = dashboard.room.membership_status;
    const isJoined = membershipStatus === "joined";

    workBtn.disabled = false;
    workBtn.dataset.action = isJoined ? "work" : "join";
    workBtn.textContent = isJoined ? "Приступить к работе" : "Вступить в комнату";
    workNote.textContent = isJoined
      ? "Обзор комнаты открыт. Вход в комнату, получение задач и отправка результата доступны только в отдельной рабочей среде."
      : "Ты приглашен в комнату. Сначала подтверди вступление, после этого кнопка переключится на переход в рабочую среду.";
  }

  async function loadDashboard() {
    const dashboard = await api(`/api/v1/rooms/${currentRoomId}/dashboard/`);
    state.roomDashboard = dashboard;

    renderRoomDashboardHeader(title, subtitle, roomHeaderMeta, roomMetrics, dashboard);

    if (dashboard.actor.role === "annotator") {
      customerWorkspace.classList.add("hidden");
      annotatorWorkspace.classList.remove("hidden");

      renderAnnotatorOverview(annotatorSummary, annotatorActivity, dashboard);
      updateAnnotatorWorkAction(dashboard);
      return;
    }

    annotatorWorkspace.classList.add("hidden");
    customerWorkspace.classList.remove("hidden");
    renderCustomerView(dashboard);
    bindDeleteRoomButton();
  }

  function renderCustomerView(dashboard) {
    renderStaticLabels(customerLabels, dashboard.labels);
    exportFormatSelect.innerHTML = (dashboard.export_formats || [])
      .map((item) => `<option value="${item.value}">${item.label}</option>`)
      .join("");
    exportBtn.disabled = !dashboard.export_formats?.length;

    if (!dashboard.annotators?.length) {
      annotatorsList.innerHTML = '<div class="empty-card">В этой комнате пока нет исполнителей.</div>';
      renderCustomerAnnotatorDetail(annotatorDetailPanel, annotatorDetailActivity, null);
      return;
    }

    annotatorsList.innerHTML = dashboard.annotators
      .map(
        (annotator, index) => `
          <button class="annotator-row ${index === 0 ? "is-active" : ""}" type="button" data-user-id="${annotator.user_id}">
            <div class="annotator-row__meta">
              <strong>${annotator.username}</strong>
              <span>${translateMembership(annotator.status)}</span>
            </div>
            <div class="annotator-row__brief">
              <div>${formatPercent(annotator.progress_percent)}</div>
              <div>${annotator.completed_tasks} из ${dashboard.overview.total_tasks}</div>
            </div>
          </button>
        `
      )
      .join("");

    const setAnnotator = (annotator) => {
      renderCustomerAnnotatorDetail(annotatorDetailPanel, annotatorDetailActivity, annotator);
      annotatorsList.querySelectorAll(".annotator-row").forEach((row) => {
        row.classList.toggle("is-active", Number(row.dataset.userId) === annotator.user_id);
      });
    };

    const firstAnnotator = dashboard.annotators[0];
    setAnnotator(firstAnnotator);
    annotatorsList.querySelectorAll(".annotator-row").forEach((row) => {
      row.addEventListener("click", () => {
        const annotator = dashboard.annotators.find((item) => item.user_id === Number(row.dataset.userId));
        setAnnotator(annotator);
      });
    });
  }

  inviteForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFlash();

    const invitedUserId = Number(inviteUserIdInput.value);
    if (!Number.isInteger(invitedUserId) || invitedUserId <= 0) {
      showFlash("Укажи корректный ID пользователя.", "error");
      return;
    }

    try {
      await api(`/api/v1/rooms/${currentRoomId}/invite/`, {
        method: "POST",
        body: { annotator_id: invitedUserId },
      });
      inviteUserIdInput.value = "";
      showFlash(`Пользователь #${invitedUserId} добавлен в комнату.`, "success");
      await loadDashboard();
    } catch (error) {
      showFlash(error.message, "error");
    }
  });

  workBtn?.addEventListener("click", async () => {
    clearFlash();
    if (workBtn.dataset.action === "join") {
      try {
        await api(`/api/v1/rooms/${currentRoomId}/join/`, { method: "POST", body: {} });
        showFlash("Ты вступил в комнату. Теперь можно переходить к задачам.", "success");
        await loadDashboard();
      } catch (error) {
        showFlash(error.message, "error");
      }
      return;
    }

    window.location.href = `/rooms/${currentRoomId}/work/`;
  });

  exportBtn?.addEventListener("click", async () => {
    clearFlash();
    try {
      await downloadRoomExport(currentRoomId, exportFormatSelect.value || "native_json");
      showFlash("Файл с размеченным датасетом подготовлен.", "success");
    } catch (error) {
      showFlash(error.message, "error");
    }
  });

  state.pageRefresh = async () => {
    if (!state.user) {
      return;
    }

    try {
      await loadDashboard();
    } catch (error) {
      showFlash(error.message, "error");
    }
  };
}

function createMediaAnnotationEditor({
  mediaTool,
  instructions,
  labelPalette,
  activeLabelNote,
  mediaStage,
  annotationList,
  clearBtn,
  resultJson,
  resultLabel,
  submitBtn,
}) {
  const editor = {
    annotations: [],
    activeLabelId: null,
    mediaElement: null,
    overlayElement: null,
    draftElement: null,
    draftStart: null,
    dragState: null,
    resizeState: null,
    suppressLabelClickUntil: 0,
    eventsAttached: false,
  };

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function getLabels() {
    return state.roomDashboard?.labels || [];
  }

  function getLabelById(labelId) {
    return getLabels().find((label) => label.id === labelId) || null;
  }

  function getFrameRate() {
    return Number(state.currentTask?.input_payload?.frame_rate) || 25;
  }

  function getCurrentFrame() {
    if (state.currentTask?.source_type !== "video" || !editor.mediaElement) {
      return 0;
    }
    return Math.max(0, Math.round(editor.mediaElement.currentTime * getFrameRate()));
  }

  function isVisibleOnCurrentFrame(annotation) {
    if (state.currentTask?.source_type !== "video") {
      return true;
    }
    return annotation.frame === getCurrentFrame();
  }

  function setActiveLabel(labelId) {
    editor.activeLabelId = labelId;
    const label = getLabelById(labelId);
    activeLabelNote.textContent = label
      ? `Активный label: ${label.name}. Новые выделения получат его сразу, зажатие перемещает область, нижний правый угол меняет размер, а одиночный клик меняет ее label на активный.`
      : "Активный label пока не выбран.";

    labelPalette.querySelectorAll("[data-label-id]").forEach((button) => {
      button.classList.toggle("is-active", Number(button.dataset.labelId) === labelId);
    });
  }

  function getNaturalSize() {
    if (!editor.mediaElement) {
      return { width: 0, height: 0 };
    }
    if (state.currentTask?.source_type === "video") {
      return {
        width: editor.mediaElement.videoWidth || mediaStage.clientWidth,
        height: editor.mediaElement.videoHeight || mediaStage.clientHeight,
      };
    }
    return {
      width: editor.mediaElement.naturalWidth || mediaStage.clientWidth,
      height: editor.mediaElement.naturalHeight || mediaStage.clientHeight,
    };
  }

  function buildPayload() {
    return {
      annotations: editor.annotations
        .filter((annotation) => annotation.label_id)
        .map((annotation) => ({
          type: annotation.type,
          label_id: annotation.label_id,
          points: annotation.points,
          frame: annotation.frame,
          attributes: annotation.attributes,
          occluded: annotation.occluded,
        })),
    };
  }

  function updateSubmitState() {
    if (!submitBtn) {
      return;
    }
    submitBtn.disabled = !state.currentTask || editor.annotations.some((annotation) => !annotation.label_id);
  }

  function updateResultPreview() {
    resultJson.value = JSON.stringify(buildPayload(), null, 2);
    updateSubmitState();
  }

  function removeAnnotation(localId) {
    editor.annotations = editor.annotations.filter((annotation) => annotation.local_id !== localId);
    render();
  }

  function updateClearButtonVisibility() {
    clearBtn?.classList.toggle("hidden", !editor.annotations.length);
  }

  function renderAnnotationList() {
    if (!editor.annotations.length) {
      annotationList.className = "annotation-list empty-card";
      annotationList.textContent = "Разметка пока отсутствует.";
      return;
    }

    annotationList.className = "annotation-list";
    annotationList.innerHTML = editor.annotations
      .map((annotation, index) => {
        const label = getLabelById(annotation.label_id);
        return `
          <div class="annotation-row ${isVisibleOnCurrentFrame(annotation) ? "is-current" : ""}">
            <div class="annotation-row__meta">
              <strong>#${index + 1}</strong>
              <span>${label ? label.name : "Без лейбла"}</span>
              <small>frame ${annotation.frame}</small>
            </div>
            <div class="annotation-row__points">[${annotation.points.join(", ")}]</div>
            <button class="btn btn--muted btn--compact" type="button" data-remove-id="${annotation.local_id}">Удалить</button>
          </div>
        `;
      })
      .join("");

    annotationList.querySelectorAll("[data-remove-id]").forEach((button) => {
      button.addEventListener("click", () => {
        removeAnnotation(button.dataset.removeId);
      });
    });
  }

  function renderPalette() {
    const labels = getLabels();
    if (!labels.length) {
      labelPalette.innerHTML = '<div class="empty-card">Лейблы для этой комнаты не заданы.</div>';
      setActiveLabel(null);
      return;
    }

    labelPalette.innerHTML = labels
      .map(
        (label) => `
          <button
            class="label-chip label-chip--button ${editor.activeLabelId === label.id ? "is-active" : ""}"
            type="button"
            data-label-id="${label.id}"
            style="--label-color: ${label.color}"
          >
            <i></i>
            <span>${label.name}</span>
          </button>
        `
      )
      .join("");

    labelPalette.querySelectorAll("[data-label-id]").forEach((button) => {
      button.addEventListener("click", () => {
        setActiveLabel(Number(button.dataset.labelId));
      });
    });

    if (!editor.activeLabelId) {
      setActiveLabel(labels[0].id);
    }
  }

  function renderBoxes() {
    if (!editor.overlayElement) {
      return;
    }

    editor.overlayElement.querySelectorAll(".media-bbox").forEach((node) => node.remove());

    const bounds = editor.overlayElement.getBoundingClientRect();
    const naturalSize = getNaturalSize();
    const scaleX = naturalSize.width > 0 && bounds.width > 0 ? bounds.width / naturalSize.width : 1;
    const scaleY = naturalSize.height > 0 && bounds.height > 0 ? bounds.height / naturalSize.height : 1;

    editor.annotations
      .filter((annotation) => isVisibleOnCurrentFrame(annotation))
      .forEach((annotation) => {
        const label = getLabelById(annotation.label_id);
        const [xMin, yMin, xMax, yMax] = annotation.points;
        const button = document.createElement("button");
        button.type = "button";
        button.className = "media-bbox";
        button.style.left = `${xMin * scaleX}px`;
        button.style.top = `${yMin * scaleY}px`;
        button.style.width = `${Math.max((xMax - xMin) * scaleX, 1)}px`;
        button.style.height = `${Math.max((yMax - yMin) * scaleY, 1)}px`;
        button.style.setProperty("--bbox-color", label?.color || "#B8B8B8");
        button.innerHTML = `
          <span>${label ? label.name : "Без лейбла"}</span>
          <i class="media-bbox__resize-handle" aria-hidden="true"></i>
        `;
        button.addEventListener("mousedown", (event) => {
          startDragging(event, annotation);
        });
        button.querySelector(".media-bbox__resize-handle")?.addEventListener("mousedown", (event) => {
          startResizing(event, annotation);
        });
        button.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (Date.now() < editor.suppressLabelClickUntil) {
            return;
          }
          if (!editor.activeLabelId) {
            showFlash("Сначала выбери label.", "error");
            return;
          }
          annotation.label_id = editor.activeLabelId;
          render();
        });
        editor.overlayElement.appendChild(button);
      });
  }

  function render() {
    updateClearButtonVisibility();
    renderPalette();
    renderBoxes();
    renderAnnotationList();
    updateResultPreview();
  }

  function clearDraft() {
    editor.draftElement?.remove();
    editor.draftElement = null;
    editor.draftStart = null;
  }

  function startDragging(event, annotation) {
    if (event.button !== 0 || !editor.overlayElement) {
      return;
    }

    if (state.currentTask?.source_type === "video" && editor.mediaElement && !editor.mediaElement.paused) {
      showFlash("Поставь видео на паузу перед перемещением области.", "error");
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    editor.dragState = {
      annotation,
      startClientX: event.clientX,
      startClientY: event.clientY,
      originalPoints: [...annotation.points],
      moved: false,
    };
  }

  function startResizing(event, annotation) {
    if (event.button !== 0 || !editor.overlayElement) {
      return;
    }

    if (state.currentTask?.source_type === "video" && editor.mediaElement && !editor.mediaElement.paused) {
      showFlash("Поставь видео на паузу перед изменением размера области.", "error");
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    editor.resizeState = {
      annotation,
      startClientX: event.clientX,
      startClientY: event.clientY,
      originalPoints: [...annotation.points],
      moved: false,
    };
  }

  function startDrawing(event) {
    if (event.button !== 0 || !editor.overlayElement) {
      return;
    }

    if (state.currentTask?.source_type === "video" && editor.mediaElement && !editor.mediaElement.paused) {
      showFlash("Поставь видео на паузу перед выделением области.", "error");
      return;
    }

    const bounds = editor.overlayElement.getBoundingClientRect();
    editor.draftStart = {
      x: Math.min(Math.max(event.clientX - bounds.left, 0), bounds.width),
      y: Math.min(Math.max(event.clientY - bounds.top, 0), bounds.height),
    };
    editor.draftElement = document.createElement("div");
    editor.draftElement.className = "media-bbox media-bbox--draft";
    editor.overlayElement.appendChild(editor.draftElement);
  }

  function updateDraft(event) {
    if (editor.resizeState && editor.overlayElement) {
      const bounds = editor.overlayElement.getBoundingClientRect();
      const naturalSize = getNaturalSize();
      const scaleX = bounds.width > 0 ? naturalSize.width / bounds.width : 1;
      const scaleY = bounds.height > 0 ? naturalSize.height / bounds.height : 1;
      const deltaX = Math.round((event.clientX - editor.resizeState.startClientX) * scaleX);
      const deltaY = Math.round((event.clientY - editor.resizeState.startClientY) * scaleY);
      const [startXMin, startYMin, startXMax, startYMax] = editor.resizeState.originalPoints;
      const minWidth = 8;
      const minHeight = 8;
      const maxWidth = Math.max((naturalSize.width || 0) - startXMin, minWidth);
      const maxHeight = Math.max((naturalSize.height || 0) - startYMin, minHeight);
      const nextWidth = clamp((startXMax - startXMin) + deltaX, minWidth, maxWidth);
      const nextHeight = clamp((startYMax - startYMin) + deltaY, minHeight, maxHeight);

      editor.resizeState.moved =
        editor.resizeState.moved ||
        Math.abs(event.clientX - editor.resizeState.startClientX) > 3 ||
        Math.abs(event.clientY - editor.resizeState.startClientY) > 3;
      editor.resizeState.annotation.points = [
        startXMin,
        startYMin,
        startXMin + nextWidth,
        startYMin + nextHeight,
      ];
      renderBoxes();
      renderAnnotationList();
      updateResultPreview();
      return;
    }

    if (editor.dragState && editor.overlayElement) {
      const bounds = editor.overlayElement.getBoundingClientRect();
      const naturalSize = getNaturalSize();
      const scaleX = bounds.width > 0 ? naturalSize.width / bounds.width : 1;
      const scaleY = bounds.height > 0 ? naturalSize.height / bounds.height : 1;
      const deltaX = Math.round((event.clientX - editor.dragState.startClientX) * scaleX);
      const deltaY = Math.round((event.clientY - editor.dragState.startClientY) * scaleY);
      const [startXMin, startYMin, startXMax, startYMax] = editor.dragState.originalPoints;
      const boxWidth = startXMax - startXMin;
      const boxHeight = startYMax - startYMin;
      const maxX = Math.max((naturalSize.width || 0) - boxWidth, 0);
      const maxY = Math.max((naturalSize.height || 0) - boxHeight, 0);
      const nextXMin = clamp(startXMin + deltaX, 0, maxX);
      const nextYMin = clamp(startYMin + deltaY, 0, maxY);

      editor.dragState.moved =
        editor.dragState.moved ||
        Math.abs(event.clientX - editor.dragState.startClientX) > 3 ||
        Math.abs(event.clientY - editor.dragState.startClientY) > 3;
      editor.dragState.annotation.points = [
        nextXMin,
        nextYMin,
        nextXMin + boxWidth,
        nextYMin + boxHeight,
      ];
      renderBoxes();
      renderAnnotationList();
      updateResultPreview();
      return;
    }

    if (!editor.draftStart || !editor.draftElement || !editor.overlayElement) {
      return;
    }

    const bounds = editor.overlayElement.getBoundingClientRect();
    const currentX = Math.min(Math.max(event.clientX - bounds.left, 0), bounds.width);
    const currentY = Math.min(Math.max(event.clientY - bounds.top, 0), bounds.height);
    const left = Math.min(editor.draftStart.x, currentX);
    const top = Math.min(editor.draftStart.y, currentY);
    const width = Math.abs(currentX - editor.draftStart.x);
    const height = Math.abs(currentY - editor.draftStart.y);

    editor.draftElement.style.left = `${left}px`;
    editor.draftElement.style.top = `${top}px`;
    editor.draftElement.style.width = `${width}px`;
    editor.draftElement.style.height = `${height}px`;
  }

  function finishDrawing(event) {
    if (editor.resizeState) {
      if (editor.resizeState.moved) {
        editor.suppressLabelClickUntil = Date.now() + 150;
      }
      editor.resizeState = null;
      return;
    }

    if (editor.dragState) {
      if (editor.dragState.moved) {
        editor.suppressLabelClickUntil = Date.now() + 150;
      }
      editor.dragState = null;
      return;
    }

    if (!editor.draftStart || !editor.overlayElement) {
      return;
    }

    const bounds = editor.overlayElement.getBoundingClientRect();
    const currentX = Math.min(Math.max(event.clientX - bounds.left, 0), bounds.width);
    const currentY = Math.min(Math.max(event.clientY - bounds.top, 0), bounds.height);
    const left = Math.min(editor.draftStart.x, currentX);
    const top = Math.min(editor.draftStart.y, currentY);
    const width = Math.abs(currentX - editor.draftStart.x);
    const height = Math.abs(currentY - editor.draftStart.y);

    if (width >= 8 && height >= 8) {
      const naturalSize = getNaturalSize();
      const xScale = bounds.width > 0 ? naturalSize.width / bounds.width : 1;
      const yScale = bounds.height > 0 ? naturalSize.height / bounds.height : 1;

      editor.annotations.push({
        local_id: `${Date.now()}-${Math.random()}`,
        type: "bbox",
        label_id: editor.activeLabelId,
        points: [
          Math.round(left * xScale),
          Math.round(top * yScale),
          Math.round((left + width) * xScale),
          Math.round((top + height) * yScale),
        ],
        frame: getCurrentFrame(),
        attributes: [],
        occluded: false,
      });
    }

    clearDraft();
    render();
  }

  function attachOverlayEvents() {
    if (!editor.overlayElement) {
      return;
    }

    editor.overlayElement.addEventListener("mousedown", (event) => {
      if (event.target !== editor.overlayElement) {
        return;
      }
      startDrawing(event);
    });

    if (editor.eventsAttached) {
      return;
    }

    window.addEventListener("mousemove", updateDraft);
    window.addEventListener("mouseup", finishDrawing);
    window.addEventListener("resize", renderBoxes);
    editor.eventsAttached = true;
  }

  clearBtn?.addEventListener("click", () => {
    editor.annotations = [];
    render();
  });

  function reset() {
    editor.annotations = [];
    editor.activeLabelId = null;
    editor.mediaElement = null;
    editor.overlayElement = null;
    clearDraft();
    editor.dragState = null;
    editor.resizeState = null;
    mediaTool.classList.add("hidden");
    mediaStage.className = "media-stage empty-card";
    mediaStage.textContent = "Файл задачи загрузится после выбора задания.";
    resultLabel.textContent = "Результат разметки";
    resultJson.readOnly = false;
    render();
  }

  function loadTask(task) {
    if (!task || !["image", "video"].includes(task.source_type) || !task.source_file_url) {
      reset();
      return;
    }

    mediaTool.classList.remove("hidden");
    instructions.textContent =
      task.source_type === "video"
        ? "Поставь видео на паузу на нужном кадре, зажми левую кнопку мыши и выдели область. Новое выделение сразу получит активный label. Зажми существующую область, чтобы переместить ее, потяни за правый нижний угол, чтобы изменить размер, или выбери другой label и кликни по области один раз, чтобы поменять label."
        : "Зажми левую кнопку мыши и выдели область. Новое выделение сразу получит активный label. Зажми существующую область, чтобы переместить ее, потяни за правый нижний угол, чтобы изменить размер, или выбери другой label и кликни по области один раз, чтобы поменять label.";
    resultLabel.textContent = "Результат bbox-разметки";
    resultJson.readOnly = true;
    editor.annotations = [];

    const wrapper = document.createElement("div");
    wrapper.className = "media-canvas";
    const overlay = document.createElement("div");
    overlay.className = "media-overlay";

    let mediaElement;
    if (task.source_type === "video") {
      mediaElement = document.createElement("video");
      mediaElement.controls = true;
      mediaElement.preload = "metadata";
      mediaElement.addEventListener("loadedmetadata", renderBoxes);
      mediaElement.addEventListener("seeked", renderBoxes);
      mediaElement.addEventListener("pause", renderBoxes);
    } else {
      mediaElement = document.createElement("img");
      mediaElement.alt = task.source_name || `Task ${task.id}`;
      mediaElement.addEventListener("load", renderBoxes);
    }
    mediaElement.className = "media-stage__asset";
    mediaElement.src = task.source_file_url;

    wrapper.appendChild(mediaElement);
    wrapper.appendChild(overlay);
    mediaStage.className = "media-stage";
    mediaStage.innerHTML = "";
    mediaStage.appendChild(wrapper);

    editor.mediaElement = mediaElement;
    editor.overlayElement = overlay;
    attachOverlayEvents();
    render();
  }

  return {
    reset,
    loadTask,
    hasUnlabeledAnnotations() {
      return editor.annotations.some((annotation) => !annotation.label_id);
    },
  };
}

function initRoomWorkPage() {
  if (!currentRoomId) {
    showFlash("Не удалось определить ID комнаты из URL.", "error");
    state.pageRefresh = async () => {};
    return;
  }

  const joinBtn = document.getElementById("work-join-btn");
  const taskBox = document.getElementById("work-task-box");
  const submitForm = document.getElementById("work-submit-form");
  const resultJson = document.getElementById("work-result-json");
  const resultLabel = document.getElementById("work-result-label");
  const submitBtn = submitForm?.querySelector('button[type="submit"]');

  const mediaEditor = createMediaAnnotationEditor({
    mediaTool: document.getElementById("work-media-tool"),
    instructions: document.getElementById("work-media-instructions"),
    labelPalette: document.getElementById("work-label-palette"),
    activeLabelNote: document.getElementById("work-active-label"),
    mediaStage: document.getElementById("work-media-stage"),
    annotationList: document.getElementById("work-annotation-list"),
    clearBtn: document.getElementById("work-clear-annotations-btn"),
    resultJson,
    resultLabel,
    submitBtn,
  });

  function resetCurrentTask(message) {
    state.currentTask = null;
    submitForm.classList.add("hidden");
    mediaEditor.reset();
    renderEmptyTaskBox(taskBox, message);
  }

  function prepareTaskForm(task) {
    renderCurrentTask(taskBox, task);
    submitForm.classList.toggle("hidden", !task);

    if (!task) {
      mediaEditor.reset();
      return;
    }

    if (["image", "video"].includes(task.source_type)) {
      mediaEditor.loadTask(task);
      return;
    }

    mediaEditor.reset();
    resultLabel.textContent = "Результат разметки";
    resultJson.readOnly = false;
    resultJson.value = JSON.stringify(
      {
        label: "positive",
        confidence: 0.95,
      },
      null,
      2
    );
    if (submitBtn) {
      submitBtn.disabled = false;
    }
  }

  async function loadNextTask({ emptyMessage }) {
    const task = await api(`/api/v1/rooms/${currentRoomId}/tasks/next/`);
    state.currentTask = task;
    prepareTaskForm(task);

    if (!task) {
      renderEmptyTaskBox(taskBox, emptyMessage || "Доступных задач больше нет.");
      if (emptyMessage) {
        showFlash(emptyMessage, "success");
      }
      return null;
    }
    return task;
  }

  async function loadDashboard() {
    const dashboard = await api(`/api/v1/rooms/${currentRoomId}/dashboard/`);
    state.roomDashboard = dashboard;

    if (dashboard.actor.role !== "annotator") {
      showFlash("Рабочая среда доступна только исполнителю комнаты.", "error");
      window.setTimeout(() => {
        window.location.href = `/rooms/${currentRoomId}/`;
      }, 900);
      return;
    }

    const isJoined = dashboard.room.membership_status === "joined";
    joinBtn?.classList.toggle("hidden", isJoined);
    if (joinBtn) {
      joinBtn.disabled = isJoined;
      joinBtn.textContent = "Войти в комнату";
    }

    if (!isJoined) {
      resetCurrentTask("Сначала войди в комнату, чтобы получить задачу на разметку.");
    } else if (!state.currentTask) {
      await loadNextTask({
        emptyMessage: "Доступных задач больше нет.",
      });
    }
  }

  joinBtn?.addEventListener("click", async () => {
    clearFlash();
    try {
      await api(`/api/v1/rooms/${currentRoomId}/join/`, { method: "POST", body: {} });
      await loadDashboard();
    } catch (error) {
      showFlash(error.message, "error");
    }
  });

  submitForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFlash();

    if (!state.currentTask) {
      showFlash("Подожди загрузки задачи.", "error");
      return;
    }

    if (["image", "video"].includes(state.currentTask.source_type) && mediaEditor.hasUnlabeledAnnotations()) {
      showFlash("Назначь лейблы всем выделенным областям перед отправкой.", "error");
      return;
    }

    let payload;
    try {
      payload = JSON.parse(resultJson.value);
    } catch (error) {
      showFlash("Результат должен быть валидным JSON.", "error");
      return;
    }

    try {
      const completedTaskId = state.currentTask.id;
      await api(`/api/v1/tasks/${state.currentTask.id}/submit/`, {
        method: "POST",
        body: { result_payload: payload },
      });
      resetCurrentTask("Загружаем следующую задачу...");
      await loadDashboard();
      if (!state.currentTask) {
        showFlash(`Задача #${completedTaskId} успешно размечена. Доступных задач больше нет.`, "success");
      } else {
        showFlash(`Задача #${completedTaskId} успешно размечена. Следующая задача уже готова.`, "success");
      }
    } catch (error) {
      showFlash(error.message, "error");
    }
  });

  state.pageRefresh = async () => {
    if (!state.user) {
      return;
    }

    try {
      await loadDashboard();
    } catch (error) {
      showFlash(error.message, "error");
    }
  };
}

function initPage() {
  switch (currentPage) {
    case "rooms":
      initRoomsPage();
      break;
    case "profile":
      initProfilePage();
      break;
    case "room-create":
      initRoomCreatePage();
      break;
    case "room-detail":
      initRoomDetailPage();
      break;
    case "room-work":
      initRoomWorkPage();
      break;
    default:
      state.pageRefresh = async () => {};
      break;
  }
}

initPage();
initGlobalHeader();
