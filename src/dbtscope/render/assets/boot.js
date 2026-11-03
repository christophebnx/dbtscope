// Page boot: shared layout store, tabs, the export / import / reset of manual arrangements, and the
// shared helpers that save files and exported images.
const PAGE = JSON.parse(document.getElementById('data').textContent);
document.documentElement.lang = PAGE.lang;
const L = {
  en: { universe: 'Universe', detail: 'Detail', reset: 'Reset layout', export: 'Export layout', import: 'Import layout',
        resetAsk: 'Forget the manual arrangement of this tab?', bad: 'Not a dbt-erd layout file.',
        imageSaved: f => `Image created: ${f}`, imageError: 'The image could not be created.' },
  fr: { universe: 'Univers', detail: 'Détail', reset: 'Réinitialiser la disposition', export: 'Exporter la disposition',
        import: 'Importer une disposition',
        resetAsk: 'Oublier la disposition manuelle de cet onglet ?', bad: 'Ce fichier n\'est pas une disposition dbt-erd.',
        imageSaved: f => `Image créée : ${f}`, imageError: 'L\'image n\'a pas pu être créée.' },
}[PAGE.lang];

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
    dump: () => ({ format: 'dbt-erd-layout', version: 1, ...data }),
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

const views = {};
let current = null;
function showTab(name) {
  current = name;
  document.querySelectorAll('#tabs button[data-tab]').forEach(b => b.classList.toggle('on', b.dataset.tab === name));
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.id === 'tab-' + name));
  if (!views[name]) views[name] = name === 'detail' ? startDetail(PAGE.detail, LAYOUT, EXPORT)
    : startUniverse(PAGE.universe, PAGE.lang, openInDetail, new Set(PAGE.detail.entities.map(e => e.id)), LAYOUT, EXPORT);
  else if (views[name].shown) views[name].shown();
}
function openInDetail(id) {
  showTab('detail');
  views.detail.focus(id);
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
    if (d.format !== 'dbt-erd-layout') throw new Error();
    LAYOUT.load(d);
    Object.values(views).forEach(v => v.relayout());
  } catch (e) { alert(L.bad); }
};
showTab(PAGE.view);
