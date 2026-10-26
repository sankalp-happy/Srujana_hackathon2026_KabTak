// Kab Tak? UI. Every number shown comes from the engine result; this file only formats and draws.
const $ = (s) => document.querySelector(s);
const LAKH = 1e5;
const SVGNS = "http://www.w3.org/2000/svg";
const SERIES = ["#1f5fa8", "#7a4fb5", "#0f7c7c", "#9a5a00"];
const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
let R = null; // current result
let SOURCE = "";
let step = 0; // story step

/* ---------- formatting ---------- */
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
function inr(n) {
  if (n == null) return "–";
  const sign = n < 0 ? "−" : "";
  const a = Math.abs(n);
  if (a >= LAKH) return `${sign}₹${(a / LAKH).toFixed(a >= 10 * LAKH ? 0 : 1).replace(/\.0$/, "")} L`;
  return `${sign}₹${Math.round(a).toLocaleString("en-IN")}`;
}
const signed = (n) => (n > 0 ? "+" : "") + inr(n);
const pct = (p) => `${Math.round(p * 100)}%`;
const toDate = (iso) => new Date(`${iso}T00:00:00`);
const day = (iso, lang = "en-IN") => toDate(iso).toLocaleDateString(lang, { day: "numeric", month: "short" });
const fullDay = (iso) => toDate(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
const addDays = (iso, n) => { const d = toDate(iso); d.setDate(d.getDate() + n); return d; };
const has = (v) => Array.isArray(v) ? v.length > 0 : v != null;

// Three checks against the result's own risk target; "likely short" means more likely than not.
function level(p) {
  if (p <= R.risk_target) return { k: "ok", label: "OK" };
  if (p < 0.5) return { k: "watch", label: "At risk" };
  return { k: "ng", label: "Likely short" };
}
const stamp = (p) => { const l = level(p); return `<span class="stamp s-${l.k}">${l.label}</span>`; };
const fixById = (id) => (R.fixes || []).find((f) => f.id === id);
const how = (t) => `<p class="how">${t}</p>`;

/* ---------- header ---------- */
const TYPE_TEXT = {
  status: () => "Status check",
  new_order: (s) => `New order from ${s.party} · ${inr(s.amount_inr)} on ${s.days}-day terms`,
  delay_payment: (s) => `${s.party} pays ${s.days} days late`,
  expense_shock: (s) => `Sudden expense of ${inr(s.amount_inr)} on ${s.date ? day(s.date) : "–"}`,
  sales_drop: (s) => `Sales fall ${s.pct}% for ${s.days} days`,
  supplier_terms: (s) => `${s.party} wants payment in ${s.days} days`,
  schedule_change: (s) => `Move ${s.obligation} to ${s.date ? day(s.date) : "–"}`,
  payment_received: (s) => `${s.party} paid ${inr(s.amount_inr)}`,
};
const scenarioText = (s = R.scenario || { type: "status" }) => (TYPE_TEXT[s.type] || (() => s.type))(s);
function renderHeader() {
  const s = R.scenario || { type: "status" };
  $("#asked").innerHTML = (s.transcript ? `<q lang="mr">${esc(s.transcript)}</q> · ` : "") + esc(scenarioText(s));
  const bits = [`As of ${fullDay(R.as_of)}`, `${pct(R.risk_target)} risk limit`];
  if (R.placeholder) bits.push("placeholder numbers");
  bits.push(SOURCE);
  $("#meta").textContent = bits.join(" · ");
}

/* ---------- verdict (owner view, also on top of CA view) ---------- */
function orderAnswer(o) {
  if (o.max_safe_terms_days >= o.terms_days) return `Safe to take on ${o.terms_days}-day terms.`;
  if (o.max_safe_terms_days > 0) return `Take it at up to ${o.max_safe_terms_days} days, or ask for a ${o.min_advance_pct}% advance.`;
  return `Terms alone don't make it safe; ask for a ${o.min_advance_pct}% advance.`;
}
function renderVerdict() {
  const w = R.worst_week, l = level(w.p_shortfall), n = R.fan.dates.length;
  const wk = day(w.week_start), wkMr = day(w.week_start, "mr-IN-u-nu-latn"), p = pct(w.p_shortfall);
  const head = { ok: `Safe for the next ${n} days`, watch: `Week of ${wk} is at risk`, ng: `Week of ${wk} will likely fall short` }[l.k];
  const why = l.k === "ok"
    ? `Hardest week starts ${wk}: ${p} chance of a shortfall, inside the ${pct(R.risk_target)} limit.`
    : `${p} chance you can't pay ${esc(w.obligation)}.`;
  const mr = {
    ok: `पुढचे ${n} दिवस सुरक्षित आहेत. सर्वात कठीण आठवडा ${wkMr}: ${p} धोका.`,
    watch: `${wkMr} च्या आठवड्यात पैसे कमी पडण्याची शक्यता ${p} आहे.`,
    ng: `${wkMr} च्या आठवड्यात पैसे कमी पडण्याची शक्यता जास्त आहे: ${p}.`,
  }[l.k];

  let action;
  const plan = R.plan, first = plan && plan.fix_ids.length ? fixById(plan.fix_ids[0]) : null;
  if (plan) {
    const label = esc(first ? first.label : plan.fix_ids[0]);
    action = `<p class="lead">Do this first: <b>${label}</b>${first ? ` <span class="muted">· costs ${inr(first.cost_inr)}</span>` : ""}</p>
      <p class="muted">Full plan: ${plan.fix_ids.length} ${plan.fix_ids.length === 1 ? "fix" : "fixes"} for ${inr(plan.total_cost_inr)} takes the risk from ${pct(plan.p_shortfall_before)} to ${pct(plan.p_shortfall_after)} ${stamp(plan.p_shortfall_after)}</p>
      <p lang="mr" class="hi" style="font-size:17px;margin:0">पहिली पायरी: ${label}</p>`;
  } else if (l.k === "ok") {
    action = `<p class="lead"><b>No fixes needed.</b></p>`;
  } else {
    action = `<p class="lead"><b>No fixes available.</b> <span class="muted">The engine found nothing that lowers this risk.</span></p>`;
  }
  if (R.order) action += `<p><b>This order:</b> ${esc(orderAnswer(R.order))}</p>`;

  $("#verdict").innerHTML = `
    <div class="big strike s-${l.k}" style="background:none">${l.label}<small>worst week · ${p}</small></div>
    <div>
      <h2 id="verdict-h">${head}</h2>
      <p class="sub" style="margin:6px 0 0;font-size:17px;color:var(--ink)">${why}</p>
      <p class="hi" lang="mr">${mr}</p>
      <div class="action">${action}</div>
    </div>`;
}

/* ---------- today ---------- */
function bar(parts, total, fmt = inr) {
  return `<div class="track" role="img" aria-label="${esc(parts.map((p) => `${p.label} ${fmt(p.v)}`).join(", "))}">${parts
    .map((p) => `<i style="width:${(Math.max(0, p.v) / total) * 100}%;background:${p.c}"></i>`).join("")}</div>
    <div class="legend">${parts.map((p) => `<span style="--c:${p.c}">${p.label} ${fmt(p.v)}</span>`).join("")}</div>`;
}
function todayHTML() {
  const t = R.today;
  return `
    <dl class="today">
      <div><dt>Bank balance</dt><dd>${inr(t.bank_inr)}</dd></div>
      <div><dt>Undrawn overdraft headroom</dt><dd>${inr(t.headroom_inr)}</dd></div>
      <div><dt>Owed to you</dt><dd>${inr(t.receivable_inr)}</dd></div>
      <div><dt>Overdue more than 45 days</dt><dd class="${t.overdue_45_inr > 0 ? "bad" : ""}">${inr(t.overdue_45_inr)}</dd></div>
    </dl>
    <div class="gauges">
      <div class="gauge"><p>Overdraft limit ${inr(t.od_limit_inr)}</p>${bar([
        { label: "Drawn", v: t.od_drawn_inr, c: "var(--shell)" },
        { label: "Headroom", v: t.headroom_inr, c: "var(--band-deep)" },
        { label: "Blocked by drawing power", v: t.od_limit_inr - t.drawing_power_inr, c: "#dfe5ec" },
      ], t.od_limit_inr)}</div>
      <div class="gauge"><p>Receivables ${inr(t.receivable_inr)}</p>${bar([
        { label: "Overdue >45 days", v: t.overdue_45_inr, c: "var(--ng)" },
        { label: "Not yet overdue", v: t.receivable_inr - t.overdue_45_inr, c: "var(--band-deep)" },
      ], t.receivable_inr)}</div>
    </div>
    ${how("The left bar is the overdraft: what you've drawn, what you can still draw, and what the bank won't lend because old invoices don't count. The right bar is money buyers owe you; red is more than 45 days late.")}`;
}

/* ---------- svg helpers ---------- */
function niceStep(range, count) {
  const raw = range / count, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  return [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw);
}
function el(name, attrs, parent) {
  const e = document.createElementNS(SVGNS, name);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}
function txt(parent, x, y, text, attrs = {}) { const t = el("text", { x, y, ...attrs }, parent); t.textContent = text; return t; }
const line = (pts) => "M" + pts.map(([x, y]) => `${x},${y}`).join(" L");
function obligationsBetween(startIso, days) {
  const a = toDate(startIso), b = addDays(startIso, days);
  return R.obligations.filter((o) => { const d = toDate(o.date); return d >= a && d < b; });
}
function stopTimers(box) { (box._timers || []).forEach(clearTimeout); box._timers = []; }

/* ---------- fan chart ---------- */
// o.baseline: grey "before" fan underneath; o.paths: sample futures; o.animate: draw them one by one
function drawFan(box, o = {}) {
  stopTimers(box);
  const f = R.fan, n = f.dates.length, w = R.worst_week, id = box.id;
  const base = o.baseline && R.baseline && R.baseline.fan;
  const paths = o.paths && has(R.sample_paths) ? R.sample_paths : null;
  const W = Math.max(260, box.clientWidth), H = Math.round(Math.min(o.tall ? 440 : 380, Math.max(260, W * 0.42)));
  const m = { l: W < 500 ? 46 : 62, r: 12, t: 34, b: 52 };
  const vals = [0, ...f.p10, ...f.p90, ...(base ? [...base.p10, ...base.p90] : []), ...(paths ? paths.flatMap((p) => p.values) : [])];
  const lo = Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo) * 0.08;
  const stp = niceStep(hi - lo + 2 * pad, W < 500 ? 4 : 5);
  const y0 = Math.floor((lo - pad) / stp) * stp, y1 = Math.ceil((hi + pad) / stp) * stp;
  const X = (i) => m.l + (i * (W - m.l - m.r)) / (n - 1);
  const Y = (v) => m.t + ((y1 - v) * (H - m.t - m.b)) / (y1 - y0);
  const bottom = H - m.b;

  box.innerHTML = "";
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img", tabindex: 0,
    "aria-label": `Fan chart over ${n} days. Middle outcome ends at ${inr(f.p50[n - 1])}. Worst week starts ${day(w.week_start)} with a ${pct(w.p_shortfall)} chance of a shortfall.${base ? ` Before this change the worst-week risk was ${pct(R.baseline.p_shortfall)}.` : ""} Use left and right arrow keys to read each day.` }, box);
  const hatch = el("pattern", { id: `hatch-${id}`, width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" }, el("defs", {}, svg));
  el("rect", { width: 6, height: 6, fill: "#fde8e6" }, hatch);
  el("line", { x1: 0, y1: 0, x2: 0, y2: 6, stroke: "#e8a29b", "stroke-width": 2 }, hatch);

  for (let v = y0; v <= y1 + 1e-6; v += stp) {
    el("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), stroke: "#e3e9ef" }, svg);
    txt(svg, m.l - 8, Y(v) + 4, inr(v), { "text-anchor": "end" });
  }
  el("rect", { x: m.l, y: Y(0), width: W - m.l - m.r, height: Math.max(0, bottom - Y(0)), fill: "#fdf0ee" }, svg);

  const wi = f.dates.indexOf(w.week_start);
  if (wi >= 0) {
    const x0 = X(wi), x1 = X(Math.min(n - 1, wi + 7));
    el("rect", { x: x0, y: m.t, width: x1 - x0, height: bottom - m.t, fill: `url(#hatch-${id})`, opacity: 0.9 }, svg);
    const t = txt(svg, x0, m.t - 10, `Worst week · ${pct(w.p_shortfall)} chance short`, { style: "fill:var(--ng);font-weight:600;font-size:13px" });
    if (x0 + t.getComputedTextLength() > W - m.r) { t.setAttribute("x", Math.max(m.l, x1)); t.setAttribute("text-anchor", "end"); }
  }

  const area = (lo_, hi_) => "M" + hi_.map((v, i) => `${X(i)},${Y(v)}`).join(" L") + " L" + lo_.map((v, i) => `${X(i)},${Y(v)}`).reverse().join(" L") + "Z";
  if (base) {
    el("path", { d: area(base.p10, base.p90), fill: "#e1e6ec", stroke: "#b6c1cc", "stroke-width": 1 }, svg);
    el("path", { d: line(base.p50.map((v, i) => [X(i), Y(v)])), fill: "none", stroke: "#7d8a98", "stroke-width": 2, "stroke-dasharray": "5 4" }, svg);
  }
  const g = el("g", { class: "band" }, svg);
  el("path", { d: area(f.p10, f.p90), fill: "#c4d8ef", "fill-opacity": paths ? 0.55 : base ? 0.75 : 0.85, stroke: "#8fb4de", "stroke-width": 1 }, g);

  // sample futures, drawn in one at a time
  if (paths) {
    const pg = el("g", {}, svg);
    const order = paths.map((p, k) => k);
    let shown = 0;
    const add = (k) => {
      const p = paths[k];
      const e = el("path", { d: line(p.values.map((v, i) => [X(i), Y(v)])), fill: "none", stroke: p.short ? "#8f1d14" : "#6f93bd",
        "stroke-width": p.short ? 1.6 : 1.1, "stroke-opacity": p.short ? 0.9 : 0.55, "stroke-linejoin": "round" }, pg);
      if (o.animate && !REDUCED) {
        const len = e.getTotalLength();
        e.style.strokeDasharray = len; e.style.strokeDashoffset = len;
        e.getBoundingClientRect();
        e.style.transition = "stroke-dashoffset .7s cubic-bezier(.16,1,.3,1)";
        e.style.strokeDashoffset = 0;
      }
      shown++;
      if (o.onProgress) o.onProgress(shown, paths.length);
    };
    if (o.animate && !REDUCED) order.forEach((k, j) => box._timers.push(setTimeout(() => add(k), 160 * j)));
    else order.forEach(add);
  }
  el("path", { d: line(f.p50.map((v, i) => [X(i), Y(v)])), fill: "none", stroke: "#1f5fa8", "stroke-width": 2.25, "stroke-linejoin": "round" }, svg);

  el("line", { x1: m.l, x2: W - m.r, y1: Y(0), y2: Y(0), stroke: "#b42318", "stroke-width": 1.5, "stroke-dasharray": "6 4" }, svg);
  txt(svg, W - m.r - 4, Y(0) + 16, "₹0 · can't pay below this", { "text-anchor": "end", style: "fill:var(--ng);font-weight:600;font-size:12.5px" });

  el("line", { x1: m.l, x2: W - m.r, y1: bottom, y2: bottom, stroke: "#9fb0c1" }, svg);
  let lastLabel = -Infinity;
  f.dates.forEach((d, i) => {
    const dt = toDate(d);
    if (dt.getDay() === 1) el("line", { x1: X(i), x2: X(i), y1: bottom, y2: bottom + 4, stroke: "#9fb0c1" }, svg);
    if ((dt.getDate() === 1 || i === 0) && X(i) - lastLabel > 48) {
      lastLabel = X(i);
      el("line", { x1: X(i), x2: X(i), y1: bottom, y2: bottom + 8, stroke: "#4a5d70" }, svg);
      txt(svg, X(i), bottom + 22, day(d), { "text-anchor": i === 0 ? "start" : "middle", style: "font-weight:600" });
    }
  });

  const byDate = {};
  R.obligations.forEach((ob) => (byDate[ob.date] = byDate[ob.date] || []).push(ob));
  Object.keys(byDate).forEach((d) => {
    const i = f.dates.indexOf(d);
    if (i < 0) return;
    const x = X(i), yb = bottom + 32;
    el("path", { d: `M${x - 5},${yb + 8} L${x},${yb} L${x + 5},${yb + 8}Z`, fill: "#0f2233" }, svg);
  });
  el("path", { d: `M${m.l},${H - 3} L${m.l + 4},${H - 10} L${m.l + 8},${H - 3}Z`, fill: "#0f2233" }, svg);
  txt(svg, m.l + 13, H - 2, "payment due (hover for details)", { style: "font-size:11.5px" });

  // hover / keyboard readout
  const cross = el("line", { y1: m.t, y2: bottom, stroke: "#0f2233", "stroke-width": 1, opacity: 0 }, svg);
  const dots = ["p90", "p50", "p10"].map((k) => el("circle", { r: k === "p50" ? 4 : 3, fill: k === "p50" ? "#1f5fa8" : "#fff", stroke: "#1f5fa8", "stroke-width": 1.5, opacity: 0 }, svg));
  const tip = document.createElement("div");
  tip.className = "tip"; tip.hidden = true; box.appendChild(tip);
  let hover = null;
  const show = (i) => {
    hover = i;
    if (i == null) { cross.setAttribute("opacity", 0); dots.forEach((d) => d.setAttribute("opacity", 0)); tip.hidden = true; return; }
    const x = X(i);
    cross.setAttribute("x1", x); cross.setAttribute("x2", x); cross.setAttribute("opacity", 0.5);
    ["p90", "p50", "p10"].forEach((k, j) => { dots[j].setAttribute("cx", x); dots[j].setAttribute("cy", Y(f[k][i])); dots[j].setAttribute("opacity", 1); });
    tip.innerHTML = `<b>${fullDay(f.dates[i])}</b>
      <div class="row"><span>Good case (P90)</span><b>${inr(f.p90[i])}</b></div>
      <div class="row"><span>Middle (P50)</span><b>${inr(f.p50[i])}</b></div>
      <div class="row"><span>Bad case (P10)</span><b>${inr(f.p10[i])}</b></div>
      ${base ? `<div class="row"><span>Middle, before change</span><b>${inr(base.p50[i])}</b></div>` : ""}
      ${(byDate[f.dates[i]] || []).map((ob) => `<div class="row"><span>Due: ${esc(ob.label)}</span><b>${inr(ob.amount_inr)}</b></div>`).join("")}`;
    tip.hidden = false;
    tip.style.left = `${Math.min(Math.max(x, 100), W - 100)}px`; tip.style.top = `${Math.max(Y(f.p90[i]) - 12, 90)}px`;
  };
  svg.addEventListener("pointermove", (e) => {
    const r = svg.getBoundingClientRect(), px = ((e.clientX - r.left) / r.width) * W;
    show(Math.max(0, Math.min(n - 1, Math.round(((px - m.l) / (W - m.l - m.r)) * (n - 1)))));
  });
  svg.addEventListener("pointerleave", () => show(null));
  svg.addEventListener("blur", () => show(null));
  svg.addEventListener("keydown", (e) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault(); e.stopPropagation();
    const cur = hover == null ? Math.max(0, wi) : hover + (e.key === "ArrowRight" ? 1 : -1);
    show(Math.max(0, Math.min(n - 1, cur)));
  });
}
function fanKey(o = {}) {
  const sw = (inner) => `<svg viewBox="0 0 22 12" aria-hidden="true">${inner}</svg>`;
  return `<div class="key">
    <span>${sw('<rect width="22" height="12" fill="#c4d8ef" stroke="#8fb4de"/>')}Middle 80% of futures</span>
    <span>${sw('<line x1="0" x2="22" y1="6" y2="6" stroke="#1f5fa8" stroke-width="2.5"/>')}Middle future</span>
    ${o.baseline && R.baseline ? `<span>${sw('<rect width="22" height="12" fill="#e1e6ec" stroke="#b6c1cc"/><line x1="0" x2="22" y1="6" y2="6" stroke="#7d8a98" stroke-width="2" stroke-dasharray="4 3"/>')}Before this change</span>` : ""}
    ${o.paths && has(R.sample_paths) ? `<span>${sw('<path d="M0,8 C6,2 14,10 22,4" fill="none" stroke="#6f93bd" stroke-width="1.5"/>')}One future that stays above ₹0</span>
      <span>${sw('<path d="M0,3 C6,10 14,2 22,9" fill="none" stroke="#8f1d14" stroke-width="1.8"/>')}One future that runs short</span>` : ""}
    <span>${sw('<line x1="0" x2="22" y1="6" y2="6" stroke="#b42318" stroke-width="1.5" stroke-dasharray="5 3"/>')}₹0, can't pay below this</span>
    <span>${sw('<rect width="22" height="12" fill="#fde8e6" stroke="#e8a29b"/><path d="M0,12 L12,0 M8,12 L20,0" stroke="#e8a29b" stroke-width="2"/>')}Worst week</span></div>`;
}
function deltaHTML() {
  const b = R.baseline;
  if (!b) return "";
  return `Shortfall risk ${pct(b.p_shortfall)} ${stamp(b.p_shortfall)} <span aria-hidden="true">→</span><span class="sr">changes to</span> ${pct(R.worst_week.p_shortfall)} ${stamp(R.worst_week.p_shortfall)}
    <span class="muted" style="font-weight:400;font-size:15px">before vs with: ${esc(scenarioText())}</span>`;
}

/* ---------- weekly inspection ---------- */
function renderWeeks() {
  const ww = R.worst_week.week_start, t = R.risk_target;
  const rows = R.weeks.map((wk) => {
    const l = level(wk.p_shortfall), due = obligationsBetween(wk.week_start, 7);
    const worst = wk.week_start === ww;
    return `<tr class="${worst ? "worst" : ""}">
      <td>${day(wk.week_start)}${worst ? ' <span class="muted">· worst</span>' : ""}</td>
      <td class="muted">${due.map((o) => esc(o.label)).join(", ") || "–"}</td>
      <td><div class="dev" aria-hidden="true"><i style="width:${wk.p_shortfall * 100}%;background:var(--${l.k})"></i><u style="left:${t * 100}%"></u></div></td>
      <td class="num"><b>${pct(wk.p_shortfall)}</b></td>
      <td class="num">${wk.expected_shortfall_inr ? inr(wk.expected_shortfall_inr) : "–"}</td>
      <td>${stamp(wk.p_shortfall)}</td></tr>`;
  }).join("");
  $("#weeks").innerHTML = `<h3>Week by week</h3>
    <div class="scroll"><table>
      <thead><tr><th scope="col">Week of</th><th scope="col">Payments due</th><th scope="col" style="width:28%">Shortfall risk</th><th scope="col" class="num">Risk</th><th scope="col" class="num">Expected gap</th><th scope="col">Check</th></tr></thead>
      <tbody>${rows}</tbody></table></div>
    ${how(`Each bar is the chance of running short in that week; the dashed mark is the ${pct(t)} limit. A bar past the mark fails the check. Expected gap is the average shortfall when it happens.`)}`;
}

/* ---------- fixes ---------- */
function fixesHTML() {
  const fixes = R.fixes || [], plan = R.plan;
  if (!fixes.length && !plan) {
    const ok = R.worst_week.p_shortfall <= R.risk_target;
    return `<div class="empty"><b>${ok ? "No fixes needed" : "No fixes available"}</b>
      <p class="muted">${ok ? "Every week is inside the risk limit." : "The engine returned no fixes for this scenario."}</p></div>`;
  }
  const inPlan = new Set(plan ? plan.fix_ids : []);
  const t = R.risk_target;
  const sum = plan
    ? `<div class="plan-sum"><span class="tag plan">Plan</span>
        <p><b>${plan.fix_ids.length} ${plan.fix_ids.length === 1 ? "fix" : "fixes"}, ${inr(plan.total_cost_inr)} in total.</b> Worst-week risk ${pct(plan.p_shortfall_before)} ${stamp(plan.p_shortfall_before)} → ${pct(plan.p_shortfall_after)} ${stamp(plan.p_shortfall_after)}</p></div>`
    : `<div class="plan-sum"><p>No plan chosen; compare the fixes below.</p></div>`;
  const rows = fixes.map((f) => {
    const l = level(f.p_shortfall_after);
    return `<tr class="${inPlan.has(f.id) ? "inplan" : ""}">
      <td>${esc(f.label)}<details class="why"><summary>Why this number?</summary><p>${esc(f.why)}</p></details></td>
      <td class="num">${f.cost_inr ? inr(f.cost_inr) : "Free"}</td>
      <td><div class="after"><div class="dev" aria-hidden="true"><i style="width:${f.p_shortfall_after * 100}%;background:var(--${l.k})"></i><u style="left:${t * 100}%"></u></div><b>${pct(f.p_shortfall_after)}</b></div></td>
      <td><span class="tag ${f.available_now ? "now" : "later"}">${f.available_now ? "Available now" : "Set up for next time"}</span></td>
      <td>${inPlan.has(f.id) ? '<span class="tag plan">In plan</span>' : ""}</td></tr>`;
  }).join("");
  return `${sum}<div class="scroll"><table>
    <thead><tr><th scope="col">Fix</th><th scope="col" class="num">Cost</th><th scope="col" class="num">Risk after</th><th scope="col">When</th><th scope="col"><span class="sr">In plan</span></th></tr></thead>
    <tbody>${rows}</tbody></table></div>
    ${how(`Risk after is the worst-week shortfall chance if you take only that fix; the dashed mark is the ${pct(t)} limit. Highlighted rows are the cheapest set the engine picked.`)}`;
}

/* ---------- kab tak ---------- */
function kabTakBarsHTML() {
  const n = R.fan.dates.length;
  const buyers = (R.kab_tak || []).map((b) => {
    const d = b.max_delay_days, full = d >= n;
    return `<div class="buyer"><b>${esc(b.buyer)}</b>
      <div class="track" role="img" aria-label="${esc(b.buyer)} can pay up to ${d} days late"><i style="width:${(Math.min(d, n) / n) * 100}%;background:var(--blue)"></i></div>
      <span class="val">${full ? `${n}+ days late is fine` : `up to ${d} days late`}</span></div>`;
  }).join("");
  if (!buyers) return '<p class="muted">No buyers in this result.</p>';
  return `<div class="buyers">${buyers}<div class="axis" aria-hidden="true"><span></span><div><span>0 days</span><span>${Math.round(n / 2)}</span><span>${n} days</span></div><span></span></div></div>
    ${how(`Each bar is how many days late that buyer can pay before your shortfall risk passes ${pct(R.risk_target)}. A short bar means you depend on that buyer paying on time.`)}`;
}
function orderHTML() {
  const o = R.order;
  if (!o) return "";
  const safe = Math.min(o.max_safe_terms_days, o.terms_days), ok = o.max_safe_terms_days >= o.terms_days;
  return `<div class="order" id="order-box">
    <h3>This order: ${esc(o.party)}, ${inr(o.amount_inr)} on ${o.terms_days}-day terms ${ok ? '<span class="stamp s-ok">OK as asked</span>' : '<span class="stamp s-watch">Change terms</span>'}</h3>
    <p class="answer">${esc(orderAnswer(o))}</p>
    <div>${bar([{ label: "Safe terms", v: safe, c: "var(--ok)" }, { label: "Unsafe", v: o.terms_days - safe, c: "var(--ng)" }], o.terms_days, (v) => `${v} days`)}</div>
    <dl>
      <div><dt>Terms asked</dt><dd>${o.terms_days} days</dd></div>
      <div><dt>Longest safe terms</dt><dd>${o.max_safe_terms_days ? `${o.max_safe_terms_days} days` : "None"}</dd></div>
      <div><dt>Minimum advance</dt><dd>${o.min_advance_pct}%</dd></div>
      <div><dt>Margin on the order</dt><dd>${inr(o.margin_inr)}</dd></div>
    </dl>
    ${how("Green is how long you can wait for this buyer's money and stay safe; red is the part of the terms that pushes you short.")}</div>`;
}
const curvesShell = (id) => `<h3 style="font:600 16px/1.3 var(--sans);margin:24px 0 6px">Risk vs days late</h3><div class="chart" id="${id}"></div>
  <div class="curvectl"><label for="${id}-b">Buyer</label><select id="${id}-b">${R.kab_tak_curves.map((c, k) => `<option value="${k}">${esc(c.buyer)}</option>`).join("")}</select>
    <input type="range" id="${id}-d" min="0" value="0" aria-label="Days late"></div>
  <p class="curveread" id="${id}-read" aria-live="polite"></p>
  ${how(`Each line is the shortfall risk if that buyer pays later, read from the engine's runs. The dashed line is the ${pct(R.risk_target)} target; the ring marks each buyer's kab tak day. ${kabTakRule()}Move the slider to read any point.`)}`;
function kabTakRule() {
  const a = (R.assumptions || []).find((x) => /kab tak/i.test(x.name));
  return a ? `Engine rule: ${esc(a.value)}. ` : "";
}

function drawCurves(id) {
  const box = document.getElementById(id), sel = document.getElementById(`${id}-b`), rng = document.getElementById(`${id}-d`);
  if (!box) return;
  const C = R.kab_tak_curves, cur = C[+sel.value];
  rng.max = cur.delays.length - 1;
  if (+rng.value > +rng.max) rng.value = rng.max;
  const k = +rng.value, d = cur.delays[k], p = cur.p_shortfall[k];
  const W = Math.max(260, box.clientWidth), H = Math.round(Math.min(320, Math.max(220, W * 0.34)));
  const m = { l: 46, r: W < 500 ? 64 : 90, t: 16, b: 38 };
  const xMax = Math.max(...C.flatMap((c) => c.delays)), yMax = Math.max(R.risk_target * 2, ...C.flatMap((c) => c.p_shortfall)) * 1.08;
  const X = (v) => m.l + (v / xMax) * (W - m.l - m.r), Y = (v) => m.t + (1 - v / yMax) * (H - m.t - m.b);
  box.innerHTML = "";
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img",
    "aria-label": `Shortfall risk against days late for ${C.map((c) => c.buyer).join(", ")}. ${cur.buyer} at ${d} days late: ${pct(p)}.` }, box);
  const ys = niceStep(yMax, 4);
  for (let v = 0; v <= yMax + 1e-9; v += ys) {
    el("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), stroke: "#e3e9ef" }, svg);
    txt(svg, m.l - 8, Y(v) + 4, pct(v), { "text-anchor": "end" });
  }
  const xs = niceStep(xMax, W < 500 ? 3 : 6);
  for (let v = 0; v <= xMax + 1e-9; v += xs) txt(svg, X(v), H - m.b + 18, `${v}`, { "text-anchor": "middle" });
  txt(svg, W - m.r, H - 4, "days late →", { "text-anchor": "end", style: "font-size:11.5px" });
  el("line", { x1: m.l, x2: W - m.r, y1: H - m.b, y2: H - m.b, stroke: "#9fb0c1" }, svg);
  el("line", { x1: m.l, x2: W - m.r, y1: Y(R.risk_target), y2: Y(R.risk_target), stroke: "#b42318", "stroke-width": 1.5, "stroke-dasharray": "6 4" }, svg);
  txt(svg, m.l + 6, Y(R.risk_target) - 6, `${pct(R.risk_target)} risk target`, { style: "fill:var(--ng);font-weight:600;font-size:12px" });

  C.forEach((c, j) => {
    const col = SERIES[j % SERIES.length], on = c === cur;
    el("path", { d: line(c.delays.map((x, i) => [X(x), Y(c.p_shortfall[i])])), fill: "none", stroke: col, "stroke-width": on ? 3 : 1.75, "stroke-opacity": on ? 1 : 0.55 }, svg);
    const lastI = c.delays.length - 1;
    txt(svg, X(c.delays[lastI]) + 6, Y(c.p_shortfall[lastI]) + 4, c.buyer, { style: `fill:${col};font-weight:600` });
    const kt = (R.kab_tak || []).find((b) => b.buyer === c.buyer);
    if (kt && kt.max_delay_days <= xMax) {
      // ring sits on the line at the engine's kab tak day (position only; no new number is shown)
      const j1 = c.delays.findIndex((x) => x >= kt.max_delay_days), j0 = Math.max(0, j1 - 1);
      const span = c.delays[j1] - c.delays[j0] || 1, t = (kt.max_delay_days - c.delays[j0]) / span;
      const ry = Y(c.p_shortfall[j0] + t * (c.p_shortfall[j1] - c.p_shortfall[j0]));
      el("circle", { cx: X(kt.max_delay_days), cy: ry, r: 5.5, fill: "#fff", stroke: col, "stroke-width": 2 }, svg);
      const lab = txt(svg, X(kt.max_delay_days) + 8, ry + 16 + j * 13, `${c.buyer}: ${kt.max_delay_days} d`, { style: `fill:${col};font-weight:600;font-size:11.5px` });
      if (X(kt.max_delay_days) + 8 + lab.getComputedTextLength() > W) { lab.setAttribute("x", X(kt.max_delay_days) - 8); lab.setAttribute("text-anchor", "end"); }
    }
  });
  const col = SERIES[C.indexOf(cur) % SERIES.length];
  el("line", { x1: X(d), x2: X(d), y1: Y(p), y2: H - m.b, stroke: col, "stroke-dasharray": "2 3" }, svg);
  el("circle", { cx: X(d), cy: Y(p), r: 7, fill: col, stroke: "#fff", "stroke-width": 2 }, svg);
  document.getElementById(`${id}-read`).innerHTML = `If ${esc(cur.buyer)} pays ${d ? `${d} days late` : "on time"}: ${pct(p)} risk ${stamp(p)}`;
}
function wireCurves(id) {
  const sel = document.getElementById(`${id}-b`), rng = document.getElementById(`${id}-d`);
  if (!sel) return;
  // start the slider at the buyer's kab tak point so the first reading lands on the target
  const startAt = () => {
    const c = R.kab_tak_curves[+sel.value], kt = (R.kab_tak || []).find((b) => b.buyer === c.buyer);
    const i = kt ? c.delays.findIndex((x) => x >= kt.max_delay_days) : 0;
    rng.max = c.delays.length - 1; rng.value = i < 0 ? c.delays.length - 1 : i;
  };
  sel.addEventListener("change", () => { startAt(); drawCurves(id); });
  rng.addEventListener("input", () => drawCurves(id));
  startAt();
}
function renderKabTak() {
  $("#kabtak-body").innerHTML = kabTakBarsHTML() + (has(R.kab_tak_curves) ? curvesShell("kt-curves") : "") + orderHTML();
  wireCurves("kt-curves");
}

