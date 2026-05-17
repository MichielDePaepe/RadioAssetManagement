(function () {
  const payload = JSON.parse(document.getElementById("phonebook-data").textContent);
  const state = {
    port: null,
    reader: null,
    writer: null,
    buffer: "",
    contacts: payload.contacts.fire,
    selectedPhonebook: "fire",
    totalSlots: 0,
    usedSlots: 0,
    busy: false,
  };

  const els = {
    connectBtn: document.getElementById("connectBtn"),
    refreshBtn: document.getElementById("refreshBtn"),
    updateBtn: document.getElementById("updateBtn"),
    clearLogBtn: document.getElementById("clearLogBtn"),
    app: document.getElementById("serialApp"),
    gate: document.getElementById("serialGate"),
    gateMessage: document.getElementById("serialGateMessage"),
    flagHelp: document.getElementById("serialFlagHelp"),
    serialOrigin: document.getElementById("serialOrigin"),
    tei: document.getElementById("teiValue"),
    issi: document.getElementById("issiValue"),
    alias: document.getElementById("aliasValue"),
    model: document.getElementById("modelValue"),
    revision: document.getElementById("revisionValue"),
    phonebook: document.getElementById("phonebookValue"),
    phonebookChoices: document.querySelectorAll('input[name="phonebookChoice"]'),
    phonebookSuggestion: document.getElementById("phonebookSuggestion"),
    connectionTitle: document.getElementById("connectionTitle"),
    notice: document.getElementById("serialNotice"),
    progressBar: document.getElementById("progressBar"),
    progressStatus: document.getElementById("progressStatus"),
    etaStatus: document.getElementById("etaStatus"),
    log: document.getElementById("atLog"),
    logLines: document.getElementById("atLogLines"),
  };

  function log(kind, message) {
    const line = document.createElement("div");
    line.className = `log-line ${kind.toLowerCase()}`;
    const stamp = new Date().toLocaleTimeString();
    line.textContent = `[${stamp}] ${kind.padEnd(4)} ${message}`;
    els.logLines.appendChild(line);
    els.logLines.scrollTop = els.logLines.scrollHeight;
  }

  function sanitizeAtText(value) {
    return String(value || "").replace(/[\r\n"]/g, " ").trim();
  }

  function normalizeIssi(value) {
    const digits = String(value || "").replace(/\D/g, "");
    return digits.length > 7 ? digits.slice(-7) : digits;
  }

  function renderContacts() {
  }

  function setSelectedPhonebook(phonebook, options = {}) {
    const selected = phonebook === "medical" ? "medical" : "fire";
    state.selectedPhonebook = selected;
    state.contacts = payload.contacts[selected] || [];
    for (const choice of els.phonebookChoices) {
      choice.checked = choice.value === selected;
    }
    if (options.manual) {
      if (els.phonebookSuggestion) {
        els.phonebookSuggestion.textContent = "Handmatig gekozen.";
      }
    }
  }

  function syncSelectedPhonebookFromForm() {
    const checkedChoice = Array.from(els.phonebookChoices).find((choice) => choice.checked);
    setSelectedPhonebook(checkedChoice ? checkedChoice.value : state.selectedPhonebook);
  }

  function setPhonebookChoiceDisabled(disabled) {
    for (const choice of els.phonebookChoices) {
      choice.disabled = disabled;
    }
  }

  function showNotice(message, level = "warning") {
    if (!els.notice) return;
    els.notice.className = `alert alert-${level} mb-3`;
    els.notice.textContent = message;
  }

  function hideNotice() {
    if (!els.notice) return;
    els.notice.className = "alert alert-warning d-none mb-3";
    els.notice.textContent = "";
  }

  function setConnectionStatus(message) {
    els.connectionTitle.textContent = message;
  }

  function getSerialSupportMessage() {
    if (!window.isSecureContext) {
      return {
        reason: "insecure",
        message: "Deze interne site draait via HTTP. Browsers laten Web Serial alleen toe via HTTPS of localhost.",
      };
    }
    if (!("serial" in navigator)) {
      return {
        reason: "browser",
        message: "Deze browser ondersteunt Web Serial niet. Gebruik Chrome of Edge op desktop; Safari, Firefox en iOS ondersteunen dit niet.",
      };
    }
    return null;
  }

  function updateSerialSupportState() {
    const supportProblem = getSerialSupportMessage();
    if (!supportProblem) {
      if (els.gate) els.gate.classList.add("d-none");
      if (els.app) els.app.classList.remove("d-none");
      els.connectBtn.disabled = false;
      setConnectionStatus("Niet verbonden");
      els.progressStatus.textContent = "Web Serial beschikbaar";
      return;
    }

    if (els.app) els.app.classList.add("d-none");
    if (els.gate) els.gate.classList.remove("d-none");
    if (els.gateMessage) els.gateMessage.textContent = supportProblem.message;
    els.connectBtn.disabled = true;

    const showFlagHelp = supportProblem.reason === "insecure" && /Chrome|Chromium|Edg\//.test(navigator.userAgent);
    if (els.flagHelp) els.flagHelp.classList.toggle("d-none", !showFlagHelp);
    if (els.serialOrigin) els.serialOrigin.textContent = window.location.origin;

    if (!els.gate) {
      showNotice(supportProblem.message, "warning");
    }
  }

  async function copyOrigin() {
    const origin = window.location.origin;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(origin);
      } else {
        const input = document.createElement("input");
        input.value = origin;
        document.body.appendChild(input);
        input.select();
        document.execCommand("copy");
        input.remove();
      }
    } catch (error) {
      showNotice(`Kopieren mislukt: ${error.message}`, "warning");
    }
  }

  function setProgress(done, total, status, startedAt) {
    const pct = total ? Math.round((done / total) * 100) : 0;
    els.progressBar.style.width = `${pct}%`;
    els.progressBar.textContent = `${pct}%`;
    els.progressStatus.textContent = status;

    if (!startedAt || done === 0 || done >= total) {
      els.etaStatus.textContent = done >= total && total ? "Klaar" : "ETA -";
      return;
    }

    const elapsed = (Date.now() - startedAt) / 1000;
    const avg = elapsed / done;
    const remaining = Math.max(0, Math.round(avg * (total - done)));
    els.etaStatus.textContent = `${formatDuration(remaining)} resterend`;
  }

  function formatDuration(seconds) {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const rest = seconds % 60;
    return `${minutes}min ${rest}s`;
  }

  async function readLoop() {
    const decoder = new TextDecoder();
    while (state.port && state.port.readable) {
      state.reader = state.port.readable.getReader();
      try {
        while (true) {
          const { value, done } = await state.reader.read();
          if (done) break;
          state.buffer += decoder.decode(value, { stream: true });
        }
      } catch (error) {
        log("WARN", `Leeslus gestopt: ${error.message}`);
      } finally {
        state.reader.releaseLock();
        state.reader = null;
      }
    }
  }

  async function sendCommand(command, options = {}) {
    if (!state.writer) throw new Error("Geen seriële verbinding");

    const timeoutMs = options.timeoutMs || 4500;
    const encoder = new TextEncoder();
    state.buffer = "";
    log("TX", command);
    await state.writer.write(encoder.encode(`${command}\r`));

    const started = Date.now();
    while (Date.now() - started < timeoutMs) {
      await sleep(60);
      const normalized = state.buffer.replace(/\r/g, "\n");
      if (/(^|\n)OK\s*(\n|$)/.test(normalized) || /(^|\n)ERROR\s*(\n|$)/.test(normalized) || /\+CME ERROR|\+CMS ERROR/.test(normalized)) {
        const lines = normalized.split("\n").map((line) => line.trim()).filter(Boolean);
        for (const line of lines) log("RX", line);
        if (lines.some((line) => line === "ERROR" || line.startsWith("+CME ERROR") || line.startsWith("+CMS ERROR"))) {
          throw new Error(`${command} gaf ERROR`);
        }
        return lines.filter((line) => line !== "OK" && line !== command);
      }
    }
    log("WARN", `${command} timeout`);
    throw new Error(`${command} timeout`);
  }

  async function commandWithFallback(commands, parser) {
    let lastError = null;
    for (const command of commands) {
      try {
        const lines = await sendCommand(command);
        const parsed = parser(lines);
        if (parsed) return parsed;
      } catch (error) {
        lastError = error;
        log("WARN", `${command} niet bruikbaar: ${error.message}`);
      }
    }
    if (lastError) throw lastError;
    return "";
  }

  function firstResponseValue(lines, prefixes) {
    for (const line of lines) {
      for (const prefix of prefixes) {
        if (line.startsWith(prefix)) {
          return line.replace(`${prefix}:`, "").replace(prefix, "").trim();
        }
      }
      if (!line.startsWith("AT")) return line;
    }
    return "";
  }

  async function connect() {
    const unsupportedMessage = getSerialSupportMessage();
    if (unsupportedMessage) {
      updateSerialSupportState();
      return;
    }

    hideNotice();
    els.connectBtn.disabled = true;
    setConnectionStatus("Verbinden...");
    els.progressStatus.textContent = "Kies een seriële poort in de browser...";

    try {
      state.port = await navigator.serial.requestPort();
      els.progressStatus.textContent = "Seriële poort openen...";
      await state.port.open({ baudRate: 9600, dataBits: 8, stopBits: 1, parity: "none", flowControl: "hardware" });
      state.writer = state.port.writable.getWriter();
      readLoop();
      els.refreshBtn.disabled = false;
      els.updateBtn.disabled = false;
      els.progressStatus.textContent = "Verbonden, radio uitlezen...";
      setConnectionStatus("Verbonden");
      log("WARN", "Seriële poort verbonden op 9600 8N1 RTS/CTS");
      await initializeRadio();
    } catch (error) {
      const message = error.name === "NotFoundError"
        ? "Geen seriële poort gekozen. Klik opnieuw op verbinden en selecteer de radio."
        : `Verbinden mislukt: ${error.message || error.name}`;
      showNotice(message, "danger");
      setConnectionStatus("Niet verbonden");
      els.progressStatus.textContent = "Niet verbonden";
      log("ERROR", message);
      els.connectBtn.disabled = false;
    }
  }

  async function initializeRadio() {
    await sendCommand("AT");
    await sendCommand("ATE0");
    await sendCommand("ATV1");
    await sendCommand("AT+CMEE=1");
    await refreshStatus();
  }

  async function refreshStatus() {
    if (state.busy) return;
    state.busy = true;
    els.refreshBtn.disabled = true;
    els.updateBtn.disabled = true;
    try {
      const tei = await commandWithFallback(["AT+CGSN", "AT+GSN"], (lines) => firstResponseValue(lines, ["+CGSN", "+GSN"]));
      const issiRaw = await commandWithFallback(["AT+CNUMF?", "AT+CNUM"], (lines) => {
        const joined = lines.join(" ");
        const match = joined.match(/\d{7,}/);
        return match ? match[0] : "";
      });
      const model = await commandWithFallback(["AT+CGMM", "AT+GMM"], (lines) => firstResponseValue(lines, ["+CGMM", "+GMM"]));
      const revision = await commandWithFallback(["AT+CGMR", "AT+GMR"], (lines) => firstResponseValue(lines, ["+CGMR", "+GMR"]));
      await sendCommand('AT+CPBS="ME"');
      const cpbs = await sendCommand("AT+CPBS?");

      const issi = normalizeIssi(issiRaw);
      selectPhonebookForIssi(issi);
      els.tei.textContent = tei || "-";
      els.issi.textContent = issi || "-";
      els.model.textContent = model || "-";
      els.revision.textContent = revision || "-";
      els.phonebook.textContent = parseCpbs(cpbs);
    } finally {
      state.busy = false;
      els.refreshBtn.disabled = false;
      els.updateBtn.disabled = false;
    }
  }

  function selectPhonebookForIssi(issi) {
    const radioRecord = payload.issi_lookup[issi] || {};
    const suggested = radioRecord.discipline === "MEDICAL" ? "medical" : "fire";
    setSelectedPhonebook(suggested);
    els.alias.textContent = radioRecord.alias || "Niet gevonden in database";
    if (els.phonebookSuggestion) {
      const label = suggested === "medical" ? "geel medisch" : "rood brandweer";
      els.phonebookSuggestion.textContent = `Voorstel op basis van ISSI: ${label}.`;
    }
    renderContacts();
  }

  function parseCpbs(lines) {
    const line = lines.find((item) => item.startsWith("+CPBS:")) || "";
    const match = line.match(/\+CPBS:\s*"?([^",]+)"?\s*,\s*(\d+)\s*,\s*(\d+)/);
    if (!match) return line || "-";
    state.usedSlots = Number(match[2]);
    state.totalSlots = Number(match[3]);
    return `${state.usedSlots}/${state.totalSlots}`;
  }

  async function updatePhonebook() {
    if (state.busy) return;
    syncSelectedPhonebookFromForm();
    if (!state.contacts.length) {
      log("WARN", "Geen contacten om te schrijven");
      return;
    }
    hideNotice();

    state.busy = true;
    els.updateBtn.disabled = true;
    els.refreshBtn.disabled = true;
    setPhonebookChoiceDisabled(true);
    const deleteFrom = state.contacts.length + 1;
    const deleteUntil = Math.max(state.usedSlots, state.contacts.length);
    const deleteCount = Math.max(0, deleteUntil - state.contacts.length);
    const total = state.contacts.length + deleteCount;
    const startedAt = Date.now();
    let done = 0;

    try {
      await sendCommand('AT+CPBS="ME"');
      if (state.totalSlots && state.contacts.length > state.totalSlots) {
        throw new Error(`Phonebook heeft ${state.totalSlots} plaatsen, maar ${state.contacts.length} contacten moeten geschreven worden`);
      }
      const phonebookLabel = state.selectedPhonebook === "medical" ? "geel medisch" : "rood brandweer";
      log("WARN", `Start schrijven ${phonebookLabel} phonebook (${state.contacts.length} contacten)`);
      els.progressStatus.textContent = `Start schrijven ${phonebookLabel} phonebook`;
      for (const contact of state.contacts) {
        const command = `AT+CPBW=${contact.index},"${sanitizeAtText(contact.number)}",${contact.type},"${sanitizeAtText(contact.name)}"`;
        await sendCommand(command, { timeoutMs: 6500 });
        done += 1;
        setProgress(done, total, `Schrijf ${contact.index}/${state.contacts.length}`, startedAt);
      }

      for (let index = deleteFrom; index <= deleteUntil; index += 1) {
        await sendCommand(`AT+CPBW=${index}`, { timeoutMs: 6500 });
        done += 1;
        setProgress(done, total, `Wis oude entry ${index}`, startedAt);
      }

      setProgress(total, total, `${phonebookLabel} phonebook bijgewerkt`, startedAt);
      await refreshStatus();
    } catch (error) {
      log("ERROR", error.message);
      setProgress(done, total, "Update gestopt", startedAt);
    } finally {
      state.busy = false;
      els.updateBtn.disabled = false;
      els.refreshBtn.disabled = false;
      setPhonebookChoiceDisabled(false);
    }
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  els.connectBtn.addEventListener("click", () => connect());
  els.refreshBtn.addEventListener("click", () => refreshStatus().catch((error) => {
    showNotice(`Status lezen mislukt: ${error.message}`, "danger");
    log("ERROR", error.message);
  }));
  els.updateBtn.addEventListener("click", () => updatePhonebook().catch((error) => {
    showNotice(`Phonebook schrijven mislukt: ${error.message}`, "danger");
    log("ERROR", error.message);
  }));
  for (const choice of els.phonebookChoices) {
    choice.addEventListener("change", () => {
      if (choice.checked) setSelectedPhonebook(choice.value, { manual: true });
    });
  }
  els.clearLogBtn.addEventListener("click", () => {
    els.logLines.innerHTML = "";
  });
  if (els.serialOrigin) {
    els.serialOrigin.addEventListener("click", copyOrigin);
  }

  updateSerialSupportState();
  renderContacts();
}());
