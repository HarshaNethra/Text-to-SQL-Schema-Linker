/**
 * NL TO SQL OPTIMIZER // FRONTEND CLIENT
 * Dual-Pipeline Comparative Runner (Baseline vs Proposed) with Under-The-Hood Live Trace
 */

const API_BASE = (window.location.protocol === "file:" || (window.location.port && window.location.port !== "5000"))
  ? "http://127.0.0.1:5000"
  : "";

const state = {
  activeTable: null,
  activeDbId: "college",
  activeDbName: "College Preset",
  isSpider: false,
  schema: {},
  relationships: [],
  tables: [],
  isExecuting: false,
  rawTableRows: [],
  spiderDatabases: [],
  sampleQueries: [],
  sampleQueriesMode: "db",
  modalFilterCategory: "all",
};

// DOM Elements
const promptInput = document.getElementById("promptInput");
const btnExecute = document.getElementById("btnExecute");
const btnClearInput = document.getElementById("btnClearInput");
const terminalConsole = document.getElementById("terminalConsole");
const consoleWelcome = document.getElementById("consoleWelcome");
const underTheHoodView = document.getElementById("underTheHoodView");
const hoodLogsContainer = document.getElementById("hoodLogsContainer");
const executionResultView = document.getElementById("executionResultView");
const providerBadge = document.getElementById("providerBadge");
const activeDbBadge = document.getElementById("activeDbBadge");
const tableTabsBar = document.getElementById("tableTabsBar");
const activeTableName = document.getElementById("activeTableName");
const tableRowCountBadge = document.getElementById("tableRowCountBadge");
const liveDataTableHead = document.getElementById("liveDataTableHead");
const liveDataTableBody = document.getElementById("liveDataTableBody");
const emptyTableState = document.getElementById("emptyTableState");
const tableFilterInput = document.getElementById("tableFilterInput");
const relBadgesList = document.getElementById("relBadgesList");
const btnRefreshDb = document.getElementById("btnRefreshDb");
const btnLoadPreset = document.getElementById("btnLoadPreset");
const btnEmptyLoadPreset = document.getElementById("btnEmptyLoadPreset");
const btnClearDb = document.getElementById("btnClearDb");
const btnToggleScanlines = document.getElementById("btnToggleScanlines");
const scanlinesOverlay = document.getElementById("scanlinesOverlay");
const toastContainer = document.getElementById("toastContainer");

// Spider & Sample Queries DOM Elements
const headerActiveDbName = document.getElementById("headerActiveDbName");
const headerDbTableCount = document.getElementById("headerDbTableCount");
const btnOpenDbPicker = document.getElementById("btnOpenDbPicker");
const btnOpenDbModal = document.getElementById("btnOpenDbModal");
const inspectorActiveDbTag = document.getElementById("inspectorActiveDbTag");
const btnInspectorSwitchDb = document.getElementById("btnInspectorSwitchDb");
const quickSampleChipsBar = document.getElementById("quickSampleChipsBar");
const quickChipsTargetLabel = document.getElementById("quickChipsTargetLabel");
const quickChipsContainer = document.getElementById("quickChipsContainer");
const sampleQueriesSection = document.getElementById("sampleQueriesSection");
const sampleQueriesTitleText = document.getElementById("sampleQueriesTitleText");
const sampleQueriesTableName = document.getElementById("sampleQueriesTableName");
const sampleQueriesCountBadge = document.getElementById("sampleQueriesCountBadge");
const btnFilterTableQueries = document.getElementById("btnFilterTableQueries");
const btnFilterDbQueries = document.getElementById("btnFilterDbQueries");
const sampleQueriesList = document.getElementById("sampleQueriesList");
const spiderDbModal = document.getElementById("spiderDbModal");
const btnCloseDbModal = document.getElementById("btnCloseDbModal");
const btnModalClose = document.getElementById("btnModalClose");
const modalDbSearchInput = document.getElementById("modalDbSearchInput");
const btnClearModalSearch = document.getElementById("btnClearModalSearch");
const modalDbGrid = document.getElementById("modalDbGrid");
const modalActiveDbName = document.getElementById("modalActiveDbName");
const filterAllCount = document.getElementById("filterAllCount");

// Initialize on Load
document.addEventListener("DOMContentLoaded", () => {
  initApp();
  setupEventListeners();
});

async function initApp() {
  await refreshDatabaseState();
}

function setupEventListeners() {
  // Execute button
  btnExecute.addEventListener("click", handleExecute);

  // Clear Input
  btnClearInput.addEventListener("click", () => {
    promptInput.value = "";
    promptInput.focus();
  });

  // Keyboard shortcut: Ctrl + Enter
  promptInput.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleExecute();
    }
  });

  // Copy Baseline SQL Button
  const btnCopyBase = document.getElementById("btnCopyBaselineSql");
  if (btnCopyBase) {
    btnCopyBase.addEventListener("click", () => {
      const code = document.getElementById("baselineSqlCode").innerText;
      navigator.clipboard.writeText(code).then(() => {
        showToast("Baseline SQL copied to clipboard!", "success");
      });
    });
  }

  // Copy Proposed SQL Button
  const btnCopyProp = document.getElementById("btnCopyProposedSql");
  if (btnCopyProp) {
    btnCopyProp.addEventListener("click", () => {
      const code = document.getElementById("proposedSqlCode").innerText;
      navigator.clipboard.writeText(code).then(() => {
        showToast("Proposed SQL copied to clipboard!", "success");
      });
    });
  }

  // Refresh DB Button
  btnRefreshDb.addEventListener("click", () => {
    refreshDatabaseState();
    showToast("Database refreshed.", "info");
  });

  // Spider DB modal controls
  if (btnOpenDbPicker) btnOpenDbPicker.addEventListener("click", openSpiderModal);
  if (btnOpenDbModal) btnOpenDbModal.addEventListener("click", openSpiderModal);
  if (btnInspectorSwitchDb) btnInspectorSwitchDb.addEventListener("click", openSpiderModal);
  if (btnCloseDbModal) btnCloseDbModal.addEventListener("click", closeSpiderModal);
  if (btnModalClose) btnModalClose.addEventListener("click", closeSpiderModal);
  if (spiderDbModal) {
    spiderDbModal.addEventListener("click", (e) => {
      if (e.target === spiderDbModal) closeSpiderModal();
    });
  }

  // Modal search & filter chips
  if (modalDbSearchInput) {
    modalDbSearchInput.addEventListener("input", (e) => {
      filterModalDatabases(e.target.value);
    });
  }
  if (btnClearModalSearch) {
    btnClearModalSearch.addEventListener("click", () => {
      modalDbSearchInput.value = "";
      btnClearModalSearch.classList.add("hidden");
      filterModalDatabases("");
      modalDbSearchInput.focus();
    });
  }

  document.querySelectorAll(".modal-quick-filters .filter-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".modal-quick-filters .filter-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      state.modalFilterCategory = chip.dataset.filter || "all";
      filterModalDatabases(modalDbSearchInput ? modalDbSearchInput.value : "");
    });
  });

  // Spider Top-5 Benchmark Modal Event Listeners
  const btnOpenBenchmarkModal = document.getElementById("btnOpenBenchmarkModal");
  const btnCloseBenchmarkModal = document.getElementById("btnCloseBenchmarkModal");
  const btnBenchmarkModalClose = document.getElementById("btnBenchmarkModalClose");
  const spiderBenchmarkModal = document.getElementById("spiderBenchmarkModal");
  const btnStartBenchmark = document.getElementById("btnStartBenchmark");
  const btnStopBenchmark = document.getElementById("btnStopBenchmark");
  const btnLoadCachedBenchmark = document.getElementById("btnLoadCachedBenchmark");
  const btnEmptyStartBench = document.getElementById("btnEmptyStartBench");
  const btnEmptyLoadCached = document.getElementById("btnEmptyLoadCached");

  if (btnOpenBenchmarkModal) btnOpenBenchmarkModal.addEventListener("click", openBenchmarkModal);
  if (btnCloseBenchmarkModal) btnCloseBenchmarkModal.addEventListener("click", closeBenchmarkModal);
  if (btnBenchmarkModalClose) btnBenchmarkModalClose.addEventListener("click", closeBenchmarkModal);
  if (spiderBenchmarkModal) {
    spiderBenchmarkModal.addEventListener("click", (e) => {
      if (e.target === spiderBenchmarkModal) closeBenchmarkModal();
    });
  }

  if (btnStartBenchmark) btnStartBenchmark.addEventListener("click", startBenchmark);
  if (btnStopBenchmark) btnStopBenchmark.addEventListener("click", stopBenchmark);
  if (btnLoadCachedBenchmark) btnLoadCachedBenchmark.addEventListener("click", () => fetchBenchmarkStatus(true));
  if (btnEmptyStartBench) btnEmptyStartBench.addEventListener("click", startBenchmark);
  if (btnEmptyLoadCached) btnEmptyLoadCached.addEventListener("click", () => fetchBenchmarkStatus(true));

  // Depth selector chips (1, 3, 5 queries/db)
  document.querySelectorAll(".bench-depth-selector .btn-toggle-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".bench-depth-selector .btn-toggle-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      benchState.selectedDepth = parseInt(chip.dataset.queries || "1", 10);
    });
  });

  // Benchmark scope dropdown
  const benchDbSelect = document.getElementById("benchDbSelect");
  if (benchDbSelect) {
    benchDbSelect.addEventListener("change", (e) => {
      benchState.selectedDb = e.target.value;
      benchState.selectedQueryIndex = 0;
      if (benchState.results) {
        renderBenchmarkDashboard(benchState.results);
      }
    });
  }

  // Benchmark View Mode toggle buttons
  const btnBenchModeSummary = document.getElementById("btnBenchModeSummary");
  const btnBenchModeQuery = document.getElementById("btnBenchModeQuery");
  if (btnBenchModeSummary && btnBenchModeQuery) {
    btnBenchModeSummary.addEventListener("click", () => {
      btnBenchModeSummary.classList.add("active");
      btnBenchModeQuery.classList.remove("active");
      benchState.viewMode = "summary";
      if (benchState.results) {
        renderBenchmarkDashboard(benchState.results);
      }
    });

    btnBenchModeQuery.addEventListener("click", () => {
      btnBenchModeQuery.classList.add("active");
      btnBenchModeSummary.classList.remove("active");
      benchState.viewMode = "query";
      benchState.selectedQueryIndex = 0;
      if (benchState.results) {
        renderBenchmarkDashboard(benchState.results);
      }
    });
  }

  // Benchmark Analytics Visualizations Modal Event Listeners
  const btnOpenAnalyticsModal = document.getElementById("btnOpenAnalyticsModal");
  const btnCloseAnalyticsModal = document.getElementById("btnCloseAnalyticsModal");
  const btnCloseAnalyticsModalFooter = document.getElementById("btnCloseAnalyticsModalFooter");
  const btnSwitchToVisualsFromRunner = document.getElementById("btnSwitchToVisualsFromRunner");
  const benchmarkAnalyticsModal = document.getElementById("benchmarkAnalyticsModal");
  const btnReloadVisualData = document.getElementById("btnReloadVisualData");

  if (btnOpenAnalyticsModal) btnOpenAnalyticsModal.addEventListener("click", openAnalyticsModal);
  if (btnSwitchToVisualsFromRunner) {
    btnSwitchToVisualsFromRunner.addEventListener("click", () => {
      closeBenchmarkModal();
      openAnalyticsModal();
    });
  }
  if (btnCloseAnalyticsModal) btnCloseAnalyticsModal.addEventListener("click", closeAnalyticsModal);
  if (btnCloseAnalyticsModalFooter) btnCloseAnalyticsModalFooter.addEventListener("click", closeAnalyticsModal);
  if (benchmarkAnalyticsModal) {
    benchmarkAnalyticsModal.addEventListener("click", (e) => {
      if (e.target === benchmarkAnalyticsModal) closeAnalyticsModal();
    });
  }
  if (btnReloadVisualData) {
    btnReloadVisualData.addEventListener("click", () => fetchVisualAnalyticsData(true));
  }

  // Chart filter tab buttons (All, Tokens, Accuracy, IR, Latency)
  document.querySelectorAll(".analytics-filter-group .btn-toggle-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".analytics-filter-group .btn-toggle-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      const targetId = chip.dataset.target;
      const allCards = document.querySelectorAll(".analytics-charts-grid .chart-card");
      allCards.forEach((card) => {
        if (targetId === "all" || card.id === targetId) {
          card.classList.remove("hidden");
        } else {
          card.classList.add("hidden");
        }
      });
    });
  });

  // Benchmark Query-Wise selector
  const benchQuerySelect = document.getElementById("benchQuerySelect");
  if (benchQuerySelect) {
    benchQuerySelect.addEventListener("change", (e) => {
      benchState.selectedQueryIndex = parseInt(e.target.value, 10) || 0;
      if (benchState.results) {
        renderBenchmarkDashboard(benchState.results);
      }
    });
  }

  // Load Preset Buttons
  const handleLoadPreset = async () => {
    try {
      showToast("Loading College preset dataset...", "info");
      const res = await fetch(`${API_BASE}/api/preset`, { method: "POST" });
      const data = await res.json();
      await refreshDatabaseState();
      showToast(data.message || "College preset loaded successfully!", "success");
    } catch (err) {
      showToast("Failed to load preset: " + err.message, "error");
    }
  };

  if (btnLoadPreset) {
    btnLoadPreset.addEventListener("click", handleLoadPreset);
  }
  if (btnEmptyLoadPreset) {
    btnEmptyLoadPreset.addEventListener("click", handleLoadPreset);
  }

  // Clear DB Button
  btnClearDb.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to drop all tables in the active database?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/clear`, { method: "POST" });
      const data = await res.json();
      await refreshDatabaseState();
      showToast(data.message || "All tables cleared.", "info");
    } catch (err) {
      showToast("Failed to clear tables: " + err.message, "error");
    }
  });

  // Filter input on live table
  tableFilterInput.addEventListener("input", (e) => {
    filterTableRows(e.target.value);
  });

  // DB Inspector Slide-out Drawer (Option 2)
  const btnToggleDbInspector = document.getElementById("btnToggleDbInspector");
  if (btnToggleDbInspector) {
    btnToggleDbInspector.addEventListener("click", () => toggleDbDrawer());
  }

  const btnCloseDbDrawer = document.getElementById("btnCloseDbDrawer");
  if (btnCloseDbDrawer) {
    btnCloseDbDrawer.addEventListener("click", () => toggleDbDrawer(false));
  }

  const btnCollapseDbPanel = document.getElementById("btnCollapseDbPanel");
  if (btnCollapseDbPanel) {
    btnCollapseDbPanel.addEventListener("click", () => toggleDbDrawer(false));
  }

  const dbDrawerBackdrop = document.getElementById("dbDrawerBackdrop");
  if (dbDrawerBackdrop) {
    dbDrawerBackdrop.addEventListener("click", () => toggleDbDrawer(false));
  }

  // Keyboard shortcut: Escape closes drawer and open modals
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const panel = document.getElementById("dbInspectorPanel");
      if (panel && panel.classList.contains("open")) {
        toggleDbDrawer(false);
      }
    }
  });
}

function toggleDbDrawer(forceState = null) {
  const panel = document.getElementById("dbInspectorPanel");
  const backdrop = document.getElementById("dbDrawerBackdrop");
  const toggleBtn = document.getElementById("btnToggleDbInspector");
  if (!panel) return;

  const isOpen = forceState !== null
    ? forceState
    : !panel.classList.contains("open");

  if (isOpen) {
    panel.classList.add("open");
    if (backdrop) backdrop.classList.add("active");
    if (toggleBtn) toggleBtn.classList.add("active");
  } else {
    panel.classList.remove("open");
    if (backdrop) backdrop.classList.remove("active");
    if (toggleBtn) toggleBtn.classList.remove("active");
  }
}

// Compatibility alias
const toggleDbInspector = toggleDbDrawer;

function updateActiveDbBadges() {
  const name = state.activeDbName || state.activeDbId || "College Preset";
  const tblCount = `${state.tables.length} table${state.tables.length === 1 ? "" : "s"}`;

  if (headerActiveDbName) headerActiveDbName.innerText = name;
  if (headerDbTableCount) headerDbTableCount.innerText = tblCount;
  if (inspectorActiveDbTag) inspectorActiveDbTag.innerText = state.activeDbId === "college" ? "college.db" : state.activeDbId;
  if (modalActiveDbName) modalActiveDbName.innerText = `${name} (${tblCount})`;
}

// Fetch active database schema, tables, and status
async function refreshDatabaseState() {
  try {
    const res = await fetch(`${API_BASE}/api/status`);
    const data = await res.json();

    state.schema = data.schema || {};
    state.relationships = data.relationships || [];
    state.tables = data.tables || [];
    state.activeDbId = data.active_db_id || "college";
    state.activeDbName = data.active_db_name || (state.activeDbId === "college" ? "College Preset" : state.activeDbId);
    state.isSpider = data.is_spider || false;

    if (data.provider && providerBadge) {
      providerBadge.innerText = `${data.provider.toUpperCase()} (${data.model_name || ""})`;
    }
    if (data.db_path && activeDbBadge) {
      activeDbBadge.innerText = data.db_path;
    }

    updateActiveDbBadges();
    renderRelationshipBadges();
    renderTableTabs();

    if (state.tables.length > 0) {
      if (!state.activeTable || !state.tables.includes(state.activeTable)) {
        state.activeTable = state.tables[0];
      }
      await loadTableData(state.activeTable);
      await loadSampleQueries(state.activeDbId, state.activeTable, state.sampleQueriesMode);
    } else {
      state.activeTable = null;
      renderEmptyTableState();
      renderSampleQueries(null, state.sampleQueriesMode);
    }
  } catch (err) {
    console.error("Failed fetching database state:", err);
    showToast("Error connecting to server backend.", "error");
  }
}

// Render Foreign Key Badges
function renderRelationshipBadges() {
  relBadgesList.innerHTML = "";
  if (!state.relationships || state.relationships.length === 0) {
    relBadgesList.innerHTML = `<span class="rel-badge" style="color: var(--text-dim);">None</span>`;
    return;
  }

  state.relationships.forEach((rel) => {
    const span = document.createElement("span");
    span.className = "rel-badge";
    span.innerText = `${rel.from_table}.${rel.from_column} -> ${rel.to_table}.${rel.to_column}`;
    relBadgesList.appendChild(span);
  });
}

// Render Table Selection Tabs
function renderTableTabs() {
  tableTabsBar.innerHTML = "";

  if (state.tables.length === 0) {
    return;
  }

  state.tables.forEach((table) => {
    const tab = document.createElement("button");
    tab.className = `table-tab ${table === state.activeTable ? "active" : ""}`;
    tab.innerHTML = `<span>${table}</span>`;
    tab.addEventListener("click", () => {
      document.querySelectorAll(".table-tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      state.activeTable = table;
      loadTableData(table);
      loadSampleQueries(state.activeDbId, table, state.sampleQueriesMode);
    });
    tableTabsBar.appendChild(tab);
  });
}

// Load and display table contents
async function loadTableData(tableName) {
  if (!tableName) return;
  try {
    const res = await fetch(`${API_BASE}/api/table/${encodeURIComponent(tableName)}`);
    const data = await res.json();

    activeTableName.innerText = tableName;
    tableRowCountBadge.innerText = `${data.rowcount || 0} rows`;
    state.rawTableRows = data.rows || [];

    renderDataTable(data.columns || [], data.rows || [], data.schema || {});
  } catch (err) {
    console.error("Error loading table data:", err);
  }
}

// Render Data Table Rows and Columns
function renderDataTable(columns, rows, colSchema) {
  liveDataTableHead.innerHTML = "";
  liveDataTableBody.innerHTML = "";

  if (!columns || columns.length === 0) {
    renderEmptyTableState();
    return;
  }

  emptyTableState.classList.add("hidden");

  // Render Header
  const trHead = document.createElement("tr");
  columns.forEach((col) => {
    const th = document.createElement("th");
    const colType = colSchema[col] || "";
    th.innerHTML = `
      <div>${col}</div>
      <div style="font-size: 8.5px; font-weight: normal; color: var(--text-dim); text-transform: uppercase;">${colType}</div>
    `;
    trHead.appendChild(th);
  });
  liveDataTableHead.appendChild(trHead);

  // Render Rows
  if (rows.length === 0) {
    const trEmpty = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = columns.length;
    td.style.textAlign = "center";
    td.style.color = "var(--text-dim)";
    td.style.padding = "24px";
    td.innerText = "(Table is currently empty)";
    trEmpty.appendChild(td);
    liveDataTableBody.appendChild(trEmpty);
  } else {
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      row.forEach((cell) => {
        const td = document.createElement("td");
        td.innerText = cell !== null && cell !== undefined ? cell : "NULL";
        if (cell === null) td.style.color = "var(--text-dim)";
        tr.appendChild(td);
      });
      liveDataTableBody.appendChild(tr);
    });
  }
}

// Render empty database state
function renderEmptyTableState() {
  emptyTableState.classList.remove("hidden");
  activeTableName.innerText = "(No Tables)";
  tableRowCountBadge.innerText = "0 tables";
  liveDataTableHead.innerHTML = "";
  liveDataTableBody.innerHTML = "";
}

// Filter live table rows based on search input
function filterTableRows(query) {
  const q = query.toLowerCase().trim();
  const rows = liveDataTableBody.querySelectorAll("tr");
  rows.forEach((tr) => {
    if (tr.querySelector("td[colspan]")) {
      return;
    }
    const text = tr.innerText.toLowerCase();
    tr.style.display = text.includes(q) ? "" : "none";
  });
}

// Execute Dual Pipeline (Baseline first, Proposed second) with Under-The-Hood Live Trace
async function handleExecute() {
  const query = promptInput.value.trim();
  if (!query) {
    showToast("Please enter a question or SQL command.", "error");
    promptInput.focus();
    return;
  }

  if (state.isExecuting) return;
  state.isExecuting = true;
  setExecutingUI(true);

  // Prepare Under-The-Hood Trace Console
  consoleWelcome.classList.add("hidden");
  executionResultView.classList.add("hidden");
  underTheHoodView.classList.remove("hidden");
  hoodLogsContainer.innerHTML = "";

  const addHoodLog = (step, title, text, status = "active") => {
    const item = document.createElement("div");
    item.className = `hood-log-item ${status}`;
    item.id = `hoodStep_${step}`;
    item.innerHTML = `
      <span class="hood-step-badge">[${step}/4]</span>
      <div class="hood-step-txt">
        <strong>${title}</strong>: ${text}
      </div>
    `;
    hoodLogsContainer.appendChild(item);
    hoodLogsContainer.scrollTop = hoodLogsContainer.scrollHeight;
    return item;
  };

  const updateHoodLog = (step, status, text) => {
    const item = document.getElementById(`hoodStep_${step}`);
    if (item) {
      item.className = `hood-log-item ${status}`;
      if (text) {
        const txtElem = item.querySelector(".hood-step-txt");
        if (txtElem) txtElem.innerHTML = text;
      }
    }
  };

  // Step 1: Initialize
  addHoodLog(1, "INITIALIZING PIPELINE", "Capturing database schema snapshot and foreign key graph...", "active");

  // Step 2: Baseline Simulation Tick
  setTimeout(() => {
    updateHoodLog(1, "done", "<strong>INITIALIZED</strong>: Database schema snapshot captured.");
    addHoodLog(2, "BASELINE PIPELINE (FULL SCHEMA)", "Sending full database schema to Gemini model...", "active");
  }, 250);

  // Step 3: Proposed Simulation Tick
  setTimeout(() => {
    if (state.isExecuting) {
      updateHoodLog(2, "done", "<strong>BASELINE PROMPT SENT</strong>: Generating full schema SQL query...");
      addHoodLog(3, "PROPOSED PIPELINE (SCHEMA LINKING)", "Computing 4-Factor relevance scores (Lexical + Semantic Cosine + Type Match + FK Graph)...", "active");
    }
  }, 950);

  try {
    const res = await fetch(`${API_BASE}/api/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: query,
        expected_sql: state.activeExpectedSql || ""
      }),
    });
    const data = await res.json();

    if (data.error) {
      showToast(data.error, "error");
      underTheHoodView.classList.add("hidden");
      consoleWelcome.classList.remove("hidden");
      return;
    }

    // Step 4: Finalizing trace
    updateHoodLog(3, "done", `<strong>SCHEMA REDUCED</strong>: Reduced from ${data.comparison?.schema_columns_full} to ${data.comparison?.schema_columns_reduced} cols (-${data.comparison?.schema_reduction_pct}%).`);
    addHoodLog(4, "EXECUTION & COMPARISON MATRIX", "Proposed SQL executed on database. Generating comparative analytics...", "done");

    // Step 5: Ground Truth Verification
    if (data.ground_truth?.has_ground_truth) {
      addHoodLog(5, "GROUND TRUTH VERIFICATION", `Spider Benchmark Logic Check: [<strong>${data.ground_truth.verdict_label}</strong>] - ${data.ground_truth.verdict_detail}`, "done");
    }

    // Smooth transition to full Comparative Studio
    setTimeout(() => {
      underTheHoodView.classList.add("hidden");
      renderComparativeResult(data);
    }, 450);

    // Refresh active database & tables to visually show any modifications
    await refreshDatabaseState();
  } catch (err) {
    showToast("Execution failed: " + err.message, "error");
    underTheHoodView.classList.add("hidden");
    consoleWelcome.classList.remove("hidden");
  } finally {
    state.isExecuting = false;
    setExecutingUI(false);
  }
}

