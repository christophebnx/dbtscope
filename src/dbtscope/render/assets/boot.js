// Page boot: shared layout store, tabs, the export / import / reset of manual arrangements, and the
// services that save files and exported images. The page-wide globals (PAGE, L…) come from common.js.
const LAYOUT_FORMAT = 'dbt-erd-layout';   // domain/layout.LAYOUT_FORMAT, the format of the layout file

// Manual positions, per view and per scope (universe: detail level; detail: what is drawn).
// Kept in the browser, and seeded from the dbt-erd-layout.json embedded at generation:
// whichever copy was saved last wins.
const LAYOUT = (() => {
  const key = 'dbt-erd-layout:' + PAGE.title;
  let data = PAGE.layout || {};
  try {
    const local = JSON.parse(localStorage.getItem(key) || 'null');
    if (local && (local.savedAt || '') > (data.savedAt || '')) data = local;
  } catch (e) { /* storage unavailable: embedded layout only */ }
  const save = () => {
    data.savedAt = new Date().toISOString();
    try { localStorage.setItem(key, JSON.stringify(data)); } catch (e) { /* not persisted */ }
  };
  return {
    get: (view, scope) => (data[view] || {})[scope],
    set(view, scope, value) { (data[view] = data[view] || {})[scope] = value; save(); },
    clear(view) { delete data[view]; save(); },
    dump: () => ({ format: LAYOUT_FORMAT, version: 1, ...data }),
    load(d) { data = d; save(); },
  };
})();

// --- saving files ------------------------------------------------------------
// file name: "<title>-<view>.<ext>", title reduced to ASCII letters, digits, '-' and '_'
const fileSlug = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^A-Za-z0-9_-]+/g, '-')
  .replace(/^-+|-+$/g, '') || 'dbtscope';
// hand a file to the browser: Blob URL + temporary <a download>, revoked once the click is handled
function saveFile(name, blob) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 0);
}
// exported images of both views: what is on screen, at 2 x the screen resolution
const EXPORT = (() => {
  const MAX_PIXELS = 16777216, MAX_SIDE = 16384;   // smallest canvas limits of current browsers
  const live = document.getElementById('export-live');
  return {
    // device pixels per CSS pixel for a w x h CSS-px image: 2 x devicePixelRatio, lowered to fit the limits
    scale(w, h) {
      const cap = Math.min(MAX_SIDE / Math.max(w, h, 1), Math.sqrt(MAX_PIXELS / Math.max(w * h, 1))) * 0.999;
      return Math.min(2 * (window.devicePixelRatio || 1), cap);
    },
    // canvas -> Promise<Blob> (PNG); rejects if the browser returns null
    png: canvas => new Promise((resolve, reject) =>
      canvas.toBlob(b => (b ? resolve(b) : reject(new Error('toBlob returned null'))), 'image/png')),
    // run make() -> Promise<Blob>, save it as "<title>-<view>.<ext>" and announce it; on failure alert.
    // The button gets aria-disabled while it works (native disabled would drop the keyboard focus).
    async save(view, ext, make, button) {
      if (button.getAttribute('aria-disabled') === 'true') return;
      button.setAttribute('aria-disabled', 'true');
      const name = `${fileSlug(PAGE.title)}-${view}.${ext}`;
      try {
        const blob = await make();
        if (!blob) throw new Error('nothing drawn');
        saveFile(name, blob);
        live.textContent = '';   // emptied first, so the same message twice is announced twice
        requestAnimationFrame(() => { live.textContent = L.imageSaved(name); });
      } catch (e) {
        alert(L.imageError);
      } finally {
        button.removeAttribute('aria-disabled');
      }
    },
  };
})();

