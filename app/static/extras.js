/* ATS check + shareable result card */
(function () {
  const sel = $("#atsRole");
  api("/api/ats/roles").then(r => sel.innerHTML = r.map(x => `<option>${escapeHtml(x)}</option>`).join("")).catch(() => {});
  $("#atsRun").onclick = async () => {
    const btn = $("#atsRun"); btn.disabled = true;
    try {
      const skills = (document.getElementById("skillsText")?.value || "").split(",").map(s => s.trim()).filter(Boolean);
      const r = await api("/api/ats", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ role: sel.value, text: state.resumeText || "", skills }) });
      $("#atsOut").innerHTML = `<div class="ats-score"><div class="ats-ring" style="--p:${r.score}%"><b>${r.score}</b><small>/100</small></div><div><h3>${escapeHtml(r.role)} match</h3><p class="cp-sub">${state.resumeText ? "Based on your uploaded resume text." : "Based on your skills only. Upload a resume for a full check."}</p></div></div>
      <h3>Keywords found</h3><div class="chips">${r.matched.map(k => `<span class="chip have">✓ ${escapeHtml(k)}</span>`).join("") || "<span class='cp-sub'>None yet</span>"}</div>
      <h3>Keywords missing</h3><div class="chips">${r.missing.map(k => `<span class="chip">${escapeHtml(k)}</span>`).join("")}</div>
      <h3>Structure checks</h3><ul class="watch">${r.checks.map(c => `<li>${c.ok ? "✅" : "⚠️"} ${escapeHtml(c.name)}</li>`).join("")}</ul>
      <h3>Fix these first</h3><ul class="watch">${r.tips.map(t => `<li>${escapeHtml(t)}</li>`).join("") || "<li>Looks solid. Keep it tailored to each job.</li>"}</ul>`;
    } catch (e) { toast(e.message, "error"); } finally { btn.disabled = false; }
  };
  async function card() {
    let p = state.lastResult?.profile, res = state.lastResult?.result;
    if (!p) { try { const h = await api("/api/history?limit=1"); if (h[0]) { p = h[0].profile; res = h[0]; } } catch {} }
    if (!p) return toast("Run an analysis first, then download your card.", "error");
    const w = await api("/api/world/estimate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile: p }) });
    const cs = (await api("/api/countries")).countries, top = Object.entries(w.estimates).sort((a, b) => b[1].gross_inr - a[1].gross_inr).slice(0, 3).map(([id, e]) => [cs.find(c => c.id === id), e]);
    const cv = document.createElement("canvas"); cv.width = 1200; cv.height = 630; const c = cv.getContext("2d");
    const g = c.createLinearGradient(0, 0, 1200, 630); g.addColorStop(0, "#0a0d22"); g.addColorStop(.5, "#1a1050"); g.addColorStop(1, "#0b2a3d"); c.fillStyle = g; c.fillRect(0, 0, 1200, 630);
    [[160, 120, "#8b5cf6"], [1040, 520, "#ff5fd2"], [900, 90, "#22d3ee"]].forEach(([x, y, col]) => { const r = c.createRadialGradient(x, y, 0, x, y, 320); r.addColorStop(0, col + "66"); r.addColorStop(1, "transparent"); c.fillStyle = r; c.fillRect(0, 0, 1200, 630); });
    c.fillStyle = "#fff"; c.font = "700 54px Space Grotesk, Inter, sans-serif"; c.fillText(p.name || "Candidate", 70, 120);
    c.fillStyle = "#9db0ff"; c.font = "500 24px JetBrains Mono, monospace"; c.fillText("PLACEMENT INTELLIGENCE · RESUME CARD", 70, 168);
    const stats = [["Placement chance", w.prediction.probability.toFixed(1) + "%"], ["India salary est.", "₹" + (w.prediction.salary / 1e5).toFixed(1) + " L"], ["Resume score", w.resume_score + "/100"]];
    stats.forEach(([k, v], i) => { const x = 70 + i * 370; c.fillStyle = "rgba(255,255,255,.08)"; c.beginPath(); c.roundRect(x, 210, 340, 130, 22); c.fill(); c.strokeStyle = "#8b5cf6"; c.stroke(); c.fillStyle = "#c9d2ff"; c.font = "500 22px Inter, sans-serif"; c.fillText(k, x + 24, 252); c.fillStyle = "#fff"; c.font = "800 50px Sora, Inter, sans-serif"; c.fillText(v, x + 24, 316); });
    c.fillStyle = "#22d3ee"; c.font = "700 26px Space Grotesk, sans-serif"; c.fillText("Top countries for my resume (estimates)", 70, 400);
    top.forEach(([co, e], i) => { c.fillStyle = "#fff"; c.font = "600 34px Space Grotesk, sans-serif"; c.fillText(`${i + 1}. ${co.name}`, 70, 458 + i * 52); c.fillStyle = "#ff9be6"; c.font = "700 34px Sora, sans-serif"; c.fillText("₹" + (e.gross_inr / 1e5).toFixed(1) + " L / yr", 560, 458 + i * 52); });
    c.fillStyle = "#8a96c9"; c.font = "400 18px Inter, sans-serif"; c.fillText("Indicative estimates, not guarantees. Verify visa and pay on official sources.", 70, 604);
    const a = document.createElement("a"); a.download = "placement-card.png"; a.href = cv.toDataURL("image/png"); a.click(); toast("Result card downloaded.", "success");
  }
  ["#cardBtn", "#cardBtn2"].forEach(s => $(s).addEventListener("click", () => card().catch(e => toast(e.message, "error"))));
})();
