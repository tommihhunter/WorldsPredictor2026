// Compare picker: navigate to the canonical static page, <a>-vs-<b> with a < b by code.
(() => {
  const f = document.getElementById('compare-pick');
  if (!f) return;
  f.addEventListener('submit', (e) => {
    e.preventDefault();
    const x = f.elements.a.value;
    const y = f.elements.b.value;
    f.querySelector('.msg').hidden = x !== y;
    if (x === y) return;
    location.href = `${f.dataset.base}${[x, y].sort().join('-vs-').toLowerCase()}/`;
  });
})();
