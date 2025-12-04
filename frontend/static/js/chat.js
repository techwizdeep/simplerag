// DOM elements
const chatContainer = document.getElementById("chat-container");
const chatHistory = document.getElementById("chat-history");
const loadingIndicator = document.getElementById("loading-indicator");
const errorContainer = document.getElementById("error-container");
const errorMessage = document.getElementById("error-message");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");

const btnPersonalInfo = document.getElementById("btn-personal-info");
const btnWarranty = document.getElementById("btn-warranty");
const btnCompany = document.getElementById("btn-company");

// Templates
const emptyChatTemplate = document.getElementById("empty-chat-template");
const userMessageTemplate = document.getElementById("user-message-template");
const assistantMessageTemplate = document.getElementById(
  "assistant-message-template"
);

// State
let hasMessages = false;

// ---------------- Helpers ----------------

function clearError() {
  errorContainer.classList.add("d-none");
  errorMessage.textContent = "";
}

function showError(msg) {
  errorMessage.textContent = msg;
  errorContainer.classList.remove("d-none");
}

function showLoading() {
  loadingIndicator.classList.remove("d-none");
}

function hideLoading() {
  loadingIndicator.classList.add("d-none");
}

function scrollToBottom() {
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function renderEmptyStateIfNeeded() {
  if (!hasMessages && chatHistory.children.length === 0) {
    const clone = emptyChatTemplate.content.cloneNode(true);
    chatHistory.appendChild(clone);
  }
}

function clearEmptyState() {
  if (!hasMessages) {
    chatHistory.innerHTML = "";
  }
}

// ---------------- Rendering messages ----------------

function addUserMessage(text) {
  clearEmptyState();
  hasMessages = true;

  const clone = userMessageTemplate.content.cloneNode(true);
  const contentEl = clone.querySelector(".message-content");
  contentEl.textContent = text;
  chatHistory.appendChild(clone);
  scrollToBottom();
}

function addAssistantMessage(text) {
  clearEmptyState();
  hasMessages = true;

  const clone = assistantMessageTemplate.content.cloneNode(true);
  const contentEl = clone.querySelector(".message-content");
  contentEl.textContent = text;
  chatHistory.appendChild(clone);
  scrollToBottom();
}

// ---------------- API call ----------------

async function sendMessageToApi(question) {
  const payload = {
    messages: [{ role: "user", content: question }],
    top_k: 5,
  };

  clearError();
  showLoading();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      // If Easy Auth is enabled and using cookies, include them:
      credentials: "include",
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      let text;
      try {
        text = await res.text();
      } catch {
        text = `HTTP ${res.status}`;
      }
      throw new Error(`Request failed: ${text}`);
    }

    const data = await res.json();
    const answer = data.answer || "[No answer returned]";
    addAssistantMessage(answer);
  } catch (err) {
    console.error(err);
    showError("Something went wrong while contacting the server.");
    addAssistantMessage("Sorry, I couldn’t process that request.");
  } finally {
    hideLoading();
  }
}

// ---------------- Event handlers ----------------

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;

  addUserMessage(text);
  chatInput.value = "";
  sendMessageToApi(text);
});

btnPersonalInfo.addEventListener("click", () => {
  const q = "What personal information do you have about me?";
  chatInput.value = q;
  chatInput.focus();
});

btnWarranty.addEventListener("click", () => {
  const q = "How can I submit a warranty claim?";
  chatInput.value = q;
  chatInput.focus();
});

btnCompany.addEventListener("click", () => {
  const q = "Tell me about the company.";
  chatInput.value = q;
  chatInput.focus();
});

// ---------------- Init ----------------

renderEmptyStateIfNeeded();
clearError();
hideLoading();
