let isSignupMode = false;

const form        = document.getElementById("auth-form");
const nameInput   = document.getElementById("name");
const nameGroup   = document.getElementById("name-group");
const emailInput  = document.getElementById("email");
const passwordInput = document.getElementById("password");
const submitBtn   = document.getElementById("auth-submit");
const errorMsg    = document.getElementById("auth-error");
const toggleLink  = document.getElementById("toggle-mode");
const toggleText  = document.getElementById("toggle-text");

const existingUserId = localStorage.getItem("civicai_user_id");
if (existingUserId) window.location.href = "report.html";

toggleLink.addEventListener("click", (e) => {
  e.preventDefault();
  isSignupMode = !isSignupMode;

  if (isSignupMode) {
    nameGroup.classList.remove("hidden");
    passwordInput.autocomplete = "new-password";
    submitBtn.innerText = "Sign up";
    toggleText.innerText = "Already have an account?";
    toggleLink.innerText = "Log in";
    document.getElementById("auth-title").innerText = "Create account";
    document.getElementById("auth-subtitle").innerText = "Join CivicAI and start reporting issues";
  } else {
    nameGroup.classList.add("hidden");
    passwordInput.autocomplete = "current-password";
    submitBtn.innerText = "Log in";
    toggleText.innerText = "Don't have an account?";
    toggleLink.innerText = "Sign up";
    document.getElementById("auth-title").innerText = "Welcome back";
    document.getElementById("auth-subtitle").innerText = "Log in to report or track civic issues";
  }
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorMsg.classList.add("hidden");

  const email    = emailInput.value.trim();
  const password = passwordInput.value;

  if (!email || !password) {
    errorMsg.innerText = "Email and password are required.";
    errorMsg.classList.remove("hidden");
    return;
  }

  try {
    let result;
    if (isSignupMode) {
      result = await supabaseClient.auth.signUp({
        email,
        password,
        options: { data: { name: nameInput.value.trim() } },
      });
      if (result.error) throw result.error;
    } else {
      result = await supabaseClient.auth.signInWithPassword({ email, password });
      if (result.error) throw result.error;
    }

    const userId = result.data.user?.id;
    if (!userId) throw new Error("Please confirm your email address, then log in.");
    localStorage.setItem("civicai_user_id", userId);
    window.location.href = "report.html";

  } catch (err) {
    errorMsg.innerText = err.message || "Something went wrong. Please try again.";
    errorMsg.classList.remove("hidden");
  }
});
