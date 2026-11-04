const PAGE_SIZE = 12;

const state = { tasks: [], query: "", domain: "all", showAll: false };
const taskBody = document.querySelector("#task-table-body");
const taskEmpty = document.querySelector("#task-empty");
const taskCount = document.querySelector("#task-count");
const searchInput = document.querySelector("#task-search");
const domainFilter = document.querySelector("#domain-filter");
const showAllButton = document.querySelector("#show-all-tasks");
const leaderboardBody = document.querySelector("#leaderboard-body");
const leaderboardTotal = document.querySelector("#leaderboard-total");

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
    const matchesQuery = !query || [task.project_id, task.paper_title, task.target_task, task.target_metric, task.evaluation_dataset]
      .some((value) => value.toLowerCase().includes(query));
    const matchesDomain = state.domain === "all" || task.domain_key === state.domain;
    return matchesQuery && matchesDomain;
  });
}

function renderTasks() {
  const matches = filteredTasks();
  const visible = state.showAll ? matches : matches.slice(0, PAGE_SIZE);
  taskBody.innerHTML = visible.map((task) => `
    <tr>
      <td><span class="task-title">${escapeHTML(task.paper_title)}</span><span class="task-target">${escapeHTML(task.target_task)}</span></td>
      <td><span class="domain-label">${escapeHTML(task.domain_label)}</span></td>
      <td>${escapeHTML(task.target_metric)}<span class="metric-reference">ref. ${escapeHTML(task.reference_display)}</span></td>
      <td><a class="repository-link" href="${escapeHTML(task.repository_url)}" aria-label="Open source repository for ${escapeHTML(task.paper_title)}" title="Source repository"><i data-lucide="arrow-up-right" aria-hidden="true"></i></a></td>
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

function scoreCell(value, denominator) {
  const rate = (100 * value / denominator).toFixed(1);
  return `${value}/${denominator} <span class="score-rate">${rate}%</span>`;
}

async function loadLeaderboard() {
  try {
    const response = await fetch("./data/leaderboard.json");
    if (!response.ok) throw new Error(`Leaderboard data returned ${response.status}`);
    const payload = await response.json();
    const denominator = payload.cohort.denominator_per_configuration;
    leaderboardBody.innerHTML = payload.rows.map((row) => `
      <tr>
        <td>${row.rank}</td>
        <td><strong>${escapeHTML(row.model)}</strong></td>
        <td>${escapeHTML(row.agent)}</td>
        <td>${scoreCell(row.execution, denominator)}</td>
        <td>${scoreCell(row.delivery, denominator)}</td>
        <td>${scoreCell(row.replay_match, denominator)}</td>
        <td class="strict-score">${scoreCell(row.strict_success, denominator)}</td>
        <td>${row.unresolved}</td>
      </tr>
    `).join("");
    leaderboardTotal.innerHTML = `<tr><th colspan="3" scope="row">All 423 runs</th><td>${payload.totals.execution}/423</td><td>${payload.totals.delivery}/423</td><td>${payload.totals.replay_match}/423</td><td>${payload.totals.strict_success}/423</td><td>${payload.totals.unresolved}</td></tr>`;
  } catch (error) {
    leaderboardBody.innerHTML = '<tr><td colspan="8">Frozen leaderboard data could not be loaded.</td></tr>';
    console.error(error);
  }
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

showAllButton.addEventListener("click", () => {
  state.showAll = true;
  renderTasks();
});

window.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) window.lucide.createIcons();
  loadLeaderboard();
  loadTasks();
});
