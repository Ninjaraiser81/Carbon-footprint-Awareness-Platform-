/**
 * EcoTrack — Carbon Footprint Tracker
 * Main application JavaScript
 *
 * Architecture:
 * - State object holds all app state
 * - API module handles all HTTP calls
 * - UI module handles rendering
 * - Event-driven navigation
 */

"use strict";

/* ══════════════════════════════════════════════════════════════════════════
   CONFIG
══════════════════════════════════════════════════════════════════════════ */
const CONFIG = Object.freeze({
  API_BASE: "http://localhost:8000/api/v1",
  TOKEN_KEY: "eco_token",
  USER_KEY: "eco_user",
  DEMO_USER: { username: "demouser", password: "DemoPass1" },
});

/* ══════════════════════════════════════════════════════════════════════════
   STATE
══════════════════════════════════════════════════════════════════════════ */
const state = {
  token: null,
  user: null,
  currentPage: "dashboard",
  subcategories: {},     // { category: [{subcategory, unit, kg_co2e_per_unit, description}] }
  selectedCategory: "transport",
  dashboardData: null,
  insightsData: null,
  historyPage: 1,
  historyPageSize: 15,
  historyCategory: "",
  historyStart: "",
  historyEnd: "",
  deleteTargetId: null,
  charts: { trend: null, category: null, gauge: null },
};

/* ══════════════════════════════════════════════════════════════════════════
   CATEGORY ICONS
══════════════════════════════════════════════════════════════════════════ */
const CAT_ICONS = {
  transport: "🚗", energy: "⚡", food: "🍽️",
  shopping: "🛍️", travel: "✈️", waste: "♻️",
};
const CAT_COLORS = {
  transport: "#3b82f6", energy: "#f97316", food: "#22c55e",
  shopping: "#a855f7", travel: "#14b8a6", waste: "#ef4444",
};

