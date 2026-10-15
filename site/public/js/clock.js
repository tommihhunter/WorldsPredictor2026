// Day boundaries without a rebuild: mark series whose start has passed, and date the Today card
// from the viewer's clock in NZDT. Rows carry data-start as an ISO UTC time (site/src/lib/stage.ts toUtc).
(() => {
  const now = Date.now();
  for (const el of document.querySelectorAll('[data-start]')) {
    if (el.classList.contains('started') || now < Date.parse(el.dataset.start)) continue;
    el.classList.add('started');
    const when = el.querySelector('.when');
    if (when && !el.querySelector('.result')) when.append(' (started)');
  }
  const today = new Intl.DateTimeFormat('en-GB', { timeZone: 'Pacific/Auckland', day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date());
  for (const el of document.querySelectorAll('[data-today]')) el.textContent = today;
})();