/* ---------- due vs expected ---------- */
function drawArrivals() {
  const box = $("#arr-body");
  $("#arrivals").hidden = !has(R.arrivals);
  if (!has(R.arrivals)) return;
  box.innerHTML = `<div class="key" style="margin:0 0 12px">
      <span><svg viewBox="0 0 22 12" aria-hidden="true"><rect x="1" y="1" width="20" height="10" fill="#fff" stroke="#0f2233" stroke-width="1.5"/></svg>Due on the invoice</span>
      <span><svg viewBox="0 0 22 12" aria-hidden="true"><rect width="22" height="12" fill="#1f5fa8"/></svg>Expected to arrive (engine)</span></div>
    <div class="arr">${R.arrivals.map((a, k) => `<div><h3>${esc(a.buyer)}</h3>
      <p>Open ${inr(a.open_inr)} · due in these weeks ${inr(a.due_by_week_inr.reduce((s, v) => s + v, 0))} · expected ${inr(a.expected_by_week_inr.reduce((s, v) => s + v, 0))}</p>
      <div class="chart" id="arr-${k}"></div></div>`).join("")}</div>
    ${how("Outlined bars are what each buyer owes by its invoice due dates, week by week. Solid bars are when the engine expects the money to actually land. A solid bar sitting to the right of its outline is a buyer who usually pays late.")}`;
  const yMax = Math.max(1, ...R.arrivals.flatMap((a) => [...a.due_by_week_inr, ...a.expected_by_week_inr]));
  R.arrivals.forEach((a, k) => {
    const host = document.getElementById(`arr-${k}`);
    const W = Math.max(240, host.clientWidth), H = 150, m = { l: 44, r: 6, t: 8, b: 24 };
    const nW = a.due_by_week_inr.length, gw = (W - m.l - m.r) / nW, bw = Math.max(3, gw * 0.36);
    const Y = (v) => m.t + (1 - v / yMax) * (H - m.t - m.b);
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img",
      "aria-label": `${a.buyer}: due by week ${a.due_by_week_inr.map(inr).join(", ")}; expected by week ${a.expected_by_week_inr.map(inr).join(", ")}` }, host);
    const ys = niceStep(yMax, 2);
    for (let v = 0; v <= yMax + 1e-6; v += ys) {
      el("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), stroke: "#e3e9ef" }, svg);
      txt(svg, m.l - 6, Y(v) + 4, inr(v), { "text-anchor": "end", style: "font-size:11px" });
    }
    a.due_by_week_inr.forEach((v, i) => {
      const x = m.l + i * gw + gw / 2;
      if (v) el("rect", { x: x - bw - 0.5, y: Y(v), width: bw, height: Y(0) - Y(v), fill: "#fff", stroke: "#0f2233", "stroke-width": 1.25 }, svg);
      const e = a.expected_by_week_inr[i];
      if (e) el("rect", { x: x + 0.5, y: Y(e), width: bw, height: Y(0) - Y(e), fill: "#1f5fa8" }, svg);
      if (i % 4 === 0 && R.weeks[i]) txt(svg, x, H - 6, day(R.weeks[i].week_start), { "text-anchor": "middle", style: "font-size:11px" });
    });
    el("line", { x1: m.l, x2: W - m.r, y1: Y(0), y2: Y(0), stroke: "#9fb0c1" }, svg);
  });
}

