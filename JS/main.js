document.addEventListener("DOMContentLoaded", () => {
  const themeToggle = document.getElementById("theme-toggle");

  const savedTheme = localStorage.getItem("diamond-theme");

  if (savedTheme === "dark") {
    document.documentElement.setAttribute("data-theme", "dark");

    if (themeToggle) {
      themeToggle.textContent = "☀";
    }
  } else {
    document.documentElement.setAttribute("data-theme", "light");

    if (themeToggle) {
      themeToggle.textContent = "☾";
    }
  }

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const currentTheme = document.documentElement.getAttribute("data-theme");

      if (currentTheme === "dark") {
        document.documentElement.setAttribute("data-theme", "light");
        localStorage.setItem("diamond-theme", "light");
        themeToggle.textContent = "☾";
      } else {
        document.documentElement.setAttribute("data-theme", "dark");
        localStorage.setItem("diamond-theme", "dark");
        themeToggle.textContent = "☀";
      }
    });
  }
});

function scrollToChat() {
  const chat = document.getElementById("chatbot");

  if (chat) {
    chat.scrollIntoView({ behavior: "smooth" });
  }
}

function showInfo() {
  const notification = document.createElement("div");

  notification.className = "notification";
  notification.textContent =
    "האייג׳נט מנתח מאפייני יהלומים, מסביר על איכות, מחיר ודמיון בין פריטים.";

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.remove();
  }, 3000);
}

const API_URL = "https://diamond-agent-fvvd.onrender.com/chat";
const WARMUP_URL = "https://diamond-agent-fvvd.onrender.com/warmup";

fetch(WARMUP_URL).catch((error) => {
  console.log("Warmup request failed:", error);
});

const sessionId = crypto.randomUUID();

const chatForm = document.getElementById("chat-form");
const userInput = document.getElementById("user-input");
const chatWindow = document.getElementById("chat-window");

function addMessage(text, sender) {
  const messageDiv = document.createElement("div");

  messageDiv.className =
    sender === "user" ? "user-message" : "bot-message";

  messageDiv.textContent = text.trim();

  chatWindow.appendChild(messageDiv);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

if (chatForm) {
  chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const message = userInput.value.trim();

    if (!message) {
      return;
    }

    addMessage(message, "user");
    userInput.value = "";

    const loadingMessage = document.createElement("div");
    loadingMessage.className = "bot-message";
    loadingMessage.textContent = "⏳ בודק עבורך...";
    chatWindow.appendChild(loadingMessage);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: message, session_id: sessionId,
        }),
      });

      const data = await response.json();

      loadingMessage.textContent =
        data.answer ? data.answer.trim() : "לא התקבלה תשובה מהשרת.";
    } catch (error) {
      loadingMessage.textContent =
        "לא הצלחתי להתחבר לשרת.\nנא לבדוק שהשרת ב־Render פעיל ושאין שגיאת CORS או שגיאת API.";
      console.error(error);
    }

    chatWindow.scrollTop = chatWindow.scrollHeight;
  });
}