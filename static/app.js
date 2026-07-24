const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const workspace = document.getElementById("workspace");
const preview = document.getElementById("preview");
const meta = document.getElementById("meta");
const statusEl = document.getElementById("status");
const btnDownload = document.getElementById("btn-download");
const btnReset = document.getElementById("btn-reset");
const rotateButtons = document.querySelectorAll("[data-degrees]");

let sessionId = null;
let filename = null;
let previewUrl = null;

function setStatus(message, ok = false) {
  statusEl.textContent = message || "";
  statusEl.classList.toggle("is-ok", ok);
}

function setBusy(busy) {
  rotateButtons.forEach((btn) => {
    btn.disabled = busy;
  });
  btnDownload.disabled = busy || !sessionId;
  btnReset.disabled = busy;
  fileInput.disabled = busy;
}

function revokePreview() {
  if (previewUrl) {
    URL.revokeObjectURL(previewUrl);
    previewUrl = null;
  }
}

function showPreview(blob) {
  revokePreview();
  previewUrl = URL.createObjectURL(blob);
  preview.src = `${previewUrl}#toolbar=0&navpanes=0`;
}

function showWorkspace(show) {
  dropzone.classList.toggle("is-hidden", show);
  workspace.classList.toggle("is-hidden", !show);
}

async function uploadFile(file) {
  if (!file || file.type !== "application/pdf") {
    setStatus("PDFファイルを選んでください");
    return;
  }

  setBusy(true);
  setStatus("アップロード中…");

  const form = new FormData();
  form.append("file", file);

  try {
    const res = await fetch("/api/upload", { method: "POST", body: form });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || "アップロードに失敗しました");
    }

    sessionId = data.session_id;
    filename = data.filename;
    meta.textContent = `${data.filename} ／ ${data.page_count}ページ`;

    const previewRes = await fetch(`/api/preview/${sessionId}`);
    if (!previewRes.ok) {
      throw new Error("プレビューの取得に失敗しました");
    }
    showPreview(await previewRes.blob());
    showWorkspace(true);
    setStatus("回転ボタンで向きを直し、ダウンロードしてください", true);
  } catch (err) {
    setStatus(err.message || "エラーが発生しました");
    showWorkspace(false);
    sessionId = null;
  } finally {
    setBusy(false);
  }
}

async function rotate(degrees) {
  if (!sessionId) return;

  setBusy(true);
  setStatus("回転しています…");

  try {
    const res = await fetch("/api/rotate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, degrees }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "回転に失敗しました");
    }
    showPreview(await res.blob());
    setStatus("向きを更新しました。問題なければダウンロードしてください", true);
  } catch (err) {
    setStatus(err.message || "エラーが発生しました");
  } finally {
    setBusy(false);
  }
}

async function download() {
  if (!sessionId) return;
  setBusy(true);
  try {
    const q = new URLSearchParams({ filename: filename || "rotated.pdf" });
    const res = await fetch(`/api/download/${sessionId}?${q}`);
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "ダウンロードに失敗しました");
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || "document.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setStatus("ダウンロードしました", true);
  } catch (err) {
    setStatus(err.message || "エラーが発生しました");
  } finally {
    setBusy(false);
  }
}

function reset() {
  sessionId = null;
  filename = null;
  revokePreview();
  preview.src = "";
  meta.textContent = "";
  fileInput.value = "";
  showWorkspace(false);
  setStatus("");
}

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("is-dragover");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("is-dragover");
});

dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("is-dragover");
  const file = e.dataTransfer?.files?.[0];
  if (file) uploadFile(file);
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  if (file) uploadFile(file);
});

rotateButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const degrees = Number(btn.dataset.degrees);
    rotate(degrees);
  });
});

btnDownload.addEventListener("click", download);
btnReset.addEventListener("click", reset);