/* ---------- bridge waterfall ---------- */
function drawBridge(box) {
  const b = R.bridge;
  const bars = [{ label: "Today", v: b.start_inr, total: true }, ...b.items.map((i) => ({ label: i.label, v: i.amount_inr })), { label: `End of week ${day(b.week_start)}`, v: b.end_inr, total: true }];
  let run = 0;
  bars.forEach((x) => { if (x.total) { x.a = 0; x.b = x.v; run = x.v; } else { x.a = run; run += x.v; x.b = run; } });
  const W = Math.max(640, box.clientWidth), H = 340, m = { l: 56, r: 10, t: 26, b: 58 };
  const vals = [0, ...bars.flatMap((x) => [x.a, x.b])], lo = Math.min(...vals), hi = Math.max(...vals);
  const st = niceStep(hi - lo, 5), y0 = Math.floor(lo / st) * st, y1 = Math.ceil(hi / st) * st;
  const Y = (v) => m.t + ((y1 - v) * (H - m.t - m.b)) / (y1 - y0);
  const gw = (W - m.l - m.r) / bars.length, bw = Math.min(64, gw * 0.66);
  box.innerHTML = "";
  const wrap = document.createElement("div"); wrap.className = "scroll"; box.appendChild(wrap);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img",
    "aria-label": `Money from today to the end of the week of ${day(b.week_start)} on the average path: starts at ${inr(b.start_inr)}, ${b.items.map((i) => `${i.label} ${signed(i.amount_inr)}`).join(", ")}, ends at ${inr(b.end_inr)}.` }, wrap);
  for (let v = y0; v <= y1 + 1e-6; v += st) {
    el("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), stroke: "#e3e9ef" }, svg);
    txt(svg, m.l - 8, Y(v) + 4, inr(v), { "text-anchor": "end" });
  }
  el("line", { x1: m.l, x2: W - m.r, y1: Y(0), y2: Y(0), stroke: "#b42318", "stroke-width": 1.5, "stroke-dasharray": "6 4" }, svg);
  bars.forEach((x, i) => {
    const cx = m.l + i * gw + gw / 2, top = Y(Math.max(x.a, x.b)), h = Math.max(1.5, Math.abs(Y(x.a) - Y(x.b)));
    const fill = x.total ? (x.v < 0 ? "#b42318" : "#123a63") : x.v >= 0 ? "#1a7343" : "#b42318";
    el("rect", { x: cx - bw / 2, y: top, width: bw, height: h, fill, rx: 2 }, svg);
    if (i < bars.length - 1) el("line", { x1: cx + bw / 2, x2: cx + gw - bw / 2, y1: Y(x.b), y2: Y(x.b), stroke: "#9fb0c1", "stroke-dasharray": "2 2" }, svg);
    txt(svg, cx, top - 6, x.total ? inr(x.v) : signed(x.v), { "text-anchor": "middle", style: `font-weight:600;fill:${fill}` });
    // wrap the label onto up to three lines
    const words = x.label.split(" "), lines = [""];
    words.forEach((w) => { if ((lines[lines.length - 1] + " " + w).trim().length > Math.max(8, gw / 7) && lines[lines.length - 1]) lines.push(w); else lines[lines.length - 1] = (lines[lines.length - 1] + " " + w).trim(); });
    lines.slice(0, 3).forEach((l, j) => txt(svg, cx, H - m.b + 16 + j * 14, l, { "text-anchor": "middle", style: "font-size:11.5px" }));
  });
}

