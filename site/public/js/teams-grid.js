// Teams grid: filter by region and tier, sort by a card data attribute. The page is complete without
// this script (cards are server-rendered in rank order); it only hides and reorders them. State lives in
// location.hash (#region=LCK&tier=S&sort=odds) so a filtered view can be shared.
(() => {
  const grid = document.getElementById('teams-grid');
  const filters = document.querySelector('.filters');
  if (!grid || !filters) return;
  const cards = [...grid.children];
  const empty = document.getElementById('teams-empty');
  const state = { region: '', tier: '', sort: '' };

  const apply = () => {
    let shown = 0;
    for (const c of cards) {
      const ok = (!state.region || c.dataset.region === state.region) && (!state.tier || c.dataset.tier === state.tier);
      c.style.display = ok ? '' : 'none';
      if (ok) shown++;
    }
    const k = state.sort;
    const sorted = [...cards].sort((a, b) =>
      k ? Number(b.dataset[k]) - Number(a.dataset[k]) || a.dataset.rank - b.dataset.rank : a.dataset.rank - b.dataset.rank);
    grid.append(...sorted);
    if (empty) empty.hidden = shown > 0;
    for (const key of ['region', 'tier', 'sort']) {
      for (const b of filters.querySelectorAll(`.chip[data-${key}]`)) {
        b.setAttribute('aria-pressed', String(b.dataset[key] === state[key]));
      }
    }
  };

  const write = () => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(state)) if (v) q.set(k, v);
    const h = q.toString();
    history.replaceState(null, '', h ? `#${h}` : location.pathname + location.search);
  };

  const read = () => {
    const q = new URLSearchParams(location.hash.slice(1));
    for (const k of Object.keys(state)) {
      const v = q.get(k) || '';
      // Ignore values no chip offers, so a stale or hand-edited hash cannot hide every card.
      state[k] = v && filters.querySelector(`.chip[data-${k}="${CSS.escape(v)}"]`) ? v : '';
    }
  };

  filters.addEventListener('click', (e) => {
    const b = e.target.closest('.chip');
    if (!b) return;
    for (const k of Object.keys(state)) {
      if (k in b.dataset) state[k] = k === 'sort' && state.sort === b.dataset.sort ? '' : b.dataset[k];
    }
    write();
    apply();
  });
  window.addEventListener('hashchange', () => { read(); apply(); });

  filters.hidden = false;
  read();
  apply();
})();