/* ══════════════════════════════════════════════════════════════════════════
   API MODULE
══════════════════════════════════════════════════════════════════════════ */
const api = (() => {
  /**
   * Core fetch wrapper with error handling.
   * @param {string} path
   * @param {RequestInit} opts
   */
  async function request(path, opts = {}) {
    const headers = { "Content-Type": "application/json" };
    if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
    const res = await fetch(`${CONFIG.API_BASE}${path}`, { ...opts, headers });
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try { detail = (await res.json()).detail || detail; } catch (_) {}
      throw new Error(detail);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  return {
    // Auth
    register: (data) => request("/auth/register", { method: "POST", body: JSON.stringify(data) }),
    login:    (data) => request("/auth/login", { method: "POST", body: JSON.stringify(data) }),
    me:       ()     => request("/auth/me"),

    // Subcategories (public)
    subcategories: () => request("/activities/subcategories"),

    // Activities
    createActivity: (data) => request("/activities/", { method: "POST", body: JSON.stringify(data) }),
    listActivities: (params = {}) => {
      const q = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => { if (v !== "" && v != null) q.set(k, v); });
      return request(`/activities/?${q}`);
    },
    updateActivity: (id, data) => request(`/activities/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    deleteActivity: (id) => request(`/activities/${id}`, { method: "DELETE" }),

    // Dashboard & Insights
    dashboard: () => request("/dashboard/"),
    insights:  () => request("/insights/"),
  };
})();

/* ══════════════════════════════════════════════════════════════════════════
   PERSISTENCE
══════════════════════════════════════════════════════════════════════════ */
function saveSession(token, user) {
  state.token = token;
  state.user = user;
  try {
    localStorage.setItem(CONFIG.TOKEN_KEY, token);
    localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(user));
  } catch (_) { /* storage might be blocked */ }
}

function loadSession() {
  try {
    state.token = localStorage.getItem(CONFIG.TOKEN_KEY);
    const raw = localStorage.getItem(CONFIG.USER_KEY);
    state.user = raw ? JSON.parse(raw) : null;
  } catch (_) {}
}

function clearSession() {
  state.token = null;
  state.user = null;
  try {
    localStorage.removeItem(CONFIG.TOKEN_KEY);
    localStorage.removeItem(CONFIG.USER_KEY);
  } catch (_) {}
}

/* ══════════════════════════════════════════════════════════════════════════
   AUTH FLOWS
══════════════════════════════════════════════════════════════════════════ */
function switchAuthTab(tab) {
  const isLogin = tab === "login";
  document.getElementById("tab-login").classList.toggle("active", isLogin);
  document.getElementById("tab-register").classList.toggle("active", !isLogin);
  document.getElementById("tab-login").setAttribute("aria-selected", String(isLogin));
  document.getElementById("tab-register").setAttribute("aria-selected", String(!isLogin));
  document.getElementById("panel-login").classList.toggle("hidden", !isLogin);
  document.getElementById("panel-register").classList.toggle("hidden", isLogin);
}

async function handleLogin(e) {
  e.preventDefault();
  const errEl = document.getElementById("login-error");
  const btn   = document.getElementById("login-btn");
  errEl.textContent = "";
  btn.disabled = true;
  btn.innerHTML = '<span>Signing in…</span>';
  try {
    const data = await api.login({
      username: document.getElementById("login-username").value.trim(),
      password: document.getElementById("login-password").value,
    });
    saveSession(data.access_token, data.user);
    showApp();
  } catch (err) {
    errEl.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Sign In</span><i data-lucide="arrow-right" aria-hidden="true"></i>';
    lucide.createIcons();
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const errEl = document.getElementById("register-error");
  const btn   = document.getElementById("register-btn");
  errEl.textContent = "";
  btn.disabled = true;
  btn.innerHTML = '<span>Creating account…</span>';
  try {
    const data = await api.register({
      username:     document.getElementById("reg-username").value.trim(),
      email:        document.getElementById("reg-email").value.trim(),
      password:     document.getElementById("reg-password").value,
      full_name:    document.getElementById("reg-fullname").value.trim() || undefined,
      country:      document.getElementById("reg-country").value,
      annual_goal_kg: parseFloat(document.getElementById("reg-goal").value) || 2000,
    });
    saveSession(data.access_token, data.user);
    showApp();
  } catch (err) {
    errEl.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Create Account</span><i data-lucide="user-plus" aria-hidden="true"></i>';
    lucide.createIcons();
  }
}

function logout() {
  clearSession();
  // Destroy charts
  Object.values(state.charts).forEach(c => c?.destroy());
  state.charts = { trend: null, category: null, gauge: null };
  // Reset UI
  document.getElementById("app").classList.add("hidden");
  document.getElementById("auth-overlay").classList.remove("hidden");
  document.getElementById("login-form").reset();
  switchAuthTab("login");
}

/* ══════════════════════════════════════════════════════════════════════════
   APP BOOTSTRAP
══════════════════════════════════════════════════════════════════════════ */
async function showApp() {
  document.getElementById("auth-overlay").classList.add("hidden");
  document.getElementById("app").classList.remove("hidden");

  // Populate sidebar
  const u = state.user;
  document.getElementById("sidebar-username").textContent = u?.username || "";
  document.getElementById("user-avatar").textContent = (u?.username || "?")[0].toUpperCase();

  // Load subcategories
  try {
    state.subcategories = await api.subcategories();
  } catch (_) {}

  // Set today's date in log form
  document.getElementById("act-date").value = new Date().toISOString().split("T")[0];

  // Populate subcategory dropdown
  selectCategory(state.selectedCategory);

  navigateTo("dashboard");
}

/* ══════════════════════════════════════════════════════════════════════════
   NAVIGATION
══════════════════════════════════════════════════════════════════════════ */
function navigateTo(page) {
  // Update nav items
  document.querySelectorAll(".nav-item").forEach(el => {
    const isActive = el.dataset.page === page;
    el.classList.toggle("active", isActive);
    el.setAttribute("aria-current", isActive ? "page" : "false");
  });

  // Update page visibility
  document.querySelectorAll(".page").forEach(el => {
    el.classList.toggle("active", el.id === `page-${page}`);
    el.classList.toggle("hidden", el.id !== `page-${page}`);
  });

  state.currentPage = page;

  // Close mobile sidebar
  document.getElementById("sidebar").classList.remove("open");
  document.getElementById("menu-toggle")?.setAttribute("aria-expanded", "false");

  // Load page data
  switch (page) {
    case "dashboard": loadDashboard(); break;
    case "insights":  loadInsights();  break;
    case "history":   loadHistory();   break;
    case "badges":    loadBadges();    break;
  }
}

function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");
  const btn = document.getElementById("menu-toggle");
  const isOpen = sidebar.classList.toggle("open");
  btn.setAttribute("aria-expanded", String(isOpen));
}

/* ══════════════════════════════════════════════════════════════════════════
   DASHBOARD
══════════════════════════════════════════════════════════════════════════ */
async function loadDashboard() {
  try {
    const data = await api.dashboard();
    state.dashboardData = data;
    renderDashboard(data);
  } catch (err) {
    showToast("Failed to load dashboard: " + err.message, "error");
  }
}

function refreshDashboard() { loadDashboard(); }

function renderDashboard(data) {
  const u = state.user;
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  document.getElementById("dash-greeting").textContent = `${greeting}, ${u?.username || ""}! 🌿`;

  // KPIs
  animateCount("kpi-score", 0, data.carbon_score, 800, "", "");
  animateCount("kpi-month", 0, data.total_co2e_this_month, 800, "", " kg");
  animateCount("kpi-streak", 0, data.streak_days, 600, "", "");
  animateCount("kpi-goal", 0, data.goal_progress_pct, 800, "", "%");

  document.getElementById("kpi-score-label").textContent = getEcoLabel(data.carbon_score);

  // Tip
  document.getElementById("tip-text").textContent = data.badges?.length > 0
    ? `You have ${data.badges.length} badge${data.badges.length > 1 ? "s" : ""}! Keep going! 🏆`
    : "Start logging activities to get your personalised tip!";

  // Comparison bars
  renderComparisonBars(data);

  // Charts
  renderTrendChart(data.daily_trend);
  renderCategoryChart(data.category_breakdown);

  // Recent activities
  renderActivityList("recent-activities", data.recent_activities, false);
}

function renderComparisonBars(data) {
  const el = document.getElementById("comparison-bars");
  const monthly = data.total_co2e_this_month;
  const global  = data.global_avg_monthly_kg;
  const national= data.national_avg_monthly_kg;
  const maxVal  = Math.max(monthly, global, national, 1);

  const bars = [
    { label: "You",      value: monthly, color: getScoreColor(data.carbon_score) },
    { label: "Global Avg",  value: global, color: "#3b82f6" },
    { label: `${state.user?.country || "National"} Avg`, value: national, color: "#a855f7" },
  ];

  el.innerHTML = bars.map(b => `
    <div class="comp-bar-row">
      <div class="comp-bar-label">
        <span>${b.label}</span>
        <span>${b.value.toFixed(1)} kg</span>
      </div>
      <div class="comp-bar-track">
        <div class="comp-bar-fill" style="width:${(b.value/maxVal*100).toFixed(1)}%; background:${b.color};"></div>
      </div>
    </div>
  `).join("");
}

function getEcoLabel(score) {
  if (score >= 95) return "Net Zero Hero 🌟";
  if (score >= 85) return "Carbon Champion 🏆";
  if (score >= 70) return "Eco Warrior 💚";
  if (score >= 55) return "Green Minded 🌱";
  if (score >= 35) return "Aware & Improving 📈";
  if (score >= 15) return "Room to Grow 🌿";
  return "High Impact ⚠️";
}
function getScoreColor(score) {
  if (score >= 70) return "#22c55e";
  if (score >= 40) return "#f97316";
  return "#ef4444";
}

/* ══════════════════════════════════════════════════════════════════════════
   CHARTS
══════════════════════════════════════════════════════════════════════════ */
function renderTrendChart(daily_trend) {
  const ctx = document.getElementById("trend-chart").getContext("2d");
  if (state.charts.trend) state.charts.trend.destroy();

  const labels = daily_trend.map(d => {
    const [, m, day] = d.date.split("-");
    return `${day}/${m}`;
  });
  const values = daily_trend.map(d => d.co2e_kg);

  state.charts.trend = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "CO₂e (kg)",
        data: values,
        borderColor: "#22c55e",
        backgroundColor: "rgba(34,197,94,0.08)",
        borderWidth: 2,
        pointBackgroundColor: "#22c55e",
        pointRadius: 3,
        pointHoverRadius: 6,
        fill: true,
        tension: 0.4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { mode: "index", intersect: false } },
      scales: {
        x: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#4d7a4d", maxTicksLimit: 8 } },
        y: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#4d7a4d" }, beginAtZero: true },
      },
    },
  });
}

function renderCategoryChart(breakdown) {
  const ctx = document.getElementById("category-chart").getContext("2d");
  if (state.charts.category) state.charts.category.destroy();

  if (!breakdown || breakdown.length === 0) {
    ctx.canvas.parentElement.innerHTML = '<p class="muted" style="text-align:center;padding:40px">No data yet. Log some activities!</p>';
    return;
  }

  state.charts.category = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: breakdown.map(b => b.category.charAt(0).toUpperCase() + b.category.slice(1)),
      datasets: [{
        data: breakdown.map(b => b.co2e_kg),
        backgroundColor: breakdown.map(b => CAT_COLORS[b.category] || "#22c55e"),
        borderColor: "#0d1a0d",
        borderWidth: 2,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "65%",
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: "#a7c5a7", font: { size: 11 }, padding: 12, boxWidth: 12 },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.parsed.toFixed(2)} kg CO₂e (${breakdown[ctx.dataIndex]?.percentage}%)`,
          },
        },
      },
    },
  });
}

