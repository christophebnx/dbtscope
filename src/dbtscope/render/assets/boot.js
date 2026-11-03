// Page boot: shared layout store, tabs, and the export / import / reset of manual arrangements.
const PAGE = JSON.parse(document.getElementById('data').textContent);
document.documentElement.lang = PAGE.lang;
const L = {
  en: { universe: 'Universe', detail: 'Detail', reset: 'Reset layout', export: 'Export layout', import: 'Import layout',
        resetAsk: 'Forget the manual arrangement of this tab?', bad: 'Not a dbt-erd layout file.' },
  fr: { universe: 'Univers', detail: 'Détail', reset: 'Réinitialiser', export: 'Exporter la disposition', import: 'Importer',
        resetAsk: 'Oublier la disposition manuelle de cet onglet ?', bad: 'Ce fichier n\'est pas une disposition dbt-erd.' },
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

const views = {};
let current = null;
function showTab(name) {
  current = name;
  document.querySelectorAll('#tabs button[data-tab]').forEach(b => b.classList.toggle('on', b.dataset.tab === name));
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.id === 'tab-' + name));
  if (!views[name]) views[name] = name === 'detail' ? startDetail(PAGE.detail, LAYOUT)
    : startUniverse(PAGE.universe, PAGE.lang, openInDetail, new Set(PAGE.detail.entities.map(e => e.id)), LAYOUT);
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
$l('export').onclick = () => {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(LAYOUT.dump(), null, 1)], { type: 'application/json' }));
  a.download = 'dbt-erd-layout.json';
  a.click();
  URL.revokeObjectURL(a.href);
};
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
