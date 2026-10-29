const TOKEN_KEY = "gsd_token";

export function setToken(t: string) { localStorage.setItem(TOKEN_KEY, t); }
export function getToken() { return localStorage.getItem(TOKEN_KEY); }
export function clearToken() { localStorage.removeItem(TOKEN_KEY); }

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers || {});
  headers.set("Content-Type", "application/json");
  const t = getToken();
  if (t) headers.set("Authorization", `Bearer ${t}`);
  const res = await fetch(path, { ...init, headers });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${res.status} ${txt}`);
  }
  return res.json();
}

export const api = {
  login: async (email: string, password: string) => {
    const body = new URLSearchParams({ username: email, password });
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!res.ok) throw new Error("Login failed");
    return res.json();
  },
  register: (email: string, password: string) =>
    req<{ access_token: string }>("/api/auth/register", {
      method: "POST", body: JSON.stringify({ email, password }),
    }),
  me: () => req<{ id: number; email: string }>("/api/auth/me"),
  dashboard: () => req<import("./types").Dashboard>("/api/dashboard"),
  tasks: () => req<import("./types").Task[]>("/api/tasks"),
  goals: () => req<import("./types").Goal[]>("/api/goals"),
  createGoal: (g: Partial<import("./types").Goal>) =>
    req("/api/goals", { method: "POST", body: JSON.stringify(g) }),
  deleteTask: (id: number) =>
    req<{ deleted: number }>(`/api/tasks/${id}`, { method: "DELETE" }),
  createTask: (t: any) =>
    req<import("./types").Task>("/api/tasks", { method: "POST", body: JSON.stringify(t) }),
  updateTask: (id: number, patch: any) =>
    req<import("./types").Task>(`/api/tasks/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  completeTask: (id: number) =>
    req<import("./types").Task>(`/api/tasks/${id}/complete`, { method: "POST" }),
  startTask: (id: number) =>
    req<import("./types").Task>(`/api/tasks/${id}/start`, { method: "POST" }),
  scheduleSuggest: (week_start: string) =>
    req<any>(`/api/schedule/suggest?week_start=${week_start}`),
  scheduleApply: (week_start: string) =>
    req<any>(`/api/schedule/apply?week_start=${week_start}`, { method: "POST" }),
  setAvailability: (date: string, available_minutes: number) =>
    req("/api/schedule/availability", { method: "POST", body: JSON.stringify({ date, available_minutes }) }),
  chat: (message: string) =>
    req<{ reply: string; tool_calls: any[] }>("/api/agent/chat", {
      method: "POST", body: JSON.stringify({ message }),
    }),
  prefs: () => req<import("./types").Prefs>("/api/settings/prefs"),
  updatePrefs: (p: Partial<import("./types").Prefs>) =>
    req<import("./types").Prefs>("/api/settings/prefs", { method: "PATCH", body: JSON.stringify(p) }),
  ideas: () => req<any[]>("/api/ideas"),
  addIdea: (content: string) =>
    req("/api/ideas", { method: "POST", body: JSON.stringify({ content }) }),
  ideaToTask: (id: number) => req(`/api/ideas/${id}/to-task`, { method: "POST" }),
  logMood: (mood: number, energy: number) =>
    req("/api/tracking/mood", { method: "POST", body: JSON.stringify({ mood, energy }) }),
  logWater: (amount: number) =>
    req<{ today_ml: number }>("/api/tracking/water", { method: "POST", body: JSON.stringify({ amount_ml: amount }) }),
  water: () => req<{ today_ml: number; goal_ml: number }>("/api/tracking/water"),
    logFood: (meal_type: string, description: string, notes = "") =>
    req<{ id: number }>("/api/tracking/food", {
      method: "POST",
      body: JSON.stringify({ meal_type, description, notes }),
    }),
      // Goals CRUD
  updateGoal: (id: number, patch: any) =>
    req<import("./types").Goal>(`/api/goals/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  deleteGoal: (id: number) =>
    req<{ deleted: number }>(`/api/goals/${id}`, { method: "DELETE" }),

  // Ideas CRUD
  updateIdea: (id: number, patch: any) =>
    req(`/api/ideas/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  deleteIdea: (id: number) =>
    req<{ deleted: number }>(`/api/ideas/${id}`, { method: "DELETE" }),

  // Food CRUD
  logFood: (meal_type: string, description: string, notes = "") =>
    req<import("./types").FoodEntry>("/api/tracking/food", {
      method: "POST",
      body: JSON.stringify({ meal_type, description, notes }),
    }),
  foodList: () =>
    req<import("./types").FoodEntry[]>("/api/tracking/food"),
  updateFood: (id: number, patch: any) =>
    req<import("./types").FoodEntry>(`/api/tracking/food/${id}`, {
      method: "PATCH", body: JSON.stringify(patch),
    }),
  deleteFood: (id: number) =>
    req<{ deleted: number }>(`/api/tracking/food/${id}`, { method: "DELETE" }),

  // Mood CRUD
  getMoods: (days = 30) =>
    req<import("./types").MoodEntry[]>(`/api/tracking/mood?days=${days}`),
  updateMood: (id: number, patch: any) =>
    req<import("./types").MoodEntry>(`/api/tracking/mood/${id}`, {
      method: "PATCH", body: JSON.stringify(patch),
    }),
  deleteMood: (id: number) =>
    req<{ deleted: number }>(`/api/tracking/mood/${id}`, { method: "DELETE" }),
  focusStart: (task_id: number | null, planned_minutes: number) =>
    req<{ session_id: number }>("/api/focus/start", { method: "POST", body: JSON.stringify({ task_id, planned_minutes }) }),
  focusEnd: (session_id: number, completed: boolean, notes = "") =>
    req("/api/focus/end", { method: "POST", body: JSON.stringify({ session_id, completed, notes }) }),
};