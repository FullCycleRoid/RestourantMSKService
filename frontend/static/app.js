const $ = (sel) => document.querySelector(sel);

const state = {
  map: null,
  mapsAvailable: false,
  userPoints: new Map(), // id -> {marker|null, data}
};

async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {}
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

async function init() {
  bindForm();
  initMap();
  try {
    await Promise.all([loadRing(), loadRestaurants(), loadUserPoints()]);
  } catch (e) {
    alert(`Ошибка загрузки данных: ${e.message}`);
  }
}

function initMap() {
  if (typeof L === "undefined") {
    $("#map").innerHTML =
      '<div class="map-error">Карта недоступна (Leaflet не загрузился).<br>Сайдбар работает без карты.</div>';
    state.mapsAvailable = false;
    return;
  }
  state.map = L.map("map").setView([55.7558, 37.6173], 13);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(state.map);
  state.mapsAvailable = true;
}

async function loadRing() {
  const feature = await fetchJSON("/api/garden-ring");
  if (!state.mapsAvailable) return;
  L.geoJSON(feature, {
    style: {
      color: "#ff8a00",
      weight: 3,
      fillColor: "#ff8a00",
      fillOpacity: 0.1,
    },
  }).addTo(state.map);
}

async function loadRestaurants() {
  const items = await fetchJSON("/api/restaurants");
  $("#rest-count").textContent = items.length;
  if (!state.mapsAvailable) return;
  for (const r of items) {
    L.circleMarker([r.lat, r.lon], {
      radius: 7,
      color: "#fff",
      weight: 2,
      fillColor: "#d23",
      fillOpacity: 1,
    })
      .bindPopup(
        `<strong>${escapeHTML(r.name)}</strong> ★${r.rating}<br>${escapeHTML(r.address || "")}`
      )
      .addTo(state.map);
  }
}

async function loadUserPoints() {
  const items = await fetchJSON("/api/user-points");
  for (const p of items) addUserPointToUI(p);
}

function addUserPointToUI(p) {
  let marker = null;
  if (state.mapsAvailable) {
    const icon = L.divIcon({
      className: "user-point-icon",
      html: '<div class="user-point-marker">★</div>',
      iconSize: [22, 22],
      iconAnchor: [11, 11],
    });
    marker = L.marker([p.lat, p.lon], { icon })
      .bindPopup(
        `<strong>${escapeHTML(p.name || "(без имени)")}</strong><br>${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}`
      )
      .addTo(state.map);
  }
  state.userPoints.set(p.id, { marker, data: p });
  renderUserPointsList();
}

function removeUserPointFromUI(id) {
  const entry = state.userPoints.get(id);
  if (!entry) return;
  if (entry.marker && state.mapsAvailable) {
    state.map.removeLayer(entry.marker);
  }
  state.userPoints.delete(id);
  renderUserPointsList();
}

function renderUserPointsList() {
  const ul = $("#user-points-list");
  ul.innerHTML = "";
  $("#points-count").textContent = state.userPoints.size;
  for (const { data } of state.userPoints.values()) {
    const li = document.createElement("li");
    li.innerHTML = `
      <span>
        <strong>${escapeHTML(data.name || "(без имени)")}</strong><br>
        <span class="meta">${data.lat.toFixed(5)}, ${data.lon.toFixed(5)}</span>
      </span>
      <button type="button" title="Удалить">×</button>
    `;
    li.querySelector("button").addEventListener("click", () => deletePoint(data.id));
    ul.appendChild(li);
  }
}

function bindForm() {
  $("#add-point-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fd = new FormData(ev.target);
    const body = {
      lat: parseFloat(fd.get("lat")),
      lon: parseFloat(fd.get("lon")),
    };
    const name = (fd.get("name") || "").trim();
    if (name) body.name = name;
    try {
      const created = await fetchJSON("/api/user-points", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      addUserPointToUI(created);
      if (state.mapsAvailable) {
        state.map.setView([created.lat, created.lon], state.map.getZoom());
      }
      ev.target.reset();
    } catch (e) {
      alert(`Не удалось добавить точку: ${e.message}`);
    }
  });
}

async function deletePoint(id) {
  try {
    await fetchJSON(`/api/user-points/${id}`, { method: "DELETE" });
    removeUserPointFromUI(id);
  } catch (e) {
    alert(`Не удалось удалить точку: ${e.message}`);
  }
}

function escapeHTML(s) {
  return String(s).replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

init();
