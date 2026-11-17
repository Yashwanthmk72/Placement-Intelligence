/* Visual effects: intro splash, starfield, cursor spotlight, confetti */
(function () {
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduce) { const s = document.createElement("div"); s.id = "intro"; s.innerHTML = "<i></i><b>PLACEMENT INTELLIGENCE</b>"; document.body.append(s); setTimeout(() => s.remove(), 1700); }
  const cv = document.getElementById("starfield"), c = cv.getContext("2d"); let st = [], mx = 0, my = 0;
  function init() { cv.width = innerWidth; cv.height = innerHeight; st = Array.from({ length: 90 }, () => ({ x: Math.random() * cv.width, y: Math.random() * cv.height, z: Math.random() * .8 + .2, p: Math.random() * 6 })); }
  init(); addEventListener("resize", init);
  addEventListener("pointermove", e => { mx = e.clientX / innerWidth - .5; my = e.clientY / innerHeight - .5; const t = e.target.closest?.(".panel,.stat-card"); if (t) { const r = t.getBoundingClientRect(); t.style.setProperty("--mx", e.clientX - r.left + "px"); t.style.setProperty("--my", e.clientY - r.top + "px"); } });
  (function f(t) { c.clearRect(0, 0, cv.width, cv.height); const light = document.documentElement.dataset.theme === "light";
    for (const s of st) { const a = (.3 + .5 * Math.sin(t / 900 + s.p)) * s.z; c.fillStyle = light ? `rgba(110,90,220,${a * .5})` : `rgba(200,210,255,${a})`; c.beginPath(); c.arc(s.x - mx * 30 * s.z, s.y - my * 30 * s.z, s.z * 1.4, 0, 7); c.fill(); }
    if (!reduce) requestAnimationFrame(f); })(0);
  window.confetti = function () { if (reduce) return; const cols = ["#8b5cf6", "#22d3ee", "#ff5fd2", "#5df0b0", "#fbbf24"];
    for (let i = 0; i < 70; i++) { const e = document.createElement("i"); e.className = "confetti"; e.style.left = Math.random() * 100 + "vw"; e.style.background = cols[i % 5]; e.style.setProperty("--dx", (Math.random() * 200 - 100) + "px"); e.style.animationDelay = Math.random() * .5 + "s"; document.body.append(e); setTimeout(() => e.remove(), 3200); } };
})();