function renderGaugeChart(score) {
  const ctx = document.getElementById("eco-gauge").getContext("2d");
  if (state.charts.gauge) state.charts.gauge.destroy();

  const remaining = 100 - score;
  const color = getScoreColor(score);

  state.charts.gauge = new Chart(ctx, {
    type: "doughnut",
    data: {
      datasets: [{
        data: [score, remaining],
        backgroundColor: [color, "rgba(255,255,255,0.05)"],
        borderColor: "transparent",
        borderWidth: 0,
        circumference: 270,
        rotation: -135,
      }],
    },
    options: {
      responsive: false,
      cutout: "78%",
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      animation: { duration: 1000, easing: "easeInOutQuart" },
    },
  });

  document.getElementById("eco-score-num").textContent = score;
}

/* ══════════════════════════════════════════════════════════════════════════
   ACTIVITY LOG
══════════════════════════════════════════════════════════════════════════ */
function selectCategory(cat) {
  state.selectedCategory = cat;

  // Update buttons
  document.querySelectorAll(".cat-btn").forEach(btn => {
    const isActive = btn.dataset.cat === cat;
    btn.classList.toggle("active", isActive);
    btn.setAttribute("aria-pressed", String(isActive));
  });

  // Populate subcategory select
  const select = document.getElementById("act-subcategory");
  const factors = state.subcategories[cat] || [];
  select.innerHTML = '<option value="">Select an activity…</option>' +
    factors.map(f => `<option value="${f.subcategory}" data-unit="${f.unit}" data-rate="${f.kg_co2e_per_unit}">${f.description}</option>`).join("");

  // Unit field & preview
  document.getElementById("act-unit").value = "";
  updateCo2Preview();

  // Quick ref
  renderQuickRef(factors);
}

