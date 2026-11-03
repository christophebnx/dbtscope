// Universe view: every table of the project as a star, grouped into one constellation per data
// domain. d3-force lays out the tables inside each domain, then the domains; a canvas draws it.
// Started the first time its tab is shown.

// Trajectory of one table along the lineage, a page global so it stays pure and testable.
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

function startUniverse(DATA, lang, openInDetail, detailIds, LAYOUT) {
const $u = id => document.getElementById('u-' + id);
const T = {
  en: { links: 'Links', relations: 'business relations', lineage: 'lineage', both: 'both', detail: 'Tables',
        names: 'names', keys: 'keys', all: 'all fields', layers: 'Layers', kinds: 'Types', domains: 'Domains',
        every: 'all', nothing: 'none', fit: 'Fit', search: 'Find a table…', tables: 'tables', linksN: 'links',
        domainsN: 'domains', columns: 'columns', owner: 'owner', empty: 'No table for these filters.',
        openDetail: 'Double-click: open in the Detail tab', zoomIn: 'Double-click: zoom in',
        frame: 'Double-click: zoom on this domain',
        trajectory: 'Trajectory', trajFound: 'Trajectory of the table found', trajOf: 'Trajectory of',
        direction: 'Direction', depth: 'Depth', up: 'upstream', down: 'downstream',
        d1: '1 level', d2: '2 levels', d3: '3 levels', dall: 'all levels',
        countUp: n => `${n} upstream`, countDown: n => `${n} downstream`,
        noLineage: 'No upstream or downstream table', noUp: 'No upstream table', noDown: 'No downstream table',
        brought: n => n === 1 ? '1 table brought back by the trajectory' : `${n} tables brought back by the trajectory`,
        hiddenN: n => n === 1 ? '1 hidden by the filters' : `${n} hidden by the filters`,
        lgStart: 'start', leave: 'Leave', leaveTitle: 'Leave the trajectory (Esc)', closed: 'Trajectory closed',
        fitTraj: 'Frame the trajectory', tipStart: 'Start of the trajectory',
        tipUp: d => `Upstream, level ${d}`, tipDown: d => `Downstream, level ${d}`,
        clickTraj: 'Click: show its trajectory',
        hint: 'Wheel: zoom · drag the background to pan · drag a table, or a domain by its name, to arrange them · '
            + 'click a table to see its trajectory (Esc to leave) · '
            + 'double-click a domain to zoom in, a table to open its detail' },
  fr: { links: 'Liens', relations: 'relations métier', lineage: 'lignage', both: 'les deux', detail: 'Tables',
        names: 'noms', keys: 'clés', all: 'tous les champs', layers: 'Couches', kinds: 'Types', domains: 'Domaines',
        every: 'tout', nothing: 'aucun', fit: 'Recadrer', search: 'Chercher une table…', tables: 'tables', linksN: 'liens',
        domainsN: 'domaines', columns: 'colonnes', owner: 'propriétaire', empty: 'Aucune table pour ces filtres.',
        openDetail: 'Double-clic : ouvrir dans l\'onglet Détail', zoomIn: 'Double-clic : zoomer',
        frame: 'Double-clic : cadrer ce domaine',
        trajectory: 'Trajectoire', trajFound: 'Trajectoire de la table trouvée', trajOf: 'Trajectoire de',
        direction: 'Sens', depth: 'Profondeur', up: 'amont', down: 'aval',
        d1: '1 niveau', d2: '2 niveaux', d3: '3 niveaux', dall: 'tous les niveaux',
        countUp: n => `${n} en amont`, countDown: n => `${n} en aval`,
        noLineage: 'Aucune table en amont ni en aval', noUp: 'Aucune table en amont', noDown: 'Aucune table en aval',
        brought: n => n === 1 ? '1 table ramenée par la trajectoire' : `${n} tables ramenées par la trajectoire`,
        hiddenN: n => n === 1 ? '1 masquée par les filtres' : `${n} masquées par les filtres`,
        lgStart: 'départ', leave: 'Quitter', leaveTitle: 'Quitter la trajectoire (Échap)', closed: 'Trajectoire fermée',
        fitTraj: 'Cadrer la trajectoire', tipStart: 'Départ de la trajectoire',
        tipUp: d => `En amont, niveau ${d}`, tipDown: d => `En aval, niveau ${d}`,
        clickTraj: 'Clic : afficher sa trajectoire',
        hint: 'Molette : zoom · glisser le fond : déplacer la vue · glisser une table, ou un domaine par son nom, pour les ranger · '
            + 'clic sur une table : sa trajectoire (Échap pour quitter) · '
            + 'double-clic sur un domaine pour le cadrer, sur une table pour son détail' },
}[lang];

const N = DATA.nodes; N.forEach((n, i) => n.i = i);
// how connected each table is over all links: pivots (hubs, dimensions...) get bigger stars and their names first
const DEG = new Array(N.length).fill(0);
[...DATA.relations, ...DATA.lineage].forEach(([a, b]) => { DEG[a]++; DEG[b]++; });
const starR = n => Math.min(14, 3 + 1.6 * Math.sqrt(DEG[n.i]));
// names compete for room on screen: kinds listed first in the config win, then the most connected tables
const KIND_RANK = Object.fromEntries(DATA.kinds.map((k, i) => [k.key, i]));
const labelScore = n => (DEG[n.i] + 1) * (1 - 0.7 * KIND_RANK[n.kind] / Math.max(1, DATA.kinds.length - 1));
const DOM = Object.fromEntries(DATA.domains.map(d => [d.key, d]));
const KIND = Object.fromEntries(DATA.kinds.map(k => [k.key, k]));
const LAYER = Object.fromEntries(DATA.layers.map((l, i) => [l.key, { ...l, rank: i }]));
const counts = key => d3.rollup(N, v => v.length, n => n[key]);
const COUNT = { domain: counts('domain'), layer: counts('layer'), kind: counts('kind') };
const state = {
  domains: new Set(DATA.domains.map(d => d.key)),
  layers: new Set(DATA.layers.map(l => l.key)),
  kinds: new Set(DATA.kinds.map(k => k.key).filter(k => !DATA.defaults.hiddenKinds.includes(k))),
  links: DATA.defaults.links, detail: DATA.defaults.detail,
};
const stage = $u('stage'), canvas = $u('canvas'), ctx = canvas.getContext('2d'), tip = $u('tip');
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const layoutCache = new Map();
let P = [], B = [], REL = new Map(), labelHits = [], visible = [], edges = [], domains = [], routes = [], tree = null;
let t = d3.zoomIdentity, hover = null, found = null, perf = { layout: 0, draw: 0 };
// trajectory mode: null = off, else { start, up, down, edges: [[child, parent, 'up'|'down']], brought }
const trajOpts = { direction: 'both', depth: Infinity };   // kept across trajectories in the session
const DEPTH = { d1: 1, d2: 2, d3: 3, dall: Infinity };
let traj = null, layoutRuns = 0;   // layoutRuns: read by the test hook only
const bar = $u('trajbar'), live = $u('tj-live');

// ---------------------------------------------------------------- controls
const options = (el, values, current) => {
  el.innerHTML = values.map(v => `<option value="${v}" ${v === current ? 'selected' : ''}>${T[v]}</option>`).join('');
};
options($u('links'), ['relations', 'lineage', 'both'], state.links);
options($u('detail'), ['names', 'keys', 'all'], state.detail);
$u('links').onchange = ev => { state.links = ev.target.value; relayout(); };
$u('detail').onchange = ev => { state.detail = ev.target.value; relayout(); };
$u('h-links').textContent = T.links; $u('h-detail').textContent = T.detail;
$u('h-layers').textContent = T.layers; $u('h-kinds').textContent = T.kinds; $u('h-domains').textContent = T.domains;
$u('all').textContent = T.every; $u('none').textContent = T.nothing;
$u('fit').textContent = T.fit; $u('q').placeholder = T.search; $u('hint').textContent = T.hint;

function checkboxes(el, items, countOf, set, color, title) {
  el.innerHTML = '';
  items.forEach(it => {
    const l = document.createElement('label'); l.className = 'chk';
    if (title) l.title = title(it);
    l.innerHTML = `<input type="checkbox" ${set.has(it.key) ? 'checked' : ''}>${color ? `<i style="background:${color(it)}"></i>` : ''}` +
      `<span>${esc(it.label)}</span><small>${countOf.get(it.key) || 0}</small>`;
    l.querySelector('input').onchange = ev => { ev.target.checked ? set.add(it.key) : set.delete(it.key); relayout(); };
    el.appendChild(l);
  });
}
function refreshPanel() {
  checkboxes($u('layers'), DATA.layers, COUNT.layer, state.layers);
  checkboxes($u('kinds'), DATA.kinds, COUNT.kind, state.kinds, k => k.color);
  checkboxes($u('domains'), DATA.domains, COUNT.domain, state.domains, d => d.color, d => d.owner ? `${T.owner}: ${d.owner}` : d.label);
}
refreshPanel();
$u('all').onclick = () => { DATA.domains.forEach(d => state.domains.add(d.key)); refreshPanel(); relayout(); };
$u('none').onclick = () => { state.domains.clear(); refreshPanel(); relayout(); };
$u('toggle').onclick = () => { $u('panel').classList.toggle('closed'); resize(); fit(false); };
$u('fit').onclick = () => fit(true);
$u('names').innerHTML = N.map(n => `<option value="${esc(n.name)}">`).join('');
// a table by its exact name, case-insensitive (search box, Trajectory button)
const findByName = text => { const q = String(text).trim().toLowerCase(); return N.find(n => n.name.toLowerCase() === q); };
// tick back on the domain, layer and type of every listed table that is filtered out; recompute once
// if anything changed; returns how many of the listed tables were hidden
function reveal(indices) {
  let count = 0;
  indices.forEach(i => {
    if (P[i]) return;
    const n = N[i]; count++;
    state.domains.add(n.domain); state.layers.add(n.layer); state.kinds.add(n.kind);
  });
  if (count) { refreshPanel(); relayout(); }
  return count;
}
$u('q').onchange = ev => {
  const n = findByName(ev.target.value);
  if (!n) return;
  reveal([n.i]);
  found = n.i;
  zoomTo(P[n.i].x, P[n.i].y, Math.max(t.k, 1.5));
};

// ---------------------------------------------------------------- geometry
// Each table reserves the room of what it shows: its name, or a card with keys / all fields.
function box(n) {
  if (state.detail === 'names') return { w: Math.max(14 + n.name.length * 5.6, 2 * starR(n) + 4), h: 2 * starR(n) + 16 };
  const rows = state.detail === 'keys' ? n.cols.filter(c => c[2]) : n.cols, shown = rows.slice(0, 30);
  const chars = Math.max(n.name.length * 1.15, ...shown.map(r => r[0].length + 1 + r[1].length * 0.8), 10);
  return { w: 16 + chars * 5.6, h: 18 + shown.length * 11 + (rows.length > shown.length ? 11 : 0), shown, more: rows.length - shown.length };
}

// d3-force collides circles; tables are rectangles, so finish with a sweep that pushes overlapping ones apart
function separate(ns, pad = 4) {
  for (let it = 0; it < 40; it++) {
    let moved = false;
    ns.sort((a, b) => (a.x - a.w / 2) - (b.x - b.w / 2));
    for (let a = 0; a < ns.length; a++) {
      const A = ns[a], right = A.x + A.w / 2 + pad;
      for (let b = a + 1; b < ns.length; b++) {
        const Bn = ns[b];
        if (Bn.x - Bn.w / 2 > right) break;
        const ox = (A.w + Bn.w) / 2 + pad - Math.abs(A.x - Bn.x), oy = (A.h + Bn.h) / 2 + pad - Math.abs(A.y - Bn.y);
        if (ox <= 0 || oy <= 0) continue;
        moved = true;
        if (ox < oy) { const s = (A.x < Bn.x ? -1 : 1) * ox / 2; A.x += s; Bn.x -= s; }
        else { const s = (A.y < Bn.y ? -1 : 1) * oy / 2; A.y += s; Bn.y -= s; }
      }
    }
    if (!moved) break;
  }
}

// ---------------------------------------------------------------- layout
function layout() {
  layoutRuns++;
  const t0 = performance.now();
  visible = N.filter(n => state.domains.has(n.domain) && state.layers.has(n.layer) && state.kinds.has(n.kind));
  const vis = new Set(visible.map(n => n.i));
  B = []; visible.forEach(n => B[n.i] = box(n));
  const seen = new Set(); edges = [];
  const add = list => list.forEach(([a, b]) => {
    const key = a < b ? a + ',' + b : b + ',' + a;
    if (vis.has(a) && vis.has(b) && !seen.has(key)) { seen.add(key); edges.push([a, b]); }
  });
  if (state.links !== 'lineage') add(DATA.relations);
  if (state.links !== 'relations') add(DATA.lineage);

  const local = new Map();
  for (const [dom, members] of d3.group(visible, n => n.domain)) {
    // a domain's inner layout only depends on its own tables, links and detail level
    const key = [dom, state.detail, state.links, members.map(n => n.i).join(',')].join('|');
    if (!layoutCache.has(key)) layoutCache.set(key, layoutDomain(members));
    local.set(dom, layoutCache.get(key));
  }

  // domains: linked ones attract, ordered left to right along the flow, never overlapping
  const agg = new Map(), flow = new Map();
  edges.forEach(([a, b]) => {
    const da = N[a].domain, db = N[b].domain;
    if (da !== db) { const k = da < db ? da + '|' + db : db + '|' + da; agg.set(k, (agg.get(k) || 0) + 1); }
  });
  DATA.lineage.forEach(([child, parent]) => {  // data flows from parent to child
    if (!vis.has(child) || !vis.has(parent)) return;
    const from = N[parent].domain, to = N[child].domain;
    if (from === to) return;
    const k = from < to ? from + '|' + to : to + '|' + from;
    flow.set(k, (flow.get(k) || 0) + (from < to ? 1 : -1));
  });
  // manual arrangement: a moved table keeps its offset from its domain's centre, a moved domain is pinned
  const saved = savedLayout();
  REL = new Map();
  for (const [, L] of local) L.ns.forEach(s => REL.set(s.i, saved.nodes[N[s.i].id] || [s.x - L.cx, s.y - L.cy]));
  domains = [...local].map(([k, v]) => ({ k, rank: v.rank, n: v.ns.length,
    r: Math.max(v.R, d3.max(v.ns, s => reach(s.i))),
    mix: [...d3.rollup(v.ns, g => g.length, s => N[s.i].kind)].sort((a, b) => b[1] - a[1]) }));
  domains.forEach(d => { const p = saved.domains[d.k]; if (p) { d.fx = p[0]; d.fy = p[1]; } });
  routes = [...agg].map(([k, c]) => {
    const [a, b] = k.split('|'), f = flow.get(k) || 0;
    return { source: a, target: b, c, dir: Math.abs(f) > c * 0.2 ? Math.sign(f) : 0 };
  });
  const rand = d3.randomLcg(42), W = (d3.mean(domains, d => d.r) || 1) * 2.4;
  const sim = d3.forceSimulation(domains).randomSource(rand)
    // the padding leaves room for the domain name drawn above each constellation
    .force('collide', d3.forceCollide(d => d.r + 30 + d.r * 0.15).iterations(3))
    .force('link', d3.forceLink(routes).id(d => d.k).distance(l => l.source.r + l.target.r + 60)
      .strength(l => Math.min(0.4, 0.03 + Math.log1p(l.c) * 0.04)))
    .force('x', d3.forceX(d => d.rank * W).strength(0.06))
    .force('y', d3.forceY(0).strength(0.06))
    .force('charge', d3.forceManyBody().strength(-20))
    .stop();
  for (let k = 0; k < 400; k++) sim.tick();
  // settle with collisions only, so link forces can't leave constellations overlapping
  sim.force('link', null).force('x', null).force('y', null).force('charge', null);
  for (let k = 0; k < 100; k++) sim.tick();

  P = [];
  domains.forEach(d => local.get(d.k).ns.forEach(s => { const [dx, dy] = REL.get(s.i); P[s.i] = { x: d.x + dx, y: d.y + dy }; }));
  tree = d3.quadtree(visible, n => P[n.i].x, n => P[n.i].y);
  perf.layout = performance.now() - t0;
}

const savedLayout = () => LAYOUT.get('universe', state.detail) || { domains: {}, nodes: {} };
// how far a table reaches from its domain's centre, so the halo still surrounds a table dragged outwards
const reach = i => { const [dx, dy] = REL.get(i), b = B[i]; return Math.hypot(Math.abs(dx) + b.w / 2, Math.abs(dy) + b.h / 2) + 30; };

function layoutDomain(members) {
  const ranks = [...new Set(members.map(n => LAYER[n.layer].rank))].sort((a, b) => a - b);
  const ns = members.map(n => { const b = box(n); return { i: n.i, w: b.w, h: b.h, r: Math.sqrt(b.w * b.h) * 0.6 + 2 }; });
  const avgR = d3.mean(ns, d => d.r);
  // layers side by side along the flow, left to right
  const spacing = avgR * 2.2 * Math.sqrt(ns.length / ranks.length) + 40;
  ns.forEach((d, j) => d.tx = (ranks.indexOf(LAYER[members[j].layer].rank) - (ranks.length - 1) / 2) * spacing);
  const at = new Map(ns.map((d, j) => [d.i, j]));
  const intra = edges.filter(([a, b]) => at.has(a) && at.has(b)).map(([a, b]) => ({ source: at.get(a), target: at.get(b) }));
  const sim = d3.forceSimulation(ns).randomSource(d3.randomLcg(42))
    .force('collide', d3.forceCollide(d => d.r))
    .force('x', d3.forceX(d => d.tx).strength(0.12))
    .force('y', d3.forceY(0).strength(0.08))
    .force('link', d3.forceLink(intra).distance(l => l.source.r + l.target.r + 8).strength(0.2))
    .force('charge', d3.forceManyBody().strength(-6).distanceMax(avgR * 8))
    .stop();
  for (let k = 0, n = Math.min(120, 40 + ns.length / 3); k < n; k++) sim.tick();
  separate(ns);
  const x0 = d3.min(ns, d => d.x - d.w / 2), x1 = d3.max(ns, d => d.x + d.w / 2);
  const y0 = d3.min(ns, d => d.y - d.h / 2), y1 = d3.max(ns, d => d.y + d.h / 2);
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  const R = d3.max(ns, d => Math.hypot(Math.abs(d.x - cx) + d.w / 2, Math.abs(d.y - cy) + d.h / 2)) + 30;
  return { ns: ns.map(d => ({ i: d.i, x: d.x, y: d.y })), cx, cy, R, rank: d3.mean(members, n => LAYER[n.layer].rank) };
}

// ---------------------------------------------------------------- drawing
const C = { bg: '#f5f6f8', text: '#1f2933', muted: '#6b7280', card: '#ffffff', route: 'rgba(71,85,105,.22)',
            arrow: 'rgba(71,85,105,.55)', edge: 'rgba(100,116,139,.22)', cross: 'rgba(100,116,139,.10)', hl: 'rgba(31,41,51,.85)',
            up: '#6d28d9', down: '#c2410c' };   // trajectory: upstream (dashed marks), downstream (solid marks)
const DIM = 0.2, DIM_CTX = 0.45;   // trajectory mode: alpha of what is outside it, of domains holding none of it
stage.style.setProperty('--traj-up', C.up); stage.style.setProperty('--traj-down', C.down);
const FONT = '"Segoe UI", Arial, sans-serif';

// filled arrowhead at 55 % of the segment a -> b, pointing at b, in the current fill style
function arrowHead(ax, ay, bx, by, size) {
  const ang = Math.atan2(by - ay, bx - ax), mx = ax + (bx - ax) * 0.55, my = ay + (by - ay) * 0.55;
  ctx.beginPath(); ctx.moveTo(mx + Math.cos(ang) * size, my + Math.sin(ang) * size);
  ctx.lineTo(mx + Math.cos(ang + 2.5) * size, my + Math.sin(ang + 2.5) * size);
  ctx.lineTo(mx + Math.cos(ang - 2.5) * size, my + Math.sin(ang - 2.5) * size); ctx.fill();
}
// role of a table in the trajectory: 'start' | 'up' | 'down' | null (a table in both maps is drawn as upstream)
const roleOf = i => !traj ? null : i === traj.start ? 'start' : traj.up.has(i) ? 'up' : traj.down.has(i) ? 'down' : null;
const trajMembers = () => traj ? [traj.start, ...traj.up.keys(), ...traj.down.keys()] : [];
const trajDist = i => i === traj.start ? 0 : Math.min(traj.up.get(i) ?? Infinity, traj.down.get(i) ?? Infinity);

function draw() {
  const t0 = performance.now(), dpr = window.devicePixelRatio || 1, k = t.k, W = stage.clientWidth, H = stage.clientHeight;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  if (!visible.length) {
    ctx.fillStyle = C.muted; ctx.font = `14px ${FONT}`; ctx.fillText(T.empty, 24, 40);
    return;
  }
  const [x0, y0] = t.invert([0, 0]), [x1, y1] = t.invert([W, H]);
  const inView = (x, y, w, h) => x + w / 2 > x0 && x - w / 2 < x1 && y + h / 2 > y0 && y - h / 2 < y1;
  const screen = (x, y) => [x * k + t.x, y * k + t.y];
  // in the trajectory mode, domains holding none of its drawn tables are context only
  const tdom = traj ? new Set(trajMembers().filter(i => P[i]).map(i => N[i].domain)) : null;
  const ctxAlpha = d => tdom && !tdom.has(d.k) ? DIM_CTX : 1;

  ctx.save(); ctx.translate(t.x, t.y); ctx.scale(k, k);
  domains.forEach(d => {
    const c = DOM[d.k].color, g = ctx.createRadialGradient(d.x, d.y, 0, d.x, d.y, d.r);
    g.addColorStop(0, c + '26'); g.addColorStop(1, c + '0a');
    ctx.globalAlpha = ctxAlpha(d);
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(d.x, d.y, d.r, 0, 7); ctx.fill();
    ctx.strokeStyle = c + '66'; ctx.lineWidth = 1.5 / k; ctx.stroke();
  });
  ctx.globalAlpha = traj ? DIM : 1;

  if (k < 0.6) {  // from afar: one route per pair of domains, arrowed along the data flow
    routes.forEach(r => {
      const a = r.dir < 0 ? r.target : r.source, b = r.dir < 0 ? r.source : r.target;
      ctx.strokeStyle = C.route; ctx.fillStyle = C.arrow;
      ctx.lineWidth = (1 + Math.log2(r.c)) * 1.6 / k;
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      if (r.dir) arrowHead(a.x, a.y, b.x, b.y, 9 / k);
    });
  }
  // table-level links: hidden from afar (the routes say it), faint at mid zoom, full when close;
  // hover dimming is off in the trajectory mode, whose dimming replaces it
  const near = hover != null && !traj ? new Set([hover, ...edges.filter(e => e.includes(hover)).flat()]) : null;
  ctx.lineWidth = 1 / k;
  edges.forEach(([a, b]) => {
    const hl = near && (a === hover || b === hover), cross = N[a].domain !== N[b].domain;
    if (!hl && (k < 0.35 || (k < 0.6 && cross))) return;
    ctx.strokeStyle = hl ? C.hl : cross ? C.cross : C.edge;
    ctx.beginPath(); ctx.moveTo(P[a].x, P[a].y); ctx.lineTo(P[b].x, P[b].y); ctx.stroke();
  });

  const cards = state.detail !== 'names' && k > 0.35;
  const labels = [];
  const drawTable = n => {
    const p = P[n.i], b = B[n.i]; if (!inView(p.x, p.y, b.w, b.h)) return;
    const col = KIND[n.kind].color, mark = n.i === hover || n.i === found, role = roleOf(n.i);
    ctx.globalAlpha = traj ? (role ? 1 : DIM) : near && !near.has(n.i) ? 0.2 : 1;
    if (cards) drawCard(n, p, b, col, mark, role, k);
    else { drawStar(n, p, col, mark, role, k); labels.push(n); }
  };
  if (traj) {  // trajectory tables after its edges, so arrows never cover them
    visible.forEach(n => { if (!roleOf(n.i)) drawTable(n); });
    ctx.globalAlpha = 1;
    drawTrajectoryEdges(k);
    visible.forEach(n => { if (roleOf(n.i)) drawTable(n); });
  } else visible.forEach(drawTable);
  ctx.globalAlpha = 1;
  ctx.restore();

  // screen-space text: domain names first, then table names by importance, skipping any that would overlap
  const taken = [];
  labelHits = [];
  const free = (x, y, w, h) => !taken.some(r => x < r[0] + r[2] && x + w > r[0] && y < r[1] + r[3] && y + h > r[1]);
  ctx.textAlign = 'center';
  domains.forEach(d => {
    const dd = DOM[d.k], [sx, sy] = screen(d.x, d.y - d.r), fs = Math.max(13, Math.min(20, 10 + d.r * k / 25));
    ctx.globalAlpha = ctxAlpha(d);
    ctx.font = `600 ${fs}px ${FONT}`; ctx.fillStyle = dd.color;
    ctx.fillText(dd.label, sx, sy - 22);
    const w = Math.max(ctx.measureText(dd.label).width, 80) + 8;
    ctx.font = `12px ${FONT}`; ctx.fillStyle = C.muted;
    ctx.fillText(`${d.n} ${T.tables}`, sx, sy - 8);
    // composition by type, readable before any single star is
    let bx = sx - 40;
    d.mix.forEach(([kind, c]) => { const bw = 80 * c / d.n; ctx.fillStyle = KIND[kind].color; ctx.fillRect(bx, sy - 4, bw, 4); bx += bw; });
    taken.push([sx - w / 2, sy - 22 - fs, w, fs + 22]);
    labelHits.push({ d, x: sx - w / 2, y: sy - 22 - fs, w, h: fs + 22 });
  });
  ctx.globalAlpha = 1;
  if (!cards) drawNames(orderLabels(labels), screen, free, taken, k);
  ctx.textAlign = 'left';
  perf.draw = performance.now() - t0;
  $u('meta').textContent = `${visible.length} ${T.tables} · ${edges.length} ${T.linksN} · ${domains.length} ${T.domainsN}`;
}

// names by priority: in the trajectory mode its tables first (start, then by distance), then the hovered one, then by score
function orderLabels(labels) {
  labels.sort((a, b) => labelScore(b) - labelScore(a));
  const hov = hover != null && P[hover] ? [N[hover]] : [];
  if (!traj) return [...hov, ...labels];
  const inT = labels.filter(n => roleOf(n.i)).sort((a, b) => trajDist(a.i) - trajDist(b.i));
  return [...inT, ...hov, ...labels.filter(n => !roleOf(n.i))];
}
function drawNames(labels, screen, free, taken, k) {
  let shown = 0;
  for (const n of labels) {
    if (shown >= 400) break;
    const role = roleOf(n.i);
    const strong = role ? trajDist(n.i) <= 1 : labelScore(n) >= 10 || n.i === hover;
    ctx.font = `${strong ? 600 : 400} 11px ${FONT}`;
    const [sx, sy] = screen(P[n.i].x, P[n.i].y), r = Math.max(starR(n) * k, 2.5);
    const w = ctx.measureText(n.name).width + 6, y = sy + r + 2;
    if (!free(sx - w / 2, y, w, 14)) continue;
    taken.push([sx - w / 2, y, w, 14]); shown++;
    ctx.globalAlpha = traj && !role ? DIM : 1;
    ctx.fillStyle = 'rgba(245,246,248,.85)'; ctx.fillRect(sx - w / 2, y, w, 14);
    ctx.fillStyle = strong || role ? C.text : C.muted;
    ctx.fillText(n.name, sx, y + 11);
  }
  ctx.globalAlpha = 1;
}
// a ring around a star: dashed for upstream, as on the legend
function ring(p, r, color, width, dashed, k) {
  ctx.strokeStyle = color; ctx.lineWidth = width;
  ctx.setLineDash(dashed ? [5 / k, 3 / k] : []);
  ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, 7); ctx.stroke();
  ctx.setLineDash([]);
}
function drawStar(n, p, col, mark, role, k) {
  const far = k < 0.6, r = Math.max(starR(n), (role ? 3 : 2.5) / k);
  ctx.fillStyle = col; ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, 7); ctx.fill();
  ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1 / k; ctx.stroke();
  if (role === 'start') { ring(p, r + 3 / k, C.text, 1.5 / k, false, k); ring(p, r + 6 / k, C.text, 1.5 / k, false, k); return; }
  let out = 4 / k;
  if (role) { out = (far ? 3 : 4) / k; ring(p, r + out, C[role], (far ? 1.5 : 2) / k, role === 'up', k); out += 3 / k; }
  if (mark) ring(p, r + out, C.text, 2 / k, false, k);
}
function drawCard(n, p, b, col, mark, role, k) {
  const x = p.x - b.w / 2, y = p.y - b.h / 2, mk = Math.min(k, 1);
  ctx.fillStyle = C.card; ctx.fillRect(x, y, b.w, b.h);
  ctx.strokeStyle = role === 'start' ? C.text : role ? C[role] : mark ? C.text : col;
  ctx.lineWidth = (role === 'start' ? 3 : role ? 2.5 : mark ? 2.5 : 1) / mk;
  ctx.setLineDash(role === 'up' ? [6 / mk, 3 / mk] : []);
  ctx.strokeRect(x, y, b.w, b.h);
  ctx.setLineDash([]);
  if (role === 'start' || (role && mark)) {  // outer rectangle 3 px outside
    const o = 3 / k + ctx.lineWidth / 2;
    ctx.strokeStyle = C.text; ctx.lineWidth = 1.5 / mk; ctx.strokeRect(x - o, y - o, b.w + 2 * o, b.h + 2 * o);
  }
  ctx.fillStyle = col; ctx.fillRect(x, y, b.w, 16);
  if (k > 0.6) {
    ctx.fillStyle = '#fff'; ctx.font = `600 10px ${FONT}`; ctx.fillText(n.name, x + 5, y + 12);
    ctx.font = `9px ${FONT}`;
    b.shown.forEach((r, j) => {
      ctx.fillStyle = r[2] ? C.text : C.muted; ctx.fillText(r[0], x + 5, y + 28 + j * 11);
      ctx.fillStyle = '#9aa3af'; ctx.fillText(r[1], x + b.w - 5 - ctx.measureText(r[1]).width, y + 28 + j * 11);
    });
    if (b.more > 0) { ctx.fillStyle = C.muted; ctx.fillText(`+ ${b.more}`, x + 5, y + 28 + b.shown.length * 11); }
  }
}
// the lineage edges of the trajectory, parent -> child, at every zoom and whatever the Links selector shows
function drawTrajectoryEdges(k) {
  const far = k < 0.6, lw = (far ? 1.5 : 2) / k, head = (far ? 7 : 8) / k;
  traj.edges.forEach(([c, p, dir]) => {
    const a = P[p], b = P[c];
    if (!a || !b) return;   // hidden by a filter changed in the mode
    ctx.strokeStyle = C[dir]; ctx.fillStyle = C[dir]; ctx.lineWidth = lw;
    ctx.setLineDash(dir === 'up' ? [5 / k, 3 / k] : []);
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    ctx.setLineDash([]);
    if (!far || Math.hypot(b.x - a.x, b.y - a.y) * k >= 24) arrowHead(a.x, a.y, b.x, b.y, head);
  });
}

