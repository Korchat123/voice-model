"use strict";

const form = document.querySelector("#voice-form");
const panels = [...document.querySelectorAll(".step-panel")];
const stepButtons = [...document.querySelectorAll(".step")];
const backButton = document.querySelector("#back-button");
const nextButton = document.querySelector("#next-button");
const currentStepLabel = document.querySelector("#current-step");
const controls = [...document.querySelectorAll(".control input")];
const presets = [...document.querySelectorAll(".preset")];
const previewButton = document.querySelector("#preview-button");
const stopButton = document.querySelector("#stop-button");
const previewStatus = document.querySelector("#preview-status");
const recordButton = document.querySelector("#record-button");
const upload = document.querySelector("#audio-upload");
const audioStatus = document.querySelector("#audio-status");
const audioPreview = document.querySelector("#audio-preview");
const recorder = document.querySelector(".recorder");
const exportButton = document.querySelector("#export-button");
const exportStatus = document.querySelector("#export-status");

let step = 1;
let referenceFile = null;
let mediaRecorder = null;
let mediaStream = null;
let recordingChunks = [];
let activeRequestId = null;
let audioContext = null;
let activeSource = null;

const presetValues = {
  neutral: { pitch: 0, pace: 0, energy: 0, warmth: 0, resonance: 0, expressiveness: 0 },
  warm: { pitch: -0.05, pace: -0.08, energy: -0.05, warmth: 0.4, resonance: 0.18, expressiveness: 0.08 },
  cheerful: { pitch: 0.18, pace: 0.12, energy: 0.2, warmth: 0.15, resonance: 0.08, expressiveness: 0.35 },
  serious: { pitch: -0.14, pace: -0.12, energy: 0.08, warmth: -0.08, resonance: 0.1, expressiveness: -0.25 },
  thinking: { pitch: -0.05, pace: -0.2, energy: -0.15, warmth: 0.1, resonance: 0, expressiveness: 0.12 },
};

function showStep(nextStep) {
  step = Math.max(1, Math.min(4, nextStep));
  panels.forEach((panel) => panel.classList.toggle("is-active", Number(panel.dataset.step) === step));
  stepButtons.forEach((button) => button.classList.toggle("is-active", Number(button.dataset.stepTarget) === step));
  currentStepLabel.textContent = String(step);
  backButton.disabled = step === 1;
  nextButton.hidden = step === 4;
  if (step === 4) renderReview();
  document.querySelector(".steps").scrollIntoView({ behavior: "smooth", block: "start" });
}

function validateFoundation() {
  const name = document.querySelector("#voice-name");
  const consent = document.querySelector("#consent");
  if (!name.value.trim()) {
    name.focus();
    name.setCustomValidity("Give this voice a short local name.");
    name.reportValidity();
    name.addEventListener("input", () => name.setCustomValidity(""), { once: true });
    return false;
  }
  if (!consent.checked) {
    consent.focus();
    consent.reportValidity();
    return false;
  }
  return true;
}

nextButton.addEventListener("click", () => {
  if (step === 1 && !validateFoundation()) return;
  showStep(step + 1);
});
backButton.addEventListener("click", () => showStep(step - 1));
stepButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const target = Number(button.dataset.stepTarget);
    if (target > 1 && !validateFoundation()) return;
    showStep(target);
  });
});

function currentControls() {
  return Object.fromEntries(controls.map((control) => [control.id, Number(control.value)]));
}

function updateControlLabels() {
  controls.forEach((control) => {
    document.querySelector(`output[for="${control.id}"]`).textContent = Number(control.value).toFixed(2);
  });
}

controls.forEach((control) => {
  control.addEventListener("input", () => {
    updateControlLabels();
    presets.forEach((preset) => preset.classList.remove("is-active"));
  });
});

presets.forEach((button) => {
  button.addEventListener("click", () => {
    Object.entries(presetValues[button.dataset.preset]).forEach(([name, value]) => {
      document.querySelector(`#${name}`).value = String(value);
    });
    presets.forEach((preset) => preset.classList.toggle("is-active", preset === button));
    updateControlLabels();
  });
});

function setReference(file, label) {
  if (referenceFile?.url) URL.revokeObjectURL(referenceFile.url);
  const url = URL.createObjectURL(file);
  referenceFile = { file, url, label };
  audioPreview.src = url;
  audioPreview.hidden = false;
  audioStatus.textContent = `${label}: ${file.name || "browser-recording.webm"} · ${(file.size / 1024).toFixed(1)} KB`;
}

upload.addEventListener("change", () => {
  if (upload.files?.[0]) setReference(upload.files[0], "Selected");
});

recordButton.addEventListener("click", async () => {
  if (mediaRecorder?.state === "recording") {
    mediaRecorder.stop();
    mediaStream?.getTracks().forEach((track) => track.stop());
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    audioStatus.textContent = "Browser recording is unavailable. Upload a WAV or WebM file instead.";
    return;
  }
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recordingChunks = [];
    mediaRecorder = new MediaRecorder(mediaStream);
    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size) recordingChunks.push(event.data);
    });
    mediaRecorder.addEventListener("stop", () => {
      const blob = new Blob(recordingChunks, { type: mediaRecorder.mimeType || "audio/webm" });
      const file = new File([blob], "voice-reference.webm", { type: blob.type });
      setReference(file, "Recorded locally");
      recorder.classList.remove("is-recording");
      recordButton.innerHTML = '<span aria-hidden="true">●</span> Start recording';
    });
    mediaRecorder.start(250);
    recorder.classList.add("is-recording");
    recordButton.textContent = "■ Stop recording";
    audioStatus.textContent = "Recording locally… speak naturally and stop after 15–30 seconds.";
  } catch {
    audioStatus.textContent = "Microphone permission was not granted. You can upload a file instead.";
  }
});

