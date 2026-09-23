const profileList = document.getElementById("profile-reports-list");
const historyMessage = document.getElementById("history-message");
const BACKEND_URL = "https://civicai-backend-qrb9.onrender.com";

supabaseClient.auth.getSession().then(async ({ data, error }) => {
  const user = data?.session?.user;
  if (error || !user) {
    localStorage.removeItem("civicai_user_id");
    window.location.replace("index.html");
    return;
  }

  localStorage.setItem("civicai_user_id", user.id);
  const name = user.user_metadata?.name || "Citizen";
  document.getElementById("profile-name").textContent = name;
  document.getElementById("profile-email").textContent = user.email || "";
  document.getElementById("profile-avatar").textContent = name.trim().charAt(0).toUpperCase() || "C";
  await loadProfileHistory(user.id);
});

document.querySelectorAll("[data-sign-out]").forEach(button => {
  button.addEventListener("click", async () => {
    button.disabled = true;
    const { error } = await supabaseClient.auth.signOut();
    localStorage.removeItem("civicai_user_id");
    if (error) {
      button.disabled = false;
      window.alert("Could not log out. Please try again.");
      return;
    }
    window.location.replace("index.html");
  });
});

async function loadProfileHistory(userId) {
  try {
    const response = await fetch(`${BACKEND_URL}/reports/user/${encodeURIComponent(userId)}`);
    if (!response.ok) throw new Error("Reports are unavailable");
    const reports = await response.json();

    document.getElementById("total-reports").textContent = reports.length;
    document.getElementById("resolved-reports").textContent = reports.filter(report => report.status === "resolved").length;
    document.getElementById("open-reports").textContent = reports.filter(report => report.status !== "resolved").length;

    if (!reports.length) {
      historyMessage.textContent = "You haven’t submitted any reports yet.";
      return;
    }

    historyMessage.textContent = "Your submitted civic reports and their latest status.";
    profileList.replaceChildren(...reports.map(createReportCard));
  } catch (_) {
    historyMessage.textContent = "We couldn’t load your report history right now. Please try again later.";
  }
}

function createReportCard(report) {
  const card = document.createElement("article");
  card.className = `status-card ${report.status === "resolved" ? "status-card-resolved" : ""}`;

  const title = document.createElement("p");
  const category = document.createElement("strong");
  category.textContent = report.category || "Civic issue";
  title.append(category, document.createTextNode(` — ${report.address || "Location unavailable"}`));

  const date = document.createElement("p");
  date.className = "report-date";
  date.textContent = report.created_at ? new Date(report.created_at).toLocaleString() : "Submission date unavailable";

  const severity = document.createElement("p");
  severity.className = `severity severity-${safeClass(report.severity, "medium")}`;
  severity.textContent = `Severity: ${report.severity || "medium"}`;

  const status = document.createElement("p");
  status.className = `status-badge status-${safeClass(report.status, "pending")}`;
  status.textContent = formatStatus(report.status);

  card.append(title, date, severity, status);
  return card;
}

function safeClass(value, fallback) {
  return /^[a-z-]+$/.test(value || "") ? value : fallback;
}

function formatStatus(status) {
  if (status === "pending") return "Pending review";
  if (status === "in-progress") return "Being worked on";
  if (status === "resolved") return "Resolved";
  return status || "Status unavailable";
}
