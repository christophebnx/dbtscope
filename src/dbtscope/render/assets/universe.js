// Universe view: every table of the project as a star, grouped into one constellation per data
// domain, or per layer (D-048). A constellation's tables are packed in bands (layer bands, or domain
// bands in layer mode) into the smallest disc (D-040), then d3-force places the constellations; a
// canvas draws it.
// Started the first time its tab is shown. The trajectory traversal and its shared strings are in common.js.

function startUniverse(DATA, openInDetail, detailIds, LAYOUT, EXPORT, openFlow, FOLD, GROUPING) {
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
          foldTitle: 'Draw each descriptive table inside its entity. Search or a trajectory shows it around its entity.',
          entitiesN: ['entity', 'entities'],
          entity: 'Entity', entityHidden: ' (filtered out)', entityLayer: ' (other layer)',
          foldOn: n => `Descriptive tables folded into ${plural(n, T.entitiesN)}`, foldOff: 'Descriptive tables shown',
          foundFolded: (n, p) => `${n} is folded into ${p}; shown around it.`, shownAround: 'Shown around their entity',
          hintFold: ' · a number on a star: tables folded into it, shown around it by search or trajectory',
          summary: 'Summary', zoomBtn: 'Zoom', zoomOn: name => `Zoom on ${name}`, mainTables: 'Main tables',
          zoomRow: 'Zoom on this layer', zoomRowC: 'Zoom on this domain', layerOne: 'Layer',
          rowZoom: 'click a row: zoom on it', groupHint: 'Click a row: zoom on it · double-click: frame the systems', zoomed: name => `Zoomed on ${name}`,
          hintCards: ' · from afar each constellation is a summary card: double-click it, or click one of its rows, to see its tables',
          // source systems and routes (M8.4, D-065..D-067)
          systems: 'Source systems', systemsN: ['system', 'systems'], systemOne: 'Source system',
          routesN: ['route', 'routes'], routesShownN: ['route shown', 'routes shown'], allRoutes: 'All routes',
          allRoutesOn: 'All routes shown', allRoutesOff: 'Strongest routes shown',
          lineageN: ['lineage link', 'lineage links'], relationsN: ['relation', 'relations'],
          reads: (r, u) => `${r} reads ${u}`, systemsList: 'Systems',
          routesOf: (s, n) => `${num(s)} of ${plural(n, T.routesN)}`,
          routes: 'Routes', routesNone: 'none', readsFrom: 'reads', readBy: 'read by', relWith: 'relations with',
          hintRoutes: ' · hover a constellation to see all its routes, a route for the links it carries' },
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
          foldTitle: 'Dessiner chaque table descriptive dans son entité. La recherche ou une trajectoire l\'affiche autour de son entité.',
          entitiesN: ['entité', 'entités'],
          entity: 'Entité', entityHidden: ' (masquée par les filtres)', entityLayer: ' (autre couche)',
          foldOn: n => `Tables descriptives repliées dans ${plural(n, T.entitiesN)}`, foldOff: 'Tables descriptives affichées',
          foundFolded: (n, p) => `${n} est repliée dans ${p}\u202f; affichée autour d\'elle.`, shownAround: 'Affichées autour de leur entité',
          hintFold: ' · un nombre sur une étoile\u00a0: tables repliées dans celle-ci, affichées autour d\'elle par la recherche ou la trajectoire',
          summary: 'Synthèse', zoomBtn: 'Cadrer', zoomOn: name => `Cadrer ${name}`, mainTables: 'Tables principales',
          zoomRow: 'Cadrer cette couche', zoomRowC: 'Cadrer ce domaine', layerOne: 'Couche',
          rowZoom: 'clic sur une ligne\u00a0: la cadrer', groupHint: 'Clic sur une ligne\u00a0: la cadrer · double-clic\u00a0: cadrer les systèmes', zoomed: name => `Cadré sur ${name}`,
          hintCards: ' · de loin, chaque constellation est une carte de synthèse\u00a0: double-clic dessus, ou clic sur une de ses lignes, pour voir ses tables',
          systems: 'Systèmes sources', systemsN: ['système', 'systèmes'], systemOne: 'Système source',
          routesN: ['route', 'routes'], routesShownN: ['route affichée', 'routes affichées'], allRoutes: 'Toutes les routes',
          allRoutesOn: 'Toutes les routes affichées', allRoutesOff: 'Routes principales affichées',
          lineageN: ['lien de lignage', 'liens de lignage'], relationsN: ['relation', 'relations'],
          reads: (r, u) => `${r} lit ${u}`, systemsList: 'Systèmes',
          routesOf: (s, n) => `${plural(s, T.routesN)} sur ${num(n)}`,
          routes: 'Routes', routesNone: 'aucune', readsFrom: 'lit', readBy: 'lu par', relWith: 'relations avec',
          hintRoutes: ' · survolez une constellation pour voir toutes ses routes, une route pour les liens qu\'elle porte' },
  }[PAGE.lang];

  const N = DATA.nodes; N.forEach((n, i) => n.i = i);
  // how connected each table is over all links: pivots (hubs, dimensions...) get bigger stars and their names first
  const DEG = new Array(N.length).fill(0);
  [...DATA.relations, ...DATA.lineage].forEach(([a, b]) => { DEG[a]++; DEG[b]++; });
  // role of a kind (D-058): core, connector, descriptive, technical, or none. It sizes the star, orders the names
  // and the Types list; Python decides it, the page only reads it
  const NAME_ORDER = ['core', 'connector', null, 'descriptive', 'technical'];   // name priority
  const ROLE_STAR = { core: 1.35, descriptive: 0.75, technical: 0.75 };          // connector and none: 1
  const STAR_MAX = 14, STAR_MIN = 2.5;   // degree radius cap before the factor; floor after it (world px)
  const OVERVIEW_K = 0.6;                // = the `far` threshold of drawStar, routes and band markers
  const TABLE_K = 0.35;                  // below it a table is a star whatever the detail level, and no link is drawn; above, a card
  const CARDS_ALPHA = 0.5;               // the card layer's alpha from which the cards are the ones in play (interactions, routes)
  const OVERVIEW_NAMES = 3;              // core names offered per constellation below OVERVIEW_K
  // folded tables (M8.2, D-062)
  const BADGE_H = 15, BADGE_MAX = 26;   // entity badge, screen px: height; widest (3 characters "99+")
  const BADGE_ARC = 2.5;                // below OVERVIEW_K the badge is a dark arc of this screen width on the star's north-east rim, no digits
  const ORBIT_GAP = 18;                 // world px between an entity's star and its first orbit
  const ORBIT_RING = 16, ORBIT_STEP = 16;  // most shown tables per orbit; world px between two orbits
  const ORBIT_ROOM = 10;                // world px added to a shown star's radius when spacing neighbours (room for ring + search mark)
  const FOLD_ROWS = 12, FOLD_HEAD = 15;  // folded rows on a card; heading row height
  // summary cards (M8.3, D-063, D-064): a star "can be told apart" above SUMMARY_CELL screen px of room (the star cell);
  // cards fade into stars over a zoom ratio of SUMMARY_FADE; at most SUMMARY_NAMES main tables on a card
  const SUMMARY_CELL = 14, SUMMARY_FADE = 1.3, SUMMARY_NAMES = 5;
  const KIND = Object.fromEntries(DATA.kinds.map(k => [k.key, k]));
  const roleOf = n => KIND[n.kind].role ?? null;
  const isEntity = n => roleOf(n) === 'core' || roleOf(n) === 'connector';   // what the meta line and a card count as an entity
  const HAS_CORE = DATA.kinds.some(k => k.role === 'core');
  const starR = n => Math.max(STAR_MIN, Math.min(STAR_MAX, 3 + 1.6 * Math.sqrt(DEG[n.i])) * (ROLE_STAR[roleOf(n)] ?? 1));
  // business relations of each table, both ends, whatever the Links selector says: ranks the main tables
  const RELN = new Array(N.length).fill(0);
  DATA.relations.forEach(([a, b]) => { RELN[a]++; RELN[b]++; });
  // the core tables of a constellation, the most related first (relations, then links of any kind, then name, then id)
  const mainTables = members => members.filter(n => roleOf(n) === 'core')
    .sort((a, b) => RELN[b.i] - RELN[a.i] || DEG[b.i] - DEG[a.i] || byNameThenId(a, b));
  let MAIN = new Map();   // table -> its rank in its constellation (0 = main), set by layout()
  // summary cards (D-063): set by summarise() at the end of layout(); CELL = the star cell (world px)
  let SUMMARIES = new Map(), CELL = 1, summaryScale = 1, starsScale = 1;
  // names compete for room on screen: by role, then (core) by rank in the constellation, then the most
  // connected tables, the kinds listed first in the config winning
  const KIND_RANK = Object.fromEntries(DATA.kinds.map((k, i) => [k.key, i]));
  const labelScore = n => (DEG[n.i] + 1) * (1 - 0.7 * KIND_RANK[n.kind] / Math.max(1, DATA.kinds.length - 1));
  // the order of the Types list: by role, then as in the payload (the panel, the bars of the summary cards)
  const kindOrder = kindsByRole(DATA.kinds);
  // name priority: by role (NAME_ORDER; core by rank in its constellation), then by score
  const nameOrder = (a, b) => NAME_ORDER.indexOf(roleOf(a)) - NAME_ORDER.indexOf(roleOf(b))
    || (roleOf(a) === 'core' ? (MAIN.get(a.i) ?? Infinity) - (MAIN.get(b.i) ?? Infinity) : 0) || labelScore(b) - labelScore(a);
  // the main tables of a constellation, first the main ones (D-058): on a page with a core kind its core tables by rank
  // (none for a constellation without any), else all by role then score. The summary cards' main tables (D-064) read it;
  // names at overview (orderLabels) share nameOrder and offer the first OVERVIEW_NAMES of the tables on screen.
  const overviewOrder = members => members.filter(n => !HAS_CORE || roleOf(n) === 'core').sort(nameOrder);
  const DOM = Object.fromEntries(DATA.domains.map(d => [d.key, d]));
  // source systems (M8.4, D-065, D-066): Python decides which domains are plumbing, the page only reads the flag. DOMAIN_ORDER is
  // the one order of domains in the page: business domains in payload order, then source systems (the Domains panel, the layer
  // mode's bands and card rows); without a system it is the payload order
  const SYSTEM = new Set(DATA.domains.filter(d => d.system).map(d => d.key));
  const DOMAIN_ORDER = [...DATA.domains.filter(d => !d.system), ...DATA.domains.filter(d => d.system)];
  const isSystem = key => state.by === 'domains' && SYSTEM.has(key);   // a source system's constellation: only in domain mode
  const NEUTRAL = '#8a94a6', GROUP = '\u0000systems';   // a source system's colour (drawn through CONTRAST.edge); the group card's key
  const LAYER = Object.fromEntries(DATA.layers.map((l, i) => [l.key, { ...l, rank: i }]));
  const counts = key => d3.rollup(N, v => v.length, n => n[key]);
  const COUNT = { domain: countByDomain(N, N.keys()), layer: counts('layer'), kind: counts('kind') };
  // the viewer's last grouping: GROUPING (boot.js, key `dbtscope-constellations:<title>`), kept apart from the shared layout and
  // never exported (D-048); stored only when it differs from the page default
  const BY_WORDS = ['domains', 'layers'];
  // the switch exists from two rows of the Layers list; below, the page stays in domains
  const CAN_BY = DATA.layers.length >= 2;
  const DEFAULT_BY = DATA.defaults.constellations === 'layers' ? 'layers' : 'domains';
  // the parent of each table (a node index, null for none): Python decides it, the page never guesses from names (D-061)
  const IDX = new Map(N.map(n => [n.id, n.i]));
  const PARENT = N.map(n => (n.parent == null ? null : IDX.get(n.parent) ?? null));
  const FOLDABLE = PARENT.some(p => p != null);
  const state = {
    domains: new Set(DATA.domains.map(d => d.key)),
    layers: new Set(DATA.layers.map(l => l.key)),
    kinds: new Set(DATA.kinds.map(k => k.key).filter(k => !DATA.defaults.hiddenKinds.includes(k))),
    links: DATA.defaults.links, detail: DATA.defaults.detail,
    by: CAN_BY ? GROUPING.get(BY_WORDS) || DEFAULT_BY : 'domains',
    fold: FOLDABLE && FOLD.on(),
    allRoutes: false,   // exploration, not a lasting choice: never stored nor exported
  };
  const stage = $u('stage'), canvas = $u('canvas'), screenCtx = canvas.getContext('2d'), tip = $u('tip');
  let ctx = screenCtx;   // what the drawing helpers paint on: the screen, or an exported image during draw()
  const layoutCache = new Map();
  let P = [], B = [], REL = new Map(), labelHits = [], visible = [], edges = [], constellations = [], routes = [], tree = null;
  // folded tables (D-062): vis = filter-visible tables; drawn = visible minus folded; FOLDED = parent -> its visible folded
  // tables; foldedSet = those tables; SP / orbits = folded tables shown now, on an orbit round their entity (placeShown)
  // routes (M8.4): the individual routes are `routes`; BUNDLE the bundled graph through the group card (built on demand);
  // FLOWRANK the business domains' flow ranks; GROUPED the source systems the group card stands for (two or more, else none);
  // routeFocus the constellation (or GROUP) whose routes are all drawn; routeSeen what the last screen frame drew
  let litSet = null;   // the keys the focus lights (null: no focus)
  const litAlpha = key => (litSet && !litSet.has(key) ? DIM_CTX : 1);
  let BUNDLE = null, FLOWRANK = new Map(), GROUPED = [], routeFocus = null, routeSeen = { list: [], obstacles: [] };
  let vis = new Set(), drawn = [], FOLDED = new Map(), foldedSet = new Set(), entityCount = 0;
  let SP = new Map(), orbits = [], ORBIT_R = new Map();   // ORBIT_R: entity -> { r, tall } its outer orbit and tallest shown star, world
  const posOf = i => P[i] || SP.get(i);
  let drawnNames = [];   // the tables whose names the last screen frame drew (test hook)
  let t = d3.zoomIdentity, hover = null, overCard = null, found = null, perf = { layout: 0, draw: 0, place: 0, cards: 0, cardLayout: 0, routes: 0 };
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
    radio.onchange = () => { if (!radio.checked) return; state.by = radio.value; GROUPING.set(state.by, DEFAULT_BY); relayout(); };
  });
  // the fold control (D-062): one checkbox, shown only when some table has a parent; its second line names the
  // descriptive kinds that fold here, as written in the config
  $u('fold').hidden = !FOLDABLE;
  $u('fold-t').textContent = L.fold;
  $u('fold-kinds').textContent = foldKindsText(foldKindLabels(DATA.kinds, N.filter(n => PARENT[n.i] != null)));
  $u('fold-n').textContent = num(PARENT.filter(p => p != null).length);
  $u('fold').querySelector('label').title = T.foldTitle;
  $u('fold-on').checked = state.fold;
  const hintText = () => T.hint + (state.fold ? T.hintFold : '') + T.hintCards + T.hintRoutes;
  $u('fold-on').onchange = ev => {
    FOLD.set(ev.target.checked, applyFold);
    applyFold(ev.target.checked);
    live.textContent = state.fold ? T.foldOn(entityCount) : T.foldOff;
  };
  // the choice changed (here, or in the detail view, D-069): follow it; a hidden tab lays out when shown
  let foldStale = false;
  function applyFold(on) {
    state.fold = FOLDABLE && on; $u('fold-on').checked = state.fold;
    $u('hint').textContent = hintText();
    if (document.getElementById('tab-universe').classList.contains('on')) relayout(); else foldStale = true;
  }
  FOLD.listen(applyFold);
  const BUSINESS = DOMAIN_ORDER.filter(d => !d.system), SYSTEMS = DOMAIN_ORDER.filter(d => d.system);
  $u('h-layers').textContent = T.layers; $u('h-kinds').textContent = L.kinds; $u('h-domains').textContent = T.domains;
  $u('all').textContent = T.every; $u('none').textContent = T.nothing;
  $u('h-systems').textContent = T.systems; $u('sys-all').textContent = T.every; $u('sys-none').textContent = T.nothing;
  $u('h-systems-row').hidden = !SYSTEMS.length;
  $u('routes-t').textContent = T.allRoutes;
  $u('routes').onchange = ev => {
    state.allRoutes = ev.target.checked; draw();
    live.textContent = state.allRoutes ? T.allRoutesOn : T.allRoutesOff;
  };
  $u('fit').textContent = L.fit; $u('q').placeholder = T.search; $u('hint').textContent = hintText();

  function checkboxes(el, items, countOf, set, color, title) {
    el.replaceChildren(...items.map(it => {
      const row = filterRow(
        { label: labelOf(it), color: color && color(it), count: countOf.get(it.key) || 0, checked: set.has(it.key),
          title: title && title(it) },
        on => { on ? set.add(it.key) : set.delete(it.key); relayout(); });
      if (el.id === 'u-domains' || el.id === 'u-systems') focusRow(row, it.key, () => state.by === 'domains');   // keyboard focus lights the routes (D-067)
      return row;
    }));
  }
  function refreshPanel() {
    checkboxes($u('layers'), DATA.layers, COUNT.layer, state.layers);
    checkboxes($u('kinds'), kindOrder, COUNT.kind, state.kinds, k => k.color,
      k => k.role ? `${T.role}${L.colon}${T.roles[k.role]}` : labelOf(k));
    const domainTitle = d => d.owner ? `${T.owner}${L.colon}${d.owner}` : labelOf(d);
    checkboxes($u('domains'), BUSINESS, COUNT.domain, state.domains, d => d.color, domainTitle);
    checkboxes($u('systems'), SYSTEMS, COUNT.domain, state.domains, d => d.color, domainTitle);
  }
  refreshPanel();
  // all / none act on their own list: the business domains, or the source systems
  const setAll = (list, on) => () => { list.forEach(d => (on ? state.domains.add(d.key) : state.domains.delete(d.key))); refreshPanel(); relayout(); };
  $u('all').onclick = setAll(BUSINESS, true); $u('none').onclick = setAll(BUSINESS, false);
  $u('sys-all').onclick = setAll(SYSTEMS, true); $u('sys-none').onclick = setAll(SYSTEMS, false);
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
    zoomTo(p.x, p.y, Math.max(t.k, 1.5, starsScale * 1.05));   // past the summary cards: the table is seen as a star
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
    entityCount = visible.filter(isEntity).length;
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
    const agg = new Map(), flow = new Map(), rel = new Map(), lin = new Map();
    const pairKey = (a, b) => (a < b ? a + '|' + b : b + '|' + a);
    edges.forEach(([a, b]) => {
      const da = G.of(N[a]), db = G.of(N[b]);
      if (da !== db) { const k = pairKey(da, db); agg.set(k, (agg.get(k) || 0) + 1); }
    });
    // what each route carries, by kind of link (its tooltip), under the Links selector
    const tally = (list, into) => list.forEach(([a, b]) => {
      if (!vis.has(a) || !vis.has(b) || G.of(N[a]) === G.of(N[b])) return;
      const k = pairKey(G.of(N[a]), G.of(N[b]));
      into.set(k, (into.get(k) || 0) + 1);
    });
    if (state.links !== 'lineage') tally(DATA.relations, rel);
    if (state.links !== 'relations') tally(DATA.lineage, lin);
    DATA.lineage.forEach(([child, parent]) => {  // data flows from parent to child
      if (!vis.has(child) || !vis.has(parent)) return;
      const from = G.of(N[parent]), to = G.of(N[child]);
      if (from === to) return;
      const k = pairKey(from, to);
      flow.set(k, (flow.get(k) || 0) + (from < to ? 1 : -1));
    });
    // manual arrangement: a moved table keeps its offset from its constellation's centre, a moved
    // constellation is pinned
    const saved = savedLayout();
    REL = new Map();
    for (const [, dl] of local) placeAroundDragged(dl.ns, saved.nodes);
    constellations = [...local].map(([k, v]) => ({ k, rank: v.rank, n: whole.get(k).length, bands: v.bands,
      r: Math.max(v.R, d3.max(v.ns, s => reach(s.i))) }));
    constellations.forEach(d => { const p = saved[G.pins][d.k]; if (p) { d.fx = p[0]; d.fy = p[1]; } });
    routes = [...agg].map(([k, c]) => {
      const [a, b] = k.split('|'), f = flow.get(k) || 0;
      const r = { source: a, target: b, c, rel: rel.get(k) || 0, lin: lin.get(k) || 0, f, flow: 0, dir: 0, strong: false };
      r.flow = netFlow(r); r.dir = r.lin ? r.flow : 0;
      return r;
    });
    const strong = strongRoutes(routes);
    routes.forEach(r => { r.strong = strong.has(r); });
    BUNDLE = null;
    // source systems stay out of the simulation: they are stacked upstream afterwards (stackSystems). Business domains are
    // placed along the data flow: their x target is their rank over the business-domain graph (domainRanks)
    const byKey = new Map(constellations.map(d => [d.k, d])), isSys = d => isSystem(d.k);
    const business = constellations.filter(d => !isSys(d)), systems = constellations.filter(isSys);
    FLOWRANK = new Map();
    if (state.by === 'domains') {
      FLOWRANK = domainRanks(business, whole, routes);
      business.forEach(d => { d.rank = FLOWRANK.get(d.k); });
    }
    const rand = d3.randomLcg(42), W = (d3.mean(business, d => d.r) || 1) * 2.4;
    const inSim = new Set(business.map(d => d.k));
    const links = routes.filter(r => inSim.has(r.source) && inSim.has(r.target)).map(r => ({ source: r.source, target: r.target, c: r.c }));
    const sim = d3.forceSimulation(business).randomSource(rand)
      // the padding leaves room for the domain name drawn above each constellation
      .force('collide', d3.forceCollide(roomOf).iterations(3))
      .force('link', d3.forceLink(links).id(d => d.k).distance(l => l.source.r + l.target.r + 60)
        .strength(l => Math.min(0.4, 0.03 + Math.log1p(l.c) * 0.04)))
      .force('x', d3.forceX(d => d.rank * W).strength(G.flowX))
      .force('y', d3.forceY(0).strength(0.06))
      .force('charge', d3.forceManyBody().strength(-20))
      .stop();
    for (let k = 0; k < 400; k++) sim.tick();
    // settle with collisions only, so link forces can't leave constellations overlapping
    sim.force('link', null).force('x', null).force('y', null).force('charge', null);
    for (let k = 0; k < 100; k++) sim.tick();
    stackSystems(systems, business, byKey);
    GROUPED = systems.length >= 2 ? systems : [];
    if (GROUPED.length) placeGroup();
    // the control for every route: only when some are left out, evaluated per layout so it never flickers while zooming
    const all = routes.every(r => r.strong);
    $u('routes-row').hidden = all;
    if (all && state.allRoutes) { state.allRoutes = false; $u('routes').checked = false; }

    P = [];
    constellations.forEach(d => local.get(d.k).ns.forEach(s => { const [dx, dy] = REL.get(s.i); P[s.i] = { x: d.x + dx, y: d.y + dy }; }));
    tree = d3.quadtree(drawn, n => P[n.i].x, n => P[n.i].y);
    placeShown();
    perf.layout = performance.now() - t0;
    summarise();
    renderSummary();
  }

  // ---------------------------------------------------------------- source systems and routes (M8.4, D-065..D-067)
  // The business domains' x target (D-066): the rank of each over the graph of business constellations, reusing flowRanks. An edge
  // runs from the upstream domain to the one that reads it (routes with a net direction); the layer of a constellation is its
  // median table's (null when that is the catch-all, which gets no floor). A domain read by others sits left of them.
  function domainRanks(business, whole, list) {
    const keys = business.map(d => d.k), at = new Set(keys);
    const edgesUp = list.filter(r => r.flow && at.has(r.source) && at.has(r.target)).map(r => (r.flow > 0 ? [r.source, r.target] : [r.target, r.source]));
    const layerAt = key => {
      const ranks = whole.get(key).map(n => LAYER[n.layer].rank).sort((a, b) => a - b), m = ranks[ranks.length >> 1];
      return DATA.layers[m].key === NO_LAYER ? null : m;
    };
    return flowRanks(keys, edgesUp, layerAt).rank;
  }
  // The source systems in columns left of the business domains (D-066), after the simulation: no randomness. A column's height is
  // capped at the business box's; the systems, sorted by the mean y of the business domains they feed, are dealt round-robin into
  // the columns (the first nearest the business box), each column keeping every disc as close to that y as the room between two
  // discs allows (an isotonic fit, pool-adjacent-violators). A pinned system stays at its pin; a free one steps over it.
  const STACK_GAP = 30;
  const stackOrder = (a, b) => a.y - b.y || b.x - a.x;   // the order of the source systems, top to bottom (the stack, the group card, the text summary)
  // The direction of a route (the one threshold): the sign of its net lineage flow when that exceeds 20 % of its weight. `flow` is
  // that, whatever Links shows (it places the business domains along the data flow); `dir`, what is drawn and said (arrowhead,
  // "reads"), is `flow` only while the route carries lineage on screen
  const netFlow = r => (Math.abs(r.f) > r.c * 0.2 ? Math.sign(r.f) : 0);
  const roomOf = d => d.r + 30 + d.r * 0.15;   // the collide radius
  function stackSystems(systems, business, byKey) {
    systems.filter(d => d.fx != null).forEach(d => { d.x = d.fx; d.y = d.fy; });
    const free = systems.filter(d => d.fx == null), pinned = systems.filter(d => d.fx != null);
    if (!free.length) return;
    const roomSum = d3.sum(free, d => 2 * roomOf(d));
    const top = business.length ? d3.min(business, d => d.y - d.r) : 0, bottom = business.length ? d3.max(business, d => d.y + d.r) : 0;
    const H = business.length ? Math.max(bottom - top, 2 * d3.max(free, roomOf)) : Math.sqrt(d3.sum(free, d => (2 * roomOf(d)) ** 2));
    const mid = (top + bottom) / 2, ncol = Math.max(1, Math.ceil(roomSum / H));
    const bary = d => {
      let w = 0, sum = 0;
      routes.forEach(r => {
        const other = r.source === d.k ? r.target : r.target === d.k ? r.source : null, o = other && byKey.get(other);
        if (o && !SYSTEM.has(other)) { w += r.c; sum += r.c * o.y; }
      });
      return w ? sum / w : mid;
    };
    const order = free.map((d, i) => ({ d, i, y: bary(d) })).sort((a, b) => a.y - b.y || a.i - b.i);
    const cols = Array.from({ length: ncol }, () => []);
    order.forEach((e, j) => cols[j % ncol].push(e));
    let right = (business.length ? d3.min(business, d => d.x - d.r) : 0) - STACK_GAP;
    cols.forEach(col => {
      if (!col.length) return;
      const wide = d3.max(col, e => e.d.r), cx = right - wide;
      right = cx - wide - STACK_GAP;
      // y_i = z_i + cum_i, z non-decreasing: the isotonic fit of (wanted y - cum) keeps the order and the room
      let cum = 0;
      const blocks = [];
      col.forEach((e, j) => {
        if (j) cum += roomOf(col[j - 1].d) + roomOf(e.d);
        e.cum = cum;
        blocks.push({ sum: e.y - cum, n: 1 });
        while (blocks.length > 1 && blocks[blocks.length - 2].sum / blocks[blocks.length - 2].n >= blocks[blocks.length - 1].sum / blocks[blocks.length - 1].n) {
          const b = blocks.pop(); blocks[blocks.length - 1].sum += b.sum; blocks[blocks.length - 1].n += b.n;
        }
      });
      let at = 0, prev = -Infinity;
      blocks.forEach(b => { for (let j = 0; j < b.n; j++, at++) col[at].z = b.sum / b.n; });
      col.forEach(e => {
        const R = roomOf(e.d);
        let y = Math.max(e.z + e.cum, prev + R);
        for (let again = true, guard = 0; again && guard <= pinned.length; guard++) {   // step over a pinned disc in this column
          again = false;
          pinned.forEach(p => {
            if (Math.abs(cx - p.x) < e.d.r + p.r + STACK_GAP && Math.abs(y - p.y) < R + roomOf(p)) { y = p.y + roomOf(p) + R; again = true; }
          });
        }
        e.d.x = cx; e.d.y = y; prev = y + R;
      });
    });
  }
  // The strongest routes (D-067): each constellation keeps its STRONG_ROUTES heaviest (by `c`), ties included; a route is kept
  // when it is among the strongest of either end. -> Set of the routes of `list` kept
  const STRONG_ROUTES = 2;
  function strongRoutes(list) {
    const by = new Map(), keep = new Set();
    list.forEach(r => [r.source, r.target].forEach(k => { if (!by.has(k)) by.set(k, []); by.get(k).push(r); }));
    by.forEach(rs => {
      rs.sort((a, b) => b.c - a.c);
      const floor = rs[Math.min(STRONG_ROUTES, rs.length) - 1].c;
      rs.forEach(r => { if (r.c >= floor) keep.add(r); });
    });
    return keep;
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
  const DOM_POS = Object.fromEntries(DOMAIN_ORDER.map((d, i) => [d.key, i]));
  // What a constellation stands for (D-048): of, its key for a table; band, a table's band position (null:
  // no band, placed by lineage); bandKey, a band position's key; rank, the constellation's x target along
  // the flow; flowX, the strength of that target; pins, the key of saved centres; scope, the layout scope;
  // rowOf, a table's row on a summary card (its own layer, or its own domain) and rowList, the rows' order (D-064)
  const BY = {
    domains: { of: n => n.domain, band: layerPos, bandKey: pos => DATA.layers[pos].key,
               rank: () => 0, flowX: 0.1,   // rank: replaced by domainRanks() (the flow over the business domains), see layout()
               pins: 'domains', scope: () => state.detail, rowOf: n => n.layer, rowList: DATA.layers },
    layers: { of: n => n.layer, band: n => DOM_POS[n.domain], bandKey: pos => DOMAIN_ORDER[pos].key,
              rank: key => LAYER[key].rank, flowX: 0.3, pins: 'layers', scope: () => 'layers:' + state.detail,
              rowOf: n => n.domain, rowList: DOMAIN_ORDER },
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
      band.tables.sort((a, b) => rank.get(a.i) - rank.get(b.i) || bary.get(a.i) - bary.get(b.i) || byNameThenId(a, b));
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
  const C = { bg: THEME.bg, text: THEME.fg, muted: THEME.muted, card: '#ffffff', edge: 'rgba(100,116,139,.22)', cross: 'rgba(100,116,139,.10)', hl: 'rgba(31,41,51,.85)',
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
  // the stars layer (links, stars, badges, orbits, names...) is drawn at 1 - the summary cards' alpha (D-063): every alpha
  // it sets goes through setA, which scales it by LA
  let LA = 1;
  const setA = v => { ctx.globalAlpha = v * LA; };

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
    const a = visible.length ? summaryAlpha(k) : 0;   // the card layer's alpha; the stars layer's is LA = 1 - a
    LA = 1 - a;
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
    if (onScreen) {
      $u('export').disabled = !visible.length;
      const groups = plural(constellations.length, state.by === 'layers' ? T.layersN : L.domainsN);
      const entities = state.fold ? ` · ${plural(entityCount, T.entitiesN)}` : '';
      // the routes left out, while routes are drawn (D-067): the bundled graph's counts while the group card is on
      const { total, shown } = k < OVERVIEW_K ? routeCounts(a) : { total: 0, shown: 0 };
      const left = !state.allRoutes && shown < total ? ` · ${T.routesOf(shown, total)}` : '';
      $u('meta').textContent = $u('meta').title = `${plural(visible.length, L.tables)}${entities} · ${plural(edges.length, T.linksN)} · ${groups}${left}`;
    }
    if (!visible.length) {
      ctx.fillStyle = C.muted; ctx.font = `14px ${FONT}`; ctx.fillText(L.empty, 24, 40);
      if (onScreen) { summaryHits = []; summaryAll = []; routeSeen = { list: [], obstacles: [] }; }
      return;
    }
    const [x0, y0] = t.invert([0, 0]), [x1, y1] = t.invert([W, H]);
    const inView = (x, y, w, h) => x + w / 2 > x0 && x - w / 2 < x1 && y + h / 2 > y0 && y - h / 2 < y1;
    const screen = (x, y) => [x * k + t.x, y * k + t.y];
    // in the trajectory mode, constellations holding none of its drawn tables are context only
    const G = grouping(), byLayers = state.by === 'layers';
    const tdom = traj ? new Set(trajMembers().filter(i => posOf(i)).map(i => G.of(N[i]))) : null;
    // the routes in play (below OVERVIEW_K), and what the focus lights: its constellation, its neighbours, the rest at DIM_CTX
    const rs = k < OVERVIEW_K ? routeLayout(k, a, traj ? null : routeFocus) : null;
    litSet = rs && rs.focus ? rs.lit : null;
    const ctxAlpha = d => tdom && !tdom.has(d.k) ? DIM_CTX : litSet && !litSet.has(d.k) ? DIM_CTX : 1;

    ctx.save(); ctx.translate(t.x, t.y); ctx.scale(k, k);
    constellations.forEach(d => {
      // a source system's halo is neutral (D-066), at half strength while the group card stands for it
      const sys = isSystem(d.k);
      ctx.globalAlpha = ctxAlpha(d) * (sys && GROUPED.length ? 1 - a / 2 : 1);
      if (byLayers) { drawDomainBands(d, k); return; }
      const c = CONTRAST.edge(sys ? NEUTRAL : DOM[d.k].color, C.bg), g = ctx.createRadialGradient(d.x, d.y, 0, d.x, d.y, d.r);   // 3:1 (D-042)
      g.addColorStop(0, c + (sys ? '1f' : '26')); g.addColorStop(1, c + '0a');
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(d.x, d.y, d.r, 0, 7); ctx.fill();
      ctx.strokeStyle = c + (sys ? '80' : '66'); ctx.lineWidth = 1.5 / k; ctx.stroke();
    });
    if (k >= OVERVIEW_K && LA > 0) constellations.forEach(d => { setA(ctxAlpha(d)); drawBandMarkers(d, k); });
    ctx.globalAlpha = traj ? DIM : 1;

    if (rs) {  // from afar: the routes, outline to outline around the other constellations (D-067), in screen px
      ctx.save(); ctx.setTransform(scale, 0, 0, scale, t.x * scale, t.y * scale);
      drawRoutes(rs, onScreen);
      ctx.restore();
    } else if (onScreen) routeSeen = { list: [], obstacles: [] };
    // table-level links: hidden from afar (the routes say it), faint at mid zoom, full when close;
    // hover dimming is off in the trajectory mode, whose dimming replaces it
    const near = hover != null && !traj ? new Set([hover, ...edges.filter(e => e.includes(hover)).flat()]) : null;
    ctx.lineWidth = 1 / k;
    if (LA > 0) edges.forEach(([p, q]) => {
      if (!P[p] || !P[q]) return;   // an end is folded into its entity: not drawn inside the constellation
      const hl = near && (p === hover || q === hover), cross = G.of(N[p]) !== G.of(N[q]);
      if (!hl && (k < TABLE_K || (k < OVERVIEW_K && cross))) return;
      setA(traj ? DIM : 1);
      ctx.strokeStyle = hl ? C.hl : cross ? C.cross : C.edge;
      ctx.beginPath(); ctx.moveTo(P[p].x, P[p].y); ctx.lineTo(P[q].x, P[q].y); ctx.stroke();
    });

    const cards = state.detail !== 'names' && k > TABLE_K;
    const labels = [], badges = [];
    const drawTable = n => {
      const p = P[n.i], b = B[n.i]; if (!inView(p.x, p.y + b.oy, b.w, b.h)) return;
      const col = KIND[n.kind].color, mark = n.i === hover || n.i === found, side = sideOf(n.i);
      setA((litSet && !litSet.has(G.of(n)) ? DIM_CTX : 1) * (traj ? (side ? 1 : DIM) : near && !near.has(n.i) ? 0.2 : 1));
      if (cards) drawCard(n, p, b, col, mark, side, k);
      else {
        drawStar(n, p, col, mark, side, k); labels.push(n);
        if (FOLDED.has(n.i)) badges.push([p, Math.max(starR(n), (side ? 3 : 2.5) / k), FOLDED.get(n.i).length, ctx.globalAlpha]);
      }
    };
    if (LA > 0) {
      if (traj) {  // trajectory tables after its edges, so arrows never cover them
        drawn.forEach(n => { if (!sideOf(n.i)) drawTable(n); });
        setA(1);
        drawTrajectoryEdges(k);
        drawn.forEach(n => { if (sideOf(n.i)) drawTable(n); });
      } else drawn.forEach(drawTable);
      badges.forEach(b => { ctx.globalAlpha = b[3]; drawBadge(...b.slice(0, 3), k); });
      setA(1);
      if (SP.size) drawOrbits(k);
    }
    ctx.restore();

    // screen-space text: constellation names first, then band names (layer mode), then table names by
    // importance, skipping any that would overlap
    const taken = [], hits = [];
    const free = (x, y, w, h) => !taken.some(r => x < r[0] + r[2] && x + w > r[0] && y < r[1] + r[3] && y + h > r[1]);
    ctx.textAlign = 'center';
    // the name, count and composition bar above a disc. A constellation whose card is at level `count` or `frame` has no name
    // on it, so this label stays at full alpha and replaces it (drawn after the cards, below); the others fade with the stars
    const placed = a > 0 ? cardLayout(k) : null, bare = d => !!placed && placed.byKey.get(d.k).lv >= 4;
    // every card drawn is an obstacle for a bare constellation's label (it would print over the card's text). The label then tries,
    // in turn, eight places round its disc (below, the sides, above, nearest first, then a step farther, kept inside the stage),
    // first whole, then compact (name and count, no bar), the first that is free of cards and of the names already placed; it is skipped only when
    // none is (`labelShown: false` in the hook): the name stays in the Domains list, the
    // tooltip and the text summary
    const cardBoxes = placed && cardsOnAt(a) ? placed.items.filter(e => e.lv <= 3).map(e => [e.px - e.w / 2 + t.x, e.py - e.h / 2 + t.y, e.w, e.h, e.key]) : [];
    const onCard = (x, y, w, h, key) => cardBoxes.some(r => r[4] !== key && x < r[0] + r[2] && x + w > r[0] && y < r[1] + r[3] && y + h > r[1]);
    const discLabel = (d, alpha, counts = plural(d.n, L.tables), avoid = false) => {
      const sys = isSystem(d.k);   // a source system: 13 px, neutral (D-066)
      const [cx0, rim] = screen(d.x, d.y - d.r), fs = sys ? 13 : Math.max(13, Math.min(20, 10 + d.r * k / 25));
      const name = constellationLabel(d.k), font = `600 ${fs}px ${FONT}`;
      const sizeOf = compact => (compact ? [Math.max(textW(font, name), textW(`12px ${FONT}`, counts)) + 8, fs + 16] : [Math.max(textW(font, name), 80) + 8, fs + 22]);
      let sx = cx0, sy = rim - (byLayers ? NAME_LIFT : 0), compact = false, [w, bh] = sizeOf(false);
      if (avoid && onCard(sx - w / 2, sy - bh, w, bh, d.k)) {
        const [, mid] = screen(d.x, d.y), edge = d.r * k + 4, dirs = [[0, 1], [1, 0], [-1, 0], [1, 1], [-1, 1], [0, -1], [1, -1], [-1, -1]];
        const spot = [false, true].flatMap(c => {
          const [cw0, ch] = sizeOf(c), cw = Math.max(cw0, textW(`12px ${FONT}`, counts) + 8);   // the count line can be the wider
          return [0, 24, 60, 120, 200].flatMap(more => dirs.map(([ux, uy]) => {   // eight sides of the disc, then a step farther
            const n = Math.hypot(ux, uy), dist = edge + more;
            const x = cx0 + ux / n * (dist + Math.abs(ux) / n * cw / 2), y = mid + uy / n * (dist + Math.abs(uy) / n * ch / 2) + ch / 2;
            return { x: Math.max(cw / 2 + 2, Math.min(W - cw / 2 - 2, x)), y: Math.max(ch + 2, Math.min(H - 2, y)), c, w: cw, h: ch };
          }));
        }).find(o => free(o.x - o.w / 2, o.y - o.h, o.w, o.h) && !onCard(o.x - o.w / 2, o.y - o.h, o.w, o.h, d.k));
        if (!spot) return null;
        ({ x: sx, y: sy, c: compact, w, h: bh } = spot);
      }
      const up = compact ? 8 : 0;   // a compact label has no bar: its lines sit lower
      ctx.globalAlpha = alpha; ctx.textAlign = 'center';
      // a domain name in its colour, readable on the page (D-037); a layer name in the text colour; a source system's muted.
      // A 3 px outline in the page colour keeps a route from cutting a letter
      ctx.font = font; ctx.fillStyle = byLayers ? C.text : sys ? C.muted : CONTRAST.ink(DOM[d.k].color, C.bg);
      ctx.lineJoin = 'round'; ctx.lineWidth = 3; ctx.strokeStyle = C.bg; ctx.strokeText(name, sx, sy - 22 + up); ctx.lineJoin = 'miter';
      ctx.fillText(name, sx, sy - 22 + up);
      ctx.font = `12px ${FONT}`; ctx.fillStyle = C.muted;
      ctx.fillText(counts, sx, sy - 8 + up);
      // composition by type in the Types-list order (D-064: the cards' bar, `SUMMARIES` kinds), readable before any single star is
      let bx = sx - 40;
      if (!compact) SUMMARIES.get(d.k).kinds.forEach(([kind, c]) => { const bw = 80 * c / d.n; ctx.fillStyle = CONTRAST.edge(KIND[kind].color, C.bg); ctx.fillRect(bx, sy - 4, bw, 4); bx += bw; });
      taken.push([sx - w / 2, sy - bh, w, bh]);
      return { d, x: sx - w / 2, y: sy - bh, w, h: bh };
    };
    if (LA > 0) constellations.forEach(d => { if (!bare(d)) hits.push(discLabel(d, ctxAlpha(d) * LA)); });
    // a badge's pill is an obstacle for every name below: its number is never hidden (the far arc has no digits and
    // is no obstacle: from afar names are rare and the arc is a mark on the star's rim)
    if (k >= OVERVIEW_K && LA > 0) badges.forEach(([p, r, held]) => {
      const [bx, by] = screen(p.x + 0.71 * r, p.y - 0.71 * r);
      taken.push([bx, by - BADGE_H, badgeWidth(held), BADGE_H]);
    });
    if (byLayers && k >= OVERVIEW_K && LA > 0) constellations.forEach(d => { setA(ctxAlpha(d)); drawBandNames(d, screen, free, taken, k); });
    setA(1);
    const around = SP.size && LA > 0 ? drawShownNames(screen, taken, k) : [];
    const named = LA > 0 ? [...around, ...(cards ? [] : drawNames(orderLabels(labels, k), screen, free, taken, k))] : [];
    // the summary cards, over everything: drawn at alpha a, their headers are the drag handles while cards are on
    const drawnCards = placed ? placed.items.map(e => (e.g ? drawGroup : drawSummary)(e, a, onScreen ? overCard : null)) : [];
    const bareHits = constellations.filter(bare).map(d => discLabel(d, ctxAlpha(d), SUMMARIES.get(d.k).counts, true));
    constellations.filter(bare).forEach((d, i) => {   // what became of each bare label (the hook says it)
      const rec = drawnCards.find(c => c.key === d.k), h = bareHits[i];
      if (rec) { rec.labelShown = !!h; rec.labelAt = h ? { x: h.x, y: h.y, w: h.w, h: h.h } : null; }
    });
    ctx.globalAlpha = 1; ctx.textAlign = 'left';
    if (!onScreen) return;
    drawnNames = named;
    summaryAll = drawnCards; summaryHits = drawnCards.filter(c => c.drawn);   // a card at level count / frame is not drawn: no hit either
    labelHits = cardsOnAt(a) ? [...drawnCards.filter(c => !c.label).map(c => ({ d: c.d, ...c.header })), ...bareHits.filter(Boolean)] : [...hits, ...bareHits.filter(Boolean)];
    perf.draw = performance.now() - t0;
  }
  // the view as shown (filters, zoom, detail level, search mark, trajectory) as a PNG at 2 x the screen
  // resolution; hover is pointer state, like the tooltip, so it is left out. null when nothing is drawn.
  function image() {
    if (!visible.length) return null;
    const W = stage.clientWidth, H = stage.clientHeight, s = EXPORT.scale(W, H), c = document.createElement('canvas');
    c.width = Math.round(W * s); c.height = Math.round(H * s);
    const pointer = hover, focus = routeFocus;   // hover and focus are pointer-like state: left out (D-021, D-064)
    hover = null; routeFocus = null;
    try { draw(c.getContext('2d'), s); } finally { hover = pointer; routeFocus = focus; }
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
  const constellationLabel = key => (key === GROUP ? T.systems : labelOf(state.by === 'layers' ? LAYER[key] : DOM[key]));
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
    const main = n => MAIN.get(n.i) ?? Infinity, overview = HAS_CORE && k < OVERVIEW_K;
    const rest = labels.filter(n => !sideOf(n.i) && (!overview || (roleOf(n) === 'core' && main(n) < OVERVIEW_NAMES)))
      .sort(nameOrder);
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
      setA(traj && !side ? DIM : 1);
      ctx.fillStyle = 'rgba(245,246,248,.85)'; ctx.fillRect(x, y, w, h);
      ctx.fillStyle = strong || side ? C.text : C.muted;
      lines.forEach((s, j) => ctx.fillText(s, sx, y + 11 + LINE_H * j));
    }
    setA(1);
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
    if (k > OVERVIEW_K) {
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
  // kind per table (FOLD_ROWS rows, then "+ N"); below OVERVIEW_K only the separator is drawn
  function drawFolded(b, x, y, k) {
    const top = y + b.top;
    ctx.strokeStyle = C.edge; ctx.lineWidth = 1 / Math.min(k, 1);
    ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x + b.w, top); ctx.stroke();
    if (k <= OVERVIEW_K) return;
    ctx.fillStyle = C.text; ctx.font = `600 9px ${FONT}`; ctx.fillText(plural(b.held.length, L.foldedN), x + 5, top + 11);
    ctx.font = `9px ${FONT}`;
    b.held.slice(0, FOLD_ROWS).forEach((i, j) => {
      const n = N[i], base = top + FOLD_HEAD + 9 + j * 11, label = labelOf(KIND[n.kind]);
      cardDot(x + 8, base - 3, KIND[n.kind].color, 2.5, 1 / k);
      ctx.fillStyle = C.text; ctx.fillText(n.name, x + 14, base);
      ctx.fillStyle = C.muted; ctx.fillText(label, x + b.w - 5 - ctx.measureText(label).width, base);
    });
    const more = overflow(b.held.length, FOLD_ROWS);
    if (more) { ctx.fillStyle = C.muted; ctx.fillText(more, x + 5, top + FOLD_HEAD + 9 + FOLD_ROWS * 11); }
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
    ctx.save(); ctx.strokeStyle = C.muted; setA(0.6); ctx.lineWidth = 1 / k; ctx.setLineDash([3 / k, 3 / k]);
    orbits.forEach(o => { ctx.beginPath(); ctx.arc(o.x, o.y, o.r, 0, 7); ctx.stroke(); });
    ctx.restore();
    SP.forEach((p, i) => {
      const n = N[i], side = sideOf(i), r = Math.max(starR(n), (side ? 3 : 2.5) / k);
      setA(traj && !side ? DIM : 1);
      ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.arc(p.x, p.y, r + 2 / k, 0, 7); ctx.fill();
      drawStar(n, p, KIND[n.kind].color, i === hover || i === found, side, k);
    });
    setA(1);
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
      setA(traj && !sideOf(i) ? DIM : 1);
      ctx.textAlign = 'left'; ctx.lineJoin = 'round'; ctx.lineWidth = 3; ctx.strokeStyle = '#ffffff';
      ctx.strokeText(n.name, x + 3, y + 10); ctx.fillStyle = C.text; ctx.fillText(n.name, x + 3, y + 10);
      ctx.lineJoin = 'miter'; ctx.textAlign = 'center';
    });
    setA(1);
    return out;
  }
  // the lineage edges of the trajectory, parent -> child, at every zoom and whatever the Links selector shows
  function drawTrajectoryEdges(k) {
    const far = k < OVERVIEW_K, lw = (far ? 1.5 : 2) / k, head = (far ? 7 : 8) / k;
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

  // ---------------------------------------------------------------- summary cards (M8.3, D-063, D-064)
  // Content, decided here from the payload: per constellation its table count (folded tables included: never reduced),
  // its entities, one row per layer (layer mode: per domain) holding the tables whose own layer (domain) it is, the kinds
  // of each row in the Types-list order, and its main tables. Also the star cell and the two scales of the cross-fade.
  // the composition by kind of some tables, [[kind key, count]] in the Types-list order (`kindOrder`): the one computation, read
  // by a card's rows and bar (level 2) and by the bar above a disc (`discLabel`)
  const kindMix = list => kindCounts(kindOrder, list).map(([k, n]) => [k.key, n]);
  const cardCounts = s => plural(s.n, L.tables) + (s.entities ? ` · ${plural(s.entities, T.entitiesN)}` : '');
  function summarise() {
    const t0 = performance.now(), G = grouping();
    const rank = new Map(G.rowList.map((it, i) => [it.key, i]));
    CELL = d3.median(drawn, n => Math.sqrt(B[n.i].w * B[n.i].h)) || 1;
    summaryScale = SUMMARY_CELL / CELL; starsScale = summaryScale * SUMMARY_FADE;
    SUMMARIES = new Map();
    for (const [key, members] of d3.group(visible, G.of)) {
      const ents = members.filter(isEntity).length;
      const rows = [...d3.group(members, G.rowOf)].sort((a, b) => rank.get(a[0]) - rank.get(b[0])).map(([rk, ms]) => ({
        key: rk, label: labelOf(G.rowList[rank.get(rk)]), n: ms.length,
        kinds: kindMix(ms) }));
      const s = { key, label: constellationLabel(key), n: members.length, kinds: kindMix(members), entities: state.fold && ents ? ents : null, rows,
        main: overviewOrder(members.filter(n => !foldedSet.has(n.i))).slice(0, SUMMARY_NAMES).map(n => n.i) };
      SUMMARIES.set(key, { ...s, counts: cardCounts(s) });
    }
    if (GROUPED.length) {   // the one card of every source system (D-066): a row per system, in stack order, top to bottom
      const rows = [...GROUPED].sort(stackOrder).map(d => ({ key: d.k, label: constellationLabel(d.k), n: SUMMARIES.get(d.k).n }));
      const n = d3.sum(rows, r => r.n);
      SUMMARIES.set(GROUP, { key: GROUP, label: T.systems, n, rows, main: [], entities: null, g: true,
        counts: `${plural(rows.length, T.systemsN)} · ${plural(n, L.tables)}` });
    }
    perf.cards = performance.now() - t0;
  }
  // 0 under prefers-reduced-motion: reduce, else ms: the camera's animations (zoomTo, frame) jump instead of gliding
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const motionMs = ms => (reduceMotion.matches ? 0 : ms);
  // the card layer's opacity at scale k: 1 up to summaryScale, 0 from starsScale, linear in log k between. A pure function
  // of the zoom: no timer, no state, the same image zooming in and out
  const summaryAlpha = k => Math.max(0, Math.min(1, Math.log(starsScale / k) / Math.log(SUMMARY_FADE)));
  const cardsOnAt = a => a >= CARDS_ALPHA;   // at card alpha a, the cards are the ones in play
  const cardsOn = () => cardsOnAt(summaryAlpha(t.k));   // the card interactions; below CARDS_ALPHA the stars' ones

  // Card geometry, in screen px at constant text size (13 px name, 11 px otherwise). A card's content has levels, from most
  // to least: 0 rows and main tables, 1 rows, 2 one bar by kind, 3 name and tables, 4 the count, 5 a frame (D-063).
  const CARD = { PAD_X: 8, PAD_Y: 6, NAME: 16, LINE: 14, SEC: 4, ROW: 22, BAR: 6, BAR_MIN: 6, SEG_MIN: 2, W_MIN: 112, W_MAX: 176,
                 NAMES_MIN: 3, RADIUS: 6, BORDER: 2, BORDER_HOVER: 3, GAP: 2, TRAJ_ROOM: 8, ITER: 40, DAMP: 0.6, ROUNDS: 30, WORK: 600,
                 GROUP_ROW: 17, GROUP_ROWS: 8, GROUP_W: [150, 190], GROUP_NAME_W: 150 };   // the group card (M8.4): rows, widths
  const LEVELS = ['rows', 'rows', 'bar', 'name', 'count', 'frame'];
  const F_NAME = `600 13px ${FONT}`, F_TEXT = `11px ${FONT}`;
  const TW = new Map();   // widths of texts by font: asked for every card in every frame
  function textW(font, text) {
    const key = font + '|' + text;
    if (TW.size > 4000) TW.clear();
    if (!TW.has(key)) { ctx.font = font; TW.set(key, ctx.measureText(text).width); }
    return TW.get(key);
  }
  // `text` cut with an ellipsis to fit `w` px
  function cutText(font, text, w) {
    if (textW(font, text) <= w) return text;
    let lo = 0, hi = text.length;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (textW(font, text.slice(0, mid) + '…') <= w) lo = mid; else hi = mid - 1; }
    return text.slice(0, Math.max(1, lo)) + '…';
  }
  // what the trajectory holds of each constellation: Map(key -> { start, up, down }), tables counted by side
  function trajHolds() {
    const m = new Map(), G = grouping();
    if (!traj) return m;
    const at = i => { const key = G.of(N[i]); if (!m.has(key)) m.set(key, { start: false, up: 0, down: 0 }); return m.get(key); };
    at(traj.start).start = true;
    traj.up.forEach((_, i) => at(i).up++); traj.down.forEach((_, i) => at(i).down++);
    return m;
  }
  const trajLine = h => [h.start ? L.lgStart : null, h.up + h.down ? trajectoryCounts(trajOpts.direction, h.up, h.down) : null].filter(Boolean).join(' · ');
  // the width of a card: its widest line and a margin, between W_MIN and W_MAX (the counts line is never cut)
  function cardWidth(e) {
    const s = e.s, dot = state.by === 'layers' ? 12 : 0;
    if (e.g) {   // the group card: a name, a counts line and one line per system, between GROUP_W
      const w = Math.max(textW(F_NAME, s.label), textW(F_TEXT, s.counts), textW(F_TEXT, e.line),
        ...s.rows.slice(0, CARD.GROUP_ROWS).map(r => textW(F_TEXT, r.label) + 12 + textW(F_TEXT, num(r.n)))) + 2 * CARD.PAD_X;
      return Math.max(CARD.GROUP_W[0], Math.min(CARD.GROUP_W[1], Math.ceil(w)));
    }
    const w = Math.max(textW(F_NAME, s.label), textW(F_TEXT, s.counts), textW(F_TEXT, e.line),
      ...s.rows.map(r => dot + textW(F_TEXT, r.label) + 12 + textW(F_TEXT, num(r.n))),
      ...s.main.map(i => 14 + Math.min(textW(F_TEXT, N[i].name), 100))) + 2 * CARD.PAD_X;
    return Math.max(CARD.W_MIN, Math.min(CARD.W_MAX, Math.ceil(w)), Math.ceil(textW(F_TEXT, s.counts)) + 2 * CARD.PAD_X);
  }
  // [w, h] of a card at its level; sets e.names, the main tables listed: 3 to 5 as the disc's screen height allows
  function cardSize(e) {
    const line = e.line && e.lv <= 3 ? CARD.LINE : 0, m = e.s.main.length;
    e.names = 0;
    if (e.g) {   // the group card: rows, then its name and counts only (it never becomes a bare pill: it carries every name)
      if (e.lv >= 3) return [CARD.GROUP_NAME_W, 42 + line];
      const shown = Math.min(e.s.rows.length, CARD.GROUP_ROWS), more = e.s.rows.length > shown ? CARD.LINE : 0;
      return [e.cw, CARD.PAD_Y + CARD.NAME + CARD.LINE + line + CARD.SEC + CARD.GROUP_ROW * shown + more + CARD.PAD_Y];
    }
    if (e.lv === 5) return [20, 14];
    if (e.lv === 4) return [40, 24];
    if (e.lv === 3) return [96, 42 + line];
    if (e.lv === 2) return [e.cw, 52 + line];
    const base = CARD.PAD_Y + CARD.NAME + CARD.LINE + line + CARD.SEC + CARD.ROW * e.s.rows.length + CARD.PAD_Y;
    if (e.lv === 0) e.names = Math.max(Math.min(CARD.NAMES_MIN, m), Math.min(SUMMARY_NAMES, m, Math.floor((2 * e.r - base - CARD.SEC) / CARD.LINE)));
    return [e.cw, e.names ? base + CARD.SEC + CARD.LINE * e.names : base];
  }
  // Puts every card on its anchor, then pushes overlapping pairs apart (CARD.ITER passes): each pair along the line between
  // its centres by the distance that clears the nearer axis, the smaller card moving more, the pushes of a pass summed and
  // applied at CARD.DAMP. Deterministic, no state. Sets e.px, e.py (centre), e.disp (distance from the anchor), e.over.
  function relaxCards(items) {
    items.forEach(e => {
      [e.w, e.h] = cardSize(e);
      const room = e.tj ? CARD.TRAJ_ROOM : 0;
      e.bw = e.w + 2 * room; e.bh = e.h + 2 * room; e.px = e.ax; e.py = e.ay;
    });
    const n = items.length, mv = new Float64Array(2 * n), order = items.map((_, i) => i);
    for (let it = 0; it < CARD.ITER; it++) {
      mv.fill(0);
      let any = false;
      // sweep by left edge: the candidates of a card are the cards that start before it ends, so a pass costs about
      // O(n log n) when the cards are spread out, not O(n^2) (about 50 domains)
      order.sort((p, q) => (items[p].px - items[p].bw / 2) - (items[q].px - items[q].bw / 2) || p - q);
      for (let oi = 0; oi < n; oi++) for (let oj = oi + 1; oj < n; oj++) {
        const first = items[order[oi]];
        if (items[order[oj]].px - items[order[oj]].bw / 2 >= first.px + first.bw / 2 + CARD.GAP) break;
        const i = Math.min(order[oi], order[oj]), j = Math.max(order[oi], order[oj]), a = items[i], b = items[j];
        let dx = b.px - a.px; const dy = b.py - a.py;
        const sx = (a.bw + b.bw) / 2 + CARD.GAP, sy = (a.bh + b.bh) / 2 + CARD.GAP;
        if (sx - Math.abs(dx) <= 0 || sy - Math.abs(dy) <= 0) continue;
        any = true;
        if (Math.abs(dx) < 1e-6 && Math.abs(dy) < 1e-6) dx = 1e-3;   // two cards on one point: the later one goes right
        const dist = Math.hypot(dx, dy), ux = dx / dist, uy = dy / dist;
        const s = Math.min(Math.abs(dx) > 1e-6 ? sx / Math.abs(dx) : Infinity, Math.abs(dy) > 1e-6 ? sy / Math.abs(dy) : Infinity);
        const push = (s - 1) * dist, wa = b.w * b.h / (a.w * a.h + b.w * b.h);
        mv[2 * i] -= ux * push * wa; mv[2 * i + 1] -= uy * push * wa;
        mv[2 * j] += ux * push * (1 - wa); mv[2 * j + 1] += uy * push * (1 - wa);
      }
      if (!any) break;
      items.forEach((e, i) => { e.px += mv[2 * i] * CARD.DAMP; e.py += mv[2 * i + 1] * CARD.DAMP; });
    }
    items.forEach(e => { e.disp = Math.hypot(e.px - e.ax, e.py - e.ay); e.over = 0; });
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
      const a = items[i], b = items[j];
      if ((a.bw + b.bw) / 2 + CARD.GAP - Math.abs(a.px - b.px) > 0.5 && (a.bh + b.bh) / 2 + CARD.GAP - Math.abs(a.py - b.py) > 0.5) { a.over++; b.over++; }
    }
  }
  // A card stays on its constellation: its centre within the disc's screen radius and clear of every other card. While one
  // is not, the worst offender (shift over radius, an overlap weighing 10) drops one level and the push restarts, at most
  // CARD.ROUNDS times (fewer with many constellations: a round costs up to n² when cards crowd (the sweep makes it about n log n
  // when they are spread), so CARD.WORK / n rounds keep the total about linear in n), then every offender goes to its frame.
  function settleCards(items) {
    const rounds = Math.max(1, Math.min(CARD.ROUNDS, Math.floor(CARD.WORK / items.length)));
    for (let round = 1; ; round++) {
      relaxCards(items);
      const score = e => e.disp / e.r + 10 * e.over;
      const last = e => (e.g ? 3 : 5);   // the group card stops at its name
      const offends = e => e.disp > e.r || e.over;
      const bad = items.filter(e => e.lv < last(e) && offends(e)).sort((a, b) => score(b) - score(a));
      if (!bad.length) {   // a card already at its last level still off its disc: the nearest card that can give a level gives it
        const stuck = items.filter(e => e.lv >= last(e) && offends(e)).sort((a, b) => score(b) - score(a))[0];
        const near = stuck && items.filter(e => e.lv < last(e) && e !== stuck)
          .sort((a, b) => Math.hypot(a.px - stuck.ax, a.py - stuck.ay) - Math.hypot(b.px - stuck.ax, b.py - stuck.ay))[0];
        if (!near) return;
        bad.push(near);
      }
      if (round >= rounds) {   // out of rounds: every offender to its last level, and the group card (the biggest) to its name
        bad.forEach(e => { e.lv = last(e); });
        items.forEach(e => { if (e.g) e.lv = 3; });
        relaxCards(items); return;
      }
      bad[0].lv = bad[0].g ? 3 : bad[0].lv + 1;
    }
  }
  // The place of every card at scale k, in screen px from the origin of the camera's translation (the anchor of a card is
  // its disc's centre, d.x * k): a pure function of the layout, the zoom, the moved constellations and the trajectory,
  // so cached by those; the one place that places cards. -> { items, byKey }
  let cardCache = null, dragRev = 0;   // dragRev: bumped when a constellation moves without a layout
  function cardLayout(k) {
    const c = cardCache;
    if (c && c.k === k && c.runs === layoutRuns && c.rev === dragRev && c.traj === traj) return c;
    const t0 = performance.now(), holds = trajHolds(), grouped = new Set(GROUPED.map(d => d.k));
    const item = (d, extra) => {
      const h = holds.get(d.k), s = SUMMARIES.get(d.k), held = h && (h.start || h.up + h.down > 0);
      const e = { d, key: d.k, s, ax: d.x * k, ay: d.y * k, r: d.r * k, tj: held ? h : null, line: held ? trajLine(h) : '', lv: s.main.length ? 0 : 1, ...extra };
      e.cw = cardWidth(e);
      return e;
    };
    const items = constellations.filter(d => !grouped.has(d.k)).map(d => item(d, {}));
    let group = null;
    if (GROUPED.length) {   // the group card: anchored on the middle of the systems' box, "on" it within half its diagonal
      placeGroup();
      const parts = GROUPED.map(d => holds.get(d.k)).filter(Boolean);
      holds.set(GROUP, parts.length ? { start: parts.some(h => h.start), up: d3.sum(parts, h => h.up), down: d3.sum(parts, h => h.down) } : undefined);
      group = item(GROUPD, { g: true, lv: 0 });
      items.push(group);
    }
    settleCards(items);
    const byKey = new Map(items.map(e => [e.key, e]));
    if (group) GROUPED.forEach(d => byKey.set(d.k, group));
    cardCache = { k, runs: layoutRuns, rev: dragRev, traj, items, byKey };
    perf.cardLayout = performance.now() - t0;
    return cardCache;
  }
  // the group's pseudo constellation: the bounding circle of its members (world), refreshed whenever one moves
  // the bounding box of some constellations' discs, `box` ([x0, y0, x1, y1]), and its circle (`x`, `y`, `r`): the group's, or the one the
  // text summary's Zoom on the source systems frames
  function groupBox(members) {
    const x0 = d3.min(members, d => d.x - d.r), x1 = d3.max(members, d => d.x + d.r), y0 = d3.min(members, d => d.y - d.r), y1 = d3.max(members, d => d.y + d.r);
    return { x: (x0 + x1) / 2, y: (y0 + y1) / 2, r: Math.hypot(x1 - x0, y1 - y0) / 2, box: [x0, y0, x1, y1] };
  }
  const placeGroup = () => Object.assign(GROUPD, { members: GROUPED, ...groupBox(GROUPED) });
  // the world rectangle ({x, y, w, h}, top left) of d's card as cardLayout places it now: the one place that says where a
  // constellation's outline is (the routes' ends, the obstacles of a route and the group card build on it). A source system
  // standing in the group card has the group card's rectangle.
  function summaryRect(d) {
    const e = cardLayout(t.k).byKey.get(d.k), k = t.k;
    return { x: (e.px - e.w / 2) / k, y: (e.py - e.h / 2) / k, w: e.w / k, h: e.h / k };
  }
  // where a route toward `toward` ({x, y}, world) leaves d (D-067): between the point of its disc toward `toward` (a = 0) and the
  // point where the ray from its card's centre toward `toward` leaves the card's rectangle (a = 1), by the card alpha `a`:
  // continuous in the zoom, so a route never jumps
  function edgeOf(d, toward, a) {
    const dx = toward.x - d.x, dy = toward.y - d.y, len = Math.hypot(dx, dy) || 1;
    const disc = [d.x + dx / len * d.r, d.y + dy / len * d.r];
    if (!a) return disc;
    const r = summaryRect(d), cx = r.x + r.w / 2, cy = r.y + r.h / 2, ex = toward.x - cx, ey = toward.y - cy;
    const s = Math.min(ex ? r.w / 2 / Math.abs(ex) : Infinity, ey ? r.h / 2 / Math.abs(ey) : Infinity);
    if (!isFinite(s)) return disc;
    return [disc[0] + a * (cx + ex * s - disc[0]), disc[1] + a * (cy + ey * s - disc[1])];
  }

  // ---------------------------------------------------------------- routes (M8.4, D-067)
  // A route is the one line between two constellations, carrying their links. Below OVERVIEW_K it is drawn from outline to outline,
  // as a curve around the other constellations, with an arrowhead at the reader (net lineage direction), dashed when it carries
  // relations only; by default only the strongest ones, all of a constellation's on hover or keyboard focus.
  const ROUTE = { W_MIN: 1, W_MAX: 3, W_SAT: 128, BOW: 0.08, MARGIN: 6, PASSES: 6, WAYPOINTS: 4, SAMPLES: 24, CLEAR: 12, GAP: 2,
                  DIM: 0.15, DETOUR_WORK: 12000, BUILDS: 250, DASH: [6, 4], INK: '#7b8494', INK_HI: '#475569', HIT: 6 };
  const routeInk = hi => CONTRAST.edge(hi ? ROUTE.INK_HI : ROUTE.INK, C.bg);
  const routeWidth = c => ROUTE.W_MIN + (ROUTE.W_MAX - ROUTE.W_MIN) * Math.min(1, Math.log2(Math.max(1, c)) / Math.log2(ROUTE.W_SAT));
  // the pseudo constellation of the group card: key GROUP, the bounding circle of its members (world); refreshed with each card layout
  const GROUPD = { k: GROUP, members: [], x: 0, y: 0, r: 0 };
  const isMember = key => GROUPED.some(d => d.k === key);
  // the constellation (or the group) a route's end names
  const endOf = key => (key === GROUP ? GROUPD : constellations.find(d => d.k === key));

  // The routes through the group card (D-066): while it is drawn, the routes between a source system and a business constellation are
  // summed per business constellation into one bundled route from the group; routes between two systems are not drawn. Built once per
  // layout. -> { bundles, biz, all, strong }: the bundled routes, the routes between business constellations, both, the Set kept
  function bundled() {
    if (BUNDLE) return BUNDLE;
    const sys = new Set(GROUPED.map(d => d.k)), per = new Map(), biz = [];
    routes.forEach(r => {
      const sa = sys.has(r.source), sb = sys.has(r.target);
      if (sa && sb) return;
      if (!sa && !sb) { biz.push(r); return; }
      const other = sa ? r.target : r.source, up = sa ? r.source : r.target;
      if (!per.has(other)) per.set(other, { source: GROUP, target: other, c: 0, rel: 0, lin: 0, f: 0, strong: false, systems: new Map() });
      const b = per.get(other);
      b.c += r.c; b.rel += r.rel; b.lin += r.lin; b.f += sa ? r.f : -r.f;   // f > 0: from the group to `other`
      b.systems.set(up, (b.systems.get(up) || 0) + r.c);
    });
    const bundles = [...per.values()];
    bundles.forEach(b => { b.dir = b.lin ? netFlow(b) : 0; });
    const all = [...bundles, ...biz];
    BUNDLE = { bundles, biz, all, strong: strongRoutes(all) };
    BUNDLE.bundles.forEach(b => { b.strong = BUNDLE.strong.has(b); });
    return BUNDLE;
  }
  const groupShown = a => GROUPED.length > 0 && cardsOnAt(a);   // the bundled graph is the one in play
  // how many routes the default set holds, of how many (the meta line): the bundled graph while the group card is on
  function routeCounts(a) {
    const list = groupShown(a) ? bundled().all : routes, strong = groupShown(a) ? bundled().strong : null;
    return { total: list.length, shown: state.allRoutes ? list.length : list.filter(r => (strong ? strong.has(r) : r.strong)).length };
  }
  // The routes to draw at card alpha `a`, with their ends and alpha: the default set (strongest, or all), plus every route of the
  // focused constellation. Source systems in the group card fade as 1 - a into the bundled routes. -> { specs, lit }
  function routeSpecs(a, focus) {
    const grouped = GROUPED.length > 0 && a > 0, on = groupShown(a), B = grouped ? bundled() : null, sys = new Set(GROUPED.map(d => d.k));
    const key = on && focus && isMember(focus) ? GROUP : focus;   // the group stands for its systems while it is drawn
    const specs = [], involved = new Set(key ? [key] : []);
    // the group heading without the group card (stars scale) lights every route of every system
    const isKey = k => (key === GROUP && !on ? sys.has(k) : k === key), touches = r => isKey(r.source) || isKey(r.target);
    const add = (r, alpha, bundle, own) => {
      const from = r.dir < 0 ? r.target : r.source, to = r.dir < 0 ? r.source : r.target;
      const hi = !!key && touches(r) && (!own || !on);
      if (hi) { involved.add(r.source); involved.add(r.target); }
      specs.push({ r, alpha, bundle, hi, from: endOf(from), to: endOf(to), fa: grouped && own && sys.has(from) ? 0 : a, ta: grouped && own && sys.has(to) ? 0 : a });
    };
    const wanted = (r, kept) => state.allRoutes || kept;
    routes.forEach(r => {
      const own = grouped && (sys.has(r.source) || sys.has(r.target));   // a route of a system inside the group card
      if (own) { if (a < 1 && (wanted(r, r.strong) || (!on && key && touches(r)))) add(r, 1 - a, false, true); return; }
      const kept = on ? B.strong.has(r) : r.strong, hi = key && touches(r);
      if (wanted(r, kept) || hi) add(r, 1, false, false);
    });
    if (grouped) B.bundles.forEach(b => { if (wanted(b, B.strong.has(b)) || (key && on && (b.source === key || b.target === key))) add(b, a, true, false); });
    // what is lit: the focus, its neighbours, and the systems of the group when it is
    const lit = new Set(involved);
    if (lit.has(GROUP)) GROUPED.forEach(d => lit.add(d.k));
    return { specs, lit, focus: key };
  }

  // ---- the path of one route
  // The obstacles of a route, in screen px from the camera's translation: the drawn outline of every constellation (its disc while
  // stars are on, its card while cards are; the group card for the systems it holds), except the keys in `skip`
  function outlines(a, k) {
    const placed = a > 0 ? cardLayout(k) : null, cards = cardsOnAt(a), out = [];
    const disc = d => out.push({ shape: 'disc', key: d.k, x: d.x * k, y: d.y * k, r: d.r * k });
    constellations.forEach(d => {
      if (!cards) return disc(d);
      if (GROUPED.includes(d)) return;
      const e = placed.byKey.get(d.k);
      if (e.lv >= 4 && !e.tj) return disc(d);
      out.push({ shape: 'card', key: d.k, x: e.px - e.w / 2, y: e.py - e.h / 2, w: e.w, h: e.h });
    });
    if (cards && GROUPED.length) {
      const e = placed.byKey.get(GROUP);
      out.push({ shape: 'card', key: GROUP, x: e.px - e.w / 2, y: e.py - e.h / 2, w: e.w, h: e.h });
    }
    return out;
  }
  // how deep the point (x, y) lies inside obstacle o inflated by `m` px (0: outside)
  function depth(o, x, y, m) {
    if (o.shape === 'disc') return Math.max(0, o.r + m - Math.hypot(x - o.x, y - o.y));
    const d = Math.min(x - (o.x - m), o.x + o.w + m - x, y - (o.y - m), o.y + o.h + m - y);
    return Math.max(0, d);
  }
  // Catmull-Rom (centripetal) through the points, as cubic Béziers [[p0, c1, c2, p3], ...]; two points make a straight segment
  function smooth(pts) {
    if (pts.length === 2) { const [p, q] = pts; return [[p, [p[0] + (q[0] - p[0]) / 3, p[1] + (q[1] - p[1]) / 3], [p[0] + 2 * (q[0] - p[0]) / 3, p[1] + 2 * (q[1] - p[1]) / 3], q]]; }
    const ext = [[2 * pts[0][0] - pts[1][0], 2 * pts[0][1] - pts[1][1]], ...pts, [2 * pts[pts.length - 1][0] - pts[pts.length - 2][0], 2 * pts[pts.length - 1][1] - pts[pts.length - 2][1]]];
    const dist = (p, q) => Math.max(1e-6, Math.sqrt(Math.hypot(q[0] - p[0], q[1] - p[1])));
    const segs = [];
    for (let i = 1; i < ext.length - 2; i++) {
      const [p0, p1, p2, p3] = [ext[i - 1], ext[i], ext[i + 1], ext[i + 2]], d1 = dist(p0, p1), d2 = dist(p1, p2), d3 = dist(p2, p3);
      const c1 = [0, 1].map(j => (d1 * d1 * p2[j] - d2 * d2 * p0[j] + (2 * d1 * d1 + 3 * d1 * d2 + d2 * d2) * p1[j]) / (3 * d1 * (d1 + d2)));
      const c2 = [0, 1].map(j => (d3 * d3 * p1[j] - d2 * d2 * p3[j] + (2 * d3 * d3 + 3 * d3 * d2 + d2 * d2) * p2[j]) / (3 * d3 * (d3 + d2)));
      segs.push([p1, c1, c2, p2]);
    }
    return segs;
  }
  const bezier = ([p0, c1, c2, p3], u) => {
    const v = 1 - u, a = v * v * v, b = 3 * v * v * u, c = 3 * v * u * u, d = u * u * u;
    return [a * p0[0] + b * c1[0] + c * c2[0] + d * p3[0], a * p0[1] + b * c1[1] + c * c2[1] + d * p3[1]];
  };
  const sampleCurve = segs => {
    const pts = [segs[0][0]];
    segs.forEach(sg => { for (let i = 1; i <= ROUTE.SAMPLES; i++) pts.push(bezier(sg, i / ROUTE.SAMPLES)); });
    return pts;
  };
  // Where a route of `spec` runs: its drawn polyline (screen px from the camera's translation), deterministic. The ends leave the
  // outlines toward the first waypoint (else the other end). Unobstructed first (a curve bowed to the right of lower key -> higher
  // key, so two routes never coincide); else up to ROUTE.PASSES passes, each taking the first obstacle the curve enters and adding a
  // waypoint beside it on the side that penetrates less (at most ROUTE.WAYPOINTS); when none clears, the least penetrating
  // candidate is kept and the route is `blocked`. Never loops, never throws.
  function routePath(spec, obstacles, k) {
    const skip = new Set([spec.from.k, spec.to.k]);
    if (isMember(spec.from.k) || isMember(spec.to.k)) skip.add(GROUP);
    const obs = obstacles.filter(o => !skip.has(o.key)), world = p => ({ x: p[0] / k, y: p[1] / k });
    const centre = d => [d.x * k, d.y * k];
    const ends = wps => {
      const next = wps.length ? wps[0] : centre(spec.to), prev = wps.length ? wps[wps.length - 1] : centre(spec.from);
      return [edgeOf(spec.from, world(next), spec.fa).map(v => v * k), edgeOf(spec.to, world(prev), spec.ta).map(v => v * k)];
    };
    // how deep the polyline runs into the obstacles (sum over its samples): `sum` weighs a real crossing 100 times a graze of the
    // ROUTE.MARGIN around an outline, so a curve that only grazes beats one that crosses; `worst` is the obstacle run into most
    const depthInto = (o, pts, m) => {
      const [x0, y0, x1, y1] = o.shape === 'disc' ? [o.x - o.r - m, o.y - o.r - m, o.x + o.r + m, o.y + o.r + m] : [o.x - m, o.y - m, o.x + o.w + m, o.y + o.h + m];
      let own = 0;
      for (let i = 0; i < pts.length; i++) {   // the bounding box first: most samples are far from most obstacles
        const x = pts[i][0], y = pts[i][1];
        if (x > x0 && x < x1 && y > y0 && y < y1) own += depth(o, x, y, m);
      }
      return own;
    };
    const penetration = pts => {
      let sum = 0, worst = null, most = 0, crossing = 0;
      obs.forEach(o => {
        const real = depthInto(o, pts, 0), own = real * 100 + depthInto(o, pts, ROUTE.MARGIN);
        crossing += real; sum += own;
        if (own > most) { most = own; worst = o; }
      });
      return { sum, worst, crossing };
    };
    const [A0, B0] = ends([]), len = Math.hypot(B0[0] - A0[0], B0[1] - A0[1]) || 1, u = [(B0[0] - A0[0]) / len, (B0[1] - A0[1]) / len];
    const nrm = [-u[1], u[0]];   // the visual right of the chord's direction (screen y down)
    const sign = spec.from.k < spec.to.k ? 1 : -1;
    const bowed = (() => {
      const q = [(A0[0] + B0[0]) / 2 + sign * nrm[0] * ROUTE.BOW * len, (A0[1] + B0[1]) / 2 + sign * nrm[1] * ROUTE.BOW * len];
      const c1 = [A0[0] + 2 / 3 * (q[0] - A0[0]), A0[1] + 2 / 3 * (q[1] - A0[1])], c2 = [B0[0] + 2 / 3 * (q[0] - B0[0]), B0[1] + 2 / 3 * (q[1] - B0[1])];
      return sampleCurve([[A0, c1, c2, B0]]);
    })();
    const done = c => ({ pts: c.pts, blocked: c.crossing > 0 });
    const first = { pts: bowed, ...penetration(bowed), wps: [] };
    if (first.sum === 0) return done(first);
    const build = wps => {
      builds++;
      const [A, B] = ends(wps), pts = sampleCurve(smooth([A, ...wps, B]));
      return { pts, ...penetration(pts), wps };
    };
    const proj = p => (p[0] - A0[0]) * u[0] + (p[1] - A0[1]) * u[1];
    // Waypoints, by a small depth-first search: the obstacle the curve runs deepest into gets a waypoint on its circle (a card: the
    // circle round it), at the middle of the arc the route would follow (the direction between the ends as seen from its centre) or
    // on the other side; each side is tried, down to ROUTE.WAYPOINTS of them; the first curve that clears everything wins, else
    // the least penetrating one (the route is then `blocked` if it still crosses an outline)
    const search = cand => {
      if (cand.sum === 0 || cand.wps.length >= ROUTE.WAYPOINTS || builds >= ROUTE.BUILDS) return cand;   // BUILDS: a fixed budget per layout, so a hairball stays cheap
      const o = cand.worst, c0 = o.shape === 'disc' ? [o.x, o.y] : [o.x + o.w / 2, o.y + o.h / 2];
      const R = (o.shape === 'disc' ? o.r + ROUTE.MARGIN : Math.hypot(o.w / 2 + ROUTE.MARGIN, o.h / 2 + ROUTE.MARGIN)) + ROUTE.CLEAR;
      const unit = p => { const l = Math.hypot(p[0] - c0[0], p[1] - c0[1]) || 1; return [(p[0] - c0[0]) / l, (p[1] - c0[1]) / l]; };
      const ua = unit(A0), ub = unit(B0), sum = [ua[0] + ub[0], ua[1] + ub[1]], sl = Math.hypot(sum[0], sum[1]);
      const m = sl < 0.2 ? nrm : [sum[0] / sl, sum[1] / sl];   // the ends opposite each other: the chord's right side
      let best = cand;
      for (const d of [m, [-m[0], -m[1]]]) {
        const w = [c0[0] + d[0] * R, c0[1] + d[1] * R];
        if (cand.wps.some(v => Math.hypot(v[0] - w[0], v[1] - w[1]) <= 2)) continue;
        const next = search(build([...cand.wps, w].sort((p, q) => proj(p) - proj(q))));
        if (next.sum < best.sum) best = next;
        if (best.sum === 0) break;
      }
      return best;
    };
    const straight = build([]), best = search(straight.sum < first.sum ? straight : first);
    let result = best.sum < first.sum ? best : first;
    if (result.crossing > 0 && detourWork < ROUTE.DETOUR_WORK) {   // the search found no way: the shortest way round the outlines, if one exists (rare, bounded)
      const way = detour(A0, B0, obs);
      if (way) { const c = build(way); if (c.sum < result.sum) result = c; }
    }
    return done(result);
  }
  // The shortest polyline from a to b around the obstacles (screen px): a visibility graph over the corners of every outline
  // (a disc as a 12-gon round it), Dijkstra on it. -> the waypoints between a and b, or null when b cannot be reached
  function detour(a, b, obs) {
    const pad = ROUTE.MARGIN + ROUTE.CLEAR / 2, tight = ROUTE.MARGIN - 0.5;
    const blocks = (o, p, q, margin) => {   // does the segment p -> q run into the outline o (inflated by margin)?
      if (o.shape === 'disc') {
        const dx = q[0] - p[0], dy = q[1] - p[1], l2 = dx * dx + dy * dy || 1;
        const f = Math.max(0, Math.min(1, ((o.x - p[0]) * dx + (o.y - p[1]) * dy) / l2));
        return Math.hypot(p[0] + f * dx - o.x, p[1] + f * dy - o.y) < o.r + margin;
      }
      let t0 = 0, t1 = 1;   // Liang-Barsky against the rectangle
      for (const [pk, dk, lo, hi] of [[p[0], q[0] - p[0], o.x - margin, o.x + o.w + margin], [p[1], q[1] - p[1], o.y - margin, o.y + o.h + margin]]) {
        if (Math.abs(dk) < 1e-9) { if (pk <= lo || pk >= hi) return false; continue; }
        let u0 = (lo - pk) / dk, u1 = (hi - pk) / dk;
        if (u0 > u1) [u0, u1] = [u1, u0];
        t0 = Math.max(t0, u0); t1 = Math.min(t1, u1);
        if (t0 >= t1) return false;
      }
      return true;
    };
    const within = (o, p, m) => (o.shape === 'disc' ? Math.hypot(p[0] - o.x, p[1] - o.y) < o.r + m
      : p[0] > o.x - m && p[0] < o.x + o.w + m && p[1] > o.y - m && p[1] < o.y + o.h + m);
    const inside = p => obs.some(o => within(o, p, tight));
    // an end already inside an outline's margin (a card pushed onto a neighbour's disc) leaves it: only a real crossing blocks there
    const margins = obs.map(o => [a, b].map(e => (within(o, e, tight) ? 0.5 : tight)));
    const nodes = [a, b];
    obs.forEach(o => {
      if (o.shape === 'disc') for (let i = 0; i < 12; i++) nodes.push([o.x + Math.cos(i * Math.PI / 6) * (o.r + pad) / Math.cos(Math.PI / 12), o.y + Math.sin(i * Math.PI / 6) * (o.r + pad) / Math.cos(Math.PI / 12)]);
      else for (const [cx, cy] of [[o.x - pad, o.y - pad], [o.x + o.w + pad, o.y - pad], [o.x + o.w + pad, o.y + o.h + pad], [o.x - pad, o.y + o.h + pad]]) nodes.push([cx, cy]);
    });
    const usable = nodes.map((p, i) => i < 2 || !inside(p));
    const dist = nodes.map(() => Infinity), from = nodes.map(() => -1), done = nodes.map(() => false);
    dist[0] = 0;
    for (;;) {
      let u = -1;
      dist.forEach((d, i) => { if (!done[i] && d < Infinity && (u < 0 || d < dist[u])) u = i; });
      if (u < 0 || detourWork > ROUTE.DETOUR_WORK) return null;   // unreachable, or out of budget
      if (u === 1) break;
      done[u] = true;
      nodes.forEach((q, v) => {
        if (done[v] || !usable[v]) return;
        detourWork += obs.length;
        if (obs.some((o, i) => blocks(o, nodes[u], q, u < 2 ? margins[i][u] : v < 2 ? margins[i][v] : tight))) return;
        const d = dist[u] + Math.hypot(q[0] - nodes[u][0], q[1] - nodes[u][1]);
        if (d < dist[v]) { dist[v] = d; from[v] = u; }
      });
    }
    const way = [];
    for (let v = from[1]; v > 0; v = from[v]) way.unshift(nodes[v]);
    return way.slice(0, 8);
  }

  // the paths of the routes in play at (k, a, focus), cached like the cards (a pan reuses them): by the zoom, the layout, the moved
  // constellations, the card layout, the route set shown and the focus. -> { specs, lit, focus, obstacles }
  let routeCache = null, builds = 0, detourWork = 0;   // builds: the curves tried by this layout's searches; detourWork: segment tests spent by the detours of this layout (a fixed budget: deterministic)
  function routeLayout(k, a, focus) {
    const cl = a > 0 ? cardLayout(k) : null, key = `${k}|${layoutRuns}|${dragRev}|${state.allRoutes}|${focus}|${traj ? 1 : 0}`;
    if (routeCache && routeCache.key === key && routeCache.cl === cl) return routeCache;
    const t0 = performance.now(), set = routeSpecs(a, focus), obstacles = outlines(a, k);
    detourWork = 0; builds = 0;
    set.specs.forEach(sp => { Object.assign(sp, routePath(sp, obstacles, k)); });
    routeCache = { ...set, key, cl, obstacles };
    perf.routes = performance.now() - t0;
    return routeCache;
  }
  // the polyline cut by `head` px at its start and `tail` px at its end (arc length); null when nothing is left
  function cutPath(pts, head, tail) {
    const cum = [0];
    for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    const total = cum[cum.length - 1], from = head, to = total - tail;
    if (to - from < 1) return null;
    const at = d => {
      let i = 1;
      while (i < cum.length - 1 && cum[i] < d) i++;
      const f = (d - cum[i - 1]) / ((cum[i] - cum[i - 1]) || 1);
      return [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * f, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * f];
    };
    return [at(from), ...pts.filter((_, i) => cum[i] > from && cum[i] < to), at(to)];
  }
  // Draws the routes of `rs` (screen px from the camera's translation, the focused ones last) and records what it drew for the hooks
  // and the hit-test. A route with a net direction ends in a triangle at the reader's outline; relations only: dashed.
  function drawRoutes(rs, onScreen) {
    const seen = [];
    [...rs.specs].sort((p, q) => p.hi - q.hi).forEach(sp => {
      const r = sp.r, w = routeWidth(r.c), dim = rs.focus && !sp.hi ? ROUTE.DIM : 1, head = 6 + 1.2 * w, half = 3 + 0.8 * w;
      const line = cutPath(sp.pts, ROUTE.GAP, ROUTE.GAP) || sp.pts;
      let stroke = line, arrow = null;
      if (r.dir) {   // a route too short for its arrowhead gets a smaller one, never none
        const room = cutPath(line, 0, 0) && Math.hypot(line[line.length - 1][0] - line[0][0], line[line.length - 1][1] - line[0][1]);
        const base = cutPath(line, 0, Math.min(head, 0.7 * (room || head)));
        if (base) { stroke = base; arrow = { tip: line[line.length - 1], from: base[base.length - 1] }; }
        else arrow = { tip: line[line.length - 1], from: line[0] };
      }
      ctx.globalAlpha = sp.alpha * (traj ? DIM : dim); ctx.strokeStyle = ctx.fillStyle = routeInk(sp.hi && !traj);
      ctx.lineWidth = w; ctx.lineCap = 'butt'; ctx.lineJoin = 'round'; ctx.setLineDash(r.lin ? [] : ROUTE.DASH);
      ctx.beginPath(); stroke.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke();
      ctx.setLineDash([]);
      if (arrow) {
        const ang = Math.atan2(arrow.tip[1] - arrow.from[1], arrow.tip[0] - arrow.from[0]), [tx, ty] = arrow.tip;
        ctx.beginPath(); ctx.moveTo(tx, ty);
        ctx.lineTo(tx - Math.cos(ang) * head + Math.sin(ang) * half, ty - Math.sin(ang) * head - Math.cos(ang) * half);
        ctx.lineTo(tx - Math.cos(ang) * head - Math.sin(ang) * half, ty - Math.sin(ang) * head + Math.cos(ang) * half);
        ctx.closePath(); ctx.fill();
      }
      if (onScreen) seen.push({ sp, w, arrow: arrow ? [arrow.tip[0] + t.x, arrow.tip[1] + t.y] : null,
                                pts: sp.pts.map(([x, y]) => [x + t.x, y + t.y]) });
    });
    ctx.globalAlpha = 1; ctx.lineJoin = 'miter';
    if (onScreen) routeSeen = { list: seen, obstacles: rs.obstacles.map(o => ({ ...o, x: o.x + t.x, y: o.y + t.y })) };
  }
  // the route under a screen point, by the last frame: within max(HIT, half the width + 3) px of its polyline
  function routeAt(px, py) {
    let best = null, near = Infinity;
    routeSeen.list.forEach(e => {
      const tol = Math.max(ROUTE.HIT, e.w / 2 + 3);
      for (let i = 1; i < e.pts.length; i++) {
        const [ax, ay] = e.pts[i - 1], [bx, by] = e.pts[i], dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy || 1;
        const f = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / l2)), d = Math.hypot(px - ax - f * dx, py - ay - f * dy);
        if (d <= tol && d < near) { near = d; best = e; }
      }
    });
    return best;
  }
  // the route tooltip (D-067): upstream -> reader (without a direction: both ends), what it carries, who reads whom; a bundled
  // route lists its systems (the first 5, then "+ N")
  function routeTip(e) {
    const r = e.sp.r, up = e.sp.from, down = e.sp.to, name = d => esc(constellationLabel(d.k));
    const carries = [r.lin ? plural(r.lin, T.lineageN) : null, r.rel ? plural(r.rel, T.relationsN) : null].filter(Boolean).join(' · ');
    const ends = r.dir ? `${name(up)} → ${name(down)}` : `${name(up)} – ${name(down)}`;
    const systems = r.systems ? [...r.systems].sort((a, b) => b[1] - a[1]).map(([key]) => esc(constellationLabel(key))) : [];
    return `<b>${ends}</b><div class="m">${carries}</div>` + (r.dir ? `<div class="m">${T.reads(name(down), name(up))}</div>` : '')
      + (systems.length ? `<div class="m">${T.systemsList}${L.colon}${systems.slice(0, 5).join(', ')}${overflow(systems.length, 5, ', ')}</div>` : '');
  }
  // ---- focus: a constellation's routes in full (the mouse over it, or keyboard focus in its panel row or text summary)
  let focusByMouse = false;   // the focus comes from the mouse (it clears when the mouse leaves), not from keyboard focus
  function focusOn(key) {
    if (routeFocus === key) return;
    routeFocus = key; draw();
  }
  function announceFocus(key) {
    const grouped = groupShown(summaryAlpha(t.k)), sys = new Set(GROUPED.map(d => d.k));
    const of = key === GROUP && !grouped ? r => sys.has(r.source) || sys.has(r.target)   // no group card: every route of its systems
      : (at => r => r.source === at || r.target === at)(grouped && (key === GROUP || isMember(key)) ? GROUP : key);
    const n = (grouped ? bundled().all : routes).filter(of).length;
    live.textContent = `${key === GROUP ? T.systems : constellationLabel(key)}${L.colon}${plural(n, T.routesShownN)}`;
  }
  // keyboard focus in a panel row: lights its constellation's routes while it lasts
  // `when`: an optional guard; focus moving inside the element keeps the focus (no redraw, no new announcement)
  function focusRow(el, key, when) {
    el.addEventListener('focusin', () => {
      if (when && !when()) return;
      focusByMouse = false; if (routeFocus !== key) announceFocus(key); focusOn(key);
    });
    el.addEventListener('focusout', ev => { if (!el.contains(ev.relatedTarget)) focusOn(null); });
  }
  // the routes of a constellation, as text, heaviest first: "reads A (36), B (12) · read by C (8) · relations with D (5)"
  function routesLine(key) {
    const label = k => constellationLabel(k), by = (list, f) => list.sort((a, b) => b.c - a.c || (label(a.o) < label(b.o) ? -1 : 1))
      .map(x => `${label(x.o)} (${num(x.c)})`).join(', ');
    const reads = [], read = [], rel = [];
    routes.forEach(r => {
      if (r.source !== key && r.target !== key) return;
      const o = r.source === key ? r.target : r.source;
      (!r.dir ? rel : (r.dir > 0) === (r.target === key) ? reads : read).push({ o, c: r.c });
    });
    const parts = [reads.length && `${T.readsFrom} ${by(reads)}`, read.length && `${T.readBy} ${by(read)}`, rel.length && `${T.relWith} ${by(rel)}`].filter(Boolean);
    return `${T.routes}${L.colon}${parts.length ? parts.join(' · ') : T.routesNone}`;
  }

  function roundedRect(x, y, w, h, r) {
    r = Math.min(r, w / 2, h / 2);
    ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }
  // a bar of `w` px at (x, y), split by kind (kinds: [[kind, n]] in Types-list order), each segment in its kind's mark colour
  // (D-042), 1 px of the card's white between two, none narrower than SEG_MIN; under 3 px per kind present: one segment in the
  // dominant kind's colour
  function drawBar(x, y, w, kinds) {
    const total = d3.sum(kinds, z => z[1]), mark = kind => CONTRAST.edge(KIND[kind].color, C.bg);
    if (w < 3 * kinds.length) { ctx.fillStyle = mark(d3.greatest(kinds, z => z[1])[0]); ctx.fillRect(x, y, w, CARD.BAR); return; }
    const wide = kinds.map(z => w * z[1] / total), big = d3.sum(wide.filter(v => v >= CARD.SEG_MIN));
    const keep = (big - d3.sum(wide.filter(v => v < CARD.SEG_MIN).map(v => CARD.SEG_MIN - v))) / big;
    let bx = x;
    kinds.forEach((z, j) => {
      const sw = wide[j] < CARD.SEG_MIN ? CARD.SEG_MIN : wide[j] * keep;
      ctx.fillStyle = mark(z[0]); ctx.fillRect(bx, y, sw - (j < kinds.length - 1 ? 1 : 0), CARD.BAR); bx += sw;
    });
  }
  // the frames of a card holding trajectory tables, outside its border (D-064): start two dark rectangles, else upstream
  // dashed violet and downstream solid orange (both: upstream outside)
  function drawCardFrames(h, x, y, w, ht) {
    const ring = (o, color, lw, dashed) => {
      ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.setLineDash(dashed ? [6, 3] : []);
      roundedRect(x - o, y - o, w + 2 * o, ht + 2 * o, CARD.RADIUS + o); ctx.stroke();
    };
    if (h.start) { ring(4, C.text, 1.5); ring(8, C.text, 1.5); }
    else { if (h.up) ring(h.down ? 8 : 4, C.up, 2.5, true); if (h.down) ring(4, C.down, 2.5, false); }
    ctx.setLineDash([]);
  }
  // A colour dot of radius r (4: 8 px) at (x, y): filled, outlined in its mark colour, `lw` wide, when the colour alone falls
  // short (D-042). On a card, and in a folded row of an entity's card (in world units there: r 2.5, lw 1 / k)
  function cardDot(x, y, color, r = 4, lw = 1) {
    const edge = CONTRAST.edge(color, C.bg);
    ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill();
    if (edge !== color) { ctx.strokeStyle = edge; ctx.lineWidth = lw; ctx.stroke(); }
  }
  // Draws the card of e at its place, at layer alpha `a` (dimmed when the trajectory holds none of its tables); `over` is the
  // hovered { key, row }. Content by level; text laid out in screen space at constant size. -> the record of what it drew,
  // in screen px: the rectangle, the header (the drag handle) and the rows (the click targets), the text and the level
  function drawSummary(e, a, over) {
    const s = e.s, byLayers = state.by === 'layers', lv = e.lv, x = e.px - e.w / 2 + t.x, y = e.py - e.h / 2 + t.y;
    const system = isSystem(e.key);   // a lone source system: neutral (D-066)
    const mark = byLayers ? C.muted : CONTRAST.edge(DOM[e.key].color, C.bg), ink = byLayers ? C.text : system ? C.muted : CONTRAST.ink(DOM[e.key].color, C.card);
    const ix = x + CARD.PAD_X, iw = e.w - 2 * CARD.PAD_X, hov = over && over.key === e.key;
    const rec = { key: e.key, d: e.d, x, y, w: e.w, h: e.h, shift: e.disp, level: LEVELS[lv], name: null, counts: null, rows: [], main: [], drawn: !(lv >= 4 && !e.tj),
      traj: null, fonts: [null, null], header: { x, y, w: e.w, h: lv <= 2 ? CARD.PAD_Y + CARD.NAME : e.h }, rowHits: [] };
    if (lv >= 4) {   // no room for the name: the label above the disc stays instead (paint), so a bare pill is drawn only to carry a frame
      rec.label = true; rec.labelShown = true; rec.name = s.label; rec.counts = s.counts; rec.fonts = [13, 12];
      if (!e.tj) return rec;
    }
    ctx.globalAlpha = a * (traj && !e.tj ? DIM_CTX : 1) * litAlpha(e.key);
    if (e.tj) drawCardFrames(e.tj, x, y, e.w, e.h);
    ctx.fillStyle = C.card; ctx.strokeStyle = isSystem(e.key) ? CONTRAST.edge(NEUTRAL, C.bg) : mark; ctx.lineWidth = hov ? CARD.BORDER_HOVER : CARD.BORDER;
    roundedRect(x, y, e.w, e.h, CARD.RADIUS); ctx.fill(); ctx.stroke();
    if (lv >= 4) return rec;
    ctx.textAlign = 'left'; ctx.fillStyle = ink; ctx.font = F_NAME;
    let ty = y + CARD.PAD_Y;
    ctx.fillText(rec.name = cutText(F_NAME, s.label, iw), ix, ty + 12); ty += CARD.NAME;
    ctx.font = F_TEXT; ctx.fillStyle = C.muted;
    ctx.fillText(rec.counts = lv === 3 ? plural(s.n, L.tables) : s.counts, ix, ty + 10); ty += CARD.LINE;
    if (e.line && lv <= 3) { ctx.fillText(rec.traj = cutText(F_TEXT, e.line, iw), ix, ty + 10); ty += CARD.LINE; }
    rec.fonts = [13, 11];
    if (lv === 3) return rec;
    ty += CARD.SEC;
    if (lv === 2) {
      drawBar(ix, ty, iw, s.kinds);
      return rec;
    }
    const big = d3.max(s.rows, r => r.n), dot = byLayers ? 12 : 0;
    s.rows.forEach(r => {
      if (hov && over.row === r.key) { ctx.fillStyle = mark + '1f'; ctx.fillRect(x + 1, ty, e.w - 2, CARD.ROW - 1); }
      if (byLayers) cardDot(ix + 4, ty + 6, DOM[r.key].color);
      const count = num(r.n);
      ctx.font = F_TEXT; ctx.fillStyle = C.text; ctx.fillText(cutText(F_TEXT, r.label, iw - dot - textW(F_TEXT, count) - 8), ix + dot, ty + 10);
      ctx.fillStyle = C.muted; ctx.textAlign = 'right'; ctx.fillText(count, ix + iw, ty + 10); ctx.textAlign = 'left';
      drawBar(ix, ty + 14, Math.max(CARD.BAR_MIN, iw * r.n / big), r.kinds);
      rec.rows.push(r.key); rec.rowHits.push({ key: r.key, x, y: ty, w: e.w, h: CARD.ROW });
      ty += CARD.ROW;
    });
    if (!e.names) return rec;
    ty += CARD.SEC;
    s.main.slice(0, e.names).forEach(i => {
      cardDot(ix + 4, ty + 6, KIND[N[i].kind].color);
      ctx.fillStyle = C.text; ctx.fillText(cutText(F_TEXT, N[i].name, iw - 14), ix + 14, ty + 10);
      rec.main.push(N[i].id); ty += CARD.LINE;
    });
    return rec;
  }
  // The group card (D-066), at layer alpha `a`: the same record as drawSummary's. Header "Source systems", the counts line, then
  // one row per system in stack order (label, count; no bar by kind: that is on the system's own card), `+ N` past GROUP_ROWS.
  // At level `name` (the ladder stops there) only the header and the counts.
  function drawGroup(e, a, over) {
    const s = e.s, lv = e.lv, x = e.px - e.w / 2 + t.x, y = e.py - e.h / 2 + t.y, ix = x + CARD.PAD_X, iw = e.w - 2 * CARD.PAD_X;
    const mark = CONTRAST.edge(NEUTRAL, C.bg), hov = over && over.key === GROUP;
    const rec = { key: GROUP, d: e.d, x, y, w: e.w, h: e.h, shift: e.disp, level: lv ? 'name' : 'rows', name: null, counts: s.counts, rows: [], main: [],
      drawn: true, traj: null, fonts: [13, 11], header: { x, y, w: e.w, h: lv ? e.h : CARD.PAD_Y + CARD.NAME }, rowHits: [] };
    ctx.globalAlpha = a * (traj && !e.tj ? DIM_CTX : 1) * litAlpha(GROUP);
    if (e.tj) drawCardFrames(e.tj, x, y, e.w, e.h);
    ctx.fillStyle = C.card; ctx.strokeStyle = mark; ctx.lineWidth = hov ? CARD.BORDER_HOVER : CARD.BORDER;
    roundedRect(x, y, e.w, e.h, CARD.RADIUS); ctx.fill(); ctx.stroke();
    ctx.textAlign = 'left'; ctx.fillStyle = C.muted; ctx.font = F_NAME;
    let ty = y + CARD.PAD_Y;
    ctx.fillText(rec.name = cutText(F_NAME, s.label, iw), ix, ty + 12); ty += CARD.NAME;
    ctx.font = F_TEXT; ctx.fillText(s.counts, ix, ty + 10); ty += CARD.LINE;
    if (e.line && lv < 3) { ctx.fillText(rec.traj = cutText(F_TEXT, e.line, iw), ix, ty + 10); ty += CARD.LINE; }
    if (lv) return rec;
    ty += CARD.SEC;
    s.rows.slice(0, CARD.GROUP_ROWS).forEach(r => {
      if (hov && over.row === r.key) { ctx.fillStyle = C.cross; ctx.fillRect(x + 1, ty, e.w - 2, CARD.GROUP_ROW); }
      const count = num(r.n);
      ctx.font = F_TEXT; ctx.fillStyle = C.text; ctx.fillText(cutText(F_TEXT, r.label, iw - textW(F_TEXT, count) - 8), ix, ty + 12);
      ctx.fillStyle = C.muted; ctx.textAlign = 'right'; ctx.fillText(count, ix + iw, ty + 12); ctx.textAlign = 'left';
      rec.rows.push(r.key); rec.rowHits.push({ key: r.key, x, y: ty, w: e.w, h: CARD.GROUP_ROW });
      ty += CARD.GROUP_ROW;
    });
    const more = overflow(s.rows.length, CARD.GROUP_ROWS);
    if (more) { ctx.fillStyle = C.muted; ctx.fillText(more, ix, ty + 10); }
    return rec;
  }
  // the card part under a screen point, by the last frame: { rec, d, part: 'header' | 'row' | 'card', row }, or null
  let summaryHits = [], summaryAll = [];   // summaryHits: the cards drawn (hit-testing); summaryAll: every card (the summariesDrawn hook)
  function summaryAt(x, y) {
    const inside = r => x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h, rec = summaryHits.find(inside);
    if (!rec) return null;
    const row = rec.rowHits.find(inside);
    return { rec, d: rec.d, part: inside(rec.header) ? 'header' : row ? 'row' : 'card', row: row && row.key };
  }
  // zooming on a constellation or on one of its bands (the canvas, the cards, the summary): at least to the scale where
  // stars are drawn, so the tables are seen
  function zoomOnConstellation(d) {
    const w = stage.clientWidth, h = stage.clientHeight - top();
    if (d.members) {   // the source systems together: their box, at least where stars are drawn
      const bx = groupBox(d.members).box;
      return zoomTo((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2, Math.max(0.92 * Math.min(w / (bx[2] - bx[0] + 60), h / (bx[3] - bx[1] + 60)), starsScale * 1.05));
    }
    zoomTo(d.x, d.y, Math.max(0.92 * Math.min(w, h) / (2 * d.r + 60), starsScale * 1.05));
  }
  // a row's band (domain mode: a layer; layer mode: a domain); the constellation when that band is not drawn
  function zoomOnRow(d, key) {
    const b = bandSpans(d).find(s => s.key === key);
    if (!b) return zoomOnConstellation(d);
    const w = stage.clientWidth, h = stage.clientHeight - top(), mid = d.x + (b.s0 + b.s1) / 2;
    const half = rimHalf(d, b.s0 <= 0 && b.s1 >= 0 ? 0 : Math.min(Math.abs(b.s0), Math.abs(b.s1)));
    zoomTo(mid, d.y, Math.max(0.92 * Math.min(w / (b.s1 - b.s0 + 30), h / (2 * half + 60)), starsScale * 1.05));
  }

  // The summary as text, in the panel (D-064): a closed-by-default section, built only while open. Per constellation, left to
  // right: its name and a Zoom button, its counts, a button per row, its main tables; the trajectory's counts while it is on.
  const sumBox = $u('sum');
  function renderSummary() {
    const byLayers = state.by === 'layers';
    $u('sum-h').textContent = `${T.summary}${L.colon}${plural(constellations.length, byLayers ? T.layersN : L.domainsN)}`;
    if (!sumBox.open) return;
    const holds = trajHolds(), mk = (tag, text) => { const el = document.createElement(tag); if (text != null) el.textContent = text; return el; };
    const button = (text, onclick) => { const b = mk('button', text); b.type = 'button'; b.onclick = onclick; return b; };
    // business constellations first, left to right; then the source systems under their own heading, top to bottom (D-066)
    const isSys = d => isSystem(d.k);
    const section = d => {
      const s = SUMMARIES.get(d.k), box = mk('div'), h = mk('h4'), h4 = [], line = holds.get(d.k);
      box.className = 'sum-c';
      if (!byLayers) h4.push(paintDot(mk('i'), DOM[d.k].color));
      const go = button(T.zoomBtn, () => { zoomOnConstellation(d); live.textContent = T.zoomed(s.label); });
      go.setAttribute('aria-label', T.zoomOn(s.label));
      h.append(...h4, mk('span', s.label), go);
      box.append(h, mk('p', s.counts));
      if (line && (line.start || line.up + line.down)) { const p = mk('p', trajLine(line)); p.className = 'traj'; box.append(p); }
      const ul = mk('ul');
      s.rows.forEach(r => {
        const kinds = r.kinds.map(([kind, c]) => `${labelOf(KIND[kind])} ${num(c)}`).join(' · ');
        const b = button(`${r.label}${L.colon}${plural(r.n, L.tables)} (${kinds})`, () => { zoomOnRow(d, r.key); live.textContent = T.zoomed(`${s.label}, ${r.label}`); });
        b.title = byLayers ? T.zoomRowC : T.zoomRow;
        const li = mk('li'); li.append(b); ul.append(li);
      });
      box.append(ul);
      if (s.main.length) box.append(mk('p', `${T.mainTables}${L.colon}${s.main.map(i => N[i].name).join(', ')}`));
      box.append(mk('p', routesLine(d.k)));   // the canvas is silent: the routes as text
      focusRow(box, d.k);
      return box;
    };
    const business = [...constellations].filter(d => !isSys(d)).sort((a, b) => a.x - b.x || a.y - b.y);
    const systems = [...constellations].filter(isSys).sort(stackOrder);
    const items = business.map(section);
    if (systems.length) {
      const box = mk('div'), h = mk('h4'), tables = d3.sum(systems, d => SUMMARIES.get(d.k).n);
      box.className = 'sum-sys';
      const go = button(T.zoomBtn, () => { zoomOnConstellation({ members: systems }); live.textContent = T.zoomed(T.systems); });
      go.setAttribute('aria-label', T.zoomOn(T.systems));
      h.append(mk('span', `${T.systems}${L.colon}${num(systems.length)} · ${plural(tables, L.tables)}`), go);
      box.append(h);
      const key = systems.length > 1 ? GROUP : systems[0].k;
      focusRow(box, key);
      items.push(box, ...systems.map(section));
    }
    $u('sum-list').replaceChildren(...(items.length ? items : [mk('p', L.empty)]));
  }
  sumBox.addEventListener('toggle', renderSummary);

  // ---------------------------------------------------------------- navigation
  const zoom = d3.zoom().scaleExtent(ZOOM_EXTENT).on('zoom', ev => { t = ev.transform; draw(); });
  // mouse only: on touch every finger goes to the zoom, so a pinch starting on a table or a domain name
  // zooms and a one-finger drag pans, as in the detail (a touch drag cannot hand a finger over to a pinch)
  const drag = d3.drag().container(canvas).touchable(false).filter(ev => !ev.button)
    .subject(ev => {
      const [wx, wy] = t.invert([ev.x, ev.y]);
      if (t.k >= FAR && !cardsOn() && pickShown(wx, wy)) return null;   // a shown (orbit) table is not draggable: the pointer pans
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
      else {   // a constellation, or the group card: every source system it stands for
        const moved = s.d.members || [s.d], keys = new Set(moved.map(m => m.k));
        moved.forEach(m => { m.x += dx; m.y += dy; });
        dragRev++;
        drawn.forEach(n => { if (keys.has(grouping().of(n))) { P[n.i].x += dx; P[n.i].y += dy; } });
      }
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
      dragRev++;
      draw();
    });
  const sel = zoomOn(d3.select(canvas).call(drag), zoom);
  // room kept free at the top of the canvas: the trajectory bar overlays it while the mode is on
  const top = () => traj ? bar.offsetHeight : 0;
  // frame a world-space box, at most at scale kMax
  // constellation names sit above the halos at a fixed screen size: keep that strip free at the top
  const NAME_STRIP = 46;
  const frameScale = (bx0, by0, bx1, by1, kMax = Infinity) =>
    Math.min(kMax, 0.95 * Math.min(stage.clientWidth / (bx1 - bx0), (stage.clientHeight - top() - NAME_STRIP) / (by1 - by0)));
  const FIT_PAD = 4;   // the least room Fit leaves between a card and the stage's side, screen px
  function frame(bx0, by0, bx1, by1, animate, kMax = Infinity, kFixed = null) {
    const NAME = NAME_STRIP, top0 = top(), w = stage.clientWidth, h = stage.clientHeight - top0 - NAME;
    const k = kFixed ?? frameScale(bx0, by0, bx1, by1, kMax);
    const tr = d3.zoomIdentity.translate(w / 2, top0 + NAME + h / 2).scale(k).translate(-(bx0 + bx1) / 2, -(by0 + by1) / 2);
    (animate && motionMs(500) ? sel.transition().duration(500) : sel).call(zoom.transform, tr);
  }
  // the whole universe, or the drawn tables of the trajectory while the mode is on
  function fit(animate) {
    const tj = trajMembers().filter(i => posOf(i));
    if (tj.length) {
      return frame(d3.min(tj, i => posOf(i).x - boxOf(i).w / 2), d3.min(tj, i => posOf(i).y + boxOf(i).oy - boxOf(i).h / 2),
        d3.max(tj, i => posOf(i).x + boxOf(i).w / 2), d3.max(tj, i => posOf(i).y + boxOf(i).oy + boxOf(i).h / 2), animate, 2);
    }
    if (!constellations.length) return draw();
    let box = [d3.min(constellations, d => d.x - d.r), d3.min(constellations, d => d.y - d.r),
      d3.max(constellations, d => d.x + d.r), d3.max(constellations, d => d.y + d.r)];
    // the cards are pushed off their discs and keep their screen size: Fit makes room for the cards drawn at the scale the discs
    // alone give (one pass: a card's shift grows as k falls, so iterating would shrink the view for ever), then lowers the scale
    // by steps until the cards' own extent at that scale fits the stage's width, and centres that extent: no card is cut at the side
    const base = box, k0 = frameScale(...base), cardsAt = k => (cardsOnAt(summaryAlpha(k)) ? cardLayout(k).items.filter(e => e.lv <= 3) : []);
    cardsAt(k0).forEach(e => {
      box = [Math.min(box[0], (e.px - e.w / 2) / k0), Math.min(box[1], (e.py - e.h / 2) / k0),
             Math.max(box[2], (e.px + e.w / 2) / k0), Math.max(box[3], (e.py + e.h / 2) / k0)];
    });
    let k = frameScale(...box);
    if (!cardsAt(k).length) return frame(...box, animate);
    const w = stage.clientWidth, reach = kk => {   // the screen extent (from the world's origin) of the discs and of the cards at kk
      const cs = cardsAt(kk);
      return [Math.min(base[0] * kk, d3.min(cs, e => e.px - e.w / 2)), Math.max(base[2] * kk, d3.max(cs, e => e.px + e.w / 2))];
    };
    let [lo, hi] = reach(k);
    for (let i = 0; i < 24 && hi - lo > w - 2 * FIT_PAD; i++) { k *= 0.97; [lo, hi] = reach(k); }
    const cx = (lo + hi) / 2 / k, half = (box[2] - box[0]) / 2;   // the centre of the extent, in world units
    frame(cx - half, box[1], cx + half, box[3], animate, Infinity, k);
  }
  function zoomTo(x, y, k) {
    const top0 = top(), w = stage.clientWidth, h = stage.clientHeight - top0;
    const tr = d3.zoomIdentity.translate(w / 2, top0 + h / 2).scale(k).translate(-x, -y);
    (motionMs(600) ? sel.transition().duration(600) : sel).call(zoom.transform, tr);
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
    if (cardsOn()) return null;   // the stars are not drawn: nothing to aim at
    const over = pickShown(wx, wy);
    if (over) return over;
    if (!tree) return null;
    const n = tree.find(wx, wy, Math.max(200, 12 / t.k));
    if (!n) return null;
    const p = P[n.i], b = B[n.i];
    const hit = state.detail !== 'names' && t.k > TABLE_K
      ? Math.abs(wx - p.x) <= b.w / 2 && Math.abs(wy - p.y) <= b.h / 2
      : Math.hypot(wx - p.x, wy - p.y) <= Math.max(8, 8 / t.k);
    return hit ? n : null;
  }
  // the constellation name under a screen point, if any
  const labelAt = (x, y) => labelHits.find(h => x >= h.x && x <= h.x + h.w && y >= h.y && y <= h.y + h.h);
  // the constellation under the pointer, if any
  // (while cards are on, its card first, then its disc: a card may overlap a neighbour's disc)
  function domainAt(ev) {
    const [px, py] = d3.pointer(ev, canvas), card = cardsOn() ? summaryAt(px, py) : null;
    if (card) return card.d;
    const [wx, wy] = t.invert([px, py]);
    return constellations.find(d => Math.hypot(wx - d.x, wy - d.y) < d.r);
  }
  // Layer mode tooltip of a constellation (D-048): its domains in band order (first TIP_DOMAINS, then "+ N"), and the
  // band under the world x `wx`, if any; on a card, the row under the pointer instead (`row`: its key)
  function layerTip(d, wx, cards, row) {
    const names = d.bands.slice(0, TIP_DOMAINS).map(b => esc(labelOf(DOM[b.key]))).join(' · ');
    const more = overflow(d.bands.length, TIP_DOMAINS, ' · ');
    const band = cards ? SUMMARIES.get(d.k).rows.find(r => r.key === row) : bandSpans(d).find(b => wx - d.x >= b.s0 && wx - d.x <= b.s1);
    return `<b>${esc(constellationLabel(d.k))}</b><div class="m">${plural(d.n, L.tables)}</div>`
      + `<div class="m">${T.domains}${L.colon}${names}${more}</div>`
      + (band ? `<div class="m">${T.domainOne}${L.colon}${esc(labelOf(DOM[band.key]))} · ${plural(band.n, L.tables)}</div>` : '')
      + `<div class="a">${frameText()}${cards ? ' · ' + T.rowZoom : ''}</div>`;
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
    text += `<div class="m"><b>${plural(held.length, L.foldedN)}</b></div>`
      + foldedLines(held.map(i => [N[i].name, labelOf(KIND[N[i].kind])])).map(l => `<div class="m">${esc(l)}</div>`).join('');
    return text;
  }
  const sameCard = (a, b) => (a && a.key) === (b && b.key) && (a && a.row) === (b && b.row);
  canvas.addEventListener('mousemove', ev => {
    const n = pick(ev), h = n ? n.i : null, [px, py] = d3.pointer(ev, canvas);
    const cards = cardsOn(), part = cards ? summaryAt(px, py) : null, at = part ? { key: part.d.k, row: part.row } : null;
    if (h !== hover || !sameCard(at, overCard)) { hover = h; overCard = at; draw(); }
    const d = n ? null : domainAt(ev);
    // the mouse over a constellation (not a table) lights its routes (D-067); leaving it clears them
    const fk = !n && !traj && t.k < OVERVIEW_K && d ? d.k : null;
    if (fk) { focusByMouse = true; focusOn(fk); } else if (focusByMouse) { focusByMouse = false; focusOn(null); }
    const hitRoute = !n && !(part && cards) && !traj && t.k < OVERVIEW_K ? routeAt(px, py) : null;
    canvas.style.cursor = (n && !SP.has(n.i) && t.k >= FAR) || labelAt(px, py) ? 'grab' : part && part.row ? 'pointer' : '';
    if (!n && !d && !hitRoute) { tip.style.display = 'none'; return; }
    if (hitRoute) {
      tip.innerHTML = routeTip(hitRoute);
    } else if (n) {
      const dbl = detailIds.has(n.id) ? T.openDetail : T.zoomIn, start = traj && n.i === traj.start;
      tip.innerHTML = tableTip(DATA, n) + foldTip(n) + (traj ? trajectoryTip(traj, n.i) : '') + tableDesc(n) +
        `<div class="a">${t.k < FAR ? frameText() : start ? dbl : T.clickTraj + ' · ' + dbl}</div>`;
    } else if (d.members) {   // the group card
      tip.innerHTML = `<b>${esc(T.systems)}</b><div class="m">${SUMMARIES.get(GROUP).counts}</div><div class="a">${T.groupHint}</div>`;
    } else if (state.by === 'layers') {
      tip.innerHTML = layerTip(d, t.invert([px, py])[0], cards, part && part.d === d ? part.row : null);
    } else {
      const dd = DOM[d.k], row = cards && part && part.d === d && part.row ? SUMMARIES.get(d.k).rows.find(r => r.key === part.row) : null;
      tip.innerHTML = `<b>${esc(labelOf(dd))}</b><div class="m">${plural(d.n, L.tables)}${dd.owner ? ` · ${T.owner}${L.colon}${esc(dd.owner)}` : ''}</div>`
        + (isSystem(d.k) ? `<div class="m">${T.systemOne}</div>` : `<div class="m">${T.layers}${L.colon}${esc(bandLabels(d))}</div>`)
        + (row ? `<div class="m">${T.layerOne}${L.colon}${esc(row.label)} · ${plural(row.n, L.tables)}</div>` : '')
        + `<div class="a">${T.frame}${cards ? ' · ' + T.rowZoom : ''}</div>`;
    }
    const r = stage.getBoundingClientRect();
    tip.style.display = 'block';
    tip.style.left = Math.min(ev.clientX - r.left + 14, r.width - 380) + 'px';
    tip.style.top = (ev.clientY - r.top + 14) + 'px';
  });
  canvas.addEventListener('mouseleave', () => {
    tip.style.display = 'none';
    if (focusByMouse) { focusByMouse = false; focusOn(null); }
    if (hover != null || overCard) { hover = null; overCard = null; draw(); }
  });
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
    if (d) zoomOnConstellation(d);
  });
  // single click: a table enters the trajectory mode, or moves it; only the empty background
  // (no table, domain label or domain halo, at any zoom) leaves it.
  // d3-drag and d3-zoom swallow the click that ends a drag or a pan.
  canvas.addEventListener('click', ev => {
    if (ev.detail > 1) return;   // the second click of a double-click
    const n = t.k >= FAR ? pick(ev) : null;
    if (n) { enterTrajectory(n.i); return; }
    const hit = cardsOn() ? summaryAt(...d3.pointer(ev, canvas)) : null;
    if (hit && hit.part === 'row') { hit.d.members ? zoomOnConstellation(hit.d.members.find(m => m.k === hit.row)) : zoomOnRow(hit.d, hit.row); return; }   // a click elsewhere on a card does nothing
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
    renderSummary();
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
    renderSummary();
    draw();
  }
  // fills the bar from the current trajectory; returns the counts (or empty-state) text
  function renderBar() {
    const n = N[traj.start], u = traj.up.size, d = traj.down.size, empty = u + d === 0;
    paintDot($u('tj-dot'), KIND[n.kind].color);
    $u('tj-start').textContent = n.name; $u('tj-start').title = n.name;
    const ups = countByDomain(N, traj.up.keys()), downs = countByDomain(N, traj.down.keys());
    const rows = [...new Set([...ups.keys(), ...downs.keys()])].map(k => [k, ups.get(k) || 0, downs.get(k) || 0])
      .map(([k, cu, cd]) => ({ k, total: cu + cd, text: `${labelOf(DOM[k])}${L.colon}${countsText(cu, cd)}` }))
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
  function relayout() { found = null; hover = null; overCard = null; layout(); if (traj) renderBar(); fit(false); draw(); }
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
      summary: { cell: CELL, scale: summaryScale, stars: starsScale, alpha: summaryAlpha(t.k) },
      routes: routes.map(r => ({ source: r.source, target: r.target, c: r.c, dir: r.dir, rel: r.rel, lin: r.lin, strong: r.strong,
        bundle: GROUPED.some(d => d.k === r.source || d.k === r.target) && !(isMember(r.source) && isMember(r.target)) ? GROUP : null })),
      systems: { keys: DATA.domains.filter(d => d.system).map(d => d.key), grouped: GROUPED.map(d => d.k) },
      tables: [...drawn, ...[...SP.keys()].map(i => N[i])].map(n => ({ id: n.id, domain: n.domain, layer: n.layer,
        x: posOf(n.i).x, y: posOf(n.i).y, w: boxOf(n.i).w, h: boxOf(n.i).h, oy: boxOf(n.i).oy, r: starR(n),
        parent: PARENT[n.i] == null ? null : N[PARENT[n.i]].id, held: (FOLDED.get(n.i) || []).length, shown: SP.has(n.i) })),
      fold: { available: FOLDABLE, on: state.fold },
      folded: [...foldedSet].filter(i => !SP.has(i)).map(i => N[i].id),
      constellations: constellations.map(d => ({ key: d.k, n: d.n, x: d.x, y: d.y, r: d.r, summary: summaryOf(d),
                                   system: isSystem(d.k), flowRank: FLOWRANK.has(d.k) ? FLOWRANK.get(d.k) : null,
                                   bands: d.bands.map(b => ({ key: b.key, n: b.n, x0: d.x + b.x0, x1: d.x + b.x1 })) })) };
  }

  // a constellation's card for the tests: its world rectangle, and what it says (counts, rows by kind, main tables' ids)
  function summaryOf(d) {
    const s = SUMMARIES.get(d.k);
    return { ...summaryRect(d), tables: s.n, entities: s.entities, main: s.main.map(i => N[i].id),
      rows: s.rows.map(r => ({ key: r.key, n: r.n, kinds: r.kinds })) };
  }
  // what the last screen frame drew of each card, in screen px (kept out of geometry() so geometries compare equal)
  const summariesDrawn = () => summaryAll.map(c => ({ key: c.key, x: c.x, y: c.y, w: c.w, h: c.h, shift: c.shift, level: c.level, name: c.name,
    counts: c.counts, rows: c.rows, main: c.main, traj: c.traj, fonts: c.fonts, label: !!c.label, labelShown: !!c.label && c.labelShown !== false, labelAt: c.labelAt || null }));

  // the d3 zoom transform; camera({x, y, k}) moves it first, through the zoom (the browser tests frame a domain)
  function camera(to) {
    if (to) sel.call(zoom.transform, d3.zoomIdentity.translate(to.x, to.y).scale(to.k));
    return { x: t.x, y: t.y, k: t.k };
  }

  // image is for the browser tests' pixel comparison; the page uses it through #u-export.
  // camera, place and geometry are for the tests too: closing the flow leaves the camera as it was.
  // routesDrawn: what the last screen frame drew of each route and the outlines it avoided (screen px); routesMs: the last route
  // layout; focus(key): the keyboard focus' effect, for the tests
  const routesDrawn = () => ({
    routes: routeSeen.list.map(e => ({ source: e.sp.r.source, target: e.sp.r.target, bundled: e.sp.bundle, c: e.sp.r.c, rel: e.sp.r.rel, lin: e.sp.r.lin,
      dir: e.sp.r.dir, alpha: e.sp.alpha, dashed: !e.sp.r.lin, blocked: e.sp.blocked, hi: e.sp.hi, arrow: e.arrow, samples: e.pts })),
    obstacles: routeSeen.obstacles.map(o => (o.shape === 'disc' ? { key: o.key, kind: 'disc', x: o.x, y: o.y, r: o.r } : { key: o.key, kind: 'card', x: o.x, y: o.y, w: o.w, h: o.h })) });
  return { shown: () => { resize(); if (foldStale) { foldStale = false; relayout(); } }, relayout, trajectoryState, image, camera, place, geometry, drawnNames: () => drawnNames, placeMs: () => perf.place,
    summariesDrawn, cardsMs: () => perf.cards, layoutCardsMs: () => perf.cardLayout, drawMs: () => perf.draw, routesDrawn, routesMs: () => perf.routes,
    focus: key => { focusByMouse = false; focusOn(key ?? null); } };
}