function renderQuickRef(factors) {
  const list = document.getElementById("quick-ref-list");
  if (!factors.length) { list.innerHTML = '<p class="muted">No data available</p>'; return; }
  list.innerHTML = factors.map(f => `
    <div class="ref-item">
      <span class="ref-item-name">${f.description}</span>
      <span class="ref-item-value">${f.kg_co2e_per_unit} kg/${f.unit}</span>
    </div>
  `).join("");
}

function updateCo2Preview() {
  const select = document.getElementById("act-subcategory");
  const qty    = parseFloat(document.getElementById("act-quantity").value);
  const opt    = select.options[select.selectedIndex];
  const rate   = parseFloat(opt?.dataset?.rate);
  const unit   = opt?.dataset?.unit;

  if (unit) document.getElementById("act-unit").value = unit;

  const preview = document.getElementById("preview-value");
  if (!isNaN(rate) && !isNaN(qty) && qty > 0) {
    preview.textContent = (rate * qty).toFixed(3);
  } else {
    preview.textContent = "—";
  }
}

async function handleActivityLog(e) {
  e.preventDefault();
  const errEl  = document.getElementById("log-error");
  const succEl = document.getElementById("log-success");
  const btn    = document.getElementById("log-btn");
  errEl.textContent = "";
  succEl.textContent = "";

  const select = document.getElementById("act-subcategory");
  const subcat = select.value;
  const qty    = parseFloat(document.getElementById("act-quantity").value);
  const date   = document.getElementById("act-date").value;

  if (!subcat) { errEl.textContent = "Please select an activity type."; return; }
  if (!qty || qty <= 0) { errEl.textContent = "Please enter a valid quantity."; return; }
  if (!date) { errEl.textContent = "Please select a date."; return; }

  btn.disabled = true;
  btn.innerHTML = '<span>Logging…</span>';

  try {
    await api.createActivity({
      category:      state.selectedCategory,
      subcategory:   subcat,
      quantity:      qty,
      unit:          document.getElementById("act-unit").value,
      description:   document.getElementById("act-description").value.trim() || undefined,
      activity_date: new Date(date).toISOString(),
    });

    succEl.textContent = "✅ Activity logged successfully!";
    document.getElementById("activity-form").reset();
    document.getElementById("act-date").value = new Date().toISOString().split("T")[0];
    document.getElementById("preview-value").textContent = "—";
    selectCategory(state.selectedCategory);
    showToast("Activity logged!", "success");

    setTimeout(() => { succEl.textContent = ""; }, 3000);
  } catch (err) {
    errEl.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i data-lucide="save" aria-hidden="true"></i><span>Log Activity</span>';
    lucide.createIcons();
  }
}

