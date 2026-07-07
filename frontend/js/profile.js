/**
 * profile.js — profile info editing, password change, and theme preference
 * (synced to the backend as well as localStorage so it's remembered across devices).
 */
function showTab(tabId) {
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("hidden"));
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.getElementById(tabId).classList.remove("hidden");
  document.querySelector(`[data-tab="${tabId}"]`).classList.add("active");
}

async function initProfilePage() {
  let user;
  try {
    user = await Api.me();
  } catch (err) {
    showToast("Couldn't load your profile.", { icon: "⚠️" });
    return;
  }

  document.getElementById("profile-initial").textContent = (user.display_name || user.username)[0].toUpperCase();
  document.getElementById("profile-name-header").textContent = user.display_name || user.username;
  document.getElementById("profile-username-header").textContent = `@${user.username}`;

  document.getElementById("display_name").value = user.display_name || "";
  document.getElementById("email").value = user.email;
  document.getElementById("theme_preference").value = user.theme_preference;

  document.getElementById("profile-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const alertBox = document.getElementById("profile-alert");
    try {
      const updated = await Api.updateProfile({
        display_name: document.getElementById("display_name").value.trim(),
        email: document.getElementById("email").value.trim(),
        theme_preference: document.getElementById("theme_preference").value,
      });
      document.documentElement.setAttribute("data-theme", updated.theme_preference);
      localStorage.setItem(Theme.KEY, updated.theme_preference);
      alertBox.className = "alert alert-success";
      alertBox.textContent = "Profile updated!";
      alertBox.classList.remove("hidden");
      document.getElementById("profile-name-header").textContent = updated.display_name || updated.username;
    } catch (err) {
      alertBox.className = "alert alert-error";
      alertBox.textContent = err.message;
      alertBox.classList.remove("hidden");
    }
  });

  document.getElementById("password-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const alertBox = document.getElementById("password-alert");
    try {
      await Api.changePassword({
        current_password: document.getElementById("current_password").value,
        new_password: document.getElementById("new_password").value,
      });
      alertBox.className = "alert alert-success";
      alertBox.textContent = "Password changed!";
      alertBox.classList.remove("hidden");
      document.getElementById("password-form").reset();
    } catch (err) {
      alertBox.className = "alert alert-error";
      alertBox.textContent = err.message;
      alertBox.classList.remove("hidden");
    }
  });

  document.getElementById("sound-toggle").checked = Sound.enabled();
  document.getElementById("sound-toggle").addEventListener("change", (e) => {
    localStorage.setItem("kana_trainer_sound", e.target.checked ? "on" : "off");
  });
}
