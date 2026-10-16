// Series picker: a card with data-show="<detail id>" shows that detail and hides the other [data-detail]
// panels in the same [data-select] group. No animation. Without this script the server-picked detail shows.
document.addEventListener('click', (e) => {
  const card = e.target.closest('[data-show]');
  const group = card && card.closest('[data-select]');
  if (!group) return;
  for (const c of group.querySelectorAll('[data-show]')) {
    const on = c === card;
    c.classList.toggle('is-selected', on);
    c.setAttribute('aria-pressed', String(on));
  }
  let shown = null;
  for (const d of group.querySelectorAll('[data-detail]')) {
    d.hidden = d.id !== card.dataset.show;
    if (!d.hidden) shown = d;
  }
  if (shown && matchMedia('(max-width: 640px)').matches) shown.scrollIntoView({ block: 'nearest' });
});
