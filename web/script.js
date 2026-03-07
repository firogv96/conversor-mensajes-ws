// Translation Dictionary
let currentLang = navigator.language.startsWith("es") ? "es" : "en";

function applyLanguage() {
  const t = translations[currentLang];
  document.documentElement.lang = currentLang;

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (t[key]) {
      if (el.tagName === "INPUT" && el.type === "text") {
        el.placeholder = t[key];
      } else if (el.tagName === "OPTION") {
        el.textContent = t[key];
      } else {
        let replaced = false;
        for (let node of el.childNodes) {
          if (node.nodeType === 3 && node.nodeValue.trim().length > 0) {
            node.nodeValue = " " + t[key] + " ";
            replaced = true;
            break;
          }
        }
        if (!replaced) el.textContent = t[key];
      }
    }
  });

  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    const key = el.getAttribute("data-i18n-title");
    if (t[key]) el.title = t[key];
  });

  document.title = t.title;

  const pA = document.getElementById("person-a");
  const pB = document.getElementById("person-b");
  if (pA && pA.options.length > 0 && currentNames.length === 0) {
    if (
      pA.options[0].textContent.includes("Esperando") ||
      pA.options[0].textContent.includes("Waiting")
    ) {
      pA.options[0].textContent = t.waitingFile;
      pB.options[0].textContent = t.waitingFile;
    } else {
      pA.options[0].textContent = t.notDetected;
      pB.options[0].textContent = t.notDetected;
    }
  }
}

function toggleLanguage() {
  currentLang = currentLang === "es" ? "en" : "es";
  applyLanguage();
}

// Global State
let selectedFilePath = "";
let dateRowIdCounter = 0;
let currentNames = [];

async function selectFile() {
  try {
    document.getElementById("drop-empty").style.display = "none";
    document.getElementById("drop-filled").style.display = "none";
    const loadingDiv = document.getElementById("drop-loading");
    if (loadingDiv) loadingDiv.style.display = "flex";
    document.getElementById("drop-zone").classList.remove("zone-filled");

    const response = await eel.select_file()();

    if (response && response.success) {
      selectedFilePath = response.filepath;

      // Update UI
      const filename = selectedFilePath.split("\\").pop().split("/").pop();
      const fileNameEl = document.getElementById("file-name");
      fileNameEl.textContent = filename;

      if (loadingDiv) loadingDiv.style.display = "none";
      document.getElementById("drop-empty").style.display = "none";
      document.getElementById("drop-filled").style.display = "flex";
      document.getElementById("drop-zone").classList.add("zone-filled");

      // Enable and populate participants
      const pA = document.getElementById("person-a");
      const pB = document.getElementById("person-b");
      const aA = document.getElementById("alias-a");
      const aB = document.getElementById("alias-b");

      pA.disabled = false;
      pB.disabled = false;
      aA.disabled = false;
      aB.disabled = false;

      pA.innerHTML = "";
      pB.innerHTML = "";

      if (response.names.length === 0) {
        const t = translations[currentLang];
        pA.innerHTML = `<option>${t.notDetected}</option>`;
        pB.innerHTML = `<option>${t.notDetected}</option>`;
        currentNames = [];
      } else {
        currentNames = response.names;
        response.names.forEach((name) => {
          const opt1 = document.createElement("option");
          opt1.value = name;
          opt1.textContent = name;
          pA.appendChild(opt1);

          const opt2 = document.createElement("option");
          opt2.value = name;
          opt2.textContent = name;
          pB.appendChild(opt2);
        });

        // Set initial selections
        if (response.names.length >= 2) {
          pA.selectedIndex = 0;
          pB.selectedIndex = 1;
        }
      }

      // Set default output path
      document.getElementById("out-path").value = response.default_out;

      // Enable generate button
      document.getElementById("btn-generate").disabled = false;
    } else {
      clearFile(null);
    }
  } catch (e) {
    console.error(e);
    const t = translations[currentLang];
    showAlert(t.alertErrorLoad, t.alertNotice);
    clearFile(null);
  }
}

