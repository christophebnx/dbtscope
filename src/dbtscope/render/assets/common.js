// Page-wide globals, inlined first so every later script can use them: the payload, the shared string
// table, the one HTML escaper, plural agreement, the side-panel toggle and the filter checkbox row.
// Declarations only: no DOM work at load but the page language.
const PAGE = JSON.parse(document.getElementById('data').textContent);
document.documentElement.lang = PAGE.lang;

// Strings used by boot.js, or shown with the same text by both views. A view's own strings live in its T.
// A count's noun is a [singular, plural] pair, read through plural().
const STRINGS = {
  en: { universe: 'Universe', detail: 'Detail', reset: 'Reset layout', export: 'Export layout', import: 'Import layout',
        resetAsk: 'Forget the manual arrangement of this tab?', bad: 'Not a dbt-erd layout file.',
        imageSaved: f => `Image created: ${f}`, imageError: 'The image could not be created.',
        exportImage: 'Export image', png: 'PNG', filters: 'Filters', empty: 'No table for these filters.',
        kinds: 'Types', tables: ['table', 'tables'], columns: ['column', 'columns'] },
  fr: { universe: 'Univers', detail: 'Détail', reset: 'Réinitialiser la disposition', export: 'Exporter la disposition',
        import: 'Importer une disposition',
        resetAsk: 'Oublier la disposition manuelle de cet onglet ?', bad: 'Ce fichier n\'est pas une disposition dbt-erd.',
        imageSaved: f => `Image créée : ${f}`, imageError: 'L\'image n\'a pas pu être créée.',
        exportImage: 'Exporter l\'image', png: 'PNG', filters: 'Filtres', empty: 'Aucune table pour ces filtres.',
        kinds: 'Types', tables: ['table', 'tables'], columns: ['colonne', 'colonnes'] },
};
const L = STRINGS[PAGE.lang];

// The one HTML escaper: safe in text and in single- or double-quoted attributes (and in Graphviz HTML-like labels).
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

// "1 table", "2 tables"; forms is [singular, plural]. English: singular for 1; French: for 0 and 1.
const plural = (n, forms) => `${n} ${forms[n === 1 || (n === 0 && PAGE.lang === 'fr') ? 0 : 1]}`;

// Wires the ☰ button #<view>-toggle to the panel #<view>-panel. A view started in a window 600 px wide
// or narrower (the page.css breakpoint) starts with its panel closed (D-035); after that only the button
// decides. onToggle runs after each click (resize and refit the drawing).
function sidePanel(view, onToggle) {
  const button = document.getElementById(view + '-toggle'), panel = document.getElementById(view + '-panel');
  const sync = () => button.setAttribute('aria-expanded', String(!panel.classList.contains('closed')));
  button.title = L.filters; button.setAttribute('aria-label', L.filters);
  if (matchMedia('(max-width: 600px)').matches) panel.classList.add('closed');
  sync();
  button.onclick = () => { panel.classList.toggle('closed'); sync(); onToggle(); };
}

// One checkbox row of a filter panel, built with DOM calls (the label is untrusted text):
// checkbox, colour dot (when there is a colour), label, count. onChange(checked) runs on each change.
function filterRow({ label, color, count, checked, title }, onChange) {
  const row = document.createElement('label'), box = document.createElement('input');
  box.type = 'checkbox'; box.checked = checked;
  box.onchange = () => onChange(box.checked);
  row.append(box);
  if (color) { const dot = document.createElement('i'); dot.style.background = color; row.append(dot); }
  const name = document.createElement('span'), n = document.createElement('small');
  name.textContent = label; n.textContent = count;
  row.append(name, n);
  if (title) row.title = title;
  return row;
}
