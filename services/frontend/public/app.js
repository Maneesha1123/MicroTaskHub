const API_BASE = '';
const STORAGE_KEY = 'microtaskhub_token';

const authOverlay = document.querySelector('#auth-overlay');
const loginForm = document.querySelector('#login-form');
const loginFeedback = document.querySelector('#login-feedback');
const logoutButton = document.querySelector('#logout-button');

const userForm = document.querySelector('#user-form');
const taskForm = document.querySelector('#task-form');
const userFeedback = document.querySelector('#user-feedback');
const taskFeedback = document.querySelector('#task-feedback');
const assigneeSelect = document.querySelector('#assignee-select');
const userListElement = document.querySelector('#user-list');
const userTemplate = document.querySelector('#user-template');
const taskListElement = document.querySelector('#task-list');
const taskTemplate = document.querySelector('#task-template');
const refreshButton = document.querySelector('#refresh-tasks');

const allowedStatuses = ['todo', 'in_progress', 'done'];
let authToken = sessionStorage.getItem(STORAGE_KEY) || null;
const usersCache = new Map();
const tasksCache = new Map();

function setAuthToken(token) {
  authToken = token;
  if (token) {
    sessionStorage.setItem(STORAGE_KEY, token);
    authOverlay.classList.add('hidden');
    document.body.classList.add('authenticated');
  } else {
    sessionStorage.removeItem(STORAGE_KEY);
    authOverlay.classList.remove('hidden');
    document.body.classList.remove('authenticated');
  }
}

function handleUnauthorized(message = 'Session expired. Please sign in.') {
  setAuthToken(null);
  loginFeedback.textContent = message;
}

async function fetchJson(url, options = {}) {
  const requestInit = { ...options };
  const headers = new Headers(options.headers || {});
  if (authToken) {
    headers.set('Authorization', `Bearer ${authToken}`);
  }
  requestInit.headers = headers;

  const response = await fetch(url, requestInit);
  const responseText = response.status === 204 ? '' : await response.text();

  if (response.status === 401) {
    handleUnauthorized();
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    let detail = response.statusText;
    if (responseText) {
      try {
        const parsed = JSON.parse(responseText);
        detail = parsed.detail || detail;
      } catch (_) {
        detail = responseText;
      }
    }
    throw new Error(detail || 'Unexpected error');
  }

  if (!responseText) {
    return null;
  }

  try {
    return JSON.parse(responseText);
  } catch (_) {
    return null;
  }
}

async function login(username, password) {
  const response = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const text = await response.text();
  if (!response.ok) {
    let detail = response.statusText;
    if (text) {
      try {
        detail = JSON.parse(text).detail || detail;
      } catch (_) {
        detail = text;
      }
    }
    throw new Error(detail || 'Login failed');
  }
  const data = text ? JSON.parse(text) : {};
  if (!data.token) {
    throw new Error('Authentication token missing');
  }
  setAuthToken(data.token);
}

function populateAssigneeSelect(users) {
  assigneeSelect.innerHTML = '';
  users.forEach((user) => {
    const option = document.createElement('option');
    option.value = user.id;
    option.textContent = `${user.full_name} (${user.role})`;
    assigneeSelect.append(option);
  });
  if (users.length === 0) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'Create a user first';
    assigneeSelect.append(option);
  }
}

function renderUserList(users) {
  userListElement.innerHTML = '';
  if (users.length === 0) {
    const empty = document.createElement('li');
    empty.textContent = 'No users yet.';
    userListElement.append(empty);
    return;
  }

  users.forEach((user) => {
    const node = userTemplate.content.cloneNode(true);
    const item = node.querySelector('.user-item');
    item.dataset.userId = user.id;
    node.querySelector('[data-field="full_name"]').textContent = user.full_name;
    node.querySelector('[data-field="email"]').textContent = user.email;
    node.querySelector('[data-field="role"]').textContent = user.role;
    userListElement.append(node);
  });
}

async function loadUsers() {
  const users = await fetchJson(`${API_BASE}/users`);
  usersCache.clear();
  users.forEach((user) => usersCache.set(user.id, user));
  populateAssigneeSelect(users);
  renderUserList(users);
}