// ---------------------------------------------------------------- navigation
const zoom = d3.zoom().scaleExtent([0.01, 12]).on('zoom', ev => { t = ev.transform; draw(); });
const drag = d3.drag().container(canvas).filter(ev => !ev.button)
  .subject(ev => {
    const n = t.k >= FAR ? pickAt(...t.invert([ev.x, ev.y])) : null;
    if (n) return { n, x: ev.x, y: ev.y };
    const hit = labelAt(ev.x, ev.y);
    return hit ? { d: hit.d, x: ev.x, y: ev.y } : null;
  })
  .on('start', ev => { ev.subject.moved = false; tip.style.display = 'none'; canvas.style.cursor = 'grabbing'; })
  .on('drag', ev => {
    const dx = ev.dx / t.k, dy = ev.dy / t.k, s = ev.subject;
    s.moved = true;
    if (s.n) { P[s.n.i].x += dx; P[s.n.i].y += dy; }
    else { s.d.x += dx; s.d.y += dy; visible.forEach(n => { if (n.domain === s.d.k) { P[n.i].x += dx; P[n.i].y += dy; } }); }
    draw();
  })
  .on('end', ev => {
    const s = ev.subject;
    canvas.style.cursor = '';
    if (!s.moved) return;
    const saved = savedLayout();
    if (s.n) {
      const d = domains.find(d => d.k === s.n.domain);
      REL.set(s.n.i, [P[s.n.i].x - d.x, P[s.n.i].y - d.y]);
      saved.nodes[s.n.id] = REL.get(s.n.i);
      d.r = Math.max(d.r, reach(s.n.i));
    }
    // pin every domain where it stands, so recomputing the layout later doesn't move the others
    domains.forEach(d => saved.domains[d.k] = [d.x, d.y]);
    LAYOUT.set('universe', state.detail, saved);
    tree = d3.quadtree(visible, n => P[n.i].x, n => P[n.i].y);
    draw();
  });
