(() => {
  const timer = document.querySelector("#timer");
  const submitForm = document.querySelector("#submit-exam");
  const status = document.querySelector("#save-status");
  let submitting = false;
  document.querySelectorAll(".answer-form input[type=radio]").forEach(input => {
    input.addEventListener("change", async event => {
      const form = event.target.form;
      status.textContent = "Saving…";
      try {
        const response = await fetch(form.action, {method: "POST", body: new FormData(form), headers: {"X-Requested-With": "XMLHttpRequest"}});
        if (!response.ok) throw new Error((await response.json()).error || "Save failed");
        status.textContent = "Answer saved.";
      } catch (error) { status.textContent = error.message; }
    });
  });
  if (!timer || !submitForm) return;
  const expires = new Date(timer.dataset.expires).getTime();
  const tick = () => {
    const remaining = Math.max(0, expires - Date.now());
    const total = Math.ceil(remaining / 1000);
    timer.textContent = `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
    if (remaining <= 0 && !submitting) { submitting = true; submitForm.submit(); }
  };
  tick(); setInterval(tick, 1000);
})();