/* ---------- assumptions ---------- */
function renderAssumptions() {
  $("#assume-body").innerHTML = `<div class="scroll"><table class="assume"><thead><tr><th scope="col">Assumption</th><th scope="col">Value</th></tr></thead><tbody>${(R.assumptions || [])
    .map((a) => `<tr><td>${esc(a.name)}</td><td>${esc(a.value)}</td></tr>`).join("")}</tbody></table></div>`;
}

/* ---------- story ---------- */
const STEPS = [
  { title: () => "Your books today",
    say: () => { const t = R.today; return `You have ${inr(t.bank_inr)} in the bank and can still draw ${inr(t.headroom_inr)} on the overdraft. Buyers owe you ${inr(t.receivable_inr)}, and ${inr(t.overdue_45_inr)} of that is more than 45 days late.`; },
    draw: (stage) => { stage.innerHTML = todayHTML(); } },
  { title: () => (R.n_paths ? `${R.n_paths.toLocaleString("en-IN")} futures` : "Possible futures"),
    say: () => (has(R.sample_paths) && R.n_paths
      ? `We play out the next ${R.fan.dates.length} days ${R.n_paths.toLocaleString("en-IN")} different ways. Each line is one possible future; the dark red ones run out of money.`
      : `We play out the next ${R.fan.dates.length} days many different ways. The band shows where 8 in 10 of those futures land.`),
    draw: (stage, animate) => {
      stage.innerHTML = `<div class="chart" id="story-fan"></div>${fanKey({ paths: true })}<p class="counter" id="counter" aria-live="polite"></p>
        ${how("Each thin line is one simulated future of the money you can reach. The blue band is where most of them land. Every red line crosses ₹0 at least once: a day when a payment would fail.")}`;
      const counter = $("#counter");
      const final = () => { if (R.n_paths != null && R.n_short_paths != null) counter.innerHTML = `<b>${R.n_short_paths.toLocaleString("en-IN")}</b> of ${R.n_paths.toLocaleString("en-IN")} futures run short`; };
      drawFan($("#story-fan"), { paths: true, animate, tall: true,
        onProgress: (k, total) => (k < total ? (counter.textContent = `Drawing sample future ${k} of ${total}…`) : final()) });
      if (!has(R.sample_paths)) final();
    } },
  { title: () => "Why that week",
    say: () => `The week of ${day(R.worst_week.week_start)} is the hardest: ${pct(R.worst_week.p_shortfall)} chance you can't pay ${R.worst_week.obligation}.`,
    draw: (stage) => {
      const due = obligationsBetween(R.worst_week.week_start, 7);
      stage.innerHTML = (R.bridge ? `<h3>How the money moves from today to the end of that week</h3><div id="story-bridge"></div>
        ${how("Start with what you can reach today. Green bars are money coming in from each buyer, red bars are payments going out. The last bar is what's left at the end of the worst week on an average future; below the red line means short.")}` : "")
        + `<h3>Due that week</h3><ul class="oblist">${due.map((o) => `<li>${day(o.date)} · <b>${esc(o.label)}</b> ${inr(o.amount_inr)}</li>`).join("") || "<li>Nothing scheduled</li>"}</ul>`;
      if (R.bridge) drawBridge($("#story-bridge"));
    } },
  { title: () => "What changes it",
    say: () => (R.baseline
      ? `${scenarioText()} moves the shortfall risk from ${pct(R.baseline.p_shortfall)} to ${pct(R.worst_week.p_shortfall)}. Here is what would bring it back down.`
      : `Here is what moves the risk: how late each buyer can pay${R.order ? ", what terms the order can take" : ""}${has(R.fixes) ? ", and the fixes on offer" : ""}.`),
    draw: (stage) => {
      stage.innerHTML = (R.baseline ? `<h3>Before and after</h3><p class="delta">${deltaHTML()}</p><div class="chart" id="story-base"></div>${fanKey({ baseline: true })}
          ${how("Grey is the next 90 days without this change; blue is with it. Where blue sits lower, the change costs you cash.")}` : "")
        + `<h3>Kab tak? How late can each buyer pay</h3>` + (has(R.kab_tak_curves) ? curvesShell("story-curves").replace(/^<h3[^>]*>Risk vs days late<\/h3>/, "") : kabTakBarsHTML())
        + orderHTML()
        + (has(R.fixes) ? `<h3>Fixes</h3>${fixesHTML()}` : "");
      if (R.baseline) drawFan($("#story-base"), { baseline: true });
      wireCurves("story-curves");
      if (has(R.kab_tak_curves)) drawCurves("story-curves");
    } },
];
function renderStory(animate) {
  $("#steps").innerHTML = STEPS.map((s, i) => `<li><button type="button" data-step="${i}" class="${i < step ? "done" : ""}" ${i === step ? 'aria-current="step"' : ""}><b>STEP ${i + 1}</b>${esc(s.title())}</button></li>`).join("");
  $("#say").textContent = STEPS[step].say();
  STEPS[step].draw($("#stage"), animate);
  $("#back").disabled = step === 0;
  $("#next").textContent = step === STEPS.length - 1 ? "Start again" : "Next";
  $("#stepno").textContent = `${step + 1} of ${STEPS.length}`;
}
function go(i) { step = (i + STEPS.length) % STEPS.length; renderStory(true); }
$("#steps").addEventListener("click", (e) => { const b = e.target.closest("[data-step]"); if (b) go(+b.dataset.step); });
$("#back").addEventListener("click", () => go(step - 1));
$("#next").addEventListener("click", () => go(step + 1));
document.addEventListener("keydown", (e) => {
  if (document.body.dataset.view !== "story" || e.target.closest("input, select, textarea, svg")) return;
  if (e.key === "ArrowRight" && step < STEPS.length - 1) go(step + 1);
  if (e.key === "ArrowLeft" && step > 0) go(step - 1);
});