const sel = d3.select(canvas).call(drag).call(zoom).on('dblclick.zoom', null);
// room kept free at the top of the canvas: the trajectory bar overlays it while the mode is on
const top = () => traj ? bar.offsetHeight : 0;
// frame a world-space box, at most at scale kMax
function frame(bx0, by0, bx1, by1, animate, kMax = Infinity) {
  // domain names sit above the halos at a fixed screen size: keep that strip free at the top
  const NAME = 46, top0 = top(), w = stage.clientWidth, h = stage.clientHeight - top0 - NAME;
  const k = Math.min(kMax, 0.95 * Math.min(w / (bx1 - bx0), h / (by1 - by0)));
  const tr = d3.zoomIdentity.translate(w / 2, top0 + NAME + h / 2).scale(k).translate(-(bx0 + bx1) / 2, -(by0 + by1) / 2);
  (animate ? sel.transition().duration(500) : sel).call(zoom.transform, tr);
}
// the whole universe, or the drawn tables of the trajectory while the mode is on
function fit(animate) {
  const tj = trajMembers().filter(i => P[i]);
  if (tj.length) {
    return frame(d3.min(tj, i => P[i].x - B[i].w / 2), d3.min(tj, i => P[i].y - B[i].h / 2),
      d3.max(tj, i => P[i].x + B[i].w / 2), d3.max(tj, i => P[i].y + B[i].h / 2), animate, 2);
  }
  if (!domains.length) return draw();
  frame(d3.min(domains, d => d.x - d.r), d3.min(domains, d => d.y - d.r),
    d3.max(domains, d => d.x + d.r), d3.max(domains, d => d.y + d.r), animate);
}
function zoomTo(x, y, k) {
  const top0 = top(), w = stage.clientWidth, h = stage.clientHeight - top0;
  sel.transition().duration(600).call(zoom.transform, d3.zoomIdentity.translate(w / 2, top0 + h / 2).scale(k).translate(-x, -y));
}
const pick = ev => pickAt(...t.invert(d3.pointer(ev, canvas)));
function pickAt(wx, wy) {
  if (!tree) return null;
  const n = tree.find(wx, wy, Math.max(200, 12 / t.k));
  if (!n) return null;
  const p = P[n.i], b = B[n.i];
  const hit = state.detail !== 'names' && t.k > 0.35
    ? Math.abs(wx - p.x) <= b.w / 2 && Math.abs(wy - p.y) <= b.h / 2
    : Math.hypot(wx - p.x, wy - p.y) <= Math.max(8, 8 / t.k);
  return hit ? n : null;
}
// the domain name under a screen point, if any
const labelAt = (x, y) => labelHits.find(h => x >= h.x && x <= h.x + h.w && y >= h.y && y <= h.y + h.h);
function domainAt(ev) {
  const [wx, wy] = t.invert(d3.pointer(ev, canvas));
  return domains.find(d => Math.hypot(wx - d.x, wy - d.y) < d.r);
}
canvas.addEventListener('mousemove', ev => {
  const n = pick(ev), h = n ? n.i : null;
  if (h !== hover) { hover = h; draw(); }
  const d = n ? null : domainAt(ev);
  const [px, py] = d3.pointer(ev, canvas);
  canvas.style.cursor = (n && t.k >= FAR) || labelAt(px, py) ? 'grab' : '';
  if (!n && !d) { tip.style.display = 'none'; return; }
  if (n) {
    const dbl = detailIds.has(n.id) ? T.openDetail : T.zoomIn, start = traj && n.i === traj.start;
    tip.innerHTML = `<b>${esc(n.name)}</b><div class="m">${esc(DOM[n.domain].label)} · ${esc(LAYER[n.layer].label)} · ${esc(KIND[n.kind].label)} · ${n.cols.length} ${T.columns}</div>` +
      trajTip(n.i) + (n.desc ? `<div style="margin-top:6px">${esc(n.desc)}</div>` : '') +
      `<div class="a">${t.k < FAR ? T.frame : start ? dbl : T.clickTraj + ' · ' + dbl}</div>`;
  } else {
    const dd = DOM[d.k];
    tip.innerHTML = `<b>${esc(dd.label)}</b><div class="m">${d.n} ${T.tables}${dd.owner ? ` · ${T.owner} : ${esc(dd.owner)}` : ''}</div><div class="a">${T.frame}</div>`;
  }
  const r = stage.getBoundingClientRect();
  tip.style.display = 'block';
  tip.style.left = Math.min(ev.clientX - r.left + 14, r.width - 380) + 'px';
  tip.style.top = (ev.clientY - r.top + 14) + 'px';
});
canvas.addEventListener('mouseleave', () => { tip.style.display = 'none'; if (hover != null) { hover = null; draw(); } });
// from afar stars are packed too tightly to aim at: double-click frames the domain until zoomed in
const FAR = 0.5;
canvas.addEventListener('dblclick', ev => {
  const n = t.k >= FAR ? pick(ev) : null;
  if (n) {
    if (detailIds.has(n.id)) { tip.style.display = 'none'; openInDetail(n.id); return; }
    found = n.i; zoomTo(P[n.i].x, P[n.i].y, Math.max(t.k * 2.5, 1.5));
    return;
  }
  const d = domainAt(ev);
  if (d) zoomTo(d.x, d.y, 0.92 * Math.min(stage.clientWidth, stage.clientHeight - top()) / (2 * d.r + 60));
});
// single click: a table enters the trajectory mode, or moves it; only the empty background
// (no table, domain label or domain halo, at any zoom) leaves it.
// d3-drag and d3-zoom swallow the click that ends a drag or a pan.
canvas.addEventListener('click', ev => {
  if (ev.detail > 1) return;   // the second click of a double-click
  const n = t.k >= FAR ? pick(ev) : null;
  if (n) { enterTrajectory(n.i); return; }
  if (traj && !labelAt(...d3.pointer(ev, canvas)) && !domainAt(ev)) leaveTrajectory(false);
});