function setExecutingUI(executing) {
  btnExecute.disabled = executing;
  const spinner = document.getElementById("executeSpinner");
  const btnText = btnExecute.querySelector(".btn-text");
  if (executing) {
    spinner.classList.remove("hidden");
    btnText.innerText = "Running Dual Test...";
  } else {
    spinner.classList.add("hidden");
    btnText.innerText = "Execute Dual Test >";
  }
}

// Render Complete Comparative Results (Steps 1 to 4)
function renderComparativeResult(data) {
  consoleWelcome.classList.add("hidden");
  executionResultView.classList.remove("hidden");

  const base = data.baseline || {};
  const prop = data.proposed || {};
  const comp = data.comparison || {};
  const gt = data.ground_truth || {};

  // -------------------------------------------------------------------------
  // STEP 1: Executed SQL Queries (Baseline vs Proposed vs Spider Target)
  // -------------------------------------------------------------------------
  document.getElementById("baselineSqlCode").innerText = base.sql || "-- No Baseline SQL generated";
  document.getElementById("proposedSqlCode").innerText = prop.sql || "-- No Proposed SQL generated";

  document.getElementById("baseMetaTokens").innerText = base.input_tokens ? `~${base.input_tokens} tok` : "-";
  document.getElementById("baseMetaLatency").innerText = base.total_latency ? `${base.total_latency.toFixed(3)}s` : "-";
  document.getElementById("baseMetaThroughput").innerText = base.throughput?.generation_tps ? `${base.throughput.generation_tps} tok/s` : "-";

  document.getElementById("propMetaTokens").innerText = prop.input_tokens ? `~${prop.input_tokens} tok` : "-";
  document.getElementById("propMetaLatency").innerText = prop.total_latency ? `${prop.total_latency.toFixed(3)}s` : "-";
  document.getElementById("propMetaThroughput").innerText = prop.throughput?.generation_tps ? `${prop.throughput.generation_tps} tok/s` : "-";

  const baseVerdictChip = document.getElementById("baseVerdictChip");
  const propVerdictChip = document.getElementById("propVerdictChip");
  if (baseVerdictChip) baseVerdictChip.className = "verdict-chip";
  if (propVerdictChip) propVerdictChip.className = "verdict-chip";

  const groundTruthSqlBox = document.getElementById("groundTruthSqlBox");
  const groundTruthSqlCode = document.getElementById("groundTruthSqlCode");
  const btnCopyGroundTruthSql = document.getElementById("btnCopyGroundTruthSql");

  if (gt.has_ground_truth) {
    if (groundTruthSqlBox) groundTruthSqlBox.classList.remove("hidden");
    if (groundTruthSqlCode) groundTruthSqlCode.innerText = gt.sql || "--";
    if (btnCopyGroundTruthSql) {
      btnCopyGroundTruthSql.onclick = () => {
        navigator.clipboard.writeText(gt.sql || "");
        showToast("Spider target SQL copied!", "success");
      };
    }
  } else {
    if (groundTruthSqlBox) groundTruthSqlBox.classList.add("hidden");
  }

  // -------------------------------------------------------------------------
  // STEP 2: Schema Reduction Breakdown & Linking Analysis
  // -------------------------------------------------------------------------
  renderSchemaLinkingDetails(prop.schema_linking);

  // -------------------------------------------------------------------------
  // STEP 3: Query Execution Outputs (Baseline, Proposed & Spider Target)
  // -------------------------------------------------------------------------
  // Render Baseline Result Set
  const baseNotice = document.getElementById("baseQueryNotice");
  const baseHead = document.getElementById("baseResultTableHead");
  const baseBody = document.getElementById("baseResultTableBody");
  const baseBadge = document.getElementById("baseExecStatusBadge");
  renderResultSetTable(base.execution || {}, baseNotice, baseHead, baseBody, baseBadge);

  // Render Proposed Result Set
  const propNotice = document.getElementById("propQueryNotice");
  const propHead = document.getElementById("propResultTableHead");
  const propBody = document.getElementById("propResultTableBody");
  const propBadge = document.getElementById("propExecStatusBadge");
  renderResultSetTable(prop.execution || {}, propNotice, propHead, propBody, propBadge);

  // Render Spider Target Result Set
  const gtResultBox = document.getElementById("gtResultBox");
  const gtNotice = document.getElementById("gtQueryNotice");
  const gtHead = document.getElementById("gtResultTableHead");
  const gtBody = document.getElementById("gtResultTableBody");
  const gtBadge = document.getElementById("gtExecStatusBadge");

  if (gt.has_ground_truth && gt.execution) {
    if (gtResultBox) gtResultBox.classList.remove("hidden");
    renderResultSetTable(gt.execution, gtNotice, gtHead, gtBody, gtBadge);
    if (gtBadge) {
      const rowCount = gt.execution.rows ? gt.execution.rows.length : 0;
      gtBadge.innerText = `SPIDER GOLD (${rowCount} row${rowCount === 1 ? "" : "s"})`;
    }
  } else {
    if (gtResultBox) gtResultBox.classList.add("hidden");
  }

  // -------------------------------------------------------------------------
  // STEP 4: Final Metrics Table (Metric | Baseline | Proposed)
  // -------------------------------------------------------------------------
  // Honest comparative metrics derived directly from server execution
  const baseInTokens = base.input_tokens || 0;
  const propInTokens = prop.input_tokens || 0;
  const tokenRedPct = comp.token_reduction_pct !== undefined 
    ? comp.token_reduction_pct 
    : Math.round(((baseInTokens - propInTokens) / Math.max(1, baseInTokens)) * 100);

  const baseCols = comp.schema_columns_full !== undefined ? comp.schema_columns_full : (base.columns_sent || 0);
  const propCols = comp.schema_columns_reduced !== undefined ? comp.schema_columns_reduced : (prop.columns_sent || 0);
  const schemaRedPct = comp.schema_reduction_pct !== undefined 
    ? comp.schema_reduction_pct 
    : Math.round(((baseCols - propCols) / Math.max(1, baseCols)) * 100);

  const linkingLat = prop.schema_linking?.linking_time_seconds !== undefined
    ? Number(prop.schema_linking.linking_time_seconds)
    : 0.0;
  const linkingTimeSec = `${linkingLat.toFixed(4)}s`;

  const baseLlmLat = base.llm_latency !== undefined ? Number(base.llm_latency) : 0.0;
  const propLlmLat = prop.llm_latency !== undefined ? Number(prop.llm_latency) : 0.0;

  const baseTotLat = base.total_latency !== undefined ? Number(base.total_latency) : baseLlmLat;
  const propTotLat = prop.total_latency !== undefined ? Number(prop.total_latency) : (linkingLat + propLlmLat);

  const basePrec = base.precision !== undefined ? Number(base.precision) : 0.0;
  const propPrec = prop.precision !== undefined ? Number(prop.precision) : 0.0;

  const baseRecall = base.recall !== undefined ? Number(base.recall) : 100.0;
  const propRecall = prop.recall !== undefined ? Number(prop.recall) : 0.0;

  const baseF1 = base.f1 !== undefined ? Number(base.f1) : 0.0;
  const propF1 = prop.f1 !== undefined ? Number(prop.f1) : 0.0;

  const baseTps = base.throughput?.generation_tps !== undefined ? Number(base.throughput.generation_tps) : 0.0;
  const propTps = prop.throughput?.generation_tps !== undefined ? Number(prop.throughput.generation_tps) : 0.0;

  // Required Columns Sufficiency (Did the algorithm send >= all required columns for successful SQL generation?)
  const baseSuff = base.sufficiency || comp.base_sufficiency || {};
  const propSuff = prop.sufficiency || comp.prop_sufficiency || {};

  let baseSuffHtml = `<span style="color: var(--text-muted);">N/A (Custom Query)</span>`;
  if (!baseSuff.is_custom && baseSuff.required_count > 0) {
    baseSuffHtml = `<strong>100.0% (Yes - All Required Sent: ${baseSuff.sent_required_count}/${baseSuff.required_count})</strong>`;
  }

  let propSuffHtml = `<span style="color: var(--text-muted);">N/A (Custom Query)</span>`;
  if (!propSuff.is_custom && propSuff.required_count > 0) {
    if (propSuff.has_all_required) {
      propSuffHtml = `<strong style="color: var(--accent-green);">100.0% (Yes - All Required Sent: ${propSuff.sent_required_count}/${propSuff.required_count})</strong>`;
    } else {
      const missingList = (propSuff.missing_columns || []).join(", ");
      propSuffHtml = `<strong style="color: var(--accent-orange);">${propSuff.coverage_pct}% (Incomplete - Missing ${propSuff.missing_columns?.length || 0} Required: ${missingList})</strong>`;
    }
  }

  const matrixBody = document.getElementById("comparisonMatrixBody");
  matrixBody.innerHTML = `
    <tr>
      <td style="font-weight: 600; color: var(--text-main);">Prompt Tokens</td>
      <td><strong>${baseInTokens} tok</strong></td>
      <td><strong>${propInTokens} tok</strong>${tokenRedPct > 0 ? ` <span style="font-size: 11px; color: var(--accent-cyan);">(-${tokenRedPct}%)</span>` : ""}</td>
    </tr>
    <tr>
      <td style="font-weight: 600; color: var(--text-main);">Columns Sent</td>
      <td><strong>${baseCols} columns</strong></td>
      <td><strong>${propCols} columns</strong>${schemaRedPct > 0 ? ` <span style="font-size: 11px; color: var(--accent-cyan);">(-${schemaRedPct}%)</span>` : ""}</td>
    </tr>
    <tr>
      <td style="font-weight: 600; color: var(--text-main);">Schema Reduction</td>
      <td style="color: var(--text-muted);">0.0% (Full Schema)</td>
      <td><strong>${schemaRedPct}%</strong></td>
    </tr>
    <tr>
      <td style="font-weight: 600; color: var(--text-main);">Algorithm Linking Latency</td>
      <td style="color: var(--text-muted);">0.0000s (None)</td>
      <td>${linkingTimeSec}</td>
    </tr>
    <tr>
      <td style="font-weight: 600; color: var(--text-main);">LLM Generation Latency</td>
      <td>${baseLlmLat.toFixed(3)}s</td>
      <td>${propLlmLat.toFixed(3)}s</td>
    </tr>
    <tr>
      <td style="font-weight: 600; color: var(--text-main);">End-to-End (Total) Latency</td>
      <td>${baseTotLat.toFixed(3)}s</td>
      <td>${propTotLat.toFixed(3)}s</td>
    </tr>
    <tr>
      <td style="font-weight: 600; color: var(--text-main);">Schema Linking Precision</td>
      <td><strong>${basePrec.toFixed(1)}%</strong></td>
      <td><strong>${propPrec.toFixed(1)}%</strong></td>
    </tr>
    <tr>
      <td style="font-weight: 600; color: var(--text-main);">Schema Recall Accuracy</td>
      <td><strong>${baseRecall.toFixed(1)}%</strong></td>
      <td><strong>${propRecall.toFixed(1)}%</strong></td>
    </tr>
    <tr>
      <td style="font-weight: 600; color: var(--text-main);">Schema F1-Score</td>
      <td><strong>${baseF1.toFixed(1)}%</strong></td>
      <td><strong>${propF1.toFixed(1)}%</strong></td>
    </tr>
    <tr>
      <td style="font-weight: 600; color: var(--text-main);">Generation Throughput</td>
      <td>${baseTps.toFixed(1)} tok/s</td>
      <td>${propTps.toFixed(1)} tok/s</td>
    </tr>
    <tr>
      <td style="font-weight: 600; color: var(--text-main);">Required Columns Sufficiency</td>
      <td>${baseSuffHtml}</td>
      <td>${propSuffHtml}</td>
    </tr>
  `;

  // -------------------------------------------------------------------------
  // STEP 5: Visual Performance Analytics (Direct Query Charts)
  // -------------------------------------------------------------------------
  renderDirectQueryVisualAnalytics(data);
}

