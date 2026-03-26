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

async function api(path, options = {}) {
  if (!state.user) {
    throw new Error("Сначала войди в аккаунт.");
  }

  const requestOptions = {
    method: options.method || "GET",
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": String(state.user.id),
      ...(options.headers || {}),
    },
  };

  if (options.body !== undefined) {
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
    throw new Error(data?.detail || `HTTP ${response.status}`);
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

function formatMonthLabel(dateString) {
  return new Intl.DateTimeFormat("ru-RU", { month: "short" })
    .format(new Date(`${dateString}T00:00:00`))
    .replace(".", "");
}

function shiftDateString(dateString, days) {
  const date = new Date(`${dateString}T00:00:00`);
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
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
    const date = new Date(`${item.date}T00:00:00`);
    const monthKey = `${date.getFullYear()}-${date.getMonth()}`;
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

function buildCalendarSeries(series, targetWeekCount = 12) {
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

  const targetWeekCount = 12;
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
    const isReady = roomIdInput.value.trim() && passwordInput.value.trim();
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

function initRoomCreatePage() {
  const form = document.getElementById("room-create-form");

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFlash();

    const formData = new FormData(form);
    const annotatorIds = (formData.get("annotator_ids") || "")
      .toString()
      .split(",")
      .map((item) => Number(item.trim()))
      .filter((item) => Number.isInteger(item) && item > 0);

    const deadlineValue = formData.get("deadline");
    const payload = {
      title: formData.get("title"),
      description: formData.get("description"),
      password: formData.get("password"),
      annotator_ids: annotatorIds,
      dataset_mode: "demo",
      test_task_count: Number(formData.get("test_task_count") || 12),
      dataset_label: formData.get("dataset_label") || "Тестовый датасет",
    };

    if (deadlineValue) {
      payload.deadline = new Date(deadlineValue.toString()).toISOString();
    }

    try {
      const room = await api("/api/v1/rooms/", {
        method: "POST",
        body: payload,
      });
      showFlash(`Комната #${room.id} создана. Переходим к ней.`, "success");
      window.setTimeout(() => {
        window.location.href = `/rooms/${room.id}/`;
      }, 700);
    } catch (error) {
      showFlash(error.message, "error");
    }
  });

  state.pageRefresh = async () => {
    return;
  };
}

function renderCurrentTask(taskBox, task) {
  if (!task) {
    taskBox.className = "empty-card";
    taskBox.textContent = "Задача пока не выбрана.";
    return;
  }

  taskBox.className = "task-box";
  taskBox.innerHTML = `
    <strong>Задача #${task.id}</strong>
    <div>Статус: ${translateTaskStatus(task.status)}</div>
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

function initRoomDetailPage() {
  const title = document.getElementById("room-title");
  const subtitle = document.getElementById("room-subtitle");
  const roomHeaderMeta = document.getElementById("room-header-meta");
  const roomMetrics = document.getElementById("room-metrics");
  const annotatorWorkspace = document.getElementById("annotator-workspace");
  const customerWorkspace = document.getElementById("customer-workspace");
  const annotatorSummary = document.getElementById("annotator-summary");
  const annotatorActivity = document.getElementById("annotator-activity");
  const joinBtn = document.getElementById("detail-join-btn");
  const nextTaskBtn = document.getElementById("detail-next-task-btn");
  const taskBox = document.getElementById("detail-task-box");
  const submitForm = document.getElementById("detail-submit-form");
  const resultJson = document.getElementById("detail-result-json");
  const annotatorsList = document.getElementById("annotators-list");
  const annotatorDetailPanel = document.getElementById("annotator-detail-panel");
  const annotatorDetailActivity = document.getElementById("annotator-detail-activity");
  const inviteForm = document.getElementById("detail-invite-form");
  const inviteUserIdInput = document.getElementById("detail-invite-user-id");

  async function loadDashboard() {
    const dashboard = await api(`/api/v1/rooms/${currentRoomId}/dashboard/`);
    state.roomDashboard = dashboard;

    title.textContent = dashboard.room.title;
    subtitle.textContent = dashboard.room.description || "Описание для этой комнаты пока не заполнено.";
    roomHeaderMeta.innerHTML = `
      <div class="summary-stack">
        <div class="summary-row"><span>ID комнаты</span><strong>#${dashboard.room.id}</strong></div>
        <div class="summary-row"><span>Датасет</span><strong>${dashboard.room.dataset_label || "Тестовый датасет"}</strong></div>
        <div class="summary-row"><span>Дедлайн</span><strong>${formatDate(dashboard.room.deadline)}</strong></div>
        <div class="summary-row"><span>Доступ</span><strong>${dashboard.room.has_password ? "С паролем" : "Без пароля"}</strong></div>
      </div>
    `;

    renderMetricCards(roomMetrics, [
      { label: "Всего задач", value: dashboard.overview.total_tasks },
      { label: "Выполнено", value: dashboard.overview.completed_tasks },
      { label: "Осталось", value: dashboard.overview.remaining_tasks },
      { label: "Готовность", value: formatPercent(dashboard.overview.progress_percent) },
    ]);

    if (dashboard.actor.role === "annotator") {
      customerWorkspace.classList.add("hidden");
      annotatorWorkspace.classList.remove("hidden");

      renderSummaryRows(annotatorSummary, [
        { label: "Роль в комнате", value: translateRole(dashboard.actor.role) },
        { label: "Выполнено мной", value: dashboard.annotator_stats.completed_tasks },
        { label: "В работе", value: dashboard.annotator_stats.in_progress_tasks },
        { label: "Осталось", value: dashboard.annotator_stats.remaining_tasks },
        { label: "Мой прогресс", value: formatPercent(dashboard.annotator_stats.progress_percent) },
      ]);
      renderActivity(annotatorActivity, dashboard.annotator_stats.activity);

      const isJoined = dashboard.room.membership_status === "joined";
      joinBtn.disabled = isJoined;
      joinBtn.textContent = isJoined ? "Вы уже в комнате" : "Войти в комнату";
    } else {
      annotatorWorkspace.classList.add("hidden");
      customerWorkspace.classList.remove("hidden");
      renderCustomerView(dashboard);
    }
  }

  function renderCustomerView(dashboard) {
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

  joinBtn?.addEventListener("click", async () => {
    clearFlash();
    try {
      await api(`/api/v1/rooms/${currentRoomId}/join/`, { method: "POST", body: {} });
      showFlash("Ты вошел в комнату. Теперь можно брать задачи.", "success");
      await loadDashboard();
    } catch (error) {
      showFlash(error.message, "error");
    }
  });

  nextTaskBtn?.addEventListener("click", async () => {
    clearFlash();
    try {
      const task = await api(`/api/v1/rooms/${currentRoomId}/tasks/next/`);
      state.currentTask = task;
      renderCurrentTask(taskBox, task);
      submitForm.classList.toggle("hidden", !task);
      showFlash(task ? `Задача #${task.id} готова к разметке.` : "Доступных задач больше нет.", "success");
    } catch (error) {
      showFlash(error.message, "error");
    }
  });

  submitForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFlash();

    if (!state.currentTask) {
      showFlash("Сначала возьми задачу.", "error");
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
      await api(`/api/v1/tasks/${state.currentTask.id}/submit/`, {
        method: "POST",
        body: { result_payload: payload },
      });
      showFlash(`Задача #${state.currentTask.id} успешно размечена.`, "success");
      state.currentTask = null;
      renderCurrentTask(taskBox, null);
      submitForm.classList.add("hidden");
      await loadDashboard();
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
    default:
      state.pageRefresh = async () => {};
      break;
  }
}

initPage();
initGlobalHeader();