/* ---------- render ---------- */
function drawCharts(animate) {
  if (!R) return;
  const v = document.body.dataset.view;
  if (v === "ca") {
    $("#fan-delta").hidden = !R.baseline;
    $("#fan-delta").innerHTML = deltaHTML();
    drawFan($("#fan-chart"), { baseline: true });
    $("#fan-key").outerHTML = fanKey({ baseline: true }).replace('class="key"', 'class="key" id="fan-key"');
    if (has(R.kab_tak_curves)) drawCurves("kt-curves");
    drawArrivals();
  }
  if (v === "story") renderStory(animate);
}
function render() {
  renderHeader();
  renderVerdict();
  $("#today-body").innerHTML = todayHTML();
  $("#fan-sub").textContent = "Money you could reach each day (bank plus undrawn overdraft) across simulated futures. Below ₹0 a payment can't be made.";
  renderWeeks();
  $("#fixes-body").innerHTML = fixesHTML();
  renderKabTak();
  renderAssumptions();
  $("#arrivals").hidden = !has(R.arrivals);
  drawCharts(true);
  $("#foot").textContent = R.synthetic ? "All figures come from a synthetic business. Not a real company's books." : "";
}

/* ---------- scenario panel ---------- */
const FIELDS = {
  status: [], new_order: ["party", "amount_inr", "days"], delay_payment: ["party", "days"],
  expense_shock: ["amount_inr", "date"], sales_drop: ["pct", "days"], supplier_terms: ["party", "days"],
  schedule_change: ["obligation", "date"], payment_received: ["party", "amount_inr", "date"],
};
const DAYS_LABEL = { new_order: "Payment terms (days)", delay_payment: "Days late", sales_drop: "How long (days)", supplier_terms: "New supplier terms (days)" };
const LABEL = { party: "Party", amount_inr: "Amount", days: "Days", pct: "Drop", date: "Date", obligation: "Payment to move" };
const form = $("#scn");