/* ══════════════════════════════════════════════════════════════════════════
   INSIGHTS
══════════════════════════════════════════════════════════════════════════ */
async function loadInsights() {
  try {
    const data = await api.insights();
    state.insightsData = data;
    renderInsights(data);
  } catch (err) {
    showToast("Failed to load insights: " + err.message, "error");
  }
}

function renderInsights(data) {
  renderGaugeChart(data.eco_score);
  document.getElementById("eco-label").textContent = data.score_label;

  // Comparisons
  const compEl = document.getElementById("eco-comparisons");
  const mkComp = (pct, label) => {
    const better = pct < 0;
    const cls = better ? "badge-better" : pct === 0 ? "badge-same" : "badge-worse";
    const txt = better
      ? `${Math.abs(pct).toFixed(1)}% below ${label}`
      : `${pct.toFixed(1)}% above ${label}`;
    return `<div class="eco-comp-row"><span class="eco-comp-badge ${cls}">${better ? "✓" : "↑"}</span><span>${txt}</span></div>`;
  };
  compEl.innerHTML = [
    mkComp(data.comparison_global_pct, "global average"),
    mkComp(data.comparison_national_pct, `${state.user?.country || "national"} average`),
  ].join("");

  // Recommendations
  const recsEl = document.getElementById("recs-grid");
  if (!data.recommendations.length) {
    recsEl.innerHTML = '<p class="muted">No recommendations yet. Log more activities!</p>';
    return;
  }
  recsEl.innerHTML = data.recommendations.map((r, i) => `
    <article class="rec-card glass-card" style="animation-delay:${i * 60}ms; animation: fade-in 0.4s ease backwards;">
      <span class="rec-icon" aria-hidden="true">${r.icon}</span>
      <h4 class="rec-title">${escHtml(r.title)}</h4>
      <p class="rec-desc">${escHtml(r.description)}</p>
      <div class="rec-footer">
        <span class="rec-saving">${r.potential_saving_kg > 0 ? `Save ~${r.potential_saving_kg} kg CO₂e` : "Keep it up!"}</span>
        <span class="diff-badge diff-${r.difficulty}">${r.difficulty}</span>
      </div>
    </article>
  `).join("");

  // Monthly trend
  const trendEl = document.getElementById("monthly-comparison");
  const improving = data.monthly_trend_pct <= 0;
  trendEl.innerHTML = `
    <div class="month-box">
      <div class="month-box-label">Last Month</div>
      <div class="month-box-value">—</div>
      <div class="month-box-unit">kg CO₂e</div>
    </div>
    <div>
      <div class="trend-arrow">${improving ? "↓" : "↑"}</div>
      <div class="trend-pct ${improving ? "improving" : "worsening"}">
        ${data.monthly_trend_pct > 0 ? "+" : ""}${data.monthly_trend_pct.toFixed(1)}%
      </div>
    </div>
    <div class="month-box">
      <div class="month-box-label">This Month</div>
      <div class="month-box-value">${state.dashboardData?.total_co2e_this_month?.toFixed(1) || "—"}</div>
      <div class="month-box-unit">kg CO₂e</div>
    </div>
  `;

  // Tip
  document.getElementById("tip-text").textContent = data.tip_of_the_day || "";
  lucide.createIcons();
}

