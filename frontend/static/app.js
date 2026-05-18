const $ = (sel) => document.querySelector(sel);

const state = {
  map: null,
  restaurantsLayer: null,
  userPointsLayer: null,
  ringLayer: null,
  userPoints: new Map(), // id -> {marker, data}
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
  if (typeof ymaps3 === "undefined") {
    $("#map").innerHTML = '<div class="map-error">Карта недоступна (Yandex Maps не загрузился)</div>';
    return;
  }
  await ymaps3.ready;
  const { YMap, YMapDefaultSchemeLayer, YMapDefaultFeaturesLayer, YMapMarker, YMapFeature } = ymaps3;

  state.map = new YMap($("#map"), {
    location: { center: [37.6173, 55.7558], zoom: 12 },
  });
  state.map.addChild(new YMapDefaultSchemeLayer());
  state.map.addChild(new YMapDefaultFeaturesLayer());

  await Promise.all([loadRing(), loadRestaurants(), loadUserPoints()]);
  bindForm();
}

async function loadRing() {
  const feature = await fetchJSON("/api/garden-ring");
  const { YMapFeature } = ymaps3;
  const ringFeature = new YMapFeature({
    geometry: feature.geometry,
    style: {
      stroke: [{ color: "#ff8a00", width: 3 }],
      fill: "rgba(255, 138, 0, 0.10)",
    },
  });
  state.map.addChild(ringFeature);
  state.ringLayer = ringFeature;
}

async function loadRestaurants() {
  const items = await fetchJSON("/api/restaurants");
  $("#rest-count").textContent = items.length;
  const { YMapMarker } = ymaps3;
  for (const r of items) {
    const el = document.createElement("div");
    el.style.cssText = "width:14px;height:14px;background:#d23;border:2px solid #fff;border-radius:50%;box-shadow:0 0 3px rgba(0,0,0,0.4);cursor:pointer;";
    el.title = `${r.name} ★${r.rating}\n${r.address || ""}`;
    const m = new YMapMarker({ coordinates: [r.lon, r.lat] }, el);
    state.map.addChild(m);
  }
}

async function loadUserPoints() {
  const items = await fetchJSON("/api/user-points");
  for (const p of items) addUserPointToUI(p);
}

function addUserPointToUI(p) {
  const { YMapMarker } = ymaps3;
  const el = document.createElement("div");
  el.style.cssText = "width:18px;height:18px;background:#2d7ff9;color:#fff;font-size:12px;line-height:18px;text-align:center;border:2px solid #fff;border-radius:50%;box-shadow:0 0 3px rgba(0,0,0,0.4);cursor:pointer;";
  el.textContent = "★";
  el.title = `${p.name || "(без имени)"} ${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}`;
  const marker = new YMapMarker({ coordinates: [p.lon, p.lat] }, el);
  state.map.addChild(marker);
  state.userPoints.set(p.id, { marker, data: p });
  renderUserPointsList();
}

function removeUserPointFromUI(id) {
  const entry = state.userPoints.get(id);
  if (!entry) return;
  state.map.removeChild(entry.marker);
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
      <button type="button" data-id="${data.id}" title="Удалить">×</button>
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
  return String(s).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
}

init();
