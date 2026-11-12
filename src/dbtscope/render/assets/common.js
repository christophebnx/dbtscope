// Page-wide globals, inlined first so every later script can use them: the payload, the shared string
// table, the one HTML escaper, numbers and plural agreement, the theme colours and the contrast of text
// on colours, the side-panel toggle, the filter checkbox row, the lineage traversal of the trajectory,
// the columns along the data flow (flow view, universe layer bands), and the Graphviz helpers of the
// detail and flow views (render, zoom mount, image export).
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
        foldedN: ['folded table', 'folded tables'], foldH: 'Entities', foldRow: 'Fold',
        foldTitle: 'Draw these tables inside the table they describe',
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
        foldedN: ['table repliée', 'tables repliées'], foldH: 'Entités', foldRow: 'Replier',
        foldTitle: 'Dessiner ces tables à l\'intérieur de la table qu\'elles décrivent',
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
// edge(color, bg): the same darkening to MARK (3:1, WCAG 1.4.11), for a colour drawn as a mark (D-042).
const CONTRAST = (() => {
  const AA = 4.5, MARK = 3, cache = new Map();
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
  function darken(color, bg, min) {
    const rgb = channels(color);
    if (!rgb || ratio(color, bg) >= min) return color;
    for (let j = 1; j <= 32; j++) {
      const mixed = hex(rgb.map(v => v * (1 - j / 32)));
      if (ratio(mixed, bg) >= min) return mixed;
    }
    return '#000000';
  }
  return { AA, MARK, ratio, textOn,
    ink: (color, bg) => memo('ink|' + color + '|' + bg, () => darken(color, bg, AA)),
    edge: (color, bg) => memo('edge|' + color + '|' + bg, () => darken(color, bg, MARK)) };
})();

// The one colour dot of the page (legends, filters, title dots): filled with `color`, outlined in its
// CONTRAST.edge when the colour alone does not reach 3:1 on the page (D-042), else with no outline.
// Returns `el` (a dot reused from table to table is cleared of a previous outline).
function paintDot(el, color) {
  const edge = CONTRAST.edge(color, THEME.bg);
  el.style.background = color;
  el.style.boxShadow = edge === color ? '' : 'inset 0 0 0 1px ' + edge;
  return el;
}
// The attributes outlining a Graphviz cell filled with `color`: '' when the colour reaches 3:1 on the page,
// else a 1 px border in its CONTRAST.edge (D-042).
function dotEdge(color) {
  const edge = CONTRAST.edge(color, THEME.bg);
  return edge === color ? '' : ` border="1" color="${esc(edge)}"`;
}

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
  if (color) row.append(paintDot(document.createElement('i'), color));
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

// The name shown for a domain, layer or kind of the payload: its label, or its key when the config set
// `label: null`. The one display-name rule of the panels, tooltips and canvas.
const labelOf = item => item.label ?? item.key;

// Folded tables a tooltip lists before "+ N": the one limit of the universe's entity tooltip and the detail's.
const TIP_FOLDED = 12;

// The label of the fold row (D-063, D-073), shown by both views: "Fold Satellite · PIT", the descriptive kinds
// that fold, the first three, then " + N".
function foldLabel(kinds) {
  const names = kinds.map(labelOf), more = names.length > 3 ? ` + ${num(names.length - 3)}` : '';
  return `${L.foldRow} ${names.slice(0, 3).join(' · ')}${more}`;
}

// A viewer choice, kept apart from the shared layout and never exported (D-048, D-063, D-073): stored only when
// it differs from the page default; without storage the choice lasts for the session.
const viewerMemory = (name, values) => {
  const key = name + ':' + PAGE.title;
  return {
    get() { try { const v = localStorage.getItem(key); return values.includes(v) ? v : null; } catch (e) { return null; } },
    set(value, fallback) {
      try { if (value === fallback) localStorage.removeItem(key); else localStorage.setItem(key, value); } catch (e) { /* session only */ }
    },
  };
};

