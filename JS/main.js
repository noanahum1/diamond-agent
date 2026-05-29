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