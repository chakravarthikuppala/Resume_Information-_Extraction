const form = document.getElementById("upload-form");
const fileInput = document.getElementById("file-input");
const fileLabel = document.getElementById("file-label");
const dropzone = document.getElementById("dropzone");
const statusEl = document.getElementById("status");
const extractBtn = document.getElementById("extract-btn");
const sampleBtn = document.getElementById("sample-btn");
const downloadBtn = document.getElementById("download-json");
const steps = [...document.querySelectorAll(".pipeline li")];

let lastResult = null;

fileInput.addEventListener("change", () => {
  fileLabel.textContent = fileInput.files[0]?.name || "or click to browse";
});

["dragenter", "dragover"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("drag");
  });
});
["dragleave", "drop"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove("drag");
  });
});
dropzone.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];
  if (file) {
    fileInput.files = event.dataTransfer.files;
    fileLabel.textContent = file.name;
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!fileInput.files[0]) {
    setStatus("Choose a resume file first.", true);
    return;
  }
  const data = new FormData();
  data.append("resume", fileInput.files[0]);
  await runExtract("/api/extract", { method: "POST", body: data });
});

sampleBtn.addEventListener("click", async () => {
  await runExtract("/api/sample");
});

downloadBtn.addEventListener("click", () => {
  if (!lastResult) return;
  const blob = new Blob([JSON.stringify(lastResult, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "resume_extraction.json";
  link.click();
  URL.revokeObjectURL(url);
});

async function runExtract(url, options = {}) {
  setBusy(true);
  markSteps(2);
  setStatus("Extracting text and identifying fields…");
  try {
    const response = await fetch(url, options);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Extraction failed.");
    lastResult = payload;
    markSteps(5);
    render(payload);
    setStatus("Structured information is ready.");
  } catch (error) {
    setStatus(error.message, true);
    markSteps(1);
  } finally {
    setBusy(false);
  }
}

function render(data) {
  document.getElementById("raw-text").textContent = data.raw_text || "";
  document.getElementById("text-meta").textContent =
    `${data.word_count || 0} words · ${data.char_count || 0} characters · sections: ${(data.sections_found || []).join(", ")}`;
  document.getElementById("candidate-name").textContent = data.name || "Name not detected";
  if (data.engine) {
    document.getElementById("engine-note").textContent =
      `${data.engine.name}: ${data.engine.note}`;
  }

  const contact = data.contact || {};
  const rows = [
    ["Email", (contact.emails || []).join(", ")],
    ["Phone", (contact.phones || []).join(", ")],
    ["Location", contact.location],
    ["LinkedIn", contact.linkedin],
    ["GitHub", contact.github],
    ["Website", (contact.websites || []).join(", ")],
  ];
  document.getElementById("contact-list").innerHTML = rows
    .map(([label, value]) => `<dt>${label}</dt><dd>${escapeHtml(value || "—")}</dd>`)
    .join("");

  document.getElementById("summary-text").textContent = data.summary || "—";
  renderChips("skills", data.skills || []);
  renderChips("languages", data.languages || []);

  document.getElementById("education").innerHTML = (data.education || [])
    .map(
      (item) => `<div class="edu"><h4>${escapeHtml(item.degree || "Degree")}</h4>
        <div class="sub">${escapeHtml([item.field, item.institution, item.year].filter(Boolean).join(" · "))}</div></div>`
    )
    .join("") || "<p class='muted'>—</p>";

  document.getElementById("experience").innerHTML = (data.experience || [])
    .map(
      (job) => `<div class="job"><h4>${escapeHtml(job.title || "Role")}</h4>
        <div class="sub">${escapeHtml([job.company, job.dates].filter(Boolean).join(" · "))}</div>
        <ul>${(job.highlights || []).map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul></div>`
    )
    .join("") || "<p class='muted'>—</p>";

  fillList("projects", data.projects);
  fillList("certs", data.certifications);
  document.getElementById("entities").textContent = JSON.stringify(data.entities || {}, null, 2);
  downloadBtn.disabled = false;
}

function renderChips(id, items) {
  document.getElementById(id).innerHTML = items.length
    ? items.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("")
    : "<p class='muted'>—</p>";
}

function fillList(id, items) {
  const list = items || [];
  document.getElementById(id).innerHTML = list.length
    ? list.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
    : "<li class='muted'>—</li>";
}

function setBusy(isBusy) {
  extractBtn.disabled = isBusy;
  sampleBtn.disabled = isBusy;
}

function setStatus(message, isError = false) {
  statusEl.hidden = !message;
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

function markSteps(upto) {
  steps.forEach((step, index) => {
    step.style.borderColor = index < upto ? "#7ee0c3" : "";
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