// The name and meta lines of a table's tooltip (universe payload), escaped:
// "<name>" then "domain · layer · kind · N columns". Each view appends its own lines.
function tableTip(DATA, n) {
  const label = (list, key) => labelOf(list.find(x => x.key === key));
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

// ---------------------------------------------------------------- columns along the data flow
// Columns along the data flow: lineage first, layers as a floor. A pure page global, tested directly;
// the flow's columns and the order of the universe's layer bands (D-036, D-040).
// members: table indices; edges: [[parent, child]] among members (data flows left to right);
// layerOf: index -> position of its layer in DATA.layers, or null for a table without a layer.
// -> { rank: Map(index -> column), back: Set of "parent,child" edges left out of the ranking (cycles) }
// span[L] = 1 + the longest chain of edges inside layer L (0 when L has no table); floor[L] = the sum of
// the spans of the layers before L; rank(n) = max(floor[layer(n)], rank(p) + 1 over its parents p).
// A table without a layer has no floor (0) and counts in no layer's span.
// Every edge not in `back` goes left to right. O(V + E); never loops nor throws on a cycle.
function flowRanks(members, edges, layerOf) {
  const at = new Map(members.map((m, j) => [m, j]));
  const links = edges.filter(([p, c]) => p !== c && at.has(p) && at.has(c));
  const layer = members.map(m => layerOf(m) ?? null);
  // longest-path ranks over `list` (Kahn), each table at least at base(j); a table left over by a cycle is
  // ranked over its ranked parents only, its other in-edges go to `back`
  function longest(list, base) {
    const parents = members.map(() => []), children = members.map(() => []), indeg = members.map(() => 0);
    list.forEach(([p, c]) => { const a = at.get(p), b = at.get(c); parents[b].push(a); children[a].push(b); indeg[b]++; });
    const rank = members.map(() => -1), back = new Set(), queue = [];
    members.forEach((_, j) => { if (!indeg[j]) queue.push(j); });
    function place(j) {
      let r = base(j);
      parents[j].forEach(a => { if (rank[a] >= 0) r = Math.max(r, rank[a] + 1); else back.add(members[a] + ',' + members[j]); });
      rank[j] = r;
      children[j].forEach(b => { if (rank[b] < 0 && --indeg[b] === 0) queue.push(b); });
    }
    let head = 0, next = 0;
    for (;;) {
      while (head < queue.length) { const j = queue[head++]; if (rank[j] < 0) place(j); }
      while (next < members.length && rank[next] >= 0) next++;
      if (next === members.length) break;
      place(next);
    }
    return { rank, back };
  }
  const inLayer = ([p, c]) => layer[at.get(p)] !== null && layer[at.get(p)] === layer[at.get(c)];
  const inner = longest(links.filter(inLayer), () => 0).rank;
  const span = [];
  inner.forEach((r, j) => { if (layer[j] !== null) span[layer[j]] = Math.max(span[layer[j]] || 0, r + 1); });
  const floor = [];
  for (let l = 0, sum = 0; l < span.length; l++) { floor[l] = sum; sum += span[l] || 0; }
  const { rank, back } = longest(links, j => (layer[j] === null ? 0 : floor[layer[j]]));
  return { rank: new Map(members.map((m, j) => [m, rank[j]])), back };
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

// The one scale range of every zoom of the page (universe, detail, flow; D-045).
const ZOOM_EXTENT = [0.01, 12];

// Puts the d3 `zoom` behaviour on the selection `sel` (the element that receives the gestures) and
// returns `sel`; `sel.on('.zoom .gesture', null)` takes it off. Double-click does not zoom (it keeps its
// meaning in the views). Safari on macOS reports a trackpad pinch as its own gesturestart / gesturechange
// / gestureend events (event.scale, clientX / Y), not as ctrl+wheel, and would zoom the whole page: they
// are cancelled and scale the d3 zoom around the pointer, by the ratio of the gesture scale between two
// events, through the zoom behaviour (D-045). A touch pinch (iPad Safari fires gesture events with it)
// is left to d3's touch handling: the gestures only stop the page zoom while fingers are down.
function zoomOn(sel, zoom) {
  let last = 1, touches = 0;
  // in the capture phase: a d3.drag or d3.zoom touch handler on the same element stops the later ones
  sel.on('touchstart.gesture touchmove.gesture touchend.gesture', ev => { touches = ev.touches.length; }, true)
    .on('touchcancel.gesture', () => { touches = 0; }, true);
  sel.call(zoom).on('dblclick.zoom', null);
  sel.on('gesturestart.gesture', ev => { ev.preventDefault(); last = ev.scale || 1; })
    .on('gesturechange.gesture', ev => {
      ev.preventDefault();
      const scale = ev.scale || 1;
      if (!touches) zoom.scaleBy(sel, scale / last, d3.pointer(ev, sel.node()));
      last = scale;
    })
    .on('gestureend.gesture', ev => { ev.preventDefault(); last = 1; });
  return sel;
}

// Puts a Graphviz svg in `box` and zooms it with d3.zoom attached to `box` (an HTML block, a hit target
// over its whole area in every engine), fitted and centred (D-045). The svg's children move into one bare
// <g>, the zoom layer, and the svg fills the box at one CSS pixel per Graphviz point at scale 1. Waits until
// the box and the drawing have a real size (page laid out in the background). onZoom(transform) runs on
// every zoom or pan. -> Promise<zv>, or null as soon as isCurrent() turns false (a newer render replaced
// this one). zv: { layer, fit(), get(), set({x, y, k}), centre(rect, k), destroy() }.
function graphZoom(box, svg, isCurrent, onZoom) {
  const vb = (svg.getAttribute('viewBox') || '').split(/[\s,]+/).map(Number);
  const size = vb.length === 4 ? [vb[2], vb[3]] : [parseFloat(svg.getAttribute('width')), parseFloat(svg.getAttribute('height'))];
  svg.removeAttribute('viewBox');
  svg.setAttribute('width', '100%'); svg.setAttribute('height', '100%');
  const layer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  layer.append(...svg.childNodes);
  svg.append(layer);
  box.replaceChildren(svg);
  return new Promise(resolve => {
    const init = () => {
      if (!isCurrent()) return resolve(null);
      const bb = layer.getBBox();
      if (!(bb.width && bb.height && box.clientWidth && box.clientHeight)) return requestAnimationFrame(init);
      resolve(zoomHandle(box, layer, size, onZoom));
    };
    init();
  });
}
// The zoom of a mounted Graphviz diagram (see graphZoom).
function zoomHandle(box, layer, size, onZoom) {
  const [w, h] = size, sel = d3.select(box);
  const fitScale = () => Math.min(box.clientWidth / w, box.clientHeight / h);
  const zoom = d3.zoom().scaleExtent([Math.min(ZOOM_EXTENT[0], fitScale()), ZOOM_EXTENT[1]]).clickDistance(3)
    .on('zoom', ev => { layer.setAttribute('transform', ev.transform); if (onZoom) onZoom(ev.transform); });
  zoomOn(sel, zoom);
  const set = ({ x, y, k }) => zoom.transform(sel, d3.zoomIdentity.translate(x, y).scale(k));
  const zv = {
    layer,
    // contain and centre, no padding; nothing while the box has no size (hidden tab)
    fit() {
      if (!box.clientWidth || !box.clientHeight) return;
      const k = fitScale();
      set({ x: (box.clientWidth - w * k) / 2, y: (box.clientHeight - h * k) / 2, k });
    },
    get() { const t = d3.zoomTransform(box); return { x: t.x, y: t.y, k: t.k }; },
    set,
    // the centre of a screen rectangle at the centre of the box, at scale k (the current one when omitted)
    centre(rect, k) {
      const b = box.getBoundingClientRect(), t = d3.zoomTransform(box), s = k || t.k;
      const [px, py] = t.invert([rect.left + rect.width / 2 - b.left, rect.top + rect.height / 2 - b.top]);
      set({ x: box.clientWidth / 2 - px * s, y: box.clientHeight / 2 - py * s, k: s });
    },
    destroy() { sel.on('.zoom .gesture', null); },
  };
  zv.fit();
  return zv;
}

// CSS of page.css that changes how a Graphviz diagram looks, inlined into the exported SVG when it differs
// from its default (everything else is Graphviz presentation attributes). A new such #d-graph or #f-graph
// rule adds its property here.
const INLINE = { opacity: '1' };

// The visible part of the Graphviz diagram of `box` (zoomed by graphZoom's `zv`) as a standalone SVG
// document, `scale` x its size on screen (the drawing stays vector); null when nothing is drawn. Only what
// is shown: tables and links outside the visible area and tooltips are left out, the zoom layer keeps no
// transform (the viewBox frames the visible area); ids (dbt unique_ids) are kept.
function svgImage(box, zv, scale) {
  const svg = zv && box.querySelector('svg');
  if (!svg) return null;
  const XLINK = 'http://www.w3.org/1999/xlink', XMLNS = 'http://www.w3.org/2000/xmlns/';
  const overlaps = (a, b) => a.right > b.left && a.left < b.right && a.bottom > b.top && a.top < b.bottom;
  const vp = zv.layer, r = svg.getBoundingClientRect();
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
  clone.querySelectorAll('title').forEach(el => el.remove());
  [clone, ...clone.querySelectorAll('*')].forEach(el => {
    el.removeAttribute('title'); el.removeAttributeNS(XLINK, 'title');
    if (!el.getAttribute('style')) el.removeAttribute('style');
  });
  cvp.removeAttribute('transform');
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
async function svgFile(box, zv) {
  const text = svgImage(box, zv, 1);
  return text && new Blob([text], { type: 'image/svg+xml' });
}

// The same SVG rasterised at 2 x the screen resolution (EXPORT.scale; a data: URL keeps the canvas untainted).
async function pngImage(box, zv, EXPORT) {
  const svg = zv && box.querySelector('svg');
  if (!svg) return null;
  const r = svg.getBoundingClientRect(), s = EXPORT.scale(r.width, r.height);
  const img = new Image();
  img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgImage(box, zv, s));
  await img.decode();
  const c = document.createElement('canvas');
  c.width = Math.round(r.width * s); c.height = Math.round(r.height * s);
  const g = c.getContext('2d');
  g.fillStyle = getComputedStyle(document.body).backgroundColor; g.fillRect(0, 0, c.width, c.height);
  g.drawImage(img, 0, 0, c.width, c.height);
  return EXPORT.png(c);
}
