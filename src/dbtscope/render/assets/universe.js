// Universe view: every table of the project as a star, grouped into one constellation per data
// domain, or per layer (D-048). A constellation's tables are packed in bands (layer bands, or domain
// bands in layer mode) into the smallest disc (D-040), then d3-force places the constellations; a
// canvas draws it.
// Started the first time its tab is shown. The trajectory traversal and its shared strings are in common.js.

function startUniverse(DATA, openInDetail, detailIds, LAYOUT, EXPORT, openFlow) {
  const $u = id => document.getElementById('u-' + id);
  const T = {
    en: { links: 'Links', relations: 'business relations', lineage: 'lineage', detail: 'Tables',
          names: 'names', keys: 'keys', all: 'all fields', layers: 'Layers', domains: 'Domains',
          every: 'all', nothing: 'none', search: 'Find a table…', linksN: ['link', 'links'], owner: 'owner',
          openDetail: 'Double-click: open in the Detail tab', zoomIn: 'Double-click: zoom in',
          frame: 'Double-click: zoom on this domain', frameC: 'Double-click: zoom on this constellation',
          by: 'Constellations', layersN: ['layer', 'layers'], domainOne: 'Domain',
          trajectory: 'Trajectory', trajFound: 'Trajectory of the table found', trajOf: 'Trajectory of',
          brought: ['table brought back by the trajectory', 'tables brought back by the trajectory'],
          hiddenN: ['hidden by the filters', 'hidden by the filters'],
          leave: 'Leave', leaveTitle: 'Leave the trajectory (Esc)', closed: 'Trajectory closed',
          fitTraj: 'Frame the trajectory', flow: 'Flow', flowTitle: 'Show this trajectory as a left-to-right flow',
          clickTraj: 'Click: show its trajectory',
          pngTitle: 'Save the view as shown as a PNG image (high resolution)',
          role: 'role', roles: { core: 'core', connector: 'connector', descriptive: 'descriptive', technical: 'technical' },
          hint: 'Wheel: zoom · drag the background to pan · drag a table, or a constellation by its name, to arrange them · '
              + 'click a table to see its trajectory (Esc to leave) · '
              + 'double-click a constellation to zoom in, a table to open its detail',
          fold: 'Fold descriptive tables into their entity',
          foldTitle: 'Draw each descriptive table inside its entity. Search or a trajectory shows it around its entity.',
          foldedN: ['folded table', 'folded tables'], entitiesN: ['entity', 'entities'],
          entity: 'Entity', entityHidden: ' (filtered out)', entityLayer: ' (other layer)',
          foldOn: n => `Descriptive tables folded into ${plural(n, T.entitiesN)}`, foldOff: 'Descriptive tables shown',
          foundFolded: (n, p) => `${n} is folded into ${p}; shown around it.`, shownAround: 'Shown around their entity',
          hintFold: ' · a number on a star: tables folded into it, shown around it by search or trajectory' },
    fr: { links: 'Liens', relations: 'relations métier', lineage: 'lignage', detail: 'Tables',
          names: 'noms', keys: 'clés', all: 'tous les champs', layers: 'Couches', domains: 'Domaines',
          every: 'tout', nothing: 'aucun', search: 'Chercher une table…', linksN: ['lien', 'liens'],
          owner: 'propriétaire',
          openDetail: 'Double-clic\u00a0: ouvrir dans l\'onglet Détail', zoomIn: 'Double-clic\u00a0: zoomer',
          frame: 'Double-clic\u00a0: cadrer ce domaine', frameC: 'Double-clic\u00a0: cadrer cette constellation',
          by: 'Constellations', layersN: ['couche', 'couches'], domainOne: 'Domaine',
          trajectory: 'Trajectoire', trajFound: 'Trajectoire de la table trouvée', trajOf: 'Trajectoire de',
          brought: ['table ramenée par la trajectoire', 'tables ramenées par la trajectoire'],
          hiddenN: ['masquée par les filtres', 'masquées par les filtres'],
          leave: 'Quitter', leaveTitle: 'Quitter la trajectoire (Échap)', closed: 'Trajectoire fermée',
          fitTraj: 'Cadrer la trajectoire', flow: 'Flux',
          flowTitle: 'Afficher cette trajectoire en flux, de gauche à droite',
          clickTraj: 'Clic\u00a0: afficher sa trajectoire',
          pngTitle: 'Enregistrer la vue telle qu\'affichée en image PNG (haute résolution)',
          role: 'rôle', roles: { core: 'centrale', connector: 'de liaison', descriptive: 'descriptive', technical: 'technique' },
          hint: 'Molette\u00a0: zoom · glisser le fond\u00a0: déplacer la vue · glisser une table, ou une constellation par son nom, pour les ranger · '
              + 'clic sur une table\u00a0: sa trajectoire (Échap pour quitter) · '
              + 'double-clic sur une constellation pour la cadrer, sur une table pour son détail',
          fold: 'Replier les tables descriptives dans leur entité',
          foldTitle: 'Dessiner chaque table descriptive dans son entité. La recherche ou une trajectoire l\'affiche autour de son entité.',
          foldedN: ['table repliée', 'tables repliées'], entitiesN: ['entité', 'entités'],
          entity: 'Entité', entityHidden: ' (masquée par les filtres)', entityLayer: ' (autre couche)',
          foldOn: n => `Tables descriptives repliées dans ${plural(n, T.entitiesN)}`, foldOff: 'Tables descriptives affichées',
          foundFolded: (n, p) => `${n} est repliée dans ${p}\u202f; affichée autour d\'elle.`, shownAround: 'Affichées autour de leur entité',
          hintFold: ' · un nombre sur une étoile\u00a0: tables repliées dans celle-ci, affichées autour d\'elle par la recherche ou la trajectoire' },
  }[PAGE.lang];

  const N = DATA.nodes; N.forEach((n, i) => n.i = i);
  // how connected each table is over all links: pivots (hubs, dimensions...) get bigger stars and their names first
  const DEG = new Array(N.length).fill(0);
  [...DATA.relations, ...DATA.lineage].forEach(([a, b]) => { DEG[a]++; DEG[b]++; });
  // role of a kind (D-058): core, connector, descriptive, technical, or none. It sizes the star, orders the names
  // and the Types list; Python decides it, the page only reads it
  const ROLE_ORDER = ['core', 'connector', 'descriptive', 'technical', null];   // Types list
  const NAME_ORDER = ['core', 'connector', null, 'descriptive', 'technical'];   // name priority
  const ROLE_STAR = { core: 1.35, descriptive: 0.75, technical: 0.75 };          // connector and none: 1
  const STAR_MAX = 14, STAR_MIN = 2.5;   // degree radius cap before the factor; floor after it (world px)
  const OVERVIEW_K = 0.6;                // = the `far` threshold of drawStar, routes and band markers
  const OVERVIEW_NAMES = 3;              // core names offered per constellation below OVERVIEW_K
  // folded tables (M8.2, D-062)
  const BADGE_H = 15, BADGE_MAX = 26;   // entity badge, screen px: height; widest (3 characters "99+")
  const BADGE_ARC = 2.5;                // below OVERVIEW_K the badge is a dark arc of this screen width on the star's north-east rim, no digits
  const ORBIT_GAP = 18;                 // world px between an entity's star and its first orbit
  const ORBIT_RING = 16, ORBIT_STEP = 16;  // most shown tables per orbit; world px between two orbits
  const ORBIT_ROOM = 10;                // world px added to a shown star's radius when spacing neighbours (room for ring + search mark)
  const FOLD_ROWS = 12, FOLD_HEAD = 15, TIP_FOLDED = 8;  // folded rows on a card; heading row height; folded names in a tooltip
  const KIND_LIST = 3;                  // kind labels written under the panel control before "+ N"
  const KIND = Object.fromEntries(DATA.kinds.map(k => [k.key, k]));
  const roleOf = n => KIND[n.kind].role ?? null;
  const HAS_CORE = DATA.kinds.some(k => k.role === 'core');
  const starR = n => Math.max(STAR_MIN, Math.min(STAR_MAX, 3 + 1.6 * Math.sqrt(DEG[n.i])) * (ROLE_STAR[roleOf(n)] ?? 1));
  // business relations of each table, both ends, whatever the Links selector says: ranks the main tables
  const RELN = new Array(N.length).fill(0);
  DATA.relations.forEach(([a, b]) => { RELN[a]++; RELN[b]++; });
  // the core tables of a constellation, the most related first (relations, then links of any kind, then name, then id)
  const mainTables = members => members.filter(n => roleOf(n) === 'core')
    .sort((a, b) => RELN[b.i] - RELN[a.i] || DEG[b.i] - DEG[a.i] || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0) || (a.id < b.id ? -1 : 1));
  let MAIN = new Map();   // table -> its rank in its constellation (0 = main), set by layout()
  // names compete for room on screen: by role, then (core) by rank in the constellation, then the most
  // connected tables, the kinds listed first in the config winning
  const KIND_RANK = Object.fromEntries(DATA.kinds.map((k, i) => [k.key, i]));
  const labelScore = n => (DEG[n.i] + 1) * (1 - 0.7 * KIND_RANK[n.kind] / Math.max(1, DATA.kinds.length - 1));
  const DOM = Object.fromEntries(DATA.domains.map(d => [d.key, d]));
  const LAYER = Object.fromEntries(DATA.layers.map((l, i) => [l.key, { ...l, rank: i }]));
  const counts = key => d3.rollup(N, v => v.length, n => n[key]);
  const COUNT = { domain: counts('domain'), layer: counts('layer'), kind: counts('kind') };
  // the viewer's last grouping, kept apart from the shared layout and never exported (D-048): stored only
  // when it differs from the page default; without storage the choice lasts for the session
  const byMemory = (() => {
    const key = 'dbtscope-constellations:' + PAGE.title;
    return {
      get() { try { const v = localStorage.getItem(key); return v === 'domains' || v === 'layers' ? v : null; } catch (e) { return null; } },
      set(value, fallback) {
        try { if (value === fallback) localStorage.removeItem(key); else localStorage.setItem(key, value); } catch (e) { /* session only */ }
      },
    };
  })();
  // the switch exists from two rows of the Layers list; below, the page stays in domains
  const CAN_BY = DATA.layers.length >= 2;
  const DEFAULT_BY = DATA.defaults.constellations === 'layers' ? 'layers' : 'domains';
  // the viewer's last fold choice, kept apart from the layout like the grouping and never exported (D-062)
  const foldMemory = (() => {
    const key = 'dbtscope-fold:' + PAGE.title;
    return {
      get() { try { const v = localStorage.getItem(key); return v === 'folded' ? true : v === 'shown' ? false : null; } catch (e) { return null; } },
      set(value, fallback) {
        try { if (value === fallback) localStorage.removeItem(key); else localStorage.setItem(key, value ? 'folded' : 'shown'); } catch (e) { /* session only */ }
      },
    };
  })();
  // the parent of each table (a node index, null for none): Python decides it, the page never guesses from names (D-061)
  const IDX = new Map(N.map(n => [n.id, n.i]));
  const PARENT = N.map(n => (n.parent == null ? null : IDX.get(n.parent) ?? null));
  const FOLDABLE = PARENT.some(p => p != null);
  const state = {
    domains: new Set(DATA.domains.map(d => d.key)),
    layers: new Set(DATA.layers.map(l => l.key)),
    kinds: new Set(DATA.kinds.map(k => k.key).filter(k => !DATA.defaults.hiddenKinds.includes(k))),
    links: DATA.defaults.links, detail: DATA.defaults.detail,
    by: CAN_BY ? byMemory.get() || DEFAULT_BY : 'domains',
    fold: FOLDABLE ? foldMemory.get() ?? DATA.defaults.fold : false,
  };
  const stage = $u('stage'), canvas = $u('canvas'), screenCtx = canvas.getContext('2d'), tip = $u('tip');
  let ctx = screenCtx;   // what the drawing helpers paint on: the screen, or an exported image during draw()
  const layoutCache = new Map();
  let P = [], B = [], REL = new Map(), labelHits = [], visible = [], edges = [], constellations = [], routes = [], tree = null;
  // folded tables (D-062): vis = filter-visible tables; drawn = visible minus folded; FOLDED = parent -> its visible folded
  // tables; foldedSet = those tables; SP / orbits = folded tables shown now, on an orbit round their entity (placeShown)
  let vis = new Set(), drawn = [], FOLDED = new Map(), foldedSet = new Set(), entityCount = 0;
  let SP = new Map(), orbits = [], ORBIT_R = new Map();   // ORBIT_R: entity -> { r, tall } its outer orbit and tallest shown star, world
  const posOf = i => P[i] || SP.get(i);
  let drawnNames = [];   // the tables whose names the last screen frame drew (test hook)
  let t = d3.zoomIdentity, hover = null, found = null, perf = { layout: 0, draw: 0, place: 0 };
  // trajectory mode: null = off, else { start, up, down, edges: [[child, parent, 'up'|'down']], brought }
  const trajOpts = { direction: 'both', depth: Infinity };   // kept across trajectories in the session
  const DEPTH = { d1: 1, d2: 2, d3: 3, dall: Infinity };
  let traj = null, layoutRuns = 0;   // layoutRuns: read by the test hook only
  const bar = $u('trajbar'), live = $u('tj-live');

  // ---------------------------------------------------------------- controls
  // a select of string keys, each labelled by the view's T or the shared L
  const options = (el, values, current) => fillSelect(el, values.map(v => [v, v in T ? T[v] : L[v]]), current);
  options($u('links'), ['relations', 'lineage', 'both'], state.links);
  options($u('detail'), ['names', 'keys', 'all'], state.detail);
  $u('links').onchange = ev => { state.links = ev.target.value; relayout(); };
  $u('detail').onchange = ev => { state.detail = ev.target.value; relayout(); };
  $u('h-links').textContent = T.links; $u('h-detail').textContent = T.detail;
  $u('h-by').textContent = T.by; $u('by-domains').textContent = T.domains; $u('by-layers').textContent = T.layers;
  $u('by-domains-n').textContent = num(DATA.domains.length); $u('by-layers-n').textContent = num(DATA.layers.length);
  $u('by').hidden = !CAN_BY;
  $u('by').querySelectorAll('input').forEach(radio => {
    radio.checked = radio.value === state.by;
    radio.onchange = () => { if (!radio.checked) return; state.by = radio.value; byMemory.set(state.by, DEFAULT_BY); relayout(); };
  });
  // the fold control (D-062): one checkbox, shown only when some table has a parent; its second line names the
  // descriptive kinds that fold here, as written in the config
  $u('fold').hidden = !FOLDABLE;
  const foldKinds = DATA.kinds.filter(k => k.role === 'descriptive' && N.some(n => n.kind === k.key && PARENT[n.i] != null)).map(labelOf);
  $u('fold-t').textContent = T.fold;
  $u('fold-kinds').textContent = foldKinds.slice(0, KIND_LIST).join(', ') + (foldKinds.length > KIND_LIST ? ` + ${num(foldKinds.length - KIND_LIST)}` : '');
  $u('fold-n').textContent = num(PARENT.filter(p => p != null).length);
  $u('fold').querySelector('label').title = T.foldTitle;
  $u('fold-on').checked = state.fold;
  const hintText = () => T.hint + (state.fold ? T.hintFold : '');
  $u('fold-on').onchange = ev => {
    state.fold = ev.target.checked; foldMemory.set(state.fold, DATA.defaults.fold);
    $u('hint').textContent = hintText();
    relayout();
    live.textContent = state.fold ? T.foldOn(entityCount) : T.foldOff;
  };
  $u('h-layers').textContent = T.layers; $u('h-kinds').textContent = L.kinds; $u('h-domains').textContent = T.domains;
  $u('all').textContent = T.every; $u('none').textContent = T.nothing;
  $u('fit').textContent = L.fit; $u('q').placeholder = T.search; $u('hint').textContent = hintText();

  function checkboxes(el, items, countOf, set, color, title) {
    el.replaceChildren(...items.map(it => filterRow(
      { label: labelOf(it), color: color && color(it), count: countOf.get(it.key) || 0, checked: set.has(it.key),
        title: title && title(it) },
      on => { on ? set.add(it.key) : set.delete(it.key); relayout(); })));
  }
  function refreshPanel() {
    checkboxes($u('layers'), DATA.layers, COUNT.layer, state.layers);
    const kinds = [...DATA.kinds].sort((a, b) => ROLE_ORDER.indexOf(a.role ?? null) - ROLE_ORDER.indexOf(b.role ?? null));
    checkboxes($u('kinds'), kinds, COUNT.kind, state.kinds, k => k.color,
      k => k.role ? `${T.role}${L.colon}${T.roles[k.role]}` : labelOf(k));
    checkboxes($u('domains'), DATA.domains, COUNT.domain, state.domains, d => d.color, d => d.owner ? `${T.owner}${L.colon}${d.owner}` : labelOf(d));
  }
  refreshPanel();
  $u('all').onclick = () => { DATA.domains.forEach(d => state.domains.add(d.key)); refreshPanel(); relayout(); };
  $u('none').onclick = () => { state.domains.clear(); refreshPanel(); relayout(); };
  sidePanel('u', () => { resize(); fit(false); });
  $u('export-h').textContent = L.exportImage;
  $u('export').textContent = L.png; $u('export').title = T.pngTitle;
  $u('export').onclick = () => EXPORT.save('universe', 'png', image, $u('export'));
  $u('fit').onclick = () => fit(true);
  $u('names').innerHTML = N.map(n => `<option value="${esc(n.name)}">`).join('');
  // a table by its exact name, case-insensitive (search box, Trajectory button)
  function findByName(text) { const q = String(text).trim().toLowerCase(); return N.find(n => n.name.toLowerCase() === q); }
  // tick back on the domain, layer and type of every listed table that is filtered out; recompute once
  // if anything changed; returns how many of the listed tables were hidden
  function reveal(indices) {
    let hidden = 0;
    indices.forEach(i => {
      if (vis.has(i)) return;
      const n = N[i]; hidden++;
      state.domains.add(n.domain); state.layers.add(n.layer); state.kinds.add(n.kind);
    });
    if (hidden) { refreshPanel(); relayout(); }
    return hidden;
  }
  $u('q').onchange = ev => {
    const n = findByName(ev.target.value);
    if (!n) return;
    reveal([n.i]);
    found = n.i;
    placeShown();   // a folded table is shown on an orbit round its entity, nothing is laid out again
    if (foldedSet.has(n.i)) live.textContent = T.foundFolded(n.name, N[PARENT[n.i]].name);
    const p = posOf(n.i);
    zoomTo(p.x, p.y, Math.max(t.k, 1.5));
    draw();
  };

  // ---------------------------------------------------------------- geometry
  // Each table reserves the room of what it shows: its star and name, or a card with keys / all fields.
  // oy: offset of the reserved box's centre from the table's point (the star centre). At names level the
  // box runs from the star top to the bottom of the label drawn below it (one or two lines, nameLines); the
  // label width is estimated (11 px, bold), never measured, so the placement does not depend on the fonts
  // installed (D-040).
  // An entity also reserves what marks its folded tables (D-062): at names level the room of its badge (sized by
  // BADGE_MAX, not by the digits, so a filter does not move it), on a card the list of its folded tables.
  function box(n) {
    const held = FOLDED.get(n.i) || [];
    if (state.detail === 'names') {
      const r = starR(n), lines = nameLines(n.name), longest = d3.max(lines, s => s.length);
      const b = { w: Math.max(6 + longest * 6.2, 2 * r + 4), h: 2 * r + 4 + LINE_H * lines.length, oy: LINE_H / 2 * lines.length };
      if (!held.length) return b;
      const e = Math.max(0, Math.ceil(0.71 * r + BADGE_H - (r + 2)));
      return { w: Math.max(b.w, 2 * (0.71 * r + BADGE_MAX)), h: b.h + e, oy: b.oy - e / 2 };
    }
    const rows = state.detail === 'keys' ? n.cols.filter(c => c[2]) : n.cols, shown = rows.slice(0, 30);
    const chars = Math.max(n.name.length * 1.15, ...shown.map(r => r[0].length + 1 + r[1].length * 0.8), 10,
      ...held.map(i => N[i].name.length + 1 + labelOf(KIND[N[i].kind]).length * 0.8));
    const top = 18 + shown.length * 11 + (rows.length > shown.length ? 11 : 0), listed = Math.min(held.length, FOLD_ROWS);
    const list = held.length ? FOLD_HEAD + 11 * listed + (held.length > FOLD_ROWS ? 11 : 0) : 0;
    return { w: 16 + chars * 5.6, h: top + list, oy: 0, shown, more: rows.length - shown.length, held, top };
  }

  // A table's name as drawn below its star: one line up to 14 characters, else two, split after the `__`
  // nearest the middle, else after the `_` nearest the middle (a name without `_` stays on one line)
  const LINE_H = 14;
  function nameLines(name) {
    if (name.length <= 14) return [name];
    const cut = sep => {
      let best = -1;
      for (let j = name.indexOf(sep); j > 0; j = name.indexOf(sep, j + 1)) {
        if (best < 0 || Math.abs(j + sep.length - name.length / 2) < Math.abs(best + sep.length - name.length / 2)) best = j;
      }
      return best < 0 || best + sep.length >= name.length ? -1 : best + sep.length;
    };
    const at = cut('__') > 0 ? cut('__') : cut('_');
    return at > 0 ? [name.slice(0, at), name.slice(at)] : [name];
  }

  // Pushes overlapping rectangles ({i, x, y, w, h, pinned}, centred on x, y) apart, in place. A pinned
  // (dragged) one never moves: the other takes the whole push; two free ones share it. Deterministic.
  function separate(rects, pad = 4) {
    const left = r => r.x - r.w / 2;
    for (let it = 0; it < 200; it++) {
      let moved = false;
      rects.sort((a, b) => left(a) - left(b) || a.i - b.i);
      for (let a = 0; a < rects.length; a++) {
        const A = rects[a], right = A.x + A.w / 2 + pad;
        for (let b = a + 1; b < rects.length; b++) {
          const Bn = rects[b];
          if (left(Bn) > right) break;
          if (A.pinned && Bn.pinned) continue;
          const ox = (A.w + Bn.w) / 2 + pad - Math.abs(A.x - Bn.x), oy = (A.h + Bn.h) / 2 + pad - Math.abs(A.y - Bn.y);
          if (ox <= 0 || oy <= 0) continue;
          moved = true;
          const axis = ox < oy ? 'x' : 'y', d = ox < oy ? ox : oy;
          const s = (A[axis] < Bn[axis] || (A[axis] === Bn[axis] && A.i < Bn.i) ? -1 : 1) * d;
          if (A.pinned) Bn[axis] -= s;
          else if (Bn.pinned) A[axis] += s;
          else { A[axis] += s / 2; Bn[axis] -= s / 2; }
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
    vis = new Set(visible.map(n => n.i));
    // a visible table is folded when its parent is visible and in its constellation (a layer differing from its
    // parent's keeps it a star, a filtered-out parent too); every count still holds the folded tables
    const G = grouping();
    FOLDED = new Map(); foldedSet = new Set();
    if (state.fold) {
      visible.forEach(n => {
        const p = PARENT[n.i];
        if (p == null || !vis.has(p) || G.of(N[p]) !== G.of(n)) return;
        foldedSet.add(n.i);
        if (!FOLDED.has(p)) FOLDED.set(p, []);
        FOLDED.get(p).push(n.i);   // N is sorted by name then id
      });
    }
    drawn = visible.filter(n => !foldedSet.has(n.i));
    entityCount = visible.filter(n => roleOf(n) === 'core' || roleOf(n) === 'connector').length;
    B = []; drawn.forEach(n => B[n.i] = box(n));
    const seen = new Set(); edges = [];
    const add = list => list.forEach(([a, b]) => {
      const key = a < b ? a + ',' + b : b + ',' + a;
      if (vis.has(a) && vis.has(b) && !seen.has(key)) { seen.add(key); edges.push([a, b]); }
    });
    if (state.links !== 'lineage') add(DATA.relations);
    if (state.links !== 'relations') add(DATA.lineage);

    const local = new Map(), whole = d3.group(visible, G.of);
    MAIN = new Map();
    for (const [key, members] of d3.group(drawn, G.of)) {
      mainTables(members).forEach((n, rank) => MAIN.set(n.i, rank));
      // a constellation's inner layout only depends on the grouping, its own tables, links, detail level and the
      // fold state: folded tables change an entity's box (its badge, its card)
      const held = members.filter(n => FOLDED.has(n.i)).map(n => `${n.i}:${FOLDED.get(n.i).join('.')}`).join(';');
      const cached = [state.by, key, state.detail, state.links, state.fold, members.map(n => n.i).join(','), held].join('|');
      if (!layoutCache.has(cached)) layoutCache.set(cached, layoutConstellation(key, members));
      local.set(key, layoutCache.get(cached));
    }

    // constellations: linked ones attract, ordered left to right along the flow, never overlapping
    const agg = new Map(), flow = new Map();
    edges.forEach(([a, b]) => {
      const da = G.of(N[a]), db = G.of(N[b]);
      if (da !== db) { const k = da < db ? da + '|' + db : db + '|' + da; agg.set(k, (agg.get(k) || 0) + 1); }
    });
    DATA.lineage.forEach(([child, parent]) => {  // data flows from parent to child
      if (!vis.has(child) || !vis.has(parent)) return;
      const from = G.of(N[parent]), to = G.of(N[child]);
      if (from === to) return;
      const k = from < to ? from + '|' + to : to + '|' + from;
      flow.set(k, (flow.get(k) || 0) + (from < to ? 1 : -1));
    });
    // manual arrangement: a moved table keeps its offset from its constellation's centre, a moved
    // constellation is pinned
    const saved = savedLayout();
    REL = new Map();
    for (const [, dl] of local) placeAroundDragged(dl.ns, saved.nodes);
    constellations = [...local].map(([k, v]) => ({ k, rank: v.rank, n: whole.get(k).length, bands: v.bands,
      r: Math.max(v.R, d3.max(v.ns, s => reach(s.i))),
      mix: [...d3.rollup([...v.ns.map(s => N[s.i]), ...whole.get(k).filter(n => foldedSet.has(n.i))], g => g.length, s => s.kind)]
        .sort((a, b) => b[1] - a[1]) }));
    constellations.forEach(d => { const p = saved[G.pins][d.k]; if (p) { d.fx = p[0]; d.fy = p[1]; } });
    routes = [...agg].map(([k, c]) => {
      const [a, b] = k.split('|'), f = flow.get(k) || 0;
      return { source: a, target: b, c, dir: Math.abs(f) > c * 0.2 ? Math.sign(f) : 0 };
    });
    const rand = d3.randomLcg(42), W = (d3.mean(constellations, d => d.r) || 1) * 2.4;
    const sim = d3.forceSimulation(constellations).randomSource(rand)
      // the padding leaves room for the domain name drawn above each constellation
      .force('collide', d3.forceCollide(d => d.r + 30 + d.r * 0.15).iterations(3))
      .force('link', d3.forceLink(routes).id(d => d.k).distance(l => l.source.r + l.target.r + 60)
        .strength(l => Math.min(0.4, 0.03 + Math.log1p(l.c) * 0.04)))
      .force('x', d3.forceX(d => d.rank * W).strength(G.flowX))
      .force('y', d3.forceY(0).strength(0.06))
      .force('charge', d3.forceManyBody().strength(-20))
      .stop();
    for (let k = 0; k < 400; k++) sim.tick();
    // settle with collisions only, so link forces can't leave constellations overlapping
    sim.force('link', null).force('x', null).force('y', null).force('charge', null);
    for (let k = 0; k < 100; k++) sim.tick();

    P = [];
    constellations.forEach(d => local.get(d.k).ns.forEach(s => { const [dx, dy] = REL.get(s.i); P[s.i] = { x: d.x + dx, y: d.y + dy }; }));
    tree = d3.quadtree(drawn, n => P[n.i].x, n => P[n.i].y);
    placeShown();
    perf.layout = performance.now() - t0;
  }

  // the saved arrangement of the current grouping and detail level: { <pins>: {key: [x, y]}, nodes: {id: [dx, dy]} }
  function savedLayout() {
    const G = grouping(), s = LAYOUT.get('universe', G.scope()) || {};
    return { ...s, [G.pins]: s[G.pins] || {}, nodes: s.nodes || {} };
  }
  // Room kept between a domain's farthest reserved box and its circle (world px), by detail level
  const margin = () => (state.detail === 'names' ? 16 : 24);
  // the domain radius that holds a table's reserved box b at offset (dx, dy) of its point from the centre
  const holds = (dx, dy, b) => Math.hypot(Math.abs(dx) + b.w / 2, Math.abs(dy + b.oy) + b.h / 2) + margin();
  // how far a table reaches from its domain's centre, so the halo still surrounds a table dragged outwards
  function reach(i) { const [dx, dy] = REL.get(i); return holds(dx, dy, B[i]); }
  // REL of a domain's tables: the computed offsets, a dragged table's saved one; computed tables under a
  // dragged one are pushed off it (the only rectangular pass: the packing never overlaps, D-040)
  function placeAroundDragged(ns, nodes) {
    const rects = ns.map(s => {
      const off = nodes[N[s.i].id], b = B[s.i], [x, y] = off || [s.x, s.y];
      return { i: s.i, x, y: y + b.oy, w: b.w, h: b.h, pinned: !!off };
    });
    if (rects.some(r => r.pinned)) separate(rects);
    rects.forEach(r => REL.set(r.i, r.pinned ? nodes[N[r.i].id] : [r.x, r.y - B[r.i].oy]));
  }

  // The catch-all layer of configured layers ('other', always last, domain/classify.OTHER): its tables have
  // no layer and are placed by lineage. Without configured layers no layer is the catch-all.
  const NO_LAYER = DATA.layers.length && DATA.layers[DATA.layers.length - 1].key === 'other' ? 'other' : null;
  const layerPos = n => (n.layer === NO_LAYER ? null : LAYER[n.layer].rank);
  const DOM_POS = Object.fromEntries(DATA.domains.map((d, i) => [d.key, i]));
  // What a constellation stands for (D-048): of, its key for a table; band, a table's band position (null:
  // no band, placed by lineage); bandKey, a band position's key; rank, the constellation's x target along
  // the flow; flowX, the strength of that target; pins, the key of saved centres; scope, the layout scope
  const BY = {
    domains: { of: n => n.domain, band: layerPos, bandKey: pos => DATA.layers[pos].key,
               rank: (key, members) => d3.mean(members, n => LAYER[n.layer].rank), flowX: 0.06,
               pins: 'domains', scope: () => state.detail },
    layers: { of: n => n.layer, band: n => DOM_POS[n.domain], bandKey: pos => DATA.domains[pos].key,
              rank: key => LAYER[key].rank, flowX: 0.3, pins: 'layers', scope: () => 'layers:' + state.detail },
  };
  const grouping = () => BY[state.by];
  const PACK = { PAD: 6, STRIP_GAP: 8, BAND_GAP: 20, TRIES: 24, REFINE: 6 };

  // A constellation's tables in bands, left to right (layer bands along the data flow, or domain bands in
  // the order of the Domains panel), in the smallest circle (D-040).
  // A band is one column, split into balanced columns when taller than a height H; H is scanned to give the
  // smallest circle around the reserved boxes. No simulation and no randomness: the same tables give the
  // same offsets on every machine.
  // -> { ns: [{i, x, y}] offsets of the star from the circle centre, R, rank, bands: [{key, n, x0, x1}] }; a band's n
  // counts tables: its drawn ones and those folded into them (same domain, so same band, in layer mode)
  function layoutConstellation(key, members) {
    const bands = bandsOf(members);
    const PAD = PACK.PAD;
    const items = bands.map(band => band.tables.map(n => { const b = box(n); return { i: n.i, w: b.w, h: b.h, oy: b.oy }; }));
    const all = items.flat(), stack = list => d3.sum(list, b => b.h) + PAD * (list.length - 1);
    const lo = d3.max(all, b => b.h), hi = Math.max(lo, d3.max(items, stack));
    let best = null;
    for (let k = 0; k <= PACK.TRIES; k++) {
      const row = packRow(items, items.map(() => lo * Math.pow(hi / lo, k / PACK.TRIES)), PAD);
      if (!best || row.r < best.r) best = row;
    }
    // then the bands near the edge are cut to the circle's chord there, which may shrink the circle again
    for (let k = 0; k < PACK.REFINE; k++) {
      const caps = best.bands.map(([x0, x1], j) =>
        Math.max(lo, Math.min(best.H[j], 2 * Math.sqrt(Math.max(0, best.r ** 2 - Math.max(x0 * x0, x1 * x1))))));
      const row = packRow(items, caps, PAD);
      if (row.r >= best.r) break;
      best = row;
    }
    const R = d3.max(all, (b, j) => holds(best.at[j].x, best.at[j].y - b.oy, b));
    return { ns: all.map((b, j) => ({ i: b.i, x: best.at[j].x, y: best.at[j].y - b.oy })), R,
             rank: grouping().rank(key, members),
             bands: bands.map((band, j) => ({ key: band.key, n: d3.sum(band.tables, n => 1 + (FOLDED.get(n.i) || []).length), x0: best.bands[j][0], x1: best.bands[j][1] })) };
  }
  // The bands of a constellation, ordered tables included: [{key, tables}] (see the M5.5 design note § 2).
  // In layer mode every table has a band (its domain), so the catch-all placement never applies.
  function bandsOf(members) {
    const { band, bandKey } = grouping();
    const ids = members.map(n => n.i), inDom = new Set(ids);
    // lineage that keeps bands apart: both ends in one band, or a child without a band
    const flowEdges = DATA.lineage.filter(([c, p]) => inDom.has(c) && inDom.has(p))
      .filter(([c, p]) => band(N[c]) === null || band(N[c]) === band(N[p])).map(([c, p]) => [p, c]);
    const { rank } = flowRanks(ids, flowEdges, i => band(N[i]));
    const byBand = d3.group(members.filter(n => band(n) !== null), band);
    const ranges = [...byBand.keys()].sort((a, b) => a - b)
      .map(pos => ({ key: bandKey(pos), lo: d3.min(byBand.get(pos), n => rank.get(n.i)),
                     hi: d3.max(byBand.get(pos), n => rank.get(n.i)), tables: [...byBand.get(pos)] }));
    if (!ranges.length) ranges.push({ key: NO_LAYER || members[0].layer, lo: 0, hi: Infinity, tables: [] });
    members.filter(n => band(n) === null).forEach(n => {
      const r = rank.get(n.i);
      (ranges.find(b => r >= b.lo && r <= b.hi) || ranges[ranges.length - 1]).tables.push(n);
    });
    // order inside a band: lineage depth, then barycentre of the neighbours in earlier bands, name, id;
    // neighbours over lineage and the drawn links, each pair counted once
    const nb = new Map(ids.map(i => [i, new Set()]));
    [...DATA.lineage, ...edges].forEach(([a, b]) => { if (a !== b && inDom.has(a) && inDom.has(b)) { nb.get(a).add(b); nb.get(b).add(a); } });
    const order = new Map();
    ranges.forEach(band => {
      const bary = new Map(band.tables.map(n => {
        const pos = [...nb.get(n.i)].filter(j => order.has(j)).map(j => order.get(j));
        return [n.i, pos.length ? d3.mean(pos) : 0.5];
      }));
      band.tables.sort((a, b) => rank.get(a.i) - rank.get(b.i) || bary.get(a.i) - bary.get(b.i)
        || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
      band.tables.forEach((n, j) => order.set(n.i, band.tables.length > 1 ? j / (band.tables.length - 1) : 0.5));
    });
    return ranges.map(b => ({ key: b.key, tables: b.tables }));
  }
  // Splits a band's boxes ([{h}], in order) into the fewest columns of stacked height <= H, balanced: the
  // smallest cap that keeps that number of columns, so no short column is left over. -> [[box]]
  function columns(items, H, PAD) {
    const fill = cap => {
      const cols = [];
      let h = Infinity;
      items.forEach(b => {
        if (h + PAD + b.h > cap + 1e-6) { cols.push([]); h = -PAD; }   // 1e-6: a cap equal to a stack still holds it
        cols[cols.length - 1].push(b); h += PAD + b.h;
      });
      return cols;
    };
    const target = fill(H).length;
    let lo = d3.max(items, b => b.h), hi = Math.max(lo, H);
    for (let k = 0; k < 16 && hi - lo > 0.5; k++) { const mid = (lo + hi) / 2; if (fill(mid).length <= target) hi = mid; else lo = mid; }
    return fill(hi);
  }
  // Lays the bands' boxes ([[{w, h}]], in order) out in one row: bands left to right, band j in columns of
  // height <= H[j] centred on y = 0, then moves the whole so the smallest circle around the box corners is
  // centred on (0, 0). -> { at: [{x, y}] box centres in the order of bands.flat(), bands: [[x0, x1]], r, H }
  function packRow(bands, H, PAD) {
    const cols = bands.map((items, j) => columns(items, H[j], PAD));
    const width = list => d3.max(list, b => b.w);
    const W = d3.sum(cols, band => d3.sum(band, width) + PACK.STRIP_GAP * (band.length - 1)) + PACK.BAND_GAP * (bands.length - 1);
    const at = [], ranges = [], corners = [];
    let x = -W / 2;
    cols.forEach((band, j) => {
      if (j) x += PACK.BAND_GAP;
      const start = x;
      band.forEach((col, m) => {
        if (m) x += PACK.STRIP_GAP;
        const w = width(col);
        let y = -(d3.sum(col, b => b.h) + PAD * (col.length - 1)) / 2;
        col.forEach(b => {
          at.push({ x: x + w / 2, y: y + b.h / 2 });
          const x0 = x + w / 2 - b.w / 2, x1 = x0 + b.w;
          corners.push({ x: x0, y, r: 0 }, { x: x1, y, r: 0 }, { x: x0, y: y + b.h, r: 0 }, { x: x1, y: y + b.h, r: 0 });
          y += b.h + PAD;
        });
        x += w;
      });
      ranges.push([start, x]);
    });
    const c = d3.packEnclose(corners);   // the smallest circle around them; d3 shuffles with a fixed seed: deterministic
    at.forEach(p => { p.x -= c.x; p.y -= c.y; });
    return { at, bands: ranges.map(([x0, x1]) => [x0 - c.x, x1 - c.x]), r: c.r, H };
  }

  // ---------------------------------------------------------------- drawing
  const C = { bg: THEME.bg, text: THEME.fg, muted: THEME.muted, card: '#ffffff', route: 'rgba(71,85,105,.22)',
              arrow: 'rgba(71,85,105,.55)', edge: 'rgba(100,116,139,.22)', cross: 'rgba(100,116,139,.10)', hl: 'rgba(31,41,51,.85)',
              ...TRAJ_COLORS };   // trajectory: upstream (dashed marks), downstream (solid marks)
  const DIM = 0.2, DIM_CTX = 0.45;   // trajectory mode: alpha of what is outside it, of constellations holding none of it
  // layer mode (D-048): a domain band's opaque tint (the page mixed with the domain's mark colour at 6 %), the
  // screen width of its arc on the rim, the screen gap between two arcs
  const TINTS = new Map();   // cached per colour, like CONTRAST: asked for every band in every frame
  function TINT(color) {
    if (!TINTS.has(color)) TINTS.set(color, d3.rgb(d3.interpolateRgb(C.bg, CONTRAST.edge(color, C.bg))(0.06)).formatHex());
    return TINTS.get(color);
  }
  const ARC_W = 4, ARC_GAP = 1;
  // layer mode: the constellation name, count and composition bar are raised by this many screen pixels, so
  // the bar ends 4 px above the outer edge of the rim arcs
  const NAME_LIFT = 8;
  const TIP_DOMAINS = 12;   // layer mode tooltip: the domains listed before "+ N"

  // on the tab, so the trajectory bar and the flow view (an overlay of the tab) both inherit them
  const tab = document.getElementById('tab-universe');
  tab.style.setProperty('--traj-up', C.up); tab.style.setProperty('--traj-down', C.down);
  const FONT = '"Segoe UI", Arial, sans-serif';

  // filled arrowhead at 55 % of the segment a -> b, pointing at b, in the current fill style
  function arrowHead(ax, ay, bx, by, size) {
    const ang = Math.atan2(by - ay, bx - ax), mx = ax + (bx - ax) * 0.55, my = ay + (by - ay) * 0.55;
    ctx.beginPath(); ctx.moveTo(mx + Math.cos(ang) * size, my + Math.sin(ang) * size);
    ctx.lineTo(mx + Math.cos(ang + 2.5) * size, my + Math.sin(ang + 2.5) * size);
    ctx.lineTo(mx + Math.cos(ang - 2.5) * size, my + Math.sin(ang - 2.5) * size); ctx.fill();
  }
  // side of a table in the trajectory: 'start' | 'up' | 'down' | null (a table in both maps is drawn as upstream)
  const sideOf = i => !traj ? null : i === traj.start ? 'start' : traj.up.has(i) ? 'up' : traj.down.has(i) ? 'down' : null;
  const trajMembers = () => traj ? [traj.start, ...traj.up.keys(), ...traj.down.keys()] : [];
  const trajDist = i => i === traj.start ? 0 : Math.min(traj.up.get(i) ?? Infinity, traj.down.get(i) ?? Infinity);

  // Draws the view on the screen, or on `target` (an exported image) at `scale` device pixels per CSS
  // pixel, over the same W x H area. Keep it synchronous: it swaps the closure's ctx until it returns.
  function draw(target = screenCtx, scale = window.devicePixelRatio || 1) {
    const onScreen = target === screenCtx;
    ctx = target;
    try { paint(onScreen, scale); } finally { ctx = screenCtx; }
  }
  function paint(onScreen, scale) {
    const t0 = performance.now(), k = t.k, W = stage.clientWidth, H = stage.clientHeight;
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
    if (onScreen) {
      $u('export').disabled = !visible.length;
      const groups = plural(constellations.length, state.by === 'layers' ? T.layersN : L.domainsN);
      const entities = state.fold ? ` · ${plural(entityCount, T.entitiesN)}` : '';
      $u('meta').textContent = `${plural(visible.length, L.tables)}${entities} · ${plural(edges.length, T.linksN)} · ${groups}`;
    }
    if (!visible.length) {
      ctx.fillStyle = C.muted; ctx.font = `14px ${FONT}`; ctx.fillText(L.empty, 24, 40);
      return;
    }
    const [x0, y0] = t.invert([0, 0]), [x1, y1] = t.invert([W, H]);
    const inView = (x, y, w, h) => x + w / 2 > x0 && x - w / 2 < x1 && y + h / 2 > y0 && y - h / 2 < y1;
    const screen = (x, y) => [x * k + t.x, y * k + t.y];
    // in the trajectory mode, constellations holding none of its drawn tables are context only
    const G = grouping(), byLayers = state.by === 'layers';
    const tdom = traj ? new Set(trajMembers().filter(i => posOf(i)).map(i => G.of(N[i]))) : null;
    const ctxAlpha = d => tdom && !tdom.has(d.k) ? DIM_CTX : 1;

    ctx.save(); ctx.translate(t.x, t.y); ctx.scale(k, k);
    constellations.forEach(d => {
      ctx.globalAlpha = ctxAlpha(d);
      if (byLayers) { drawDomainBands(d, k); return; }
      const c = CONTRAST.edge(DOM[d.k].color, C.bg), g = ctx.createRadialGradient(d.x, d.y, 0, d.x, d.y, d.r);   // 3:1 (D-042)
      g.addColorStop(0, c + '26'); g.addColorStop(1, c + '0a');
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(d.x, d.y, d.r, 0, 7); ctx.fill();
      ctx.strokeStyle = c + '66'; ctx.lineWidth = 1.5 / k; ctx.stroke();
    });
    if (k >= 0.6) constellations.forEach(d => { ctx.globalAlpha = ctxAlpha(d); drawBandMarkers(d, k); });
    ctx.globalAlpha = traj ? DIM : 1;

    if (k < 0.6) {  // from afar: one route per pair of constellations, arrowed along the data flow
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
      if (!P[a] || !P[b]) return;   // an end is folded into its entity: not drawn inside the constellation
      const hl = near && (a === hover || b === hover), cross = G.of(N[a]) !== G.of(N[b]);
      if (!hl && (k < 0.35 || (k < 0.6 && cross))) return;
      ctx.strokeStyle = hl ? C.hl : cross ? C.cross : C.edge;
      ctx.beginPath(); ctx.moveTo(P[a].x, P[a].y); ctx.lineTo(P[b].x, P[b].y); ctx.stroke();
    });

    const cards = state.detail !== 'names' && k > 0.35;
    const labels = [], badges = [];
    const drawTable = n => {
      const p = P[n.i], b = B[n.i]; if (!inView(p.x, p.y + b.oy, b.w, b.h)) return;
      const col = KIND[n.kind].color, mark = n.i === hover || n.i === found, side = sideOf(n.i);
      ctx.globalAlpha = traj ? (side ? 1 : DIM) : near && !near.has(n.i) ? 0.2 : 1;
      if (cards) drawCard(n, p, b, col, mark, side, k);
      else {
        drawStar(n, p, col, mark, side, k); labels.push(n);
        if (FOLDED.has(n.i)) badges.push([p, Math.max(starR(n), (side ? 3 : 2.5) / k), FOLDED.get(n.i).length, ctx.globalAlpha]);
      }
    };
    if (traj) {  // trajectory tables after its edges, so arrows never cover them
      drawn.forEach(n => { if (!sideOf(n.i)) drawTable(n); });
      ctx.globalAlpha = 1;
      drawTrajectoryEdges(k);
      drawn.forEach(n => { if (sideOf(n.i)) drawTable(n); });
    } else drawn.forEach(drawTable);
    badges.forEach(b => { ctx.globalAlpha = b[3]; drawBadge(...b.slice(0, 3), k); });
    ctx.globalAlpha = 1;
    if (SP.size) drawOrbits(k);
    ctx.restore();

    // screen-space text: constellation names first, then band names (layer mode), then table names by
    // importance, skipping any that would overlap
    const taken = [], hits = [];
    const free = (x, y, w, h) => !taken.some(r => x < r[0] + r[2] && x + w > r[0] && y < r[1] + r[3] && y + h > r[1]);
    ctx.textAlign = 'center';
    constellations.forEach(d => {
      const [sx, rim] = screen(d.x, d.y - d.r), fs = Math.max(13, Math.min(20, 10 + d.r * k / 25));
      const sy = rim - (byLayers ? NAME_LIFT : 0);
      const name = constellationLabel(d.k);
      ctx.globalAlpha = ctxAlpha(d);
      // a domain name in its colour, readable on the page (D-037); a layer name in the text colour
      ctx.font = `600 ${fs}px ${FONT}`; ctx.fillStyle = byLayers ? C.text : CONTRAST.ink(DOM[d.k].color, C.bg);
      ctx.fillText(name, sx, sy - 22);
      const w = Math.max(ctx.measureText(name).width, 80) + 8;
      ctx.font = `12px ${FONT}`; ctx.fillStyle = C.muted;
      ctx.fillText(plural(d.n, L.tables), sx, sy - 8);
      // composition by type, readable before any single star is
      let bx = sx - 40;
      d.mix.forEach(([kind, c]) => { const bw = 80 * c / d.n; ctx.fillStyle = CONTRAST.edge(KIND[kind].color, C.bg); ctx.fillRect(bx, sy - 4, bw, 4); bx += bw; });
      taken.push([sx - w / 2, sy - 22 - fs, w, fs + 22]);
      hits.push({ d, x: sx - w / 2, y: sy - 22 - fs, w, h: fs + 22 });
    });
    // a badge's pill is an obstacle for every name below: its number is never hidden (the far arc has no digits and
    // is no obstacle: from afar names are rare and the arc is a mark on the star's rim)
    if (k >= OVERVIEW_K) badges.forEach(([p, r, held]) => {
      const [bx, by] = screen(p.x + 0.71 * r, p.y - 0.71 * r);
      taken.push([bx, by - BADGE_H, badgeWidth(held), BADGE_H]);
    });
    if (byLayers && k >= 0.6) constellations.forEach(d => { ctx.globalAlpha = ctxAlpha(d); drawBandNames(d, screen, free, taken, k); });
    ctx.globalAlpha = 1;
    const around = SP.size ? drawShownNames(screen, taken, k) : [];
    const named = [...around, ...(cards ? [] : drawNames(orderLabels(labels, k), screen, free, taken, k))];
    ctx.textAlign = 'left';
    if (!onScreen) return;
    drawnNames = named;
    labelHits = hits;
    perf.draw = performance.now() - t0;
  }
  // the view as shown (filters, zoom, detail level, search mark, trajectory) as a PNG at 2 x the screen
  // resolution; hover is pointer state, like the tooltip, so it is left out. null when nothing is drawn.
  function image() {
    if (!visible.length) return null;
    const W = stage.clientWidth, H = stage.clientHeight, s = EXPORT.scale(W, H), c = document.createElement('canvas');
    c.width = Math.round(W * s); c.height = Math.round(H * s);
    const pointer = hover;
    hover = null;
    try { draw(c.getContext('2d'), s); } finally { hover = pointer; }
    return EXPORT.png(c);
  }

  // the layer markers of a domain: a faint line in the middle of each gap between two bands, clipped to the disc
  function drawBandMarkers(d, k) {
    ctx.strokeStyle = C.cross; ctx.lineWidth = 1 / k;
    bandSpans(d).slice(1).forEach(({ s0 }) => {
      const half = rimHalf(d, s0);
      ctx.beginPath(); ctx.moveTo(d.x + s0, d.y - half); ctx.lineTo(d.x + s0, d.y + half); ctx.stroke();
    });
  }
  // the labels of a domain's layer bands, in flow order (its tooltip)
  const bandLabels = d => d.bands.map(b => labelOf(LAYER[b.key])).join(' → ');
  // a constellation's name: its domain's, or its layer's
  const constellationLabel = key => labelOf(state.by === 'layers' ? LAYER[key] : DOM[key]);
  // the horizontal span of each band of d, relative to its centre: from the midpoint with the previous band
  // (the disc's left edge for the first) to the midpoint with the next (the right edge for the last)
  const bandSpans = d => d.bands.map((b, j) => ({ ...b,
    s0: j ? (d.bands[j - 1].x1 + b.x0) / 2 : -d.r, s1: j < d.bands.length - 1 ? (b.x1 + d.bands[j + 1].x0) / 2 : d.r }));
  // the angle of the disc's upper rim above x (relative to the centre), from -π (left) to 0 (right)
  const rimAngle = (d, x) => -Math.acos(Math.max(-1, Math.min(1, x / d.r)));
  // the half-height of the disc above x (relative to the centre): the rim is at d.y ± rimHalf(d, x)
  const rimHalf = (d, x) => Math.sqrt(Math.max(0, d.r * d.r - x * x));
  // Layer mode (D-048): each domain band tinted in its domain colour, clipped to the disc, and marked by an
  // arc of the upper rim in the domain's mark colour (3:1, D-042), at every zoom; then the neutral outline
  function drawDomainBands(d, k) {
    const spans = bandSpans(d);
    ctx.save(); ctx.beginPath(); ctx.arc(d.x, d.y, d.r, 0, 7); ctx.clip();
    spans.forEach(b => { ctx.fillStyle = TINT(DOM[b.key].color); ctx.fillRect(d.x + b.s0, d.y - d.r, b.s1 - b.s0, 2 * d.r); });
    ctx.restore();
    ctx.strokeStyle = C.muted + '66'; ctx.lineWidth = 1.5 / k;
    ctx.beginPath(); ctx.arc(d.x, d.y, d.r, 0, 7); ctx.stroke();
    const gap = ARC_GAP / 2 / k / d.r;
    ctx.lineWidth = ARC_W / k; ctx.lineCap = 'butt';
    spans.forEach((b, j) => {
      const a0 = rimAngle(d, b.s0) + (j ? gap : 0), a1 = rimAngle(d, b.s1) - (j < spans.length - 1 ? gap : 0);
      if (a1 <= a0) return;
      ctx.strokeStyle = CONTRAST.edge(DOM[b.key].color, C.bg);
      ctx.beginPath(); ctx.arc(d.x, d.y, d.r, a0, a1); ctx.stroke();
    });
  }
  // Layer mode at constellation zoom: each band's domain name, 14 px below its arc, in its colour readable on
  // its tint (D-037); skipped when wider than the band or overlapping a name already drawn
  function drawBandNames(d, screen, free, taken, k) {
    ctx.font = `600 11px ${FONT}`;
    bandSpans(d).forEach(b => {
      const dom = DOM[b.key], name = labelOf(dom), cx = (b.s0 + b.s1) / 2, w = ctx.measureText(name).width + 6, h = LINE_H;
      if (w > (b.s1 - b.s0) * k) return;
      const [sx, sy] = screen(d.x + cx, d.y - rimHalf(d, cx));
      const x = sx - w / 2, y = sy + 14;
      if (!free(x, y, w, h)) return;
      taken.push([x, y, w, h]);
      ctx.fillStyle = CONTRAST.ink(dom.color, TINT(dom.color));
      ctx.fillText(name, sx, y + 11);
    });
  }

  // names by priority: in the trajectory mode its tables first (start, then by distance), then the hovered one,
  // then by role (NAME_ORDER; core by rank in its constellation, then by score). Below OVERVIEW_K, on a page
  // with a core kind, an ordinary name is offered only for the first OVERVIEW_NAMES core tables of a constellation.
  function orderLabels(labels, k) {
    const rank = n => NAME_ORDER.indexOf(roleOf(n)), main = n => MAIN.get(n.i) ?? Infinity;
    const overview = HAS_CORE && k < OVERVIEW_K;
    const rest = labels.filter(n => !sideOf(n.i) && (!overview || (roleOf(n) === 'core' && main(n) < OVERVIEW_NAMES)))
      .sort((a, b) => rank(a) - rank(b) || (roleOf(a) === 'core' ? main(a) - main(b) : 0) || labelScore(b) - labelScore(a));
    const onScreen = new Set(labels.map(n => n.i));
    const hov = [...new Set([...(hover != null && P[hover] ? [hover] : []), ...[...ORBIT_R.keys()].filter(i => P[i] && onScreen.has(i))])].map(i => N[i]);   // a shown table's name is drawn anyway
    if (!traj) return [...hov, ...rest];
    const inT = labels.filter(n => sideOf(n.i)).sort((a, b) => trajDist(a.i) - trajDist(b.i));
    return [...inT, ...hov, ...rest];
  }
  // Table names below their stars, in one or two lines (nameLines), each over a light backdrop, skipping any
  // that would overlap a name already drawn or a domain name. An ordinary name is also skipped when it would
  // cover another star or leave its domain's circle (semantic zoom: names are 11 px whatever the zoom, so
  // from afar only the room around a star decides); trajectory and hovered names always compete.
  function drawNames(labels, screen, free, taken, k) {
    const at = new Map(labels.map(n => [n.i, screen(P[n.i].x, P[n.i].y)]));
    const rad = n => Math.max(starR(n) * k, 2.5), rMax = Math.max(STAR_MAX * ROLE_STAR.core * k, 2.5);
    const stars = d3.quadtree(labels, n => at.get(n.i)[0], n => at.get(n.i)[1]);
    const disc = new Map(constellations.map(d => [d.k, [...screen(d.x, d.y), d.r * k]]));
    const coversStar = (x, y, w, h) => {
      let hit = false;
      stars.visit((q, x0, y0, x1, y1) => {
        if (hit || x0 > x + w + rMax || x1 < x - rMax || y0 > y + h + rMax || y1 < y - rMax) return true;
        for (let leaf = q.length ? null : q; leaf; leaf = leaf.next) {
          const [cx, cy] = at.get(leaf.data.i), r = rad(leaf.data);
          if (cx + r > x && cx - r < x + w && cy + r > y && cy - r < y + h) hit = true;
        }
        return hit;
      });
      return hit;
    };
    const inDisc = (n, x, y, w, h) => {
      const [cx, cy, r] = disc.get(grouping().of(n));
      return [[x, y], [x + w, y], [x, y + h], [x + w, y + h]].every(([px, py]) => Math.hypot(px - cx, py - cy) <= r);
    };
    // below its star, or, while its folded tables are on an orbit, below the orbit, their stars and their names
    const below = n => {
      const o = ORBIT_R.get(n.i);
      return o ? o.r * k + Math.max(o.tall * k, 3) + 6 + LINE_H : rad(n);
    };
    const drawn = [];
    for (const n of labels) {
      if (drawn.length >= 400) break;
      const side = sideOf(n.i);
      const strong = side ? trajDist(n.i) <= 1 : labelScore(n) >= 10 || n.i === hover || ORBIT_R.has(n.i);
      ctx.font = `${strong ? 600 : 400} 11px ${FONT}`;
      const [sx, sy] = at.get(n.i), lines = nameLines(n.name);
      const w = d3.max(lines, s => ctx.measureText(s).width) + 6, h = LINE_H * lines.length, x = sx - w / 2, y = sy + below(n) + 2;
      if (!free(x, y, w, h)) continue;
      if (!side && n.i !== hover && !ORBIT_R.has(n.i) && (coversStar(x, y, w, h) || !inDisc(n, x, y, w, h))) continue;
      taken.push([x, y, w, h]); drawn.push(n.i);
      ctx.globalAlpha = traj && !side ? DIM : 1;
      ctx.fillStyle = 'rgba(245,246,248,.85)'; ctx.fillRect(x, y, w, h);
      ctx.fillStyle = strong || side ? C.text : C.muted;
      lines.forEach((s, j) => ctx.fillText(s, sx, y + 11 + LINE_H * j));
    }
    ctx.globalAlpha = 1;
    return drawn;
  }
  // a ring around a star: dashed for upstream, as on the legend
  function ring(p, r, color, width, dashed, k) {
    ctx.strokeStyle = color; ctx.lineWidth = width;
    ctx.setLineDash(dashed ? [5 / k, 3 / k] : []);
    ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, 7); ctx.stroke();
    ctx.setLineDash([]);
  }
  function drawStar(n, p, col, mark, side, k) {
    const far = k < OVERVIEW_K, r = Math.max(starR(n), (side ? 3 : 2.5) / k);
    const edge = CONTRAST.edge(col, C.bg);   // a star too light for the page is outlined (D-042)
    ctx.fillStyle = col; ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, 7); ctx.fill();
    ctx.strokeStyle = edge === col ? '#ffffff' : edge; ctx.lineWidth = 1 / k; ctx.stroke();
    if (side === 'start') { ring(p, r + 3 / k, C.text, 1.5 / k, false, k); ring(p, r + 6 / k, C.text, 1.5 / k, false, k); return; }
    let out = 4 / k;
    if (side) { out = (far ? 3 : 4) / k; ring(p, r + out, C[side], (far ? 1.5 : 2) / k, side === 'up', k); out += 3 / k; }
    if (mark) ring(p, r + out, C.text, 2 / k, false, k);
  }
  function drawCard(n, p, b, col, mark, side, k) {
    const x = p.x - b.w / 2, y = p.y - b.h / 2, mk = Math.min(k, 1), edge = CONTRAST.edge(col, C.bg);   // D-042
    ctx.fillStyle = C.card; ctx.fillRect(x, y, b.w, b.h);
    ctx.strokeStyle = side === 'start' ? C.text : side ? C[side] : mark ? C.text : edge;
    ctx.lineWidth = (side === 'start' ? 3 : side ? 2.5 : mark ? 2.5 : 1) / mk;
    ctx.setLineDash(side === 'up' ? [6 / mk, 3 / mk] : []);
    ctx.strokeRect(x, y, b.w, b.h);
    ctx.setLineDash([]);
    if (side === 'start' || (side && mark)) {  // outer rectangle 3 px outside
      const o = 3 / k + ctx.lineWidth / 2;
      ctx.strokeStyle = C.text; ctx.lineWidth = 1.5 / mk; ctx.strokeRect(x - o, y - o, b.w + 2 * o, b.h + 2 * o);
    }
    ctx.fillStyle = col; ctx.fillRect(x, y, b.w, 16);
    if (edge !== col) { ctx.strokeStyle = edge; ctx.lineWidth = 1 / mk; ctx.strokeRect(x, y, b.w, 16); }
    if (k > 0.6) {
      ctx.fillStyle = CONTRAST.textOn(col); ctx.font = `600 10px ${FONT}`; ctx.fillText(n.name, x + 5, y + 12);
      ctx.font = `9px ${FONT}`;
      b.shown.forEach((r, j) => {
        ctx.fillStyle = r[2] ? C.text : C.muted; ctx.fillText(r[0], x + 5, y + 28 + j * 11);
        ctx.fillStyle = C.muted; ctx.fillText(r[1], x + b.w - 5 - ctx.measureText(r[1]).width, y + 28 + j * 11);
      });
      if (b.more > 0) { ctx.fillStyle = C.muted; ctx.fillText(`+ ${num(b.more)}`, x + 5, y + 28 + b.shown.length * 11); }
    }
    if (b.held.length) drawFolded(b, x, y, k);
  }
  // the folded tables of an entity on its card, under its columns: a separator, a heading, then a kind dot, name and
  // kind per table (FOLD_ROWS rows, then "+ N"); below scale 0.6 only the separator is drawn
  function drawFolded(b, x, y, k) {
    const top = y + b.top;
    ctx.strokeStyle = C.edge; ctx.lineWidth = 1 / Math.min(k, 1);
    ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x + b.w, top); ctx.stroke();
    if (k <= 0.6) return;
    ctx.fillStyle = C.text; ctx.font = `600 9px ${FONT}`; ctx.fillText(plural(b.held.length, T.foldedN), x + 5, top + 11);
    ctx.font = `9px ${FONT}`;
    b.held.slice(0, FOLD_ROWS).forEach((i, j) => {
      const n = N[i], col = KIND[n.kind].color, edge = CONTRAST.edge(col, C.bg), base = top + FOLD_HEAD + 9 + j * 11, label = labelOf(KIND[n.kind]);
      ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x + 8, base - 3, 2.5, 0, 7); ctx.fill();
      if (edge !== col) { ctx.strokeStyle = edge; ctx.lineWidth = 1 / k; ctx.stroke(); }
      ctx.fillStyle = C.text; ctx.fillText(n.name, x + 14, base);
      ctx.fillStyle = C.muted; ctx.fillText(label, x + b.w - 5 - ctx.measureText(label).width, base);
    });
    if (b.held.length > FOLD_ROWS) { ctx.fillStyle = C.muted; ctx.fillText(`+ ${num(b.held.length - FOLD_ROWS)}`, x + 5, top + FOLD_HEAD + 9 + FOLD_ROWS * 11); }
  }
  // the count badge of an entity (names level): a dark pill with the number at the upper right of its star, sized in
  // screen pixels; from afar a short dark arc on the star's north-east rim, so the star's colour stays visible.
  // r is the drawn radius of the star.
  const badgeWidth = held => Math.max(15, 8 + 6 * (held > 99 ? '99+' : num(held)).length);   // screen px
  function drawBadge(p, r, held, k) {
    const ax = p.x + 0.71 * r, ay = p.y - 0.71 * r;
    if (k < OVERVIEW_K) {
      ctx.strokeStyle = C.text; ctx.lineWidth = BADGE_ARC / k; ctx.lineCap = 'round';
      ctx.beginPath(); ctx.arc(p.x, p.y, r, -1.4, -0.2); ctx.stroke();
      ctx.lineCap = 'butt';
      return;
    }
    ctx.fillStyle = C.text; ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1 / k;
    const text = held > 99 ? '99+' : num(held), w = badgeWidth(held) / k, h = BADGE_H / k, rad = h / 2, y = ay - h;
    ctx.beginPath(); ctx.moveTo(ax + rad, y); ctx.lineTo(ax + w - rad, y); ctx.arc(ax + w - rad, y + rad, rad, -Math.PI / 2, Math.PI / 2);
    ctx.lineTo(ax + rad, y + h); ctx.arc(ax + rad, y + rad, rad, Math.PI / 2, Math.PI * 1.5); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#ffffff'; ctx.font = `700 ${10 / k}px ${FONT}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(text, ax + w / 2, y + h / 2 + 0.5 / k);
    ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
  }
  // the folded tables shown now (search, trajectory): a dashed orbit round each entity, then its tables on it, each
  // over a white halo, above everything else
  function drawOrbits(k) {
    ctx.save(); ctx.strokeStyle = C.muted; ctx.globalAlpha = 0.6; ctx.lineWidth = 1 / k; ctx.setLineDash([3 / k, 3 / k]);
    orbits.forEach(o => { ctx.beginPath(); ctx.arc(o.x, o.y, o.r, 0, 7); ctx.stroke(); });
    ctx.restore();
    SP.forEach((p, i) => {
      const n = N[i], side = sideOf(i), r = Math.max(starR(n), (side ? 3 : 2.5) / k);
      ctx.globalAlpha = traj && !side ? DIM : 1;
      ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.arc(p.x, p.y, r + 2 / k, 0, 7); ctx.fill();
      drawStar(n, p, KIND[n.kind].color, i === hover || i === found, side, k);
    });
    ctx.globalAlpha = 1;
  }
  // the names of the shown tables, outside their orbit along the radial direction (right half left-aligned, left half
  // right-aligned, near the vertical centred), over a white stroke; they never yield to another name. -> their indices
  function drawShownNames(screen, taken, k) {
    const out = [], vertical = Math.sin(20 * Math.PI / 180);
    SP.forEach((p, i) => {
      const n = N[i], [sx, sy] = screen(p.x, p.y), gap = Math.max(starR(n) * k, 3) + 4 + 2;
      const cos = Math.cos(p.a), sin = Math.sin(p.a), ax = sx + cos * gap, ay = sy + sin * gap;
      ctx.font = `${i === found ? 600 : 400} 11px ${FONT}`;
      const w = ctx.measureText(n.name).width + 6, h = LINE_H - 2;
      const x = Math.abs(cos) <= vertical ? ax - w / 2 : cos > 0 ? ax : ax - w, y = Math.abs(cos) <= vertical ? (sin < 0 ? ay - h : ay) : ay - h / 2;
      taken.push([x, y, w, h]); out.push(i);
      ctx.globalAlpha = traj && !sideOf(i) ? DIM : 1;
      ctx.textAlign = 'left'; ctx.lineJoin = 'round'; ctx.lineWidth = 3; ctx.strokeStyle = '#ffffff';
      ctx.strokeText(n.name, x + 3, y + 10); ctx.fillStyle = C.text; ctx.fillText(n.name, x + 3, y + 10);
      ctx.lineJoin = 'miter'; ctx.textAlign = 'center';
    });
    ctx.globalAlpha = 1;
    return out;
  }
  // the lineage edges of the trajectory, parent -> child, at every zoom and whatever the Links selector shows
  function drawTrajectoryEdges(k) {
    const far = k < 0.6, lw = (far ? 1.5 : 2) / k, head = (far ? 7 : 8) / k;
    traj.edges.forEach(([c, p, dir]) => {
      const a = posOf(p), b = posOf(c);
      if (!a || !b) return;   // hidden by a filter changed in the mode
      ctx.strokeStyle = C[dir]; ctx.fillStyle = C[dir]; ctx.lineWidth = lw;
      ctx.setLineDash(dir === 'up' ? [5 / k, 3 / k] : []);
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      ctx.setLineDash([]);
      if (!far || Math.hypot(b.x - a.x, b.y - a.y) * k >= 24) arrowHead(a.x, a.y, b.x, b.y, head);
    });
  }

  // ---------------------------------------------------------------- navigation
  const zoom = d3.zoom().scaleExtent(ZOOM_EXTENT).on('zoom', ev => { t = ev.transform; draw(); });
  // mouse only: on touch every finger goes to the zoom, so a pinch starting on a table or a domain name
  // zooms and a one-finger drag pans, as in the detail (a touch drag cannot hand a finger over to a pinch)
  const drag = d3.drag().container(canvas).touchable(false).filter(ev => !ev.button)
    .subject(ev => {
      const [wx, wy] = t.invert([ev.x, ev.y]);
      if (t.k >= FAR && pickShown(wx, wy)) return null;   // a shown (orbit) table is not draggable: the pointer pans
      const n = t.k >= FAR ? pickAt(wx, wy) : null;
      if (n) return { n, x: ev.x, y: ev.y };
      const hit = labelAt(ev.x, ev.y);
      return hit ? { d: hit.d, x: ev.x, y: ev.y } : null;
    })
    .on('start', ev => { ev.subject.moved = false; tip.style.display = 'none'; canvas.style.cursor = 'grabbing'; })
    .on('drag', ev => {
      const dx = ev.dx / t.k, dy = ev.dy / t.k, s = ev.subject;
      s.moved = true;
      if (s.n) { P[s.n.i].x += dx; P[s.n.i].y += dy; }
      else { s.d.x += dx; s.d.y += dy; drawn.forEach(n => { if (grouping().of(n) === s.d.k) { P[n.i].x += dx; P[n.i].y += dy; } }); }
      if (SP.size) placeShown();   // the orbits follow their entity
      draw();
    })
    .on('end', ev => {
      const s = ev.subject;
      canvas.style.cursor = '';
      if (!s.moved) return;
      const G = grouping(), saved = savedLayout();
      if (s.n) {
        const d = constellations.find(d => d.k === G.of(s.n));
        REL.set(s.n.i, [P[s.n.i].x - d.x, P[s.n.i].y - d.y]);
        saved.nodes[s.n.id] = REL.get(s.n.i);
        d.r = Math.max(d.r, reach(s.n.i));
      }
      // pin every constellation where it stands, so recomputing the layout later doesn't move the others
      constellations.forEach(d => saved[G.pins][d.k] = [d.x, d.y]);
      LAYOUT.set('universe', G.scope(), saved);
      tree = d3.quadtree(drawn, n => P[n.i].x, n => P[n.i].y);
      draw();
    });
  const sel = zoomOn(d3.select(canvas).call(drag), zoom);
  // room kept free at the top of the canvas: the trajectory bar overlays it while the mode is on
  const top = () => traj ? bar.offsetHeight : 0;
  // frame a world-space box, at most at scale kMax
  function frame(bx0, by0, bx1, by1, animate, kMax = Infinity) {
    // constellation names sit above the halos at a fixed screen size: keep that strip free at the top
    const NAME = 46, top0 = top(), w = stage.clientWidth, h = stage.clientHeight - top0 - NAME;
    const k = Math.min(kMax, 0.95 * Math.min(w / (bx1 - bx0), h / (by1 - by0)));
    const tr = d3.zoomIdentity.translate(w / 2, top0 + NAME + h / 2).scale(k).translate(-(bx0 + bx1) / 2, -(by0 + by1) / 2);
    (animate ? sel.transition().duration(500) : sel).call(zoom.transform, tr);
  }
  // the whole universe, or the drawn tables of the trajectory while the mode is on
  function fit(animate) {
    const tj = trajMembers().filter(i => posOf(i));
    if (tj.length) {
      return frame(d3.min(tj, i => posOf(i).x - boxOf(i).w / 2), d3.min(tj, i => posOf(i).y + boxOf(i).oy - boxOf(i).h / 2),
        d3.max(tj, i => posOf(i).x + boxOf(i).w / 2), d3.max(tj, i => posOf(i).y + boxOf(i).oy + boxOf(i).h / 2), animate, 2);
    }
    if (!constellations.length) return draw();
    frame(d3.min(constellations, d => d.x - d.r), d3.min(constellations, d => d.y - d.r),
      d3.max(constellations, d => d.x + d.r), d3.max(constellations, d => d.y + d.r), animate);
  }
  function zoomTo(x, y, k) {
    const top0 = top(), w = stage.clientWidth, h = stage.clientHeight - top0;
    sel.transition().duration(600).call(zoom.transform, d3.zoomIdentity.translate(w / 2, top0 + h / 2).scale(k).translate(-x, -y));
  }
  const pick = ev => pickAt(...t.invert(d3.pointer(ev, canvas)));
  // the shown (orbit) table nearest to a world point, if one is within reach
  function pickShown(wx, wy) {
    let best = null, near = Math.max(8, 8 / t.k);
    SP.forEach((p, i) => { const d = Math.hypot(wx - p.x, wy - p.y); if (d <= near) { best = N[i]; near = d; } });
    return best;
  }
  // a shown table wins over the table at rest under it
  function pickAt(wx, wy) {
    const over = pickShown(wx, wy);
    if (over) return over;
    if (!tree) return null;
    const n = tree.find(wx, wy, Math.max(200, 12 / t.k));
    if (!n) return null;
    const p = P[n.i], b = B[n.i];
    const hit = state.detail !== 'names' && t.k > 0.35
      ? Math.abs(wx - p.x) <= b.w / 2 && Math.abs(wy - p.y) <= b.h / 2
      : Math.hypot(wx - p.x, wy - p.y) <= Math.max(8, 8 / t.k);
    return hit ? n : null;
  }
  // the constellation name under a screen point, if any
  const labelAt = (x, y) => labelHits.find(h => x >= h.x && x <= h.x + h.w && y >= h.y && y <= h.y + h.h);
  // the constellation under the pointer, if any
  function domainAt(ev) {
    const [wx, wy] = t.invert(d3.pointer(ev, canvas));
    return constellations.find(d => Math.hypot(wx - d.x, wy - d.y) < d.r);
  }
  // Layer mode tooltip of a constellation (D-048): its domains in band order (first TIP_DOMAINS, then "+ N"), and the
  // band under the world x `wx`, if any
  function layerTip(d, wx) {
    const names = d.bands.slice(0, TIP_DOMAINS).map(b => esc(labelOf(DOM[b.key]))).join(' · ');
    const more = d.bands.length > TIP_DOMAINS ? ` · + ${num(d.bands.length - TIP_DOMAINS)}` : '';
    const band = bandSpans(d).find(b => wx - d.x >= b.s0 && wx - d.x <= b.s1);
    return `<b>${esc(constellationLabel(d.k))}</b><div class="m">${plural(d.n, L.tables)}</div>`
      + `<div class="m">${T.domains}${L.colon}${names}${more}</div>`
      + (band ? `<div class="m">${T.domainOne}${L.colon}${esc(labelOf(DOM[band.key]))} · ${plural(band.n, L.tables)}</div>` : '')
      + `<div class="a">${T.frameC}</div>`;
  }
  // the fold lines of a table's tooltip: an entity lists its folded tables (name, kind; TIP_FOLDED, then "+ N"); a table with
  // a parent names it, and says why it is not folded when it is a star at rest while the page folds
  function foldTip(n) {
    const held = FOLDED.get(n.i) || [], p = PARENT[n.i];
    let text = '';
    if (p != null) {
      const why = !state.fold || SP.has(n.i) ? '' : !vis.has(p) ? T.entityHidden : T.entityLayer;
      text += `<div class="m">${T.entity}${L.colon}${esc(N[p].name)}${why}</div>`;
    }
    if (!held.length) return text;
    text += `<div class="m"><b>${plural(held.length, T.foldedN)}</b></div>`
      + held.slice(0, TIP_FOLDED).map(i => `<div class="m">${esc(N[i].name)} · ${esc(labelOf(KIND[N[i].kind]))}</div>`).join('');
    return text + (held.length > TIP_FOLDED ? `<div class="m">+ ${num(held.length - TIP_FOLDED)}</div>` : '');
  }
  canvas.addEventListener('mousemove', ev => {
    const n = pick(ev), h = n ? n.i : null;
    if (h !== hover) { hover = h; draw(); }
    const d = n ? null : domainAt(ev);
    const [px, py] = d3.pointer(ev, canvas);
    canvas.style.cursor = (n && !SP.has(n.i) && t.k >= FAR) || labelAt(px, py) ? 'grab' : '';
    if (!n && !d) { tip.style.display = 'none'; return; }
    if (n) {
      const dbl = detailIds.has(n.id) ? T.openDetail : T.zoomIn, start = traj && n.i === traj.start;
      tip.innerHTML = tableTip(DATA, n) + foldTip(n) + (traj ? trajectoryTip(traj, n.i) : '') + tableDesc(n) +
        `<div class="a">${t.k < FAR ? frameText() : start ? dbl : T.clickTraj + ' · ' + dbl}</div>`;
    } else if (state.by === 'layers') {
      tip.innerHTML = layerTip(d, t.invert(d3.pointer(ev, canvas))[0]);
    } else {
      const dd = DOM[d.k];
      tip.innerHTML = `<b>${esc(labelOf(dd))}</b><div class="m">${plural(d.n, L.tables)}${dd.owner ? ` · ${T.owner}${L.colon}${esc(dd.owner)}` : ''}</div>`
        + `<div class="m">${T.layers}${L.colon}${esc(bandLabels(d))}</div><div class="a">${T.frame}</div>`;
    }
    const r = stage.getBoundingClientRect();
    tip.style.display = 'block';
    tip.style.left = Math.min(ev.clientX - r.left + 14, r.width - 380) + 'px';
    tip.style.top = (ev.clientY - r.top + 14) + 'px';
  });
  canvas.addEventListener('mouseleave', () => { tip.style.display = 'none'; if (hover != null) { hover = null; draw(); } });
  // from afar stars are packed too tightly to aim at: double-click frames the constellation until zoomed in
  const FAR = 0.5;
  const frameText = () => (state.by === 'layers' ? T.frameC : T.frame);
  canvas.addEventListener('dblclick', ev => {
    const n = t.k >= FAR ? pick(ev) : null;
    if (n) {
      if (detailIds.has(n.id)) { tip.style.display = 'none'; openInDetail(n.id); return; }
      found = n.i; placeShown(); zoomTo(posOf(n.i).x, posOf(n.i).y, Math.max(t.k * 2.5, 1.5));
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
    if (labelAt(...d3.pointer(ev, canvas)) || domainAt(ev)) return;
    if (traj) leaveTrajectory(false);
    if (found != null && foldedSet.has(found)) { found = null; placeShown(); draw(); }   // the empty background hides the orbit
  });

  // ---------------------------------------------------------------- trajectory mode
  const countsText = (u, d) => trajectoryCounts(trajOpts.direction, u, d);
  function enterTrajectory(i) {
    const { up, down } = trajectory(DATA.lineage, i, trajOpts.direction, trajOpts.depth);
    traj = { start: i, up, down, edges: trajectoryEdges(DATA.lineage, i, up, down), brought: 0 };
    bar.hidden = false;   // shown before reveal, so a relayout frames the trajectory below the bar
    traj.brought = reveal(trajMembers());
    placeShown();   // the folded tables of the trajectory, start included, on their entities' orbits
    const n = N[i], summary = renderBar(), around = trajMembers().filter(j => SP.has(j)).length;
    live.textContent = `${T.trajOf} ${n.name}${L.colon}${summary}.` + (traj.brought ? ` ${plural(traj.brought, T.brought)}.` : '')
      + (around ? ` ${T.shownAround}${L.colon}${num(around)}.` : '');
    draw();
  }
  function leaveTrajectory(restoreFocus) {
    if (!traj) return;
    const inBar = bar.contains(document.activeElement);
    traj = null; bar.hidden = true; $u('tj-counts').open = false;
    placeShown();   // the search keeps what it shows
    $u('fit').removeAttribute('title');
    live.textContent = T.closed;
    if (restoreFocus && inBar) ($u('traj').disabled ? $u('q') : $u('traj')).focus();
    draw();
  }
  // fills the bar from the current trajectory; returns the counts (or empty-state) text
  function renderBar() {
    const n = N[traj.start], u = traj.up.size, d = traj.down.size, empty = u + d === 0;
    paintDot($u('tj-dot'), KIND[n.kind].color);
    $u('tj-start').textContent = n.name; $u('tj-start').title = n.name;
    const ups = countByDomain(N, traj.up.keys()), downs = countByDomain(N, traj.down.keys());
    const rows = [...new Set([...ups.keys(), ...downs.keys()])].map(k => [k, ups.get(k) || 0, downs.get(k) || 0])
      .map(([k, cu, cd]) => ({ k, total: cu + cd, text: `${DOM[k].label}${L.colon}${countsText(cu, cd)}` }))
      .sort((a, b) => b.total - a.total || a.text.localeCompare(b.text));
    $u('tj-list').replaceChildren(...rows.map(r => {
      const li = document.createElement('li');
      li.append(paintDot(document.createElement('i'), DOM[r.k].color), r.text);
      return li;
    }));
    const sum = $u('tj-sum'), emptyText = noTrajectory(trajOpts.direction);
    sum.textContent = countsText(u, d); sum.title = rows.map(r => r.text).join('\n');
    $u('tj-counts').hidden = empty; $u('tj-empty').hidden = !empty;
    $u('tj-empty').textContent = empty ? emptyText : '';
    $u('tj-flow').disabled = empty;
    const hidden = trajMembers().filter(j => !vis.has(j)).length;
    $u('tj-hidden').textContent = hidden ? plural(hidden, T.hiddenN) : '';
    $u('tj-back').textContent = traj.brought ? plural(traj.brought, T.brought) : '';
    $u('fit').title = T.fitTraj;
    return empty ? emptyText : sum.textContent;
  }
  bar.setAttribute('aria-label', T.trajectory);
  $u('tj-title').textContent = T.trajOf;
  $u('tj-h-dir').textContent = L.direction; $u('tj-h-depth').textContent = L.depth;
  $u('tj-l-start').textContent = L.lgStart; $u('tj-l-up').textContent = L.up; $u('tj-l-down').textContent = L.down;
  $u('tj-leave').textContent = T.leave; $u('tj-leave').title = T.leaveTitle;
  $u('tj-flow').textContent = T.flow; $u('tj-flow').title = T.flowTitle;
  // the flow view opens on this trajectory and never changes it (D-036)
  $u('tj-flow').onclick = () => { if (traj) openFlow(N[traj.start].id, trajOpts.direction, trajOpts.depth); };
  options($u('tj-dir'), ['both', 'up', 'down'], trajOpts.direction);
  options($u('tj-depth'), ['dall', 'd1', 'd2', 'd3'], 'dall');
  $u('tj-dir').onchange = ev => { trajOpts.direction = ev.target.value; if (traj) enterTrajectory(traj.start); };
  $u('tj-depth').onchange = ev => { trajOpts.depth = DEPTH[ev.target.value]; if (traj) enterTrajectory(traj.start); };
  $u('tj-leave').onclick = () => leaveTrajectory(true);
  const trajBtn = $u('traj');
  function syncTrajBtn() { trajBtn.disabled = !findByName($u('q').value); }
  trajBtn.textContent = T.trajectory; trajBtn.title = T.trajFound;
  $u('q').addEventListener('input', syncTrajBtn); $u('q').addEventListener('change', syncTrajBtn);
  trajBtn.onclick = () => {
    const n = findByName($u('q').value);
    if (!n) return;
    enterTrajectory(n.i);
    $u('tj-dir').focus();
  };
  document.addEventListener('keydown', ev => {
    if (ev.key !== 'Escape' || ev.defaultPrevented || !traj || !tab.classList.contains('on')) return;   // the flow's Esc
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
  const boxOf = i => B[i] || { w: 2 * starR(N[i]) + 4, h: 2 * starR(N[i]) + 4, oy: 0 };   // a shown table reserves nothing: its star
  // Puts the folded tables that must be seen on an orbit round their entity, without laying anything out again
  // (D-018): the folded tables of the trajectory, start included, and every folded table of the entity of the table
  // found by search. Ring j of an entity holds at most ORBIT_RING tables, evenly spaced from the top, in name order;
  // its radius clears the entity's star and the shown stars next to each other. They reserve no room.
  function placeShown() {
    const t0 = performance.now();
    SP = new Map(); orbits = []; ORBIT_R = new Map();
    const want = new Set(trajMembers().filter(i => foldedSet.has(i)));
    if (found != null && foldedSet.has(found)) FOLDED.get(PARENT[found]).forEach(i => want.add(i));
    const byParent = d3.group([...want].sort((a, b) => a - b), i => PARENT[i]);
    byParent.forEach((list, parent) => {
      const c = P[parent], tallest = d3.max(list, i => starR(N[i]));
      for (let j = 0; j * ORBIT_RING < list.length; j++) {
        const ring = list.slice(j * ORBIT_RING, (j + 1) * ORBIT_RING), m = ring.length;
        const r = Math.max(starR(N[parent]) + ORBIT_GAP + j * ORBIT_STEP, (tallest + ORBIT_ROOM) / Math.sin(Math.PI / Math.max(m, 2)));
        orbits.push({ x: c.x, y: c.y, r });
        ORBIT_R.set(parent, { r, tall: tallest });
        ring.forEach((i, q) => {
          const a = -Math.PI / 2 + 2 * Math.PI * q / m;
          SP.set(i, { x: c.x + r * Math.cos(a), y: c.y + r * Math.sin(a), a });
        });
      }
    });
    perf.place = performance.now() - t0;
  }
  let size = '';
  new ResizeObserver(() => {
    const s = stage.clientWidth + 'x' + stage.clientHeight;
    if (stage.clientWidth && s !== size) { size = s; resize(); fit(false); }
  }).observe(stage);
  layout(); resize(); fit(false);

  // the screen rectangle reserved by a drawn table (its card, or its star and name), in CSS px from the
  // canvas's top left corner; null when not drawn
  function place(id) {
    const n = N.find(m => m.id === id), p = n && posOf(n.i), b = n && boxOf(n.i);
    return p ? { x: (p.x - b.w / 2) * t.k + t.x, y: (p.y + b.oy - b.h / 2) * t.k + t.y, w: b.w * t.k, h: b.h * t.k } : null;
  }
  // the placement in world coordinates (the grouping; tables at their point P, with their reserved box;
  // constellations with their bands) and the time of the last layout: read-only, for the browser tests
  function geometry() {
    return { by: state.by, layoutMs: perf.layout,
      tables: [...drawn, ...[...SP.keys()].map(i => N[i])].map(n => ({ id: n.id, domain: n.domain, layer: n.layer,
        x: posOf(n.i).x, y: posOf(n.i).y, w: boxOf(n.i).w, h: boxOf(n.i).h, oy: boxOf(n.i).oy, r: starR(n),
        parent: PARENT[n.i] == null ? null : N[PARENT[n.i]].id, held: (FOLDED.get(n.i) || []).length, shown: SP.has(n.i) })),
      fold: { available: FOLDABLE, on: state.fold },
      folded: [...foldedSet].filter(i => !SP.has(i)).map(i => N[i].id),
      constellations: constellations.map(d => ({ key: d.k, n: d.n, x: d.x, y: d.y, r: d.r,
                                   bands: d.bands.map(b => ({ key: b.key, n: b.n, x0: d.x + b.x0, x1: d.x + b.x1 })) })) };
  }

  // the d3 zoom transform; camera({x, y, k}) moves it first, through the zoom (the browser tests frame a domain)
  function camera(to) {
    if (to) sel.call(zoom.transform, d3.zoomIdentity.translate(to.x, to.y).scale(to.k));
    return { x: t.x, y: t.y, k: t.k };
  }

  // image is for the browser tests' pixel comparison; the page uses it through #u-export.
  // camera, place and geometry are for the tests too: closing the flow leaves the camera as it was.
  return { shown: () => { resize(); }, relayout, trajectoryState, image, camera, place, geometry, drawnNames: () => drawnNames, placeMs: () => perf.place };
}
