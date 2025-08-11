// Minimal, backend-safe UI helpers for login/signup

(function () {
  // Add focus/filled classes for inputs (nice subtle animation hooks)
  const inputs = document.querySelectorAll('.card .input input');
  inputs.forEach((el) => {
    const wrapper = el.closest('.input');
    if (!wrapper) return;

    const setState = () => {
      wrapper.classList.toggle('filled', !!el.value.trim());
    };

    el.addEventListener('focus', () => wrapper.classList.add('focused'));
    el.addEventListener('blur', () => wrapper.classList.remove('focused'));
    el.addEventListener('input', setState);
    // init
    setState();
  });

  // Optional: password visibility toggle
  // Works if you add an element with data-toggle="password" inside the password .input
  // (see small HTML snippet below)
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-toggle="password"]');
    if (!btn) return;
    const input = btn.closest('.input')?.querySelector('input[type="password"], input[type="text"]');
    if (!input) return;
    const isHidden = input.type === 'password';
    input.type = isHidden ? 'text' : 'password';
    // If you want to flip an icon/text:
    btn.setAttribute('aria-pressed', String(isHidden));
  });

  // Prevent double submit & show quick feedback
  const forms = document.querySelectorAll('form.card');
  forms.forEach((form) => {
    let submitting = false;
    form.addEventListener('submit', () => {
      if (submitting) {
        // block double submit
        event.preventDefault?.();
        return false;
      }
      submitting = true;
      const btn = form.querySelector('.btn[type="submit"], .btn');
      if (btn) {
        btn.dataset.originalText = btn.textContent;
        btn.textContent = 'Please wait…';
        btn.disabled = true;
      }
      // If navigation doesn’t happen (e.g., validation error server-side),
      // re-enable after a short timeout so the form remains usable.
      setTimeout(() => {
        if (btn) {
          btn.textContent = btn.dataset.originalText || 'Submit';
          btn.disabled = false;
        }
        submitting = false;
      }, 3500);
    });
  });

  // If there’s an error flash, do a subtle shake to draw attention
  const hasError = document.querySelector('.flash .error');
  if (hasError) {
    const card = document.querySelector('form.card');
    if (card) {
      card.classList.add('shake');
      setTimeout(() => card.classList.remove('shake'), 600);
    }
  }
})();