function syncFields() {
  const type = form.type.value;
  document.querySelectorAll("[data-f]").forEach((d) => (d.hidden = !FIELDS[type].includes(d.dataset.f)));
  $("#days-label").textContent = DAYS_LABEL[type] || "Days";
  showJson();
}
function scenario() {
  const type = form.type.value, use = FIELDS[type];
  const int = (v) => (v === "" ? null : Math.round(Number(v)));
  const val = {
    party: form.party.value.trim() || null, amount_inr: int(form.amount_inr.value), days: int(form.days.value),
    pct: int(form.pct.value), date: form.date.value || null, obligation: form.obligation.value,
  };
  const s = { type };
  for (const k of ["party", "amount_inr", "days", "pct", "date", "obligation"]) s[k] = use.includes(k) ? val[k] : null;
  s.transcript = form.transcript.value.trim() || null;
  s.needs_clarification = false;
  s.question = null;
  return s;
}
function showJson() {
  const s = scenario();
  $("#json").textContent = JSON.stringify(s, null, 2);
  $("#amount-hint").textContent = s.amount_inr ? inr(s.amount_inr) : "";
}
function prefill(s) {
  if (!s) return;
  form.type.value = FIELDS[s.type] ? s.type : "status";
  for (const k of ["party", "amount_inr", "days", "pct", "date"]) if (s[k] != null) form[k].value = s[k];
  if (s.obligation) form.obligation.value = s.obligation;
  if (s.transcript) form.transcript.value = s.transcript;
  syncFields();
}
function setStatus(msg, err) { const st = $("#status"); st.textContent = msg; st.className = `status${err ? " err" : ""}`; }

