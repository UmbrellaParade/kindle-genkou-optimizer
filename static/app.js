// タブ切り替え
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
  });
});

// ファイル選択表示
function bindFileInput(inputId, labelId) {
  const input = document.getElementById(inputId);
  const label = document.getElementById(labelId);
  if (!input || !label) return;
  input.addEventListener("change", () => {
    label.textContent = input.files[0] ? `選択中: ${input.files[0].name}` : "";
  });
}

bindFileInput("check-file", "check-filename");
bindFileInput("convert-file", "convert-filename");
bindFileInput("cover-file", "cover-filename");

// ドラッグ＆ドロップ
document.querySelectorAll(".drop-area").forEach(area => {
  area.addEventListener("dragover", e => {
    e.preventDefault();
    area.classList.add("dragover");
  });
  area.addEventListener("dragleave", () => area.classList.remove("dragover"));
  area.addEventListener("drop", e => {
    e.preventDefault();
    area.classList.remove("dragover");
    const input = area.closest(".file-drop").querySelector("input[type=file]");
    if (input && e.dataTransfer.files.length) {
      const transfer = new DataTransfer();
      transfer.items.add(e.dataTransfer.files[0]);
      input.files = transfer.files;
      input.dispatchEvent(new Event("change"));
    }
  });
});

function showLoading() { document.getElementById("loading").classList.remove("hidden"); }
function hideLoading() { document.getElementById("loading").classList.add("hidden"); }

// ===== チェック =====
document.getElementById("check-form").addEventListener("submit", async e => {
  e.preventDefault();
  const file = document.getElementById("check-file").files[0];
  if (!file) { alert("ファイルを選択してください"); return; }

  const formData = new FormData(e.target);
  showLoading();

  try {
    const res = await fetch("/api/check", { method: "POST", body: formData });
    const data = await res.json();
    if (data.error) { alert("エラー: " + data.error); return; }
    renderCheckResult(data);
  } catch (err) {
    alert("通信エラーが発生しました");
  } finally {
    hideLoading();
  }
});

function renderCheckResult({ stats, issues }) {
  document.getElementById("stat-chars").textContent = stats.total_chars.toLocaleString() + " 字";
  document.getElementById("stat-pages").textContent = stats.estimated_pages.toLocaleString() + " ページ";
  document.getElementById("stat-sentences").textContent = stats.sentence_count.toLocaleString() + " 文";
  document.getElementById("stat-lines").textContent = stats.line_count.toLocaleString() + " 行";

  // 章別
  const tbody = document.getElementById("chapter-tbody");
  tbody.innerHTML = "";
  const section = document.getElementById("chapters-section");
  if (stats.chapters && stats.chapters.length) {
    section.classList.remove("hidden");
    stats.chapters.forEach(ch => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${ch.title}</td><td>${ch.chars.toLocaleString()} 字</td>`;
      tbody.appendChild(tr);
    });
  } else {
    section.classList.add("hidden");
  }

  // 品質チェック
  const list = document.getElementById("issues-list");
  list.innerHTML = "";
  if (!issues || issues.length === 0) {
    list.innerHTML = '<p class="no-issues">✅ 問題は検出されませんでした</p>';
  } else {
    issues.forEach(issue => {
      const div = document.createElement("div");
      div.className = `issue-item ${issue.type}`;
      const icon = issue.type === "error" ? "🔴" : "🟡";
      const examples = issue.examples.length
        ? `<div class="issue-examples">例: ${issue.examples.join(" / ")}</div>`
        : "";
      div.innerHTML = `
        <div class="issue-title">${icon} ${issue.message}</div>
        <div class="issue-count">${issue.count} 箇所検出</div>
        ${examples}
      `;
      list.appendChild(div);
    });
  }

  document.getElementById("check-result").classList.remove("hidden");
  document.getElementById("check-result").scrollIntoView({ behavior: "smooth" });
}

// ===== プレビュー =====
document.getElementById("preview-btn").addEventListener("click", async () => {
  const file = document.getElementById("convert-file").files[0];
  if (!file) { alert("先に原稿ファイルを選択してください"); return; }

  const formData = new FormData();
  formData.append("file", file);
  showLoading();

  try {
    const res = await fetch("/api/preview", { method: "POST", body: formData });
    const data = await res.json();
    if (data.error) { alert("エラー: " + data.error); return; }
    document.getElementById("preview-content").innerHTML = data.html;
    document.getElementById("preview-modal").classList.remove("hidden");
  } catch (err) {
    alert("通信エラーが発生しました");
  } finally {
    hideLoading();
  }
});

function closePreview() {
  document.getElementById("preview-modal").classList.add("hidden");
}

document.addEventListener("keydown", e => {
  if (e.key === "Escape") closePreview();
});

// ===== EPUB変換 =====
document.getElementById("convert-form").addEventListener("submit", async e => {
  e.preventDefault();
  const file = document.getElementById("convert-file").files[0];
  if (!file) { alert("原稿ファイルを選択してください"); return; }

  const formData = new FormData(e.target);
  showLoading();

  try {
    const res = await fetch("/api/convert", { method: "POST", body: formData });
    if (!res.ok) {
      const data = await res.json();
      alert("エラー: " + (data.error || "変換に失敗しました"));
      return;
    }
    const blob = await res.blob();
    const cd = res.headers.get("Content-Disposition") || "";
    const match = cd.match(/filename\*?=(?:UTF-8'')?["']?([^"';\n]+)/i);
    const filename = match ? decodeURIComponent(match[1]) : "output.epub";
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert("通信エラーが発生しました");
  } finally {
    hideLoading();
  }
});
