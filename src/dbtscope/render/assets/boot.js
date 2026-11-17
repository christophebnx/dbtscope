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

const views = {};
const DETAIL_INDEX = detailIndex(PAGE.detail);   // what the detail knows of a table, for the universe's table panel (M9.3)
const DOMAINS = detailDomains(PAGE.detail, PAGE.universe);   // the detail's groups as universe domains, or null (D-084)
let current = null;
let flow = null;   // the flow view (D-036), started on first use; an overlay of the Universe tab, not a view of `views`
function showTab(name) {
  current = name;
  document.querySelectorAll('#tabs button[data-tab]').forEach(b => b.classList.toggle('on', b.dataset.tab === name));
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.id === 'tab-' + name));
  // the Layout menu's reset acts on the arrangement of a tab; the Schema sheet is computed, so it has none (D-085, D-092)
  $l('reset').disabled = name === 'schema';
  $l('reset-why').hidden = name !== 'schema';
  if (!views[name]) views[name] = name === 'detail' ? startDetail(PAGE.detail, LAYOUT, EXPORT, DOMAINS)
    : name === 'schema' ? startSchema(PAGE.universe, DETAIL_INDEX, EXPORT, universeAccess)
    : startUniverse(PAGE.universe, openInDetail, DETAIL_INDEX, LAYOUT, EXPORT, openFlow);
  else if (views[name].shown) views[name].shown();
}
// what the Schema tab reads of the universe view, which may not be started yet (D-092)
const universeAccess = { location: () => (views.universe ? views.universe.location() : null),
  passingIds: () => (views.universe ? views.universe.passingIds() : null) };
// the universe location as the detail's trail (D-086, D-089): `← All domains › Vehicle › car_hub`, every segment a button back to the
// Universe tab at that level; a function of the detail's focus, so the last segment follows it when it is a universe table
const inUniverse = id => PAGE.universe.nodes.some(n => n.id === id);
function trailOf(inside, handOff) {
  return focus => {
    const id = focus && inUniverse(focus) ? focus : handOff;
    const name = id && PAGE.universe.nodes.find(n => n.id === id).name;
    return views.universe.trail(inside, id).map((item, j) => ({ label: item.label, title: item.step === 2 ? L.backToUniverse(name) : item.title, back: j === 0,
      go: () => item.step === 2 ? backToUniverse(handOff) : leaveDetail(item.step, inside) }));
  };
}
function leaveDetail(step, inside) {
  if (flow && flow.isOpen()) closeFlow();
  showTab('universe');
  views.universe.go(step, inside);
}
// the universe location each tab last showed: the Detail and Schema tabs follow it when it changes (D-089, D-092)
const followed = { detail: null, schema: null };
// the Schema tab also follows a selected table; the Detail tab only the entered constellation
const locationKey = (loc, withTable) => loc.by + '|' + (loc.inside ?? '') + (withTable ? '|' + (loc.table ?? '') : '');
// double-click on a universe table: the Detail tab on it, with the way back in its toolbar (D-086)
function openInDetail(id) {
  const loc = views.universe.location();
  showTab('detail');
  followed.detail = locationKey(loc);
  views.detail.focus(id, trailOf(loc.inside, id));
}
// a tab shown by its button follows the universe location when it changed since it last did; the viewer's own choice (the
// Detail's group, the Schema's scope) stands until the location changes again. Detail: its trail and (in domain mode, without a
// focused table) its group; Schema: the entered domain or layer as its scope, a selected table framed
function follow(name) {
  if (!views.universe || !views[name]) return;
  const loc = views.universe.location(), key = locationKey(loc, name === 'schema');
  if (key === followed[name]) return;
  followed[name] = key;
  if (name === 'schema') return views.schema.follow(loc);
  const group = loc.by === 'domains' && loc.inside && DOMAINS && DOMAINS.has(loc.inside) ? loc.inside : null;
  views.detail.follow(group, loc.inside ? trailOf(loc.inside, null) : null);
}
// the way back: the Universe tab, on the detail's current focus when it is a universe table (the viewer may have moved
// on), else on the table of the hand-off
function backToUniverse(handOff) {
  const focus = views.detail.focused();
  if (flow && flow.isOpen()) closeFlow();   // the lineage graph covers the universe: close it so the table shows
  showTab('universe');
  views.universe.locate(focus && inUniverse(focus) ? focus : handOff);
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
document.querySelectorAll('#tabs button[data-tab]').forEach(b => { b.textContent = L[b.dataset.tab]; b.onclick = () => { showTab(b.dataset.tab); if (b.dataset.tab !== 'universe') follow(b.dataset.tab); }; });
document.querySelector('#tabs button[data-tab=universe]').title = L.tabUniverse;
document.querySelector('#tabs button[data-tab=detail]').title = DOMAINS ? L.tabDetail : L.tabDetailGroups;
document.querySelector('#tabs button[data-tab=schema]').title = L.tabSchema;

const $l = id => document.getElementById('l-' + id);
$l('menu-t').textContent = L.layout;
$l('reset').textContent = L.reset; $l('export').textContent = L.export; $l('import').textContent = L.import;
dismissable($l('menu'));
// an action closes the menu and gives the focus back to its summary
const inMenu = action => () => { $l('menu').open = false; $l('menu').querySelector('summary').focus(); action(); };
$l('reset-why').textContent = L.schemaNoReset;
$l('reset').onclick = inMenu(() => { if (confirm(L.resetAsk)) { LAYOUT.clear(current); views[current].relayout(); } });
$l('export').onclick = inMenu(() =>
  saveFile('dbt-erd-layout.json', new Blob([JSON.stringify(LAYOUT.dump(), null, 1)], { type: 'application/json' })));
$l('import').onclick = inMenu(() => $l('file').click());
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