// The viewer's memory: a choice kept in the localStorage key `<prefix>:<title>`, apart from the layout and never exported
// (D-048, D-062). `words` are the values a key may hold, anything else reads as no choice; a value is stored only when it
// differs from the default, and without storage the choice lasts for the session. One store per choice.
const memoryOf = prefix => {
  const key = prefix + ':' + PAGE.title;
  return {
    get(words) { try { const v = localStorage.getItem(key); return words.includes(v) ? v : null; } catch (e) { return null; } },
    set(word, fallback) {
      try { if (word === fallback) localStorage.removeItem(key); else localStorage.setItem(key, word); } catch (e) { /* session only */ }
    },
  };
};
// the grouping of the universe (D-048), passed to the universe
const GROUPING = memoryOf('dbtscope-constellations');
// the summary cards switch (D-074): key `dbtscope-cards:<title>`, values `shown` / `hidden`, passed to the universe
const CARDS = memoryOf('dbtscope-cards');

// The viewer's fold choice, shared by both views (D-069): the key `dbtscope-fold:<title>`, values `folded` / `shown`.
const FOLD = (() => {
  const memory = memoryOf('dbtscope-fold'), words = ['folded', 'shown'], listeners = [];
  const word = on => (on ? 'folded' : 'shown'), fallback = PAGE.universe.defaults.fold;
  return {
    on: () => { const v = memory.get(words); return v === null ? fallback : v === 'folded'; },
    // `from` is the listener of the view that made the change: it already follows
    set(on, from) {
      memory.set(word(on), word(fallback));
      listeners.forEach(fn => { if (fn !== from) fn(on); });
    },
    listen: fn => listeners.push(fn),
  };
})();

const views = {};
let current = null;
let flow = null;   // the flow view (D-036), started on first use; an overlay of the Universe tab, not a view of `views`
function showTab(name) {
  current = name;
  document.querySelectorAll('#tabs button[data-tab]').forEach(b => b.classList.toggle('on', b.dataset.tab === name));
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.id === 'tab-' + name));
  if (!views[name]) views[name] = name === 'detail' ? startDetail(PAGE.detail, LAYOUT, EXPORT, FOLD)
    : startUniverse(PAGE.universe, openInDetail, new Set(PAGE.detail.entities.map(e => e.id)), LAYOUT, EXPORT, openFlow, FOLD, GROUPING, CARDS);
  else if (views[name].shown) views[name].shown();
}
function openInDetail(id) {
  showTab('detail');
  views.detail.focus(id);
}
// the universe under the flow overlay: unreachable (no focus, no click, skipped by screen readers) while it is open
function coverUniverse(on) {
  [document.getElementById('u-panel'), document.querySelector('#tab-universe > .stage')].forEach(el => { el.inert = on; });
}
// open the flow of a trajectory (from the universe's Flow button); the universe state is left untouched
function openFlow(id, direction, depth) {
  if (!flow) flow = startFlow(PAGE.universe, EXPORT, closeFlow);
  coverUniverse(true);
  flow.open(id, direction, depth);
  document.getElementById('f-back').focus();
}
// back to the universe exactly as it was (Back, Esc)
function closeFlow() {
  flow.close();
  coverUniverse(false);
  document.getElementById('u-tj-flow').focus();
}
document.querySelectorAll('#tabs button[data-tab]').forEach(b => { b.textContent = L[b.dataset.tab]; b.onclick = () => showTab(b.dataset.tab); });

const $l = id => document.getElementById('l-' + id);
$l('reset').textContent = L.reset; $l('export').textContent = L.export; $l('import').textContent = L.import;
$l('reset').onclick = () => { if (confirm(L.resetAsk)) { LAYOUT.clear(current); views[current].relayout(); } };
$l('export').onclick = () =>
  saveFile('dbt-erd-layout.json', new Blob([JSON.stringify(LAYOUT.dump(), null, 1)], { type: 'application/json' }));
$l('import').onclick = () => $l('file').click();
$l('file').onchange = async ev => {
  const file = ev.target.files[0]; ev.target.value = '';
  if (!file) return;
  try {
    const d = JSON.parse(await file.text());
    if (d.format !== LAYOUT_FORMAT) throw new Error();
    LAYOUT.load(d);
    Object.values(views).forEach(v => v.relayout());
  } catch (e) { alert(L.bad); }
};
showTab(PAGE.view);