form.addEventListener("input", (e) => (e.target === form.type ? syncFields() : showJson()));
const TENANT = new URLSearchParams(location.search).get("tenant");   // /dashboard?tenant=<id>; none = the demo business
const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(TENANT ? { ...body, tenant: TENANT } : body) });
// Runs a scenario through the engine and redraws; say(msg, err) reports progress. Returns true on success.
async function run(s, btn, say) {
  btn.disabled = true; say("Running…");
  try {
    const res = await post("/api/answer", s);
    const body = await res.json();
    if (!res.ok) { say(body.error || "The engine could not answer.", true); return false; }
    R = body.result; SOURCE = body.source; step = 0;
    render();
    say(body.source === "engine" ? "Answered by the engine." : "Engine not available here, so this shows the saved fixture.");
    return true;
  } catch {
    say("Can't reach the server. Start it with python3 ui/server.py.", true);
    return false;
  } finally { btn.disabled = false; }
}
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const s = scenario();
  const missing = FIELDS[s.type].filter((k) => s[k] == null);
  if (missing.length) return setStatus(`Fill in: ${missing.map((k) => LABEL[k]).join(", ")}.`, true);
  explainRun++; $("#explain").hidden = true;
  await run(s, form.querySelector(".run"), setStatus);
});

/* ---------- free-text question: LLM parses, owner confirms, engine runs, LLM explains ---------- */
const ask = $("#ask");
let pending = null;   // parsed scenario waiting for "Run it"
let clarify = null;   // {text, question, first} when the LLM asked a follow-up
let explainRun = 0;   // ignore stale explanations
/* Clear button + the follow-up question box. Clear shows whenever there is anything to clear. */
function showClarify() {
  $("#clarify").hidden = !clarify;
  if (clarify) { $("#clarify-q").textContent = clarify.question; $("#clarify-first").textContent = clarify.first; }
}
function syncClear() {
  $("#clear").hidden = !(clarify || pending || ask.q.value.trim() || !$("#explain").hidden || !$("#ask-status").hidden);
}
$("#clear").addEventListener("click", () => {
  clarify = null; pending = null; explainRun++;   // explainRun++ drops an explanation still being written
  ask.q.value = ""; setAsk(""); showClarify();
  $("#readback").hidden = true; $("#explain").hidden = true;
  syncClear(); ask.q.focus();
});
ask.q.addEventListener("input", syncClear);
function setAsk(msg, err) { const st = $("#ask-status"); st.hidden = !msg; st.textContent = msg || ""; st.className = `status${err ? " err" : ""}`; syncClear(); }