function renderTaskList(tasks) {
  taskListElement.innerHTML = '';
  if (tasks.length === 0) {
    const emptyState = document.createElement('li');
    emptyState.textContent = 'No tasks yet. Create one!';
    taskListElement.append(emptyState);
    return;
  }

  tasks.forEach((task) => {
    const node = taskTemplate.content.cloneNode(true);
    const item = node.querySelector('.task-item');
    item.dataset.taskId = task.id;
    node.querySelector('[data-field="title"]').textContent = task.title;
    node.querySelector('[data-field="description"]').textContent = task.description || 'No description';
    node.querySelector('[data-field="status"]').textContent = task.status;
    node.querySelector('[data-field="assignee"]').textContent = task.assignee
      ? `${task.assignee.full_name} (${task.assignee.email})`
      : 'Unknown';
    node.querySelector('[data-field="due_date"]').textContent = task.due_date || 'Not set';
    taskListElement.append(node);
  });
}

async function loadTasks() {
  const tasks = await fetchJson(`${API_BASE}/tasks`);
  tasksCache.clear();
  const detailedTasks = [];
  for (const task of tasks) {
    const detailed = await fetchJson(`${API_BASE}/tasks/${task.id}?include_assignee=true`);
    tasksCache.set(detailed.id, detailed);
    detailedTasks.push(detailed);
  }
  renderTaskList(detailedTasks);
}

function buildUserUpdatePayload(existing) {
  const payload = {};
  const email = prompt('Email', existing.email);
  if (email === null) {
    return null;
  }
  const fullName = prompt('Full name', existing.full_name);
  if (fullName === null) {
    return null;
  }
  const role = prompt('Role (member, manager)', existing.role);
  if (role === null) {
    return null;
  }

  if (email && email !== existing.email) {
    payload.email = email.trim();
  }
  if (fullName && fullName !== existing.full_name) {
    payload.full_name = fullName.trim();
  }
  if (role && role !== existing.role) {
    payload.role = role.trim();
  }
  return payload;
}

