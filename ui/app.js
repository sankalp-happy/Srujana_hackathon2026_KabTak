// Kab Tak? UI. Every number shown comes from the engine result; this file only formats and draws.
const $ = (s) => document.querySelector(s);
const LAKH = 1e5;
const SVGNS = "http://www.w3.org/2000/svg";
let R = null; // current result
let hover = null; // fan chart hover index

/* ---------- formatting ---------- */
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
function inr(n) {
  if (n == null) return "–";
  const sign = n < 0 ? "−" : "";
  const a = Math.abs(n);
  if (a >= LAKH) return `${sign}₹${(a / LAKH).toFixed(a >= 10 * LAKH ? 0 : 1).replace(/\.0$/, "")} L`;
  return `${sign}₹${Math.round(a).toLocaleString("en-IN")}`;
}
const pct = (p) => `${Math.round(p * 100)}%`;
const toDate = (iso) => new Date(`${iso}T00:00:00`);
const day = (iso, lang = "en-IN") => toDate(iso).toLocaleDateString(lang, { day: "numeric", month: "short" });
const fullDay = (iso) => toDate(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
const addDays = (iso, n) => { const d = toDate(iso); d.setDate(d.getDate() + n); return d; };

// Three checks against the result's own risk target; "likely short" means more likely than not.
function level(p) {
  if (p <= R.risk_target) return { k: "ok", label: "OK", long: "Within limit" };
  if (p < 0.5) return { k: "watch", label: "At risk", long: "At risk" };
  return { k: "ng", label: "Likely short", long: "Likely short" };
}
const stamp = (p) => { const l = level(p); return `<span class="stamp s-${l.k}">${l.label}</span>`; };
const fixById = (id) => (R.fixes || []).find((f) => f.id === id);

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
function renderHeader(source) {
  const s = R.scenario || { type: "status" };
  const what = (TYPE_TEXT[s.type] || (() => s.type))(s);
  $("#asked").innerHTML = (s.transcript ? `<q lang="mr">${esc(s.transcript)}</q> · ` : "") + esc(what);
  const bits = [`As of ${fullDay(R.as_of)}`, `${pct(R.risk_target)} risk limit`];
  if (R.placeholder) bits.push("placeholder numbers");
  bits.push(source);
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
  const wk = day(w.week_start), wkHi = day(w.week_start, "hi-IN"), p = pct(w.p_shortfall);
  const head = {
    ok: `Safe for the next ${n} days`,
    watch: `Week of ${wk} is at risk`,
    ng: `Week of ${wk} will likely fall short`,
  }[l.k];
  const why = l.k === "ok"
    ? `Hardest week starts ${wk}: ${p} chance of a shortfall, inside the ${pct(R.risk_target)} limit.`
    : `${p} chance you can't pay ${esc(w.obligation)}.`;
  const hi = {
    ok: `अगले ${n} दिन सुरक्षित हैं। सबसे कठिन हफ़्ता ${wkHi}: ${p} जोखिम।`,
    watch: `${wkHi} वाले हफ़्ते में ${p} संभावना है कि भुगतान नहीं हो पाएगा।`,
    ng: `${wkHi} वाले हफ़्ते में भुगतान चूकने की संभावना ज़्यादा है: ${p}।`,
  }[l.k];

  let action;
  const plan = R.plan, first = plan && plan.fix_ids.length ? fixById(plan.fix_ids[0]) : null;
  if (plan) {
    action = `<p class="lead">Do this first: <b>${esc(first ? first.label : plan.fix_ids[0])}</b>${first ? ` <span class="muted">· costs ${inr(first.cost_inr)}</span>` : ""}</p>
      <p class="muted">Full plan: ${plan.fix_ids.length} ${plan.fix_ids.length === 1 ? "fix" : "fixes"} for ${inr(plan.total_cost_inr)} takes the risk from ${pct(plan.p_shortfall_before)} to ${pct(plan.p_shortfall_after)} ${stamp(plan.p_shortfall_after)}</p>
      <p lang="hi" class="hi" style="font-size:17px;margin:0">पहला कदम: ${esc(first ? first.label : plan.fix_ids[0])}</p>`;
  } else if (l.k === "ok") {
    action = `<p class="lead"><b>No fixes needed.</b></p>`;
  } else {
    action = `<p class="lead"><b>No fixes available.</b> <span class="muted">The engine found nothing that lowers this risk.</span></p>`;
  }
  if (R.order) action += `<p><b>This order:</b> ${esc(orderAnswer(R.order))}</p>`;

  $("#verdict").className = "sheet verdict";
  $("#verdict").innerHTML = `
    <div class="big strike s-${l.k}" style="background:none">${l.label}<small>worst week · ${p}</small></div>
    <div>
      <h2 id="verdict-h">${head}</h2>
      <p class="sub" style="margin:6px 0 0;font-size:17px;color:var(--ink)">${why}</p>
      <p class="hi" lang="hi">${hi}</p>
      <div class="action">${action}</div>
    </div>`;
}

/* ---------- 1. today ---------- */
function bar(parts, total, fmt = inr) {
  return `<div class="track" role="img" aria-label="${esc(parts.map((p) => `${p.label} ${fmt(p.v)}`).join(", "))}">${parts
    .map((p) => `<i style="width:${(Math.max(0, p.v) / total) * 100}%;background:${p.c}"></i>`).join("")}</div>
    <div class="legend">${parts.map((p) => `<span style="--c:${p.c}">${p.label} ${fmt(p.v)}</span>`).join("")}</div>`;
}
function renderToday() {
  const t = R.today;
  $("#today-body").innerHTML = `
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
    </div>`;
}

/* ---------- 2. fan chart + weekly inspection ---------- */
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
function weekIndex(iso) { return R.fan.dates.indexOf(iso); }
function obligationsBetween(startIso, days) {
  const a = toDate(startIso), b = addDays(startIso, days);
  return R.obligations.filter((o) => { const d = toDate(o.date); return d >= a && d < b; });
}

function renderFan() {
  const box = $("#fan-chart"), f = R.fan, n = f.dates.length;
  const w = R.worst_week;
  $("#fan-sub").innerHTML = `Money you could reach each day (bank plus undrawn overdraft) across simulated futures. The band holds the middle 80% of outcomes; below ₹0 a payment can't be made.`;
  const W = Math.max(260, box.clientWidth), H = Math.round(Math.min(380, Math.max(260, W * 0.4)));
  const m = { l: W < 500 ? 46 : 62, r: 12, t: 34, b: 52 };
  const lo = Math.min(0, ...f.p10), hi = Math.max(0, ...f.p90);
  const pad = (hi - lo) * 0.08;
  const step = niceStep(hi - lo + 2 * pad, W < 500 ? 4 : 5);
  const y0 = Math.floor((lo - pad) / step) * step, y1 = Math.ceil((hi + pad) / step) * step;
  const X = (i) => m.l + (i * (W - m.l - m.r)) / (n - 1);
  const Y = (v) => m.t + ((y1 - v) * (H - m.t - m.b)) / (y1 - y0);
  const bottom = H - m.b;

  box.innerHTML = "";
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img", tabindex: 0,
    "aria-label": `Fan chart over ${n} days. Middle outcome ends at ${inr(f.p50[n - 1])}. Worst week starts ${day(w.week_start)} with a ${pct(w.p_shortfall)} chance of a shortfall. Use left and right arrow keys to read each day.` }, box);
  const defs = el("defs", {}, svg);
  const hatch = el("pattern", { id: "hatch", width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" }, defs);
  el("rect", { width: 6, height: 6, fill: "#fde8e6" }, hatch);
  el("line", { x1: 0, y1: 0, x2: 0, y2: 6, stroke: "#e8a29b", "stroke-width": 2 }, hatch);

  // grid + y labels
  for (let v = y0; v <= y1 + 1e-6; v += step) {
    el("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), stroke: "#e3e9ef" }, svg);
    el("text", { x: m.l - 8, y: Y(v) + 4, "text-anchor": "end" }, svg).textContent = inr(v);
  }
  // below zero
  el("rect", { x: m.l, y: Y(0), width: W - m.l - m.r, height: Math.max(0, bottom - Y(0)), fill: "#fdf0ee" }, svg);

  // worst week
  const wi = weekIndex(w.week_start);
  if (wi >= 0) {
    const x0 = X(wi), x1 = X(Math.min(n - 1, wi + 7));
    el("rect", { x: x0, y: m.t, width: x1 - x0, height: bottom - m.t, fill: "url(#hatch)", opacity: 0.9 }, svg);
    const t = el("text", { x: x0, y: m.t - 10, style: "fill:var(--ng);font-weight:600;font-size:13px" }, svg);
    t.textContent = `Worst week · ${pct(w.p_shortfall)} chance short`;
    if (x0 + t.getComputedTextLength() > W - m.r) { t.setAttribute("x", Math.max(m.l, x1)); t.setAttribute("text-anchor", "end"); }
  }

  // band + median
  const band = f.p90.map((v, i) => `${X(i)},${Y(v)}`).join(" L") + " L" + f.p10.map((v, i) => `${X(i)},${Y(v)}`).reverse().join(" L");
  const g = el("g", { class: "band" }, svg);
  el("path", { d: `M${band}Z`, fill: "#c4d8ef", "fill-opacity": 0.85, stroke: "#8fb4de", "stroke-width": 1 }, g);
  el("path", { d: "M" + f.p50.map((v, i) => `${X(i)},${Y(v)}`).join(" L"), fill: "none", stroke: "#1f5fa8", "stroke-width": 2.25, "stroke-linejoin": "round" }, g);

  // zero line
  el("line", { x1: m.l, x2: W - m.r, y1: Y(0), y2: Y(0), stroke: "#b42318", "stroke-width": 1.5, "stroke-dasharray": "6 4" }, svg);
  const zl = el("text", { x: W - m.r - 4, y: Y(0) + 16, "text-anchor": "end", style: "fill:var(--ng);font-weight:600;font-size:12.5px" }, svg);
  zl.textContent = "₹0 · can't pay below this";

  // x axis: month starts labelled, week starts ticked
  el("line", { x1: m.l, x2: W - m.r, y1: bottom, y2: bottom, stroke: "#9fb0c1" }, svg);
  let lastLabel = -Infinity;
  f.dates.forEach((d, i) => {
    const dt = toDate(d);
    if (dt.getDay() === 1) el("line", { x1: X(i), x2: X(i), y1: bottom, y2: bottom + 4, stroke: "#9fb0c1" }, svg);
    if ((dt.getDate() === 1 || i === 0) && X(i) - lastLabel > 48) {
      lastLabel = X(i);
      el("line", { x1: X(i), x2: X(i), y1: bottom, y2: bottom + 8, stroke: "#4a5d70" }, svg);
      el("text", { x: X(i), y: bottom + 22, "text-anchor": i === 0 ? "start" : "middle", style: "font-weight:600" }, svg).textContent = day(d);
    }
  });

  // obligation markers below the axis
  const byDate = {};
  R.obligations.forEach((o) => (byDate[o.date] = byDate[o.date] || []).push(o));
  Object.keys(byDate).forEach((d) => {
    const i = weekIndex(d);
    if (i < 0) return;
    const x = X(i), yb = bottom + 32;
    el("path", { d: `M${x - 5},${yb + 8} L${x},${yb} L${x + 5},${yb + 8}Z`, fill: "#0f2233" }, svg);
  });
  el("path", { d: `M${m.l},${H - 3} L${m.l + 4},${H - 10} L${m.l + 8},${H - 3}Z`, fill: "#0f2233" }, svg);
  el("text", { x: m.l + 13, y: H - 2, style: "font-size:11.5px" }, svg).textContent = "payment due (hover for details)";

  // hover / keyboard readout
  const cross = el("line", { y1: m.t, y2: bottom, stroke: "#0f2233", "stroke-width": 1, opacity: 0 }, svg);
  const dots = ["p90", "p50", "p10"].map((k) => el("circle", { r: k === "p50" ? 4 : 3, fill: k === "p50" ? "#1f5fa8" : "#fff", stroke: "#1f5fa8", "stroke-width": 1.5, opacity: 0 }, svg));
  const tip = document.createElement("div");
  tip.className = "tip"; tip.hidden = true; box.appendChild(tip);
  const show = (i) => {
    hover = i;
    if (i == null) { cross.setAttribute("opacity", 0); dots.forEach((d) => d.setAttribute("opacity", 0)); tip.hidden = true; return; }
    const x = X(i);
    cross.setAttribute("x1", x); cross.setAttribute("x2", x); cross.setAttribute("opacity", 0.5);
    ["p90", "p50", "p10"].forEach((k, j) => { dots[j].setAttribute("cx", x); dots[j].setAttribute("cy", Y(f[k][i])); dots[j].setAttribute("opacity", 1); });
    const due = byDate[f.dates[i]] || [];
    tip.innerHTML = `<b>${fullDay(f.dates[i])}</b>
      <div class="row"><span>Good case (P90)</span><b>${inr(f.p90[i])}</b></div>
      <div class="row"><span>Middle (P50)</span><b>${inr(f.p50[i])}</b></div>
      <div class="row"><span>Bad case (P10)</span><b>${inr(f.p10[i])}</b></div>
      ${due.map((o) => `<div class="row"><span>Due: ${esc(o.label)}</span><b>${inr(o.amount_inr)}</b></div>`).join("")}`;
    tip.hidden = false;
    const left = Math.min(Math.max(x, 100), W - 100);
    tip.style.left = `${left}px`; tip.style.top = `${Math.max(Y(f.p90[i]) - 12, 90)}px`;
  };
  svg.addEventListener("pointermove", (e) => {
    const r = svg.getBoundingClientRect(), px = ((e.clientX - r.left) / r.width) * W;
    show(Math.max(0, Math.min(n - 1, Math.round(((px - m.l) / (W - m.l - m.r)) * (n - 1)))));
  });
  svg.addEventListener("pointerleave", () => show(null));
  svg.addEventListener("blur", () => show(null));
  svg.addEventListener("keydown", (e) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault();
    const cur = hover == null ? (wi >= 0 ? wi : 0) : hover + (e.key === "ArrowRight" ? 1 : -1);
    show(Math.max(0, Math.min(n - 1, cur)));
  });

  $("#fan-key").innerHTML = `
    <span><svg viewBox="0 0 22 12"><rect width="22" height="12" fill="#c4d8ef" stroke="#8fb4de"/></svg>Middle 80% of outcomes</span>
    <span><svg viewBox="0 0 22 12"><line x1="0" x2="22" y1="6" y2="6" stroke="#1f5fa8" stroke-width="2.5"/></svg>Middle outcome</span>
    <span><svg viewBox="0 0 22 12"><line x1="0" x2="22" y1="6" y2="6" stroke="#b42318" stroke-width="1.5" stroke-dasharray="5 3"/></svg>₹0, can't pay below this</span>
    <span><svg viewBox="0 0 22 12"><rect width="22" height="12" fill="url(#hatch)" stroke="#e8a29b"/></svg>Worst week</span>`;
}

function renderWeeks() {
  const ww = R.worst_week.week_start, t = R.risk_target;
  const rows = R.weeks.map((wk) => {
    const l = level(wk.p_shortfall), due = obligationsBetween(wk.week_start, 7);
    const worst = wk.week_start === ww;
    return `<tr class="${worst ? "worst" : ""}">
      <td>${day(wk.week_start)}${worst ? ' <span class="muted">· worst</span>' : ""}</td>
      <td class="muted">${due.map((o) => esc(o.label)).join(", ") || "–"}</td>
      <td><div class="dev" aria-hidden="true"><i style="width:${wk.p_shortfall * 100}%;background:var(--${l.k === "ok" ? "ok" : l.k === "watch" ? "watch" : "ng"})"></i><u style="left:${t * 100}%"></u></div></td>
      <td class="num"><b>${pct(wk.p_shortfall)}</b></td>
      <td class="num">${wk.expected_shortfall_inr ? inr(wk.expected_shortfall_inr) : "–"}</td>
      <td>${stamp(wk.p_shortfall)}</td></tr>`;
  }).join("");
  $("#weeks").innerHTML = `<h3>Week by week</h3>
    <p class="sub" style="margin-bottom:8px">Bar shows the chance of a shortfall in that week; the dashed line is the ${pct(t)} limit.</p>
    <div class="scroll"><table>
      <thead><tr><th scope="col">Week of</th><th scope="col">Payments due</th><th scope="col" style="width:28%">Shortfall risk</th><th scope="col" class="num">Risk</th><th scope="col" class="num">Expected gap</th><th scope="col">Check</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`;
}

/* ---------- 3. fixes ---------- */
function renderFixes() {
  const fixes = R.fixes || [], plan = R.plan;
  if (!fixes.length && !plan) {
    const ok = R.worst_week.p_shortfall <= R.risk_target;
    $("#fixes-body").innerHTML = `<div class="empty"><b>${ok ? "No fixes needed" : "No fixes available"}</b>
      <p class="muted">${ok ? "Every week is inside the risk limit." : "The engine returned no fixes for this scenario."}</p></div>`;
    return;
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
  $("#fixes-body").innerHTML = `${sum}<div class="scroll"><table>
    <thead><tr><th scope="col">Fix</th><th scope="col" class="num">Cost</th><th scope="col" class="num">Risk after</th><th scope="col">When</th><th scope="col"><span class="sr">In plan</span></th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}

/* ---------- 4. kab tak + order ---------- */
function renderKabTak() {
  const n = R.fan.dates.length;
  const buyers = (R.kab_tak || []).map((b) => {
    const d = b.max_delay_days, full = d >= n;
    return `<div class="buyer"><b>${esc(b.buyer)}</b>
      <div class="track" role="img" aria-label="${esc(b.buyer)} can pay up to ${d} days late"><i style="width:${(Math.min(d, n) / n) * 100}%;background:var(--blue)"></i></div>
      <span class="val">${full ? `${n}+ days late is fine` : `up to ${d} days late`}</span></div>`;
  }).join("");
  const axis = `<div class="axis" aria-hidden="true"><span></span><div><span>0 days</span><span>${Math.round(n / 2)}</span><span>${n} days</span></div><span></span></div>`;
  let order = "";
  const o = R.order;
  if (o) {
    const safe = Math.min(o.max_safe_terms_days, o.terms_days);
    const pAsk = o.max_safe_terms_days >= o.terms_days ? 0 : 1;
    order = `<div class="order" id="order-box">
      <h3>This order: ${esc(o.party)}, ${inr(o.amount_inr)} on ${o.terms_days}-day terms ${pAsk ? '<span class="stamp s-watch">Change terms</span>' : '<span class="stamp s-ok">OK as asked</span>'}</h3>
      <p class="answer">${esc(orderAnswer(o))}</p>
      <div>${bar([
        { label: "Safe terms", v: safe, c: "var(--ok)" },
        { label: "Unsafe", v: o.terms_days - safe, c: "var(--ng)" },
      ], o.terms_days, (v) => `${v} days`)}</div>
      <dl>
        <div><dt>Terms asked</dt><dd>${o.terms_days} days</dd></div>
        <div><dt>Longest safe terms</dt><dd>${o.max_safe_terms_days ? `${o.max_safe_terms_days} days` : "None"}</dd></div>
        <div><dt>Minimum advance</dt><dd>${o.min_advance_pct}%</dd></div>
        <div><dt>Margin on the order</dt><dd>${inr(o.margin_inr)}</dd></div>
      </dl></div>`;
  }
  $("#kabtak-body").innerHTML = `<div class="buyers">${buyers || '<p class="muted">No buyers in this result.</p>'}${buyers ? axis : ""}</div>${order}`;
}

function renderAssumptions() {
  $("#assume-body").innerHTML = `<div class="scroll"><table class="assume"><thead><tr><th scope="col">Assumption</th><th scope="col">Value</th></tr></thead><tbody>${(R.assumptions || [])
    .map((a) => `<tr><td>${esc(a.name)}</td><td>${esc(a.value)}</td></tr>`).join("")}</tbody></table></div>`;
}

function render(source) {
  renderHeader(source);
  renderVerdict();
  renderToday();
  renderWeeks();
  renderFixes();
  renderKabTak();
  renderAssumptions();
  if (document.body.dataset.view === "ca") renderFan();
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
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const s = scenario();
  const missing = FIELDS[s.type].filter((k) => s[k] == null);
  if (missing.length) return setStatus(`Fill in: ${missing.map((k) => LABEL[k]).join(", ")}.`, true);
  const btn = form.querySelector(".run");
  btn.disabled = true; setStatus("Running…");
  try {
    const res = await fetch("/api/answer", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(s) });
    const body = await res.json();
    if (!res.ok) return setStatus(body.error || "The engine could not answer.", true);
    R = body.result;
    render(body.source);
    setStatus(body.source === "engine" ? "Answered by the engine." : "Engine not available here, so this shows the saved fixture.");
  } catch {
    setStatus("Can't reach the server. Start it with python3 ui/server.py.", true);
  } finally { btn.disabled = false; }
});

/* ---------- view toggle ---------- */
function setView(v) {
  document.body.dataset.view = v;
  $(`#v-${v}`).checked = true;
  try { localStorage.setItem("kabtak-view", v); } catch {}
  if (R && v === "ca") renderFan();
}
document.querySelectorAll('input[name="view"]').forEach((r) => r.addEventListener("change", () => setView(r.value)));
let rz;
window.addEventListener("resize", () => { cancelAnimationFrame(rz); rz = requestAnimationFrame(() => R && document.body.dataset.view === "ca" && renderFan()); });

(async function init() {
  let v = new URLSearchParams(location.search).get("view");
  if (!v) try { v = localStorage.getItem("kabtak-view"); } catch {}
  setView(v === "ca" ? "ca" : "owner");
  try {
    const body = await (await fetch("/api/result")).json();
    R = body.result;
    $("#parties").innerHTML = [...new Set([...(R.kab_tak || []).map((b) => b.buyer), R.scenario && R.scenario.party].filter(Boolean))]
      .map((p) => `<option value="${esc(p)}">`).join("");
    prefill(R.scenario);
    render(body.source);
    setStatus("Showing the saved result. Change the question and run it.");
  } catch {
    setStatus("Can't reach the server. Start it with python3 ui/server.py.", true);
  }
})();
