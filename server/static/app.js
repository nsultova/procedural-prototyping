const PRESETS = { A4: [210, 297], A3: [297, 420], Square: [200, 200] };
const state = {
  artwork: null, spec: null, params: {},
  canvas: { width: 200, height: 200, preset: "Square" },
  view: { scale: 1, x: 0, y: 0 },
};
let renderTimer = null;
let renderSeq = 0;   // guards against a slow render overwriting a newer one
let loadSeq = 0;     // guards against rapid artwork switches racing

const $ = (sel) => document.querySelector(sel);

async function boot() {
  const artworks = await (await fetch("/api/artworks")).json();
  const select = $("#artwork-select");
  artworks.forEach((a) => {
    const opt = document.createElement("option");
    opt.value = a.name; opt.textContent = a.title;
    select.appendChild(opt);
  });
  select.style.display = artworks.length > 1 ? "" : "none";
  select.addEventListener("change", () => loadArtwork(select.value));

  wireFooter();

  if (!artworks.length) {
    showError("No artworks found. Add one under artworks/ and restart the server.");
    return;
  }
  await loadArtwork(artworks[0].name);
}

async function loadArtwork(name) {
  const seq = ++loadSeq;
  state.artwork = name;
  let spec;
  try {
    spec = await (await fetch(`/api/spec/${name}`)).json();
  } catch (e) {
    showError(`Failed to load ${name}: ${e.message}`);
    return;
  }
  if (seq !== loadSeq) return;  // a newer switch superseded this one

  state.spec = spec;
  $("#title").textContent = spec.title;
  $("#subtitle").textContent = spec.subtitle || "";
  state.params = {};
  spec.params.forEach((p) => (state.params[p.name] = p.default));
  buildPanel();
  scheduleRender();
}

function buildPanel() {
  const panel = $("#panel");
  panel.innerHTML = "";

  const cg = group("Canvas");
  const presetRow = document.createElement("div");
  presetRow.className = "preset-row";
  const clearPresetActive = () => {
    presetRow.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
    state.canvas.preset = null;
  };
  Object.keys(PRESETS).forEach((name) => {
    const b = document.createElement("button");
    b.textContent = name;
    if (state.canvas.preset === name) b.classList.add("active");
    b.addEventListener("click", () => {
      const [w, h] = PRESETS[name];
      state.canvas = { width: w, height: h, preset: name };
      buildPanel();     // rebuild so width/height sliders reflect the preset
      scheduleRender();
    });
    presetRow.appendChild(b);
  });
  cg.appendChild(presetRow);
  cg.appendChild(rangeCtrl(
    { name: "width", label: "Width (mm)", min: 50, max: 420, step: 1,
      default: state.canvas.width },
    (v) => { state.canvas.width = v; clearPresetActive(); scheduleRender(); }));
  cg.appendChild(rangeCtrl(
    { name: "height", label: "Height (mm)", min: 50, max: 420, step: 1,
      default: state.canvas.height },
    (v) => { state.canvas.height = v; clearPresetActive(); scheduleRender(); }));
  panel.appendChild(cg);

  const groups = {};
  state.spec.params.forEach((p) => {
    (groups[p.group] = groups[p.group] || []).push(p);
  });
  Object.entries(groups).forEach(([gname, params]) => {
    const g = group(gname);
    params.forEach((p) => {
      g.appendChild(rangeCtrl(p, (v) => {
        state.params[p.name] = v; scheduleRender();
      }, state.params[p.name]));
    });
    panel.appendChild(g);
  });
}

function group(name) {
  const g = document.createElement("div");
  g.className = "group";
  const h = document.createElement("h3");
  h.textContent = name; g.appendChild(h);
  return g;
}

