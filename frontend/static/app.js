/* Day 10 Console - frontend logic (vanilla JS, khong dependency) */
"use strict";

const App = (() => {
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  const state = {
    tab: "dashboard",
    logOffset: 0,
    running: false,
    dataset: { columns: [], rows: [] },
    answers: [],
    polling: null,
  };

  // ------------------------------------------------------------ utils
  const esc = (v) =>
    String(v ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  const fmtNum = (v, digits = 3) => {
    if (v === null || v === undefined || v === "") return "-";
    if (typeof v !== "number") return esc(v);
    return Number.isInteger(v) ? String(v) : v.toFixed(digits);
  };

  const fmtSize = (n) => {
    if (!n) return "-";
    if (n < 1024) return n + " B";
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
    return (n / 1048576).toFixed(1) + " MB";
  };

  const api = async (path, opts) => {
    const res = await fetch(path, opts);
    if (!res.ok && res.status >= 500) {
      let msg = res.statusText;
      try { msg = (await res.json()).error || msg; } catch (_) {}
      throw new Error(msg);
    }
    return res.json();
  };

  const post = (path, body) =>
    api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });

  const setStatus = (text) => { $("#statusText").textContent = text; };

  // ------------------------------------------------------------ dialogs
  const dlg = (title, body) => {
    $("#modalTitle").textContent = title;
    $("#modalBody").innerHTML = esc(body).replace(/\n/g, "<br>");
    $("#modal").classList.add("show");
  };
  const closeDlg = () => $("#modal").classList.remove("show");

  const helpText = () =>
    "1. Chay 'Run Phase 1' de sinh baseline artifacts (raw -> clean -> embedding -> evaluation -> quality).\n" +
    "2. Sau khi baseline xong, chay 'Run Corruption Flow' de tao du lieu loi, repair va so sanh.\n" +
    "3. Tab Data Explorer xem du lieu clean/corrupted/repaired.\n" +
    "4. Tab Metrics so sanh retrieval_hit_rate, mean_token_f1, judge_accuracy giua ba trang thai.\n" +
    "5. Tab Reports doc phase1_report.md va corruption_report.md.\n\n" +
    "Luu y: pipeline chua implement se bao NotImplementedError - do la trang thai starter.";

  const teamText = () =>
    "Quan  - crossref.py\n" +
    "Duong  - cleaning.py, testset.py\n" +
    "Long  - quality.py, reporting.py\n" +
    "Phuong- corruption.py\n" +
    "Tung  - phase1.py, corruption_flow.py\n\n" +
    "Thu tu: raw -> clean + test set -> quality -> baseline -> corruption/repair -> so sanh -> bao cao";

  // ------------------------------------------------------------ tabs & menu
  const TABS = ["dashboard", "data", "quality", "metrics", "eval", "reports", "console", "config"];

  const openTab = (name) => {
    if (!TABS.includes(name)) name = "dashboard";
    state.tab = name;
    if (location.hash !== "#" + name) history.replaceState(null, "", "#" + name);
    $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
    $$(".page").forEach((p) => p.classList.toggle("active", p.id === "page-" + name));
    const loaders = {
      dashboard: loadStatus,
      data: loadDataset,
      quality: loadQuality,
      metrics: loadMetrics,
      eval: loadAnswers,
      reports: loadReport,
      config: loadConfig,
    };
    if (loaders[name]) loaders[name]();
  };

  const initMenu = () => {
    $$("[data-menu]").forEach((item) => {
      item.addEventListener("click", (ev) => {
        if (ev.target.closest(".menu-popup")) { $$("[data-menu]").forEach((m) => m.classList.remove("open")); return; }
        const wasOpen = item.classList.contains("open");
        $$("[data-menu]").forEach((m) => m.classList.remove("open"));
        if (!wasOpen) item.classList.add("open");
        ev.stopPropagation();
      });
    });
    document.addEventListener("click", () => $$("[data-menu]").forEach((m) => m.classList.remove("open")));
    $$(".tab").forEach((t) => t.addEventListener("click", () => openTab(t.dataset.tab)));
  };

  // ------------------------------------------------------------ dashboard
  const FLOW = [
    ["Crossref", "raw_records"],
    ["Raw", "raw_response"],
    ["Clean", "clean_csv"],
    ["Test set", "test_set"],
    ["Embedding", "embeddings"],
    ["Quality", "freshness"],
    ["Baseline", "baseline_metrics"],
    ["Corrupted", "corrupted_metrics"],
    ["Repaired", "repaired_metrics"],
    ["Report", "corruption_report"],
  ];

  async function loadStatus() {
    let data;
    try { data = await api("/api/status"); } catch (e) { setStatus("Loi doc trang thai: " + e.message); return; }

    const byKey = {};
    data.stages.forEach((s) => s.items.forEach((it) => (byKey[it.key] = it)));

    $("#flowDiagram").innerHTML = FLOW.map(([label, key], i) => {
      const ok = byKey[key] && byKey[key].exists;
      return (
        `<span class="badge ${ok ? "ok" : "miss"}" title="${esc(byKey[key] ? byKey[key].path : "")}">` +
        `<span class="led ${ok ? "on" : "off"}"></span>${esc(label)}</span>` +
        (i < FLOW.length - 1 ? '<span class="muted" style="margin:0 2px">&rarr;</span>' : "")
      );
    }).join("");

    const tbody = $("#artifactTable tbody");
    tbody.innerHTML = data.stages
      .map((stage) =>
        stage.items
          .map(
            (it, idx) =>
              `<tr><td>${idx === 0 ? esc(stage.stage) : ""}</td>` +
              `<td class="mono" title="${esc(it.path)}">${esc(it.label)}</td>` +
              `<td>${esc(it.owner)}</td>` +
              `<td><span class="badge ${it.exists ? "ok" : "miss"}">${it.exists ? "OK" : "thieu"}</span></td>` +
              `<td class="num">${fmtSize(it.size)}</td>` +
              `<td class="mono">${esc(it.modified || "-")}</td></tr>`
          )
          .join("")
      )
      .join("");

    const done = data.artifact_done, total = data.artifact_total;
    $("#artifactCount").textContent = `Artifact ${done}/${total}`;
    $("#statusArtifacts").textContent = `Artifacts: ${done}/${total}`;
    const blocks = Math.round((done / total) * 16);
    $("#artifactBar").innerHTML = Array.from({ length: blocks }, () => "<i></i>").join("");

    loadDashTiles();
  }

  async function loadDashTiles() {
    const data = await api("/api/metrics").catch(() => null);
    if (!data) return;
    const m = data.metrics;
    const keys = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"];
    if (!m.baseline && !m.corrupted && !m.repaired) {
      $("#dashTiles").innerHTML = '<span class="muted">Chua co metrics. Chay pipeline de sinh baseline_metrics.json.</span>';
      return;
    }
    $("#dashTiles").innerHTML = keys
      .map((k) => {
        const b = m.baseline ? m.baseline[k] : null;
        const c = m.corrupted ? m.corrupted[k] : null;
        const r = m.repaired ? m.repaired[k] : null;
        const d = typeof b === "number" && typeof c === "number" ? c - b : null;
        const cls = d === null ? "flat" : d > 0.0005 ? "up" : d < -0.0005 ? "down" : "flat";
        const sign = d === null ? "" : d > 0 ? "+" : "";
        return (
          `<div class="tile"><div class="k">${esc(k)}</div>` +
          `<div class="v">${fmtNum(b)}</div>` +
          `<div class="k">corrupted ${fmtNum(c)} <span class="delta ${cls}">${d === null ? "" : sign + d.toFixed(3)}</span></div>` +
          `<div class="k">repaired ${fmtNum(r)}</div></div>`
        );
      })
      .join("");
  }

  // ------------------------------------------------------------ data explorer
  async function loadDataset() {
    const name = $("#datasetSelect").value;
    const limit = $("#datasetLimit").value;
    const data = await api(`/api/dataset?name=${name}&limit=${limit}`).catch((e) => ({ error: e.message }));
    if (data.error) { $("#datasetInfo").textContent = data.error; return; }
    state.dataset = data;
    $("#datasetInfo").textContent = data.exists
      ? `${data.path} - ${data.total} dong, hien ${Math.min(data.rows.length, limit)}`
      : `${data.path} - chua ton tai`;
    $("#datasetTable thead").innerHTML =
      "<tr>" + (data.columns.length ? data.columns.map((c) => `<th>${esc(c)}</th>`).join("") : "<th>(trong)</th>") + "</tr>";
    renderDatasetRows();
  }

  function renderDatasetRows() {
    const q = ($("#datasetFilter").value || "").toLowerCase();
    const { columns, rows } = state.dataset;
    const body = $("#datasetTable tbody");
    if (!rows || !rows.length) {
      body.innerHTML = `<tr><td class="muted" colspan="${Math.max(columns.length, 1)}">Khong co du lieu. Chay pipeline truoc.</td></tr>`;
      $("#recordTable tbody").innerHTML = '<tr><td class="muted">Chon mot dong o bang tren.</td></tr>';
      return;
    }
    const pairs = rows.map((r, i) => [i, r]).filter(([, r]) => !q || r.join(" ").toLowerCase().includes(q));
    body.innerHTML = pairs
      .map(
        ([idx, r]) =>
          `<tr data-idx="${idx}">` + r.map((c) => `<td title="${esc(c)}">${esc(c)}</td>`).join("") + "</tr>"
      )
      .join("") || `<tr><td class="muted" colspan="${Math.max(columns.length, 1)}">Khong co dong nao khop bo loc.</td></tr>`;
    body.querySelectorAll("tr").forEach((tr) =>
      tr.addEventListener("click", () => {
        body.querySelectorAll("tr").forEach((x) => x.classList.remove("selected"));
        tr.classList.add("selected");
        showRecord(rows[Number(tr.dataset.idx)]);
      })
    );
  }

  function showRecord(row) {
    const cols = state.dataset.columns;
    $("#recordTable tbody").innerHTML = cols
      .map(
        (c, i) =>
          `<tr><td style="width:180px;font-weight:bold">${esc(c)}</td>` +
          `<td style="white-space:pre-wrap;max-width:none">${esc(row[i])}</td></tr>`
      )
      .join("");
  }

  // ------------------------------------------------------------ quality
  async function loadQuality() {
    const data = await api("/api/quality").catch((e) => ({ files: [], error: e.message }));

    const fresh = (data.files || []).find((f) => f.name.toLowerCase().includes("freshness"));
    if (fresh && fresh.content && !fresh.content.error) {
      const c = fresh.content;
      const tiles = Object.entries(c)
        .filter(([, v]) => typeof v !== "object")
        .map(([k, v]) => {
          const bad = (k === "is_fresh" && v === false) || (k === "stale_rows" && Number(v) > 0);
          return `<div class="tile"><div class="k">${esc(k)}</div><div class="v" style="${bad ? "color:var(--err)" : ""}">${esc(v)}</div></div>`;
        })
        .join("");
      $("#freshTiles").innerHTML = tiles || '<span class="muted">File freshness rong.</span>';
    } else {
      $("#freshTiles").innerHTML = '<span class="muted">Chua co data/quality/freshness_report.json.</span>';
    }

    const rows = [];
    (data.files || []).filter((f) => f !== fresh).forEach((f) => {
      const c = f.content;
      const push = (check, result, detail) => {
        const okish = /pass|true|ok|success/i.test(String(result));
        const badish = /fail|false|error/i.test(String(result));
        rows.push(
          `<tr><td class="mono" title="${esc(f.name)}">${esc(f.name)}</td><td>${esc(check)}</td>` +
            `<td><span class="badge ${okish ? "ok" : badish ? "miss" : ""}">${esc(result)}</span></td>` +
            `<td title="${esc(detail)}">${esc(detail)}</td></tr>`
        );
      };
      if (Array.isArray(c)) {
        c.forEach((item, i) =>
          typeof item === "object" && item
            ? push(item.check || item.name || item.expectation || `#${i}`, item.success ?? item.result ?? item.status ?? "-", JSON.stringify(item))
            : push(`#${i}`, "-", String(item))
        );
      } else if (c && typeof c === "object") {
        Object.entries(c).forEach(([k, v]) => {
          if (v && typeof v === "object") push(k, v.success ?? v.result ?? v.status ?? "-", JSON.stringify(v));
          else push(k, String(v), "");
        });
      }
    });
    $("#qualityTable tbody").innerHTML =
      rows.join("") || '<tr><td colspan="4" class="muted">Chua co file nao trong data/quality/.</td></tr>';

    const log = data.corruption_log;
    if (log && typeof log === "object") {
      const entries = Array.isArray(log) ? log.map((x, i) => [`#${i}`, x]) : Object.entries(log);
      $("#corruptionTable tbody").innerHTML = entries
        .map(
          ([k, v]) =>
            `<tr><td>${esc(k)}</td><td style="white-space:pre-wrap;max-width:none" class="mono">${esc(
              typeof v === "object" ? JSON.stringify(v, null, 1) : v
            )}</td></tr>`
        )
        .join("");
    } else {
      $("#corruptionTable tbody").innerHTML = '<tr><td colspan="2" class="muted">Chua co corruption_log.json.</td></tr>';
    }
  }

  // ------------------------------------------------------------ metrics
  const BAR_KEYS = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy"];

  async function loadMetrics() {
    const data = await api("/api/metrics").catch((e) => ({ metrics: {}, keys: [], error: e.message }));
    const m = data.metrics || {};
    const keys = data.keys || [];

    $("#metricsTable tbody").innerHTML = keys
      .map((k) => {
        const b = m.baseline ? m.baseline[k] : null;
        const c = m.corrupted ? m.corrupted[k] : null;
        const r = m.repaired ? m.repaired[k] : null;
        const delta = (x) => {
          if (typeof b !== "number" || typeof x !== "number") return '<td class="num muted">-</td>';
          const d = x - b;
          const cls = d > 0.0005 ? "up" : d < -0.0005 ? "down" : "flat";
          const arrow = d > 0.0005 ? "▲" : d < -0.0005 ? "▼" : "=";
          return `<td class="num delta ${cls}">${arrow} ${d >= 0 ? "+" : ""}${d.toFixed(3)}</td>`;
        };
        return (
          `<tr><td>${esc(k)}</td><td class="num">${fmtNum(b)}</td><td class="num">${fmtNum(c)}</td>` +
          `<td class="num">${fmtNum(r)}</td>${delta(c)}${delta(r)}</tr>`
        );
      })
      .join("") || '<tr><td colspan="6" class="muted">Chua co metrics.</td></tr>';

    // bieu do cot ASCII kieu Windows Forms
    const states = [["baseline", m.baseline], ["corrupted", m.corrupted], ["repaired", m.repaired]];
    const chart = BAR_KEYS.map((k) => {
      const lines = states
        .map(([name, v]) => {
          const val = v && typeof v[k] === "number" ? v[k] : null;
          const width = val === null ? 0 : Math.round(Math.max(0, Math.min(1, val)) * 40);
          const color = name === "corrupted" ? "#a00000" : name === "repaired" ? "#008000" : "#0a246a";
          return (
            `<div class="row tight"><span style="width:78px" class="muted">${name}</span>` +
            `<span style="display:inline-block;height:11px;width:${width * 6}px;background:${color};border:1px solid #404040"></span>` +
            `<span>${val === null ? "-" : val.toFixed(3)}</span></div>`
          );
        })
        .join("");
      return `<div style="margin-bottom:10px"><b>${esc(k)}</b>${lines}</div>`;
    }).join("");
    $("#metricChart").innerHTML = chart;

    const ragas = m.baseline && m.baseline.ragas ? m.baseline.ragas : null;
    $("#ragasBox").textContent = ragas ? JSON.stringify(ragas, null, 2) : "Chua co du lieu Ragas (dat RUN_RAGAS=1 de bat).";
  }

  // ------------------------------------------------------------ evaluation
  async function loadAnswers() {
    const src = $("#answerState").value;
    const url = src === "testset" ? "/api/testset" : `/api/answers?state=${src}`;
    const data = await api(url).catch((e) => ({ items: [], error: e.message }));
    const items = data.items || [];
    state.answers = items;
    $("#answerInfo").textContent = data.exists === false ? "File chua ton tai." : `${items.length} muc`;

    const body = $("#answerTable tbody");
    if (!items.length) {
      body.innerHTML = '<tr><td colspan="4" class="muted">Chua co du lieu.</td></tr>';
      $("#answerDetail tbody").innerHTML = '<tr><td class="muted">Chon mot cau hoi.</td></tr>';
      return;
    }
    body.innerHTML = items
      .map((it, i) => {
        const hit = it.retrieval_hit;
        const badge = hit === undefined ? "-" : hit ? '<span class="badge ok">Y</span>' : '<span class="badge miss">N</span>';
        return (
          `<tr data-idx="${i}"><td>${esc(it.id ?? i)}</td><td>${esc(it.question_type || "-")}</td>` +
          `<td title="${esc(it.question)}">${esc(it.question)}</td><td>${badge}</td></tr>`
        );
      })
      .join("");
    body.querySelectorAll("tr").forEach((tr) =>
      tr.addEventListener("click", () => {
        body.querySelectorAll("tr").forEach((x) => x.classList.remove("selected"));
        tr.classList.add("selected");
        showAnswer(items[Number(tr.dataset.idx)]);
      })
    );
  }

  function showAnswer(item) {
    const rows = Object.entries(item).map(([k, v]) => {
      const text = typeof v === "object" && v !== null ? JSON.stringify(v, null, 1) : String(v);
      return (
        `<tr><td style="width:150px;font-weight:bold;vertical-align:top">${esc(k)}</td>` +
        `<td style="white-space:pre-wrap;max-width:none">${esc(text)}</td></tr>`
      );
    });
    $("#answerDetail tbody").innerHTML = rows.join("");
  }

  // ------------------------------------------------------------ reports
  async function loadReport() {
    const name = $("#reportSelect").value;
    const data = await api(`/api/report?name=${name}`).catch((e) => ({ error: e.message }));
    if (data.error) { $("#reportView").innerHTML = `<p class="muted">${esc(data.error)}</p>`; return; }
    $("#reportInfo").textContent = data.exists ? `${data.path} - cap nhat ${data.modified}` : `${data.path} - chua ton tai`;
    $("#reportView").innerHTML = data.exists
      ? renderMarkdown(data.content)
      : '<p class="muted">Bao cao chua duoc sinh. Chay pipeline tuong ung truoc.</p>';
  }

  function renderMarkdown(md) {
    const lines = md.split(/\r?\n/);
    const out = [];
    let inCode = false, inList = false, tableBuf = [];

    const flushTable = () => {
      if (!tableBuf.length) return;
      const rows = tableBuf.filter((r) => !/^\s*\|?[\s:|-]+\|?\s*$/.test(r) || r.replace(/[^|]/g, "").length === 0);
      const cells = rows.map((r) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim()));
      if (cells.length) {
        out.push("<table><thead><tr>" + cells[0].map((c) => `<th>${inline(c)}</th>`).join("") + "</tr></thead><tbody>");
        cells.slice(1).forEach((r) => out.push("<tr>" + r.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>"));
        out.push("</tbody></table>");
      }
      tableBuf = [];
    };
    const closeList = () => { if (inList) { out.push("</ul>"); inList = false; } };

    const inline = (t) =>
      esc(t)
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
        .replace(/(^|[^*])\*([^*]+)\*/g, "$1<i>$2</i>");

    for (const raw of lines) {
      const line = raw.replace(/\s+$/, "");
      if (/^```/.test(line)) {
        flushTable(); closeList();
        out.push(inCode ? "</pre>" : "<pre>");
        inCode = !inCode;
        continue;
      }
      if (inCode) { out.push(esc(raw)); continue; }
      if (/^\s*\|.*\|\s*$/.test(line)) { closeList(); tableBuf.push(line); continue; }
      flushTable();
      if (/^#{1,6}\s/.test(line)) {
        closeList();
        const level = line.match(/^#+/)[0].length;
        out.push(`<h${level}>${inline(line.replace(/^#+\s*/, ""))}</h${level}>`);
      } else if (/^\s*[-*+]\s+/.test(line)) {
        if (!inList) { out.push("<ul>"); inList = true; }
        out.push(`<li>${inline(line.replace(/^\s*[-*+]\s+/, ""))}</li>`);
      } else if (/^\s*$/.test(line)) {
        closeList();
      } else if (/^---+$/.test(line)) {
        closeList(); out.push("<hr>");
      } else {
        closeList(); out.push(`<p>${inline(line)}</p>`);
      }
    }
    flushTable(); closeList();
    if (inCode) out.push("</pre>");
    return out.join("\n");
  }

  // ------------------------------------------------------------ config
  async function loadConfig() {
    const data = await api("/api/config").catch((e) => ({ env: [], error: e.message }));
    const py = data.python || {};
    const rows = [
      `<tr><td style="width:200px;font-weight:bold">Project root</td><td class="mono">${esc(data.root || "-")}</td></tr>`,
      `<tr><td style="font-weight:bold">Python interpreter</td><td class="mono">${esc(py.exe || "-")}</td></tr>`,
      `<tr><td style="font-weight:bold">Python version</td><td class="mono">${esc(py.version || "-")} ` +
        `<span class="badge ${py.ok ? "ok" : "miss"}">${py.ok ? "OK" : "canh bao"}</span> ` +
        `<span class="muted">${esc(py.note || "")}</span></td></tr>`,
      `<tr><td style="font-weight:bold">Virtualenv</td><td class="mono">${py.venv ? esc(py.venv) + "/" : "chua tao"}</td></tr>`,
    ];
    if (py.ok === false) setStatus("Canh bao: " + (py.note || "Python khong dung phien ban yeu cau."));
    (data.env || []).forEach((e) => {
      const label = e.key === "__source__" ? "Nguon cau hinh" : e.key;
      rows.push(`<tr><td style="font-weight:bold">${esc(label)}</td><td class="mono">${esc(e.value)}</td></tr>`);
    });
    $("#configTable tbody").innerHTML = rows.join("");
  }

  // ------------------------------------------------------------ pipeline run
  async function run(pipeline) {
    setStatus(`Dang khoi dong pipeline '${pipeline}'...`);
    const res = await post("/api/run", { pipeline }).catch((e) => ({ ok: false, error: e.message }));
    if (!res.ok) { dlg("Khong chay duoc", res.error || "Loi khong xac dinh"); setStatus("San sang"); return; }
    state.logOffset = 0;
    $("#consoleView").textContent = "";
    openTab("console");
    setStatus(`Pipeline '${pipeline}' dang chay...`);
  }

  async function stop() {
    const res = await post("/api/run/stop").catch((e) => ({ ok: false, error: e.message }));
    if (!res.ok) dlg("Stop", res.error || "Khong co gi de dung.");
  }

  async function clearLog() {
    const res = await post("/api/run/clear").catch((e) => ({ ok: false, error: e.message }));
    if (!res.ok) { dlg("Clear", res.error); return; }
    state.logOffset = 0;
    $("#consoleView").textContent = "";
  }

  function appendLog(lines) {
    if (!lines.length) return;
    const view = $("#consoleView");
    if (view.dataset.placeholder === "1") { view.textContent = ""; delete view.dataset.placeholder; }
    const frag = document.createDocumentFragment();
    lines.forEach((line) => {
      const span = document.createElement("span");
      if (/error|traceback|exception|fail|NotImplemented/i.test(line)) span.className = "err";
      else if (/^\s*(ok|done|saved|wrote|hoan tat)/i.test(line) || /exit code = 0/.test(line)) span.className = "ok";
      else if (line.startsWith(">")) span.className = "cmd";
      span.textContent = line + "\n";
      frag.appendChild(span);
    });
    view.appendChild(frag);
    if ($("#autoScroll").checked) view.scrollTop = view.scrollHeight;
  }

  async function pollRun() {
    let st;
    try { st = await api(`/api/run?offset=${state.logOffset}`); } catch (_) { return; }
    state.logOffset = st.offset;
    appendLog(st.lines || []);

    const wasRunning = state.running;
    state.running = st.running;
    $("#btnPhase1").disabled = st.running;
    $("#btnCorrupt").disabled = st.running;
    $("#btnStop").disabled = !st.running;
    $("#runState").innerHTML = st.running
      ? `<span class="led on"></span>Dang chay: ${esc(st.pipeline)}`
      : st.exit_code === null || st.exit_code === undefined
      ? '<span class="led off"></span>Idle'
      : st.exit_code === 0
      ? '<span class="led on"></span>Hoan tat (0)'
      : `<span class="led bad"></span>Error (exit ${st.exit_code})`;
    $("#statusPipeline").textContent = st.pipeline
      ? `Pipeline: ${st.pipeline}${st.running ? " (running)" : ` (exit ${st.exit_code})`}`
      : "Pipeline: idle";
    $("#consoleInfo").textContent = st.pipeline
      ? `${st.pipeline} - bat dau ${st.started_at || "-"}${st.running ? "" : ` - exit ${st.exit_code}`}`
      : "Chua chay lan nao.";

    if (wasRunning && !st.running) {
      setStatus(st.exit_code === 0 ? "Pipeline hoan tat." : `Pipeline ket thuc voi exit code ${st.exit_code}.`);
      refreshAll();
    }
  }

  // ------------------------------------------------------------ refresh
  function refreshAll() {
    loadStatus();
    const loaders = { data: loadDataset, quality: loadQuality, metrics: loadMetrics, eval: loadAnswers, reports: loadReport, config: loadConfig };
    if (loaders[state.tab]) loaders[state.tab]();
    setStatus("Da lam moi luc " + new Date().toLocaleTimeString());
  }

  // ------------------------------------------------------------ init
  function init() {
    initMenu();
    openTab((location.hash || "#dashboard").slice(1));
    loadStatus();
    loadConfig();
    setInterval(() => { $("#statusClock").textContent = new Date().toLocaleTimeString(); }, 1000);
    setInterval(pollRun, 1000);
    setInterval(() => { if (!state.running) loadStatus(); }, 15000);
    pollRun();

    document.addEventListener("keydown", (ev) => {
      if (ev.key === "F5" && !ev.shiftKey) { ev.preventDefault(); refreshAll(); }
      else if (ev.key === "F5" && ev.shiftKey) { ev.preventDefault(); stop(); }
      else if (ev.key === "F9") { ev.preventDefault(); run("phase1"); }
      else if (ev.key === "F10") { ev.preventDefault(); run("corruption"); }
      else if (ev.key === "F1") { ev.preventDefault(); dlg("Huong dan nhanh", helpText()); }
      else if (ev.key === "Escape") closeDlg();
      else if (ev.ctrlKey && /^[1-7]$/.test(ev.key)) {
        ev.preventDefault();
        openTab(["dashboard", "data", "quality", "metrics", "eval", "reports", "console"][Number(ev.key) - 1]);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", init);

  return { openTab, run, stop, clearLog, refreshAll, loadDataset, renderDatasetRows, loadQuality, loadMetrics, loadAnswers, loadReport, loadConfig, dlg, closeDlg, helpText, teamText };
})();
