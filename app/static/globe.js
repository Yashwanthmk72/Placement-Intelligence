/* World view: 3D globe, country detail, what-if, compare + ranking. Uses d3 (vendored), $, api, state, escapeHtml, formatINR from app.js */
(function () {
  const W = { data: null, est: null, profile: null, selected: null, hover: null, compare: [], metric: "gross_inr",
    weights: { pay: 40, save: 40, ease: 20 }, features: [], rot: [-20, -20, 0], zoom: 1, auto: true, inited: false, ctrl: null, timer: null, mapOK: false };
  const DEFAULT_PROFILE = { name: "Typical student", cgpa: 7.5, major_projects: 1, mini_projects: 1, workshops: 1, skills_count: 6, communication: 4, internship: "No", hackathon: "No", twelfth: 70, tenth: 75, backlogs: 0, skills: [] };
  const flag = c => String.fromCodePoint(...[...c].map(ch => 127397 + ch.charCodeAt(0)));
  const fmt = (n, cur) => new Intl.NumberFormat("en", { notation: n > 9999999 ? "compact" : "standard", maximumFractionDigits: 0 }).format(n) + (cur ? " " + cur : "");
  const lakh = v => v >= 1e7 ? (v / 1e7).toFixed(2) + " Cr" : (v / 1e5).toFixed(1) + " L";
  const inr = v => (v < 0 ? "−₹" : "₹") + lakh(Math.abs(v));

  function topo(t) { // minimal topojson -> GeoJSON features decoder
    const [sx, sy] = t.transform.scale, [tx, ty] = t.transform.translate;
    const arcs = t.arcs.map(a => { let x = 0, y = 0; return a.map(([dx, dy]) => [(x += dx) * sx + tx, (y += dy) * sy + ty]); });
    const arc = i => i < 0 ? arcs[~i].slice().reverse() : arcs[i];
    const ring = idx => { const r = idx.flatMap((i, k) => { const a = arc(i); return k ? a.slice(1) : a; }); return d3.geoArea({ type: "Polygon", coordinates: [r] }) > 2 * Math.PI ? r.reverse() : r; };
    return t.objects.countries.geometries.map(g => {
      const polys = g.type === "Polygon" ? [g.arcs] : g.type === "MultiPolygon" ? g.arcs : [];
      return { id: String(g.id ?? "").padStart(3, "0"), name: g.properties?.name, geometry: { type: "MultiPolygon", coordinates: polys.map(p => p.map(ring)) } };
    });
  }
  const score = (id, m = W.metric) => {
    const e = W.est?.[id]; if (!e) return null; const c = W.byId[id];
    if (m === "ease") return c.ease; if (m === "fit") return W.fit[id]; return e[m];
  };
  function computeFit() {
    const ids = Object.keys(W.est), norm = f => { const v = ids.map(f), lo = Math.min(...v), hi = Math.max(...v); return id => (f(id) - lo) / ((hi - lo) || 1); };
    const p = norm(i => W.est[i].gross_inr), s = norm(i => W.est[i].savings_inr), e = norm(i => W.byId[i].ease);
    const tw = W.weights.pay + W.weights.save + W.weights.ease || 1; W.fit = {};
    ids.forEach(i => W.fit[i] = (W.weights.pay * p(i) + W.weights.save * s(i) + W.weights.ease * e(i)) / tw);
  }
  const ramp = [[42, 58, 143], [34, 211, 238], [139, 92, 246], [255, 95, 210]];
  function color(t) { t = Math.max(0, Math.min(1, t)) * 3; const i = Math.min(2, Math.floor(t)), f = t - i; const a = ramp[i], b = ramp[i + 1]; return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * f)).join(",")})`; }
  function norm(id) { const ids = Object.keys(W.est), v = ids.map(i => score(i)), lo = Math.min(...v), hi = Math.max(...v); return (score(id) - lo) / ((hi - lo) || 1); }

  /* ---------- globe rendering ---------- */
  let cv, ctx, proj, path, size = { w: 600, h: 500 }, vel = [0, 0], dragging = false, last = null, raf = null;
  function resize() { const r = cv.parentElement.getBoundingClientRect(), d = window.devicePixelRatio || 1; size = { w: r.width, h: r.height }; cv.width = r.width * d; cv.height = r.height * d; ctx.setTransform(d, 0, 0, d, 0, 0); }
  function radius() { return Math.min(size.w, size.h) * 0.43 * W.zoom; }
  function draw() {
    const { w, h } = size, r = radius(); ctx.clearRect(0, 0, w, h);
    proj.translate([w / 2, h / 2]).scale(r).rotate(W.rot); path = d3.geoPath(proj, ctx);
    const light = document.documentElement.dataset.theme === "light";
    const halo = ctx.createRadialGradient(w / 2, h / 2, r * .95, w / 2, h / 2, r * 1.35); halo.addColorStop(0, "rgba(120,100,255,.45)"); halo.addColorStop(1, "rgba(120,100,255,0)");
    ctx.fillStyle = halo; ctx.beginPath(); ctx.arc(w / 2, h / 2, r * 1.35, 0, 7); ctx.fill();
    const g = ctx.createRadialGradient(w / 2 - r * .35, h / 2 - r * .4, r * .1, w / 2, h / 2, r);
    g.addColorStop(0, light ? "#dfe6ff" : "#1b2260"); g.addColorStop(1, light ? "#b9c4f5" : "#070a22");
    ctx.beginPath(); path({ type: "Sphere" }); ctx.fillStyle = g; ctx.fill();
    ctx.beginPath(); path(d3.geoGraticule10()); ctx.strokeStyle = light ? "rgba(90,80,200,.14)" : "rgba(140,150,255,.12)"; ctx.lineWidth = .6; ctx.stroke();
    for (const f of W.features) {
      const has = W.est && W.est[f.id]; ctx.beginPath(); path(f.geometry);
      ctx.fillStyle = has ? color(norm(f.id)) : (light ? "rgba(120,110,190,.22)" : "rgba(150,160,230,.16)");
      if (has) ctx.globalAlpha = (W.selected === f.id || W.hover === f.id) ? 1 : .8; ctx.fill(); ctx.globalAlpha = 1;
      ctx.strokeStyle = W.selected === f.id ? "#fff" : "rgba(255,255,255,.22)"; ctx.lineWidth = W.selected === f.id ? 2 : .5; ctx.stroke();
    }
    ctx.beginPath(); path({ type: "Sphere" }); ctx.strokeStyle = "rgba(160,150,255,.5)"; ctx.lineWidth = 1.5; ctx.stroke();
    const center = [-W.rot[0], -W.rot[1]];
    for (const c of W.data.countries) {
      if (d3.geoDistance(center, [c.lon, c.lat]) > Math.PI / 2 - .05) continue;
      const [x, y] = proj([c.lon, c.lat]), sel = W.selected === c.id, t = performance.now() / 600;
      ctx.beginPath(); ctx.arc(x, y, sel ? 6 : 3.5, 0, 7); ctx.fillStyle = sel ? "#fff" : "#52f0ff"; ctx.shadowColor = "#52f0ff"; ctx.shadowBlur = 12; ctx.fill(); ctx.shadowBlur = 0;
      if (sel || W.hover === c.id) { ctx.beginPath(); ctx.arc(x, y, 8 + 4 * Math.sin(t), 0, 7); ctx.strokeStyle = "rgba(255,255,255,.7)"; ctx.lineWidth = 1.5; ctx.stroke(); }
    }
    if (W.selected && W.byId[W.selected]) { // arc from India
      const a = W.byId["356"], b = W.byId[W.selected];
      if (a !== b) { const ip = d3.geoInterpolate([a.lon, a.lat], [b.lon, b.lat]); ctx.beginPath(); path({ type: "LineString", coordinates: d3.range(0, 1.01, .02).map(ip) }); ctx.strokeStyle = "#ff5fd2"; ctx.lineWidth = 2; ctx.setLineDash([6, 5]); ctx.lineDashOffset = -performance.now() / 40; ctx.stroke(); ctx.setLineDash([]); }
    }
  }
  function loop() {
    if (!dragging) { W.rot[0] += vel[0]; W.rot[1] = Math.max(-80, Math.min(80, W.rot[1] + vel[1])); vel[0] *= .94; vel[1] *= .94; if (W.auto && !W.selected && !W.hover) W.rot[0] += .12; }
    if (W.active) draw(); raf = requestAnimationFrame(loop);
  }
  function flyTo(c) { const from = W.rot.slice(), to = [-c.lon, -c.lat * .8, 0], t0 = performance.now(); W.auto = false; vel = [0, 0];
    (function s(n) { const p = Math.min(1, (n - t0) / 1000), e = 1 - Math.pow(1 - p, 3); let d = to[0] - from[0]; d = ((d + 540) % 360) - 180;
      W.rot = [from[0] + d * e, from[1] + (to[1] - from[1]) * e, 0]; if (p < 1) requestAnimationFrame(s); })(t0); }
  function pick(ev) {
    const r = cv.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top, center = [-W.rot[0], -W.rot[1]];
    let best = null, bd = 16; for (const c of W.data.countries) { if (d3.geoDistance(center, [c.lon, c.lat]) > Math.PI / 2) continue; const [px, py] = proj([c.lon, c.lat]), d = Math.hypot(px - x, py - y); if (d < bd) { bd = d; best = c.id; } }
    if (best) return best; const ll = proj.invert([x, y]); if (!ll || d3.geoDistance(center, ll) > Math.PI / 2) return null;
    const f = W.features.find(f => W.byId[f.id] && d3.geoContains(f.geometry, ll)); return f ? f.id : null;
  }
  function bindGlobe() {
    const stage = cv.parentElement, tip = $("#globeTip");
    stage.addEventListener("pointerdown", e => { dragging = true; last = [e.clientX, e.clientY]; W.moved = 0; stage.classList.add("drag"); stage.setPointerCapture(e.pointerId); });
    stage.addEventListener("pointermove", e => {
      if (dragging) { const dx = e.clientX - last[0], dy = e.clientY - last[1]; W.moved += Math.abs(dx) + Math.abs(dy); const k = .3 / W.zoom; W.rot[0] += dx * k; W.rot[1] = Math.max(-80, Math.min(80, W.rot[1] - dy * k)); vel = [dx * k, -dy * k]; last = [e.clientX, e.clientY]; return; }
      const id = pick(e); W.hover = id; const r = stage.getBoundingClientRect();
      if (id) { const c = W.byId[id], v = W.est[id]; tip.innerHTML = `${flag(c.iso2)} <b>${c.name}</b> · ${inr(v.gross_inr)}`; tip.style.left = e.clientX - r.left + "px"; tip.style.top = e.clientY - r.top + "px"; tip.style.opacity = 1; } else tip.style.opacity = 0;
    });
    stage.addEventListener("pointerup", e => { dragging = false; stage.classList.remove("drag"); if (W.moved < 5) { const id = pick(e); if (id) select(id); } });
    stage.addEventListener("pointerleave", () => { W.hover = null; $("#globeTip").style.opacity = 0; });
    stage.addEventListener("wheel", e => { e.preventDefault(); W.zoom = Math.max(.6, Math.min(2.4, W.zoom * (e.deltaY < 0 ? 1.08 : .92))); }, { passive: false });
    window.addEventListener("resize", () => W.active && resize());
  }

  /* ---------- panels ---------- */
  function countUp(el, to, f) { const t0 = performance.now(); (function s(n) { const p = Math.min(1, (n - t0) / 700); el.textContent = f(to * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(s); })(t0); }
  function select(id, fly = true) {
    W.selected = id; const c = W.byId[id], e = W.est[id]; if (fly) flyTo(c);
    const have = new Set((W.skills || []).map(s => s.toLowerCase()));
    const span = c.high * 1.2 - c.low * .85, pos = Math.max(2, Math.min(98, (e.gross_local - c.low * .85) / span * 100));
    const m = x => (x - c.low * .85) / span * 100;
    $("#countryPanel").innerHTML = `<div class="cp-head"><span class="cp-flag">${flag(c.iso2)}</span><div><h2 style="margin:0">${c.name}</h2><div class="cp-sub">${c.currency} · entry-level tech benchmark</div></div></div>
    <div><div class="cp-sub">YOUR ESTIMATED BASE PRICE (per year, gross)</div><div class="cp-price" id="cpPrice">—</div><div class="cp-sub">${fmt(e.gross_local, c.currency)} · typical for this country ${fmt(c.typical, c.currency)}</div></div>
    <div class="range"><i style="left:${pos}%"></i><span style="left:${m(c.low)}%">low</span><span style="left:${m(c.typical)}%">typical</span><span style="left:${m(c.high)}%">high</span></div>
    <div class="mini-grid"><div><small>After tax</small><b>${inr(e.net_inr)}</b></div><div><small>Living / yr</small><b>${inr(e.living_inr_year)}</b></div><div><small>Left over</small><b style="color:${e.savings_inr < 0 ? "var(--danger)" : "var(--green)"}">${inr(e.savings_inr)}</b></div></div>
    <div><b>Visa route</b> <span class="ease" title="Ease of getting work authorisation">${[1, 2, 3, 4, 5].map(i => `<i class="${i <= c.ease ? "on" : ""}"></i>`).join("")}</span><p class="cp-sub" style="margin:4px 0">${escapeHtml(c.visa)}</p></div>
    <div class="cp-sub">Market demand: <b>${c.demand}</b> · Language: ${escapeHtml(c.language)}</div>
    <div><b>In-demand skills</b> <span class="cp-sub">(green = you have it)</span><div class="chips" style="margin-top:6px">${c.skills.map(s => `<span class="chip ${have.has(s.toLowerCase()) ? "have" : ""}">${have.has(s.toLowerCase()) ? "✓ " : ""}${escapeHtml(s)}</span>`).join("")}</div></div>
    <div><b>What to look out for</b><ul class="watch">${c.watch.map(w => `<li>${escapeHtml(w)}</li>`).join("")}</ul></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="pill-btn" id="cmpAdd">＋ Compare</button></div>
    <p class="cp-sub">${c.verified ? `<span class="badge ok">✔ ${escapeHtml(c.verified)}</span>` : `<span class="badge warn">Unverified estimate: confirm before relying on it</span>`} ${c.official ? `<a href="${c.official}" target="_blank" rel="noopener">Official site ↗</a>` : ""}</p>
    <p class="cp-sub">Indicative benchmark scaled to your resume percentile (${W.pct}th). Not a guarantee; verify on official sources.</p>`;
    countUp($("#cpPrice"), e.gross_inr, v => inr(v)); $("#cmpAdd").onclick = () => { if (!W.compare.includes(id)) W.compare = [...W.compare, id].slice(-3); renderCompare(); };
    renderRank();
  }
  function renderRank() {
    computeFit(); const ids = Object.keys(W.est).sort((a, b) => W.fit[b] - W.fit[a]).slice(0, 10);
    $("#rankList").innerHTML = ids.map((id, i) => { const c = W.byId[id]; return `<div class="rank-row" tabindex="0" role="button" aria-label="Select ${c.name}" data-id="${id}"><b style="width:20px">${i + 1}</b><span>${flag(c.iso2)} ${c.name}</span><div class="bar"><i style="width:${W.fit[id] * 100}%"></i></div><small>${inr(W.est[id].gross_inr)}</small></div>`; }).join("");
    $$("#rankList .rank-row").forEach(r => { r.onclick = () => select(r.dataset.id); r.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(r.dataset.id); } }; });
  }
  function renderCompare() {
    const el = $("#cmpBody"); if (!W.compare.length) { el.innerHTML = `<p class="cp-sub">Select a country and press “＋ Compare” (up to 3).</p>`; return; }
    const rows = [["Base price", i => inr(W.est[i].gross_inr)], ["After tax", i => inr(W.est[i].net_inr)], ["Left over / yr", i => inr(W.est[i].savings_inr)], ["Visa ease (1-5)", i => W.byId[i].ease], ["Demand", i => W.byId[i].demand]];
    el.innerHTML = `<table class="cmp-table"><tr><th></th>${W.compare.map(i => `<th>${flag(W.byId[i].iso2)} ${W.byId[i].iso2}</th>`).join("")}</tr>${rows.map(([n, f]) => `<tr><td>${n}</td>${W.compare.map(i => `<td>${f(i)}</td>`).join("")}</tr>`).join("")}</table><button class="pill-btn" id="cmpClear" style="margin-top:8px">Clear</button>`;
    $("#cmpClear").onclick = () => { W.compare = []; renderCompare(); };
  }
  const SL = [["cgpa", "CGPA", 0, 10, .1], ["major_projects", "Major projects", 0, 6, 1], ["mini_projects", "Mini projects", 0, 6, 1], ["workshops", "Certifications", 0, 8, 1], ["skills_count", "Skills", 0, 15, 1], ["communication", "Communication", 0, 5, .1], ["backlogs", "Backlogs", 0, 10, 1]];
  function renderWhatIf() {
    const p = W.profile; $("#whatIf").innerHTML = SL.map(([k, l, lo, hi, st]) => `<div class="slider-row"><span>${l}</span><input type="range" min="${lo}" max="${hi}" step="${st}" value="${p[k] ?? DEFAULT_PROFILE[k]}" data-k="${k}"><b>${p[k] ?? DEFAULT_PROFILE[k]}</b></div>`).join("") +
      ["internship", "hackathon"].map(k => `<label class="slider-row"><span style="text-transform:capitalize">${k}</span><input type="checkbox" data-k="${k}" ${p[k] === "Yes" ? "checked" : ""}><span></span></label>`).join("") + `<div id="wiOut" class="cp-sub" style="margin-top:8px"></div>`;
    $$("#whatIf input").forEach(i => i.oninput = () => { const k = i.dataset.k; W.profile[k] = i.type === "checkbox" ? (i.checked ? "Yes" : "No") : Number(i.value); if (i.type !== "checkbox") i.nextElementSibling.textContent = i.value; clearTimeout(W.timer); W.timer = setTimeout(refresh, 180); });
  }
  async function refresh() {
    W.ctrl?.abort(); W.ctrl = new AbortController();
    try {
      const r = await api("/api/world/estimate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile: W.profile }), signal: W.ctrl.signal });
      W.est = r.estimates; W.pct = r.percentile; W.skills = r.skills?.length ? r.skills : (W.profile.skills || []); computeFit();
      const o = $("#wiOut"); if (o) o.innerHTML = `Placement chance <b>${r.prediction.probability.toFixed(1)}%</b> · salary in India <b>${inr(r.prediction.salary)}</b> · resume percentile <b>${r.percentile}th</b>`;
      $("#worldWho").textContent = W.profile.name || "Typical student"; renderRank(); if (W.selected) select(W.selected, false);
    } catch (e) { if (e.name !== "AbortError") toast(e.message, "error"); }
  }
  async function loadMap() {
    try { const t = await (await fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json")).json(); W.features = topo(t); W.mapOK = true; $("#globeNote").textContent = "Drag to rotate · scroll to zoom · click a country or glowing pin"; }
    catch { $("#globeNote").textContent = "Map outlines could not load (offline?). Pins still work: click a glowing pin."; }
  }
  window.worldOpen = async function () {
    W.active = true;
    if (!W.inited) {
      W.inited = true; W.data = await api("/api/countries"); W.byId = Object.fromEntries(W.data.countries.map(c => [c.id, c]));
      $("#worldDisclaimer").textContent = W.data.disclaimer + " Pay data: " + W.data.as_of + ". FX: " + W.data.fx_as_of + ".";
      cv = $("#globeCanvas"); ctx = cv.getContext("2d"); proj = d3.geoOrthographic().clipAngle(90).precision(.6); resize(); bindGlobe(); loadMap();
      $("#metricSel").onchange = e => W.metric = e.target.value; $("#autoRot").onclick = e => { W.auto = !W.auto; e.target.classList.toggle("on", W.auto); };
      $$("#weights input").forEach(i => i.oninput = () => { W.weights[i.dataset.w] = Number(i.value); if (W.metric === "fit") {} renderRank(); });
      $("#countryList").innerHTML = W.data.countries.map(c => `<option value="${c.name}">`).join("");
      $("#countrySearch").onchange = e => { const c = W.data.countries.find(x => x.name.toLowerCase() === e.target.value.trim().toLowerCase()); if (c) { select(c.id); e.target.blur(); } else toast("Country not in the list. Try e.g. Germany.", "error"); };
      renderCompare(); loop();
    }
    W.profile = { ...DEFAULT_PROFILE, ...(state.lastResult?.profile || {}) };
    if (!state.lastResult) { try { const h = await api("/api/history?limit=1"); if (h[0]) W.profile = { ...DEFAULT_PROFILE, ...h[0].profile }; } catch {} }
    $("#worldBanner").classList.toggle("hidden", Boolean(state.lastResult || W.profile.name !== "Typical student"));
    ["cgpa", "communication", "skills_count"].forEach(k => { if (W.profile[k] == null) W.profile[k] = DEFAULT_PROFILE[k]; });
    renderWhatIf(); await refresh(); resize();
  };
  window.worldSetActive = v => { W.active = v; };
})();