async function handleUserEdit(userId) {
  const existing = usersCache.get(userId);
  if (!existing) {
    userFeedback.textContent = 'User not found in cache.';
    return;
  }
  const payload = buildUserUpdatePayload(existing);
  if (payload === null) {
    return;
  }
  if (Object.keys(payload).length === 0) {
    userFeedback.textContent = 'No changes detected.';
    return;
  }
  try {
    await fetchJson(`${API_BASE}/users/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    userFeedback.textContent = 'User updated';
    await loadUsers();
    await loadTasks();
  } catch (error) {
    userFeedback.textContent = error.message;
  }
}

async function handleUserDelete(userId) {
  if (!confirm('Delete this user? Users with in-progress tasks cannot be deleted.')) {
    return;
  }
  try {
    await fetchJson(`${API_BASE}/users/${userId}`, { method: 'DELETE' });
    userFeedback.textContent = 'User deleted';
    await loadUsers();
    await loadTasks();
  } catch (error) {
    userFeedback.textContent = error.message;
  }
}

userListElement.addEventListener('click', (event) => {
  const button = event.target.closest('button[data-action]');
  if (!button) {
    return;
  }
  const listItem = button.closest('[data-user-id]');
  const userId = listItem?.dataset.userId;
  if (!userId) {
    return;
  }
  if (button.dataset.action === 'edit-user') {
    handleUserEdit(userId);
  } else if (button.dataset.action === 'delete-user') {
    handleUserDelete(userId);
  }
});

function buildTaskUpdatePayload(existing) {
  const payload = {};
  const title = prompt('Title', existing.title);
  if (title === null) {
    return null;
  }
  const description = prompt('Description', existing.description || '');
  if (description === null) {
    return null;
  }
  const dueDate = prompt('Due date (YYYY-MM-DD)', existing.due_date || '');
  if (dueDate === null) {
    return null;
  }
  const status = prompt('Status (todo, in_progress, done)', existing.status);
  if (status === null) {
    return null;
  }

  if (title && title.trim() && title.trim() !== existing.title) {
    payload.title = title.trim();
  }
  if ((description ?? '').trim() !== (existing.description ?? '')) {
    payload.description = description.trim();
  }
  if (dueDate.trim() !== (existing.due_date ?? '')) {
    payload.due_date = dueDate.trim() || null;
  }
  if (status && status !== existing.status) {
    const normalized = status.trim().toLowerCase();
    if (!allowedStatuses.includes(normalized)) {
      throw new Error('Invalid status value');
    }
    payload.status = normalized;
  }
  return payload;
}

async function handleTaskEdit(taskId) {
  const existing = tasksCache.get(taskId);
  if (!existing) {
    taskFeedback.textContent = 'Task not found in cache.';
    return;
  }
  let payload;
  try {
    payload = buildTaskUpdatePayload(existing);
  } catch (error) {
    taskFeedback.textContent = error.message;
    return;
  }
  if (payload === null) {
    return;
  }
  if (Object.keys(payload).length === 0) {
    taskFeedback.textContent = 'No changes detected.';
    return;
  }
  try {
    await fetchJson(`${API_BASE}/tasks/${taskId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    taskFeedback.textContent = 'Task updated';
    await loadTasks();
  } catch (error) {
    taskFeedback.textContent = error.message;
  }
}

async function handleTaskDelete(taskId) {
  if (!confirm('Delete this task? Only tasks marked as done can be deleted.')) {
    return;
  }
  try {
    await fetchJson(`${API_BASE}/tasks/${taskId}`, { method: 'DELETE' });
    taskFeedback.textContent = 'Task deleted';
    await loadTasks();
  } catch (error) {
    taskFeedback.textContent = error.message;
  }
}

taskListElement.addEventListener('click', (event) => {
  const button = event.target.closest('button[data-action]');
  if (!button) {
    return;
  }
  const listItem = button.closest('[data-task-id]');
  const taskId = listItem?.dataset.taskId;
  if (!taskId) {
    return;
  }
  if (button.dataset.action === 'edit-task') {
    handleTaskEdit(taskId);
  } else if (button.dataset.action === 'delete-task') {
    handleTaskDelete(taskId);
  }
});

userForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  userFeedback.textContent = '';
  const formData = new FormData(userForm);
  const payload = Object.fromEntries(formData.entries());
  try {
    await fetchJson(`${API_BASE}/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    userFeedback.textContent = 'User created';
    userForm.reset();
    await loadUsers();
  } catch (error) {
    userFeedback.textContent = error.message;
  }
});

taskForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  taskFeedback.textContent = '';
  const formData = new FormData(taskForm);
  const payload = Object.fromEntries(formData.entries());
  if (!payload.assignee_id) {
    taskFeedback.textContent = 'Create a user first and select an assignee.';
    return;
  }
  try {
    await fetchJson(`${API_BASE}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    taskFeedback.textContent = 'Task created';
    taskForm.reset();
    await loadTasks();
  } catch (error) {
    taskFeedback.textContent = error.message;
  }
});

refreshButton.addEventListener('click', () => {
  loadTasks().catch((error) => {
    taskFeedback.textContent = error.message;
  });
});

loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  loginFeedback.textContent = '';
  const formData = new FormData(loginForm);
  const payload = Object.fromEntries(formData.entries());
  try {
    await login(payload.username, payload.password);
    loginForm.reset();
    loginFeedback.textContent = '';
    await bootstrap();
  } catch (error) {
    loginFeedback.textContent = error.message;
  }
});

logoutButton.addEventListener('click', () => {
  setAuthToken(null);
  usersCache.clear();
  tasksCache.clear();
  userListElement.innerHTML = '';
  taskListElement.innerHTML = '';
  loginFeedback.textContent = '';
});

async function bootstrap() {
  if (!authToken) {
    handleUnauthorized('Please sign in to continue.');
    return;
  }
  await loadUsers().catch((error) => {
    userFeedback.textContent = error.message;
  });
  await loadTasks().catch((error) => {
    taskFeedback.textContent = error.message;
  });
}

window.addEventListener('DOMContentLoaded', () => {
  if (authToken) {
    setAuthToken(authToken);
    bootstrap();
  } else {
    setAuthToken(null);
  }
});
