// Local development API. Replace this with your deployed Render URL before publishing.
const BACKEND_URL = "https://civicai-backend-qrb9.onrender.com";

let CURRENT_USER_ID = null;

supabaseClient.auth.getSession().then(({ data, error }) => {
  const user = data?.session?.user;
  if (error || !user) {
    localStorage.removeItem("civicai_user_id");
    window.location.replace("index.html");
    return;
  }
  CURRENT_USER_ID = user.id;
  localStorage.setItem("civicai_user_id", user.id);
  const label = document.getElementById("account-label");
  if (label) label.textContent = user.user_metadata?.name || user.email || "Citizen account";
  if (document.getElementById("my-reports-list")) loadMyReports();
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

function show(el) { el.classList.remove("hidden"); }
function hide(el) { el.classList.add("hidden"); }

function countSentences(text) {
  return text.split(/[.!?]+/).filter(sentence => sentence.trim()).length;
}

let isSubmitting = false;

document.getElementById("submit-report")?.addEventListener("click", () => {
  if (isSubmitting) return;

  const submitBtn = document.getElementById("submit-report");
  const loadingMsg = document.getElementById("loading-msg");
  const acceptedCard = document.getElementById("accepted-card");
  const errorMsg = document.getElementById("error-msg");

  if (!CURRENT_USER_ID) {
    errorMsg.innerText = "Please wait while we verify your account, then try again.";
    show(errorMsg);
    return;
  }

  hide(acceptedCard);
  hide(errorMsg);

  const description = document.getElementById("description").value.trim();

  isSubmitting = true;
  submitBtn.disabled = true;
  submitBtn.innerText = "Submitting…";
  show(loadingMsg);

  navigator.geolocation.getCurrentPosition(async (position) => {
    const lat = position.coords.latitude;
    const lng = position.coords.longitude;
    const fileInput = document.getElementById("photo-input");
    const file = fileInput.files[0];

    if (!file) {
      hide(loadingMsg);
      errorMsg.innerText = "Please select or capture a photo first.";
      show(errorMsg);
      return;
    }

    const formData = new FormData();
    formData.append("image", file);
    formData.append("lat", lat);
    formData.append("lng", lng);
    formData.append("user_id", CURRENT_USER_ID);
    formData.append("description", description);

    try {
      const response = await fetch(`${BACKEND_URL}/upload-report`, {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        throw new Error(errorBody.detail || "Upload failed");
      }

      const result = await response.json();

      hide(loadingMsg);
      isSubmitting = false;
      submitBtn.disabled = false;
      submitBtn.innerText = "📤 Submit Report";
      document.getElementById("result-category").innerText = result.category;
      document.getElementById("result-severity").innerText = result.severity;
      document.getElementById("result-sentiment").innerText = result.sentiment;
      document.getElementById("result-address").innerText = result.address;

      if (result.is_duplicate_of_existing) {
        show(document.getElementById("duplicate-note"));
      }

      show(acceptedCard);
      loadMyReports(); // refresh the list below with the new submission
    } catch (err) {
      hide(loadingMsg);
      isSubmitting = false;
      submitBtn.disabled = false;
      submitBtn.innerText = "📤 Submit Report";
      errorMsg.innerText = err.message || "Something went wrong submitting your report. Please try again.";
      show(errorMsg);
    }
  }, (err) => {
    hide(loadingMsg);
    isSubmitting = false;
    submitBtn.disabled = false;
    submitBtn.innerText = "📤 Submit Report";
    if (err.code === err.PERMISSION_DENIED)
      errorMsg.innerText = "Location access was denied. Please allow location in your browser settings and try again.";
    else if (err.code === err.POSITION_UNAVAILABLE)
      errorMsg.innerText = "Location unavailable. Make sure GPS/location is enabled on your device.";
    else
      errorMsg.innerText = "Location request timed out. Please try again.";
    show(errorMsg);
  }, { timeout: 8000 });
});

// ----- My Reports status list -----
async function loadMyReports() {
  const listEl = document.getElementById("my-reports-list");
  if (!listEl || !CURRENT_USER_ID) return;

  try {
    const response = await fetch(`${BACKEND_URL}/reports/user/${CURRENT_USER_ID}`);
    const reports = await response.json();

    if (!reports.length) {
      listEl.innerText = "You haven't submitted any reports yet.";
      return;
    }

    listEl.innerHTML = reports.map(r => `
      <div class="status-card ${r.status === 'resolved' ? 'status-card-resolved' : ''}">
        <p><strong>${escapeHtml(r.category)}</strong> — ${escapeHtml(r.address || "Location unavailable")}</p>
        <p class="severity severity-${safeClass(r.severity, "medium")}">Severity: ${escapeHtml(r.severity || "medium")}</p>
        <p class="status-badge status-${safeClass(r.status, "pending")}">${escapeHtml(formatStatus(r.status))}</p>
      </div>
    `).join("");
  } catch (err) {
    listEl.innerText = "Couldn't load your reports right now.";
  }
}

function formatStatus(status) {
  if (status === "pending") return "⏳ Pending review";
  if (status === "in-progress") return "🔧 Being worked on";
  if (status === "resolved") return "✅ Resolved";
  return status;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}

function safeClass(value, fallback) {
  return /^[a-z-]+$/.test(value || "") ? value : fallback;
}

// Load the status list as soon as the page opens
if (document.getElementById("my-reports-list")) {
  // Auto-refresh every 15 seconds so status changes from admin show immediately
  setInterval(loadMyReports, 15000);
}