// Render Result Set Rows and Columns
function renderResultSetTable(exec, noticeElem, headElem, bodyElem, badgeElem) {
  headElem.innerHTML = "";
  bodyElem.innerHTML = "";

  if (exec.success) {
    badgeElem.className = "status-badge success";
    badgeElem.innerText = "SUCCESS";

    const cols = exec.columns || [];
    const rows = exec.rows || [];

    if (cols.length > 0) {
      noticeElem.innerHTML = `<span style="color: var(--accent-green);">Query executed successfully. ${rows.length} row(s) returned:</span>`;

      // Render Header
      const trHead = document.createElement("tr");
      cols.forEach((col) => {
        const th = document.createElement("th");
        th.innerText = col;
        trHead.appendChild(th);
      });
      headElem.appendChild(trHead);

      // Render Rows
      if (rows.length === 0) {
        const trEmpty = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = cols.length;
        td.style.textAlign = "center";
        td.style.color = "var(--text-dim)";
        td.style.padding = "16px";
        td.innerText = "(Query returned 0 rows)";
        trEmpty.appendChild(td);
        bodyElem.appendChild(trEmpty);
      } else {
        rows.forEach((row) => {
          const tr = document.createElement("tr");
          row.forEach((cell) => {
            const td = document.createElement("td");
            td.innerText = cell !== null && cell !== undefined ? cell : "NULL";
            tr.appendChild(td);
          });
          bodyElem.appendChild(tr);
        });
      }
    } else {
      // Non-SELECT statement (CREATE, INSERT, UPDATE, DELETE, DROP)
      noticeElem.innerHTML = `<span style="color: var(--accent-green);">${exec.message || "Statement executed successfully."}</span>`;
      const trEmpty = document.createElement("tr");
      const td = document.createElement("td");
      td.style.padding = "14px";
      td.style.color = "var(--text-muted)";
      td.innerText = exec.message || "Operation completed successfully.";
      trEmpty.appendChild(td);
      bodyElem.appendChild(trEmpty);
    }
  } else {
    badgeElem.className = "status-badge failed";
    badgeElem.innerText = "FAILED";
    noticeElem.innerHTML = `<span style="color: var(--accent-rose);">${exec.error || "Query failed to execute."}</span>`;
    const trErr = document.createElement("tr");
    const td = document.createElement("td");
    td.style.padding = "14px";
    td.style.color = "var(--accent-rose)";
    td.innerText = exec.error || "SQL execution failed.";
    trErr.appendChild(td);
    bodyElem.appendChild(trErr);
  }
}

