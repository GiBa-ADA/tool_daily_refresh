const API_BASE = 'http://127.0.0.1:5000';

const clientSelect = document.getElementById('clientSelect');
const refreshBtn = document.getElementById('refreshBtn');
const cancelBtn = document.getElementById('cancelBtn');
const statusEl = document.getElementById('status');
const statusText = document.getElementById('statusText');
const loadingIcon = document.getElementById('loadingIcon');
const healthEl = document.getElementById('health');
const includeDatabase = document.getElementById('includeDatabase');
const includeUi = document.getElementById('includeUi');
const progressPanel = document.getElementById('progressPanel');
const progressFill = document.getElementById('progressFill');
const progressLabel = document.getElementById('progressLabel');
const progressPercent = document.getElementById('progressPercent');
const queryProgressList = document.getElementById('queryProgressList');

let pollTimer;

const FALLBACK_DATABASE_TABLES = [
  'ecommerce_export_seller_sales',
  'ecommerce_export_sku_sales',
  'ecommerce_item',
];

const FALLBACK_UI_TABLES = [
  'raw_seller_metrics',
];

function setStatus(message, state = 'info') {
  statusText.textContent = message;
  statusEl.dataset.state = state;
}

function setLoading(isLoading) {
  loadingIcon.hidden = !isLoading;
}

function setBusy(isBusy) {
  refreshBtn.disabled = isBusy;
  clientSelect.disabled = isBusy;
  includeDatabase.disabled = isBusy;
  includeUi.disabled = isBusy;
  cancelBtn.hidden = !isBusy;
}

function normalizeProgress(progress = 0) {
  return Math.min(Math.max(Number(progress) || 0, 0), 100);
}

function setProgress(progress = 0, label = 'Ready', state = 'idle') {
  const normalizedProgress = normalizeProgress(progress);
  progressPanel.hidden = state === 'idle';
  progressPanel.dataset.state = state;
  progressFill.style.width = `${normalizedProgress}%`;
  progressLabel.textContent = label;
  progressPercent.textContent = `${normalizedProgress}%`;
}

function hideProgress() {
  progressPanel.hidden = true;
  progressPanel.dataset.state = 'idle';
  queryProgressList.innerHTML = '';
}

function renderQueryRow(query, groupLabel) {
  const row = document.createElement('div');
  row.className = 'step-progress-row';
  row.dataset.status = query.status || 'pending';

  const meta = document.createElement('div');
  meta.className = 'progress-meta';

  const name = document.createElement('span');
  name.className = 'query-name';
  name.textContent = `${groupLabel}: ${query.name}`;

  const percent = document.createElement('span');
  percent.textContent = `${normalizeProgress(query.progress)}%`;

  const track = document.createElement('div');
  track.className = 'progress-track';

  const fill = document.createElement('div');
  fill.className = 'progress-fill';
  fill.style.width = `${normalizeProgress(query.progress)}%`;

  const state = document.createElement('span');
  state.className = 'query-state';
  state.textContent = query.status || 'pending';

  meta.append(name, state, percent);
  track.append(fill);
  row.append(meta, track);

  return row;
}

function fallbackQueries(names) {
  return names.map((name) => ({
    name,
    status: 'pending',
    progress: 3,
  }));
}

function renderLocalPendingQueries() {
  queryProgressList.innerHTML = '';

  if (includeDatabase.checked) {
    fallbackQueries(FALLBACK_DATABASE_TABLES).forEach((query) => {
      queryProgressList.appendChild(renderQueryRow(query, 'DB'));
    });
  }

  if (includeUi.checked) {
    fallbackQueries(FALLBACK_UI_TABLES).forEach((query) => {
      queryProgressList.appendChild(renderQueryRow(query, 'UI'));
    });
  }
}

function renderQueryProgress(job) {
  queryProgressList.innerHTML = '';

  const databaseTables = job.database_tables?.length
    ? job.database_tables
    : (job.include_database ? fallbackQueries(FALLBACK_DATABASE_TABLES) : []);
  const uiTables = job.ui_tables?.length
    ? job.ui_tables
    : (job.include_ui ? fallbackQueries(FALLBACK_UI_TABLES) : []);

  databaseTables.forEach((query) => {
    queryProgressList.appendChild(renderQueryRow(query, 'DB'));
  });

  uiTables.forEach((query) => {
    queryProgressList.appendChild(renderQueryRow(query, 'UI'));
  });
}

