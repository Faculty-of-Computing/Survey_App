let duration = 5 * 60; // 5 minutes in seconds
const countdownElement = document.getElementById("countdownSpan");

const timer = setInterval(() => {
  const minutes = Math.floor(duration / 60);
  const seconds = duration % 60;

  countdownElement.textContent = `${minutes
    .toString()
    .padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;

  if (--duration < 0) {
    clearInterval(timer);
    countdownElement.textContent = "Expired";
    document.getElementById("submitButton").disabled = true;
  }
}, 1000);
document.addEventListener("DOMContentLoaded", () => {
  const otpInput = document.getElementById("otpInput");
  otpInput.addEventListener("input", () => {
    if (otpInput.value.length === 6) {
      otpInput.classList.remove("border-red-500");
      otpInput.classList.add("border-green-500");
    } else {
      otpInput.classList.remove("border-green-500");
      otpInput.classList.add("border-red-500");
    }
  });
});