async function playPcm(response) {
  const bytes = new Uint8Array(await response.arrayBuffer());
  const sampleRate = Number(response.headers.get("X-Audio-Sample-Rate") || 24000);
  const samples = new Float32Array(Math.floor(bytes.byteLength / 2));
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  for (let index = 0; index < samples.length; index += 1) {
    samples[index] = view.getInt16(index * 2, true) / 32768;
  }
  audioContext = audioContext || new AudioContext();
  const buffer = audioContext.createBuffer(1, samples.length, sampleRate);
  buffer.copyToChannel(samples, 0);
  activeSource = audioContext.createBufferSource();
  activeSource.buffer = buffer;
  activeSource.connect(audioContext.destination);
  activeSource.addEventListener("ended", () => {
    activeSource = null;
    stopButton.disabled = true;
    previewStatus.textContent = "Preview complete.";
  });
  activeSource.start();
}

previewButton.addEventListener("click", async () => {
  const text = document.querySelector("#preview-text").value.trim();
  if (!text) {
    previewStatus.textContent = "Enter a sentence to preview.";
    return;
  }
  activeRequestId = `setup-${crypto.randomUUID()}`;
  previewStatus.textContent = "Synthesizing with the local service…";
  previewButton.disabled = true;
  stopButton.disabled = false;
  try {
    const capabilities = await fetch("/v1/capabilities").then((response) => response.json());
    const supported = new Set(capabilities.controls || []);
    const boundedControls = Object.fromEntries(
      Object.entries(currentControls()).filter(([name]) => supported.has(name)),
    );
    const response = await fetch("/v1/synthesis", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Request-ID": activeRequestId },
      body: JSON.stringify({
        request_id: activeRequestId,
        text,
        language: document.querySelector("#language").value === "mixed" ? "auto" : document.querySelector("#language").value,
        voice: "primary",
        controls: boundedControls,
      }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error?.error?.message || `Service returned ${response.status}`);
    }
    await playPcm(response);
    previewStatus.textContent = "Playing local preview. The current fake engine is a test tone, not the final human voice.";
  } catch (error) {
    previewStatus.textContent = `Preview unavailable: ${error.message}`;
    stopButton.disabled = true;
  } finally {
    previewButton.disabled = false;
  }
});

stopButton.addEventListener("click", async () => {
  if (activeSource) {
    activeSource.stop();
    activeSource = null;
  }
  if (activeRequestId) {
    await fetch(`/v1/synthesis/${encodeURIComponent(activeRequestId)}`, { method: "DELETE" }).catch(() => {});
  }
  activeRequestId = null;
  stopButton.disabled = true;
  previewStatus.textContent = "Preview stopped.";
});

async function referenceMetadata() {
  if (!referenceFile) return null;
  const buffer = await referenceFile.file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  const sha256 = [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
  return {
    filename: referenceFile.file.name,
    media_type: referenceFile.file.type || "application/octet-stream",
    byte_size: referenceFile.file.size,
    sha256,
    note: "Audio bytes are not embedded in this manifest.",
  };
}

function selectedPreset() {
  return presets.find((preset) => preset.classList.contains("is-active"))?.dataset.preset || "custom";
}

function renderReview() {
  const source = form.elements.source.value;
  const items = [
    ["Voice", document.querySelector("#voice-name").value.trim()],
    ["Foundation", source.replaceAll("-", " ")],
    ["Language", document.querySelector("#language").selectedOptions[0].text],
    ["Style", selectedPreset()],
    ["Reference", referenceFile ? referenceFile.label : "No local reference"],
    ["Consent gate", document.querySelector("#consent").checked ? "Confirmed by user" : "Incomplete"],
  ];
  document.querySelector("#review").innerHTML = items
    .map(([label, value]) => `<div class="review-item"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong></div>`)
    .join("");
}

function escapeHtml(value) {
  const node = document.createElement("span");
  node.textContent = value;
  return node.innerHTML;
}

exportButton.addEventListener("click", async () => {
  if (!validateFoundation()) {
    showStep(1);
    return;
  }
  exportButton.disabled = true;
  exportStatus.textContent = "Hashing local reference and preparing manifest…";
  try {
    const manifest = {
      schema_version: "1.0",
      status: "draft-user-input",
      created_at: new Date().toISOString(),
      voice: {
        id: document.querySelector("#voice-name").value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""),
        display_name: document.querySelector("#voice-name").value.trim(),
        source: form.elements.source.value,
        language: document.querySelector("#language").value,
        style: selectedPreset(),
        controls: currentControls(),
      },
      authorization: {
        user_attested_right_to_use: document.querySelector("#consent").checked,
        signed_consent_record: "USER_INPUT_REQUIRED",
        license_review: "USER_INPUT_REQUIRED",
      },
      reference: await referenceMetadata(),
      safety: {
        recordings_uploaded_by_ui: false,
        training_approved: false,
        release_approved: false,
      },
    };
    const blob = new Blob([`${JSON.stringify(manifest, null, 2)}\n`], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${manifest.voice.id || "voice"}-setup.json`;
    link.click();
    URL.revokeObjectURL(link.href);
    exportStatus.textContent = "Manifest exported. Keep it with the consent and provenance records.";
  } catch {
    exportStatus.textContent = "Export failed. Check browser permissions and try again.";
  } finally {
    exportButton.disabled = false;
  }
});

form.addEventListener("submit", (event) => event.preventDefault());
updateControlLabels();
