(() => {
  "use strict";

  const STORAGE_KEY = "mein-aufgabenplaner-aufgaben-v1";
  const MONTH_NAMES = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
  ];
  const WEEKDAY_NAMES = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
  const EXPIRY_MS = 15 * 60 * 1000;

  const elements = {
    form: document.querySelector("#task-form"),
    title: document.querySelector("#task-title"),
    details: document.querySelector("#task-details"),
    year: document.querySelector("#task-year"),
    month: document.querySelector("#task-month"),
    day: document.querySelector("#task-day"),
    hour: document.querySelector("#task-hour"),
    minute: document.querySelector("#task-minute"),
    todayDate: document.querySelector("#today-date"),
    todayList: document.querySelector("#today-list"),
    todayEmpty: document.querySelector("#today-empty"),
    calendarMonth: document.querySelector("#calendar-month"),
    calendarGrid: document.querySelector("#calendar-grid"),
    previousMonth: document.querySelector("#previous-month"),
    nextMonth: document.querySelector("#next-month"),
    selectedDate: document.querySelector("#selected-date"),
    selectedCount: document.querySelector("#selected-count"),
    calendarList: document.querySelector("#calendar-list"),
    calendarEmpty: document.querySelector("#calendar-empty"),
    forgottenList: document.querySelector("#forgotten-list"),
    forgottenEmpty: document.querySelector("#forgotten-empty"),
    forgottenCount: document.querySelector("#forgotten-count"),
    taskMenu: document.querySelector("#task-menu"),
    detailsDialog: document.querySelector("#details-dialog"),
    detailsTitle: document.querySelector("#details-title"),
    detailsWhen: document.querySelector("#details-when"),
    detailsText: document.querySelector("#details-text"),
    editDialog: document.querySelector("#edit-dialog"),
    editForm: document.querySelector("#edit-form"),
    editTitle: document.querySelector("#edit-title"),
    editDate: document.querySelector("#edit-date"),
    editTime: document.querySelector("#edit-time"),
    editDetails: document.querySelector("#edit-details"),
    toast: document.querySelector("#toast"),
  };

  const today = localDate(new Date());
  let selectedDate = today;
  let calendarMonth = new Date(`${today}T12:00:00`);
  calendarMonth.setDate(1);
  let tasks = loadTasks();
  let selectedTaskId = null;
  let toastTimer = null;
  let expiryTimer = null;

  function localDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function loadTasks() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (!saved) return [];
      const parsed = JSON.parse(saved);
      if (!Array.isArray(parsed)) throw new Error("Die gespeicherten Aufgaben sind ungültig.");
      return parsed.map((task) => ({
        ...task,
        details: typeof task.details === "string" ? task.details : "",
        forgotten: Boolean(task.forgotten),
      }));
    } catch (error) {
      window.setTimeout(() => showToast(`Aufgaben konnten nicht geladen werden: ${error.message}`), 0);
      return [];
    }
  }

  function saveTasks() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
      return true;
    } catch (error) {
      showToast(`Speichern fehlgeschlagen: ${error.message}`);
      return false;
    }
  }

  function showToast(message) {
    elements.toast.textContent = message;
    elements.toast.classList.add("is-visible");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      elements.toast.classList.remove("is-visible");
    }, 3500);
  }

  function setSelectOptions(select, values, selected) {
    select.replaceChildren(
      ...values.map((value) => {
        const option = document.createElement("option");
        option.value = value.value;
        option.textContent = value.label;
        option.selected = value.value === selected;
        return option;
      }),
    );
  }

  function initializeDateSelectors() {
    const todayDate = new Date(`${today}T12:00:00`);
    const years = [];
    for (let year = todayDate.getFullYear(); year <= todayDate.getFullYear() + 6; year += 1) {
      years.push({ value: String(year), label: String(year) });
    }
    setSelectOptions(elements.year, years, String(todayDate.getFullYear()));
    setSelectOptions(
      elements.month,
      MONTH_NAMES.map((name, index) => ({
        value: String(index + 1).padStart(2, "0"),
        label: name,
      })),
      String(todayDate.getMonth() + 1).padStart(2, "0"),
    );
    updateDayOptions(String(todayDate.getDate()));
    elements.year.addEventListener("change", () => updateDayOptions());
    elements.month.addEventListener("change", () => updateDayOptions());

    const now = new Date();
    let hour = now.getHours();
    let minute = Math.ceil(now.getMinutes() / 5) * 5;
    if (minute === 60) {
      minute = 0;
      hour = (hour + 1) % 24;
    }
    const hours = Array.from({ length: 24 }, (_, value) => ({
      value: String(value).padStart(2, "0"),
      label: String(value).padStart(2, "0"),
    }));
    const minutes = Array.from({ length: 12 }, (_, index) => {
      const value = String(index * 5).padStart(2, "0");
      return { value, label: value };
    });
    setSelectOptions(elements.hour, hours, String(hour).padStart(2, "0"));
    setSelectOptions(elements.minute, minutes, String(minute).padStart(2, "0"));
    setSelectOptions(
      elements.editTime,
      Array.from({ length: 288 }, (_, index) => {
        const h = String(Math.floor(index / 12)).padStart(2, "0");
        const m = String((index % 12) * 5).padStart(2, "0");
        return { value: `${h}:${m}`, label: `${h}:${m}` };
      }),
      "00:00",
    );
  }

  function updateDayOptions(preferredDay) {
    const year = Number(elements.year.value);
    const month = Number(elements.month.value);
    const dayCount = new Date(year, month, 0).getDate();
    const previousDay = preferredDay || elements.day.value || "1";
    const days = Array.from({ length: dayCount }, (_, index) => {
      const value = String(index + 1).padStart(2, "0");
      return { value, label: String(index + 1) };
    });
    const selected = String(Math.min(Number(previousDay) || 1, dayCount)).padStart(2, "0");
    setSelectOptions(elements.day, days, selected);
  }

  function selectedFormDate() {
    return `${elements.year.value}-${elements.month.value}-${elements.day.value}`;
  }

  function formatDate(dateString, options = { day: "numeric", month: "long", year: "numeric" }) {
    const date = new Date(`${dateString}T12:00:00`);
    return new Intl.DateTimeFormat("de-DE", options).format(date);
  }

  function dueTime(task) {
    return task.time || "23:59";
  }

  function compareTasks(a, b) {
    return dueTime(a).localeCompare(dueTime(b)) || a.title.localeCompare(b.title, "de");
  }

  function tasksForDate(dateString) {
    return tasks
      .filter((task) => task.date === dateString)
      .sort(compareTasks);
  }

  function isExpired(task, now = Date.now()) {
    if (!task.date || !task.time) return false;
    const due = new Date(`${task.date}T${task.time}:00`).getTime();
    return Number.isFinite(due) && now >= due + EXPIRY_MS;
  }

  function markExpiredTasks() {
    let changed = false;
    const now = Date.now();
    for (const task of tasks) {
      if (!task.forgotten && isExpired(task, now)) {
        task.forgotten = true;
        changed = true;
      }
    }
    if (changed) {
      if (saveTasks()) renderAll();
      else tasks.forEach((task) => {
        if (isExpired(task, now)) task.forgotten = false;
      });
    }
    scheduleExpiryCheck();
  }

  function scheduleExpiryCheck() {
    window.clearTimeout(expiryTimer);
    const nextExpiry = tasks
      .filter((task) => !task.forgotten && task.date && task.time)
      .map((task) => new Date(`${task.date}T${task.time}:00`).getTime() + EXPIRY_MS)
      .filter((timestamp) => timestamp > Date.now())
      .sort((a, b) => a - b)[0];
    if (nextExpiry) {
      expiryTimer = window.setTimeout(markExpiredTasks, Math.max(1000, nextExpiry - Date.now()));
    }
  }

  function createTaskCard(task, mode = "today") {
    const card = document.createElement("article");
    card.className = `task-card${task.forgotten ? " is-forgotten" : ""}`;
    card.dataset.taskId = task.id;

    const main = document.createElement("div");
    main.className = "task-main";
    const title = document.createElement("p");
    title.className = "task-title";
    title.textContent = task.title;
    main.append(title);

    const meta = document.createElement("div");
    meta.className = "task-meta";
    const time = document.createElement("span");
    time.textContent = mode === "forgotten"
      ? `${task.date ? formatDate(task.date, { day: "numeric", month: "short" }) : ""}${task.time ? ` · ${task.time}` : ""}`.trim() || "Termin nicht festgelegt"
      : task.time || "Uhrzeit nicht festgelegt";
    meta.append(time);
    if (task.details) {
      const details = document.createElement("span");
      details.textContent = "Mit Details";
      meta.append(details);
    }
    if (task.forgotten && mode !== "forgotten") {
      const badge = document.createElement("span");
      badge.textContent = "Vergessen";
      meta.append(badge);
    }
    main.append(meta);

    const actions = document.createElement("div");
    actions.className = "task-actions";
    const menuButton = document.createElement("button");
    menuButton.type = "button";
    menuButton.className = "task-menu-trigger";
    menuButton.setAttribute("aria-label", `Aktionen für ${task.title}`);
    menuButton.setAttribute("aria-haspopup", "menu");
    menuButton.textContent = "⋯";
    menuButton.addEventListener("click", (event) => {
      event.stopPropagation();
      const rect = menuButton.getBoundingClientRect();
      showTaskMenu(task.id, rect.right, rect.bottom + 5);
    });
    card.addEventListener("contextmenu", (event) => {
      event.preventDefault();
      showTaskMenu(task.id, event.clientX, event.clientY);
    });
    let pressTimer;
    card.addEventListener("touchstart", (event) => {
      const touch = event.touches[0];
      pressTimer = window.setTimeout(() => {
        showTaskMenu(task.id, touch.clientX, touch.clientY);
      }, 600);
    }, { passive: true });
    card.addEventListener("touchend", () => window.clearTimeout(pressTimer));
    card.addEventListener("touchmove", () => window.clearTimeout(pressTimer));
    actions.append(menuButton);
    card.append(main, actions);
    return card;
  }

  function renderTaskList(container, emptyMessage, items, mode) {
    container.replaceChildren(...items.map((task) => createTaskCard(task, mode)));
    emptyMessage.hidden = items.length > 0;
  }

  function renderToday() {
    elements.todayDate.textContent = new Intl.DateTimeFormat("de-DE", {
      weekday: "long", day: "numeric", month: "long", year: "numeric",
    }).format(new Date(`${today}T12:00:00`));
    renderTaskList(
      elements.todayList,
      elements.todayEmpty,
      tasksForDate(today),
      "today",
    );
  }

  function addMonthsClamped(start, offset) {
    const monthIndex = start.getMonth() + offset;
    const year = start.getFullYear() + Math.floor(monthIndex / 12);
    const month = ((monthIndex % 12) + 12) % 12;
    const day = Math.min(start.getDate(), new Date(year, month + 1, 0).getDate());
    return new Date(year, month, day, 12);
  }

  function renderCalendar() {
    const first = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth(), 1, 12);
    elements.calendarMonth.textContent = new Intl.DateTimeFormat("de-DE", {
      month: "long", year: "numeric",
    }).format(first);

    const currentMonth = new Date(today + "T12:00:00");
    currentMonth.setDate(1);
    const lastMonthDate = addMonthsClamped(new Date(today + "T12:00:00"), 6);
    lastMonthDate.setDate(1);
    const currentIndex = first.getFullYear() * 12 + first.getMonth();
    const minIndex = currentMonth.getFullYear() * 12 + currentMonth.getMonth();
    const maxIndex = lastMonthDate.getFullYear() * 12 + lastMonthDate.getMonth();
    elements.previousMonth.disabled = currentIndex <= minIndex;
    elements.nextMonth.disabled = currentIndex >= maxIndex;

    const labels = WEEKDAY_NAMES.map((name) => {
      const label = document.createElement("span");
      label.className = "weekday-label";
      label.textContent = name;
      return label;
    });
    const offset = (first.getDay() + 6) % 7;
    const daysInMonth = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate();
    const cells = Array.from({ length: 42 }, (_, index) => {
      const dayNumber = index - offset + 1;
      const cell = document.createElement("span");
      if (dayNumber < 1 || dayNumber > daysInMonth) {
        cell.className = "calendar-day is-outside";
        cell.setAttribute("aria-hidden", "true");
        return cell;
      }
      const dateString = `${first.getFullYear()}-${String(first.getMonth() + 1).padStart(2, "0")}-${String(dayNumber).padStart(2, "0")}`;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "calendar-day";
      if (dateString === today) button.classList.add("is-today");
      if (dateString === selectedDate) button.classList.add("is-selected");
      button.setAttribute("aria-label", `${formatDate(dateString)}: ${tasksForDate(dateString).length} Aufgaben`);
      button.setAttribute("aria-pressed", String(dateString === selectedDate));
      const dayLabel = document.createElement("span");
      dayLabel.className = "day-number";
      dayLabel.textContent = String(dayNumber);
      const count = document.createElement("span");
      count.className = "calendar-task-count";
      const taskCount = tasksForDate(dateString).length;
      count.textContent = taskCount ? `${taskCount} ${taskCount === 1 ? "Aufgabe" : "Aufgaben"}` : " ";
      button.append(dayLabel, count);
      button.addEventListener("click", () => {
        selectedDate = dateString;
        renderCalendar();
      });
      return button;
    });
    elements.calendarGrid.replaceChildren(...labels, ...cells);

    elements.selectedDate.textContent = new Intl.DateTimeFormat("de-DE", {
      weekday: "long", day: "numeric", month: "long", year: "numeric",
    }).format(new Date(`${selectedDate}T12:00:00`));
    const dayTasks = tasksForDate(selectedDate);
    elements.selectedCount.textContent = `${dayTasks.length} ${dayTasks.length === 1 ? "Aufgabe" : "Aufgaben"}`;
    renderTaskList(
      elements.calendarList,
      elements.calendarEmpty,
      dayTasks,
      "calendar",
    );
  }

  function renderForgotten() {
    const forgotten = tasks
      .filter((task) => task.forgotten)
      .sort((a, b) => (a.date || "").localeCompare(b.date || "") || compareTasks(a, b));
    renderTaskList(elements.forgottenList, elements.forgottenEmpty, forgotten, "forgotten");
    elements.forgottenCount.textContent = String(forgotten.length);
  }

  function renderAll() {
    renderToday();
    renderCalendar();
    renderForgotten();
  }

  function showTaskMenu(taskId, x, y) {
    selectedTaskId = taskId;
    const menu = elements.taskMenu;
    menu.hidden = false;
    const width = menu.offsetWidth;
    const height = menu.offsetHeight;
    menu.style.left = `${Math.max(8, Math.min(x, window.innerWidth - width - 8))}px`;
    menu.style.top = `${Math.max(8, Math.min(y, window.innerHeight - height - 8))}px`;
  }

  function hideTaskMenu() {
    elements.taskMenu.hidden = true;
    selectedTaskId = null;
  }

  function findTask(id) {
    return tasks.find((task) => task.id === id);
  }

  function showDetails(id) {
    const task = findTask(id);
    if (!task) return;
    elements.detailsTitle.textContent = task.title;
    elements.detailsWhen.textContent = `${formatDate(task.date)} · ${task.time || "Keine Uhrzeit"}`;
    elements.detailsText.textContent = task.details || "Keine Details eingetragen.";
    elements.detailsDialog.showModal();
  }

  function editTask(id) {
    const task = findTask(id);
    if (!task) return;
    elements.editTitle.value = task.title;
    elements.editDate.value = task.date;
    elements.editTime.value = task.time || "00:00";
    elements.editDetails.value = task.details || "";
    elements.editDialog.dataset.taskId = id;
    elements.editDialog.showModal();
  }

  function deleteTask(id) {
    const task = findTask(id);
    if (!task || !window.confirm(`„${task.title}“ wirklich löschen?`)) return;
    const previous = tasks;
    tasks = tasks.filter((entry) => entry.id !== id);
    if (!saveTasks()) {
      tasks = previous;
      return;
    }
    renderAll();
    scheduleExpiryCheck();
    showToast("Aufgabe gelöscht.");
  }

  elements.form.addEventListener("submit", (event) => {
    event.preventDefault();
    const title = elements.title.value.trim();
    if (!title) {
      elements.title.focus();
      return;
    }
    const task = {
      id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
      title,
      date: selectedFormDate(),
      time: `${elements.hour.value}:${elements.minute.value}`,
      details: elements.details.value.trim(),
      forgotten: false,
    };
    tasks.push(task);
    if (!saveTasks()) {
      tasks.pop();
      return;
    }
    elements.form.reset();
    elements.title.focus();
    initializeDateSelectors();
    renderAll();
    scheduleExpiryCheck();
    showToast("Aufgabe hinzugefügt ✨");
  });

  elements.editForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const task = findTask(elements.editDialog.dataset.taskId);
    const title = elements.editTitle.value.trim();
    if (!task || !title || !elements.editDate.value || !elements.editTime.value) return;
    const previous = { ...task };
    Object.assign(task, {
      title,
      date: elements.editDate.value,
      time: elements.editTime.value,
      details: elements.editDetails.value.trim(),
      forgotten: false,
    });
    if (!saveTasks()) {
      Object.assign(task, previous);
      return;
    }
    elements.editDialog.close();
    renderAll();
    scheduleExpiryCheck();
    showToast("Änderungen gespeichert.");
  });

  elements.taskMenu.addEventListener("click", (event) => {
    const action = event.target.closest("[data-action]")?.dataset.action;
    const id = selectedTaskId;
    hideTaskMenu();
    if (!id || !action) return;
    if (action === "details") showDetails(id);
    if (action === "edit") editTask(id);
    if (action === "delete") deleteTask(id);
  });

  document.addEventListener("click", (event) => {
    if (!elements.taskMenu.hidden && !elements.taskMenu.contains(event.target)) {
      hideTaskMenu();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") hideTaskMenu();
  });

  document.querySelectorAll(".view-tab").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".view-tab").forEach((tab) => {
        tab.classList.toggle("is-active", tab === button);
      });
      document.querySelectorAll(".view-panel").forEach((panel) => {
        panel.hidden = panel.id !== `view-${button.dataset.view}`;
      });
    });
  });

  elements.previousMonth.addEventListener("click", () => {
    calendarMonth = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() - 1, 1, 12);
    renderCalendar();
  });
  elements.nextMonth.addEventListener("click", () => {
    calendarMonth = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1, 1, 12);
    renderCalendar();
  });
  elements.editDialog.querySelector("[data-close-edit]").addEventListener("click", () => {
    elements.editDialog.close();
  });

  initializeDateSelectors();
  renderAll();
  markExpiredTasks();
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) markExpiredTasks();
  });
  window.addEventListener("pageshow", markExpiredTasks);

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/planer/service-worker.js", { scope: "/planer/" })
      .catch((error) => showToast(`Offline-Installation nicht verfügbar: ${error.message}`));
  }
})();
