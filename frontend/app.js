/* =========================================================
   Smart Home IoT Dashboard - frontend (vanilla JS)
   Kết nối REST API của backend Flask.
   ========================================================= */

/* ---------------- DATA LAYER ---------------- */
const API_BASE = `${window.location.protocol}//${window.location.hostname}:3000/api`;
const API_POLL_MS = 3000;
let apiPassword = "";

const apiFetch = (url, options = {}) => fetch(url, options);

const historyRows = [];
const sensorRows = [];

async function sendDeviceCommand(deviceId, on) {
  if (!apiPassword) {
    apiPassword = window.prompt("Nhập mật khẩu API để điều khiển đèn:") || "";
  }
  if (!apiPassword) throw new Error("Đã hủy thao tác.");
  const response = await apiFetch(`${API_BASE}/devices/${deviceId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Password": apiPassword },
    body: JSON.stringify({ on }),
  });
  const result = await response.json();
  if (response.status === 401) apiPassword = "";
  if (!response.ok) throw new Error(result.error || "Không gửi được lệnh");
  await refreshHistory();
}

// Lấy số liệu cảm biến mới nhất qua REST API.
async function fetchLatest() {
  const res = await apiFetch(`${API_BASE}/sensors/latest`);
  if (!res.ok) throw new Error((await res.json()).error || "Không lấy được dữ liệu cảm biến");
  return res.json(); // { temp, light, hum, time }
}

async function refreshSensorRows() {
  const res = await apiFetch(`${API_BASE}/sensors?limit=100`);
  if (!res.ok) throw new Error("Không lấy được lịch sử cảm biến");
  const result = await res.json();
  sensorRows.splice(0, sensorRows.length, ...result.data);
  dataTable.render();
  hydrateChartFromRows(sensorRows);
}

async function refreshHistory() {
  const res = await apiFetch(`${API_BASE}/history?limit=100`);
  if (!res.ok) throw new Error("Không lấy được lịch sử điều khiển");
  const result = await res.json();
  historyRows.splice(0, historyRows.length, ...result.data);
  historyTable.render();
}

/* ---------------- ROUTER ---------------- */
const routes = ["dashboard", "data", "history", "profile"];

function navigate() {
  const hash = location.hash.replace("#/", "") || "dashboard";
  const route = routes.includes(hash) ? hash : "dashboard";
  routes.forEach((r) => document.getElementById(`page-${r}`).classList.toggle("active", r === route));
  document.querySelectorAll(".nav a").forEach((a) => a.classList.toggle("active", a.dataset.route === route));
  if (route === "history") historyTable.render();
  if (route === "data") dataTable.render();
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", navigate);

/* ---------------- GENERIC TABLE (lọc + sắp xếp + phân trang) ---------------- */
function createTable({ bodyId, pagerId, headSelector, getRows, filter, renderRow, onRender, defaultSort, sizeEl }) {
  const state = { page: 1, sortKey: defaultSort.key, sortDir: defaultSort.dir };
  const body = document.getElementById(bodyId);
  const pager = document.getElementById(pagerId);
  const heads = document.querySelectorAll(headSelector);

  heads.forEach((th) =>
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      state.sortDir = state.sortKey === key && state.sortDir === "asc" ? "desc" : "asc";
      state.sortKey = key;
      state.page = 1;
      render();
    })
  );

  function render() {
    const all = getRows();
    let rows = all.filter(filter);

    const { sortKey: k, sortDir: dir } = state;
    rows.sort((a, b) => {
      const x = a[k], y = b[k];
      const cmp = typeof x === "number" ? x - y : String(x).localeCompare(String(y), "vi");
      return dir === "asc" ? cmp : -cmp;
    });

    const sizeControl = sizeEl ? document.getElementById(sizeEl) : null;
    const size = sizeControl ? +sizeControl.value : 10;
    const pages = Math.max(1, Math.ceil(rows.length / size));
    state.page = Math.min(state.page, pages);
    const slice = rows.slice((state.page - 1) * size, state.page * size);

    body.innerHTML = slice.length
      ? slice.map(renderRow).join("")
      : `<tr><td class="empty" colspan="5">Không có dữ liệu phù hợp</td></tr>`;

    heads.forEach((th) => {
      th.classList.remove("asc", "desc");
      if (th.dataset.sort === k) th.classList.add(dir);
    });

    renderPager(pages);
    onRender && onRender(rows, all);
  }

  function renderPager(pages) {
    if (pages <= 1) { pager.innerHTML = ""; return; }
    let html = `<button data-p="prev" ${state.page === 1 ? "disabled" : ""}>← Trước</button>`;
    for (let p = 1; p <= pages; p++) {
      html += `<button data-p="${p}" class="${p === state.page ? "active" : ""}">${p}</button>`;
    }
    html += `<button data-p="next" ${state.page === pages ? "disabled" : ""}>Tiếp →</button>`;
    pager.innerHTML = html;
  }

  pager.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b || b.disabled) return;
    const p = b.dataset.p;
    state.page = p === "prev" ? state.page - 1 : p === "next" ? state.page + 1 : +p;
    render();
  });

  return { render, resetPage: () => (state.page = 1) };
}

const slug = (s) => s.toLowerCase().replace(/\s+/g, "");

/* ---------------- SEARCH TOOLBARS ---------------- */
document.getElementById("data-search").addEventListener("submit", (event) => {
  event.preventDefault();
  appliedDataFilters = {
    query: document.getElementById("d-q").value.trim().toLowerCase(),
    type: document.getElementById("d-type").value,
  };
  dataTable.resetPage();
  dataTable.render();
});
document.getElementById("history-search").addEventListener("submit", (event) => {
  event.preventDefault();
  appliedHistoryFilters = {
    query: document.getElementById("h-q").value.trim().toLowerCase(),
    device: document.getElementById("h-device").value,
    action: document.getElementById("h-action").value,
    status: document.getElementById("h-status").value,
  };
  historyTable.resetPage();
  historyTable.render();
});

let appliedDataFilters = { query: "", type: "" };
let appliedHistoryFilters = { query: "", device: "", action: "", status: "" };

/* ---------------- TRANG DỮ LIỆU ---------------- */
const dataTable = createTable({
  bodyId: "data-body",
  pagerId: "data-pager",
  headSelector: "#page-data thead th",
  sizeEl: "d-size",
  defaultSort: { key: "id", dir: "asc" },
  getRows: () => sensorRows,
  filter: (r) => {
    const { query: q, type } = appliedDataFilters;
    if (type === "time") return !q || r.time.toLowerCase().includes(q);
    if (type) {
      const isSelectedType = r.type === type;
      const valueMatches = !q || `${r.value} ${r.unit}`.toLowerCase().includes(q);
      return isSelectedType && valueMatches;
    }
    const hay = `${r.id} ${r.sensor} ${r.type} ${r.value} ${r.unit} ${r.time}`.toLowerCase();
    return !q || hay.includes(q);
  },
  renderRow: (r) => {
    const color = r.type === "Nhiệt độ" ? "c-orange" : r.type === "Độ ẩm" ? "c-green" : "";
    const lux = r.type === "Ánh sáng" ? 'style="color:#f5a524"' : "";
    return `<tr>
      <td class="id">#${r.id}</td>
      <td><span class="badge b-${slug(r.sensor)}">${r.sensor}</span></td>
      <td>${r.type}</td>
      <td><b class="${color}" ${lux}>${r.value}</b> ${r.unit}</td>
      <td>${r.time}</td>
    </tr>`;
  },
  onRender: (rows, all) => {
    document.getElementById("data-count").textContent = `${rows.length} / ${all.length} bản ghi`;
  },
});

document.getElementById("d-type").addEventListener("change", (event) => {
  const type = event.target.value;
  const labels = { "": "Tìm kiếm chung...", "Nhiệt độ": "Tìm kiếm Nhiệt độ...", "Độ ẩm": "Tìm kiếm Độ ẩm...", "Ánh sáng": "Tìm kiếm Ánh sáng...", time: "Tìm kiếm Thời gian..." };
  document.getElementById("d-q").placeholder = labels[type] || labels[""];
});

/* ---------------- TRANG LỊCH SỬ ---------------- */
const historyTable = createTable({
  bodyId: "history-body",
  pagerId: "history-pager",
  headSelector: "#page-history thead th",
  sizeEl: "h-size",
  defaultSort: { key: "id", dir: "desc" },
  getRows: () => historyRows,
  filter: (r) => {
    const { query: q, action, device, status } = appliedHistoryFilters;
    const hay = `${r.id} ${r.device} ${r.action} ${r.desc} ${r.status} ${r.time}`.toLowerCase();
    return (!q || hay.includes(q)) && (!action || r.action === action) &&
      (!device || r.device === device) && (!status || r.status === ({ failed: "Thất bại", success: "Thành công", pending: "Đang chờ" })[status]);
  },
  renderRow: (r) => `<tr>
      <td class="id">#${r.id}</td>
      <td><span class="badge b-${slug(r.device)}">${r.device}</span></td>
      <td><span class="badge ${r.action === "BẬT" ? "b-on" : "b-off"}">${r.action}</span></td>
      <td><span class="history-status ${r.status === "Thất bại" ? "failed" : r.status === "Đang chờ" ? "pending" : "success"}">${r.status}</span></td>
      <td>${r.time}</td>
    </tr>`,
  onRender: () => {
    const on = historyRows.filter((r) => r.action === "BẬT").length;
    document.getElementById("h-total").textContent = historyRows.length;
    document.getElementById("h-on").textContent = on;
    document.getElementById("h-off").textContent = historyRows.length - on;
  },
});

["d-size", "h-size"].forEach((id) => {
  document.getElementById(id).addEventListener("change", () => {
    const table = id === "d-size" ? dataTable : historyTable;
    table.resetPage();
    table.render();
  });
});

/* ---------------- DASHBOARD ---------------- */
const devices = [
  { key: "led1", id: 1, name: "LED1", sub: "LED 1", historyName: "LED1", on: false, pending: false },
  { key: "led2", id: 2, name: "LED2", sub: "LED 2", historyName: "LED2", on: false, pending: false },
];

function renderDevices() {
  const wrap = document.getElementById("devices");
  wrap.innerHTML = devices
    .map(
      (d) => `<div class="device">
        <div><strong>${d.name}</strong><span class="d-sub">${d.sub}</span></div>
        <div class="right">
          <span class="state ${d.on ? "on" : ""} ${d.pending ? "pending" : ""}" id="state-${d.key}">${d.pending ? "ĐANG CHỜ" : d.on ? "BẬT" : "TẮT"}</span>
          <label class="switch" aria-label="${d.on ? "Tắt" : "Bật"} ${d.name}">
            <input type="checkbox" data-key="${d.key}" ${d.on ? "checked" : ""} ${d.pending ? "disabled" : ""} />
            <span class="slider"></span>
          </label>
        </div>
      </div>`
    )
    .join("");

  wrap.querySelectorAll("input[data-key]").forEach((input) => {
    input.addEventListener("change", async () => {
      const device = devices.find((item) => item.key === input.dataset.key);
      const previous = device.on;
      const desired = input.checked;
      device.pending = true;
      device.requested = desired;
      device.pendingUntil = Date.now() + 10000;
      renderDevices();
      try {
        await sendDeviceCommand(device.id, desired);
        setTimeout(loadDevices, 1000);
      } catch (error) {
        device.pending = false;
        device.on = previous;
        renderDevices();
        if (error.message !== "Đã hủy thao tác.") alert(error.message);
      }
    });
  });
}

// Nhãn trạng thái
const tempStatus = (v) => (v < 18 ? "Lạnh" : v > 30 ? "Nóng" : "Bình thường");
const lightStatus = (v) => (v < 200 ? "Tối" : v > 600 ? "Sáng" : "Trung bình");
const humStatus = (v) => (v < 40 ? "Khô" : v > 75 ? "Ẩm" : "Bình thường");

// Biểu đồ
const MAX_POINTS = 10;
const chartLabels = [];
const series = { temp: [], light: [], hum: [] };
let chart;
const pad = (value) => String(value).padStart(2, "0");

function initChart() {
  const ctx = document.getElementById("envChart");
  const ds = (label, color, data) => ({
    label, data, borderColor: color, borderWidth: 2, tension: 0.4, pointRadius: 0, pointHoverRadius: 4, fill: false,
  });
  const lightDataset = ds("Ánh sáng (ADC)", "#2f6bf0", series.light);
  lightDataset.yAxisID = "yLight";
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: chartLabels,
      datasets: [
        ds("Nhiệt độ (°C)", "#f26b3a", series.temp),
        lightDataset,
        ds("Độ ẩm (%)", "#16a34a", series.hum),
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      interaction: { mode: "index", intersect: false },
      scales: {
        y: { min: 0, max: 80, position: "left", ticks: { stepSize: 20, font: { size: 10 } }, grid: { color: "#e5e7eb", borderDash: [3, 3] } },
        yLight: { min: 0, max: 1000, position: "right", ticks: { stepSize: 200, font: { size: 10 } }, grid: { drawOnChartArea: false } },
        x: { ticks: { font: { size: 10 } }, grid: { color: "#e5e7eb", borderDash: [3, 3] } },
      },
      plugins: {
        legend: { position: "bottom", labels: { usePointStyle: true, pointStyle: "line", boxWidth: 24, font: { size: 10 } } },
      },
    },
  });
}

function pushPoint(d, recordedAt) {
  const now = recordedAt ? new Date(recordedAt.replace(" ", "T")) : new Date();
  chartLabels.push(`${pad(now.getHours())}:${pad(now.getMinutes())}`);
  series.temp.push(d.temp);
  series.light.push(d.light);
  series.hum.push(d.hum);
  if (chartLabels.length > MAX_POINTS) {
    chartLabels.shift(); series.temp.shift(); series.light.shift(); series.hum.shift();
  }
  chart.update();
}

function hydrateChartFromRows(rows) {
  if (!chart || !rows.length) return;
  const byTime = new Map();
  rows.forEach((row) => {
    let sample = byTime.get(row.time);
    if (!sample) {
      sample = { time: row.time };
      byTime.set(row.time, sample);
    }
    if (row.type === "Nhiệt độ") sample.temp = Number(row.value);
    if (row.type === "Độ ẩm") sample.hum = Number(row.value);
    if (row.type === "Ánh sáng") sample.light = Number(row.value);
  });

  const samples = [...byTime.values()]
    .filter((sample) => Number.isFinite(sample.temp) && Number.isFinite(sample.hum) && Number.isFinite(sample.light))
    .sort((a, b) => new Date(a.time.replace(" ", "T")) - new Date(b.time.replace(" ", "T")))
    .slice(-MAX_POINTS);
  if (!samples.length) return;

  chartLabels.splice(0, chartLabels.length, ...samples.map((sample) => {
    const time = new Date(sample.time.replace(" ", "T"));
    return `${pad(time.getHours())}:${pad(time.getMinutes())}:${pad(time.getSeconds())}`;
  }));
  series.temp.splice(0, series.temp.length, ...samples.map((sample) => sample.temp));
  series.hum.splice(0, series.hum.length, ...samples.map((sample) => sample.hum));
  series.light.splice(0, series.light.length, ...samples.map((sample) => sample.light));
  lastChartReading = samples[samples.length - 1].time;
  chart.update("none");
}

async function tick() {
  try {
    const d = await fetchLatest();
    document.getElementById("val-temp").textContent = d.temp;
    document.getElementById("val-light").textContent = d.light;
    document.getElementById("val-hum").textContent = d.hum;
    document.getElementById("sub-temp").textContent = `Cảm biến DHT11 · ${tempStatus(d.temp)}`;
    document.getElementById("sub-light").textContent = `Cảm biến LDR · ${lightStatus(d.light)}`;
    document.getElementById("sub-hum").textContent = `Cảm biến DHT11 · ${humStatus(d.hum)}`;
    if (d.time !== lastChartReading) {
      pushPoint(d, d.time);
      lastChartReading = d.time;
    }
  } catch (err) {
    console.error("Không lấy được dữ liệu cảm biến:", err);
  }
  // Refresh the table on every poll so a temporary API failure does not leave it empty.
  try {
    await refreshSensorRows();
  } catch (err) {
    console.error("Không tải được bảng dữ liệu cảm biến:", err);
  }
}

let lastChartReading = null;

function setSystemStatus(status) {
  const set = (id, online, onText, offText) => {
    const el = document.getElementById(id);
    el.textContent = online ? onText : offText;
    el.classList.toggle("offline", !online);
    el.previousElementSibling?.classList.toggle("offline-dot", !online);
  };
  if (typeof status.mqttConnected === "boolean") set("mqtt-status", status.mqttConnected, "Connected", "Disconnected");
  if (typeof status.sensorOnline === "boolean") set("esp-status", status.sensorOnline, "Online", "Offline");
}

async function refreshHealth() {
  try {
    const response = await apiFetch(`${API_BASE}/health`);
    const status = await response.json();
    setSystemStatus(status);
  } catch (error) {
    console.error("Không gọi được API health:", error);
    setSystemStatus({ mqttConnected: false, sensorOnline: false });
  }
}

/* ---------------- KHỞI TẠO ---------------- */
async function loadDevices() {
  try {
    const response = await apiFetch(`${API_BASE}/devices`);
    if (!response.ok) throw new Error("Không lấy được trạng thái thiết bị");
    const rows = await response.json();
    rows.forEach((row) => {
      const device = devices.find((d) => d.key === `led${row.id}`);
      if (!device) return;
      if (device.pending) {
        if (row.on === device.requested || Date.now() >= device.pendingUntil) {
          device.pending = false;
          device.on = row.on;
        }
      } else {
        device.on = row.on;
      }
    });
    renderDevices();
  } catch (error) {
    console.error("Không lấy được trạng thái thiết bị:", error);
  }
}

renderDevices();
loadDevices();
refreshHistory().catch(err => console.error(err));
initChart();
tick();
refreshHealth();
setInterval(tick, API_POLL_MS);
setInterval(refreshHealth, API_POLL_MS);
setInterval(loadDevices, API_POLL_MS);
navigate();
