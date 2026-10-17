// Players grid: role chips filter the tiles; the state lives in location.hash (#role=MID) so a filtered view can be shared.
(() => {
  const bar = document.querySelector('.filters');
  const tiles = [...document.querySelectorAll('#players-grid > a')];
  if (!bar || !tiles.length) return;
  bar.hidden = false;
  const chips = [...bar.querySelectorAll('.chip')];
  const apply = (role) => {
    chips.forEach((c) => c.setAttribute('aria-pressed', String((c.dataset.role || '') === role)));
    tiles.forEach((t) => { t.hidden = !!role && t.dataset.role !== role; });
  };
  const fromHash = () => (/role=([A-Z]+)/.exec(location.hash) || [])[1] || '';
  chips.forEach((c) => c.addEventListener('click', () => {
    const role = c.dataset.role || '';
    history.replaceState(null, '', role ? `#role=${role}` : location.pathname);
    apply(role);
  }));
  apply(fromHash());
})();
