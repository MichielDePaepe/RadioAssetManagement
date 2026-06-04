(function () {
  const payload = JSON.parse(document.getElementById("phonebook-data").textContent);
  const translations = payload.translations || {};
  function t(key, fallback, values = {}) {
    let text = translations[key] || fallback;
    for (const [name, value] of Object.entries(values)) {
      text = text.replace(`{${name}}`, value);
    }
    return text;
  }
  const state = {
    port: null,
    reader: null,
    writer: null,
    buffer: "",
    contacts: payload.contacts.fire,
    selectedPhonebook: "fire",
    totalSlots: 0,
    usedSlots: 0,
    radioPresent: false,
    pollTimer: null,
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

  function findRadioDetailUrl(tei) {
    const digits = String(tei || "").replace(/\D/g, "");
    const candidates = [digits];
    if (digits.length === 15 && digits.endsWith("0")) candidates.push(digits.slice(0, -1));
    const numeric = String(Number.parseInt(digits, 10));
    if (numeric !== "NaN") {
      candidates.push(numeric, numeric.padStart(14, "0"), `${numeric.padStart(14, "0")}0`);
    }
    for (const candidate of candidates) {
      if (payload.radio_detail_lookup && payload.radio_detail_lookup[candidate]) {
        return payload.radio_detail_lookup[candidate];
      }
    }
    return "";
  }

  function renderTei(tei) {
    const value = tei || "-";
    const detailUrl = findRadioDetailUrl(value);
    els.tei.textContent = "";
    if (!detailUrl) {
      els.tei.textContent = value;
      return;
    }
    const link = document.createElement("a");
    link.href = detailUrl;
    link.textContent = value;
    link.className = "link-dark";
    els.tei.appendChild(link);
  }

  function renderContacts() {
  }

  function clearRadioStatus() {
    renderTei("");
    els.issi.textContent = "-";
    els.alias.textContent = "-";
    els.model.textContent = "-";
    els.revision.textContent = "-";
    els.phonebook.textContent = "-";
    state.usedSlots = 0;
    state.totalSlots = 0;
    els.updateBtn.disabled = true;
    els.refreshBtn.disabled = true;
    if (els.phonebookSuggestion) {
      els.phonebookSuggestion.textContent = t("suggestion_pending", "Voorstel wordt bepaald na uitlezen van ISSI.");
    }
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
        els.phonebookSuggestion.textContent = t("manual_choice", "Handmatig gekozen.");
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
        message: t("insecure_serial", "Deze interne site draait via HTTP. Browsers laten Web Serial alleen toe via HTTPS of localhost."),
      };
    }
    if (!("serial" in navigator)) {
      return {
        reason: "browser",
        message: t("unsupported_serial", "Deze browser ondersteunt Web Serial niet. Gebruik Chrome of Edge op desktop; Safari, Firefox en iOS ondersteunen dit niet."),
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
      setConnectionStatus(t("not_connected", "Niet verbonden"));
      els.progressStatus.textContent = t("serial_available", "Web Serial beschikbaar");
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
      showNotice(t("copy_failed", "Kopiëren mislukt: {error}", { error: error.message }), "warning");
    }
  }

  function setProgress(done, total, status, startedAt) {
    const pct = total ? Math.round((done / total) * 100) : 0;
    els.progressBar.style.width = `${pct}%`;
    els.progressBar.textContent = `${pct}%`;
    els.progressStatus.textContent = status;

    if (!startedAt || done === 0 || done >= total) {
      els.etaStatus.textContent = done >= total && total ? t("done", "Klaar") : t("eta_empty", "ETA -");
      return;
    }

    const elapsed = (Date.now() - startedAt) / 1000;
    const avg = elapsed / done;
    const remaining = Math.max(0, Math.round(avg * (total - done)));
    els.etaStatus.textContent = t("remaining", "{duration} resterend", { duration: formatDuration(remaining) });
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
        log("WARN", t("read_loop_stopped", "Leeslus gestopt: {error}", { error: error.message }));
      } finally {
        state.reader.releaseLock();
        state.reader = null;
      }
    }
  }

  async function sendCommand(command, options = {}) {
    if (!state.writer) throw new Error(t("no_serial_connection", "Geen seriële verbinding"));

    const timeoutMs = options.timeoutMs || 4500;
    const silent = options.silent || false;
    const encoder = new TextEncoder();
    state.buffer = "";
    if (!silent) log("TX", command);
    await state.writer.write(encoder.encode(`${command}\r`));

    const started = Date.now();
    while (Date.now() - started < timeoutMs) {
      await sleep(60);
      const normalized = state.buffer.replace(/\r/g, "\n");
      if (/(^|\n)OK\s*(\n|$)/.test(normalized) || /(^|\n)ERROR\s*(\n|$)/.test(normalized) || /\+CME ERROR|\+CMS ERROR/.test(normalized)) {
        const lines = normalized.split("\n").map((line) => line.trim()).filter(Boolean);
        if (!silent) {
          for (const line of lines) log("RX", line);
        }
        if (lines.some((line) => line === "ERROR" || line.startsWith("+CME ERROR") || line.startsWith("+CMS ERROR"))) {
          throw new Error(t("command_error", "{command} gaf ERROR", { command }));
        }
        return lines.filter((line) => line !== "OK" && line !== command);
      }
    }
    if (!silent) log("WARN", `${command} timeout`);
    throw new Error(t("command_timeout", "{command} timeout", { command }));
  }

  async function probeRadio() {
    await sendCommand("AT", { timeoutMs: 1000, silent: true });
  }

  function markRadioAbsent() {
    if (state.radioPresent) {
      log("WARN", t("radio_absent", "Geen antwoord meer op AT; radio afwezig"));
    }
    state.radioPresent = false;
    clearRadioStatus();
    setConnectionStatus(t("port_open", "Poort open"));
    els.progressStatus.textContent = t("waiting_radio", "Wachten op radio...");
  }

  async function handleRadioDetected() {
    state.radioPresent = true;
    setConnectionStatus(t("radio_detected", "Radio gedetecteerd"));
    els.progressStatus.textContent = t("reading_status", "Radio gedetecteerd, status uitlezen...");
    state.busy = true;
    try {
      await sendCommand("ATE0");
      await sendCommand("ATV1");
      await sendCommand("AT+CMEE=1");
    } finally {
      state.busy = false;
    }
    await refreshStatus();
  }

  async function pollRadioPresence() {
    if (!state.writer || state.busy) return;

    try {
      await probeRadio();
      if (!state.radioPresent) {
        await handleRadioDetected();
      }
    } catch (error) {
      markRadioAbsent();
    }
  }

  function startRadioPolling() {
    if (state.pollTimer) window.clearInterval(state.pollTimer);
    state.pollTimer = window.setInterval(() => {
      pollRadioPresence().catch((error) => log("ERROR", error.message));
    }, 2000);
    pollRadioPresence().catch((error) => log("ERROR", error.message));
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
        log("WARN", t("command_unusable", "{command} niet bruikbaar: {error}", { command, error: error.message }));
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
    setConnectionStatus(t("connecting", "Verbinden..."));
    els.progressStatus.textContent = t("choose_port", "Kies een seriële poort in de browser...");

    try {
      state.port = await navigator.serial.requestPort();
      els.progressStatus.textContent = t("opening_port", "Seriële poort openen...");
      await state.port.open({ baudRate: 9600, dataBits: 8, stopBits: 1, parity: "none", flowControl: "hardware" });
      state.writer = state.port.writable.getWriter();
      readLoop();
      clearRadioStatus();
      els.connectBtn.disabled = true;
      els.progressStatus.textContent = t("port_waiting_radio", "Seriële poort open, wachten op radio...");
      setConnectionStatus(t("port_open", "Poort open"));
      log("WARN", t("port_open_log", "Seriële poort open op 9600 8N1 RTS/CTS"));
      startRadioPolling();
    } catch (error) {
      const message = error.name === "NotFoundError"
        ? t("no_port_selected", "Geen seriële poort gekozen. Klik opnieuw op verbinden en selecteer de radio.")
        : t("connect_failed", "Verbinden mislukt: {error}", { error: error.message || error.name });
      showNotice(message, "danger");
      setConnectionStatus(t("not_connected", "Niet verbonden"));
      els.progressStatus.textContent = t("not_connected", "Niet verbonden");
      log("ERROR", message);
      els.connectBtn.disabled = false;
    }
  }

  async function refreshStatus() {
    if (state.busy || !state.radioPresent) return;
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
      renderTei(tei);
      els.issi.textContent = issi || "-";
      els.model.textContent = model || "-";
      els.revision.textContent = revision || "-";
      els.phonebook.textContent = parseCpbs(cpbs);
      els.updateBtn.disabled = false;
    } finally {
      state.busy = false;
      els.refreshBtn.disabled = false;
      els.updateBtn.disabled = !state.radioPresent;
    }
  }

  function selectPhonebookForIssi(issi) {
    const radioRecord = payload.issi_lookup[issi] || {};
    const suggested = radioRecord.discipline === "MEDICAL" ? "medical" : "fire";
    setSelectedPhonebook(suggested);
    els.alias.textContent = radioRecord.alias || t("not_found_database", "Niet gevonden in database");
    if (els.phonebookSuggestion) {
      const label = suggested === "medical" ? t("medical_phonebook", "geel medisch") : t("fire_phonebook", "rood brandweer");
      els.phonebookSuggestion.textContent = t("suggestion_for_issi", "Voorstel op basis van ISSI: {label}.", { label });
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
    if (state.busy || !state.radioPresent) return;
    syncSelectedPhonebookFromForm();
    if (!state.contacts.length) {
      log("WARN", t("no_contacts", "Geen contacten om te schrijven"));
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
        throw new Error(t("phonebook_capacity_error", "Phonebook heeft {slots} plaatsen, maar {contacts} contacten moeten geschreven worden", { slots: state.totalSlots, contacts: state.contacts.length }));
      }
      const phonebookLabel = state.selectedPhonebook === "medical" ? t("medical_phonebook", "geel medisch") : t("fire_phonebook", "rood brandweer");
      log("WARN", t("start_writing_log", "Start schrijven {label} phonebook ({contacts} contacten)", { label: phonebookLabel, contacts: state.contacts.length }));
      els.progressStatus.textContent = t("start_writing_status", "Start schrijven {label} phonebook", { label: phonebookLabel });
      for (const contact of state.contacts) {
        const command = `AT+CPBW=${contact.index},"${sanitizeAtText(contact.number)}",${contact.type},"${sanitizeAtText(contact.name)}"`;
        await sendCommand(command, { timeoutMs: 6500 });
        done += 1;
        setProgress(done, total, t("write_contact", "Schrijf {index}/{total}", { index: contact.index, total: state.contacts.length }), startedAt);
      }

      for (let index = deleteFrom; index <= deleteUntil; index += 1) {
        await sendCommand(`AT+CPBW=${index}`, { timeoutMs: 6500 });
        done += 1;
        setProgress(done, total, t("delete_old_entry", "Wis oude entry {index}", { index }), startedAt);
      }

      setProgress(total, total, t("phonebook_updated", "{label} phonebook bijgewerkt", { label: phonebookLabel }), startedAt);
      await refreshStatus();
    } catch (error) {
      log("ERROR", error.message);
      setProgress(done, total, t("update_stopped", "Update gestopt"), startedAt);
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
    showNotice(t("status_read_failed", "Status lezen mislukt: {error}", { error: error.message }), "danger");
    log("ERROR", error.message);
  }));
  els.updateBtn.addEventListener("click", () => updatePhonebook().catch((error) => {
    showNotice(t("phonebook_write_failed", "Phonebook schrijven mislukt: {error}", { error: error.message }), "danger");
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