/* ══════════════════════════════════════════════════════════════════════════
   HISTORY
══════════════════════════════════════════════════════════════════════════ */
async function loadHistory() {
  const params = {
    category: state.historyCategory || undefined,
    start_date: state.historyStart || undefined,
    end_date: state.historyEnd || undefined,
    limit: state.historyPageSize,
    offset: (state.historyPage - 1) * state.historyPageSize,
  };
  try {
    const activities = await api.listActivities(params);
    renderActivityList("history-list", activities, true);
    document.getElementById("page-info").textContent = `Page ${state.historyPage}`;
    document.getElementById("prev-page").disabled = state.historyPage <= 1;
    document.getElementById("next-page").disabled = activities.length < state.historyPageSize;
  } catch (err) {
    showToast("Failed to load history: " + err.message, "error");
  }
}

function filterHistory() {
  state.historyCategory = document.getElementById("filter-category").value;
  state.historyStart    = document.getElementById("filter-start").value;
  state.historyEnd      = document.getElementById("filter-end").value;
  state.historyPage = 1;
  loadHistory();
}

function clearFilters() {
  document.getElementById("filter-category").value = "";
  document.getElementById("filter-start").value = "";
  document.getElementById("filter-end").value = "";
  state.historyCategory = "";
  state.historyStart = "";
  state.historyEnd = "";
  state.historyPage = 1;
  loadHistory();
}

function changePage(delta) {
  state.historyPage = Math.max(1, state.historyPage + delta);
  loadHistory();
}

/* ══════════════════════════════════════════════════════════════════════════
   BADGES
══════════════════════════════════════════════════════════════════════════ */
async function loadBadges() {
  try {
    const data = await api.dashboard();
    renderBadges(data.badges);
  } catch (err) {
    showToast("Failed to load badges: " + err.message, "error");
  }
}

const ALL_BADGES_DEFS = [
  { name: "First Step",         icon: "🌱", description: "Log your first activity" },
  { name: "Week Warrior",       icon: "🔥", description: "Log for 7 consecutive days" },
  { name: "Carbon Cutter",      icon: "✂️", description: "Reduce emissions by 10%" },
  { name: "Green Champion",     icon: "🏆", description: "Stay under goal for a month" },
  { name: "Eco Warrior",        icon: "⚡", description: "Reduce emissions by 50%" },
  { name: "Plant Based Hero",   icon: "🥗", description: "Log 30 plant-based meals" },
  { name: "No Drive November",  icon: "🚶", description: "Zero transport for a week" },
  { name: "Solar Powered",      icon: "☀️", description: "Log renewable energy 10 times" },
];

function renderBadges(earnedBadges) {
  const earnedNames = new Set(earnedBadges.map(b => b.name));
  const grid = document.getElementById("badges-grid");
  grid.innerHTML = ALL_BADGES_DEFS.map((b, i) => {
    const earned = earnedNames.has(b.name);
    const eb = earnedBadges.find(e => e.name === b.name);
    const dateStr = eb?.earned_at ? new Date(eb.earned_at).toLocaleDateString() : "";
    return `
      <article class="badge-card glass-card ${earned ? "earned" : "locked"}" role="listitem"
               style="animation-delay:${i * 40}ms; animation: fade-in 0.4s ease backwards;"
               aria-label="${b.name} badge — ${earned ? "earned" : "not yet earned"}">
        <span class="badge-emoji" aria-hidden="true">${b.icon}</span>
        <span class="badge-name">${escHtml(b.name)}</span>
        <span class="badge-desc">${escHtml(b.description)}</span>
        ${earned ? `<span class="badge-date">Earned ${escHtml(dateStr)}</span>` : '<span class="badge-date" style="color:var(--clr-text-muted)">Locked 🔒</span>'}
      </article>
    `;
  }).join("");
}

