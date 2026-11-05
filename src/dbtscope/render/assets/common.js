// Page-wide globals, inlined first so every later script can use them: the payload, the shared string
// table, the one HTML escaper, numbers and plural agreement, the theme colours and the contrast of text
// on colours, the side-panel toggle, the filter checkbox row, the lineage traversal of the trajectory,
// and the Graphviz helpers of the detail and flow views (render, pan-zoom mount, image export).
// Declarations only: no DOM work at load but the page language.
const PAGE = JSON.parse(document.getElementById('data').textContent);
document.documentElement.lang = PAGE.lang;

// Strings used by boot.js, or shown with the same text by both views. A view's own strings live in its T.
// A count's noun is a [singular, plural] pair, read through plural(). French writes a no-break space
// (\u00a0) before ':' and a narrow one (\u202f) before '?', '!' and ';', always as escapes (D-039);
// a label and a value are joined with colon.
const STRINGS = {
  en: { universe: 'Universe', detail: 'Detail', reset: 'Reset layout', export: 'Export layout', import: 'Import layout',
        resetAsk: 'Forget the manual arrangement of this tab?', bad: 'Not a dbt-erd layout file.',
        colon: ': ', imageSaved: f => `Image created: ${f}`, imageError: 'The image could not be created.',
        exportImage: 'Export image', png: 'PNG', filters: 'Filters', empty: 'No table for these filters.',
        kinds: 'Types', tables: ['table', 'tables'], columns: ['column', 'columns'],
        svg: 'SVG', fit: 'Fit', computing: 'Laying out…', error: 'Render error: ', domainsN: ['domain', 'domains'],
        direction: 'Direction', depth: 'Depth', up: 'upstream', down: 'downstream', both: 'both',
        d1: '1 level', d2: '2 levels', d3: '3 levels', dall: 'all levels',
        countUp: n => `${n} upstream`, countDown: n => `${n} downstream`,
        noLineage: 'No upstream or downstream table', noUp: 'No upstream table', noDown: 'No downstream table',
        lgStart: 'start', tipStart: 'Start of the trajectory',
        tipUp: d => `Upstream, level ${d}`, tipDown: d => `Downstream, level ${d}` },
  fr: { universe: 'Univers', detail: 'Détail', reset: 'Réinitialiser la disposition', export: 'Exporter la disposition',
        import: 'Importer une disposition',
        resetAsk: 'Oublier la disposition manuelle de cet onglet\u202f?', bad: 'Ce fichier n\'est pas une disposition dbt-erd.',
        colon: '\u00a0: ', imageSaved: f => `Image créée\u00a0: ${f}`, imageError: 'L\'image n\'a pas pu être créée.',
        exportImage: 'Exporter l\'image', png: 'PNG', filters: 'Filtres', empty: 'Aucune table pour ces filtres.',
        kinds: 'Types', tables: ['table', 'tables'], columns: ['colonne', 'colonnes'],
        svg: 'SVG', fit: 'Recadrer', computing: 'Calcul du schéma…', error: 'Erreur de rendu\u00a0: ',
        domainsN: ['domaine', 'domaines'],
        direction: 'Sens', depth: 'Profondeur', up: 'amont', down: 'aval', both: 'les deux',
        d1: '1 niveau', d2: '2 niveaux', d3: '3 niveaux', dall: 'tous les niveaux',
        countUp: n => `${n} en amont`, countDown: n => `${n} en aval`,
        noLineage: 'Aucune table en amont ni en aval', noUp: 'Aucune table en amont', noDown: 'Aucune table en aval',
        lgStart: 'départ', tipStart: 'Départ de la trajectoire',
        tipUp: d => `En amont, niveau ${d}`, tipDown: d => `En aval, niveau ${d}` },
};
const L = STRINGS[PAGE.lang];

// The one HTML escaper: safe in text and in single- or double-quoted attributes (and in Graphviz HTML-like labels).
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

// A number as the page language writes it: "1,234" in English, "1\u202f234" in French (D-039).
const num = n => n.toLocaleString(PAGE.lang);
// "1 table", "2 tables"; forms is [singular, plural]. English: singular for 1; French: for 0 and 1.
const plural = (n, forms) => `${num(n)} ${forms[n === 1 || (n === 0 && PAGE.lang === 'fr') ? 0 : 1]}`;

// The theme colours the scripts draw with: a copy of --bg, --fg and --muted of page.css :root.
const THEME = { bg: '#f5f6f8', fg: '#1f2933', muted: '#5f6774' };