// ---------------------------------------------------------------- trajectory mode
const num = v => v.toLocaleString(lang);
// "5 upstream · 1 downstream", restricted to the direction shown
function countsText(u, d) {
  const dir = trajOpts.direction;
  return dir === 'up' ? T.countUp(num(u)) : dir === 'down' ? T.countDown(num(d)) : `${T.countUp(num(u))} · ${T.countDown(num(d))}`;
}
function trajTip(i) {
  if (!traj) return '';
  if (i === traj.start) return `<div class="tj start">${T.tipStart}</div>`;
  return (traj.up.has(i) ? `<div class="tj up">${T.tipUp(traj.up.get(i))}</div>` : '')
    + (traj.down.has(i) ? `<div class="tj down">${T.tipDown(traj.down.get(i))}</div>` : '');
}
function enterTrajectory(i) {
  const { up, down } = trajectory(DATA.lineage, i, trajOpts.direction, trajOpts.depth);
  const tedges = [];
  DATA.lineage.forEach(([c, p]) => {
    if (up.has(p) && (c === i || up.has(c))) tedges.push([c, p, 'up']);
    else if (down.has(c) && (p === i || down.has(p))) tedges.push([c, p, 'down']);
  });
  traj = { start: i, up, down, edges: tedges, brought: 0 };
  bar.hidden = false;   // shown before reveal, so a relayout frames the trajectory below the bar
  traj.brought = reveal(trajMembers());
  const n = N[i], summary = renderBar();
  live.textContent = `${T.trajOf} ${n.name}: ${summary}.` + (traj.brought ? ` ${T.brought(traj.brought)}.` : '');
  draw();
}
function leaveTrajectory(restoreFocus) {
  if (!traj) return;
  const inBar = bar.contains(document.activeElement);
  traj = null; bar.hidden = true; $u('tj-counts').open = false;
  $u('fit').removeAttribute('title');
  live.textContent = T.closed;
  if (restoreFocus && inBar) ($u('traj').disabled ? $u('q') : $u('traj')).focus();
  draw();
}
// fills the bar from the current trajectory; returns the counts (or empty-state) text
function renderBar() {
  const n = N[traj.start], u = traj.up.size, d = traj.down.size, empty = u + d === 0;
  $u('tj-dot').style.background = KIND[n.kind].color;
  $u('tj-start').textContent = n.name; $u('tj-start').title = n.name;
  const per = new Map();
  const tally = (m, key) => m.forEach((_, j) => {
    const c = per.get(N[j].domain) || { u: 0, d: 0 }; c[key]++; per.set(N[j].domain, c);
  });
  tally(traj.up, 'u'); tally(traj.down, 'd');
  const rows = [...per].map(([k, c]) => ({ k, total: c.u + c.d, text: `${DOM[k].label}: ${countsText(c.u, c.d)}` }))
    .sort((a, b) => b.total - a.total || a.text.localeCompare(b.text));
  $u('tj-list').replaceChildren(...rows.map(r => {
    const li = document.createElement('li'), dot = document.createElement('i');
    dot.style.background = DOM[r.k].color; li.append(dot, r.text);
    return li;
  }));
  const sum = $u('tj-sum'), emptyText = { both: T.noLineage, up: T.noUp, down: T.noDown }[trajOpts.direction];
  sum.textContent = countsText(u, d); sum.title = rows.map(r => r.text).join('\n');
  $u('tj-counts').hidden = empty; $u('tj-empty').hidden = !empty;
  $u('tj-empty').textContent = empty ? emptyText : '';
  const hidden = trajMembers().filter(j => !P[j]).length;
  $u('tj-hidden').textContent = hidden ? T.hiddenN(hidden) : '';
  $u('tj-back').textContent = traj.brought ? T.brought(traj.brought) : '';
  $u('fit').title = T.fitTraj;
  return empty ? emptyText : sum.textContent;
}
bar.setAttribute('aria-label', T.trajectory);
$u('tj-title').textContent = T.trajOf;
$u('tj-h-dir').textContent = T.direction; $u('tj-h-depth').textContent = T.depth;
$u('tj-l-start').textContent = T.lgStart; $u('tj-l-up').textContent = T.up; $u('tj-l-down').textContent = T.down;
$u('tj-leave').textContent = T.leave; $u('tj-leave').title = T.leaveTitle;
options($u('tj-dir'), ['both', 'up', 'down'], trajOpts.direction);
options($u('tj-depth'), ['dall', 'd1', 'd2', 'd3'], 'dall');
$u('tj-dir').onchange = ev => { trajOpts.direction = ev.target.value; if (traj) enterTrajectory(traj.start); };
$u('tj-depth').onchange = ev => { trajOpts.depth = DEPTH[ev.target.value]; if (traj) enterTrajectory(traj.start); };
$u('tj-leave').onclick = () => leaveTrajectory(true);
const trajBtn = $u('traj'), syncTrajBtn = () => { trajBtn.disabled = !findByName($u('q').value); };
trajBtn.textContent = T.trajectory; trajBtn.title = T.trajFound;
$u('q').addEventListener('input', syncTrajBtn); $u('q').addEventListener('change', syncTrajBtn);
trajBtn.onclick = () => {
  const n = findByName($u('q').value);
  if (!n) return;
  enterTrajectory(n.i);
  $u('tj-dir').focus();
};
document.addEventListener('keydown', ev => {
  if (ev.key !== 'Escape' || !traj || !document.getElementById('tab-universe').classList.contains('on')) return;
  const counts = $u('tj-counts');
  if (counts.open) { counts.open = false; $u('tj-sum').focus(); return; }
  if (ev.target === $u('q') || ev.target.tagName === 'SELECT') return;   // Esc belongs to the open list
  leaveTrajectory(true);
});
// read-only view of the trajectory mode, for the browser tests; ids are dbt unique_ids
function trajectoryState() {
  const ids = m => Object.fromEntries([...(m || [])].map(([i, d]) => [N[i].id, d]));
  return { active: !!traj, start: traj ? N[traj.start].id : null, direction: trajOpts.direction,
    depth: trajOpts.depth === Infinity ? 'all' : trajOpts.depth, up: ids(traj && traj.up), down: ids(traj && traj.down),
    brought: traj ? traj.brought : 0, layoutRuns };
}

function resize() {
  const dpr = window.devicePixelRatio || 1, w = stage.clientWidth, h = stage.clientHeight;
  canvas.width = w * dpr; canvas.height = h * dpr; canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
  draw();
}
// recompute the layout; the trajectory is kept (indices into N are stable, only P changes)
function relayout() { found = null; hover = null; layout(); if (traj) renderBar(); fit(false); draw(); }
let size = '';
new ResizeObserver(() => {
  const s = stage.clientWidth + 'x' + stage.clientHeight;
  if (stage.clientWidth && s !== size) { size = s; resize(); fit(false); }
}).observe(stage);
layout(); resize(); fit(false);

return { shown: () => { resize(); }, relayout, trajectoryState };
}
