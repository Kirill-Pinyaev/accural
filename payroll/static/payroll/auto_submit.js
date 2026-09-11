document.addEventListener("change", (event) => {
  if (!event.target.matches("[data-auto-submit]")) {
    return;
  }
  const form = event.target.form;
  if (!form) {
    return;
  }
  if (form.requestSubmit) {
    form.requestSubmit();
  } else {
    form.submit();
  }
});