/* ══════════════════════════════════════════════════════════════════════════
   ACTIVITY LIST RENDERER (shared)
══════════════════════════════════════════════════════════════════════════ */
function renderActivityList(containerId, activities, deletable = false) {
  const el = document.getElementById(containerId);
  if (!activities || activities.length === 0) {
    el.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon" aria-hidden="true">🌱</span>
        <p>No activities yet. Start logging to see your footprint!</p>
        <button class="btn btn-primary" onclick="navigateTo('log')" style="margin-top:16px">
          <i data-lucide="plus" aria-hidden="true"></i> Log Activity
        </button>
      </div>`;
    lucide.createIcons();
    return;
  }

  el.innerHTML = activities.map((a, i) => {
    const cat   = a.category;
    const icon  = CAT_ICONS[cat] || "📊";
    const label = a.description || a.subcategory.replace(/_/g, " ");
    const date  = new Date(a.activity_date).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
    const isNeg = a.co2e_kg < 0;
    const co2   = isNeg ? `−${Math.abs(a.co2e_kg).toFixed(3)}` : `+${a.co2e_kg.toFixed(3)}`;

    return `
      <div class="activity-item" role="listitem" style="animation-delay:${i * 30}ms">
        <div class="act-icon" aria-hidden="true">${icon}</div>
        <div class="act-body">
          <div class="act-name">${escHtml(label)}</div>
          <div class="act-meta">${escHtml(date)} · ${escHtml(cat)} · ${a.quantity} ${escHtml(a.unit)}</div>
        </div>
        <span class="act-co2 ${isNeg ? "negative" : "positive"}" aria-label="${a.co2e_kg} kg CO2 equivalent">${co2} kg</span>
        ${deletable ? `
          <div class="act-actions">
            <button class="act-del-btn" onclick="openDeleteModal(${a.id})" aria-label="Delete activity: ${escHtml(label)}" title="Delete">
              <i data-lucide="trash-2" aria-hidden="true"></i>
            </button>
          </div>` : ""}
      </div>
    `;
  }).join("");

  lucide.createIcons();
}

/* ══════════════════════════════════════════════════════════════════════════
   DELETE MODAL
══════════════════════════════════════════════════════════════════════════ */
function openDeleteModal(id) {
  state.deleteTargetId = id;
  document.getElementById("delete-modal").classList.remove("hidden");
  document.getElementById("confirm-delete-btn").focus();
}

function closeDeleteModal() {
  state.deleteTargetId = null;
  document.getElementById("delete-modal").classList.add("hidden");
}

async function confirmDelete() {
  if (!state.deleteTargetId) return;
  try {
    await api.deleteActivity(state.deleteTargetId);
    closeDeleteModal();
    showToast("Activity deleted", "success");
    if (state.currentPage === "history") loadHistory();
    if (state.currentPage === "dashboard") loadDashboard();
  } catch (err) {
    showToast("Failed to delete: " + err.message, "error");
    closeDeleteModal();
  }
}

/* ══════════════════════════════════════════════════════════════════════════
   TOAST NOTIFICATIONS
══════════════════════════════════════════════════════════════════════════ */
let toastTimer = null;
function showToast(message, type = "success") {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = `toast show ${type}`;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.classList.remove("show"); }, 3500);
}

/* ══════════════════════════════════════════════════════════════════════════
   UTILITIES
══════════════════════════════════════════════════════════════════════════ */
function escHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function animateCount(id, from, to, duration, prefix = "", suffix = "") {
  const el = document.getElementById(id);
  if (!el) return;
  const start = performance.now();
  const isFloat = !Number.isInteger(to);
  const decimals = isFloat ? 1 : 0;

  function update(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    const value = from + (to - from) * eased;
    el.textContent = prefix + value.toFixed(decimals) + suffix;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

/* ══════════════════════════════════════════════════════════════════════════
   KEYBOARD NAVIGATION
══════════════════════════════════════════════════════════════════════════ */
document.addEventListener("keydown", (e) => {
  // Close modal on Escape
  if (e.key === "Escape") {
    if (!document.getElementById("delete-modal").classList.contains("hidden")) {
      closeDeleteModal();
    }
    if (!document.getElementById("sidebar").classList.contains("hidden") &&
        document.getElementById("sidebar").classList.contains("open")) {
      document.getElementById("sidebar").classList.remove("open");
    }
  }
});

/* ══════════════════════════════════════════════════════════════════════════
   EVENT LISTENERS
══════════════════════════════════════════════════════════════════════════ */
document.addEventListener("DOMContentLoaded", () => {
  // Render Lucide icons
  lucide.createIcons();

  // Auth forms
  document.getElementById("login-form").addEventListener("submit", handleLogin);
  document.getElementById("register-form").addEventListener("submit", handleRegister);

  // Activity form
  document.getElementById("activity-form").addEventListener("submit", handleActivityLog);
  document.getElementById("act-subcategory").addEventListener("change", updateCo2Preview);
  document.getElementById("act-quantity").addEventListener("input", updateCo2Preview);

  // Close modal on overlay click
  document.getElementById("delete-modal").addEventListener("click", (e) => {
    if (e.target === document.getElementById("delete-modal")) closeDeleteModal();
  });

  // Demo user auto-fill
  document.querySelector(".auth-demo")?.addEventListener("click", () => {
    document.getElementById("login-username").value = "demouser";
    document.getElementById("login-password").value = "DemoPass1";
  });

  // Session restore
  loadSession();
  if (state.token && state.user) {
    showApp();
  }

  // Seed demo user on first load
  _ensureDemoUser();
});

/* ══════════════════════════════════════════════════════════════════════════
   DEMO USER BOOTSTRAP
══════════════════════════════════════════════════════════════════════════ */
async function _ensureDemoUser() {
  if (state.token) return; // Already logged in
  try {
    await api.register({
      username: "demouser",
      email: "demo@ecotrack.io",
      password: "DemoPass1",
      full_name: "Demo User",
      country: "United Kingdom",
      annual_goal_kg: 2000,
    });
    // Seed some demo activities
    const demoToken = (await api.login({ username: "demouser", password: "DemoPass1" })).access_token;
    state.token = demoToken;
    const now = new Date();
    const activities = [
      { category: "transport", subcategory: "car_petrol",   quantity: 30,  unit: "km",    activity_date: _daysAgo(now, 1) },
      { category: "food",      subcategory: "beef",          quantity: 0.5, unit: "kg",    activity_date: _daysAgo(now, 1) },
      { category: "energy",    subcategory: "electricity_grid", quantity: 15, unit: "kWh", activity_date: _daysAgo(now, 2) },
      { category: "transport", subcategory: "train_national", quantity: 50, unit: "km",   activity_date: _daysAgo(now, 3) },
      { category: "food",      subcategory: "vegetables",    quantity: 1,   unit: "kg",    activity_date: _daysAgo(now, 3) },
      { category: "shopping",  subcategory: "clothing_new",  quantity: 2,   unit: "item",  activity_date: _daysAgo(now, 5) },
      { category: "travel",    subcategory: "flight_short_haul", quantity: 800, unit: "km", activity_date: _daysAgo(now, 7) },
      { category: "transport", subcategory: "bicycle",       quantity: 8,   unit: "km",    activity_date: _daysAgo(now, 8) },
      { category: "food",      subcategory: "coffee",        quantity: 5,   unit: "cup",   activity_date: _daysAgo(now, 9) },
      { category: "waste",     subcategory: "recycling_paper", quantity: 2, unit: "kg",  activity_date: _daysAgo(now, 10) },
      { category: "energy",    subcategory: "natural_gas_home", quantity: 20, unit: "kWh", activity_date: _daysAgo(now, 12) },
      { category: "food",      subcategory: "chicken",        quantity: 0.3, unit: "kg",   activity_date: _daysAgo(now, 14) },
      { category: "transport", subcategory: "car_petrol",     quantity: 25, unit: "km",    activity_date: _daysAgo(now, 15) },
      { category: "food",      subcategory: "legumes",        quantity: 0.5, unit: "kg",   activity_date: _daysAgo(now, 16) },
      { category: "energy",    subcategory: "electricity_renew", quantity: 10, unit: "kWh", activity_date: _daysAgo(now, 18) },
    ];
    for (const act of activities) {
      try { await api.createActivity(act); } catch (_) {}
    }
    state.token = null; // Reset — user must log in manually or click demo
  } catch (_) {
    // Demo user might already exist, that's fine
  }
}

function _daysAgo(now, days) {
  const d = new Date(now);
  d.setDate(d.getDate() - days);
  return d.toISOString();
}
