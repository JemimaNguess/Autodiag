const MAX_RECORD_SECONDS = 15;
const MIN_RECORD_SECONDS = 3;
const DIAL_CIRCUMFERENCE = 578; // 2 * PI * r=92, arrondi

const screens = {
  record: document.getElementById("screen-record"),
  loading: document.getElementById("screen-loading"),
  result: document.getElementById("screen-result"),
};

const recordBtn = document.getElementById("record-btn");
const recordStatus = document.getElementById("record-status");
const recordTimer = document.getElementById("record-timer");
const recordError = document.getElementById("record-error");
const dialProgress = document.getElementById("dial-ring-progress");
const loadingStep = document.getElementById("loading-step");
const retryBtn = document.getElementById("retry-btn");

let mediaRecorder = null;
let audioChunks = [];
let recordSeconds = 0;
let timerInterval = null;
let autoStopTimeout = null;

function showScreen(name) {
  Object.values(screens).forEach((el) => el.classList.remove("screen--active"));
  screens[name].classList.add("screen--active");
}

function formatTime(totalSeconds) {
  const m = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const s = String(totalSeconds % 60).padStart(2, "0");
  return `${m}:${s}`;
}

function setDialProgress(seconds) {
  const ratio = Math.min(seconds / MAX_RECORD_SECONDS, 1);
  const offset = DIAL_CIRCUMFERENCE * (1 - ratio);
  dialProgress.style.strokeDashoffset = offset;
}

function resetRecordUI() {
  recordSeconds = 0;
  recordTimer.textContent = "00:00";
  setDialProgress(0);
  recordStatus.textContent = "Appuyez pour démarrer";
  recordBtn.classList.remove("is-recording");
  recordError.hidden = true;
}

async function startRecording() {
  recordError.hidden = true;
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    recordError.hidden = false;
    recordError.textContent =
      "Micro inaccessible. Autorisez l'accès au microphone dans les réglages du navigateur.";
    return;
  }

  audioChunks = [];
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
  mediaRecorder.onstop = () => {
    stream.getTracks().forEach((track) => track.stop());
    const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
    if (recordSeconds < MIN_RECORD_SECONDS) {
      recordError.hidden = false;
      recordError.textContent = `Enregistrement trop court (minimum ${MIN_RECORD_SECONDS} s). Réessayez.`;
      resetRecordUI();
      return;
    }
    sendForDiagnosis(audioBlob);
  };

  mediaRecorder.start();
  recordBtn.classList.add("is-recording");
  recordStatus.textContent = "Enregistrement… appuyez pour arrêter";

  recordSeconds = 0;
  timerInterval = setInterval(() => {
    recordSeconds += 1;
    recordTimer.textContent = formatTime(recordSeconds);
    setDialProgress(recordSeconds);
  }, 1000);

  autoStopTimeout = setTimeout(() => stopRecording(), MAX_RECORD_SECONDS * 1000);
}

function stopRecording() {
  clearInterval(timerInterval);
  clearTimeout(autoStopTimeout);
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
}

recordBtn.addEventListener("click", () => {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    stopRecording();
  } else {
    startRecording();
  }
});

// --- Écran de chargement : messages qui défilent pendant l'analyse ---
const LOADING_MESSAGES = [
  "Extraction des caractéristiques audio…",
  "Analyse par le modèle IA…",
  "Calcul du score de confiance…",
];

let loadingMessageInterval = null;

function startLoadingMessages() {
  let i = 0;
  loadingStep.textContent = LOADING_MESSAGES[0];
  loadingMessageInterval = setInterval(() => {
    i = (i + 1) % LOADING_MESSAGES.length;
    loadingStep.style.opacity = 0;
    setTimeout(() => {
      loadingStep.textContent = LOADING_MESSAGES[i];
      loadingStep.style.opacity = 1;
    }, 250);
  }, 1100);
}

function stopLoadingMessages() {
  clearInterval(loadingMessageInterval);
}

// --- Envoi au serveur et affichage du résultat ---
async function sendForDiagnosis(audioBlob) {
  showScreen("loading");
  startLoadingMessages();

  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");

  const minDisplayTime = new Promise((resolve) => setTimeout(resolve, 1400));

  try {
    const [response] = await Promise.all([
      fetch("/api/diagnose", { method: "POST", body: formData }),
      minDisplayTime,
    ]);

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error || "Erreur du serveur.");
    }

    const data = await response.json();
    stopLoadingMessages();
    displayResult(data);
  } catch (err) {
    stopLoadingMessages();
    resetRecordUI();
    showScreen("record");
    recordError.hidden = false;
    recordError.textContent = err.message || "Une erreur est survenue. Réessayez.";
  }
}

function displayResult(data) {
  const isSain = data.diagnostic === "sain";
  const color = isSain ? "var(--sain)" : "var(--anomalie)";

  const resultLabel = document.getElementById("result-label");
  resultLabel.textContent = isSain ? "Moteur sain" : "Anomalie détectée";
  resultLabel.className = "result-label " + (isSain ? "is-sain" : "is-anomalie");

  // Jauge de confiance
  const gaugeFill = document.getElementById("gauge-fill");
  const gaugeValue = document.getElementById("gauge-value");
  const circumference = 327; // 2 * PI * r=52
  const pct = Math.round(data.confiance * 100);
  gaugeFill.style.stroke = color;
  gaugeFill.style.strokeDashoffset = circumference * (1 - data.confiance);
  gaugeValue.textContent = `${pct}%`;

  // Détail des scores par classe
  const scoreBars = document.getElementById("score-bars");
  scoreBars.innerHTML = "";
  Object.entries(data.scores)
    .sort((a, b) => b[1] - a[1])
    .forEach(([label, score]) => {
      const barColor = label === "sain" ? "var(--sain)" : "var(--anomalie)";
      const row = document.createElement("div");
      row.className = "score-bar-row";
      row.innerHTML = `
        <div class="score-bar-label">
          <span>${label}</span>
          <span>${Math.round(score * 100)}%</span>
        </div>
        <div class="score-bar-track">
          <div class="score-bar-fill" style="width:${score * 100}%; background:${barColor};"></div>
        </div>
      `;
      scoreBars.appendChild(row);
    });

  // Recommandation
  const recBox = document.getElementById("recommendation");
  document.getElementById("recommendation-title").textContent = data.recommandation.titre;
  document.getElementById("recommendation-text").textContent = data.recommandation.message;
  recBox.className = "recommendation " + (isSain ? "" : "is-anomalie");

  showScreen("result");
}

retryBtn.addEventListener("click", () => {
  resetRecordUI();
  showScreen("record");
});