// Text on colours (D-037), pure and cached by arguments (the universe asks for every card in every frame).
// Colours are '#rgb', '#rrggbb' or '#rrggbbaa' (alpha ignored: the colour counts as opaque).
// ratio(a, b): the WCAG 2.x contrast ratio, NaN for anything else. textOn(bg): the text colour on a fill,
// white when it reaches AA, else black (white for an unparsable fill). ink(color, bg): `color` used as text
// on a light `bg`, itself when it reaches AA, else mixed toward black by the smallest step j / 32 that does.
const CONTRAST = (() => {
  const AA = 4.5, cache = new Map();
  function channels(c) {
    const m = /^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.exec(String(c).trim());
    if (!m) return null;
    const h = m[1].length === 3 ? m[1].replace(/./g, x => x + x) : m[1];
    return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16) / 255);
  }
  const linear = v => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
  const luminance = ([r, g, b]) => 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b);
  const hex = rgb => '#' + rgb.map(v => Math.round(v * 255).toString(16).padStart(2, '0')).join('');
  const memo = (key, compute) => { if (!cache.has(key)) cache.set(key, compute()); return cache.get(key); };
  function ratio(a, b) {
    const x = channels(a), y = channels(b);
    if (!x || !y) return NaN;
    const [hi, lo] = [luminance(x), luminance(y)].sort((p, q) => q - p);
    return (hi + 0.05) / (lo + 0.05);
  }
  const textOn = bg => memo('on|' + bg, () => (!channels(bg) || ratio('#ffffff', bg) >= AA ? '#ffffff' : '#000000'));
  function darken(color, bg) {
    const rgb = channels(color);
    if (!rgb || ratio(color, bg) >= AA) return color;
    for (let j = 1; j <= 32; j++) {
      const mixed = hex(rgb.map(v => v * (1 - j / 32)));
      if (ratio(mixed, bg) >= AA) return mixed;
    }
    return '#000000';
  }
  return { AA, ratio, textOn, ink: (color, bg) => memo('ink|' + color + '|' + bg, () => darken(color, bg)) };
})();

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
  name.textContent = label; n.textContent = num(count);
  row.append(name, n);
  if (title) row.title = title;
  return row;
}

// The options of a select from [value, label] pairs, built with DOM calls; `current` is selected.
function fillSelect(el, pairs, current) {
  el.replaceChildren(...pairs.map(([value, label]) => {
    const o = document.createElement('option');
    o.value = value; o.textContent = label; o.defaultSelected = value === current;
    return o;
  }));
}

// The name and meta lines of a table's tooltip (universe payload), escaped:
// "<name>" then "domain · layer · kind · N columns". Each view appends its own lines.
function tableTip(DATA, n) {
  const label = (list, key) => list.find(x => x.key === key).label;
  return `<b>${esc(n.name)}</b><div class="m">${esc(label(DATA.domains, n.domain))} · ${esc(label(DATA.layers, n.layer))} · `
    + `${esc(label(DATA.kinds, n.kind))} · ${plural(n.cols.length, L.columns)}</div>`;
}
// The description line of a table's tooltip (universe payload), escaped; '' without a description.
const tableDesc = n => (n.desc ? `<div class="desc">${esc(n.desc)}</div>` : '');

// ---------------------------------------------------------------- trajectory (lineage from one table)
// Colours of the trajectory: upstream (dashed marks), downstream (solid marks); the universe and the flow.
const TRAJ_COLORS = { up: '#6d28d9', down: '#c2410c' };

// Trajectory of one table along the lineage: a pure page global, tested directly.
// lineage: [[child, parent], ...]; data flows from parent to child.
// direction: 'up' | 'down' | 'both'; depth: 1 | 2 | 3 | Infinity.
// -> { up: Map(index -> distance), down: Map(index -> distance) }; start is in neither map.
// Breadth-first, so the distance is the shortest path; the seen set stops on a cycle of a malformed manifest.
function trajectory(lineage, start, direction, depth) {
  const parents = new Map(), children = new Map();
  const push = (m, k, v) => { const l = m.get(k); if (l) l.push(v); else m.set(k, [v]); };
  lineage.forEach(([child, parent]) => { push(parents, child, parent); push(children, parent, child); });
  const walk = adj => {
    const dist = new Map(), seen = new Set([start]);
    let frontier = [start];
    for (let d = 1; d <= depth && frontier.length; d++) {
      const next = [];
      frontier.forEach(i => (adj.get(i) || []).forEach(j => {
        if (!seen.has(j)) { seen.add(j); dist.set(j, d); next.push(j); }
      }));
      frontier = next;
    }
    return dist;
  };
  return { up: direction === 'down' ? new Map() : walk(parents), down: direction === 'up' ? new Map() : walk(children) };
}

