// Teams grid: filter cards by region. The page is complete without this script (every card is server-rendered
// in rank order and the chips stay hidden); it only hides cards. State lives in location.hash (#region=LCK).
(() => {
  const grid = document.getElementById('teams-grid');
  const filters = document.querySelector('.filters');
  if (!grid || !filters) return;
  const cards = [...grid.children];
  let region = '';

  const apply = () => {
    for (const c of cards) c.style.display = !region || c.dataset.region === region ? '' : 'none';
    for (const b of filters.querySelectorAll('.chip[data-region]')) b.setAttribute('aria-pressed', String(b.dataset.region === region));
  };

  const read = () => {
    const v = new URLSearchParams(location.hash.slice(1)).get('region') || '';
    // Ignore values no chip offers, so a stale or hand-edited hash cannot hide every card.
    region = v && filters.querySelector(`.chip[data-region="${CSS.escape(v)}"]`) ? v : '';
  };

  filters.addEventListener('click', (e) => {
    const b = e.target.closest('.chip[data-region]');
    if (!b) return;
    region = b.dataset.region;
    history.replaceState(null, '', region ? `#region=${encodeURIComponent(region)}` : location.pathname + location.search);
    apply();
  });
  window.addEventListener('hashchange', () => { read(); apply(); });

  filters.hidden = false;
  read();
  apply();
})();
