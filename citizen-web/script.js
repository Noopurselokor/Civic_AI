const BACKEND_URL = "https://your-backend.onrender.com"; // update after deploying backend

document.getElementById("submit-report")?.addEventListener("click", () => {
  navigator.geolocation.getCurrentPosition(async (position) => {
    const lat = position.coords.latitude;
    const lng = position.coords.longitude;
    const fileInput = document.getElementById("photo-input");
    const file = fileInput.files[0];

    const formData = new FormData();
    formData.append("image", file);
    formData.append("lat", lat);
    formData.append("lng", lng);

    const response = await fetch(`${BACKEND_URL}/upload-report`, {
      method: "POST",
      body: formData
    });
    const result = await response.json();
    document.getElementById("status-msg").innerText = "Report submitted!";
  });
});
