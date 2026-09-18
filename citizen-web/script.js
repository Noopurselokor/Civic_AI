// Local development API. Replace this with your deployed Render URL before publishing.
const BACKEND_URL = "https://civicai-backend-qrb9.onrender.com";

const CURRENT_USER_ID = localStorage.getItem("civicai_user_id");

// If nobody's logged in, send them back to the login page
if (!CURRENT_USER_ID && window.location.pathname.includes("report.html")) {
  window.location.href = "index.html";
}

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
  if (!listEl) return;

  try {
    const response = await fetch(`${BACKEND_URL}/reports/user/${CURRENT_USER_ID}`);
    const reports = await response.json();

    if (!reports.length) {
      listEl.innerText = "You haven't submitted any reports yet.";
      return;
    }

    listEl.innerHTML = reports.map(r => `
      <div class="status-card ${r.status === 'resolved' ? 'status-card-resolved' : ''}">
        <p><strong>${r.category}</strong> — ${r.address}</p>
        <p class="severity severity-${r.severity || 'medium'}">Severity: ${r.severity || 'medium'}</p>
        <p class="status-badge status-${r.status}">${formatStatus(r.status)}</p>
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

// Load the status list as soon as the page opens
if (document.getElementById("my-reports-list")) {
  loadMyReports();
  // Auto-refresh every 15 seconds so status changes from admin show immediately
  setInterval(loadMyReports, 15000);
}