function clearFile(event) {
  if (event) event.stopPropagation();
  selectedFilePath = "";

  document.getElementById("drop-empty").style.display = "flex";
  const loadingDiv = document.getElementById("drop-loading");
  if (loadingDiv) loadingDiv.style.display = "none";
  document.getElementById("drop-filled").style.display = "none";
  document.getElementById("drop-zone").classList.remove("zone-filled");

  const pA = document.getElementById("person-a");
  const pB = document.getElementById("person-b");
  const aA = document.getElementById("alias-a");
  const aB = document.getElementById("alias-b");

  pA.disabled = true;
  pB.disabled = true;
  aA.disabled = true;
  aB.disabled = true;

  const t = translations[currentLang];
  pA.innerHTML = `<option>${t.waitingFile}</option>`;
  pB.innerHTML = `<option>${t.waitingFile}</option>`;
  aA.value = "";
  aB.value = "";
  currentNames = [];

  document.getElementById("out-path").value = "";
  document.getElementById("btn-generate").disabled = true;
}

function addDateRow() {
  const container = document.getElementById("dates-container");
  const t = translations[currentLang];
  const rowId = dateRowIdCounter++;

  const row = document.createElement("div");
  row.className = "date-row";
  row.id = `daterow-${rowId}`;

  row.innerHTML = `
        <input type="text" placeholder="${t.dateStart}" class="date-start">
        <input type="text" placeholder="${t.dateEnd}" class="date-end">
        <button class="btn-icon-danger" onclick="removeDateRow(${rowId})" title="${t.delRangeTitle}">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>
    `;

  container.appendChild(row);
}

function removeDateRow(id) {
  const row = document.getElementById(`daterow-${id}`);
  if (row) {
    row.remove();
  }
}

async function browseOutput() {
  try {
    const filepath = await eel.select_output_file()();
    if (filepath) {
      document.getElementById("out-path").value = filepath;
    }
  } catch (e) {
    console.error(e);
  }
}

function showInfo() {
  document.getElementById("info-modal").classList.add("show");
}

function closeInfo(event) {
  if (event) event.preventDefault();
  document.getElementById("info-modal").classList.remove("show");
}

function showAlert(message, title = "Aviso") {
  document.getElementById("alert-title").textContent = title;
  document.getElementById("alert-message").textContent = message;
  document.getElementById("alert-modal").classList.add("show");
}

function closeAlert(event) {
  if (event) event.preventDefault();
  document.getElementById("alert-modal").classList.remove("show");
}

async function generateHtml() {
  const btn = document.getElementById("btn-generate");
  const t = translations[currentLang];
  btn.disabled = true;
  btn.innerHTML = `${t.btnGenerating} <span style="display:inline-block;animation:spin 1s linear infinite;">⏳</span>`;

  // Gather date filters
  const dateRows = document.querySelectorAll(".date-row");
  const dateFilters = [];
  dateRows.forEach((row) => {
    const start = row.querySelector(".date-start").value.trim();
    const end = row.querySelector(".date-end").value.trim();
    if (start || end) {
      dateFilters.push({ start, end });
    }
  });

  const config = {
    lang: currentLang,
    person_a: document.getElementById("person-a").value,
    person_b: document.getElementById("person-b").value,
    alias_a: document.getElementById("alias-a").value,
    alias_b: document.getElementById("alias-b").value,
    time_format: document.getElementById("time-format").value,
    ui_density: document.getElementById("ui-density").value,
    text_size: document.getElementById("text-size").value,
    columns: document.getElementById("columns-count").value,
    show_name: document.getElementById("show-name").checked,
    date_filters: dateFilters,
    out_path: document.getElementById("out-path").value,
    auto_open: document.getElementById("auto-open").checked,
  };

  try {
    const response = await eel.generate_html(config)();
    if (response.error) {
      showAlert(`${response.error}`, t.alertNotice);
    } else {
      showAlert(response.success, t.alertCompleted);
    }
  } catch (e) {
    console.error(e);
    showAlert(
      `${t.alertErrorGen} ${e.message || t.alertUnknown}`,
      t.alertNotice,
    );
  } finally {
    btn.disabled = false;
    btn.innerHTML = `${t.btnGenerate} <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  applyLanguage();
  const pA = document.getElementById("person-a");
  const pB = document.getElementById("person-b");

  pA.addEventListener("change", () => {
    if (currentNames.length === 2) {
      const available = currentNames.find((n) => n !== pA.value);
      if (available) pB.value = available;
    } else if (pA.value === pB.value) {
      const available = currentNames.find((n) => n !== pA.value);
      if (available) pB.value = available;
    }
  });

  pB.addEventListener("change", () => {
    if (currentNames.length === 2) {
      const available = currentNames.find((n) => n !== pB.value);
      if (available) pA.value = available;
    } else if (pB.value === pA.value) {
      const available = currentNames.find((n) => n !== pB.value);
      if (available) pA.value = available;
    }
  });
});