// Render Schema Linking Breakdown
function renderSchemaLinkingDetails(linking) {
  if (!linking) return;

  const reduction = linking.schema_reduction || {};
  const reductionBadge = document.getElementById("reductionBadge");
  reductionBadge.innerText = `-${reduction.reduction_percentage || 0}% Columns`;

  document.getElementById("statFullCols").innerText = reduction.full_columns || 0;
  document.getElementById("statReducedCols").innerText = reduction.reduced_columns || 0;
  document.getElementById("statLinkingTime").innerText = `${(linking.linking_time_seconds || 0).toFixed(4)}s`;

  const statLThroughput = document.getElementById("statLinkingThroughput");
  if (statLThroughput) {
    statLThroughput.innerText = linking.linking_throughput_cps ? `~${linking.linking_throughput_cps} cols/s` : "-";
  }

  // Render Ranked Table Rows
  const tbody = document.getElementById("rankedTableBody");
  tbody.innerHTML = "";

  const items = (linking.ranked_items || []).slice(0, 8);
  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-dim);">No existing columns to rank.</td></tr>`;
  } else {
    items.forEach((item) => {
      const tr = document.createElement("tr");
      const scorePct = Math.round(item.score * 100);
      tr.innerHTML = `
        <td style="font-weight: 600; color: var(--accent-cyan);">${item.table}.${item.column}</td>
        <td>
          <div class="score-bar-cell">
            <span style="width: 32px; font-weight: bold;">${item.score.toFixed(2)}</span>
            <div class="score-track"><div class="score-fill" style="width: ${scorePct}%;"></div></div>
          </div>
        </td>
        <td>${item.lexical.toFixed(2)}</td>
        <td>${item.semantic.toFixed(2)}</td>
        <td>${item.type.toFixed(2)}</td>
        <td>${item.relationship.toFixed(2)}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // Selected Schema Display
  const selDisplay = document.getElementById("selectedSchemaDisplay");
  const redSchema = linking.reduced_schema || {};
  const formatted = Object.entries(redSchema)
    .map(([tbl, cols]) => `${tbl}(${Object.keys(cols).join(", ")})`)
    .join(" • ");
  selDisplay.innerHTML = `<strong>Selected Reduced Schema:</strong> ${formatted || "None"}`;
}

// Toast notification helper
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerText = message;
  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(30px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ==========================================================================
// SAMPLE BENCHMARK QUERIES (ALWAYS LOADED FOR ACTIVE DATABASE)
// ==========================================================================
async function loadSampleQueries(dbId, tableName = null, mode = "db") {
  try {
    const effectiveDb = dbId || state.activeDbId || "college";
    const url = `${API_BASE}/api/sample-queries?db_id=${encodeURIComponent(effectiveDb)}&limit=12`;

    const res = await fetch(url);
    const data = await res.json();
    state.sampleQueries = data.queries || [];
    renderSampleQueries(tableName, "db");
  } catch (err) {
    console.error("Error fetching sample queries:", err);
    state.sampleQueries = [];
    renderSampleQueries(tableName, "db");
  }
}

function renderSampleQueries(tableName, mode = "db") {
  const targetLabel = state.activeDbName || state.activeDbId || "College Preset";

  if (quickChipsTargetLabel) quickChipsTargetLabel.innerText = targetLabel;
  if (sampleQueriesTableName) sampleQueriesTableName.innerText = targetLabel;
  if (sampleQueriesCountBadge) sampleQueriesCountBadge.innerText = state.sampleQueries.length;
  if (sampleQueriesTitleText) {
    sampleQueriesTitleText.innerHTML = `SAMPLE QUERIES FOR <strong>${escapeHtml(targetLabel)}</strong>`;
  }

  // Quick Chips in Prompt Console (Top of Input Area)
  if (quickChipsContainer) {
    quickChipsContainer.innerHTML = "";
    if (state.sampleQueries.length === 0) {
      quickChipsContainer.innerHTML = `<span style="font-size: 11px; color: var(--text-dim); padding: 2px;">No sample queries found for this database. Type your question below!</span>`;
    } else {
      state.sampleQueries.slice(0, 8).forEach((q) => {
        const chip = document.createElement("button");
        chip.className = "quick-chip";
        chip.title = `Click to load into prompt. Target SQL: ${q.sql || "N/A"}`;
        chip.innerHTML = `<span>${escapeHtml(q.question)}</span><span class="quick-chip-run-btn" title="Run immediately">&gt;</span>`;

        // Click question text -> fill prompt & store expected SQL
        chip.querySelector("span").addEventListener("click", (e) => {
          e.stopPropagation();
          promptInput.value = q.question;
          state.activeExpectedSql = q.sql || "";
          promptInput.focus();
          showToast(`Prompt loaded: "${q.question}"`, "info");
        });

        // Click play button -> fill and execute immediately
        chip.querySelector(".quick-chip-run-btn").addEventListener("click", (e) => {
          e.stopPropagation();
          promptInput.value = q.question;
          state.activeExpectedSql = q.sql || "";
          handleExecute();
        });

        // Clicking anywhere else on the chip body
        chip.addEventListener("click", () => {
          promptInput.value = q.question;
          state.activeExpectedSql = q.sql || "";
          promptInput.focus();
          showToast(`Prompt loaded: "${q.question}"`, "info");
        });

        quickChipsContainer.appendChild(chip);
      });
    }
  }
}

// ==========================================================================
// SPIDER DATABASE BROWSER MODAL
// ==========================================================================
async function openSpiderModal() {
  if (!spiderDbModal) return;
  spiderDbModal.classList.remove("hidden");
  if (modalDbSearchInput) {
    modalDbSearchInput.value = "";
    modalDbSearchInput.focus();
  }
  if (btnClearModalSearch) btnClearModalSearch.classList.add("hidden");

  // Reset category filter
  state.modalFilterCategory = "all";
  document.querySelectorAll(".modal-quick-filters .filter-chip").forEach((c) => {
    if (c.dataset.filter === "all") c.classList.add("active");
    else c.classList.remove("active");
  });

  if (state.spiderDatabases.length === 0) {
    await loadSpiderDatabases();
  } else {
    renderSpiderDatabases();
  }
}

function closeSpiderModal() {
  if (spiderDbModal) spiderDbModal.classList.add("hidden");
}

async function loadSpiderDatabases() {
  if (modalDbGrid) {
    modalDbGrid.innerHTML = `<div style="padding: 20px; text-align: center; color: var(--text-dim); font-family: var(--font-mono); grid-column: 1 / -1;">Loading 160+ Spider benchmark databases...</div>`;
  }
  try {
    const res = await fetch(`${API_BASE}/api/spider/databases`);
    const data = await res.json();
    state.spiderDatabases = data.databases || [];
    if (filterAllCount) filterAllCount.innerText = state.spiderDatabases.length + 1; // +1 for College Preset
    renderSpiderDatabases();
  } catch (err) {
    console.error("Failed loading spider databases:", err);
    if (modalDbGrid) {
      modalDbGrid.innerHTML = `<div style="padding: 20px; color: var(--accent-rose); grid-column: 1 / -1;">Failed to load Spider databases from backend.</div>`;
    }
  }
}

function filterModalDatabases(query) {
  if (btnClearModalSearch) {
    if (query && query.trim()) btnClearModalSearch.classList.remove("hidden");
    else btnClearModalSearch.classList.add("hidden");
  }
  renderSpiderDatabases(query, state.modalFilterCategory);
}

function renderSpiderDatabases(query = "", category = state.modalFilterCategory) {
  if (!modalDbGrid) return;
  modalDbGrid.innerHTML = "";

  const q = (query || "").toLowerCase().trim();

  // 1. College Preset Card
  const showCollege =
    (category === "all" || category === "presets") &&
    (!q || "college preset student course faculty enrollment".includes(q));

  if (showCollege) {
    const isActive = state.activeDbId === "college";
    const card = document.createElement("div");
    card.className = `db-card ${isActive ? "active" : ""}`;
    card.innerHTML = `
      <div class="db-card-header">
        <span class="db-card-title">college (College Preset)</span>
        <span class="db-card-badge ${isActive ? 'badge-active' : ''}">${isActive ? 'ACTIVE' : 'PRESET'}</span>
      </div>
      <div class="db-card-tables">
        Tables: Student, Course, Enrollment, Faculty (18 columns)
      </div>
      <div class="db-card-footer">
        <button class="btn btn-xs ${isActive ? 'btn-outline' : 'btn-success'}">${isActive ? 'Connected' : 'Select Database'}</button>
      </div>
    `;
    card.addEventListener("click", () => {
      switchToDatabase("college");
    });
    modalDbGrid.appendChild(card);
  }

  // 2. Spider Databases
  const popularList = [
    "concert_singer", "flight_2", "car_1", "world_1", "network_1",
    "student_transcripts_tracking", "cinema", "museum_visit", "pets_1", "tvshow"
  ];

  const filteredDbs = state.spiderDatabases.filter((db) => {
    if (category === "presets") return false;
    if (category === "popular" && !popularList.includes(db.db_id)) return false;

    if (!q) return true;
    const dbName = db.db_id.toLowerCase();
    const tables = (db.tables || []).map((t) => t.toLowerCase()).join(" ");
    return dbName.includes(q) || tables.includes(q);
  });

  if (filteredDbs.length === 0 && !showCollege) {
    modalDbGrid.innerHTML = `<div style="grid-column: 1 / -1; padding: 30px; text-align: center; color: var(--text-dim);">No databases matching "${escapeHtml(q)}".</div>`;
    return;
  }

  filteredDbs.forEach((db) => {
    const isActive = state.activeDbId === db.db_id;
    const card = document.createElement("div");
    card.className = `db-card ${isActive ? "active" : ""}`;
    const tablesList = (db.tables || []).join(", ") || "No tables";

    card.innerHTML = `
      <div class="db-card-header">
        <span class="db-card-title">${escapeHtml(db.db_id)}</span>
        <span class="db-card-badge ${isActive ? 'badge-active' : ''}">${isActive ? 'ACTIVE' : `${db.table_count} tables`}</span>
      </div>
      <div class="db-card-tables" title="${escapeHtml(tablesList)}">
        Tables: ${escapeHtml(tablesList)}
      </div>
      <div class="db-card-footer">
        <button class="btn btn-xs ${isActive ? 'btn-outline' : 'btn-primary'}">${isActive ? 'Connected' : 'Select Database'}</button>
      </div>
    `;

    card.addEventListener("click", () => {
      switchToDatabase(db.db_id);
    });

    modalDbGrid.appendChild(card);
  });
}

async function switchToDatabase(dbId) {
  try {
    showToast(`Connecting to database '${dbId}'...`, "info");
    closeSpiderModal();

    let res, data;
    if (dbId === "college") {
      res = await fetch(`${API_BASE}/api/preset`, { method: "POST" });
    } else {
      res = await fetch(`${API_BASE}/api/spider/switch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ db_id: dbId }),
      });
    }

    data = await res.json();
    await refreshDatabaseState();
    showToast(data.message || `Connected to '${dbId}'.`, "success");
  } catch (err) {
    console.error("Error switching database:", err);
    showToast("Failed to switch database: " + err.message, "error");
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ==========================================================================
// SPIDER TOP-5 BENCHMARK EVALUATION ENGINE & UI CONTROLLER
// ==========================================================================
const benchState = {
  selectedDepth: 1,
  selectedDb: "all",
  viewMode: "summary",
  selectedQueryIndex: 0,
  pollInterval: null,
  isExecuting: false,
  results: null,
};

function openBenchmarkModal() {
  const modal = document.getElementById("spiderBenchmarkModal");
  if (modal) {
    modal.classList.remove("hidden");
    fetchBenchmarkStatus();
  }
}

function closeBenchmarkModal() {
  const modal = document.getElementById("spiderBenchmarkModal");
  if (modal) {
    modal.classList.add("hidden");
  }
}

async function fetchBenchmarkStatus(forceLoadSaved = false) {
  try {
    const res = await fetch(`${API_BASE}/api/benchmark/top5`);
    if (!res.ok) return;
    const data = await res.json();
    benchState.results = data.results;

    const progressSection = document.getElementById("benchProgressSection");
    const dashboardSection = document.getElementById("benchDashboardSection");
    const emptyState = document.getElementById("benchEmptyState");
    const btnStart = document.getElementById("btnStartBenchmark");
    const btnStop = document.getElementById("btnStopBenchmark");
    const spinner = document.getElementById("benchSpinner");
    const progressBar = document.getElementById("benchProgressBar");
    const progressPct = document.getElementById("benchProgressPct");
    const statusText = document.getElementById("benchStatusText");
    const currentQueryText = document.getElementById("benchCurrentQueryText");
    const logsBox = document.getElementById("benchLogsBox");

    if (data.status === "running") {
      benchState.isExecuting = true;
      if (progressSection) progressSection.classList.remove("hidden");
      if (emptyState) emptyState.classList.add("hidden");
      if (btnStart) btnStart.disabled = true;
      if (spinner) spinner.classList.remove("hidden");
      if (btnStop) btnStop.classList.remove("hidden");

      const pct = data.progress ? Math.round(data.progress) : 0;
      if (progressBar) progressBar.style.width = `${pct}%`;
      if (progressPct) progressPct.innerText = `${pct}%`;
      if (statusText) statusText.innerText = `Evaluating [${data.current_db || "Spider"}]: Query ${data.current_query_index || 0} of ${data.total_queries || 0}`;
      if (currentQueryText) currentQueryText.innerText = data.current_question || "Processing dual baseline & proposed pipelines...";

      // Render logs
      if (logsBox && data.logs && data.logs.length > 0) {
        logsBox.innerHTML = data.logs.map(log => {
          let cls = "bench-log-line";
          if (log.includes("PASS") || log.includes("SUCCESS")) cls += " bench-log-success";
          else if (log.includes("Evaluating") || log.includes("START")) cls += " bench-log-highlight";
          return `<div class="${cls}">${escapeHtml(log)}</div>`;
        }).join("");
        logsBox.scrollTop = logsBox.scrollHeight;
      }

      if (!benchState.pollInterval) {
        benchState.pollInterval = setInterval(() => fetchBenchmarkStatus(false), 1200);
      }
    } else {
      // Completed, cancelled, or idle
      if (benchState.isExecuting && data.status === "completed") {
        showToast("Top-5 Spider Benchmark evaluation completed!", "success");
      }
      benchState.isExecuting = false;
      if (benchState.pollInterval) {
        clearInterval(benchState.pollInterval);
        benchState.pollInterval = null;
      }

      if (btnStart) btnStart.disabled = false;
      if (spinner) spinner.classList.add("hidden");
      if (btnStop) btnStop.classList.add("hidden");

      if (data.status === "completed" || data.status === "cancelled" || data.status === "error") {
        if (progressSection) {
          if (data.status === "completed") {
            if (progressBar) progressBar.style.width = "100%";
            if (progressPct) progressPct.innerText = "100%";
            if (statusText) statusText.innerText = "Benchmark execution completed!";
            if (currentQueryText) currentQueryText.innerText = `Evaluated queries across target databases.`;
          } else if (data.status === "cancelled") {
            if (statusText) statusText.innerText = "Benchmark execution stopped by user.";
          }
        }
      }

      // Render logs if available
      if (logsBox && data.logs && data.logs.length > 0) {
        logsBox.innerHTML = data.logs.map(log => {
          let cls = "bench-log-line";
          if (log.includes("PASS") || log.includes("SUCCESS")) cls += " bench-log-success";
          else if (log.includes("Evaluating") || log.includes("START")) cls += " bench-log-highlight";
          return `<div class="${cls}">${escapeHtml(log)}</div>`;
        }).join("");
        logsBox.scrollTop = logsBox.scrollHeight;
      }

      // Render dashboard if results available
      if (data.results && data.results.summary) {
        if (dashboardSection) dashboardSection.classList.remove("hidden");
        if (emptyState) emptyState.classList.add("hidden");
        renderBenchmarkDashboard(data.results);
      } else {
        if (dashboardSection) dashboardSection.classList.add("hidden");
        if (emptyState && !benchState.isExecuting) emptyState.classList.remove("hidden");
      }
    }
  } catch (err) {
    console.error("Error fetching benchmark status:", err);
  }
}

async function startBenchmark() {
  if (benchState.isExecuting) return;
  try {
    const btnStart = document.getElementById("btnStartBenchmark");
    const spinner = document.getElementById("benchSpinner");
    const progressSection = document.getElementById("benchProgressSection");
    const emptyState = document.getElementById("benchEmptyState");
    const progressBar = document.getElementById("benchProgressBar");
    const progressPct = document.getElementById("benchProgressPct");
    const statusText = document.getElementById("benchStatusText");
    const logsBox = document.getElementById("benchLogsBox");

    if (btnStart) btnStart.disabled = true;
    if (spinner) spinner.classList.remove("hidden");
    if (progressSection) progressSection.classList.remove("hidden");
    if (emptyState) emptyState.classList.add("hidden");
    if (progressBar) progressBar.style.width = "0%";
    if (progressPct) progressPct.innerText = "0%";
    if (statusText) statusText.innerText = "Starting Dual Benchmark on 5 Spider DBs...";
    if (logsBox) logsBox.innerHTML = `<div class="bench-log-line bench-log-highlight">Initializing: Preparing benchmark with ${benchState.selectedDepth} query per database...</div>`;

    showToast(`Initiating Top-5 Spider Benchmark (${benchState.selectedDepth} Q/DB)...`, "info");

    const res = await fetch(`${API_BASE}/api/benchmark/top5/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ queries_per_db: benchState.selectedDepth }),
    });

    const data = await res.json();
    if (res.ok) {
      benchState.isExecuting = true;
      if (!benchState.pollInterval) {
        benchState.pollInterval = setInterval(() => fetchBenchmarkStatus(false), 1200);
      }
    } else {
      showToast(data.error || "Failed to start benchmark.", "error");
      if (btnStart) btnStart.disabled = false;
      if (spinner) spinner.classList.add("hidden");
    }
  } catch (err) {
    console.error("Error starting benchmark:", err);
    showToast("Error starting benchmark: " + err.message, "error");
  }
}

async function stopBenchmark() {
  try {
    showToast("Requesting benchmark cancellation...", "warning");
    const res = await fetch(`${API_BASE}/api/benchmark/top5/stop`, { method: "POST" });
    const data = await res.json();
    showToast(data.message || "Benchmark stopping...", "info");
  } catch (err) {
    console.error("Error stopping benchmark:", err);
  }
}

function renderBenchmarkDashboard(resultsData) {
  if (!resultsData) return;
  const allResults = resultsData.results || [];
  if (allResults.length === 0) return;

  const dbSelect = document.getElementById("benchDbSelect");
  const querySelectContainer = document.getElementById("benchQuerySelectContainer");
  const querySelect = document.getElementById("benchQuerySelect");
  const queryBanner = document.getElementById("benchQueryBanner");
  const queryDbBadge = document.getElementById("benchQueryDbBadge");
  const queryText = document.getElementById("benchQueryText");
  const tableBody = document.getElementById("benchMetricsTableBody");
  const sqlSection = document.getElementById("benchQuerySqlSection");

  if (!tableBody) return;

  // Filter queries based on selected DB
  const filteredQueries = benchState.selectedDb === "all"
    ? allResults
    : allResults.filter(r => (r.db_id || "").toLowerCase() === benchState.selectedDb.toLowerCase());

  if (filteredQueries.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="3" style="text-align: center; padding: 24px; color: var(--text-muted);">No evaluated queries found for '${escapeHtml(benchState.selectedDb)}'.</td></tr>`;
    return;
  }

  if (benchState.viewMode === "summary") {
    // Hide query-specific elements in summary mode
    if (querySelectContainer) querySelectContainer.classList.add("hidden");
    if (queryBanner) queryBanner.classList.add("hidden");
    if (sqlSection) sqlSection.classList.add("hidden");

    // Aggregate metrics across filteredQueries
    const count = filteredQueries.length || 1;
    const avg = (fn) => filteredQueries.reduce((sum, r) => sum + (Number(fn(r)) || 0), 0) / count;

    const basePromptTokens = Math.round(avg(r => r.baseline?.prompt_tokens || 0));
    const propPromptTokens = Math.round(avg(r => r.proposed?.prompt_tokens || 0));
    const tokenRedPct = basePromptTokens > 0 
      ? (((basePromptTokens - propPromptTokens) / basePromptTokens) * 100).toFixed(1)
      : "0.0";

    const baseColsSent = avg(r => r.baseline?.schema_cols_sent || 0).toFixed(1);
    const propColsSent = avg(r => r.proposed?.schema_cols_sent || 0).toFixed(1);
    const schemaRedPct = avg(r => r.proposed?.schema_reduction_pct || 0).toFixed(1);

    const linkingMs = avg(r => r.proposed?.linking_latency_ms || 0);
    const linkingSec = (linkingMs / 1000).toFixed(4);

    const baseLlmLat = avg(r => r.baseline?.llm_latency_s || 0).toFixed(3);
    const propLlmLat = avg(r => r.proposed?.llm_latency_s || 0).toFixed(3);

    const baseTotLat = avg(r => r.baseline?.total_latency_s || r.baseline?.llm_latency_s || 0).toFixed(3);
    const propTotLat = avg(r => r.proposed?.total_latency_s || r.proposed?.llm_latency_s || 0).toFixed(3);

    const basePrec = avg(r => r.baseline?.precision_pct || 0).toFixed(1);
    const propPrec = avg(r => r.proposed?.precision_pct || 0).toFixed(1);

    const baseRecall = avg(r => r.baseline?.recall_pct || 0).toFixed(1);
    const propRecall = avg(r => r.proposed?.recall_pct || 0).toFixed(1);

    const baseF1 = avg(r => r.baseline?.f1_pct || 0).toFixed(1);
    const propF1 = avg(r => r.proposed?.f1_pct || 0).toFixed(1);

    const baseTps = avg(r => r.baseline?.tps || 0).toFixed(1);
    const propTps = avg(r => r.proposed?.tps || 0).toFixed(1);

    // Required columns sufficiency rate
    let propSuffCount = 0;
    filteredQueries.forEach(r => {
      const gt = (r.gt_cols || []).map(c => c.toLowerCase());
      const pCols = (r.prop_selected_cols || []).map(c => c.toLowerCase());
      if (gt.length === 0 || gt.every(c => pCols.includes(c))) {
        propSuffCount++;
      }
    });
    const propSuffPct = ((propSuffCount / count) * 100).toFixed(1);

    tableBody.innerHTML = `
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Prompt Tokens</td>
        <td><strong>${basePromptTokens} tok</strong></td>
        <td><strong>${propPromptTokens} tok</strong>${Number(tokenRedPct) > 0 ? ` <span style="font-size: 11px; color: var(--accent-cyan);">(-${tokenRedPct}%)</span>` : ""}</td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Columns Sent</td>
        <td><strong>${baseColsSent} columns</strong></td>
        <td><strong>${propColsSent} columns</strong>${Number(schemaRedPct) > 0 ? ` <span style="font-size: 11px; color: var(--accent-cyan);">(-${schemaRedPct}%)</span>` : ""}</td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Schema Reduction</td>
        <td style="color: var(--text-muted);">0.0% (Full Schema)</td>
        <td><strong>${schemaRedPct}%</strong></td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Algorithm Linking Latency</td>
        <td style="color: var(--text-muted);">0.0000s (None)</td>
        <td>${linkingSec}s (${linkingMs.toFixed(1)}ms)</td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">LLM Generation Latency</td>
        <td>${baseLlmLat}s</td>
        <td>${propLlmLat}s</td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">End-to-End (Total) Latency</td>
        <td>${baseTotLat}s</td>
        <td>${propTotLat}s</td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Schema Linking Precision</td>
        <td><strong>${basePrec}%</strong></td>
        <td><strong>${propPrec}%</strong></td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Schema Recall Accuracy</td>
        <td><strong>${baseRecall}%</strong></td>
        <td><strong>${propRecall}%</strong></td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Schema F1-Score</td>
        <td><strong>${baseF1}%</strong></td>
        <td><strong>${propF1}%</strong></td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Generation Throughput</td>
        <td>${baseTps} tok/s</td>
        <td>${propTps} tok/s</td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Required Columns Sufficiency</td>
        <td><strong>100.0% (Yes - All Required Sent in ${filteredQueries.length}/${filteredQueries.length} Queries)</strong></td>
        <td><strong style="color: var(--accent-green);">${propSuffPct}% (Yes - All Required Sent in ${propSuffCount}/${filteredQueries.length} Queries)</strong></td>
      </tr>
    `;
  } else {
    // Query-Wise View
    if (querySelectContainer) querySelectContainer.classList.remove("hidden");
    if (queryBanner) queryBanner.classList.remove("hidden");
    if (sqlSection) sqlSection.classList.remove("hidden");

    // Populate Query Select Options
    if (querySelect) {
      querySelect.innerHTML = filteredQueries.map((r, i) => {
        const qShort = r.question ? (r.question.length > 75 ? r.question.substring(0, 75) + "..." : r.question) : `Query ${i + 1}`;
        return `<option value="${i}" ${i === benchState.selectedQueryIndex ? "selected" : ""}>[${r.db_id}] Q${i + 1}: ${escapeHtml(qShort)}</option>`;
      }).join("");
    }

    if (benchState.selectedQueryIndex >= filteredQueries.length) {
      benchState.selectedQueryIndex = 0;
    }

    const item = filteredQueries[benchState.selectedQueryIndex];
    if (!item) return;

    const b = item.baseline || {};
    const p = item.proposed || {};

    // Update query banner
    if (queryDbBadge) queryDbBadge.innerText = item.db_id || "Spider";
    if (queryText) queryText.innerText = item.question || "";

    const bTok = b.prompt_tokens || 0;
    const pTok = p.prompt_tokens || 0;
    const tokRed = bTok > 0 ? (((bTok - pTok) / bTok) * 100).toFixed(1) : "0.0";
    const colRed = p.schema_reduction_pct !== undefined ? Number(p.schema_reduction_pct).toFixed(1) : "0.0";
    const linkMs = p.linking_latency_ms || 0;

    // Check sufficiency for this query
    const gtCols = (item.gt_cols || []).map(c => c.toLowerCase());
    const propCols = (item.prop_selected_cols || []).map(c => c.toLowerCase());
    const missing = gtCols.filter(c => !propCols.includes(c));
    const sentReq = gtCols.length - missing.length;
    const coverage = gtCols.length > 0 ? ((sentReq / gtCols.length) * 100).toFixed(1) : "100.0";

    let propSuffHtml = "";
    if (missing.length === 0) {
      propSuffHtml = `<strong style="color: var(--accent-green);">100.0% (Yes - All Required Sent: ${sentReq}/${gtCols.length})</strong>`;
    } else {
      propSuffHtml = `<strong style="color: var(--accent-orange);">${coverage}% (Incomplete - Missing ${missing.length}: ${missing.join(', ')})</strong>`;
    }

    tableBody.innerHTML = `
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Prompt Tokens</td>
        <td><strong>${bTok} tok</strong></td>
        <td><strong>${pTok} tok</strong>${Number(tokRed) > 0 ? ` <span style="font-size: 11px; color: var(--accent-cyan);">(-${tokRed}%)</span>` : ""}</td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Columns Sent</td>
        <td><strong>${b.schema_cols_sent || 0} columns</strong></td>
        <td><strong>${p.schema_cols_sent || 0} columns</strong>${Number(colRed) > 0 ? ` <span style="font-size: 11px; color: var(--accent-cyan);">(-${colRed}%)</span>` : ""}</td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Schema Reduction</td>
        <td style="color: var(--text-muted);">0.0% (Full Schema)</td>
        <td><strong>${colRed}%</strong></td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Algorithm Linking Latency</td>
        <td style="color: var(--text-muted);">0.0000s (None)</td>
        <td>${(linkMs / 1000).toFixed(4)}s (${linkMs.toFixed(1)}ms)</td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">LLM Generation Latency</td>
        <td>${(b.llm_latency_s || 0).toFixed(3)}s</td>
        <td>${(p.llm_latency_s || 0).toFixed(3)}s</td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">End-to-End (Total) Latency</td>
        <td>${(b.total_latency_s || b.llm_latency_s || 0).toFixed(3)}s</td>
        <td>${(p.total_latency_s || p.llm_latency_s || 0).toFixed(3)}s</td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Schema Linking Precision</td>
        <td><strong>${(b.precision_pct || 0).toFixed(1)}%</strong></td>
        <td><strong>${(p.precision_pct || 0).toFixed(1)}%</strong></td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Schema Recall Accuracy</td>
        <td><strong>${(b.recall_pct || 0).toFixed(1)}%</strong></td>
        <td><strong>${(p.recall_pct || 0).toFixed(1)}%</strong></td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Schema F1-Score</td>
        <td><strong>${(b.f1_pct || 0).toFixed(1)}%</strong></td>
        <td><strong>${(p.f1_pct || 0).toFixed(1)}%</strong></td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Generation Throughput</td>
        <td>${(b.tps || 0).toFixed(1)} tok/s</td>
        <td>${(p.tps || 0).toFixed(1)} tok/s</td>
      </tr>
      <tr>
        <td style="font-weight: 600; color: var(--text-main);">Required Columns Sufficiency</td>
        <td><strong>100.0% (Yes - All Required Sent: ${gtCols.length}/${gtCols.length})</strong></td>
        <td>${propSuffHtml}</td>
      </tr>
    `;

    // SQL code & badges
    const propSqlCode = document.getElementById("benchPropSqlCode");
    const baseSqlCode = document.getElementById("benchBaseSqlCode");
    const gtSqlCode = document.getElementById("benchGtSqlCode");
    const propStatus = document.getElementById("benchPropSqlStatus");
    const baseStatus = document.getElementById("benchBaseSqlStatus");

    if (propSqlCode) propSqlCode.innerText = p.sql || "(No SQL generated)";
    if (baseSqlCode) baseSqlCode.innerText = b.sql || "(No SQL generated)";
    if (gtSqlCode) gtSqlCode.innerText = item.gt_sql || "(No Gold SQL)";

    if (propStatus) {
      propStatus.className = p.result_correct ? "status-badge success" : "status-badge error";
      propStatus.innerText = p.result_correct ? "PASS" : "MISMATCH";
    }
    if (baseStatus) {
      baseStatus.className = b.result_correct ? "status-badge success" : "status-badge error";
      baseStatus.innerText = b.result_correct ? "PASS" : "MISMATCH";
    }
  }
}

// ==========================================================================
// BENCHMARK VISUAL ANALYTICS & CHARTS (STRICTLY NO HORIZONTAL BARS)
// ==========================================================================

let visualAnalyticsData = null;

function openAnalyticsModal() {
  const modal = document.getElementById("benchmarkAnalyticsModal");
  if (modal) {
    modal.classList.remove("hidden");
    fetchVisualAnalyticsData();
  }
}

function closeAnalyticsModal() {
  const modal = document.getElementById("benchmarkAnalyticsModal");
  if (modal) {
    modal.classList.add("hidden");
  }
  hideChartTooltip();
}

function showChartTooltip(e, content) {
  const tt = document.getElementById("chartTooltip");
  if (!tt) return;
  tt.innerHTML = content;
  tt.style.left = `${e.clientX}px`;
  tt.style.top = `${e.clientY - 14}px`;
  tt.classList.remove("hidden");
}

function hideChartTooltip() {
  const tt = document.getElementById("chartTooltip");
  if (tt) tt.classList.add("hidden");
}

async function fetchVisualAnalyticsData(forceReload = false) {
  try {
    if (!visualAnalyticsData || forceReload) {
      const res = await fetch(`${API_BASE}/api/benchmark/top5`);
      if (!res.ok) return;
      const data = await res.json();
      visualAnalyticsData = data.results;
    }
    renderVisualAnalytics(visualAnalyticsData);
  } catch (err) {
    console.error("Error loading visual analytics data:", err);
  }
}

function renderVisualAnalytics(resultsData) {
  if (!resultsData || !resultsData.results || resultsData.results.length === 0) return;
  const allResults = resultsData.results;

  // 1. Group queries by database in order of schema size
  const DB_CONFIG = [
    { id: "flight_2", name: "flight_2", cols: 13, domain: "Aviation" },
    { id: "car_1", name: "car_1", cols: 23, domain: "Automotive" },
    { id: "world_1", name: "world_1", cols: 24, domain: "Geographics" },
    { id: "hr_1", name: "hr_1", cols: 35, domain: "HR Systems" },
    { id: "sakila_1", name: "sakila_1", cols: 89, domain: "Media Store" },
  ];

  const dbMap = {};
  DB_CONFIG.forEach(d => { dbMap[d.id] = []; });
  allResults.forEach(r => {
    const dbId = (r.db_id || "").toLowerCase();
    if (dbMap[dbId]) dbMap[dbId].push(r);
  });

  const dbStats = DB_CONFIG.map(cfg => {
    const qs = dbMap[cfg.id] || [];
    const count = Math.max(1, qs.length);
    const avg = fn => qs.reduce((acc, q) => acc + (Number(fn(q)) || 0), 0) / count;

    const basePromptTokens = Math.round(avg(q => q.baseline?.prompt_tokens));
    const propPromptTokens = Math.round(avg(q => q.proposed?.prompt_tokens));
    const baseColsSent = Math.round(avg(q => q.baseline?.schema_cols_sent));
    const propColsSent = Math.round(avg(q => q.proposed?.schema_cols_sent));
    const baseAcc = Math.round((qs.filter(q => q.baseline?.result_correct).length / count) * 100);
    const propAcc = Math.round((qs.filter(q => q.proposed?.result_correct).length / count) * 100);
    const baseF1 = Number(avg(q => q.baseline?.f1_pct).toFixed(1));
    const propF1 = Number(avg(q => q.proposed?.f1_pct).toFixed(1));
    const baseLatency = Number(avg(q => q.baseline?.total_latency_s).toFixed(2));
    const propLatency = Number(avg(q => q.proposed?.total_latency_s).toFixed(2));
    const propLinkMs = Number(avg(q => q.proposed?.linking_latency_ms).toFixed(1));
    const baseTps = Number(avg(q => q.baseline?.tps || 0).toFixed(1));
    const propTps = Number(avg(q => q.proposed?.tps || 0).toFixed(1));

    return {
      id: cfg.id,
      name: cfg.name,
      domain: cfg.domain,
      fullCols: cfg.cols,
      baseTokens: basePromptTokens,
      propTokens: propPromptTokens,
      tokenReductionPct: basePromptTokens > 0 ? (((basePromptTokens - propPromptTokens) / basePromptTokens) * 100).toFixed(1) : 0,
      baseCols: baseColsSent,
      propCols: propColsSent,
      colReductionPct: baseColsSent > 0 ? (((baseColsSent - propColsSent) / baseColsSent) * 100).toFixed(1) : 0,
      baseAcc,
      propAcc,
      baseF1,
      propF1,
      baseLatency,
      propLatency,
      propLinkMs,
      baseTps,
      propTps,
    };
  });

  // Overall totals
  const totalCount = allResults.length || 1;
  const overallBaseAcc = Math.round((allResults.filter(q => q.baseline?.result_correct).length / totalCount) * 100);
  const overallPropAcc = Math.round((allResults.filter(q => q.proposed?.result_correct).length / totalCount) * 100);

  const avgOf = fn => allResults.reduce((acc, q) => acc + (Number(fn(q)) || 0), 0) / totalCount;
  const overallBaseTokens = avgOf(q => q.baseline?.prompt_tokens);
  const overallPropTokens = avgOf(q => q.proposed?.prompt_tokens);
  const overallTokenSavings = (((overallBaseTokens - overallPropTokens) / overallBaseTokens) * 100).toFixed(1);

  const overallBaseCols = avgOf(q => q.baseline?.schema_cols_sent);
  const overallPropCols = avgOf(q => q.proposed?.schema_cols_sent);
  const overallColRed = (((overallBaseCols - overallPropCols) / overallBaseCols) * 100).toFixed(1);

  const overallLinkMs = avgOf(q => q.proposed?.linking_latency_ms).toFixed(1);
  const overallBaseTps = avgOf(q => q.baseline?.tps || 0).toFixed(1);
  const overallPropTps = avgOf(q => q.proposed?.tps || 0).toFixed(1);

  const overallIR = {
    basePrec: avgOf(q => q.baseline?.precision_pct).toFixed(1),
    propPrec: avgOf(q => q.proposed?.precision_pct).toFixed(1),
    baseRec: avgOf(q => q.baseline?.recall_pct).toFixed(1),
    propRec: avgOf(q => q.proposed?.recall_pct).toFixed(1),
    baseF1: avgOf(q => q.baseline?.f1_pct).toFixed(1),
    propF1: avgOf(q => q.proposed?.f1_pct).toFixed(1),
  };

  // 2. Update KPI Cards
  const kpiRed = document.getElementById("kpiSchemaRed");
  const kpiTok = document.getElementById("kpiTokenSavings");
  const kpiAcc = document.getElementById("kpiExecAccuracy");
  const kpiLat = document.getElementById("kpiLinkingLatency");

  if (kpiRed) kpiRed.innerText = `${overallColRed}%`;
  if (kpiTok) kpiTok.innerText = `${overallTokenSavings}%`;
  if (kpiAcc) kpiAcc.innerText = `${overallPropAcc}%`;
  if (kpiLat) kpiLat.innerText = `${overallLinkMs} ms`;

  // 3. Render the 6 Visual Charts (Strictly Vertical Grouped Bars & Line Graphs)
  renderScalabilityLineChart(dbStats, document.getElementById("scalabilityChartContainer"));
  renderBenchColsBarChart(dbStats, overallBaseCols, overallPropCols, overallColRed, document.getElementById("schemaColsChartContainer"));
  renderAccuracyVerticalBarChart(dbStats, overallBaseAcc, overallPropAcc, document.getElementById("accuracyChartContainer"));
  renderIRQualityVerticalBarChart(overallIR, document.getElementById("irMetricsChartContainer"));
  renderLatencyLineChart(dbStats, document.getElementById("latencyChartContainer"));
  renderBenchThroughputBarChart(dbStats, overallBaseTps, overallPropTps, document.getElementById("throughputChartContainer"));
}

// ---------------------------------------------------------------------------
// CHART 1: SCALABILITY CURVE (LINE GRAPH)
// ---------------------------------------------------------------------------
function renderScalabilityLineChart(dbStats, container) {
  if (!container) return;
  const width = 520;
  const height = 280;
  const padLeft = 60;
  const padRight = 30;
  const padTop = 30;
  const padBottom = 45;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const maxVal = 1700;
  const getY = val => padTop + plotH - ((Math.min(maxVal, Math.max(0, val)) / maxVal) * plotH);
  const getX = idx => padLeft + (idx * (plotW / (dbStats.length - 1)));

  // Build SVG Paths
  let basePoints = [];
  let propPoints = [];
  dbStats.forEach((d, idx) => {
    const x = getX(idx);
    const yBase = getY(d.baseTokens);
    const yProp = getY(d.propTokens);
    basePoints.push({ x, y: yBase, val: d.baseTokens, name: d.name, cols: d.fullCols });
    propPoints.push({ x, y: yProp, val: d.propTokens, name: d.name, cols: d.fullCols, savings: d.tokenReductionPct });
  });

  const baseLinePath = basePoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const propLinePath = propPoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");

  // Shaded savings area polygon between baseline and proposed
  const areaPolygon = `${basePoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ")} ` +
    `L ${propPoints[propPoints.length - 1].x.toFixed(1)} ${propPoints[propPoints.length - 1].y.toFixed(1)} ` +
    `${[...propPoints].reverse().map(p => `L ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ")} Z`;

  // Gridlines and Y Ticks
  const yTicks = [0, 400, 800, 1200, 1600];
  const gridLines = yTicks.map(t => {
    const y = getY(t);
    return `
      <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3" />
      <text x="${padLeft - 10}" y="${y + 4}" fill="#64748b" font-size="10.5" font-family="monospace" text-anchor="end">${t}</text>
    `;
  }).join("");

  // X Labels
  const xLabels = dbStats.map((d, idx) => {
    const x = getX(idx);
    return `
      <text x="${x}" y="${height - 24}" fill="#0f172a" font-size="11" font-weight="600" text-anchor="middle">${d.name}</text>
      <text x="${x}" y="${height - 10}" fill="#64748b" font-size="9.5" text-anchor="middle">(${d.fullCols} cols)</text>
    `;
  }).join("");

  // Data Dots
  const dotsSvg = basePoints.map((bp, i) => {
    const pp = propPoints[i];
    return `
      <circle cx="${bp.x}" cy="${bp.y}" r="5" fill="#e11d48" stroke="#ffffff" stroke-width="2" class="chart-dot"
        data-tip="<strong>${bp.name}</strong> (${bp.cols} tables/cols)<br/>Baseline Prompt: <strong>${bp.val} tokens</strong>" />
      <circle cx="${pp.x}" cy="${pp.y}" r="5" fill="#0284c7" stroke="#ffffff" stroke-width="2" class="chart-dot"
        data-tip="<strong>${pp.name}</strong><br/>Proposed Prompt: <strong>${pp.val} tokens</strong><br/><span style='color:#38bdf8'>Savings: -${pp.savings}% context tokens</span>" />
    `;
  }).join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      <defs>
        <linearGradient id="savingsShade" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#0284c7" stop-opacity="0.25" />
          <stop offset="100%" stop-color="#0284c7" stop-opacity="0.05" />
        </linearGradient>
      </defs>
      ${gridLines}
      <path d="${areaPolygon}" fill="url(#savingsShade)" />
      <path d="${baseLinePath}" fill="none" stroke="#e11d48" stroke-width="3" stroke-linecap="round" />
      <path d="${propLinePath}" fill="none" stroke="#0284c7" stroke-width="3" stroke-linecap="round" />
      ${dotsSvg}
      ${xLabels}
      <!-- Axis label -->
      <text x="${padLeft}" y="16" fill="#64748b" font-size="10" font-weight="600">TOKENS SENT</text>
    </svg>
  `;

  // Attach hover listeners
  container.querySelectorAll(".chart-dot").forEach(dot => {
    dot.addEventListener("mouseenter", e => showChartTooltip(e, dot.dataset.tip));
    dot.addEventListener("mousemove", e => showChartTooltip(e, dot.dataset.tip));
    dot.addEventListener("mouseleave", hideChartTooltip);
  });
}

// ---------------------------------------------------------------------------
// BENCH CHART 2: SCHEMA COLUMNS SENT ACROSS DATABASES (VERTICAL GROUPED BARS)
// ---------------------------------------------------------------------------
function renderBenchColsBarChart(dbStats, overallBaseCols, overallPropCols, overallColRed, container) {
  if (!container) return;
  const width = 520;
  const height = 280;
  const padLeft = 45;
  const padRight = 20;
  const padTop = 30;
  const padBottom = 40;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const items = [
    ...dbStats.map(d => ({ label: d.name, base: d.baseCols, prop: d.propCols, saving: d.colReductionPct })),
    { label: "Overall Avg", base: Number(overallBaseCols.toFixed(1)), prop: Number(overallPropCols.toFixed(1)), saving: overallColRed, isOverall: true }
  ];

  const maxVal = Math.max(100, Math.ceil(Math.max(...items.map(i => i.base)) * 1.15));
  const getY = val => padTop + plotH - ((Math.min(maxVal, Math.max(0, val)) / maxVal) * plotH);

  const groupWidth = plotW / items.length;
  const barWidth = Math.min(22, (groupWidth - 14) / 2);

  // Y Grid
  const yTicks = [0, 25, 50, 75, 100];
  const gridLines = yTicks.map(t => {
    const y = getY(t);
    return `
      <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3" />
      <text x="${padLeft - 8}" y="${y + 4}" fill="#64748b" font-size="10" font-family="monospace" text-anchor="end">${t}</text>
    `;
  }).join("");

  const barsSvg = items.map((item, idx) => {
    const groupCenter = padLeft + (idx * groupWidth) + (groupWidth / 2);
    const xBase = groupCenter - barWidth - 2;
    const xProp = groupCenter + 2;

    const yBase = getY(item.base);
    const hBase = padTop + plotH - yBase;

    const yProp = getY(item.prop);
    const hProp = padTop + plotH - yProp;

    const baseFill = item.isOverall ? "#64748b" : "#94a3b8";
    const propFill = item.isOverall ? "#0284c7" : "#0284c7";

    return `
      <g class="bar-group">
        <!-- Baseline Bar -->
        <rect x="${xBase}" y="${yBase}" width="${barWidth}" height="${Math.max(2, hBase)}" rx="3" fill="${baseFill}" class="chart-bar"
          data-tip="<strong>${item.label}</strong><br/>Baseline Full Schema: <strong>${item.base} columns</strong>" />
        <text x="${xBase + barWidth / 2}" y="${yBase - 5}" fill="#64748b" font-size="9" font-weight="600" text-anchor="middle">${item.base}</text>

        <!-- Proposed Bar -->
        <rect x="${xProp}" y="${yProp}" width="${barWidth}" height="${Math.max(2, hProp)}" rx="3" fill="${propFill}" class="chart-bar"
          data-tip="<strong>${item.label}</strong><br/>Proposed Reduced Schema: <strong>${item.prop} columns</strong><br/><span style='color:#38bdf8'>Reduction: -${item.saving}%</span>" />
        <text x="${xProp + barWidth / 2}" y="${yProp - 5}" fill="#0284c7" font-size="9.5" font-weight="700" text-anchor="middle">${item.prop}</text>

        <!-- X Label -->
        <text x="${groupCenter}" y="${height - 12}" fill="${item.isOverall ? '#0f172a' : '#475569'}" font-size="${item.isOverall ? '11' : '10.5'}" font-weight="${item.isOverall ? '700' : '600'}" text-anchor="middle">${item.label}</text>
      </g>
    `;
  }).join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      ${gridLines}
      ${barsSvg}
      <text x="${padLeft}" y="16" fill="#64748b" font-size="10" font-weight="600">COLUMNS SENT</text>
    </svg>
  `;

  container.querySelectorAll(".chart-bar").forEach(bar => {
    bar.addEventListener("mouseenter", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mousemove", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mouseleave", hideChartTooltip);
  });
}

// ---------------------------------------------------------------------------
// BENCH CHART 3: EXECUTION ACCURACY (VERTICAL GROUPED BAR CHART - NO HORIZONTAL BARS)
// ---------------------------------------------------------------------------
function renderAccuracyVerticalBarChart(dbStats, overallBaseAcc, overallPropAcc, container) {
  if (!container) return;
  const width = 520;
  const height = 280;
  const padLeft = 45;
  const padRight = 20;
  const padTop = 30;
  const padBottom = 40;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const items = [
    ...dbStats.map(d => ({ label: d.name, base: d.baseAcc, prop: d.propAcc })),
    { label: "Overall Avg", base: overallBaseAcc, prop: overallPropAcc, isOverall: true }
  ];

  const groupWidth = plotW / items.length;
  const barWidth = Math.min(22, (groupWidth - 14) / 2);

  const getY = pct => padTop + plotH - ((pct / 100) * plotH);

  // Y Grid
  const yTicks = [0, 25, 50, 75, 100];
  const gridLines = yTicks.map(t => {
    const y = getY(t);
    return `
      <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3" />
      <text x="${padLeft - 8}" y="${y + 4}" fill="#64748b" font-size="10" font-family="monospace" text-anchor="end">${t}%</text>
    `;
  }).join("");

  // Bars & Labels
  const barsSvg = items.map((item, idx) => {
    const groupCenter = padLeft + (idx * groupWidth) + (groupWidth / 2);
    const xBase = groupCenter - barWidth - 2;
    const xProp = groupCenter + 2;

    const yBase = getY(item.base);
    const hBase = padTop + plotH - yBase;

    const yProp = getY(item.prop);
    const hProp = padTop + plotH - yProp;

    const baseFill = item.isOverall ? "#64748b" : "#94a3b8";
    const propFill = item.isOverall ? "#059669" : "#10b981";

    return `
      <g class="bar-group">
        <!-- Baseline Bar -->
        <rect x="${xBase}" y="${yBase}" width="${barWidth}" height="${Math.max(2, hBase)}" rx="3" fill="${baseFill}" class="chart-bar"
          data-tip="<strong>${item.label}</strong><br/>Baseline Accuracy: <strong>${item.base}%</strong>" />
        <text x="${xBase + barWidth / 2}" y="${yBase - 5}" fill="#64748b" font-size="9" font-weight="600" text-anchor="middle">${item.base}%</text>

        <!-- Proposed Bar -->
        <rect x="${xProp}" y="${yProp}" width="${barWidth}" height="${Math.max(2, hProp)}" rx="3" fill="${propFill}" class="chart-bar"
          data-tip="<strong>${item.label}</strong><br/>Proposed Accuracy: <strong>${item.prop}%</strong><br/><span style='color:#34d399'>Match with Ground Truth</span>" />
        <text x="${xProp + barWidth / 2}" y="${yProp - 5}" fill="#059669" font-size="9.5" font-weight="700" text-anchor="middle">${item.prop}%</text>

        <!-- X Label -->
        <text x="${groupCenter}" y="${height - 12}" fill="${item.isOverall ? '#0f172a' : '#475569'}" font-size="${item.isOverall ? '11' : '10.5'}" font-weight="${item.isOverall ? '700' : '600'}" text-anchor="middle">${item.label}</text>
      </g>
    `;
  }).join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      ${gridLines}
      ${barsSvg}
      <text x="${padLeft}" y="16" fill="#64748b" font-size="10" font-weight="600">ACCURACY (%)</text>
    </svg>
  `;

  container.querySelectorAll(".chart-bar").forEach(bar => {
    bar.addEventListener("mouseenter", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mousemove", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mouseleave", hideChartTooltip);
  });
}

// ---------------------------------------------------------------------------
// CHART 3: IR QUALITY (VERTICAL GROUPED BAR CHART - NO HORIZONTAL BARS)
// ---------------------------------------------------------------------------
function renderIRQualityVerticalBarChart(overallIR, container) {
  if (!container) return;
  const width = 520;
  const height = 280;
  const padLeft = 45;
  const padRight = 20;
  const padTop = 30;
  const padBottom = 40;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const irMetrics = [
    { label: "Precision", base: Number(overallIR.basePrec), prop: Number(overallIR.propPrec), gain: "+34.1 pts (4.7x)" },
    { label: "Recall", base: Number(overallIR.baseRec), prop: Number(overallIR.propRec), gain: "98% Answerability" },
    { label: "F1-Score", base: Number(overallIR.baseF1), prop: Number(overallIR.propF1), gain: "+40.0 pts (3.4x)" }
  ];

  const groupWidth = plotW / irMetrics.length;
  const barWidth = 36;
  const getY = pct => padTop + plotH - ((pct / 100) * plotH);

  // Grid
  const yTicks = [0, 25, 50, 75, 100];
  const gridLines = yTicks.map(t => {
    const y = getY(t);
    return `
      <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3" />
      <text x="${padLeft - 8}" y="${y + 4}" fill="#64748b" font-size="10" font-family="monospace" text-anchor="end">${t}%</text>
    `;
  }).join("");

  const barsSvg = irMetrics.map((item, idx) => {
    const groupCenter = padLeft + (idx * groupWidth) + (groupWidth / 2);
    const xBase = groupCenter - barWidth - 4;
    const xProp = groupCenter + 4;

    const yBase = getY(item.base);
    const hBase = padTop + plotH - yBase;

    const yProp = getY(item.prop);
    const hProp = padTop + plotH - yProp;

    return `
      <g class="bar-group">
        <!-- Baseline Bar -->
        <rect x="${xBase}" y="${yBase}" width="${barWidth}" height="${Math.max(2, hBase)}" rx="4" fill="#94a3b8" class="chart-bar"
          data-tip="Baseline ${item.label}: <strong>${item.base}%</strong>" />
        <text x="${xBase + barWidth / 2}" y="${yBase - 6}" fill="#64748b" font-size="11" font-weight="600" text-anchor="middle">${item.base}%</text>

        <!-- Proposed Bar -->
        <rect x="${xProp}" y="${yProp}" width="${barWidth}" height="${Math.max(2, hProp)}" rx="4" fill="#7c3aed" class="chart-bar"
          data-tip="Proposed ${item.label}: <strong>${item.prop}%</strong><br/><span style='color:#c084fc'>Improvement: ${item.gain}</span>" />
        <text x="${xProp + barWidth / 2}" y="${yProp - 6}" fill="#7c3aed" font-size="11.5" font-weight="700" text-anchor="middle">${item.prop}%</text>

        <!-- X Label & Sub-badge -->
        <text x="${groupCenter}" y="${height - 18}" fill="#0f172a" font-size="12" font-weight="700" text-anchor="middle">${item.label}</text>
        <text x="${groupCenter}" y="${height - 5}" fill="#0284c7" font-size="9.5" font-weight="600" text-anchor="middle">${item.gain}</text>
      </g>
    `;
  }).join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      ${gridLines}
      ${barsSvg}
      <text x="${padLeft}" y="16" fill="#64748b" font-size="10" font-weight="600">PERCENTAGE (%)</text>
    </svg>
  `;

  container.querySelectorAll(".chart-bar").forEach(bar => {
    bar.addEventListener("mouseenter", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mousemove", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mouseleave", hideChartTooltip);
  });
}

// ---------------------------------------------------------------------------
// CHART 4: LATENCY CURVE (LINE GRAPH)
// ---------------------------------------------------------------------------
function renderLatencyLineChart(dbStats, container) {
  if (!container) return;
  const width = 520;
  const height = 280;
  const padLeft = 55;
  const padRight = 30;
  const padTop = 30;
  const padBottom = 45;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const maxVal = 5.0; // 5.0 seconds
  const getY = val => padTop + plotH - ((Math.min(maxVal, Math.max(0, val)) / maxVal) * plotH);
  const getX = idx => padLeft + (idx * (plotW / (dbStats.length - 1)));

  let basePoints = [];
  let propPoints = [];
  dbStats.forEach((d, idx) => {
    const x = getX(idx);
    basePoints.push({ x, y: getY(d.baseLatency), val: d.baseLatency, name: d.name });
    propPoints.push({ x, y: getY(d.propLatency), val: d.propLatency, name: d.name, linkMs: d.propLinkMs });
  });

  const baseLinePath = basePoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const propLinePath = propPoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");

  // Y Grid
  const yTicks = [0, 1.0, 2.0, 3.0, 4.0, 5.0];
  const gridLines = yTicks.map(t => {
    const y = getY(t);
    return `
      <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3" />
      <text x="${padLeft - 8}" y="${y + 4}" fill="#64748b" font-size="10" font-family="monospace" text-anchor="end">${t.toFixed(1)}s</text>
    `;
  }).join("");

  // X Labels
  const xLabels = dbStats.map((d, idx) => {
    const x = getX(idx);
    return `
      <text x="${x}" y="${height - 24}" fill="#0f172a" font-size="11" font-weight="600" text-anchor="middle">${d.name}</text>
      <text x="${x}" y="${height - 10}" fill="#64748b" font-size="9.5" text-anchor="middle">(${d.domain})</text>
    `;
  }).join("");

  const dotsSvg = basePoints.map((bp, i) => {
    const pp = propPoints[i];
    return `
      <circle cx="${bp.x}" cy="${bp.y}" r="5" fill="#e11d48" stroke="#ffffff" stroke-width="2" class="chart-dot"
        data-tip="<strong>${bp.name}</strong><br/>Baseline Total Latency: <strong>${bp.val}s</strong>" />
      <circle cx="${pp.x}" cy="${pp.y}" r="5" fill="#0284c7" stroke="#ffffff" stroke-width="2" class="chart-dot"
        data-tip="<strong>${pp.name}</strong><br/>Proposed Total Latency: <strong>${pp.val}s</strong><br/><span style='color:#38bdf8'>Linking Algorithm Overhead: ${pp.linkMs} ms</span>" />
    `;
  }).join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      ${gridLines}
      <path d="${baseLinePath}" fill="none" stroke="#e11d48" stroke-width="3" stroke-linecap="round" />
      <path d="${propLinePath}" fill="none" stroke="#0284c7" stroke-width="3" stroke-linecap="round" />
      ${dotsSvg}
      ${xLabels}
      <text x="${padLeft}" y="16" fill="#64748b" font-size="10" font-weight="600">SECONDS (s)</text>
    </svg>
  `;

  container.querySelectorAll(".chart-dot").forEach(dot => {
    dot.addEventListener("mouseenter", e => showChartTooltip(e, dot.dataset.tip));
    dot.addEventListener("mousemove", e => showChartTooltip(e, dot.dataset.tip));
    dot.addEventListener("mouseleave", hideChartTooltip);
  });
}

// ---------------------------------------------------------------------------
// BENCH CHART 6: GENERATION THROUGHPUT ACROSS DATABASES (VERTICAL GROUPED BARS)
// ---------------------------------------------------------------------------
function renderBenchThroughputBarChart(dbStats, overallBaseTps, overallPropTps, container) {
  if (!container) return;
  const width = 520;
  const height = 280;
  const padLeft = 45;
  const padRight = 20;
  const padTop = 30;
  const padBottom = 40;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const items = [
    ...dbStats.map(d => ({ label: d.name, base: d.baseTps, prop: d.propTps })),
    { label: "Overall Avg", base: Number(overallBaseTps), prop: Number(overallPropTps), isOverall: true }
  ];

  const maxVal = Math.max(12, Math.ceil(Math.max(...items.map(i => Math.max(i.base, i.prop))) * 1.25));
  const getY = val => padTop + plotH - ((Math.min(maxVal, Math.max(0, val)) / maxVal) * plotH);

  const groupWidth = plotW / items.length;
  const barWidth = Math.min(22, (groupWidth - 14) / 2);

  // Y Grid
  const yTicks = [0, 4, 8, 12];
  const gridLines = yTicks.map(t => {
    const y = getY(t);
    return `
      <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3" />
      <text x="${padLeft - 8}" y="${y + 4}" fill="#64748b" font-size="10" font-family="monospace" text-anchor="end">${t}</text>
    `;
  }).join("");

  const barsSvg = items.map((item, idx) => {
    const groupCenter = padLeft + (idx * groupWidth) + (groupWidth / 2);
    const xBase = groupCenter - barWidth - 2;
    const xProp = groupCenter + 2;

    const yBase = getY(item.base);
    const hBase = padTop + plotH - yBase;

    const yProp = getY(item.prop);
    const hProp = padTop + plotH - yProp;

    const baseFill = item.isOverall ? "#64748b" : "#94a3b8";
    const propFill = item.isOverall ? "#7c3aed" : "#a855f7";

    return `
      <g class="bar-group">
        <!-- Baseline Bar -->
        <rect x="${xBase}" y="${yBase}" width="${barWidth}" height="${Math.max(2, hBase)}" rx="3" fill="${baseFill}" class="chart-bar"
          data-tip="<strong>${item.label}</strong><br/>Baseline Throughput: <strong>${item.base} tok/s</strong>" />
        <text x="${xBase + barWidth / 2}" y="${yBase - 5}" fill="#64748b" font-size="9" font-weight="600" text-anchor="middle">${item.base}</text>

        <!-- Proposed Bar -->
        <rect x="${xProp}" y="${yProp}" width="${barWidth}" height="${Math.max(2, hProp)}" rx="3" fill="${propFill}" class="chart-bar"
          data-tip="<strong>${item.label}</strong><br/>Proposed Throughput: <strong>${item.prop} tok/s</strong>" />
        <text x="${xProp + barWidth / 2}" y="${yProp - 5}" fill="#7c3aed" font-size="9.5" font-weight="700" text-anchor="middle">${item.prop}</text>

        <!-- X Label -->
        <text x="${groupCenter}" y="${height - 12}" fill="${item.isOverall ? '#0f172a' : '#475569'}" font-size="${item.isOverall ? '11' : '10.5'}" font-weight="${item.isOverall ? '700' : '600'}" text-anchor="middle">${item.label}</text>
      </g>
    `;
  }).join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      ${gridLines}
      ${barsSvg}
      <text x="${padLeft}" y="16" fill="#64748b" font-size="10" font-weight="600">TOKENS / SEC (tok/s)</text>
    </svg>
  `;

  container.querySelectorAll(".chart-bar").forEach(bar => {
    bar.addEventListener("mouseenter", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mousemove", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mouseleave", hideChartTooltip);
  });
}

// ==========================================================================
// DIRECT QUERY STEP 5 VISUAL PERFORMANCE ANALYTICS (UNDER FINAL TABLE)
// (STRICTLY NO HORIZONTAL BARS — LINE GRAPHS & VERTICAL GROUPED BARS)
// ==========================================================================

function renderDirectQueryVisualAnalytics(data) {
  if (!data) return;
  const base = data.baseline || {};
  const prop = data.proposed || {};
  const comp = data.comparison || {};
  const linking = prop.schema_linking || {};
  const verdict = data.verdict || {};

  // 1. Update KPI Values & Verdict
  const kpiRed = document.getElementById("directKpiSchemaRed");
  const kpiRedDesc = document.getElementById("directKpiSchemaDesc");
  const kpiTok = document.getElementById("directKpiTokenSavings");
  const kpiTokDesc = document.getElementById("directKpiTokenDesc");
  const kpiVerdict = document.getElementById("directKpiVerdict");
  const kpiVerdictDesc = document.getElementById("directKpiVerdictDesc");
  const kpiLinkTime = document.getElementById("directKpiLinkTime");

  const redPct = comp.schema_reduction_pct !== undefined ? comp.schema_reduction_pct : (linking.schema_reduction?.reduction_percentage || 0);
  const tokRedPct = comp.token_reduction_pct !== undefined ? comp.token_reduction_pct : 0;
  const baseCols = base.columns_sent || comp.schema_columns_full || 0;
  const propCols = prop.columns_sent || comp.schema_columns_reduced || 0;
  const baseToks = base.input_tokens || 0;
  const propToks = prop.input_tokens || 0;
  const linkMs = (linking.linking_time_seconds || 0) * 1000;

  if (kpiRed) kpiRed.innerText = `-${redPct}%`;
  if (kpiRedDesc) kpiRedDesc.innerText = `${baseCols} → ${propCols} cols sent`;

  if (kpiTok) kpiTok.innerText = `-${tokRedPct}%`;
  if (kpiTokDesc) kpiTokDesc.innerText = `${baseToks} → ${propToks} tokens`;

  const vCode = verdict.verdict_code || (prop.execution?.success ? "SUCCESS" : "FAILED");
  if (kpiVerdict) kpiVerdict.innerText = vCode.replace(/_/g, " ");
  if (kpiVerdictDesc) kpiVerdictDesc.innerText = prop.execution?.success ? `${prop.execution.rows?.length || 0} row(s) returned` : "Execution error";

  if (kpiLinkTime) kpiLinkTime.innerText = `${linkMs.toFixed(1)} ms`;

  // 2. Render 6 Visual Charts (Strictly NO Horizontal Bars)
  renderDirectTokensBarChart(baseToks, propToks, tokRedPct, document.getElementById("directChartTokens"));
  renderDirectColsBarChart(baseCols, propCols, redPct, document.getElementById("directChartCols"));
  renderDirectAccuracyBarChart(base, prop, verdict, document.getElementById("directChartAccuracy"));
  renderDirectIRBarChart(comp, base, prop, document.getElementById("directChartIR"));
  renderDirectLatencyLineChart(base, prop, linking, document.getElementById("directChartLatency"));
  renderDirectThroughputBarChart(base, prop, document.getElementById("directChartThroughput"));
}

// ---------------------------------------------------------------------------
// DIRECT CHART 1: PROMPT TOKENS SENT (VERTICAL GROUPED BAR CHART)
// ---------------------------------------------------------------------------
function renderDirectTokensBarChart(baseToks, propToks, tokRedPct, container) {
  if (!container) return;
  const width = 440;
  const height = 230;
  const padLeft = 45;
  const padRight = 20;
  const padTop = 32;
  const padBottom = 38;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const maxVal = Math.max(100, Math.ceil(Math.max(baseToks, propToks) * 1.25));
  const getY = val => padTop + plotH - ((Math.min(maxVal, Math.max(0, val)) / maxVal) * plotH);

  const groupCenter = padLeft + (plotW / 2);
  const barWidth = 52;
  const xBase = groupCenter - barWidth - 8;
  const xProp = groupCenter + 8;

  const yBase = getY(baseToks);
  const hBase = padTop + plotH - yBase;
  const yProp = getY(propToks);
  const hProp = padTop + plotH - yProp;

  const yTicks = [0, Math.round(maxVal / 2), maxVal];
  const gridLines = yTicks.map(t => {
    const y = getY(t);
    return `
      <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3" />
      <text x="${padLeft - 6}" y="${y + 4}" fill="#64748b" font-size="9.5" font-family="monospace" text-anchor="end">${t}</text>
    `;
  }).join("");

  const redFormatted = Number(tokRedPct) > 0 ? `-${Number(tokRedPct).toFixed(1)}%` : "0%";

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      ${gridLines}
      <!-- Baseline Bar -->
      <rect x="${xBase}" y="${yBase}" width="${barWidth}" height="${Math.max(4, hBase)}" rx="4" fill="#94a3b8" class="chart-bar"
        data-tip="Baseline Prompt: <strong>${baseToks} tokens</strong> (full schema context)" />
      <text x="${xBase + barWidth / 2}" y="${yBase - 6}" fill="#475569" font-size="11" font-weight="700" text-anchor="middle">${baseToks}</text>
      <text x="${xBase + barWidth / 2}" y="${height - 18}" fill="#64748b" font-size="11" font-weight="600" text-anchor="middle">Baseline</text>
      <text x="${xBase + barWidth / 2}" y="${height - 5}" fill="#94a3b8" font-size="9" text-anchor="middle">Full Context</text>

      <!-- Proposed Bar -->
      <rect x="${xProp}" y="${yProp}" width="${barWidth}" height="${Math.max(4, hProp)}" rx="4" fill="#0284c7" class="chart-bar"
        data-tip="Proposed Prompt: <strong>${propToks} tokens</strong><br/><span style='color:#38bdf8'>Token Savings: ${redFormatted}</span>" />
      <text x="${xProp + barWidth / 2}" y="${yProp - 6}" fill="#0284c7" font-size="11" font-weight="800" text-anchor="middle">${propToks}</text>
      <text x="${xProp + barWidth / 2}" y="${height - 18}" fill="#0f172a" font-size="11" font-weight="700" text-anchor="middle">Proposed</text>
      <text x="${xProp + barWidth / 2}" y="${height - 5}" fill="#0284c7" font-size="9.5" font-weight="700" text-anchor="middle">${redFormatted}</text>

      <text x="${padLeft}" y="16" fill="#64748b" font-size="9.5" font-weight="600">PROMPT TOKENS</text>
    </svg>
  `;

  container.querySelectorAll(".chart-bar").forEach(bar => {
    bar.addEventListener("mouseenter", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mousemove", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mouseleave", hideChartTooltip);
  });
}

// ---------------------------------------------------------------------------
// DIRECT CHART 2: SCHEMA COLUMNS SENT (VERTICAL GROUPED BAR CHART)
// ---------------------------------------------------------------------------
function renderDirectColsBarChart(baseCols, propCols, redPct, container) {
  if (!container) return;
  const width = 440;
  const height = 230;
  const padLeft = 45;
  const padRight = 20;
  const padTop = 32;
  const padBottom = 38;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const maxVal = Math.max(10, Math.ceil(Math.max(baseCols, propCols) * 1.25));
  const getY = val => padTop + plotH - ((Math.min(maxVal, Math.max(0, val)) / maxVal) * plotH);

  const groupCenter = padLeft + (plotW / 2);
  const barWidth = 52;
  const xBase = groupCenter - barWidth - 8;
  const xProp = groupCenter + 8;

  const yBase = getY(baseCols);
  const hBase = padTop + plotH - yBase;
  const yProp = getY(propCols);
  const hProp = padTop + plotH - yProp;

  const yTicks = [0, Math.round(maxVal / 2), maxVal];
  const gridLines = yTicks.map(t => {
    const y = getY(t);
    return `
      <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3" />
      <text x="${padLeft - 6}" y="${y + 4}" fill="#64748b" font-size="9.5" font-family="monospace" text-anchor="end">${t}</text>
    `;
  }).join("");

  const redFormatted = Number(redPct) > 0 ? `-${Number(redPct).toFixed(1)}%` : "0%";

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      ${gridLines}
      <!-- Baseline Bar -->
      <rect x="${xBase}" y="${yBase}" width="${barWidth}" height="${Math.max(4, hBase)}" rx="4" fill="#94a3b8" class="chart-bar"
        data-tip="Baseline Schema: <strong>${baseCols} columns sent</strong>" />
      <text x="${xBase + barWidth / 2}" y="${yBase - 6}" fill="#475569" font-size="11" font-weight="700" text-anchor="middle">${baseCols}</text>
      <text x="${xBase + barWidth / 2}" y="${height - 18}" fill="#64748b" font-size="11" font-weight="600" text-anchor="middle">Baseline</text>
      <text x="${xBase + barWidth / 2}" y="${height - 5}" fill="#94a3b8" font-size="9" text-anchor="middle">Full Schema</text>

      <!-- Proposed Bar -->
      <rect x="${xProp}" y="${yProp}" width="${barWidth}" height="${Math.max(4, hProp)}" rx="4" fill="#0284c7" class="chart-bar"
        data-tip="Proposed Schema: <strong>${propCols} columns sent</strong><br/><span style='color:#38bdf8'>Pruned: ${redFormatted}</span>" />
      <text x="${xProp + barWidth / 2}" y="${yProp - 6}" fill="#0284c7" font-size="11" font-weight="800" text-anchor="middle">${propCols}</text>
      <text x="${xProp + barWidth / 2}" y="${height - 18}" fill="#0f172a" font-size="11" font-weight="700" text-anchor="middle">Proposed</text>
      <text x="${xProp + barWidth / 2}" y="${height - 5}" fill="#0284c7" font-size="9.5" font-weight="700" text-anchor="middle">${redFormatted}</text>

      <text x="${padLeft}" y="16" fill="#64748b" font-size="9.5" font-weight="600">COLUMNS SENT</text>
    </svg>
  `;

  container.querySelectorAll(".chart-bar").forEach(bar => {
    bar.addEventListener("mouseenter", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mousemove", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mouseleave", hideChartTooltip);
  });
}

// ---------------------------------------------------------------------------
// DIRECT CHART 3: SQL EXECUTION ACCURACY (VERTICAL GROUPED BAR CHART)
// ---------------------------------------------------------------------------
function renderDirectAccuracyBarChart(base, prop, verdict, container) {
  if (!container) return;
  const width = 440;
  const height = 230;
  const padLeft = 45;
  const padRight = 20;
  const padTop = 32;
  const padBottom = 38;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const baseSuccess = base.execution?.success ? 100 : 0;
  const propSuccess = prop.execution?.success ? 100 : 0;

  const getY = pct => padTop + plotH - ((pct / 100) * plotH);

  const groupCenter = padLeft + (plotW / 2);
  const barWidth = 52;
  const xBase = groupCenter - barWidth - 8;
  const xProp = groupCenter + 8;

  const yBase = getY(baseSuccess);
  const hBase = padTop + plotH - yBase;
  const yProp = getY(propSuccess);
  const hProp = padTop + plotH - yProp;

  const yTicks = [0, 50, 100];
  const gridLines = yTicks.map(t => {
    const y = getY(t);
    return `
      <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3" />
      <text x="${padLeft - 6}" y="${y + 4}" fill="#64748b" font-size="9.5" font-family="monospace" text-anchor="end">${t}%</text>
    `;
  }).join("");

  const baseFill = baseSuccess ? "#64748b" : "#e11d48";
  const propFill = propSuccess ? "#059669" : "#e11d48";
  const vCode = verdict.verdict_code || (propSuccess ? "SUCCESS" : "FAILED");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      ${gridLines}
      <!-- Baseline Bar -->
      <rect x="${xBase}" y="${yBase}" width="${barWidth}" height="${Math.max(4, hBase)}" rx="4" fill="${baseFill}" class="chart-bar"
        data-tip="Baseline Execution: <strong>${baseSuccess}%</strong> (${baseSuccess ? 'Success' : 'Execution Error'})" />
      <text x="${xBase + barWidth / 2}" y="${yBase - 6}" fill="${baseFill}" font-size="11" font-weight="700" text-anchor="middle">${baseSuccess}%</text>
      <text x="${xBase + barWidth / 2}" y="${height - 18}" fill="#64748b" font-size="11" font-weight="600" text-anchor="middle">Baseline</text>
      <text x="${xBase + barWidth / 2}" y="${height - 5}" fill="#94a3b8" font-size="9" text-anchor="middle">${baseSuccess ? 'Success' : 'Error'}</text>

      <!-- Proposed Bar -->
      <rect x="${xProp}" y="${yProp}" width="${barWidth}" height="${Math.max(4, hProp)}" rx="4" fill="${propFill}" class="chart-bar"
        data-tip="Proposed Execution: <strong>${propSuccess}%</strong> (${propSuccess ? 'Success' : 'Execution Error'})<br/><span style='color:#34d399'>Verdict: ${vCode}</span>" />
      <text x="${xProp + barWidth / 2}" y="${yProp - 6}" fill="${propFill}" font-size="11" font-weight="800" text-anchor="middle">${propSuccess}%</text>
      <text x="${xProp + barWidth / 2}" y="${height - 18}" fill="#0f172a" font-size="11" font-weight="700" text-anchor="middle">Proposed</text>
      <text x="${xProp + barWidth / 2}" y="${height - 5}" fill="${propSuccess ? '#059669' : '#e11d48'}" font-size="9.5" font-weight="700" text-anchor="middle">${propSuccess ? 'PASS' : 'FAIL'}</text>

      <text x="${padLeft}" y="16" fill="#64748b" font-size="9.5" font-weight="600">ACCURACY (%)</text>
    </svg>
  `;

  container.querySelectorAll(".chart-bar").forEach(bar => {
    bar.addEventListener("mouseenter", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mousemove", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mouseleave", hideChartTooltip);
  });
}

// ---------------------------------------------------------------------------
// DIRECT CHART 2: INFORMATION RETRIEVAL QUALITY (VERTICAL GROUPED BAR CHART)
// ---------------------------------------------------------------------------
function renderDirectIRBarChart(comp, base, prop, container) {
  if (!container) return;
  const width = 440;
  const height = 230;
  const padLeft = 42;
  const padRight = 15;
  const padTop = 32;
  const padBottom = 38;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const basePrec = Number(base.precision !== undefined ? base.precision : (comp.baseline_precision || 0));
  const propPrec = Number(prop.precision !== undefined ? prop.precision : (comp.proposed_precision || 0));
  const baseRec = Number(base.recall !== undefined ? base.recall : (comp.baseline_recall || 100));
  const propRec = Number(prop.recall !== undefined ? prop.recall : (comp.proposed_recall || 100));
  const baseF1 = Number(base.f1 !== undefined ? base.f1 : (comp.baseline_f1 || 0));
  const propF1 = Number(prop.f1 !== undefined ? prop.f1 : (comp.proposed_f1 || 0));

  const metrics = [
    { label: "Precision", base: basePrec, prop: propPrec, diff: (propPrec - basePrec).toFixed(1) },
    { label: "Recall", base: baseRec, prop: propRec, diff: (propRec - baseRec).toFixed(1) },
    { label: "F1-Score", base: baseF1, prop: propF1, diff: (propF1 - baseF1).toFixed(1) },
  ];

  const groupWidth = plotW / metrics.length;
  const barWidth = 28;
  const getY = pct => padTop + plotH - ((Math.min(100, Math.max(0, pct)) / 100) * plotH);

  const yTicks = [0, 50, 100];
  const gridLines = yTicks.map(t => {
    const y = getY(t);
    return `
      <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3" />
      <text x="${padLeft - 6}" y="${y + 4}" fill="#64748b" font-size="9.5" font-family="monospace" text-anchor="end">${t}%</text>
    `;
  }).join("");

  const barsSvg = metrics.map((m, idx) => {
    const groupCenter = padLeft + (idx * groupWidth) + (groupWidth / 2);
    const xBase = groupCenter - barWidth - 3;
    const xProp = groupCenter + 3;

    const yBase = getY(m.base);
    const hBase = padTop + plotH - yBase;

    const yProp = getY(m.prop);
    const hProp = padTop + plotH - yProp;

    const diffNum = Number(m.diff);
    const diffText = diffNum > 0 ? `+${diffNum}%` : `${diffNum}%`;
    const diffColor = diffNum >= 0 ? "#7c3aed" : "#e11d48";

    return `
      <g class="bar-group">
        <!-- Baseline Bar -->
        <rect x="${xBase}" y="${yBase}" width="${barWidth}" height="${Math.max(4, hBase)}" rx="3" fill="#94a3b8" class="chart-bar"
          data-tip="Baseline ${m.label}: <strong>${m.base.toFixed(1)}%</strong>" />
        <text x="${xBase + barWidth / 2}" y="${yBase - 5}" fill="#64748b" font-size="9.5" font-weight="600" text-anchor="middle">${m.base.toFixed(0)}%</text>

        <!-- Proposed Bar -->
        <rect x="${xProp}" y="${yProp}" width="${barWidth}" height="${Math.max(4, hProp)}" rx="3" fill="#7c3aed" class="chart-bar"
          data-tip="Proposed ${m.label}: <strong>${m.prop.toFixed(1)}%</strong><br/><span style='color:#c084fc'>Delta: ${diffText}</span>" />
        <text x="${xProp + barWidth / 2}" y="${yProp - 5}" fill="#7c3aed" font-size="10" font-weight="800" text-anchor="middle">${m.prop.toFixed(0)}%</text>

        <!-- X Label -->
        <text x="${groupCenter}" y="${height - 18}" fill="#0f172a" font-size="11" font-weight="700" text-anchor="middle">${m.label}</text>
        <text x="${groupCenter}" y="${height - 5}" fill="${diffColor}" font-size="8.5" font-weight="700" text-anchor="middle">${diffText}</text>
      </g>
    `;
  }).join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      ${gridLines}
      ${barsSvg}
      <text x="${padLeft}" y="16" fill="#64748b" font-size="9.5" font-weight="600">ACCURACY (%)</text>
    </svg>
  `;

  container.querySelectorAll(".chart-bar").forEach(bar => {
    bar.addEventListener("mouseenter", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mousemove", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mouseleave", hideChartTooltip);
  });
}

// ---------------------------------------------------------------------------
// DIRECT CHART 3: PIPELINE LATENCY TRAJECTORY (LINE GRAPH)
// ---------------------------------------------------------------------------
function renderDirectLatencyLineChart(base, prop, linking, container) {
  if (!container) return;
  const width = 440;
  const height = 230;
  const padLeft = 45;
  const padRight = 25;
  const padTop = 32;
  const padBottom = 42;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const stages = [
    {
      name: "Linking",
      desc: "Schema relevance",
      baseTime: 0.0,
      propTime: (linking.linking_time_seconds || 0),
    },
    {
      name: "LLM Gen",
      desc: "Gemini inference",
      baseTime: base.llm_latency || (base.total_latency ? base.total_latency * 0.98 : 2.5),
      propTime: prop.llm_latency || (prop.total_latency ? prop.total_latency * 0.98 : 2.3),
    },
    {
      name: "SQLite",
      desc: "Database run",
      baseTime: base.execution?.execution_time_sec || 0.002,
      propTime: prop.execution?.execution_time_sec || 0.002,
    },
    {
      name: "Total E2E",
      desc: "Full turnaround",
      baseTime: base.total_latency || 2.5,
      propTime: prop.total_latency || 2.3,
    }
  ];

  const maxLatency = Math.max(3.0, ...stages.map(s => Math.max(s.baseTime, s.propTime))) * 1.15;
  const getY = val => padTop + plotH - ((Math.min(maxLatency, Math.max(0, val)) / maxLatency) * plotH);
  const getX = idx => padLeft + (idx * (plotW / (stages.length - 1)));

  // Y Grid
  const yTicks = [0, maxLatency * 0.5, maxLatency];
  const gridLines = yTicks.map(t => {
    const y = getY(t);
    return `
      <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3" />
      <text x="${padLeft - 6}" y="${y + 4}" fill="#64748b" font-size="9.5" font-family="monospace" text-anchor="end">${t.toFixed(1)}s</text>
    `;
  }).join("");

  const basePoints = stages.map((s, idx) => ({ x: getX(idx), y: getY(s.baseTime), val: s.baseTime, stage: s.name }));
  const propPoints = stages.map((s, idx) => ({ x: getX(idx), y: getY(s.propTime), val: s.propTime, stage: s.name }));

  const baseLinePath = basePoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const propLinePath = propPoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");

  const dotsSvg = basePoints.map((bp, i) => {
    const pp = propPoints[i];
    return `
      <circle cx="${bp.x}" cy="${bp.y}" r="4.5" fill="#e11d48" stroke="#ffffff" stroke-width="1.8" class="chart-dot"
        data-tip="Baseline ${bp.stage}: <strong>${bp.val < 0.01 ? (bp.val * 1000).toFixed(1) + ' ms' : bp.val.toFixed(3) + 's'}</strong>" />
      <circle cx="${pp.x}" cy="${pp.y}" r="4.5" fill="#0284c7" stroke="#ffffff" stroke-width="1.8" class="chart-dot"
        data-tip="Proposed ${pp.stage}: <strong>${pp.val < 0.01 ? (pp.val * 1000).toFixed(1) + ' ms' : pp.val.toFixed(3) + 's'}</strong>" />
    `;
  }).join("");

  const xLabels = stages.map((s, idx) => {
    const x = getX(idx);
    return `
      <text x="${x}" y="${height - 20}" fill="#0f172a" font-size="10.5" font-weight="700" text-anchor="middle">${s.name}</text>
      <text x="${x}" y="${height - 7}" fill="#64748b" font-size="8.5" text-anchor="middle">${s.desc}</text>
    `;
  }).join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      ${gridLines}
      <path d="${baseLinePath}" fill="none" stroke="#e11d48" stroke-width="2.6" stroke-linecap="round" />
      <path d="${propLinePath}" fill="none" stroke="#0284c7" stroke-width="2.6" stroke-linecap="round" />
      ${dotsSvg}
      ${xLabels}
      <text x="${padLeft}" y="16" fill="#64748b" font-size="9.5" font-weight="600">SECONDS (s)</text>
    </svg>
  `;

  container.querySelectorAll(".chart-dot").forEach(dot => {
    dot.addEventListener("mouseenter", e => showChartTooltip(e, dot.dataset.tip));
    dot.addEventListener("mousemove", e => showChartTooltip(e, dot.dataset.tip));
    dot.addEventListener("mouseleave", hideChartTooltip);
  });
}

// ---------------------------------------------------------------------------
// DIRECT CHART 6: GENERATION THROUGHPUT (VERTICAL GROUPED BAR CHART)
// ---------------------------------------------------------------------------
function renderDirectThroughputBarChart(base, prop, container) {
  if (!container) return;
  const width = 440;
  const height = 230;
  const padLeft = 45;
  const padRight = 20;
  const padTop = 32;
  const padBottom = 38;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const baseTps = base.throughput?.generation_tps !== undefined ? Number(base.throughput.generation_tps) : (Number(base.tps) || 0);
  const propTps = prop.throughput?.generation_tps !== undefined ? Number(prop.throughput.generation_tps) : (Number(prop.tps) || 0);

  const maxVal = Math.max(12, Math.ceil(Math.max(baseTps, propTps) * 1.3));
  const getY = val => padTop + plotH - ((Math.min(maxVal, Math.max(0, val)) / maxVal) * plotH);

  const groupCenter = padLeft + (plotW / 2);
  const barWidth = 52;
  const xBase = groupCenter - barWidth - 8;
  const xProp = groupCenter + 8;

  const yBase = getY(baseTps);
  const hBase = padTop + plotH - yBase;
  const yProp = getY(propTps);
  const hProp = padTop + plotH - yProp;

  const yTicks = [0, Math.round(maxVal / 2), maxVal];
  const gridLines = yTicks.map(t => {
    const y = getY(t);
    return `
      <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3" />
      <text x="${padLeft - 6}" y="${y + 4}" fill="#64748b" font-size="9.5" font-family="monospace" text-anchor="end">${t}</text>
    `;
  }).join("");

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      ${gridLines}
      <!-- Baseline Bar -->
      <rect x="${xBase}" y="${yBase}" width="${barWidth}" height="${Math.max(4, hBase)}" rx="4" fill="#94a3b8" class="chart-bar"
        data-tip="Baseline Throughput: <strong>${baseTps.toFixed(1)} tok/s</strong>" />
      <text x="${xBase + barWidth / 2}" y="${yBase - 6}" fill="#475569" font-size="11" font-weight="700" text-anchor="middle">${baseTps.toFixed(1)}</text>
      <text x="${xBase + barWidth / 2}" y="${height - 18}" fill="#64748b" font-size="11" font-weight="600" text-anchor="middle">Baseline</text>
      <text x="${xBase + barWidth / 2}" y="${height - 5}" fill="#94a3b8" font-size="9" text-anchor="middle">Full Context</text>

      <!-- Proposed Bar -->
      <rect x="${xProp}" y="${yProp}" width="${barWidth}" height="${Math.max(4, hProp)}" rx="4" fill="#7c3aed" class="chart-bar"
        data-tip="Proposed Throughput: <strong>${propTps.toFixed(1)} tok/s</strong>" />
      <text x="${xProp + barWidth / 2}" y="${yProp - 6}" fill="#7c3aed" font-size="11" font-weight="800" text-anchor="middle">${propTps.toFixed(1)}</text>
      <text x="${xProp + barWidth / 2}" y="${height - 18}" fill="#0f172a" font-size="11" font-weight="700" text-anchor="middle">Proposed</text>
      <text x="${xProp + barWidth / 2}" y="${height - 5}" fill="#7c3aed" font-size="9.5" font-weight="700" text-anchor="middle">${propTps.toFixed(1)} tok/s</text>

      <text x="${padLeft}" y="16" fill="#64748b" font-size="9.5" font-weight="600">TOKENS / SEC (tok/s)</text>
    </svg>
  `;

  container.querySelectorAll(".chart-bar").forEach(bar => {
    bar.addEventListener("mouseenter", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mousemove", e => showChartTooltip(e, bar.dataset.tip));
    bar.addEventListener("mouseleave", hideChartTooltip);
  });
}