// The lineage edges drawn for a trajectory: [[child, parent, 'up' | 'down']], those whose two ends are
// the start or tables of the same side.
function trajectoryEdges(lineage, start, up, down) {
  const out = [];
  lineage.forEach(([c, p]) => {
    if (up.has(p) && (c === start || up.has(c))) out.push([c, p, 'up']);
    else if (down.has(c) && (p === start || down.has(p))) out.push([c, p, 'down']);
  });
  return out;
}

// "5 upstream · 1 downstream", restricted to the direction shown (u, d: table counts of each side)
function trajectoryCounts(direction, u, d) {
  return direction === 'up' ? L.countUp(num(u)) : direction === 'down' ? L.countDown(num(d))
    : `${L.countUp(num(u))} · ${L.countDown(num(d))}`;
}
// The text shown instead of the counts when a trajectory has no table in its direction
const noTrajectory = direction => ({ both: L.noLineage, up: L.noUp, down: L.noDown })[direction];

// A table's place in a trajectory: [['start', text]], or its upstream and / or downstream levels
// (a table can be both, on a cycle) as [['up' | 'down', text]]; [] for a table outside it.
function trajectoryLevels({ start, up, down }, i) {
  if (i === start) return [['start', L.tipStart]];
  return [up.has(i) && ['up', L.tipUp(num(up.get(i)))], down.has(i) && ['down', L.tipDown(num(down.get(i)))]].filter(Boolean);
}
// The trajectory lines of a table's tooltip
const trajectoryTip = (t, i) => trajectoryLevels(t, i).map(([side, text]) => `<div class="tj ${side}">${text}</div>`).join('');

// How many of the listed tables (indices into nodes) each domain holds: Map(domain key -> count)
function countByDomain(nodes, indices) {
  const per = new Map();
  for (const i of indices) per.set(nodes[i].domain, (per.get(nodes[i].domain) || 0) + 1);
  return per;
}

// ---------------------------------------------------------------- Graphviz views (detail, flow)
// The one DOT-string escaper: ids and quoted strings of a DOT text.
const dotStr = s => String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\r?\n/g, '\\n');
// The one escaper of text inside a Graphviz HTML-like label: HTML-escaped, then every backslash doubled,
// since Graphviz reads \\, \N, \G… in label text as escapes (checked with the vendored Viz.js).
const dotText = s => esc(s).replace(/\\/g, '\\\\');

// One Viz.js instance for the page, created on first use and recreated after a failed render
// (a failed Viz instance stays broken). render(dot, options) -> Promise<SVGElement>.
const GRAPHVIZ = (() => {
  let viz = null;
  return {
    render(dot, options) {
      if (!viz) viz = new Viz();
      const used = viz;
      return used.renderSVGElement(dot, options).catch(err => { if (viz === used) viz = null; throw err; });
    },
  };
})();

// Puts a Graphviz svg in `box` at 100 % of its size and mounts svg-pan-zoom on it, fitted and centred.
// svg-pan-zoom fits to the drawing's bbox once and stays stuck at zoom 0 if that bbox is still empty
// (page laid out in the background), so it waits until the svg has a real size. -> Promise<pz>, or
// null as soon as isCurrent() turns false (a newer render replaced this one).
function panZoom(box, svg, isCurrent) {
  box.replaceChildren(svg);
  if (!svg.getAttribute('viewBox')) svg.setAttribute('viewBox', '0 0 ' + parseFloat(svg.getAttribute('width')) + ' ' + parseFloat(svg.getAttribute('height')));
  svg.setAttribute('width', '100%'); svg.setAttribute('height', '100%');
  return new Promise(resolve => {
    const init = () => {
      if (!isCurrent()) return resolve(null);
      const bb = svg.getBBox();
      if (!(bb.width && bb.height && svg.clientWidth && svg.clientHeight)) return requestAnimationFrame(init);
      resolve(svgPanZoom(svg, { zoomScaleSensitivity: 0.3, maxZoom: 40, fit: true, center: true, dblClickZoomEnabled: false }));
    };
    init();
  });
}
// Fits and centres a mounted diagram again (Fit, a panel toggle); a hidden tab (no size) waits until shown.
function panZoomFit(box, pz) { if (pz && box.clientWidth) { pz.resize(); pz.fit(); pz.center(); } }
// Unmounts svg-pan-zoom before its svg is replaced; -> null, the new pz
function panZoomDestroy(pz) {
  // destroy() resets the zoom first, which throws if the old svg has no usable size
  if (pz) { try { pz.destroy(); } catch (e) { /* the svg is replaced anyway */ } }
  return null;
}

