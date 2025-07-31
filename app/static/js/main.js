const loginButton = document.getElementById("loginButton");
const registerButton = document.getElementById("registerButton");

loginButton.addEventListener("click", (e) => {
  const url = loginButton.getAttribute("data-url");
  if (url && window.location.href !== url) {
    window.location.href = url;
  }
  e.preventDefault();
});

registerButton.addEventListener("click", (e) => {
  const url = registerButton.getAttribute("data-url");
  if (url && window.location.href !== url) {
    window.location.href = url;
  }
  e.preventDefault();
});

function toggleTab(tab) {
  document
    .getElementById("surveys")
    .classList.toggle("hidden", tab !== "surveys");
  document
    .getElementById("responses")
    .classList.toggle("hidden", tab !== "responses");
}
