const PAGE_SIZE = 12;

const state = {
  tasks: [],
  query: "",
  domain: "all",
  scale: "all",
  showAll: false,
};

const taskBody = document.querySelector("#task-table-body");
const taskEmpty = document.querySelector("#task-empty");
const taskCount = document.querySelector("#task-count");
const searchInput = document.querySelector("#task-search");
const domainFilter = document.querySelector("#domain-filter");
const showAllButton = document.querySelector("#show-all-tasks");
const scaleButtons = [...document.querySelectorAll("[data-scale]")];

function escapeHTML(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function filteredTasks() {
  const query = state.query.trim().toLowerCase();
  return state.tasks.filter((task) => {
    const matchesQuery = !query || [
      task.project_id,
      task.paper_title,
      task.target_task,
      task.target_metric,
      task.evaluation_dataset,
    ].some((value) => value.toLowerCase().includes(query));
    const matchesDomain = state.domain === "all" || task.domain_key === state.domain;
    const matchesScale = state.scale === "all" || task.scale_key === state.scale;
    return matchesQuery && matchesDomain && matchesScale;
  });
}

function renderTasks() {
  const matches = filteredTasks();
  const visible = state.showAll ? matches : matches.slice(0, PAGE_SIZE);
  taskBody.innerHTML = visible.map((task) => `
    <tr>
      <td>
        <span class="task-title">${escapeHTML(task.paper_title)}</span>
        <span class="task-target">${escapeHTML(task.target_task)}</span>
      </td>
      <td><span class="domain-label">${escapeHTML(task.domain_label)}</span></td>
      <td>
        ${escapeHTML(task.target_metric)}
        <span class="metric-reference">ref. ${escapeHTML(task.reference_display)}</span>
      </td>
      <td><span class="scale-label ${task.scale_key}">${escapeHTML(task.scale_label)}</span></td>
      <td>${escapeHTML(task.wall_time_hours)} h<br>${escapeHTML(task.hardware_label)}</td>
      <td>
        <a class="repository-link" href="${escapeHTML(task.repository_url)}" aria-label="Open source repository for ${escapeHTML(task.paper_title)}" title="Source repository">
          <i data-lucide="arrow-up-right" aria-hidden="true"></i>
        </a>
      </td>
    </tr>
  `).join("");

  taskEmpty.hidden = matches.length !== 0;
  taskCount.textContent = `${matches.length} of ${state.tasks.length} tasks`;
  showAllButton.hidden = matches.length <= PAGE_SIZE || state.showAll;
  if (window.lucide) window.lucide.createIcons();
}

function populateDomains(domains) {
  domains.forEach((domain) => {
    const option = document.createElement("option");
    option.value = domain.key;
    option.textContent = `${domain.label} (${domain.count})`;
    domainFilter.append(option);
  });
}

async function loadTasks() {
  try {
    const response = await fetch("./data/tasks.json");
    if (!response.ok) throw new Error(`Task data returned ${response.status}`);
    const payload = await response.json();
    state.tasks = payload.tasks;
    populateDomains(payload.summary.domains);
    document.querySelector("#stat-tasks").textContent = payload.summary.task_count;
    document.querySelector("#stat-domains").textContent = payload.summary.domain_count;
    renderTasks();
  } catch (error) {
    taskCount.textContent = "Task inventory unavailable";
    taskEmpty.hidden = false;
    taskEmpty.textContent = "The task inventory could not be loaded.";
    console.error(error);
  }
}

async function loadLeaderboard() {
  const body = document.querySelector("#leaderboard-body");
  const empty = document.querySelector("#leaderboard-empty");
  const updated = document.querySelector("#leaderboard-updated");
  try {
    const response = await fetch("./data/leaderboard.json");
    if (!response.ok) throw new Error(`Leaderboard data returned ${response.status}`);
    const payload = await response.json();
    if (!payload.rows.length) return;
    empty.hidden = true;
    updated.textContent = `Updated ${payload.updated_at}`;
    body.innerHTML = payload.rows.map((row) => `
      <tr>
        <td><strong>${escapeHTML(row.configuration)}</strong></td>
        <td>${escapeHTML(row.execution)}</td>
        <td>${escapeHTML(row.delivery)}</td>
        <td>${escapeHTML(row.replay_agreement)}</td>
        <td>${escapeHTML(row.strict_success)}</td>
        <td>${escapeHTML(row.pgap)}</td>
      </tr>
    `).join("");
  } catch (error) {
    updated.textContent = "Leaderboard unavailable";
    console.error(error);
  }
}

searchInput.addEventListener("input", (event) => {
  state.query = event.target.value;
  state.showAll = false;
  renderTasks();
});

domainFilter.addEventListener("change", (event) => {
  state.domain = event.target.value;
  state.showAll = false;
  renderTasks();
});

scaleButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.scale = button.dataset.scale;
    state.showAll = false;
    scaleButtons.forEach((candidate) => {
      const active = candidate === button;
      candidate.classList.toggle("is-active", active);
      candidate.setAttribute("aria-pressed", String(active));
    });
    renderTasks();
  });
});

showAllButton.addEventListener("click", () => {
  state.showAll = true;
  renderTasks();
});

const navToggle = document.querySelector(".nav-toggle");
const siteNav = document.querySelector("#site-nav");

navToggle.addEventListener("click", () => {
  const open = siteNav.classList.toggle("is-open");
  navToggle.setAttribute("aria-expanded", String(open));
  navToggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
});

siteNav.addEventListener("click", (event) => {
  if (event.target.matches("a")) {
    siteNav.classList.remove("is-open");
    navToggle.setAttribute("aria-expanded", "false");
  }
});

window.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) window.lucide.createIcons();
  loadTasks();
  loadLeaderboard();
});