// CSS of page.css that changes how a Graphviz diagram looks, inlined into the exported SVG when it differs
// from its default (everything else is Graphviz presentation attributes). A new such #d-graph or #f-graph
// rule adds its property here.
const INLINE = { opacity: '1' };

// The visible part of the Graphviz diagram of `box` (driven by svg-pan-zoom `pz`) as a standalone SVG
// document, `scale` x its size on screen (the drawing stays vector); null when nothing is drawn. Only what
// is shown: tables and links outside the visible area, tooltips and svg-pan-zoom's own markup are left
// out; ids (dbt unique_ids) are kept.
function svgImage(box, pz, scale) {
  const svg = pz && box.querySelector('svg');
  if (!svg) return null;
  const XLINK = 'http://www.w3.org/1999/xlink', XMLNS = 'http://www.w3.org/2000/xmlns/';
  const overlaps = (a, b) => a.right > b.left && a.left < b.right && a.bottom > b.top && a.top < b.bottom;
  const vp = svg.querySelector('g.svg-pan-zoom_viewport'), r = svg.getBoundingClientRect();
  const m = vp.getScreenCTM().inverse();
  function corner(x, y) { const p = svg.createSVGPoint(); p.x = x; p.y = y; return p.matrixTransform(m); }
  const a = corner(r.left, r.top), b = corner(r.right, r.bottom);
  const clone = svg.cloneNode(true);
  const originals = [svg, ...svg.querySelectorAll('*')], copies = [clone, ...clone.querySelectorAll('*')];
  const cvp = copies[originals.indexOf(vp)], cut = [];
  originals.forEach((el, i) => {
    const copy = copies[i], style = getComputedStyle(el);
    copy.style.removeProperty('cursor');
    Object.entries(INLINE).forEach(([prop, plain]) => { if (style[prop] !== plain) copy.style[prop] = style[prop]; });
    if (el.matches('g.node, g.edge') && !overlaps(el.getBoundingClientRect(), r)) cut.push(copy);
  });
  cut.forEach(el => el.remove());
  clone.querySelectorAll('title, #svg-pan-zoom-controls').forEach(el => el.remove());
  [clone, ...clone.querySelectorAll('*')].forEach(el => {
    el.removeAttribute('title'); el.removeAttributeNS(XLINK, 'title');
    if (el.classList.length) {
      [...el.classList].filter(c => c.startsWith('svg-pan-zoom')).forEach(c => el.classList.remove(c));
      if (!el.classList.length) el.removeAttribute('class');
    }
    if (!el.getAttribute('style')) el.removeAttribute('style');
  });
  cvp.removeAttribute('transform'); cvp.style.removeProperty('transform');
  if (!cvp.getAttribute('style')) cvp.removeAttribute('style');
  const w = b.x - a.x, h = b.y - a.y;
  clone.setAttribute('viewBox', `${a.x} ${a.y} ${w} ${h}`);
  clone.setAttribute('width', r.width * scale); clone.setAttribute('height', r.height * scale);
  clone.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  clone.setAttributeNS(XMLNS, 'xmlns', 'http://www.w3.org/2000/svg');
  clone.setAttributeNS(XMLNS, 'xmlns:xlink', XLINK);
  const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  const fill = getComputedStyle(document.body).backgroundColor;
  Object.entries({ x: a.x, y: a.y, width: w, height: h, fill }).forEach(([k, v]) => bg.setAttribute(k, v));
  clone.insertBefore(bg, clone.firstChild);
  return '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(clone);
}

// svgImage at its screen size as a file (Blob), or null when nothing is drawn.
async function svgFile(box, pz) {
  const text = svgImage(box, pz, 1);
  return text && new Blob([text], { type: 'image/svg+xml' });
}

// The same SVG rasterised at 2 x the screen resolution (EXPORT.scale; a data: URL keeps the canvas untainted).
async function pngImage(box, pz, EXPORT) {
  const svg = pz && box.querySelector('svg');
  if (!svg) return null;
  const r = svg.getBoundingClientRect(), s = EXPORT.scale(r.width, r.height);
  const img = new Image();
  img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgImage(box, pz, s));
  await img.decode();
  const c = document.createElement('canvas');
  c.width = Math.round(r.width * s); c.height = Math.round(r.height * s);
  const g = c.getContext('2d');
  g.fillStyle = getComputedStyle(document.body).backgroundColor; g.fillRect(0, 0, c.width, c.height);
  g.drawImage(img, 0, 0, c.width, c.height);
  return EXPORT.png(c);
}