function rangeCtrl(p, onChange, current) {
  const wrap = document.createElement("div");
  wrap.className = "ctrl";
  const row = document.createElement("div");
  row.className = "row";
  const label = document.createElement("span");
  label.textContent = p.label;
  const val = document.createElement("span");
  val.className = "val";
  row.append(label, val);

  const input = document.createElement("input");
  input.type = "range";
  input.min = p.min; input.max = p.max; input.step = p.step;
  input.value = current !== undefined ? current : p.default;
  const fmt = () => (val.textContent = (+input.value).toString());
  fmt();
  input.addEventListener("input", () => { fmt(); onChange(+input.value); });

  wrap.append(row, input);
  return wrap;
}

function buildPayload(extra = {}) {
  return {
    artwork: state.artwork,
    seed: +$("#seed").value || 0,
    canvas: { width: state.canvas.width, height: state.canvas.height },
    params: state.params,
    ...extra,
  };
}

function scheduleRender() {
  clearTimeout(renderTimer);
  renderTimer = setTimeout(doRender, 50);
}

async function doRender() {
  const seq = ++renderSeq;
  let body;
  try {
    const r = await fetch("/api/render", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildPayload()),
    });
    body = await r.json();
    if (!r.ok) throw new Error(body.error || "render failed");
  } catch (e) {
    if (seq === renderSeq) showError(e.message);
    return;
  }
  if (seq !== renderSeq) return;  // a newer render superseded this response
  hideError();
  $("#canvas").innerHTML = body.svg;
  $("#timing").textContent = `${body.ms} ms`;
  applyView();
}

function showError(msg) { const e = $("#error"); e.hidden = false; e.textContent = msg; }
function hideError() { $("#error").hidden = true; }

function applyView() {
  const wrap = $("#canvas-wrap");
  const v = state.view;
  wrap.style.transform = `translate(${v.x}px, ${v.y}px) scale(${v.scale})`;
  $("#zoom").textContent = `${Math.round(v.scale * 100)}%`;
}

function wireFooter() {
  $("#seed").addEventListener("change", scheduleRender);
  $("#randomize").addEventListener("click", () => {
    $("#seed").value = Math.floor(Math.random() * 1e9);
    scheduleRender();
  });
  $("#rerender").addEventListener("click", scheduleRender);
  $("#reset-zoom").addEventListener("click", () => {
    state.view = { scale: 1, x: 0, y: 0 }; applyView();
  });
  $("#save-draft").addEventListener("click", () => exportSvg("drafts"));
  $("#save-keeper").addEventListener("click", () => exportSvg("keepers"));

  const stage = $("#stage");
  let dragging = false, sx = 0, sy = 0;
  stage.addEventListener("mousedown", (e) => {
    dragging = true; sx = e.clientX - state.view.x; sy = e.clientY - state.view.y;
    $("#canvas-wrap").style.cursor = "grabbing";
  });
  window.addEventListener("mouseup", () => {
    dragging = false; $("#canvas-wrap").style.cursor = "grab";
  });
  window.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    state.view.x = e.clientX - sx; state.view.y = e.clientY - sy; applyView();
  });
  stage.addEventListener("wheel", (e) => {
    e.preventDefault();
    const f = e.deltaY < 0 ? 1.1 : 1 / 1.1;
    state.view.scale = Math.max(0.1, Math.min(10, state.view.scale * f));
    applyView();
  }, { passive: false });
}

async function exportSvg(kind) {
  let body;
  try {
    const r = await fetch("/api/render", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildPayload({ export: true })),
    });
    body = await r.json();
    if (!r.ok) throw new Error(body.error || "export failed");
  } catch (e) {
    showError(e.message);
    return;
  }
  const blob = new Blob([body.svg], { type: "image/svg+xml" });
  const a = document.createElement("a");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  a.href = URL.createObjectURL(blob);
  a.download = `${state.artwork}_${kind}_s${$("#seed").value}_${stamp}.svg`;
  a.click();
  URL.revokeObjectURL(a.href);
}

boot().catch((e) => showError(`Startup failed: ${e.message}`));