ask.addEventListener("submit", async (e) => {
  e.preventDefault();
  const said = ask.q.value.trim();
  if (!said) return;
  const text = clarify ? `${clarify.text}\n(Asked: "${clarify.question}" Answer: ${said})` : said;
  const first = clarify ? clarify.first : said;   // what the owner originally asked, for the header
  const btn = ask.querySelector('button[type="submit"]');
  pending = null; $("#readback").hidden = true; btn.disabled = true; setAsk("Reading your question…");
  try {
    const res = await post("/api/parse", { text });
    const body = await res.json();
    if (!res.ok) return setAsk(body.error, true);
    const s = body.scenario;
    if (s.needs_clarification) {
      clarify = { text, question: s.question, first };
      ask.q.value = ""; ask.q.focus(); showClarify();
      return setAsk("");
    }
    clarify = null; showClarify(); pending = { ...s, transcript: first };
    $("#rb-text").textContent = scenarioText(s);
    $("#readback").hidden = false; setAsk("");
    $("#rb-run").focus();
  } catch {
    setAsk("Can't reach the server. Start it with python3 ui/server.py.", true);
  } finally { btn.disabled = false; }
});
ask.q.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask.requestSubmit(); } });

/* mic: record, Groq Whisper writes it into the box, then the usual parse + read-back */
const mic = $("#mic");
let rec = null;
if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) mic.hidden = true;
function setMic(on) { mic.setAttribute("aria-pressed", String(on)); mic.querySelector("span").textContent = on ? "Stop" : "Speak"; }
mic.addEventListener("click", async () => {
  if (rec) return rec.stop();
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
  catch { return setAsk("Can't use the microphone. Allow it in the browser, or type the question.", true); }
  const chunks = [], r = new MediaRecorder(stream);
  const cap = setTimeout(() => r.state === "recording" && r.stop(), 30000);  // one question, not a speech
  r.ondataavailable = (e) => e.data.size && chunks.push(e.data);
  r.onstop = async () => {
    clearTimeout(cap); stream.getTracks().forEach((t) => t.stop());
    rec = null; setMic(false);
    const blob = new Blob(chunks, { type: r.mimeType || "audio/webm" });
    if (!blob.size) return setAsk("Didn't hear anything. Try again or type it.", true);
    mic.disabled = true; setAsk("Writing down what you said…");
    try {
      const res = await fetch("/api/transcribe", { method: "POST", headers: { "Content-Type": blob.type }, body: blob });
      const body = await res.json();
      if (!res.ok) return setAsk(body.error, true);
      if (!body.text) return setAsk("Didn't catch that. Try again or type it.", true);
      ask.q.value = body.text;
      ask.requestSubmit();
    } catch {
      setAsk("Can't reach the server. Start it with python3 ui/server.py.", true);
    } finally { mic.disabled = false; }
  };
  rec = r; r.start(); setMic(true);
  setAsk("Listening… tap Stop when you're done.");
});

$("#rb-run").addEventListener("click", async () => {
  const { lang, ...s } = pending;
  if (!(await run(s, $("#rb-run"), setAsk))) return;
  $("#readback").hidden = true;
  explain(s.transcript, lang);
});
$("#rb-edit").addEventListener("click", () => {
  const { lang, ...s } = pending;
  prefill(s);
  $("#byhand").open = true; form.type.focus();
});

async function explain(question, lang) {
  const id = ++explainRun, box = $("#explain"), out = $("#explain-text");
  box.hidden = false; syncClear(); out.lang = lang; out.textContent = "Writing a plain-language summary…"; $("#explain-src").textContent = "";
  try {
    const res = await post("/api/explain", { question, lang, result: R });
    const body = await res.json();
    if (id !== explainRun) return;
    if (!res.ok) return (box.hidden = true);
    out.textContent = body.text;
    $("#explain-src").textContent = body.source === "llm"
      ? "Written by an AI model from the engine's numbers. A check removes any sentence with a number the engine didn't produce."
      : "Standard sentence: the AI summary was unavailable or didn't pass the number check.";
  } catch { if (id === explainRun) box.hidden = true; }
}

/* ---------- view toggle ---------- */
const VIEWS = ["owner", "ca", "story"];
function setView(v) {
  document.body.dataset.view = v;
  document.querySelectorAll(".switch [data-view]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.view === v)));
  try { localStorage.setItem("kabtak-view", v); } catch {}
  drawCharts(true);
}
document.querySelectorAll(".switch [data-view]").forEach((b) => b.addEventListener("click", () => setView(b.dataset.view)));
let rz, lastW = innerWidth;
window.addEventListener("resize", () => {
  if (innerWidth === lastW) return;
  lastW = innerWidth;
  cancelAnimationFrame(rz); rz = requestAnimationFrame(() => drawCharts(false));
});

(async function init() {
  let v = new URLSearchParams(location.search).get("view");
  if (!VIEWS.includes(v)) try { v = localStorage.getItem("kabtak-view"); } catch {}
  setView(VIEWS.includes(v) ? v : "owner");
  try {
    const res = await fetch("/api/result" + (TENANT ? `?tenant=${encodeURIComponent(TENANT)}` : ""));
    const body = await res.json();
    if (!res.ok) return setStatus(body.error || "The engine could not answer.", true);
    R = body.result; SOURCE = body.source;
    if (body.business_name) {
      $("#biz").textContent = body.business_name; $("#biz").hidden = false;
      document.title = `${body.business_name} · Kab Tak?`;
    }
    if (body.synthetic === false) $("#synth").hidden = true;
    $("#parties").innerHTML = [...new Set([...(R.kab_tak || []).map((b) => b.buyer), R.scenario && R.scenario.party].filter(Boolean))]
      .map((p) => `<option value="${esc(p)}">`).join("");
    prefill(R.scenario);
    render();
    setStatus(SOURCE === "engine" ? "Live status check from the engine. Change the question and run it." : "Showing a saved result. Change the question and run it.");
  } catch {
    setStatus("Can't reach the server. Start it with python3 ui/server.py.", true);
  }
})();
