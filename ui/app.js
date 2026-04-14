const API_BASE = "";   // gleicher Origin

let history = [];
let isGenerating = false;

// ── Status-Check ──────────────────────────────────────
async function checkStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    const data = await res.json();
    const el = document.getElementById("status-indicator");
    const text = document.getElementById("status-text");
    if (data.mlx_server) {
      el.className = "status-ok";
      text.textContent = "Modell bereit";
    } else {
      el.className = "status-error";
      text.textContent = "Modell nicht verfügbar";
    }
  } catch {
    const el = document.getElementById("status-indicator");
    document.getElementById("status-text").textContent = "Server nicht erreichbar";
    el.className = "status-error";
  }
}

// ── Nachrichten rendern ───────────────────────────────
function appendMessage(role, content) {
  const container = document.getElementById("messages");

  // Welcome-Nachricht entfernen
  const welcome = container.querySelector(".welcome-message");
  if (welcome) welcome.remove();

  const div = document.createElement("div");
  div.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "Du" : "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = content;

  div.appendChild(avatar);
  div.appendChild(bubble);
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;

  return bubble;
}

function appendStreamingMessage() {
  const container = document.getElementById("messages");
  const welcome = container.querySelector(".welcome-message");
  if (welcome) welcome.remove();

  const div = document.createElement("div");
  div.className = "message assistant";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  const cursor = document.createElement("span");
  cursor.className = "cursor";
  bubble.appendChild(cursor);

  div.appendChild(avatar);
  div.appendChild(bubble);
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;

  return { bubble, cursor };
}

// ── Nachricht senden ──────────────────────────────────
async function sendMessage() {
  if (isGenerating) return;

  const input = document.getElementById("user-input");
  const message = input.value.trim();
  if (!message) return;

  input.value = "";
  input.style.height = "auto";
  isGenerating = true;
  document.getElementById("send-btn").disabled = true;

  appendMessage("user", message);
  history.push({ role: "user", content: message });

  const { bubble, cursor } = appendStreamingMessage();
  let fullResponse = "";

  try {
    const response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: history.slice(0, -1) }),
    });

    if (!response.ok) {
      const err = await response.json();
      bubble.textContent = `Fehler: ${err.detail || response.statusText}`;
      bubble.classList.add("error-message");
      cursor.remove();
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value, { stream: true });
      for (const line of text.split("\n")) {
        if (!line.startsWith("data: ")) continue;
        const data = line.slice(6);
        if (data === "[DONE]") break;
        try {
          const { token } = JSON.parse(data);
          fullResponse += token;
          // Cursor am Ende behalten
          bubble.textContent = fullResponse;
          bubble.appendChild(cursor);
          document.getElementById("messages").scrollTop =
            document.getElementById("messages").scrollHeight;
        } catch {
          // JSON-Parse-Fehler ignorieren
        }
      }
    }

    cursor.remove();
    history.push({ role: "assistant", content: fullResponse });
    saveHistory();

  } catch (err) {
    bubble.textContent = `Verbindungsfehler: ${err.message}`;
    cursor.remove();
  } finally {
    isGenerating = false;
    document.getElementById("send-btn").disabled = false;
    input.focus();
  }
}

// ── Neuer Chat ────────────────────────────────────────
function newChat() {
  history = [];
  const container = document.getElementById("messages");
  container.innerHTML = `
    <div class="welcome-message">
      <h2>Willkommen beim PPS neo Assistenten</h2>
      <p>Stellen Sie Fragen zu den Fachkonzepten, z.B.:</p>
      <div class="example-questions">
        <button class="example-btn" onclick="setQuestion(this.textContent)">
          Was ist das Berechtigungskonzept in Release EE20.4?
        </button>
        <button class="example-btn" onclick="setQuestion(this.textContent)">
          Wie funktioniert die Rechnungsstellung?
        </button>
        <button class="example-btn" onclick="setQuestion(this.textContent)">
          Welche Änderungen gibt es im Modul Organisation?
        </button>
      </div>
    </div>`;
  saveHistory();
}

function setQuestion(text) {
  const input = document.getElementById("user-input");
  input.value = text;
  input.focus();
  autoResize(input);
}

// ── Chat-History in localStorage ──────────────────────
function saveHistory() {
  localStorage.setItem("ppsneo_history", JSON.stringify(history));
}

function loadHistory() {
  try {
    const saved = localStorage.getItem("ppsneo_history");
    if (!saved) return;
    const parsed = JSON.parse(saved);
    if (!Array.isArray(parsed) || parsed.length === 0) return;
    history = parsed;

    // Nachrichten wiederherstellen
    for (const entry of history) {
      appendMessage(entry.role, entry.content);
    }
  } catch {
    // Ignore
  }
}

// ── Textarea auto-resize ──────────────────────────────
function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 160) + "px";
}

// ── Init ──────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  checkStatus();
  setInterval(checkStatus, 30000);

  loadHistory();

  document.getElementById("btn-new-chat").addEventListener("click", newChat);

  const input = document.getElementById("user-input");
  input.addEventListener("input", () => autoResize(input));
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
});
