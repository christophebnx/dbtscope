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
          mainH: 'Main tables', rowZoom: label => `Click: zoom on ${label}`, summaryH: 'Summary of the constellations',
          entitiesN: ['entity', 'entities'], foldsInto: 'Folds into',
          openedLive: (t, p) => `${t} is folded into ${p}: shown`,
          foldLiveOn: n => `Descriptive tables folded: ${n}`, foldLiveOff: 'Descriptive tables shown',
          businessH: 'Business domains', systemsH: 'Source systems', systemsShort: 'Sources', allBusiness: 'All business domains',
          noneBusiness: 'None of the business domains', allSystems: 'All source systems', noneSystems: 'No source system',
          systemsN: ['source system', 'source systems'], groupTip: 'Click a row to zoom on it',
          routesN: ['route', 'routes'], routesOf: (s, t) => `${num(s)} of ${num(t)} routes`, allRoutes: 'Show all routes',
          allRoutesOn: t => `All ${num(t)} routes shown`,
          allRoutesOff: (s, t) => `The ${num(s)} strongest of ${num(t)} routes shown`,
          relationsN: ['relation', 'relations'], lineageN: ['lineage link', 'lineage links'],
          reads: (a, b) => `${a} reads ${b}`, readEach: 'Each reads the other', noLineage: 'No lineage',
          routeFrom: 'From', routesH: 'Routes',
          pngTitle: 'Save the view as shown as a PNG image (high resolution)',
          hint: 'Wheel: zoom · drag the background to pan · drag a table, or a constellation by its name, to arrange them · '
              + 'click a table to see its trajectory (Esc to leave) · '
              + 'double-click a constellation to zoom in, a table to open its detail' },
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
          mainH: 'Tables principales', rowZoom: label => `Clic\u00a0: cadrer ${label}`,
          summaryH: 'Synthèse des constellations',
          entitiesN: ['entité', 'entités'], foldsInto: 'Se replie dans',
          openedLive: (t, p) => `${t} est repliée dans ${p}\u00a0: affichée`,
          foldLiveOn: n => `Tables descriptives repliées\u00a0: ${n}`, foldLiveOff: 'Tables descriptives affichées',
          businessH: 'Domaines métier', systemsH: 'Systèmes sources', systemsShort: 'Sources', allBusiness: 'Tous les domaines métier',
          noneBusiness: 'Aucun domaine métier', allSystems: 'Tous les systèmes sources', noneSystems: 'Aucun système source',
          systemsN: ['système source', 'systèmes sources'], groupTip: 'Clic sur une ligne pour la cadrer',
          routesN: ['route', 'routes'], routesOf: (s, t) => `${plural(s, ['route', 'routes'])} sur ${num(t)}`,
          allRoutes: 'Afficher toutes les routes', allRoutesOn: t => `Les ${num(t)} routes sont affichées`,
          allRoutesOff: (s, t) => `Les ${num(s)} routes les plus fortes sur ${num(t)} sont affichées`,
          relationsN: ['relation', 'relations'], lineageN: ['lien de lignée', 'liens de lignée'],
          reads: (a, b) => `${a} lit ${b}`, readEach: 'Chacun lit l\'autre', noLineage: 'Aucune lignée',
          routeFrom: 'Depuis', routesH: 'Routes',
          pngTitle: 'Enregistrer la vue telle qu\'affichée en image PNG (haute résolution)',
          hint: 'Molette\u00a0: zoom · glisser le fond\u00a0: déplacer la vue · glisser une table, ou une constellation par son nom, pour les ranger · '
              + 'clic sur une table\u00a0: sa trajectoire (Échap pour quitter) · '
              + 'double-clic sur une constellation pour la cadrer, sur une table pour son détail' },
  }[PAGE.lang];

  const N = DATA.nodes; N.forEach((n, i) => n.i = i);
  // how connected each table is over all links: pivots (hubs, dimensions...) get bigger stars and their names first
  const DEG = new Array(N.length).fill(0), RELDEG = new Array(N.length).fill(0);
  [...DATA.relations, ...DATA.lineage].forEach(([a, b]) => { DEG[a]++; DEG[b]++; });
  DATA.relations.forEach(([a, b]) => { RELDEG[a]++; RELDEG[b]++; });
  const KIND = Object.fromEntries(DATA.kinds.map(k => [k.key, k]));
  // a kind's role (read from the payload, D-059) sets its tier: the size of its stars and the priority of its names (D-058)
  const TIER = { core: 'large', connector: 'medium', none: 'medium', descriptive: 'small', technical: 'small' };
  const TIER_ORDER = { large: 0, medium: 1, small: 2 };
  const SIZE = { large: { base: 6, slope: 1.6, cap: 16 }, medium: { base: 3, slope: 1.6, cap: 14 }, small: { base: 2, slope: 0.8, cap: 6 } };
  const R_MAX = Math.max(...Object.values(SIZE).map(s => s.cap));
  const ROLE_ORDER = ['core', 'connector', 'descriptive', 'technical', 'none'];
  const FIT_NAMES = 3;  // names offered per constellation from afar: its core tables with the most relations
  const MAIN_MAX = 5;   // main tables listed on a summary card (the first FIT_NAMES are the names from afar)
  const S_STARS = 3, S_CARDS = 2;   // drawn radius (px) of the reference star: cards weigh 0 from S_STARS up, 1 from S_CARDS down
  const tierOf = n => TIER[KIND[n.kind].role] || 'medium';
  const R = N.map(n => { const z = SIZE[tierOf(n)]; return Math.min(z.cap, z.base + z.slope * Math.sqrt(DEG[n.i])); });
  const starR = n => R[n.i];
  // names compete for room on screen: by tier, then kinds listed first in the config win, then the most connected tables
  const KIND_RANK = Object.fromEntries(DATA.kinds.map((k, i) => [k.key, i]));
  const labelScore = n => (DEG[n.i] + 1) * (1 - 0.7 * KIND_RANK[n.kind] / Math.max(1, DATA.kinds.length - 1));
  const DOM = Object.fromEntries(DATA.domains.map(d => [d.key, d]));
  // Source systems (M8.4, D-068, D-069): the flag is computed in Python. They are set apart only while some domain
  // is not one; the panel order (DOM_POS: layer bands, card rows, the text summary) lists business domains first.
  const SYS = new Set(DATA.domains.filter(d => d.system).map(d => d.key));
  const HAS_SYS = SYS.size > 0 && SYS.size < DATA.domains.length;
  const BUSINESS = DATA.domains.filter(d => !HAS_SYS || !SYS.has(d.key)), SYSTEMS = DATA.domains.filter(d => HAS_SYS && SYS.has(d.key));
  const DOM_LIST = [...BUSINESS, ...SYSTEMS];   // the panel order: a domain's position is its index here, never in the payload
  const DOM_POS = Object.fromEntries(DOM_LIST.map((d, i) => [d.key, i]));
  const GROUP = '@systems';   // the key of the source-systems group card (not a domain key in practice)
  const LAYER = Object.fromEntries(DATA.layers.map((l, i) => [l.key, { ...l, rank: i }]));
  const counts = key => d3.rollup(N, v => v.length, n => n[key]);
  const COUNT = { domain: counts('domain'), layer: counts('layer'), kind: counts('kind') };
  const byMemory = viewerMemory('dbtscope-constellations', ['domains', 'layers']);
  const foldMemory = viewerMemory('dbtscope-fold', ['folded', 'shown']);
  // Entities (D-062, D-063): the parent of a descriptive table is computed in Python (`n.parent`, an id);
  // PARENT[i] is its index or -1. Without any parent nothing below changes the page.
  const ID = new Map(N.map(n => [n.id, n.i]));
  const PARENT = N.map(n => (n.parent && ID.has(n.parent) ? ID.get(n.parent) : -1));
  const CAN_FOLD = PARENT.some(p => p >= 0);
  // the roles of a parent: the copy of domain/fold.PARENT_ROLES (the payload does not carry them)
  const isEntity = n => ['core', 'connector'].includes(KIND[n.kind].role);
  // the entities among `tables`, as drawn: a table folded into another is no entity of its own (counts, meta line, cards)
  const entitiesIn = tables => tables.filter(n => !FOLDNOW[n.i] && isEntity(n)).length;
  // the switch exists from two rows of the Layers list; below, the page stays in domains
  const CAN_BY = DATA.layers.length >= 2;
  const DEFAULT_BY = DATA.defaults.constellations === 'layers' ? 'layers' : 'domains';
  const state = {
    domains: new Set(DATA.domains.map(d => d.key)),
    layers: new Set(DATA.layers.map(l => l.key)),
    kinds: new Set(DATA.kinds.map(k => k.key).filter(k => !DATA.defaults.hiddenKinds.includes(k))),
    links: DATA.defaults.links, detail: DATA.defaults.detail,
    by: CAN_BY ? byMemory.get() || DEFAULT_BY : 'domains',
    fold: CAN_FOLD && (foldMemory.get() ? foldMemory.get() === 'folded' : DATA.defaults.fold),
  };
  const folding = () => CAN_FOLD && state.fold;   // the fold is on (the scope of the arrangement, the meta line)
  let opened = null;   // the entity opened by the last search: its folded tables are drawn (index), at most one
  const stage = $u('stage'), canvas = $u('canvas'), screenCtx = canvas.getContext('2d'), tip = $u('tip');
  let ctx = screenCtx;   // what the drawing helpers paint on: the screen, or an exported image during draw()
  const layoutCache = new Map();
  let drawn = [], mainCache = null;  // ids of the names drawn in the last frame (for the tests); the main tables
  // pass: the tables that pass the three filters; visible: those drawn (pass minus the folded ones); edges: the
  // links between drawn tables; HELD: entity index -> the indices folded into it now (in name order)
  let P = [], B = [], REL = new Map(), labelHits = [], pass = [], visible = [], edges = [], constellations = [], routes = [], tree = null;
  let PASS = new Uint8Array(N.length), FOLDNOW = new Uint8Array(N.length), HELD = new Map(), linkCount = 0;
  // the constellation whose routes are spotlit (M8.4, D-071): a key or GROUP; pointer or focus state, never exported;
  // showAll: the "Show all routes" choice, for the session only
  let spot = null, showAll = false, geomVer = 0, dragging = false;   // geomVer: bumped when a constellation moves (routes are recomputed)
  let t = d3.zoomIdentity, hover = null, found = null, perf = { layout: 0, draw: 0, summary: 0, routes: 0 };
  // summary cards (M8.3, D-065, D-066): the reference star radius of the layout, the rows and header rectangles of
  // the last screen frame (screen px), the card under the pointer and its row, the trajectory marks of the cards
  let refR = 1, routeHits = [], lastView = null, summaryHits = [], cardInfo = [], hoverCard = null, hoverRow = null, trajCache = null, fade = 1;
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
    radio.onchange = () => { if (!radio.checked) return; state.by = radio.value; byMemory.set(state.by, DEFAULT_BY); opened = null; relayout(); };
  });
  // the fold control: one checkbox, labelled from the roles of the kinds that fold (never from names, D-059)
  $u('fold').hidden = !CAN_FOLD;
  if (CAN_FOLD) {
    const foldKeys = new Set(N.filter(n => PARENT[n.i] >= 0).map(n => n.kind));
    $u('h-fold').textContent = L.foldH;
    $u('fold-label').textContent = foldLabel(DATA.kinds.filter(k => k.role === 'descriptive' && foldKeys.has(k.key)));
    $u('fold-n').textContent = num(PARENT.filter(p => p >= 0).length);
    $u('fold-row').title = L.foldTitle;
    $u('fold-box').checked = state.fold;
    $u('fold-box').onchange = ev => {
      state.fold = ev.target.checked; opened = null;
      foldMemory.set(state.fold ? 'folded' : 'shown', DATA.defaults.fold ? 'folded' : 'shown');
      relayout();
      $u('live').textContent = state.fold ? T.foldLiveOn(plural(entitiesIn(visible), T.entitiesN)) : T.foldLiveOff;
    };
  }
  $u('h-layers').textContent = T.layers; $u('h-kinds').textContent = L.kinds;
  $u('h-domains').textContent = HAS_SYS ? T.businessH : T.domains;
  $u('all').textContent = T.every; $u('none').textContent = T.nothing;
  // source systems get their own list and heading, each with its own all / none (D-069); one heading without them
  $u('systems-h').hidden = $u('systems').hidden = !HAS_SYS;
  if (HAS_SYS) {
    $u('h-systems').textContent = T.systemsH; $u('sys-all').textContent = T.every; $u('sys-none').textContent = T.nothing;
    $u('all').setAttribute('aria-label', T.allBusiness); $u('none').setAttribute('aria-label', T.noneBusiness);
    $u('sys-all').setAttribute('aria-label', T.allSystems); $u('sys-none').setAttribute('aria-label', T.noneSystems);
  }
  $u('routes-label').textContent = T.allRoutes;
  $u('fit').textContent = L.fit; $u('q').placeholder = T.search; $u('hint').textContent = T.hint;

  // `by`: the grouping whose constellation a row stands for; hovering or focusing the row spotlights its routes
  function checkboxes(el, items, countOf, set, color, title, by) {
    el.replaceChildren(...items.map(it => {
      const row = filterRow(
        { label: labelOf(it), color: color && color(it), count: countOf.get(it.key) || 0, checked: set.has(it.key),
          title: title && title(it) },
        on => { on ? set.add(it.key) : set.delete(it.key); relayout(); });
      if (by) {
        const lit = () => { if (state.by === by && spot !== it.key) { spot = it.key; draw(); } };
        const dark = () => { if (spot != null) { spot = null; draw(); } };
        row.addEventListener('mouseenter', lit); row.addEventListener('focusin', lit);
        row.addEventListener('mouseleave', dark); row.addEventListener('focusout', dark);
      }
      return row;
    }));
  }
  // the Types rows by role, then in payload order (the sort is stable)
  const KINDS_BY_ROLE = [...DATA.kinds].sort((a, b) => ROLE_ORDER.indexOf(a.role) - ROLE_ORDER.indexOf(b.role));
  const KIND_POS = new Map(KINDS_BY_ROLE.map((k, i) => [k.key, i]));
  // a mix ([kind, count] pairs) in the order of the Types rows
  const inKindOrder = mix => [...mix].sort((p, q) => KIND_POS.get(p[0]) - KIND_POS.get(q[0]));
  function refreshPanel() {
    const owner = d => d.owner ? `${T.owner}${L.colon}${d.owner}` : labelOf(d);
    checkboxes($u('layers'), DATA.layers, COUNT.layer, state.layers, null, null, 'layers');
    checkboxes($u('kinds'), KINDS_BY_ROLE, COUNT.kind, state.kinds, k => k.color);
    checkboxes($u('domains'), BUSINESS, COUNT.domain, state.domains, d => d.color, owner, 'domains');
    if (HAS_SYS) checkboxes($u('systems'), SYSTEMS, COUNT.domain, state.domains, d => d.color, owner, 'domains');
  }
  refreshPanel();
  // all / none of one heading tick or untick only its rows
  const tickAll = (list, on) => () => { list.forEach(d => (on ? state.domains.add(d.key) : state.domains.delete(d.key))); refreshPanel(); relayout(); };
  $u('all').onclick = tickAll(BUSINESS, true); $u('none').onclick = tickAll(BUSINESS, false);
  $u('sys-all').onclick = tickAll(SYSTEMS, true); $u('sys-none').onclick = tickAll(SYSTEMS, false);
  // the all / none links are reachable by keyboard, in the order of the markup
  ['all', 'none', 'sys-all', 'sys-none'].forEach(id => {
    const a = $u(id); a.tabIndex = 0; a.setAttribute('role', 'button');
    a.onkeydown = ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); a.click(); } };
  });
  sidePanel('u', () => { resize(); fit(false); });
  $u('export-h').textContent = L.exportImage;
  $u('export').textContent = L.png; $u('export').title = T.pngTitle;
  $u('export').onclick = () => EXPORT.save('universe', 'png', image, $u('export'));
  $u('fit').onclick = () => fit(true);
  $u('names').innerHTML = N.map(n => `<option value="${esc(n.name)}">`).join('');
  // a table by its exact name, case-insensitive (search box, Trajectory button)
  function findByName(text) { const q = String(text).trim().toLowerCase(); return N.find(n => n.name.toLowerCase() === q); }
  // the three filters (domain, layer, type), read from the state
  const passes = n => state.domains.has(n.domain) && state.layers.has(n.layer) && state.kinds.has(n.kind);
  // tick back on the domain, layer and type of a table that is filtered out; true when it was hidden
  function tick(i) {
    const n = N[i];
    if (passes(n)) return false;
    state.domains.add(n.domain); state.layers.add(n.layer); state.kinds.add(n.kind);
    return true;
  }
  // tick back on the filtered-out tables among `indices`; recompute once if anything changed; returns how
  // many of the listed tables were hidden by the filters (a folded table is not: reveal never opens an entity)
  function reveal(indices) {
    const hidden = indices.filter(tick).length;
    if (hidden) { refreshPanel(); relayout(); }
    return hidden;
  }
  // would the fold draw table i inside its parent now? (the fold is on, the parent is drawn, its entity is not
  // the one opened by the search); a trajectory member is never folded (D-063)
  const foldable = i => state.fold && PARENT[i] >= 0 && passes(N[PARENT[i]]);
  const wouldFold = i => foldable(i) && PARENT[i] !== opened;
  // the trajectory members the fold would otherwise hide: what makes entering or leaving a trajectory relayout
  const unfoldedKey = () => trajMembers().filter(wouldFold).sort((a, b) => a - b).join();
  $u('q').onchange = ev => {
    const n = findByName(ev.target.value);
    if (!n) return;
    // a folded table opens its entity (one at a time); any other table closes it
    const before = opened, hidden = tick(n.i);
    const inFold = foldable(n.i);
    if (inFold) { if (!(traj && trajMembers().includes(n.i))) opened = PARENT[n.i]; } else opened = null;
    if (hidden) refreshPanel();
    if (hidden || opened !== before) relayout();
    if (opened !== before && opened != null) $u('live').textContent = T.openedLive(n.name, N[opened].name);
    found = n.i;
    zoomTo(P[n.i].x, P[n.i].y, Math.max(t.k, 1.5, kStars() * 1.05));
  };

  // ---------------------------------------------------------------- geometry
  // Each table reserves the room of what it shows: its star and name, or a card with keys / all fields.
  // oy: offset of the reserved box's centre from the table's point (the star centre). At names level the
  // box runs from the star top to the bottom of the label drawn below it (one or two lines, nameLines); the
  // label width is estimated (11 px, bold), never measured, so the placement does not depend on the fonts
  // installed (D-040).
  // An entity holding tables reserves 6 px more on its top and right for its badge (D-063); its card also
  // lists the tables folded into it under the columns (at most HELD_ROWS, then "+ N").
  function box(n) {
    const held = HELD.get(n.i) || [];
    if (state.detail === 'names') {
      const r = starR(n), lines = nameLines(n.name), longest = d3.max(lines, s => s.length), up = held.length ? 6 : 0;
      return { w: Math.max(6 + longest * 6.2, 2 * r + (up ? 16 : 4)), h: 2 * r + 4 + LINE_H * lines.length + up,
               oy: LINE_H / 2 * lines.length - up / 2 };
    }
    const rows = state.detail === 'keys' ? n.cols.filter(c => c[2]) : n.cols, shown = rows.slice(0, 30);
    const folded = held.slice(0, HELD_ROWS).map(i => [N[i].name, labelOf(KIND[N[i].kind])]);
    const chars = Math.max(n.name.length * 1.15, ...shown.map(r => r[0].length + 1 + r[1].length * 0.8),
      ...folded.map(r => r[0].length + 1 + r[1].length * 0.8), 10);
    const cw = 16 + chars * 5.6, extra = held.length ? 10 + 11 * (folded.length + (held.length > HELD_ROWS ? 1 : 0)) : 0;
    const ch = 18 + shown.length * 11 + (rows.length > shown.length ? 11 : 0) + extra, pad = held.length ? 6 : 0;
    return { w: cw + pad, h: ch + pad, cw, ch, oy: 0, shown, more: rows.length - shown.length, folded,
             heldMore: held.length - folded.length };
  }

  // A table's name as drawn below its star: one line up to 14 characters, else two, split after the `__`
  // nearest the middle, else after the `_` nearest the middle (a name without `_` stays on one line)
  const LINE_H = 14;
  const HELD_ROWS = 12;   // folded tables listed on a card, then "+ N"
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
    // the three sets (D-063): pass (the filters), folded now (inside an entity), visible = drawn = pass minus folded
    pass = N.filter(passes);
    PASS = new Uint8Array(N.length); pass.forEach(n => { PASS[n.i] = 1; });
    const members = new Set(trajMembers());
    FOLDNOW = new Uint8Array(N.length); HELD = new Map();
    pass.forEach(n => {
      if (!wouldFold(n.i) || members.has(n.i)) return;
      FOLDNOW[n.i] = 1;
      if (!HELD.has(PARENT[n.i])) HELD.set(PARENT[n.i], []);
      HELD.get(PARENT[n.i]).push(n.i);
    });
    visible = pass.filter(n => !FOLDNOW[n.i]);
    B = []; visible.forEach(n => B[n.i] = box(n));
    // the links between tables that pass (counted, and the routes' weight); only those between drawn tables are drawn
    const seen = new Set(), links = [];
    const add = list => list.forEach(([a, b]) => {
      const key = a < b ? a + ',' + b : b + ',' + a;
      if (PASS[a] && PASS[b] && !seen.has(key)) { seen.add(key); links.push([a, b]); }
    });
    if (state.links !== 'lineage') add(DATA.relations);
    if (state.links !== 'relations') add(DATA.lineage);
    linkCount = links.length;
    edges = links.filter(([a, b]) => !FOLDNOW[a] && !FOLDNOW[b]);

    const G = grouping(), local = new Map();
    // a table's reserved box depends on what it holds: its held ids (cards) or whether it holds any (names)
    const heldKey = n => state.detail === 'names' ? (HELD.has(n.i) ? 'h' : '') : (HELD.get(n.i) || []).join('.');
    for (const [key, group] of d3.group(visible, G.of)) {
      // a constellation's inner layout only depends on the grouping, its own tables, links and detail level
      const cached = [state.by, key, state.detail, state.links, group.map(n => n.i + heldKey(n)).join(',')].join('|');
      if (!layoutCache.has(cached)) layoutCache.set(cached, layoutConstellation(key, group));
      local.set(key, layoutCache.get(cached));
    }

    // manual arrangement: a moved table keeps its offset from its constellation's centre, a moved
    // constellation is pinned
    const saved = savedLayout();
    REL = new Map();
    for (const [, dl] of local) placeAroundDragged(dl.ns, saved.nodes);
    // what a constellation holds is counted over the tables that pass, folded ones included (D-063)
    const held = d3.group(pass, G.of);
    constellations = [...local].map(([k, v]) => {
      const all = held.get(k), bands = v.bands.map(b => ({ ...b }));
      all.forEach(n => { if (FOLDNOW[n.i]) bands[v.bandOf.get(PARENT[n.i])].n++; });
      return { k, rank: v.rank, n: all.length, bands, r: Math.max(v.R, d3.max(v.ns, s => reach(s.i))),
               mix: [...d3.rollup(all, g => g.length, n => n.kind)].sort((a, b) => b[1] - a[1]) };
    });
    constellations.forEach(d => { const p = saved[G.pins][d.k]; if (p) { d.fx = p[0]; d.fy = p[1]; } });
    const t1 = performance.now();
    refR = referenceRadius();
    constellations.forEach(d => { d.sum = summaryOf(d, held.get(d.k)); });
    perf.summary = performance.now() - t1;
    // constellations: linked ones attract, ordered left to right along the flow, never overlapping; the links
    // of folded tables count (a parent shares its table's constellation). Unpinned source systems are not in the
    // simulation: they fill a grid on the left (D-069); business domains take their column from the flow (D-070)
    routes = routePairs(G);
    const free = constellations.filter(d => isSystem(d.k) && d.fx == null), sim = constellations.filter(d => !free.includes(d));
    const simKeys = new Set(sim.map(d => d.k)), columns = byFlow(sim, routes);
    const simLinks = routes.filter(r => simKeys.has(r.source) && simKeys.has(r.target)).map(r => ({ source: r.source, target: r.target, c: r.c }));
    const rand = d3.randomLcg(42), W = (d3.mean(sim.length ? sim : constellations, d => d.r) || 1) * 2.4;
    const simulation = d3.forceSimulation(sim).randomSource(rand)
      // the padding leaves room for the domain name drawn above each constellation
      .force('collide', d3.forceCollide(d => collideR(d)).iterations(3))
      .force('link', d3.forceLink(simLinks).id(d => d.k).distance(l => l.source.r + l.target.r + 60)
        .strength(l => Math.min(0.4, 0.03 + Math.log1p(l.c) * 0.04)))
      .force('x', d3.forceX(d => (columns.get(d.k) ?? d.rank) * W).strength(state.by === 'domains' && !columns.size ? 0.06 : G.flowX))
      .force('y', d3.forceY(0).strength(0.06))
      .force('charge', d3.forceManyBody().strength(-20))
      .stop();
    for (let k = 0; k < 400; k++) simulation.tick();
    // settle with collisions only, so link forces can't leave constellations overlapping
    simulation.force('link', null).force('x', null).force('y', null).force('charge', null);
    for (let k = 0; k < 100; k++) simulation.tick();
    placeSystems(free, sim, routes);
    const t2 = performance.now();
    renderSummaryText();
    perf.summary += performance.now() - t2;

    P = [];
    constellations.forEach(d => local.get(d.k).ns.forEach(s => { const [dx, dy] = REL.get(s.i); P[s.i] = { x: d.x + dx, y: d.y + dy }; }));
    tree = d3.quadtree(visible, n => P[n.i].x, n => P[n.i].y);
    geomVer++;
    perf.layout = performance.now() - t0;
  }

  // ---- constellation routes and placement (M8.4, D-069 to D-071)
  const isSystem = key => HAS_SYS && state.by === 'domains' && SYS.has(key);   // a source system in this drawing
  const collideR = d => d.r + 30 + d.r * 0.15;   // the room the placement keeps around a disc, name included
  const GRID_GAP = 120, FLOW_X_BUSINESS = 0.15, DIRECTED = 0.2;   // grid gap (world px), x strength of a business domain, direction threshold
  const pairKey = (a, b) => (a < b ? a + '|' + b : b + '|' + a);
  // The routes of the grouping: one per pair of constellations linked through tables that pass the filters (folded
  // ones included). rel / lin: relations and lineage links; c: the count the Links selector shows; f: net lineage
  // flow from source to target (the sorted keys); dir: +1 target reads source, -1 source reads target, 2 each reads
  // the other, 0 none (relations only, or Links = relations: a relation has no direction)
  function routePairs(G) {
    const by = new Map(), seen = { rel: new Set(), lin: new Set(), all: new Set() };
    const slot = (da, db) => {
      const k = pairKey(da, db);
      if (!by.has(k)) by.set(k, { source: da < db ? da : db, target: da < db ? db : da, rel: 0, lin: 0, u: 0, f: 0 });
      return by.get(k);
    };
    const add = (list, field) => list.forEach(([a, b]) => {
      if (!PASS[a] || !PASS[b]) return;
      const da = G.of(N[a]), db = G.of(N[b]);
      if (da === db) return;
      const key = a < b ? a + ',' + b : b + ',' + a, p = slot(da, db);
      if (!seen[field].has(key)) { seen[field].add(key); p[field]++; }
      if (!seen.all.has(key)) { seen.all.add(key); p.u++; }
    });
    add(DATA.relations, 'rel'); add(DATA.lineage, 'lin');
    DATA.lineage.forEach(([child, parent]) => {   // data flows from parent to child
      if (!PASS[child] || !PASS[parent]) return;
      const from = G.of(N[parent]), to = G.of(N[child]);
      if (from !== to) slot(from, to).f += from < to ? 1 : -1;
    });
    return [...by.values()].map(p => ({ ...p, ...countAndDir(p) })).filter(p => p.c > 0)
      .sort((a, b) => (a.source < b.source ? -1 : a.source > b.source ? 1 : a.target < b.target ? -1 : a.target > b.target ? 1 : 0));
  }
  const countAndDir = p => ({ c: state.links === 'relations' ? p.rel : state.links === 'lineage' ? p.lin : p.u, dir: dirOf(p) });
  // the upstream and downstream ends of a directed route ([] when it has no single direction)
  const dirOf = p => (state.links === 'relations' || !p.lin ? 0 : Math.abs(p.f) > DIRECTED * p.lin ? Math.sign(p.f) : 2);
  const flowEnds = r => (r.dir === 1 ? [r.source, r.target] : r.dir === -1 ? [r.target, r.source] : []);
  // The x targets of the business domains along the data flow (D-070): the columns of `flowRanks` over the directed
  // routes between them (members in a fixed order, so cycles break the same way on every machine); a domain without
  // directed route takes the mean column. null without any directed route: the layers decide, as before.
  function flowColumns(keys, directed) {
    const used = new Set(directed.flat());
    const ranked = keys.filter(k => used.has(k));
    if (!ranked.length) return null;
    const { rank } = flowRanks(keys, directed, () => null), mean = d3.mean(ranked, k => rank.get(k));
    return new Map(keys.map(k => [k, used.has(k) ? rank.get(k) : mean]));
  }
  function byFlow(sim, model) {
    if (state.by !== 'domains' || state.links === 'relations') return new Map();
    const business = sim.filter(d => !isSystem(d.k)).sort((a, b) => a.rank - b.rank || (a.k < b.k ? -1 : 1)), keys = business.map(d => d.k);
    const directed = model.filter(r => r.dir && keys.includes(r.source) && keys.includes(r.target)).map(flowEnds);
    return flowColumns(keys, directed) || new Map();
  }
  // The unpinned source systems in a grid left of the business domains: ordered by the barycentre of the business
  // domains they feed (route-weighted, none last, then the panel order), one column while they fit the height of
  // the business box, else the fewest columns that fit, filled column by column; the grid's right edge is GRID_GAP
  // left of the leftmost business disc and its columns are centred on the box's centre (on 0 without business)
  let gridOrder = new Map();
  // constellations in the order of the source-systems grid, the panel order for the unplaced
  const inGridOrder = list => [...list].sort((a, b) => (gridOrder.get(a.k) ?? Infinity) - (gridOrder.get(b.k) ?? Infinity) || DOM_POS[a.k] - DOM_POS[b.k]);
  function placeSystems(free, sim, model) {
    gridOrder = new Map();
    if (!free.length) return;
    const at = new Map(sim.filter(d => !isSystem(d.k)).map(d => [d.k, d]));
    const bary = d => {
      let w = 0, y = 0;
      model.forEach(r => { const o = r.source === d.k ? r.target : r.target === d.k ? r.source : null; if (at.has(o)) { w += r.c; y += r.c * at.get(o).y; } });
      return w ? y / w : Infinity;
    };
    const order = free.map(d => ({ d, y: bary(d) }))
      .sort((a, b) => (a.y === b.y ? DOM_POS[a.d.k] - DOM_POS[b.d.k] : a.y < b.y ? -1 : 1)).map(o => o.d);
    const diam = d => 2 * collideR(d), cell = d3.max(order, diam);
    const top = sim.length ? d3.min(sim, d => d.y - collideR(d)) : 0, bottom = sim.length ? d3.max(sim, d => d.y + collideR(d)) : 0;
    const height = Math.max(cell, bottom - top), cy = (top + bottom) / 2, cols = [];
    let col = null, used = 0;
    order.forEach(d => {
      if (!col || used + diam(d) > height) { col = []; cols.push(col); used = 0; }
      col.push(d); used += diam(d);
    });
    const right = sim.length ? d3.min(sim, d => d.x - collideR(d)) - GRID_GAP : cell * cols.length / 2;
    cols.forEach((list, j) => {
      const x = right - cell / 2 - (cols.length - 1 - j) * cell;
      let y = cy - d3.sum(list, diam) / 2;
      list.forEach(d => { d.x = x; d.y = y + diam(d) / 2; y += diam(d); });
    });
    gridOrder = new Map(cols.flat().map((d, i) => [d.k, i]));
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
  // What a constellation stands for (D-048): of, its key for a table; band, a table's band position (null:
  // no band, placed by lineage); bandKey, a band position's key; rank, the constellation's x target along
  // the flow; flowX, the strength of that target; pins, the key of saved centres; scope, the layout scope
  const BY = {
    domains: { of: n => n.domain, band: layerPos, bandKey: pos => DATA.layers[pos].key,
               rank: (key, members) => d3.mean(members, n => LAYER[n.layer].rank), flowX: FLOW_X_BUSINESS,
               pins: 'domains', scope: () => (folding() ? 'folded:' : '') + state.detail },
    layers: { of: n => n.layer, band: n => DOM_POS[n.domain], bandKey: pos => DOM_LIST[pos].key,
              rank: key => LAYER[key].rank, flowX: 0.3, pins: 'layers',
              scope: () => 'layers:' + (folding() ? 'folded:' : '') + state.detail },
  };
  const grouping = () => BY[state.by];
  const PACK = { PAD: 6, STRIP_GAP: 8, BAND_GAP: 20, TRIES: 24, REFINE: 6 };

  // A constellation's tables in bands, left to right (layer bands along the data flow, or domain bands in
  // the order of the Domains panel), in the smallest circle (D-040).
  // A band is one column, split into balanced columns when taller than a height H; H is scanned to give the
  // smallest circle around the reserved boxes. No simulation and no randomness: the same tables give the
  // same offsets on every machine.
  // -> { ns: [{i, x, y}] offsets of the star from the circle centre, R, rank, bands: [{key, n, x0, x1}] }
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
    const bandOf = new Map(bands.flatMap((band, j) => band.tables.map(n => [n.i, j])));
    return { ns: all.map((b, j) => ({ i: b.i, x: best.at[j].x, y: best.at[j].y - b.oy })), R, bandOf,
             rank: grouping().rank(key, members),
             bands: bands.map((band, j) => ({ key: band.key, n: band.tables.length, x0: best.bands[j][0], x1: best.bands[j][1] })) };
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
        if (h + PAD + b.h > cap) { cols.push([]); h = -PAD; }
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
  const C = { bg: THEME.bg, text: THEME.fg, muted: THEME.muted, card: '#ffffff', route: 'rgba(71,85,105,.6)',
              arrow: 'rgba(71,85,105,.8)', edge: 'rgba(100,116,139,.22)', cross: 'rgba(100,116,139,.10)', hl: 'rgba(31,41,51,.85)',
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

  // filled arrowhead centred at (mx, my), pointing along `ang`, in the current fill style
  function arrowAt(mx, my, ang, size) {
    ctx.beginPath(); ctx.moveTo(mx + Math.cos(ang) * size, my + Math.sin(ang) * size);
    ctx.lineTo(mx + Math.cos(ang + 2.5) * size, my + Math.sin(ang + 2.5) * size);
    ctx.lineTo(mx + Math.cos(ang - 2.5) * size, my + Math.sin(ang - 2.5) * size); ctx.fill();
  }
  // arrowhead at 55 % of the segment a -> b, pointing at b (the links between tables)
  const arrowHead = (ax, ay, bx, by, size) =>
    arrowAt(ax + (bx - ax) * 0.55, ay + (by - ay) * 0.55, Math.atan2(by - ay, bx - ax), size);
  // side of a table in the trajectory: 'start' | 'up' | 'down' | null (a table in both maps is drawn as upstream)
  const sideOf = i => !traj ? null : i === traj.start ? 'start' : traj.up.has(i) ? 'up' : traj.down.has(i) ? 'down' : null;
  const trajMembers = () => traj ? [traj.start, ...traj.up.keys(), ...traj.down.keys()] : [];
  const trajDist = i => i === traj.start ? 0 : Math.min(traj.up.get(i) ?? Infinity, traj.down.get(i) ?? Infinity);

  // ---------------------------------------------------------------- routes (M8.4, D-071)
  // A route joins two constellations. Its path goes from centre to centre around the other constellations (computed
  // once per layout and per drag step, in world space, held in a polyline), is clipped at draw time to the outline of
  // each end (the disc, or the card while the summary weight is above 0) and ends with an arrowhead at its reader.
  // the room a route keeps around a constellation: its disc and its card (a square of half-side 0.9 r, D-065) plus MARGIN
  const MARGIN = 20;
  const obstacleOf = d => ({ k: d.k, x: d.x, y: d.y, cr: d.r + MARGIN, hw: 0.9 * d.r + MARGIN, hh: 0.9 * d.r + MARGIN, r: 1.27 * d.r + MARGIN });
  const AROUND_MAX = 14;   // obstacles around a route above which the last resort (a visibility graph) is not tried
  const ROUTES_PER = 3, CLEAR = 10, SAMPLES = 24, BENDS = [0.15, -0.15, 0.3, -0.3, 0.5, -0.5, 0.75, -0.75, 1, -1];
  const lerp2 = (p, q, f) => [p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f];
  const steps = n => Array.from({ length: n + 1 }, (_, i) => i / n);
  const straightPts = (a, b) => steps(SAMPLES).map(f => lerp2([a.x, a.y], [b.x, b.y], f));
  // a quadratic Bezier whose control point is h * length to the left of a -> b
  function bentPts(a, b, h) {
    const cx = (a.x + b.x) / 2 - (b.y - a.y) * h, cy = (a.y + b.y) / 2 + (b.x - a.x) * h;
    return steps(SAMPLES).map(f => [(1 - f) ** 2 * a.x + 2 * f * (1 - f) * cx + f * f * b.x, (1 - f) ** 2 * a.y + 2 * f * (1 - f) * cy + f * f * b.y]);
  }
  // a uniform Catmull-Rom spline through the points of P
  function smoothPts(P) {
    const out = [];
    for (let i = 0; i < P.length - 1; i++) {
      const p0 = P[Math.max(0, i - 1)], p1 = P[i], p2 = P[i + 1], p3 = P[Math.min(P.length - 1, i + 2)];
      for (let j = 0; j < 12; j++) {
        const f = j / 12, f2 = f * f, f3 = f2 * f;
        out.push([0, 1].map(c => 0.5 * (2 * p1[c] + (p2[c] - p0[c]) * f + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * f2
          + (3 * p1[c] - p0[c] - 3 * p2[c] + p3[c]) * f3)));
      }
    }
    out.push(P[P.length - 1]);
    return out;
  }
  // the distance from the point (px, py) to the segment p -> q
  function segmentDist(px, py, p, q) {
    const dx = q[0] - p[0], dy = q[1] - p[1], l2 = dx * dx + dy * dy;
    const f = l2 ? Math.max(0, Math.min(1, ((px - p[0]) * dx + (py - p[1]) * dy) / l2)) : 0;
    return Math.hypot(px - p[0] - dx * f, py - p[1] - dy * f);
  }
  // does the segment p -> q meet the obstacle: its circle (cr > 0), its rectangle (hw > 0), or both (their union)?
  function segmentHits(p, q, o) {
    const dx = q[0] - p[0], dy = q[1] - p[1];
    if (o.cr && segmentDist(o.x, o.y, p, q) < o.cr) return true;
    if (!o.hw) return false;
    let t0 = 0, t1 = 1;   // Liang-Barsky against the rectangle
    for (const [d, dist] of [[-dx, p[0] - (o.x - o.hw)], [dx, o.x + o.hw - p[0]], [-dy, p[1] - (o.y - o.hh)], [dy, o.y + o.hh - p[1]]]) {
      if (d === 0) { if (dist < 0) return false; continue; }
      const f = dist / d;
      if (d < 0) { if (f > t1) return false; t0 = Math.max(t0, f); } else { if (f < t0) return false; t1 = Math.min(t1, f); }
    }
    return true;
  }
  const boxOf = pts => pts.reduce((b, [x, y]) => [Math.min(b[0], x), Math.max(b[1], x), Math.min(b[2], y), Math.max(b[3], y)], [Infinity, -Infinity, Infinity, -Infinity]);
  const apart = (b, o) => { const ex = Math.max(o.cr, o.hw), ey = Math.max(o.cr, o.hh); return o.x + ex < b[0] || o.x - ex > b[1] || o.y + ey < b[2] || o.y - ey > b[3]; };
  // does the polyline meet any obstacle? (stops at the first)
  const blockedBy = (pts, obs) => { const b = boxOf(pts); return obs.some(o => !apart(b, o) && pts.some((p, j) => j && segmentHits(pts[j - 1], p, o))); };
  // how many obstacles a polyline meets, and the first one along it
  function crossed(pts, obs) {
    let n = 0, first = null, at = Infinity;
    const box = boxOf(pts);
    obs.forEach(o => {
      if (apart(box, o)) return;
      const i = pts.findIndex((p, j) => j && segmentHits(pts[j - 1], p, o));
      if (i > 0) { n++; if (i < at) { at = i; first = o; } }
    });
    return { n, first };
  }
  // The path from a to b (anything with x, y) clearing `obs` ({x, y, r}, or a rectangle with hw, hh): the straight
  // segment, else the first quadratic bend that clears, else a spline through one or two waypoints beside the
  // obstacles met, else the shortest way around them; when nothing clears, the candidate meeting the fewest obstacles,
  // flagged `clear: false`.
  function routePath(a, b, obs, deep = true) {
    const tried = [], clear = pts => { tried.push(pts); return !blockedBy(pts, obs); };
    const direct = straightPts(a, b);
    if (clear(direct)) return { pts: direct, clear: true };
    for (const h of BENDS) { const pts = bentPts(a, b, h); if (clear(pts)) return { pts, clear: true }; }
    const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1, nx = -dy / len, ny = dx / len;
    const along = p => (p[0] - a.x) * dx + (p[1] - a.y) * dy;
    const through = (ws, depth, hit) => {
      for (const side of [1, -1]) {
        const w = [hit.x + side * nx * (hit.r + CLEAR), hit.y + side * ny * (hit.r + CLEAR)];
        const chain = [...ws, w].sort((p, q) => along(p) - along(q));
        const pts = smoothPts([[a.x, a.y], ...chain, [b.x, b.y]]);
        if (clear(pts)) return pts;
        const next = depth > 1 ? crossed(pts, obs).first : null, deeper = next ? through(chain, depth - 1, next) : null;
        if (deeper) return deeper;
      }
      return null;
    };
    const found = through([], 2, crossed(direct, obs).first) || (deep ? around(a, b, obs, clear) : null);
    if (found) return { pts: found, clear: true };
    // nothing clears: the candidate meeting the fewest obstacles (the earliest of equals), flagged
    const fewest = tried.map(pts => crossed(pts, obs).n);
    return { pts: tried[fewest.indexOf(Math.min(...fewest))], clear: false };
  }
  // The last resort: the shortest path through the corners of the obstacles around the segment (a visibility graph,
  // A*), checked against every obstacle; null when no path exists or the path does not clear
  function around(a, b, obs, clear) {
    const len = Math.hypot(b.x - a.x, b.y - a.y), mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    const near = obs.filter(o => Math.hypot(o.x - mx, o.y - my) < 0.75 * len + o.r);
    if (near.length > AROUND_MAX) return null;   // a crowded universe: the cost grows with the square of the corners
    const nodes = [[a.x, a.y], [b.x, b.y]];
    near.forEach(o => {
      const ring = o.cr ? 8 : 0, rr = (o.cr + 3) / Math.cos(Math.PI / 8);
      for (let j = 0; j < ring; j++) nodes.push([o.x + rr * Math.cos(2 * Math.PI * j / ring), o.y + rr * Math.sin(2 * Math.PI * j / ring)]);
      if (o.hw) [[1, 1], [1, -1], [-1, 1], [-1, -1]].forEach(([sx, sy]) => nodes.push([o.x + sx * (o.hw + 3), o.y + sy * (o.hh + 3)]));
    });
    const free = nodes.filter((n, j) => j < 2 || !near.some(o => segmentHits(n, n, o)));
    const dist = free.map(() => Infinity), prev = free.map(() => -1), done = free.map(() => false);
    dist[0] = 0;
    const toward = n => Math.hypot(n[0] - b.x, n[1] - b.y);   // A*: the straight distance to the goal
    for (;;) {
      let u = -1;
      free.forEach((n, j) => { if (!done[j] && dist[j] < Infinity && (u < 0 || dist[j] + toward(n) < dist[u] + toward(free[u]))) u = j; });
      if (u < 0 || u === 1) break;
      done[u] = true;
      free.forEach((n, j) => {
        if (done[j]) return;
        const d = dist[u] + Math.hypot(n[0] - free[u][0], n[1] - free[u][1]);
        if (d < dist[j] && !near.some(o => segmentHits(free[u], n, o))) { dist[j] = d; prev[j] = u; }
      });
    }
    if (prev[1] < 0) return null;
    const way = [];
    for (let j = 1; j >= 0; j = prev[j]) way.unshift(free[j]);
    const soft = smoothPts(way);
    if (clear(soft)) return soft;
    const corners = sampleLine(way);   // the polyline itself, when rounding its corners costs the room
    return clear(corners) ? corners : null;
  }
  // a polyline resampled to about 3 points per segment of its corners (the ends kept)
  const sampleLine = way => way.flatMap((p, j) => (j ? steps(8).slice(1).map(f => lerp2(way[j - 1], p, f)) : [p]));
  // The path of the key between the ends a and b, stored in the model: the path of the previous model stays while its
  // ends have not moved and it still clears every obstacle, else it is found again. The time adds to this frame's perf.
  function pathFor(rm, key, a, b, obs) {
    const t0 = performance.now(), at = [a.x, a.y, b.x, b.y].join(), before = rm.before && rm.before.get(key);
    const kept = before && before.at === at && before.clear && !crossed(before.pts, obs).n;
    const path = kept ? before : { ...routePath(a, b, obs, !dragging), at };
    rm.paths.set(key, path);
    perf.routes += performance.now() - t0;
    return path;
  }
  // the world polyline of the pair (from, to) at its ends' centres, in that direction; cached with the route model
  function pathBetween(from, to) {
    const rm = routeModel(), key = pairKey(from, to);
    if (!rm.paths.has(key)) {
      const obs = rm.circles.filter(o => o.k !== from && o.k !== to).concat(rm.grp && !rm.members.has(from) && !rm.members.has(to) ? [rm.groupObs] : []);
      const end = k => (k === GROUP ? rm.grp : rm.by.get(k));
      pathFor(rm, key, ...(from < to ? [end(from), end(to)] : [end(to), end(from)]), obs);
    }
    const p = rm.paths.get(key);
    return from < to ? p : { ...p, pts: [...p.pts].reverse() };
  }

  // ---- the source-systems group (D-069)
  // The group card replaces the cards of the passing source systems in domain mode when there are two or more and the
  // box of their discs holds no business disc; null otherwise. Recomputed when a constellation moves.
  let groupCache = null;
  function systemsGroup() {
    if (groupCache && groupCache.ver === geomVer) return groupCache.g;
    let g = null;
    let members = constellations.filter(d => isSystem(d.k));
    if (members.length >= 2) {
      const x0 = d3.min(members, d => d.x - d.r), x1 = d3.max(members, d => d.x + d.r), y0 = d3.min(members, d => d.y - d.r), y1 = d3.max(members, d => d.y + d.r);
      const meets = d => { const cx = Math.max(x0, Math.min(d.x, x1)), cy = Math.max(y0, Math.min(d.y, y1)); return Math.hypot(d.x - cx, d.y - cy) < d.r; };
      if (!constellations.some(d => !isSystem(d.k) && meets(d))) {
        members = inGridOrder(members);
        const rows = members.map(d => ({ key: d.k, n: d.n, kinds: inKindOrder(d.mix) }));
        g = { k: GROUP, group: true, members, x: (x0 + x1) / 2, y: (y0 + y1) / 2, r: d3.max(members, d => d.r), gridW: x1 - x0, gridH: y1 - y0, n: d3.sum(members, d => d.n),
              mix: [...d3.rollup(members.flatMap(d => d.mix), v => d3.sum(v, m => m[1]), m => m[0])], sum: { rows, entities: null, main: [] } };
      }
    }
    groupCache = { ver: geomVer, g };
    return g;
  }
  // The routes of the group: those of its members with a business domain are summed per domain (flow oriented from the
  // group), those between two members are dropped (they are inside the card); the others are kept as they are.
  function bundleRoutes(model, memberKeys) {
    const keep = [], by = new Map();
    model.forEach(r => {
      const s = memberKeys.has(r.source), tg = memberKeys.has(r.target);
      if (s && tg) return;
      if (!s && !tg) { keep.push(r); return; }
      const other = s ? r.target : r.source;
      if (!by.has(other)) by.set(other, { source: GROUP, target: other, rel: 0, lin: 0, u: 0, f: 0, c: 0, from: [], bundled: true });
      const b = by.get(other);
      b.rel += r.rel; b.lin += r.lin; b.u += r.u; b.c += r.c; b.f += s ? r.f : -r.f; b.from.push({ key: s ? r.source : r.target, c: r.c });
    });
    const bundled = [...by.values()].sort((p, q) => (p.target < q.target ? -1 : 1)).map(b => ({ ...b, dir: dirOf(b), from: b.from.sort((p, q) => q.c - p.c || (p.key < q.key ? -1 : 1)) }));
    return { keep, bundled };
  }
  // The route model of the current geometry: the routes with their paths, both sets (the individual one, and the one
  // where the group's routes are bundled), cached until a constellation moves
  let routeCache = null;
  function routeModel() {
    if (routeCache && routeCache.ver === geomVer) return routeCache;
    const t0 = performance.now(), grp = systemsGroup(), by = new Map(constellations.map(d => [d.k, d]));
    const circles = constellations.map(obstacleOf);
    const members = new Set(grp ? grp.members.map(d => d.k) : []);
    const groupObs = grp ? { k: GROUP, x: grp.x, y: grp.y, cr: 0, hw: 0.9 * grp.r + MARGIN, hh: grp.gridH / 2 + MARGIN, r: Math.hypot(0.9 * grp.r, grp.gridH / 2) + MARGIN } : null;
    const rm = { ver: geomVer, grp, by, circles, members, groupObs, paths: new Map(), indiv: [], bundled: null, before: routeCache && routeCache.paths };
    routeCache = rm;   // set first: pathBetween reads the model it is filling
    rm.indiv = routes.map(r => ({ ...r }));   // paths are found when a route is drawn or asked for (pathOf)
    if (grp) {
      const { keep, bundled } = bundleRoutes(rm.indiv, members);
      rm.bundled = [...keep, ...bundled];
    }
    rm.strongIndiv = strongOf(rm.indiv); rm.strongBundled = rm.bundled ? strongOf(rm.bundled) : null;
    perf.routes += performance.now() - t0;   // the model; the paths drawn add their time as they are found
    return rm;
  }
  // the path of a bundled route (group card to a business domain), kept like the others while nothing moved
  function bundledPath(rm, b) {
    const key = GROUP + '|' + b.target;
    if (rm.paths.has(key)) return rm.paths.get(key);
    return pathFor(rm, key, rm.grp, rm.by.get(b.target), rm.circles.filter(o => !rm.members.has(o.k) && o.k !== b.target));
  }
  // the path of a route of the current model: { pts (centre to centre, world), clear }
  const pathOf = r => (r.bundled ? bundledPath(routeModel(), r) : pathBetween(r.source, r.target));
  // The routes drawn by default (D-071). A source system keeps at most its ROUTES_PER heaviest routes, never of weight 1
  // and no tie kept (weight, then the other end's key); a route between two systems must be kept by both. Any other
  // route is kept when it is among the ROUTES_PER heaviest of either end, ties included.
  function strongOf(list) {
    const top = new Map(), own = new Map(), add = (map, k, v) => { if (!map.has(k)) map.set(k, []); map.get(k).push(v); };
    const systems = r => [r.source, r.target].filter(isSystem), other = (r, k) => (r.source === k ? r.target : r.source);
    list.forEach(r => { [r.source, r.target].forEach(k => add(top, k, r.c)); systems(r).forEach(k => add(own, k, r)); });
    top.forEach(v => v.sort((a, b) => b - a));
    const floor = k => (top.get(k).length >= ROUTES_PER ? top.get(k)[ROUTES_PER - 1] : 0);
    const chosen = new Map([...own].map(([k, v]) => [k, new Set(v.filter(r => r.c > 1)
      .sort((p, q) => q.c - p.c || (other(p, k) < other(q, k) ? -1 : 1)).slice(0, ROUTES_PER))]));
    return new Set(list.filter(r => (systems(r).length ? systems(r).every(k => chosen.get(k).has(r))
      : r.c >= floor(r.source) || r.c >= floor(r.target))));
  }
  // What the frame draws of the routes at summary weight a: the sets (with their alpha), the one the pointer and the
  // counts act on, the spotlight and the constellations it keeps lit
  function routeView(a, routesOn) {
    const rm = routeModel(), sets = [{ list: rm.indiv, strong: rm.strongIndiv, alpha: rm.bundled ? 1 - a : 1, bundled: false }];
    if (rm.bundled) sets.push({ list: rm.bundled, strong: rm.strongBundled, alpha: a, bundled: true });
    const cur = rm.bundled && a >= 0.5 ? sets[1] : sets[0], all = showAll && !traj;
    let sp = !traj && routesOn ? spot : null;
    if (sp && rm.bundled && a >= 0.5 && rm.members.has(sp)) sp = GROUP;
    if (sp === GROUP && cur !== sets[1]) sp = null;
    // a route is kept by default when it is strong and its path clears the other constellations (paths are found only
    // for a set the frame draws); "all routes" and the spotlight draw the others
    sets.forEach(s => {
      s.kept = !routesOn || s.alpha < 0.01 ? [...s.strong] : s.list.filter(r => s.strong.has(r) && pathOf(r).clear);
      s.shown = all ? s.list : s.kept;
    });
    let near = null;
    if (sp) {
      near = new Set([sp]);
      cur.list.forEach(r => { if (r.source === sp) near.add(r.target); else if (r.target === sp) near.add(r.source); });
      if (near.has(GROUP)) rm.members.forEach(k => near.add(k));
    }
    return { rm, sets, cur, sp, near, hides: cur.kept.length < cur.list.length };
  }
  // the outline of a constellation (or the group) at weight a: its disc, and its card while the cards are drawn (world px)
  function outlineOf(key, rm, plans) {
    const d = key === GROUP ? rm.grp : rm.by.get(key), p = plans.get(key);
    return { x: d.x, y: d.y, r: key === GROUP ? 0 : d.r, card: p ? { hw: p.sq.w / 2 / t.k, hh: p.plan.h / 2 / t.k } : null };
  }
  // the fractional index at which a polyline (from its start) leaves `inside`; the last index when it never does
  function leaves(pts, inside) {
    let i = 0;
    while (i < pts.length && inside(pts[i])) i++;
    if (i === 0) return 0;
    if (i === pts.length) return pts.length - 1;
    let lo = 0, hi = 1;
    for (let it = 0; it < 12; it++) { const mid = (lo + hi) / 2; if (inside(lerp2(pts[i - 1], pts[i], mid))) lo = mid; else hi = mid; }
    return i - 1 + (lo + hi) / 2;
  }
  // `pts` between the outlines A and B, the clip radius interpolated by the summary weight a between the disc and the
  // card (no jump when crossing the band); null when the outlines leave nothing to draw
  function routeLine(pts, A, B, a) {
    const reach = (S, line) => {
      const disc = S.r ? leaves(line, p => Math.hypot(p[0] - S.x, p[1] - S.y) < S.r) : null;
      const card = S.card ? leaves(line, p => Math.abs(p[0] - S.x) < S.card.hw && Math.abs(p[1] - S.y) < S.card.hh) : null;
      return disc != null && card != null ? disc * (1 - a) + card * a : disc ?? card ?? 0;
    };
    const u0 = reach(A, pts), u1 = pts.length - 1 - reach(B, [...pts].reverse());
    if (u1 - u0 < 1e-6) return null;
    const at = u => { const i = Math.min(pts.length - 2, Math.floor(u)); return lerp2(pts[i], pts[i + 1], u - i); };
    return [at(u0), ...pts.slice(Math.floor(u0) + 1, Math.ceil(u1)), at(u1)];
  }
  // the "Show all routes" row: there only while some set hides a route; its count is the current set's routes
  function syncRoutesRow(view) {
    const hide = !view.hides, row = $u('routes-row');
    if (row.hidden !== hide) row.hidden = hide;
    $u('routes-n').textContent = num(view.cur.list.length);
  }
  $u('routes-box').onchange = ev => {
    showAll = ev.target.checked;
    const cur = lastView && lastView.cur;
    if (cur) $u('live').textContent = showAll ? T.allRoutesOn(cur.list.length) : T.allRoutesOff(cur.kept.length, cur.list.length);
    draw();
  };
  const lineWidth = c => Math.min(8, 1 + 1.2 * Math.log2(c));   // screen px
  // a filled arrowhead at the end of `pts` (or at its start), its tip 2 px beyond the outline, along the path
  function headAt(pts, atEnd, k, size) {
    const e = atEnd ? pts[pts.length - 1] : pts[0], q = atEnd ? pts[Math.max(0, pts.length - 4)] : pts[Math.min(pts.length - 1, 3)];
    const ang = Math.atan2(e[1] - q[1], e[0] - q[0]), s = size / k, tip = 2 / k;
    arrowAt(e[0] + Math.cos(ang) * (tip - s), e[1] + Math.sin(ang) * (tip - s), ang, s);
  }
  const routeName = key => constellationLabel(key);
  // the words of a route: its ends (upstream first), the counts the Links selector shows, the direction line
  function routeWords(r) {
    const [up, down] = flowEnds(r), reader = r.dir === 1 ? r.target : r.source;
    const title = up != null ? `${routeName(up)} → ${routeName(down)}` : `${routeName(r.source)} — ${routeName(r.target)}`;
    const counts = [...(state.links !== 'lineage' ? [plural(r.rel, T.relationsN)] : []), ...(state.links !== 'relations' ? [plural(r.lin, T.lineageN)] : [])].join(' · ');
    const dir = state.links === 'relations' ? '' : r.dir === 2 ? T.readEach : r.dir ? T.reads(routeName(reader), routeName(r.dir === 1 ? r.source : r.target)) : T.noLineage;
    return { title, counts, dir };
  }
  // draws the routes of the frame (world space, under the cards); fills the hit list of the last screen frame
  function drawRoutes(view, k, a, plans, onScreen) {
    const { rm, sp } = view;
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    view.sets.forEach(set => {
      if (set.alpha < 0.01) return;
      const list = sp ? set.list.filter(r => r.source === sp || r.target === sp) : set.shown;
      ctx.globalAlpha = (traj ? DIM : 1) * set.alpha;
      list.forEach(r => {
        const line = routeLine(pathOf(r).pts, outlineOf(r.source, rm, plans), outlineOf(r.target, rm, plans), a);
        if (!line) return;
        const w = lineWidth(r.c) + (sp ? 0.5 : 0);
        ctx.strokeStyle = sp ? C.hl : C.route; ctx.fillStyle = sp ? C.hl : C.arrow; ctx.lineWidth = w / k;
        ctx.beginPath(); line.forEach(([x, y], j) => (j ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke();
        const size = Math.max(9, 1.8 * w);
        if (r.dir === 1 || r.dir === 2) headAt(line, true, k, size);
        if (r.dir === -1 || r.dir === 2) headAt(line, false, k, size);
        if (onScreen && set === view.cur) routeHits.push({ r, w, pts: line.map(([x, y]) => [x * k + t.x, y * k + t.y]) });
      });
    });
    ctx.globalAlpha = 1; ctx.lineCap = 'butt'; ctx.lineJoin = 'miter';
  }
  // the drawn route nearest to a screen point, within max(6, half its width + 3) px
  function routeAt(px, py) {
    let best = null, bestD = Infinity;
    routeHits.forEach(({ r, w, pts }) => {
      for (let j = 1; j < pts.length; j++) {
        const d = segmentDist(px, py, pts[j - 1], pts[j]);
        if (d <= Math.max(6, w / 2 + 3) && d < bestD) { best = r; bestD = d; }
      }
    });
    return best;
  }
  // the tooltip of a route: ends, counts, direction, and the systems a bundled route sums
  function routeTip(r) {
    const { title, counts, dir } = routeWords(r);
    const from = r.from ? r.from.slice(0, TIP_DOMAINS).map(f => `${esc(labelOf(DOM[f.key]))} ${num(f.c)}`).join(' · ')
      + (r.from.length > TIP_DOMAINS ? ` · + ${num(r.from.length - TIP_DOMAINS)}` : '') : '';
    return `<b>${esc(title)}</b><div class="m">${counts}</div>` + (dir ? `<div class="m">${esc(dir)}</div>` : '')
      + (from ? `<div class="m">${T.routeFrom}${L.colon}${from}</div>` : '');
  }

  // Draws the view on the screen, or on `target` (an exported image) at `scale` device pixels per CSS
  // pixel, over the same W x H area. Keep it synchronous: it swaps the closure's ctx until it returns.
  function draw(target = screenCtx, scale = window.devicePixelRatio || 1) {
    const onScreen = target === screenCtx;
    ctx = target;
    try { paint(onScreen, scale); } finally { ctx = screenCtx; }
  }
  function paint(onScreen, scale) {
    const t0 = performance.now(), k = t.k, W = stage.clientWidth, H = stage.clientHeight;
    perf.routes = 0;   // per frame: the model and the paths this draw finds
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
    if (onScreen) { summaryHits = []; cardInfo = []; routeHits = []; }
    // the crossfade (D-065): stars, links, names and halos at 1 - a, the summary cards at a, one rule for the universe
    const a = summaryWeight(k), cardsOn = a >= 0.02, starsOn = a <= 0.98, routesOn = k < 0.6 || cardsOn;
    fade = 1 - a;
    const view = routeView(a, routesOn), grp = view.rm.grp;
    if (onScreen) {
      $u('export').disabled = !visible.length;
      const groups = plural(constellations.length, state.by === 'layers' ? T.layersN : L.domainsN);
      // tables and links are counted over what passes the filters: a fold changes what is drawn, not what is counted
      const entities = folding() ? [plural(entitiesIn(visible), T.entitiesN)] : [];
      const hidden = routesOn && !(showAll && !traj) && view.cur.shown.length < view.cur.list.length
        ? [T.routesOf(view.cur.shown.length, view.cur.list.length)] : [];
      // one line: while the routes entry shows (some routes are hidden) it replaces the links count, so it stays in view;
      // the title always holds the whole line
      const links = plural(linkCount, T.linksN), counts = [plural(pass.length, L.tables), ...entities];
      $u('meta').textContent = [...counts, ...(hidden.length ? [] : [links]), groups, ...hidden].join(' · ');
      $u('meta').title = [...counts, links, groups, ...hidden].join(' · ');
      lastView = view; syncRoutesRow(view);
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
    const tdom = traj ? new Set(trajMembers().filter(i => P[i]).map(i => G.of(N[i]))) : null;
    // spotlight (D-071): the constellation under the pointer or focus, its route neighbours; the others dim
    const ctxAlpha = d => (tdom && !tdom.has(d.k)) || (view.near && !view.near.has(d.k)) ? DIM_CTX : 1;
    const plans = cardsOn ? cardPlans(grp, view.rm) : new Map();

    ctx.save(); ctx.translate(t.x, t.y); ctx.scale(k, k);
    constellations.forEach(d => {
      if (byLayers) { drawDomainBands(d, k, ctxAlpha(d)); return; }
      if (!starsOn) return;
      ctx.globalAlpha = ctxAlpha(d) * fade;
      const c = isSystem(d.k) ? C.muted : CONTRAST.edge(DOM[d.k].color, C.bg), g = ctx.createRadialGradient(d.x, d.y, 0, d.x, d.y, d.r);   // 3:1 (D-042)
      g.addColorStop(0, c + '26'); g.addColorStop(1, c + '0a');
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(d.x, d.y, d.r, 0, 7); ctx.fill();
      ctx.strokeStyle = c + '66'; ctx.lineWidth = 1.5 / k; ctx.stroke();
    });
    if (k >= 0.6 && starsOn) constellations.forEach(d => { ctx.globalAlpha = ctxAlpha(d) * fade; drawBandMarkers(d, k); });
    ctx.globalAlpha = traj ? DIM : 1;

    if (routesOn) drawRoutes(view, k, a, plans, onScreen);   // from afar: the strongest routes, edge to edge, arrowed
    // table-level links: hidden from afar (the routes say it), faint at mid zoom, full when close;
    // hover dimming is off in the trajectory mode, whose dimming replaces it
    const near = hover != null && !traj ? new Set([hover, ...edges.filter(e => e.includes(hover)).flat()]) : null;
    ctx.lineWidth = 1 / k; ctx.globalAlpha = (traj ? DIM : 1) * fade;
    if (starsOn) edges.forEach(([a, b]) => {
      const hl = near && (a === hover || b === hover), cross = G.of(N[a]) !== G.of(N[b]);
      if (!hl && (k < 0.35 || (k < 0.6 && cross))) return;
      ctx.strokeStyle = hl ? C.hl : cross ? C.cross : C.edge;
      ctx.beginPath(); ctx.moveTo(P[a].x, P[a].y); ctx.lineTo(P[b].x, P[b].y); ctx.stroke();
    });

    const cards = state.detail !== 'names' && k > 0.35;
    const labels = [];
    const drawTable = n => {
      const p = P[n.i], b = B[n.i]; if (!inView(p.x, p.y + b.oy, b.w, b.h)) return;
      const col = KIND[n.kind].color, mark = n.i === hover || n.i === found, side = sideOf(n.i);
      ctx.globalAlpha = (traj ? (side ? 1 : DIM) : near && !near.has(n.i) ? 0.2 : 1) * fade * ctxAlpha({ k: G.of(n) });
      if (cards) drawCard(n, p, b, col, mark, side, k);
      else { drawStar(n, p, col, mark, side, k); labels.push(n); }
    };
    if (starsOn && traj) {  // trajectory tables after its edges, so arrows never cover them
      visible.forEach(n => { if (!sideOf(n.i)) drawTable(n); });
      ctx.globalAlpha = fade;
      drawTrajectoryEdges(k);
      visible.forEach(n => { if (sideOf(n.i)) drawTable(n); });
    } else if (starsOn) visible.forEach(drawTable);
    if (traj && cardsOn) { ctx.globalAlpha = a; drawTrajectoryArrows(k, a, plans, view.rm); }   // aggregated, under the cards
    ctx.globalAlpha = 1;
    ctx.restore();

    // screen-space text: constellation names first, then band names (layer mode), then table names by
    // importance, skipping any that would overlap; then the summary cards, last, over what fades
    const taken = [], hits = [];
    const free = (x, y, w, h) => !taken.some(r => x < r[0] + r[2] && x + w > r[0] && y < r[1] + r[3] && y + h > r[1]);
    ctx.textAlign = 'center';
    if (starsOn) constellations.forEach(d => {
      const [sx, rim] = screen(d.x, d.y - d.r), neutral = isSystem(d.k), fs = neutral ? 12 : Math.max(13, Math.min(20, 10 + d.r * k / 25));
      const sy = rim - (byLayers ? NAME_LIFT : 0);
      const name = constellationLabel(d.k);
      ctx.globalAlpha = ctxAlpha(d) * fade;
      // a domain name in its colour, readable on the page (D-037); a layer name in the text colour
      ctx.font = `600 ${fs}px ${FONT}`; ctx.fillStyle = byLayers || neutral ? C.text : CONTRAST.ink(DOM[d.k].color, C.bg);
      ctx.fillText(name, sx, sy - 22);
      const w = Math.max(ctx.measureText(name).width, 80) + 8;
      ctx.font = `12px ${FONT}`; ctx.fillStyle = C.muted;
      ctx.fillText(plural(d.n, L.tables), sx, sy - 8);
      // composition by type, readable before any single star is
      let bx = sx - 40;
      d.mix.forEach(([kind, c]) => { const bw = 80 * c / d.n; ctx.fillStyle = CONTRAST.edge(KIND[kind].color, C.bg); ctx.fillRect(bx, sy - 4, bw, 4); bx += bw; });
      taken.push([sx - w / 2, sy - 22 - fs, w, fs + 22]);
      if (a < 0.5) hits.push({ d, x: sx - w / 2, y: sy - 22 - fs, w, h: fs + 22 });
    });
    if (byLayers && k >= 0.6 && starsOn) constellations.forEach(d => { ctx.globalAlpha = ctxAlpha(d) * fade; drawBandNames(d, screen, free, taken, k); });
    ctx.globalAlpha = 1;
    if (onScreen) drawn = [];  // an exported image leaves the names of the screen as they are
    if (!cards && starsOn) drawNames(orderLabels(labels, k), screen, free, taken, k);
    if (cardsOn) { plans.forEach((p, key) => drawSummary(p.d, ctxAlpha(p.d), a, onScreen, hits, p)); ctx.globalAlpha = 1; }
    ctx.textAlign = 'left';
    if (!onScreen) return;
    labelHits = hits;
    perf.draw = performance.now() - t0;
  }
  // the view as shown (filters, zoom, detail level, search mark, trajectory) as a PNG at 2 x the screen
  // resolution; hover is pointer state, like the tooltip, so it is left out. null when nothing is drawn.
  function image() {
    if (!visible.length) return null;
    const W = stage.clientWidth, H = stage.clientHeight, s = EXPORT.scale(W, H), c = document.createElement('canvas');
    c.width = Math.round(W * s); c.height = Math.round(H * s);
    const pointer = hover, lit = spot;
    hover = null; spot = null;
    try { draw(c.getContext('2d'), s); } finally { hover = pointer; spot = lit; }
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
  const constellationLabel = key => (key === GROUP ? T.systemsH : labelOf(state.by === 'layers' ? LAYER[key] : DOM[key]));
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
  function drawDomainBands(d, k, alpha) {
    const spans = bandSpans(d);
    ctx.globalAlpha = alpha * fade;   // the tints and the outline fade with the stars, the arcs (the legend of the card) stay
    ctx.save(); ctx.beginPath(); ctx.arc(d.x, d.y, d.r, 0, 7); ctx.clip();
    spans.forEach(b => { ctx.fillStyle = TINT(DOM[b.key].color); ctx.fillRect(d.x + b.s0, d.y - d.r, b.s1 - b.s0, 2 * d.r); });
    ctx.restore();
    ctx.strokeStyle = C.muted + '66'; ctx.lineWidth = 1.5 / k;
    ctx.beginPath(); ctx.arc(d.x, d.y, d.r, 0, 7); ctx.stroke();
    const gap = ARC_GAP / 2 / k / d.r;
    ctx.globalAlpha = alpha;
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

  // names by priority: in the trajectory mode its tables first (start, then by distance), then the hovered one, then by score
  function orderLabels(labels, k) {
    labels.sort((a, b) => TIER_ORDER[tierOf(a)] - TIER_ORDER[tierOf(b)] || labelScore(b) - labelScore(a));
    const hov = hover != null && P[hover] ? [N[hover]] : [];
    const fit = k < 0.6 ? fitNames() : null;
    const ordinary = fit ? labels.filter(n => fit.has(n.i)) : labels;
    if (!traj) return [...hov, ...ordinary];
    const inT = labels.filter(n => sideOf(n.i)).sort((a, b) => trajDist(a.i) - trajDist(b.i));
    return [...inT, ...hov, ...ordinary.filter(n => !sideOf(n.i))];
  }
  // The main tables of each constellation (M8.3, D-058, D-066): its drawn core tables with the most relations (ties:
  // links, name, id), at most MAIN_MAX; empty map when no core table is drawn. Listed on a summary card; the first
  // FIT_NAMES are the names offered from afar. Cached per layout.
  function mainTables() {
    if (mainCache && mainCache.of === visible && mainCache.by === state.by) return mainCache.main;
    const main = new Map();
    visible.filter(n => KIND[n.kind].role === 'core').forEach(n => {
      const g = grouping().of(n); if (!main.has(g)) main.set(g, []); main.get(g).push(n);
    });
    main.forEach((list, g) => main.set(g, list
      .sort((a, b) => RELDEG[b.i] - RELDEG[a.i] || DEG[b.i] - DEG[a.i] || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0) || (a.id < b.id ? -1 : 1))
      .slice(0, MAIN_MAX)));
    mainCache = { of: visible, by: state.by, main };
    return main;
  }
  // From afar, when core tables are drawn, the ordinary names offered are, per constellation, its FIT_NAMES main
  // tables; null when no core table is drawn (names as at any zoom).
  function fitNames() {
    const main = mainTables();
    return main.size ? new Set([...main.values()].flatMap(list => list.slice(0, FIT_NAMES).map(n => n.i))) : null;
  }

  // ---------------------------------------------------------------- summary cards (M8.3, D-065, D-066)
  // At overview scale a constellation is drawn as a summary card instead of its stars. One rule on the drawn size of
  // the reference star (the median radius of the drawn stars of the highest tier present): s = k * refR screen px;
  // the weight of the cards is 0 from S_STARS up, 1 from S_CARDS down, linear in log k between.
  const referenceRadius = () => {
    const tier = d3.min(visible, n => TIER_ORDER[tierOf(n)]);
    return d3.median(visible.filter(n => TIER_ORDER[tierOf(n)] === tier), starR) || 1;
  };
  const kStars = () => S_STARS / refR, kCards = () => S_CARDS / refR;
  const summaryWeight = k => Math.max(0, Math.min(1, Math.log(S_STARS / (k * refR)) / Math.log(S_STARS / S_CARDS)));
  const tablesLive = () => summaryWeight(t.k) < 0.5;   // the pointer acts on stars below half a card, on cards above
  // what a card says (over the tables that pass the filters): rows by layer (domain mode) or by domain (layer
  // mode), each with its kinds in the order of the Types list, the entities drawn while the fold is on, the main tables
  function summaryOf(d, all) {
    const byLayers = state.by === 'layers', pos = key => (byLayers ? DOM_POS[key] : LAYER[key].rank);
    const rows = [...d3.group(all, n => (byLayers ? n.domain : n.layer))]
      .map(([key, ns]) => ({ key, n: ns.length, kinds: inKindOrder(d3.rollup(ns, v => v.length, n => n.kind)) }))
      .sort((a, b) => pos(a.key) - pos(b.key));
    return { rows, entities: folding() ? entitiesIn(all) : null,
             main: (mainTables().get(d.k) || []).map(n => n.i) };
  }
  const rowLabel = (key, group) => labelOf(group || state.by === 'layers' ? DOM[key] : LAYER[key]);
  const countLine = (n, entities) => [plural(n, L.tables), ...(entities == null ? [] : [plural(entities, T.entitiesN)])].join(' · ');
  // the text alternative of the canvas: one heading per constellation, in the flow order of the drawing, with the
  // same counts, rows and main tables as the cards (never cut by room); names and labels through textContent
  function renderSummaryText() {
    const el = (tag, text) => { const e = document.createElement(tag); e.textContent = text; return e; };
    const head = $u('summary-h'); head.textContent = T.summaryH;
    const sys = new Set(constellations.filter(d => isSystem(d.k)).map(d => d.k));
    const ordered = constellations.filter(d => !sys.has(d.k)).sort((a, b) => a.rank - b.rank || (constellationLabel(a.k) < constellationLabel(b.k) ? -1 : 1));
    // every route of a constellation (not thinned by the density), heaviest first, with its counts and direction words
    const routesBlock = (key, list) => {
      const mine = list.filter(r => r.source === key || r.target === key).sort((a, b) => b.c - a.c || (a.target + a.source < b.target + b.source ? -1 : 1));
      if (!mine.length) return [];
      const items = mine.map(r => {
        const { counts, dir } = routeWords(r), other = constellationLabel(r.source === key ? r.target : r.source);
        return `${other} (${counts}${dir ? ' — ' + dir : ''})`;
      });
      return [el('p', `${T.routesH}${L.colon}${items.join(' · ')}`)];
    };
    const parts = ordered.flatMap(d => {
      const ul = document.createElement('ul');
      d.sum.rows.forEach(r => ul.append(el('li', `${rowLabel(r.key)}${L.colon}${plural(r.n, L.tables)} — `
        + r.kinds.map(([kind, c]) => `${labelOf(KIND[kind])} ${num(c)}`).join(', '))));
      const main = d.sum.main.length ? [el('p', `${T.mainH}${L.colon}${d.sum.main.map(i => N[i].name).join(', ')}`)] : [];
      return [el('h3', constellationLabel(d.k)), el('p', countLine(d.n, d.sum.entities)), ul, ...main, ...routesBlock(d.k, routes)];
    });
    if (sys.size) {   // the source systems, one block whatever the scale or the arrangement
      const members = inGridOrder(constellations.filter(d => sys.has(d.k)));
      const ul = document.createElement('ul');
      members.forEach(d => ul.append(el('li', `${labelOf(DOM[d.k])}${L.colon}${plural(d.n, L.tables)} — `
        + inKindOrder(d.mix).map(([kind, c]) => `${labelOf(KIND[kind])} ${num(c)}`).join(', '))));
      parts.push(el('h3', T.systemsH), el('p', `${plural(members.length, T.systemsN)} · ${plural(d3.sum(members, d => d.n), L.tables)}`), ul,
        ...routesBlock(GROUP, bundleRoutes(routes, sys).bundled));
    }
    $u('summary').replaceChildren(head, ...(parts.length ? parts : [el('p', L.empty)]));
  }
  // the trajectory seen from afar: per constellation the members it holds (start excluded) and whether it holds
  // the start, and the lineage edges between constellations grouped by pair and side; cached per trajectory and layout
  function trajSummary() {
    if (trajCache && trajCache.traj === traj && trajCache.runs === layoutRuns) return trajCache;
    const G = grouping(), per = new Map(), pairs = new Map();
    const slot = k => { if (!per.has(k)) per.set(k, { up: 0, down: 0, start: false }); return per.get(k); };
    traj.up.forEach((_, i) => { if (PASS[i] && i !== traj.start) slot(G.of(N[i])).up++; });
    traj.down.forEach((_, i) => { if (PASS[i] && i !== traj.start) slot(G.of(N[i])).down++; });
    if (PASS[traj.start]) slot(G.of(N[traj.start])).start = true;
    traj.edges.forEach(([c, p, dir]) => {
      if (!PASS[c] || !PASS[p] || G.of(N[c]) === G.of(N[p])) return;
      const from = G.of(N[p]), to = G.of(N[c]), key = [from, to, dir].join('|');
      if (!pairs.has(key)) pairs.set(key, { from, to, dir, c: 0 });
      pairs.get(key).c++;
    });
    trajCache = { traj, runs: layoutRuns, per, pairs: [...pairs.values()] };
    return trajCache;
  }

  // What a card of w x h screen px shows, decided top-down from its size alone, so it is deterministic (D-066): the
  // name always (ellipsised), then the count line, the trajectory line, the rows (all, or as many as fit minus one and
  // a "+ N" row), then the main tables (with their heading when three fit under it). Fonts are set on ctx to measure.
  const COARSE = window.matchMedia('(pointer: coarse)').matches;
  const CARD = { PAD: 5, HEAD: 15, LINE: 12, GAP: 3, ROW: COARSE ? 18 : 14, BAR: 6, BAR_MIN: 24, SEG_MIN: 2, DOT: 7 };
  const HOVER_TINT = 'rgba(31,41,51,.06)';
  const textW = (text, font) => { ctx.font = font; return ctx.measureText(text).width; };
  function ellipsis(text, width, font) {
    if (width < 8) return '';
    if (textW(text, font) <= width) return text;
    let s = text;
    while (s.length > 1 && textW(s + '…', font) > width) s = s.slice(0, -1);
    return s + '…';
  }
  // the corner radius in screen px: 0.4 r, but at most max(28 px, 0.24 r), so that the corners stay within 1.18 r of the
  // centre (the collision radius of the layout) at every zoom and the text can be inset from them
  const cardRadius = w => Math.min(0.4 * w / 1.8, Math.max(28, 0.24 * w / 1.8));
  // the trajectory line of a card, from the longest wording to the shortest that fits `inner` px: the counts in words,
  // then with arrow marks; a direction without table is left out unless both are empty
  function trajLine(mark, inner) {
    if (!mark || !mark.text) return '';
    const dir = trajOpts.direction, parts = [['up', mark.up], ['down', mark.down]].filter(([k]) => dir === 'both' || k === dir);
    const kept = parts.filter(([, n]) => n > 0), use = kept.length ? kept : parts;
    const words = use.map(([k, n]) => (k === 'up' ? L.countUp : L.countDown)(num(n))).join(' · ');
    const marks = use.map(([k, n]) => `${k === 'up' ? '↑' : '↓'} ${num(n)}`).join(' · ');
    return [words, marks].find(c => textW(c, `600 11px ${FONT}`) <= inner) || ellipsis(marks, inner, `600 11px ${FONT}`);
  }
  // The height is the content's, at most the width (the card stays centred on its constellation): `plan.h`.
  const GROUP_SHORT = 60;
  function planCard(d, w, mark, cap = w) {
    const h = cap, { PAD, HEAD, LINE, GAP, ROW } = CARD, byLayers = state.by === 'layers', rows = d.sum.rows;
    const padX = Math.max(PAD, Math.round(0.34 * cardRadius(w))), inner = w - 2 * padX;
    const plan = { padX, h, name: '', size: 13, count: '', traj: '', rows: [], more: '', mainY: 0, heading: false, names: [] };
    if (w < 24) return plan;
    // the group card's heading is the short word under GROUP_SHORT px of inner width (a card of 24 px or more is always
    // named, M8.3); any name is cut with an ellipsis when it does not fit
    const name = d.group && inner < GROUP_SHORT ? T.systemsShort : constellationLabel(d.k);
    plan.size = textW(name, `600 13px ${FONT}`) <= inner ? 13 : 11;
    plan.name = ellipsis(name, inner, `600 ${plan.size}px ${FONT}`);
    let y = PAD + HEAD;
    if (y + LINE > h - 2) return plan;
    // a card never says "0 entities" (the text summary does)
    const line = d.group ? `${plural(d.members.length, T.systemsN)} · ${plural(d.n, L.tables)}` : d.sum.entities ? countLine(d.n, d.sum.entities) : '';
    plan.count = [line, plural(d.n, L.tables), num(d.n)].find(c => c && textW(c, `11px ${FONT}`) <= inner) || '';
    y += LINE;
    if (mark && mark.text && y + LINE <= h - PAD) { plan.traj = trajLine(mark, inner); y += LINE; }
    y += GAP;
    plan.rowsY = y;
    const fits = Math.floor((h - PAD - y) / ROW);
    if (inner >= 56 && fits >= 1) {
      const shown = fits < rows.length ? Math.max(0, fits - 1) : rows.length, dot = byLayers && !d.group ? CARD.DOT + 4 : 0;
      const counts = rows.map(r => num(r.n)), countW = d3.max(counts, c => textW(c, `11px ${FONT}`));
      const wide = dot + d3.max(rows.slice(0, shown), r => textW(rowLabel(r.key, d.group), `11px ${FONT}`));
      // the label column is as wide as the widest label; the bar takes the rest when that leaves BAR_MIN, else the bar goes
      // and the label takes up to what is left
      const bar = wide <= inner - countW - 8 - CARD.BAR_MIN;
      plan.rows = rows.slice(0, shown).map(r => ({ r, label: '' }));
      plan.labelW = bar ? wide : Math.min(wide, inner - countW - 4); plan.countW = countW; plan.bar = bar; plan.dot = dot;
      plan.rows.forEach(row => { row.label = ellipsis(rowLabel(row.r.key, d.group), plan.labelW - dot, `11px ${FONT}`); });
      if (shown < rows.length) {
        const more = rows.length - shown;
        plan.more = ellipsis('+ ' + plural(more, d.group ? T.systemsN : byLayers ? L.domainsN : T.layersN), inner, `11px ${FONT}`);
      }
      y += (shown + (plan.more ? 1 : 0)) * ROW;
    }
    const names = d.sum.main, left = h - PAD - y;
    if (names.length && !plan.more && left >= 3 + LINE) {
      const withHead = Math.floor((left - 3 - LINE) / LINE), without = Math.floor((left - 3) / LINE);
      // at least two names (one when there is only one, under its heading), else no block: a lone bullet reads as a stray row
      const need = Math.min(2, names.length);
      plan.mainY = y; plan.heading = withHead >= need && withHead >= 1;
      if (plan.heading) plan.names = names.slice(0, withHead);
      else if (names.length >= 2 && without >= 2) plan.names = names.slice(0, without);
      if (plan.names.length) y += 3 + (plan.heading ? LINE : 0) + plan.names.length * LINE;
    }
    plan.h = Math.min(cap, Math.ceil(y + PAD));
    return plan;
  }
  // the plan and screen square of every card of the frame: the constellations, with the group card in place of its members
  function cardPlans(grp, rm) {
    const plans = new Map(), owners = grp ? [...constellations.filter(d => !rm.members.has(d.k)), grp] : constellations;
    owners.forEach(d => {
      const sq = cardRect(d);
      plans.set(d.k, { d, sq, plan: planCard(d, sq.w, cardMark(d.k), d.group ? d.gridH * t.k : sq.w) });
    });
    return plans;
  }
  const cardRect = (d, k = t.k) => { const half = 0.9 * d.r * k; return { x: d.x * k + t.x - half, y: d.y * k + t.y - half, w: 2 * half }; };
  // the kind bar of a row: segments in Types order, each in its mark colour (3:1), at least SEG_MIN px, a 1 px gap
  // between two wide ones; the widest row of the card fills the bar
  function drawBar(row, x, y, len) {
    const total = row.kinds.reduce((s, [, c]) => s + c, 0), ws = row.kinds.map(([, c]) => Math.max(CARD.SEG_MIN, len * c / total));
    const extra = d3.sum(ws) - len, widest = ws.indexOf(d3.max(ws));
    if (extra > 0 && ws[widest] - extra >= CARD.SEG_MIN) ws[widest] -= extra;   // a row shorter than its kinds' minimum overshoots
    let bx = x;
    row.kinds.forEach(([kind], j) => {
      const gap = ws[j] >= 4 && ws[j + 1] >= 4 ? 1 : 0;
      ctx.fillStyle = CONTRAST.edge(KIND[kind].color, C.bg); ctx.fillRect(bx, y, ws[j] - gap, CARD.BAR); bx += ws[j];
    });
  }
  // a colour dot of a card, outlined in `CONTRAST.edge` when its colour falls short of 3:1 (D-042)
  function cardDot(col, cx, cy, r) {
    const edge = CONTRAST.edge(col, C.bg);
    ctx.fillStyle = col; ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.fill();
    if (edge !== col) { ctx.strokeStyle = edge; ctx.lineWidth = 1; ctx.stroke(); }
  }
  // a summary card at alpha `alpha`, in screen space, over the constellation's disc; fills `cardInfo` and, while the
  // cards are live (weight >= 0.5), `summaryHits` and the header rectangle `hits` that drags the constellation
  function drawSummary(d, alpha, a, onScreen, hits, planned) {
    const { PAD, HEAD, LINE, ROW } = CARD, sq = planned.sq, w = sq.w, neutral = state.by === 'layers' || d.group || isSystem(d.k);
    const mark = cardMark(d.k), hot = onScreen && hoverCard === d.k, radius = cardRadius(w);
    const plan = planned.plan, px = plan.padX, inner = w - 2 * px, border = neutral ? C.muted : CONTRAST.edge(DOM[d.k].color, C.bg);
    const x = sq.x, h = plan.h, y = sq.y + (w - h) / 2;
    const path = (grow = 0) => { ctx.beginPath(); ctx.roundRect(x - grow, y - grow, w + 2 * grow, h + 2 * grow, radius + grow); };
    // the surface turns opaque twice as fast as the content, so that the stars' names never show through the text
    ctx.globalAlpha = alpha * Math.min(1, 2 * a); ctx.textAlign = 'left';
    ctx.fillStyle = C.card; path(); ctx.fill();
    ctx.strokeStyle = mark ? C.text : border; ctx.lineWidth = mark || hot ? 2 : 1.5; path(); ctx.stroke();
    if (mark && mark.start) { ctx.strokeStyle = C.text; ctx.lineWidth = 1.5; path(4.5); ctx.stroke(); }
    ctx.save(); path(); ctx.clip(); ctx.globalAlpha = alpha * a;
    ctx.fillStyle = neutral ? C.text : CONTRAST.ink(DOM[d.k].color, C.bg); ctx.font = `600 ${plan.size}px ${FONT}`;
    ctx.fillText(plan.name, x + px, y + PAD + 11);
    ctx.fillStyle = C.muted; ctx.font = `11px ${FONT}`;
    ctx.fillText(plan.count, x + px, y + PAD + HEAD + 9);
    if (plan.traj) { ctx.fillStyle = C.text; ctx.font = `600 11px ${FONT}`; ctx.fillText(plan.traj, x + px, y + PAD + HEAD + LINE + 9); }
    const maxRow = d3.max(d.sum.rows, r => r.n), live = a >= 0.5, info = { k: d.k, rows: plan.rows.length, names: plan.names.length, heading: plan.heading,
      more: !!plan.more, named: plan.name !== '', count: plan.count, traj: plan.traj,
      barW: plan.bar ? inner - plan.labelW - plan.countW - 8 : 0, x, y, w, h, header: { x: x + px, y: y + PAD, w: inner, h: HEAD + LINE } };
    plan.rows.forEach(({ r, label }, j) => {
      const ry = y + plan.rowsY + j * ROW, rx = x + px;
      if (onScreen && hoverCard === d.k && hoverRow === r.key) { ctx.fillStyle = HOVER_TINT; ctx.beginPath(); ctx.roundRect(rx, ry, inner, ROW, 3); ctx.fill(); }
      if (plan.dot) cardDot(DOM[r.key].color, rx + CARD.DOT / 2, ry + ROW / 2, CARD.DOT / 2);
      ctx.fillStyle = C.text; ctx.font = `11px ${FONT}`; ctx.fillText(label, rx + plan.dot, ry + ROW / 2 + 4);
      ctx.fillStyle = C.muted; ctx.textAlign = 'right'; ctx.fillText(num(r.n), x + w - px, ry + ROW / 2 + 4); ctx.textAlign = 'left';
      if (plan.bar) drawBar(r, rx + plan.labelW + 4, ry + (ROW - CARD.BAR) / 2, (inner - plan.labelW - plan.countW - 8) * r.n / maxRow);
      if (live && onScreen) summaryHits.push({ k: d.k, row: r.key, x: rx, y: ry, w: inner, h: ROW });
    });
    if (plan.more) {
      ctx.fillStyle = C.muted; ctx.font = `11px ${FONT}`; ctx.fillText(plan.more, x + px, y + plan.rowsY + plan.rows.length * ROW + ROW / 2 + 4);
    }
    if (plan.names.length) {
      let my = y + plan.mainY;
      ctx.strokeStyle = C.muted + '66'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x + px, my + 0.5); ctx.lineTo(x + w - px, my + 0.5); ctx.stroke();
      my += 3;
      if (plan.heading) { ctx.fillStyle = C.muted; ctx.font = `600 11px ${FONT}`; ctx.fillText(ellipsis(T.mainH, inner, `600 11px ${FONT}`), x + px, my + 9); my += LINE; }
      plan.names.forEach((i, j) => {
        const ny = my + j * LINE;
        cardDot(KIND[N[i].kind].color, x + px + 2.5, ny + 6, 2.5);
        ctx.fillStyle = C.text; ctx.font = `11px ${FONT}`; ctx.fillText(ellipsis(N[i].name, inner - 11, `11px ${FONT}`), x + px + 11, ny + 9);
      });
      info.main = { x: x + px, y: y + plan.mainY, w: inner, h: 3 + (plan.heading ? LINE : 0) + plan.names.length * LINE };
    }
    ctx.restore();
    if (onScreen) cardInfo.push(info);
    if (live) hits.push({ d, card: true, x: x + px, y: y + PAD, w: inner, h: HEAD + LINE });
  }
  // the trajectory marks of a card (null outside the mode, or for a constellation holding none of it)
  function cardMark(key) {
    if (!traj) return null;
    const per = trajSummary().per, g = key === GROUP ? systemsGroup() : null;
    const m = g ? g.members.reduce((sum, d) => { const q = per.get(d.k); return q ? { up: sum.up + q.up, down: sum.down + q.down, start: sum.start || q.start } : sum; }, { up: 0, down: 0, start: false })
      : per.get(key);
    if (!m || (g && !m.up && !m.down && !m.start)) return null;
    return { start: m.start, up: m.up, down: m.down, text: m.up + m.down ? trajectoryCounts(trajOpts.direction, m.up, m.down) : '' };
  }
  // the aggregated lineage arrows between cards (one per ordered pair and side), under the cards, in world space; they
  // follow the same paths as the routes (the group card stands for its members), and two arrows of one pair are
  // set side by side so that they never coincide
  function drawTrajectoryArrows(k, a, plans, rm) {
    const into = key => (rm.grp && rm.members.has(key) ? GROUP : key), merged = new Map();
    trajSummary().pairs.forEach(p => {
      const from = into(p.from), to = into(p.to), key = [from, to, p.dir].join('|');
      if (from === to) return;
      if (!merged.has(key)) merged.set(key, { from, to, dir: p.dir, c: 0 });
      merged.get(key).c += p.c;
    });
    const sides = d3.group([...merged.values()], q => pairKey(q.from, q.to));
    sides.forEach(list => list.forEach((q, j) => {
      const { from, to, dir, c } = q, base = pathBetween(from, to).pts, [x0, y0] = base[0], [x1, y1] = base[base.length - 1];
      const len = Math.hypot(x1 - x0, y1 - y0) || 1, sign = from < to ? 1 : -1, off = (j - (list.length - 1) / 2) * 9 / k * sign;
      const moved = list.length > 1 ? base.map(([x, y]) => [x - (y1 - y0) / len * off, y + (x1 - x0) / len * off]) : base;
      const line = routeLine(moved, outlineOf(from, rm, plans), outlineOf(to, rm, plans), a);
      if (!line) return;
      ctx.strokeStyle = C[dir]; ctx.fillStyle = C[dir]; ctx.lineWidth = (1 + Math.log2(c)) * 1.2 / k;
      ctx.lineJoin = 'round'; ctx.setLineDash(dir === 'up' ? [6 / k, 4 / k] : []);
      ctx.beginPath(); line.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke(); ctx.setLineDash([]);
      headAt(line, true, k, 9);
      if (c < 2) return;
      const [mx, my] = line[Math.floor(line.length / 2)];
      ctx.font = `600 ${11 / k}px ${FONT}`; ctx.textAlign = 'center'; ctx.lineWidth = 3 / k; ctx.strokeStyle = C.card;
      ctx.strokeText(String(c), mx, my); ctx.fillStyle = C.text;
      ctx.fillText(String(c), mx, my); ctx.textAlign = 'left';
    }));
  }

  // Table names below their stars, in one or two lines (nameLines), each over a light backdrop, skipping any
  // that would overlap a name already drawn or a domain name. An ordinary name is also skipped when it would
  // cover another star or leave its domain's circle (semantic zoom: names are 11 px whatever the zoom, so
  // from afar only the room around a star decides); trajectory and hovered names always compete.
  function drawNames(labels, screen, free, taken, k) {
    const at = new Map(labels.map(n => [n.i, screen(P[n.i].x, P[n.i].y)]));
    const rad = n => Math.max(starR(n) * k, 2.5), rMax = Math.max(R_MAX * k, 2.5);
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
    let shown = 0;
    const names = [];
    for (const n of labels) {
      if (shown >= 400) break;
      const side = sideOf(n.i);
      const strong = side ? trajDist(n.i) <= 1 : labelScore(n) >= 10 || n.i === hover;
      ctx.font = `${strong ? 600 : 400} 11px ${FONT}`;
      const [sx, sy] = at.get(n.i), lines = nameLines(n.name);
      const w = d3.max(lines, s => ctx.measureText(s).width) + 6, h = LINE_H * lines.length, x = sx - w / 2, y = sy + rad(n) + 2;
      if (!free(x, y, w, h)) continue;
      if (!side && n.i !== hover && (coversStar(x, y, w, h) || !inDisc(n, x, y, w, h))) continue;
      taken.push([x, y, w, h]); shown++; names.push(n.id);
      ctx.globalAlpha = (traj && !side ? DIM : 1) * fade;
      ctx.fillStyle = 'rgba(245,246,248,.85)'; ctx.fillRect(x, y, w, h);
      ctx.fillStyle = strong || side ? C.text : C.muted;
      lines.forEach((s, j) => ctx.fillText(s, sx, y + 11 + LINE_H * j));
    }
    ctx.globalAlpha = 1;
    if (ctx === screenCtx) drawn = names;
  }
  // a ring around a star: dashed for upstream, as on the legend
  function ring(p, r, color, width, dashed, k) {
    ctx.strokeStyle = color; ctx.lineWidth = width;
    ctx.setLineDash(dashed ? [5 / k, 3 / k] : []);
    ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, 7); ctx.stroke();
    ctx.setLineDash([]);
  }
  // The badge of an entity holding `count` tables (D-063): a dark disc with a white outline, centred on
  // (cx, cy), 7 screen px with the count (99+ above 99); a card keeps a 4 px dot from afar (a star gets a ring)
  function drawBadge(cx, cy, count, k) {
    const near = k >= 0.6, rb = (near ? 7 : 4) / k;
    ctx.fillStyle = C.text; ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1.5 / k;
    ctx.beginPath(); ctx.arc(cx, cy, rb, 0, 7); ctx.fill(); ctx.stroke();
    if (!near) return;
    ctx.fillStyle = '#ffffff'; ctx.font = `700 ${9 / k}px ${FONT}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(count > 99 ? '99+' : String(count), cx, cy + 0.5 / k);
    ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
  }
  function drawStar(n, p, col, mark, side, k) {
    const far = k < 0.6, r = Math.max(starR(n), (side ? 3 : 2.5) / k), held = HELD.get(n.i);
    const edge = CONTRAST.edge(col, C.bg);   // a star too light for the page is outlined (D-042)
    ctx.fillStyle = col; ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, 7); ctx.fill();
    ctx.strokeStyle = edge === col ? '#ffffff' : edge; ctx.lineWidth = 1 / k; ctx.stroke();
    // after the rings; from afar a thin dark ring hugging the star (1.5 px gap, 1.25 px wide, tighter than every
    // trajectory ring), so the kind colour still shows; from 0.6 up the numbered badge
    const badge = () => {
      if (!held) return;
      if (far) ring(p, r + 1.5 / k, C.text, 1.25 / k, false, k);
      else drawBadge(p.x + r * Math.SQRT1_2, p.y - r * Math.SQRT1_2, held.length, k);
    };
    if (side === 'start') { ring(p, r + 3 / k, C.text, 1.5 / k, false, k); ring(p, r + 6 / k, C.text, 1.5 / k, false, k); badge(); return; }
    let out = 4 / k;
    if (side) { out = (far ? 3 : 4) / k; ring(p, r + out, C[side], (far ? 1.5 : 2) / k, side === 'up', k); out += 3 / k; }
    if (mark) ring(p, r + out, C.text, 2 / k, false, k);
    badge();
  }
  function drawCard(n, p, b, col, mark, side, k) {
    const x = p.x - b.cw / 2, y = p.y - b.ch / 2, mk = Math.min(k, 1), edge = CONTRAST.edge(col, C.bg);   // D-042
    ctx.fillStyle = C.card; ctx.fillRect(x, y, b.cw, b.ch);
    ctx.strokeStyle = side === 'start' ? C.text : side ? C[side] : mark ? C.text : edge;
    ctx.lineWidth = (side === 'start' ? 3 : side ? 2.5 : mark ? 2.5 : 1) / mk;
    ctx.setLineDash(side === 'up' ? [6 / mk, 3 / mk] : []);
    ctx.strokeRect(x, y, b.cw, b.ch);
    ctx.setLineDash([]);
    if (side === 'start' || (side && mark)) {  // outer rectangle 3 px outside
      const o = 3 / k + ctx.lineWidth / 2;
      ctx.strokeStyle = C.text; ctx.lineWidth = 1.5 / mk; ctx.strokeRect(x - o, y - o, b.cw + 2 * o, b.ch + 2 * o);
    }
    ctx.fillStyle = col; ctx.fillRect(x, y, b.cw, 16);
    if (edge !== col) { ctx.strokeStyle = edge; ctx.lineWidth = 1 / mk; ctx.strokeRect(x, y, b.cw, 16); }
    if (k > 0.6) {
      ctx.fillStyle = CONTRAST.textOn(col); ctx.font = `600 10px ${FONT}`; ctx.fillText(n.name, x + 5, y + 12);
      ctx.font = `9px ${FONT}`;
      b.shown.forEach((r, j) => {
        ctx.fillStyle = r[2] ? C.text : C.muted; ctx.fillText(r[0], x + 5, y + 28 + j * 11);
        ctx.fillStyle = C.muted; ctx.fillText(r[1], x + b.cw - 5 - ctx.measureText(r[1]).width, y + 28 + j * 11);
      });
      const below = y + 18 + (b.shown.length + (b.more > 0 ? 1 : 0)) * 11;   // where the folded tables start
      if (b.more > 0) { ctx.fillStyle = C.muted; ctx.fillText(`+ ${num(b.more)}`, x + 5, y + 28 + b.shown.length * 11); }
      if (b.folded.length) {
        ctx.strokeStyle = C.muted + '66'; ctx.lineWidth = 1 / mk;
        ctx.beginPath(); ctx.moveTo(x + 4, below + 3); ctx.lineTo(x + b.cw - 4, below + 3); ctx.stroke();
        b.folded.forEach(([name, kind], j) => {
          ctx.fillStyle = C.text; ctx.fillText(name, x + 5, below + 16 + j * 11);
          ctx.fillStyle = C.muted; ctx.fillText(kind, x + b.cw - 5 - ctx.measureText(kind).width, below + 16 + j * 11);
        });
        if (b.heldMore > 0) { ctx.fillStyle = C.muted; ctx.fillText(`+ ${num(b.heldMore)}`, x + 5, below + 16 + b.folded.length * 11); }
      }
    }
    const held = HELD.get(n.i);
    if (held) drawBadge(x + b.cw, y, held.length, k);
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
  const zoom = d3.zoom().scaleExtent(ZOOM_EXTENT).on('zoom', ev => { t = ev.transform; draw(); });
  // mouse only: on touch every finger goes to the zoom, so a pinch starting on a table or a domain name
  // zooms and a one-finger drag pans, as in the detail (a touch drag cannot hand a finger over to a pinch)
  const drag = d3.drag().container(canvas).touchable(false).filter(ev => !ev.button)
    .subject(ev => {
      const n = t.k >= FAR && tablesLive() ? pickAt(...t.invert([ev.x, ev.y])) : null;
      if (n) return { n, x: ev.x, y: ev.y };
      const hit = labelAt(ev.x, ev.y);
      return hit ? { d: hit.d, x: ev.x, y: ev.y } : null;
    })
    .on('start', ev => { ev.subject.moved = false; dragging = true; tip.style.display = 'none'; canvas.style.cursor = 'grabbing'; })
    .on('drag', ev => {
      const dx = ev.dx / t.k, dy = ev.dy / t.k, s = ev.subject;
      s.moved = true;
      if (s.n) { P[s.n.i].x += dx; P[s.n.i].y += dy; }
      else {   // a constellation, or every source system by the group card's header
        const moved = s.d.group ? s.d.members : [s.d], keys = new Set(moved.map(c => c.k));
        moved.forEach(c => { c.x += dx; c.y += dy; });
        visible.forEach(n => { if (keys.has(grouping().of(n))) { P[n.i].x += dx; P[n.i].y += dy; } });
      }
      geomVer++;
      draw();
    })
    .on('end', ev => {
      const s = ev.subject;
      canvas.style.cursor = ''; dragging = false;
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
      tree = d3.quadtree(visible, n => P[n.i].x, n => P[n.i].y);
      geomVer++;
      draw();
    });
  const sel = zoomOn(d3.select(canvas).call(drag), zoom);
  // room kept free at the top of the canvas: the trajectory bar overlays it while the mode is on
  const top = () => traj ? bar.offsetHeight : 0;
  // frame a world-space box, at most at scale kMax, at least at kMin
  function frame(bx0, by0, bx1, by1, animate, kMax = Infinity, kMin = 0) {
    // constellation names sit above the halos at a fixed screen size: keep that strip free at the top
    const NAME = 46, top0 = top(), w = stage.clientWidth, h = stage.clientHeight - top0 - NAME;
    const k = Math.max(kMin, Math.min(kMax, 0.95 * Math.min(w / (bx1 - bx0), h / (by1 - by0))));
    const tr = d3.zoomIdentity.translate(w / 2, top0 + NAME + h / 2).scale(k).translate(-(bx0 + bx1) / 2, -(by0 + by1) / 2);
    (animate ? sel.transition().duration(500) : sel).call(zoom.transform, tr);
  }
  // the whole universe, or the drawn tables of the trajectory while the mode is on
  function fit(animate) {
    const tj = trajMembers().filter(i => P[i]);
    if (tj.length) {
      return frame(d3.min(tj, i => P[i].x - B[i].w / 2), d3.min(tj, i => P[i].y + B[i].oy - B[i].h / 2),
        d3.max(tj, i => P[i].x + B[i].w / 2), d3.max(tj, i => P[i].y + B[i].oy + B[i].h / 2), animate, 2);
    }
    if (!constellations.length) return draw();
    frame(d3.min(constellations, d => d.x - d.r), d3.min(constellations, d => d.y - d.r),
      d3.max(constellations, d => d.x + d.r), d3.max(constellations, d => d.y + d.r), animate);
  }
  function zoomTo(x, y, k) {
    const top0 = top(), w = stage.clientWidth, h = stage.clientHeight - top0;
    sel.transition().duration(600).call(zoom.transform, d3.zoomIdentity.translate(w / 2, top0 + h / 2).scale(k).translate(-x, -y));
  }
  const pick = ev => (tablesLive() ? pickAt(...t.invert(d3.pointer(ev, canvas))) : null);
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
  // the constellation name under a screen point, if any
  const labelAt = (x, y) => labelHits.find(h => x >= h.x && x <= h.x + h.w && y >= h.y && y <= h.y + h.h);
  // the owners of the cards drawn now: the constellations, the group card standing for its members
  const cardOwners = () => { const g = systemsGroup(); return g ? [...constellations.filter(d => !g.members.includes(d)), g] : constellations; };
  // the constellation under the pointer, if any: its summary card while the cards are live, else its disc
  function constellationAt(ev) {
    const [px, py] = d3.pointer(ev, canvas);
    if (!tablesLive()) return cardOwners().find(d => {
      const c = cardRect(d), i = cardInfo.find(q => q.k === d.k), h = i ? i.h : c.w;   // the drawn height, centred on the square
      return px >= c.x && px <= c.x + c.w && py >= c.y + (c.w - h) / 2 && py <= c.y + (c.w + h) / 2;
    });
    const [wx, wy] = t.invert([px, py]);
    return constellations.find(d => Math.hypot(wx - d.x, wy - d.y) < d.r);
  }
  const inRect = (r, x, y) => r && x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h;
  const rowAt = (x, y) => summaryHits.find(r => inRect(r, x, y));
  // frame a constellation (or the band of one of its rows) so that its stars are drawn: never below the stars scale
  function zoomOnRow(row) {
    const inGroup = row.k === GROUP, d = constellations.find(c => c.k === (inGroup ? row.row : row.k));
    const band = !inGroup && d && bandSpans(d).find(b => b.key === row.row);
    if (!d) return;
    const kMin = kStars() * 1.05;
    if (!band) return frame(d.x - d.r, d.y - d.r, d.x + d.r, d.y + d.r, true, Infinity, kMin);
    const half = rimHalf(d, Math.max(band.s0, Math.min(band.s1, 0)));
    frame(d.x + band.s0, d.y - half, d.x + band.s1, d.y + half, true, Infinity, kMin);
  }
  // Layer mode tooltip of a constellation (D-048): its domains in band order (first TIP_DOMAINS, then "+ N"), and the
  // band under the world x `wx`, if any
  function layerTip(d, wx, extra = '') {
    const names = d.bands.slice(0, TIP_DOMAINS).map(b => esc(labelOf(DOM[b.key]))).join(' · ');
    const more = d.bands.length > TIP_DOMAINS ? ` · + ${num(d.bands.length - TIP_DOMAINS)}` : '';
    const band = bandSpans(d).find(b => wx - d.x >= b.s0 && wx - d.x <= b.s1);
    return `<b>${esc(constellationLabel(d.k))}</b><div class="m">${plural(d.n, L.tables)}</div>`
      + `<div class="m">${T.domains}${L.colon}${names}${more}</div>`
      + (band ? `<div class="m">${T.domainOne}${L.colon}${esc(labelOf(DOM[band.key]))} · ${plural(band.n, L.tables)}</div>` : '')
      + extra + `<div class="a">${T.frameC}</div>`;
  }
  // the tooltip block of a table: the tables folded into it (an entity), or where it folds (a table with a parent)
  function foldTip(n) {
    const held = HELD.get(n.i);
    if (held) {
      const lines = held.slice(0, TIP_FOLDED).map(i => `<div>${esc(N[i].name)} <span class="m">· ${esc(labelOf(KIND[N[i].kind]))}</span></div>`);
      const more = held.length > TIP_FOLDED ? `<div class="m">+ ${num(held.length - TIP_FOLDED)}</div>` : '';
      return `<div class="held"><b>${plural(held.length, L.foldedN)}</b>${lines.join('')}${more}</div>`;
    }
    return PARENT[n.i] >= 0 ? `<div class="m">${T.foldsInto}${L.colon}${esc(N[PARENT[n.i]].name)}</div>` : '';
  }
  // The tooltip TIP_GAP px below and right of the pointer; flipped to the left and above where it would leave the stage,
  // and, when one of the four places is clear of `avoid` (the hovered card, in canvas px), taken in that order
  const TIP_GAP = 12;
  function placeTip(ev, avoid) {
    const r = stage.getBoundingClientRect(), c = canvas.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top;
    const w = tip.offsetWidth, h = tip.offsetHeight, g = TIP_GAP;
    const fits = ([l, tp]) => l >= 0 && tp >= 0 && l + w <= r.width && tp + h <= r.height;
    const apart = ([l, tp]) => !avoid || l + w <= avoid.x + c.left - r.left || l >= avoid.x + avoid.w + c.left - r.left
      || tp + h <= avoid.y + c.top - r.top || tp >= avoid.y + avoid.h + c.top - r.top;
    const spots = [[x + g, y + g], [x - g - w, y + g], [x + g, y - g - h], [x - g - w, y - g - h]];
    const [left, top] = spots.find(q => fits(q) && apart(q)) || spots.find(fits) || [Math.max(0, Math.min(x + g, r.width - w)), Math.max(0, Math.min(y + g, r.height - h))];
    tip.style.left = left + 'px'; tip.style.top = top + 'px';
  }
  canvas.addEventListener('mousemove', ev => {
    const n = pick(ev), h = n ? n.i : null, over = constellationAt(ev);
    const d = n ? null : over, [px, py] = d3.pointer(ev, canvas);
    const row = d && !tablesLive() ? rowAt(px, py) : null, info = d && !tablesLive() ? cardInfo.find(c => c.k === d.k) : null;
    const card = d && !tablesLive() ? d.k : null, rowKey = row ? row.row : null, sp = over ? over.k : null;
    if (h !== hover || card !== hoverCard || rowKey !== hoverRow || sp !== spot) { hover = h; hoverCard = card; hoverRow = rowKey; spot = sp; draw(); }
    const header = info && inRect(info.header, px, py), hit = labelAt(px, py);
    canvas.style.cursor = row ? 'pointer' : header ? 'move' : (n && t.k >= FAR) || hit ? 'grab' : '';
    const route = !n && !d ? routeAt(px, py) : null;
    if (!n && !d && !route) { tip.style.display = 'none'; return; }
    if (route) {
      tip.innerHTML = routeTip(route);
    } else if (n) {
      const dbl = detailIds.has(n.id) ? T.openDetail : T.zoomIn, start = traj && n.i === traj.start;
      tip.innerHTML = tableTip(DATA, n) + (traj ? trajectoryTip(traj, n.i) : '') + tableDesc(n) +
        `<div class="a">${t.k < FAR ? frameText() : start ? dbl : T.clickTraj + ' · ' + dbl}</div>` + foldTip(n);
    } else if (d.group) {
      // the group card: its counts and the click action; over a row, that system
      const sys = row && constellations.find(c => c.k === row.row);
      tip.innerHTML = sys
        ? `<b>${esc(labelOf(DOM[sys.k]))}</b><div class="m">${plural(sys.n, L.tables)}</div><div class="m">${T.layers}${L.colon}${esc(bandLabels(sys))}</div>`
          + `<div class="a">${T.rowZoom(esc(labelOf(DOM[sys.k])))}</div>`
        : `<b>${T.systemsH}</b><div class="m">${plural(d.members.length, T.systemsN)} · ${plural(d.n, L.tables)}</div><div class="a">${T.groupTip}</div>`;
    } else {
      // over the main tables of a card: they are named in the tooltip; over a row: the click action
      const main = info && info.main && inRect(info.main, px, py)
        ? `<div class="m">${T.mainH}${L.colon}${d.sum.main.map(i => esc(N[i].name)).join(', ')}</div>` : '';
      const click = row ? `<div class="a">${T.rowZoom(esc(rowLabel(row.row)))}</div>` : '';
      if (state.by === 'layers') {
        tip.innerHTML = layerTip(d, t.invert([px, py])[0], main) + click;
      } else {
        const dd = DOM[d.k];
        tip.innerHTML = `<b>${esc(labelOf(dd))}</b><div class="m">${plural(d.n, L.tables)}${dd.owner ? ` · ${T.owner}${L.colon}${esc(dd.owner)}` : ''}</div>`
          + `<div class="m">${T.layers}${L.colon}${esc(bandLabels(d))}</div>${main}<div class="a">${T.frame}</div>${click}`;
      }
    }
    tip.style.display = 'block';
    placeTip(ev, d && !tablesLive() ? info : null);
  });
  canvas.addEventListener('mouseleave', () => {
    tip.style.display = 'none';
    if (hover != null || hoverCard != null || spot != null) { hover = null; hoverCard = null; hoverRow = null; spot = null; draw(); }
  });
  // from afar stars are packed too tightly to aim at: double-click frames the constellation until zoomed in
  const FAR = 0.5;
  const frameText = () => (state.by === 'layers' ? T.frameC : T.frame);
  canvas.addEventListener('dblclick', ev => {
    const n = t.k >= FAR ? pick(ev) : null;
    if (n) {
      if (detailIds.has(n.id)) { tip.style.display = 'none'; openInDetail(n.id); return; }
      found = n.i; zoomTo(P[n.i].x, P[n.i].y, Math.max(t.k * 2.5, 1.5));
      return;
    }
    const d = constellationAt(ev);
    // a card always lands on stars, even where the disc is wider than the screen
    const span = d && d.group ? Math.max(d.gridW, d.gridH) : d && 2 * d.r;
    if (d) zoomTo(d.x, d.y, Math.max(0.92 * Math.min(stage.clientWidth, stage.clientHeight - top()) / (span + 60), kStars() * 1.05));
  });
  // single click: a table enters the trajectory mode, or moves it; a row of a summary card frames its band; only the
  // empty background (no table, domain label, summary card or domain halo, at any zoom) leaves it.
  // d3-drag and d3-zoom swallow the click that ends a drag or a pan.
  canvas.addEventListener('click', ev => {
    if (ev.detail > 1) return;   // the second click of a double-click
    const n = t.k >= FAR ? pick(ev) : null;
    if (n) { enterTrajectory(n.i); return; }
    const row = tablesLive() ? null : rowAt(...d3.pointer(ev, canvas));
    if (row) { zoomOnRow(row); return; }
    if (traj && !labelAt(...d3.pointer(ev, canvas)) && !constellationAt(ev)) leaveTrajectory(false);
  });

  // ---------------------------------------------------------------- trajectory mode
  const countsText = (u, d) => trajectoryCounts(trajOpts.direction, u, d);
  function enterTrajectory(i) {
    const { up, down } = trajectory(DATA.lineage, i, trajOpts.direction, trajOpts.depth);
    const folded = unfoldedKey();   // the members the fold hid before: they are drawn while the mode is on
    traj = { start: i, up, down, edges: trajectoryEdges(DATA.lineage, i, up, down), brought: 0 };
    bar.hidden = false;   // shown before reveal, so a relayout frames the trajectory below the bar
    traj.brought = reveal(trajMembers());
    if (!traj.brought && unfoldedKey() !== folded) relayoutAnchored(i);   // unfold its members (or fold the last ones back)
    const n = N[i], summary = renderBar();
    live.textContent = `${T.trajOf} ${n.name}${L.colon}${summary}.` + (traj.brought ? ` ${plural(traj.brought, T.brought)}.` : '');
    draw();
  }
  function leaveTrajectory(restoreFocus) {
    if (!traj) return;
    const inBar = bar.contains(document.activeElement), unfolded = unfoldedKey() !== '', start = traj.start;
    traj = null; bar.hidden = true; $u('tj-counts').open = false;
    $u('fit').removeAttribute('title');
    live.textContent = T.closed;
    if (restoreFocus && inBar) ($u('traj').disabled ? $u('q') : $u('traj')).focus();
    if (unfolded) relayoutAnchored(start);   // the members drawn by the mode fold back, the start staying put
    else draw();
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
    const hidden = trajMembers().filter(j => !PASS[j]).length;   // hidden by the filters; a folded member is drawn
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
  // a relayout that folds or unfolds trajectory members: no refit, the camera keeps its scale and the table
  // `i` (the one clicked) stays at the same screen point, so it stays under the pointer
  function relayoutAnchored(i) {
    const was = P[i] && t.apply([P[i].x, P[i].y]);
    found = null; hover = null; spot = null; layout(); if (traj) renderBar();
    if (!was || !P[i]) return fit(false), draw();
    sel.call(zoom.transform, d3.zoomIdentity.translate(was[0] - t.k * P[i].x, was[1] - t.k * P[i].y).scale(t.k));
    draw();
  }
  function relayout() { found = null; hover = null; spot = null; layout(); if (traj) renderBar(); fit(false); draw(); }
  let size = '';
  new ResizeObserver(() => {
    const s = stage.clientWidth + 'x' + stage.clientHeight;
    if (stage.clientWidth && s !== size) { size = s; resize(); fit(false); }
  }).observe(stage);
  layout(); resize(); fit(false);

  // the screen rectangle reserved by a drawn table (its card, or its star and name), in CSS px from the
  // canvas's top left corner; null when not drawn
  function place(id) {
    const n = N.find(m => m.id === id), p = n && P[n.i], b = n && B[n.i];
    return p ? { x: (p.x - b.w / 2) * t.k + t.x, y: (p.y + b.oy - b.h / 2) * t.k + t.y, w: b.w * t.k, h: b.h * t.k } : null;
  }
  // the placement in world coordinates (the grouping; tables at their point P, with their reserved box;
  // constellations with their bands) and the time of the last layout: read-only, for the browser tests
  function geometry() {
    return { by: state.by, fold: folding(), layoutMs: perf.layout, passing: pass.length, linkCount,
      folded: N.filter(n => FOLDNOW[n.i]).map(n => n.id),
      tables: visible.map(n => ({ id: n.id, domain: n.domain, layer: n.layer, x: P[n.i].x, y: P[n.i].y,
                                  w: B[n.i].w, h: B[n.i].h, oy: B[n.i].oy, r: R[n.i],
                                  held: (HELD.get(n.i) || []).map(i => N[i].id) })),
      edges: edges.map(([a, b]) => [N[a].id, N[b].id]),
      routes: routeGeometry(), outlines: outlineGeometry(),
      constellations: constellations.map(d => ({ key: d.k, x: d.x, y: d.y, r: d.r, n: d.n, mix: d.mix,
                                   bands: d.bands.map(b => ({ key: b.key, n: b.n, x0: d.x + b.x0, x1: d.x + b.x1 })) })),
      summary: summaryGeometry(), systems: systemsGeometry() };
  }
  // the routes of the current set as the page computed them (D-071): ends (keys, GROUP for the bundled), counts, direction,
  // whether the frame draws it, whether its path clears every other constellation, and its path clipped at the outlines
  // of its ends (world points), for the tests
  function routeGeometry() {
    const a = summaryWeight(t.k), view = routeView(a, t.k < 0.6 || a >= 0.02), rm = view.rm, plans = a >= 0.02 ? cardPlans(rm.grp, rm) : new Map();
    return view.cur.list.map(r => ({ a: r.source, b: r.target, rel: r.rel, lin: r.lin, c: r.c, dir: r.dir, bundled: !!r.bundled,
      drawn: view.sp ? r.source === view.sp || r.target === view.sp : view.cur.shown.includes(r), clear: pathOf(r).clear,
      pts: routeLine(pathOf(r).pts, outlineOf(r.source, rm, plans), outlineOf(r.target, rm, plans), a) || [] }));
  }
  // the outline each drawn constellation has now: its disc below half weight, its card rectangle (world px) above;
  // the group card lists its members
  function outlineGeometry() {
    const a = summaryWeight(t.k), rm = routeModel();
    if (a < 0.5) return constellations.map(d => ({ k: d.k, disc: [d.x, d.y, d.r] }));
    const rect = ({ d, sq, plan }) => [d.x - sq.w / 2 / t.k, d.y - plan.h / 2 / t.k, sq.w / t.k, plan.h / t.k];
    return [...cardPlans(rm.grp, rm).values()].map(p => ({ k: p.d.k, rect: rect(p), ...(p.d.group ? { members: p.d.members.map(m => m.k) } : {}) }));
  }
  const systemsGeometry = () => ({ keys: [...SYS], placed: constellations.some(d => isSystem(d.k)),
    grouped: !!systemsGroup(), order: [...gridOrder.keys()], gridGap: GRID_GAP, flowX: FLOW_X_BUSINESS });
  // the summary cards as the page computed them: the rule's numbers, per card (the group card standing for its source
  // systems) its world rectangle, counts, rows, main tables (ids)
  function summaryGeometry() {
    const cards = cardOwners().map(d => ({ key: d.k, x: d.x, y: d.y, w: 1.8 * d.r, h: d.group ? d.gridH : 1.8 * d.r, r: d.r, n: d.n,
      entities: d.sum.entities, rows: d.sum.rows.map(r => ({ key: r.key, n: r.n, kinds: r.kinds })),
      main: d.sum.main.map(i => N[i].id) }));
    return { weight: summaryWeight(t.k), refR, kStars: kStars(), kCards: kCards(), cards };
  }
  // what the last screen frame drew (screen px), for the click, room and trajectory tests: the rows (hit rectangles),
  // per card its lines, the trajectory marks per constellation and the aggregated arrows (kept apart from geometry(),
  // which a trajectory never changes)
  function summaryDrawn() {
    const tj = traj ? trajSummary() : null;
    return { rows: summaryHits.map(r => ({ ...r })), cards: cardInfo.map(c => ({ ...c })),
      marks: tj ? Object.fromEntries([...tj.per].map(([k, m]) => [k, { ...m }])) : {}, arrows: tj ? tj.pairs.map(q => ({ ...q })) : [] };
  }

  // the d3 zoom transform; camera({x, y, k}) moves it first, through the zoom (the browser tests frame a domain)
  function camera(to) {
    if (to) sel.call(zoom.transform, d3.zoomIdentity.translate(to.x, to.y).scale(to.k));
    return { x: t.x, y: t.y, k: t.k };
  }

  // image is for the browser tests' pixel comparison; the page uses it through #u-export.
  // camera, place and geometry are for the tests too: closing the flow leaves the camera as it was.
  // Reset layout and an import call relayout: they close the entity a search opened
  return { shown: () => { resize(); }, relayout: () => { opened = null; relayout(); }, trajectoryState, image, camera, place, geometry, summaryHits: summaryDrawn, perf: () => ({ ...perf }), drawnNames: () => [...drawn] };
}