function renderJob(job) {
  const state = job.status === 'failed' ? 'error' : job.status;
  setStatus(job.message, state);
  const progress = job.status === 'queued' ? Math.max(job.progress || 0, 3) : job.progress || 0;
  setProgress(progress, job.current_step || 'Refreshing', state);
  renderQueryProgress(job);

  const isRunning = job.status === 'queued' || job.status === 'running';
  setLoading(isRunning);
  setBusy(isRunning);
}

async function apiFetch(path, options) {
  const response = await fetch(`${API_BASE}${path}`, options);
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.detail || 'Backend request failed.');
  }

  return payload;
}

async function finishJob(job) {
  clearInterval(pollTimer);
  setLoading(false);
  setBusy(false);

  if (job.status === 'success') {
    setProgress(100, 'Completed', 'success');
    await chrome.storage.local.remove('activeJobId');
    setTimeout(hideProgress, 2500);
  } else if (job.status === 'cancelled') {
    setProgress(job.progress || 0, 'Cancelled', 'error');
    await chrome.storage.local.remove('activeJobId');
  }
}

async function pollJob(jobId) {
  const job = await apiFetch(`/jobs/${jobId}`);
  renderJob(job);

  if (job.status === 'success' || job.status === 'failed' || job.status === 'cancelled') {
    await finishJob(job);
  }
}

function startPolling(jobId) {
  clearInterval(pollTimer);
  pollTimer = setInterval(() => pollJob(jobId).catch(async (error) => {
    clearInterval(pollTimer);
    setLoading(false);
    setBusy(false);
    await chrome.storage.local.remove('activeJobId');
    setStatus(error.message, 'error');
  }), 1500);
}

async function restoreActiveJob() {
  const { activeJobId } = await chrome.storage.local.get('activeJobId');

  if (!activeJobId) {
    return;
  }

  try {
    const job = await apiFetch(`/jobs/${activeJobId}`);
    renderJob(job);

    if (job.status === 'queued' || job.status === 'running') {
      startPolling(activeJobId);
    } else {
      await finishJob(job);
    }
  } catch (error) {
    await chrome.storage.local.remove('activeJobId');
  }
}

async function loadClients() {
  try {
    await apiFetch('/health');
    healthEl.textContent = 'Online';
    healthEl.dataset.state = 'online';

    const { clients } = await apiFetch('/clients');
    clientSelect.innerHTML = '';

    clients.forEach((client) => {
      const option = document.createElement('option');
      option.value = client;
      option.textContent = client;
      clientSelect.appendChild(option);
    });

    const { lastClient } = await chrome.storage.local.get('lastClient');
    if (lastClient && clients.includes(lastClient)) {
      clientSelect.value = lastClient;
    }

    setStatus(`Loaded ${clients.length} clients.`);
    hideProgress();
    refreshBtn.disabled = clients.length === 0;
    await restoreActiveJob();
  } catch (error) {
    healthEl.textContent = 'Offline';
    healthEl.dataset.state = 'offline';
    refreshBtn.disabled = true;
    hideProgress();
    setStatus('Backend is not running on port 5000.', 'error');
  }
}

refreshBtn.addEventListener('click', async () => {
  const client = clientSelect.value;

  if (!includeDatabase.checked && !includeUi.checked) {
    setStatus('Select Database, UI metrics, or both.', 'error');
    return;
  }

  try {
    setBusy(true);
    setLoading(true);
    setStatus(`Queueing refresh for ${client}...`, 'queued');
    setProgress(3, 'Queued', 'queued');
    renderLocalPendingQueries();

    await chrome.storage.local.set({ lastClient: client });

    const job = await apiFetch('/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client,
        include_database: includeDatabase.checked,
        include_ui: includeUi.checked,
      }),
    });

    await chrome.storage.local.set({ activeJobId: job.id });
    renderJob(job);
    startPolling(job.id);
  } catch (error) {
    setBusy(false);
    setLoading(false);
    setProgress(0, 'Failed', 'error');
    setStatus(error.message, 'error');
  }
});

cancelBtn.addEventListener('click', async () => {
  const { activeJobId } = await chrome.storage.local.get('activeJobId');

  if (!activeJobId) {
    return;
  }

  try {
    cancelBtn.disabled = true;
    setStatus('Cancelling refresh...', 'queued');
    const job = await apiFetch(`/jobs/${activeJobId}/cancel`, { method: 'POST' });
    renderJob(job);

    if (job.status === 'cancelled' || job.status === 'failed' || job.status === 'success') {
      await finishJob(job);
    }
  } catch (error) {
    setStatus(error.message, 'error');
  } finally {
    cancelBtn.disabled = false;
  }
});

loadClients();
