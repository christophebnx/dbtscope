// Detail view: entity-relationship diagram with columns, laid out by Graphviz (Viz.js).
// Started the first time its tab is shown; the returned handle lets the universe view open a table here.
function startDetail(DATA, LAYOUT, EXPORT, FOLD) {
  let tStart = performance.now();   // the first layout is timed from here (state().layoutMs)
  const $d = id => document.getElementById('d-' + id);
  const T = {
    en: { all: 'All groups', focus: 'Focus on a table…', d1: 'direct links', d2: '2 levels', d3: '3 levels', clear: 'Show all',
          cols: 'All columns', q: 'Highlight…', focused: 'Focused: ', rels: ['relation', 'relations'],
          foreign: 'dashed: other group',
          hGroup: 'Group', hDepth: 'Around the focused table', hCols: 'Columns',
          pngTitle: 'Save the visible diagram as a PNG image (high resolution)',
          svgTitle: 'Save the visible diagram as an SVG image (vector, opens in any browser)',
          hint: 'Wheel or pinch: zoom · drag the background to pan · drag a table to move it · click: highlight links · double-click: focus',
          touchHint: 'Pinch: zoom · drag: pan · tap a table: highlight its links',
          foldTitle: n => `Draw each descriptive table as a last row of its entity when more than ${n} tables are drawn. Double-click a table to see its folded tables.`,
          heavy: n => `${plural(n, L.tables)}${L.colon}the drawing will be hard to read`,
          hintFold: ' · a last row "+ N": double-click the table to draw them',
          hintFoldTouch: ' · a last row "+ N": focus the table to draw them',
          live: (n, total, folded) => `${num(n)} of ${plural(total, L.tables)} drawn, ${plural(folded, L.foldedN)} as rows`,
          liveFull: 'All tables drawn' },
    fr: { all: 'Tous les groupes', focus: 'Cibler une table…', d1: 'liens directs', d2: '2 niveaux', d3: '3 niveaux', clear: 'Tout afficher',
          cols: 'Toutes les colonnes', q: 'Surligner…', focused: 'Ciblé\u00a0: ', rels: ['relation', 'relations'],
          foreign: 'pointillé\u00a0: autre groupe',
          hGroup: 'Groupe', hDepth: 'Autour de la table ciblée', hCols: 'Colonnes',
          pngTitle: 'Enregistrer le schéma visible en image PNG (haute résolution)',
          svgTitle: 'Enregistrer le schéma visible en image SVG (vectorielle, s\'ouvre dans tout navigateur)',
          hint: 'Molette ou pincement\u00a0: zoom · glisser le fond\u00a0: déplacer la vue · glisser une table\u00a0: la déplacer · '
              + 'clic\u00a0: surligner ses liens · double-clic\u00a0: cibler',
          touchHint: 'Pincement\u00a0: zoom · glisser\u00a0: déplacer la vue · toucher une table\u00a0: surligner ses liens',
          foldTitle: n => `Dessiner chaque table descriptive comme une dernière ligne de son entité au-delà de ${n} tables. Double-cliquer une table pour voir ses tables repliées.`,
          heavy: n => `${plural(n, L.tables)}${L.colon}le schéma sera difficile à lire`,
          hintFold: ' · une dernière ligne «\u00a0+ N\u00a0»\u00a0: double-cliquer la table pour les dessiner',
          hintFoldTouch: ' · une dernière ligne «\u00a0+ N\u00a0»\u00a0: cibler la table pour les dessiner',
          live: (n, total, folded) => `${num(n)} tables dessinées sur ${num(total)}, ${plural(folded, L.foldedN)} en lignes`,
          liveFull: 'Toutes les tables sont dessinées' },
  }[PAGE.lang];
  const KIND = Object.fromEntries(DATA.kinds.map(k => [k.key, k]));
  const byId = new Map(DATA.entities.map(e => [e.id, e]));
  const neighbours = new Map(DATA.entities.map(e => [e.id, new Set()]));
  DATA.relations.forEach(r => { neighbours.get(r.child).add(r.parent); neighbours.get(r.parent).add(r.child); });
  const GROUPS = [...new Set(DATA.entities.map(e => e.group))].filter(g => g).sort();

  // the skeleton (D-069): above SKELETON_MIN tables to draw, each descriptive table with its parent drawn
  // becomes the last row of its entity. A row and the meta line list at most FOLD_KINDS kinds, the control
  // KIND_LIST, a tooltip TIP_FOLDED folded tables (both in common.js, shared with the universe)
  const SKELETON_MIN = 60, FOLD_KINDS = 2;
  const ROLE = id => KIND[byId.get(id).kind].role;
  const PASSAGES = DATA.kinds.some(k => k.role === 'connector');   // the focus walk needs a connector kind (D-070)
  const DETAIL_FOLDABLE = DATA.entities.some(e => e.parent != null);
  const CHILDREN = new Map();   // parent id -> the ids of the tables that fold into it, from the payload's `parent` (D-068)
  DATA.entities.forEach(e => { if (e.parent != null) CHILDREN.set(e.parent, [...(CHILDREN.get(e.parent) || []), e.id]); });
  let foldOn = DETAIL_FOLDABLE && FOLD.on();
  const state = { group: '', kinds: new Set(DATA.kinds.map(k => k.key)), allColumns: false, focus: null, depth: 1 };
  const box = $d('graph');
  let zv = null, renderSeq = 0;
  let skeleton = false, scopeFoldable = false, last = {}, stale = false, wasSkeleton = false;   // what the last render drew (state(), the view key)

  // --- group scope ----------------------------------------------------------
  // A group shows its own tables plus the other-group parents its tables point to.
  let scope = new Set(byId.keys());
  function computeScope() {
    scope = new Set(DATA.entities.filter(e => !state.group || e.group === state.group).map(e => e.id));
    if (state.group) DATA.relations.forEach(r => { if (byId.get(r.child).group === state.group) scope.add(r.parent); });
  }
  const isForeign = e => state.group && e.group !== state.group;
  const titleOf = e => isForeign(e) ? `${e.group} · ${e.name}` : e.name;

  // --- controls -------------------------------------------------------------
  $d('focus').placeholder = T.focus;
  fillSelect($d('depth'), [T.d1, T.d2, T.d3].map((t, i) => [String(i + 1), t]));
  $d('clear').textContent = T.clear;
  $d('cols').textContent = T.cols;
  $d('fit').textContent = L.fit;
  $d('q').placeholder = T.q;
  // on touch a drag on a table pans (tables move with the mouse only): a hint of its own
  const COARSE = matchMedia('(pointer: coarse)').matches;
  const foldVisible = () => !$d('fold').hidden;
  const hintText = () => (COARSE ? T.touchHint : T.hint) + (foldVisible() && foldOn ? (COARSE ? T.hintFoldTouch : T.hintFold) : '');
  $d('hint').textContent = hintText();
  $d('fold-t').textContent = L.fold;
  $d('fold').querySelector('label').title = T.foldTitle(SKELETON_MIN);
  $d('fold-on').checked = foldOn;
  $d('h-group').textContent = T.hGroup; $d('h-depth').textContent = T.hDepth;
  $d('h-cols').textContent = T.hCols; $d('h-kinds').textContent = L.kinds;

  const groupSel = $d('group');
  if (DATA.grouped && GROUPS.length > 1) {
    fillSelect(groupSel, [['', T.all], ...GROUPS.map(g => [g, g])]);
    groupSel.onchange = () => {
      state.group = groupSel.value;
      computeScope();
      if (state.focus && !scope.has(state.focus)) state.focus = null;
      refreshControls();
      render();
    };
    // every group at once is too much for one Graphviz drawing: open on the largest one
    const sizes = d3.rollup(DATA.entities, v => v.length, e => e.group);
    state.group = GROUPS.reduce((a, b) => (sizes.get(b) > sizes.get(a) ? b : a));
    groupSel.value = state.group;
    computeScope();
  } else { groupSel.style.display = 'none'; $d('h-group').style.display = 'none'; }

  const typesEl = $d('types');
  const focusInput = $d('focus');
  function findEntity(v) {
    const s = v.trim().toLowerCase();
    return DATA.entities.find(e => scope.has(e.id) && (titleOf(e).toLowerCase() === s || e.name.toLowerCase() === s));
  }
  function submitFocus() { const e = findEntity(focusInput.value); if (e && e.id !== state.focus) setFocus(e.id); }
  focusInput.addEventListener('change', submitFocus);
  focusInput.addEventListener('keydown', ev => { if (ev.key === 'Enter') submitFocus(); });
  $d('depth').onchange = ev => { state.depth = +ev.target.value; if (state.focus) render(); };
  $d('clear').onclick = () => setFocus(null);
  // the fold choice is shared with the universe (D-069): a change there redraws here when the tab is shown, else on shown()
  function followFold(on) {
    foldOn = DETAIL_FOLDABLE && on; $d('fold-on').checked = foldOn;
    $d('hint').textContent = hintText();
    if (document.getElementById('tab-detail').classList.contains('on')) render(); else stale = true;
  }
  $d('fold-on').onchange = ev => { FOLD.set(ev.target.checked, followFold); followFold(ev.target.checked); };
  FOLD.listen(followFold);
  $d('cols').onclick = ev => { state.allColumns = !state.allColumns; ev.target.classList.toggle('on', state.allColumns); render(); };
  // refitting a hidden tab would compute a zero zoom, so wait until it is shown again
  const refit = () => zv && zv.fit();
  $d('fit').onclick = refit;
  window.addEventListener('resize', refit);
  sidePanel('d', refit);
  const pngBtn = $d('export-png'), svgBtn = $d('export-svg');
  $d('export-h').textContent = L.exportImage;
  pngBtn.textContent = L.png; pngBtn.title = T.pngTitle;
  svgBtn.textContent = L.svg; svgBtn.title = T.svgTitle;
  // enabled only while a diagram is drawn and zoomed
  function canExport(on) { pngBtn.disabled = svgBtn.disabled = !on; }
  pngBtn.onclick = () => EXPORT.save('detail', 'png', () => pngImage(box, zv, EXPORT), pngBtn);
  svgBtn.onclick = () => EXPORT.save('detail', 'svg', () => svgFile(box, zv), svgBtn);

  // type checkboxes and the focus autocomplete follow the selected group
  function refreshControls() {
    const inScope = DATA.entities.filter(e => scope.has(e.id));
    const shown = DATA.kinds.map(k => [k, inScope.filter(e => e.kind === k.key).length]).filter(([, n]) => n);
    typesEl.replaceChildren(...shown.map(([k, n]) => filterRow(
      { label: k.label, color: k.color, count: n, checked: state.kinds.has(k.key) },
      on => { on ? state.kinds.add(k.key) : state.kinds.delete(k.key); render(); })));
    $d('tables').innerHTML = inScope.map(e => `<option value="${esc(titleOf(e))}">`).join('');
    focusInput.value = state.focus ? titleOf(byId.get(state.focus)) : '';
    refreshFold();
  }

  // the fold control exists while it can act: more than SKELETON_MIN tables in the scope, one with its parent there
  function refreshFold() {
    const held = DATA.entities.filter(e => scope.has(e.id) && e.parent != null && scope.has(e.parent));
    scopeFoldable = held.length > 0;
    $d('fold').hidden = !(scope.size > SKELETON_MIN && scopeFoldable);
    $d('fold-kinds').textContent = foldKindsText(DATA.kinds.filter(k => k.role === 'descriptive' && held.some(e => e.kind === k.key)).map(labelOf));
    $d('fold-n').textContent = num(held.length);
    $d('hint').textContent = hintText();
  }

  function setFocus(id) {
    state.focus = id;
    focusInput.value = id ? titleOf(byId.get(id)) : '';
    render();
  }

  // --- graph ----------------------------------------------------------------
  // The tables to draw: the scope, or the focus and what lies within state.depth steps of it. With a connector kind
  // (D-070) a connector the walk reaches is a passage: the tables on its other side that are not descriptive come at
  // the same level, so from a hub the direct links are its satellites, its links and the hubs across them.
  function visibleIds() {
    let ids = new Set(scope);
    if (state.focus) {
      ids = new Set([state.focus]);
      let frontier = [state.focus];
      const add = (n, next) => { ids.add(n); next.push(n); };
      for (let d = 0; d < state.depth; d++) {
        const next = [];
        frontier.forEach(id => neighbours.get(id).forEach(n => {
          if (!scope.has(n) || ids.has(n)) return;
          add(n, next);
          if (PASSAGES && ROLE(n) === 'connector') {
            neighbours.get(n).forEach(m => { if (scope.has(m) && !ids.has(m) && ROLE(m) !== 'descriptive') add(m, next); });
          }
        }));
        frontier = next;
      }
    }
    if (state.focus) {   // the focus draws its folded tables in full, related or not, and its own parent (D-070)
      const parent = byId.get(state.focus).parent;
      (CHILDREN.get(state.focus) || []).concat(parent != null ? [parent] : []).forEach(id => { if (scope.has(id)) ids.add(id); });
    }
    return new Set([...ids].filter(id => id === state.focus || state.kinds.has(byId.get(id).kind)));
  }

  // ids by table name, then id: the one order of folded tables and of the skeleton's walk
  const byName = (a, b) => (byId.get(a).name < byId.get(b).name ? -1 : byId.get(a).name > byId.get(b).name ? 1 : a < b ? -1 : a > b ? 1 : 0);
  // The tables of `ids` that fold into a parent that is drawn too: Map(parent id -> its folded entities, in name order).
  // The focus and the focus's own folded tables are never folded (D-069).
  function foldedOf(ids) {
    const out = new Map();
    DATA.entities.forEach(e => {
      if (!ids.has(e.id) || e.parent == null || !ids.has(e.parent) || e.id === state.focus || e.parent === state.focus) return;
      if (!out.has(e.parent)) out.set(e.parent, []);
      out.get(e.parent).push(e);
    });
    out.forEach(list => list.sort((a, b) => byName(a.id, b.id)));
    return out;
  }
  // `Label n` pairs of a list of entities, in payload kind order: the first FOLD_KINDS, then ", + N" other kinds
  const kindPairs = list => DATA.kinds.map(k => [k, list.filter(e => e.kind === k.key).length]).filter(([, n]) => n);
  const kindsText = pairs => pairs.slice(0, FOLD_KINDS).map(([k, n]) => `${labelOf(k)} ${num(n)}`).join(', ')
    + (pairs.length > FOLD_KINDS ? `, + ${num(pairs.length - FOLD_KINDS)}` : '');
  // the last row of an entity: "+ 3 folded tables · Satellite", or with several kinds "· Satellite 3, PIT 1"
  function foldText(list) {
    const pairs = kindPairs(list);
    return `+ ${plural(list.length, L.foldedN)} · ${pairs.length === 1 ? labelOf(pairs[0][0]) : kindsText(pairs)}`;
  }
  // the tooltip text of the folded tables: a title, then the lines of `foldedLines`
  const foldTip = list => [`${plural(list.length, L.foldedN)}${L.colon.trimEnd()}`,
    ...foldedLines(list.map(e => [e.name, labelOf(KIND[e.kind])]))].join('\n');

  // `folded`: parent id -> its folded entities, drawn as the parent's last row (skeleton only)
  function nodeDot(e, pos, folded) {
    const k = KIND[e.kind], head = esc(CONTRAST.textOn(k.color)), grey = esc(CONTRAST.ink(THEME.muted, k.bg));
    // names on the kind colour and grey text on its tint reach AA whatever the colour (D-037);
    // the table border and the header's outline reach 3:1 on the page (D-042)
    // trailing spaces keep bold names (under-measured by Viz.js) clear of the type column
    // Graphviz rejects an empty <font>: a column without data_type gets an empty cell
    const row = (name, type) => `<tr><td align="left">${name}&#160;&#160;&#160;</td><td align="left">${type ? `<font color="${grey}">${dotText(type)}</font>` : ''}</td></tr>`;
    const keys = e.columns.filter(c => c[2]), rest = e.columns.filter(c => !c[2]);
    let rows = keys.map(([c, t]) => row(`<b>${dotText(c)}</b>`, t)).join('');
    if (state.allColumns) rows += rest.map(([c, t]) => row(dotText(c), t)).join('');
    else if (rest.length) rows += `<tr><td colspan="2" align="left"><font color="${grey}"><i>+ ${plural(rest.length, L.columns)}</i></font></td></tr>`;
    const held = folded && folded.get(e.id);
    if (held) rows += `<HR/><tr><td colspan="2" align="left"><font color="${grey}">${dotText(foldText(held))}</font></td></tr>`;
    const border = e.id === state.focus ? 4 : 1;
    const style = isForeign(e) ? ' style="dashed"' : '';
    const tip = [e.group, e.name].filter(Boolean).join(' · ') + (held ? '\n\n' + foldTip(held) : '') + (e.description ? '\n\n' + e.description : '');
    const pin = pos ? ` pos="${pos[0]},${pos[1]}!"` : '';
    const id = dotStr(e.id);
    return `"${id}" [id="${id}"${pin} tooltip="${dotStr(tip)}" label=<<table border="${border}" cellborder="0" cellspacing="0" cellpadding="5"${style} color="${esc(CONTRAST.edge(k.color, THEME.bg))}" bgcolor="${esc(k.bg)}">` +
      `<tr><td colspan="2" bgcolor="${esc(k.color)}"${dotEdge(k.color)}><font color="${head}" point-size="16"><b>${dotText(titleOf(e))}</b></font></td></tr>${rows}</table>>];`;
  }

  const relsAmong = ids => DATA.relations.filter(r => ids.has(r.child) && ids.has(r.parent));
  const NODE_ATTRS = 'node [shape=plain fontname="Arial" fontsize=14];';   // Viz.js sizes boxes with built-in Helvetica/Arial metrics; any other font overflows them
  const EDGE_ATTRS = 'edge [color="#8a8f98" penwidth=1.4 arrowsize=0.8 dir=back arrowtail=crow';
  const edgeDot = r => `"${dotStr(r.parent)}" -> "${dotStr(r.child)}" [tooltip="${dotStr(`${byId.get(r.child).name}.${r.column} → ${byId.get(r.parent).name}`)}"`;

  // positions: table id -> [x, y] in Graphviz points, every table pinned (for neato); none for dot's own layout
  function buildDot(ids, positions, folded) {
    const rels = relsAmong(ids);
    const out = ['digraph G {', 'rankdir=LR; nodesep=0.35; ranksep=1.4; bgcolor="transparent";',
      // neato reads pinned positions in inches unless told they are points
      positions ? 'splines=true; overlap=true; inputscale=72;' : '',
      NODE_ATTRS, EDGE_ATTRS + '];'];
    DATA.entities.filter(e => ids.has(e.id)).forEach(e => out.push(nodeDot(e, positions && positions.get(e.id), folded)));
    // Tables nothing else references (links, satellites, facts) all land in the last column; dozens
    // of them make one endless column, so spread them over 3, as Graphviz's `unflatten -l 3` would.
    const parents = new Set(rels.map(r => r.parent));
    const sinks = [...new Set(rels.map(r => r.child))].filter(id => !parents.has(id));
    const column = new Map(sinks.length > 12 ? sinks.map((id, i) => [id, 1 + i % 3]) : []);
    // parent -> child with dir=back puts referenced tables on the left, referencing ones on the right
    rels.forEach(r => {
      const minlen = column.has(r.child) ? ` minlen=${column.get(r.child)}` : '';
      out.push(`${edgeDot(r)}${minlen}];`);
    });
    out.push('}');
    return { dot: out.join('\n'), relCount: rels.length };
  }

  // --- skeleton shape (D-071) ---------------------------------------------------
  // A skeleton still has dozens of entities in one connected component, which dot lays out as a strip (finding 7 of
  // the brief). The shape was chosen by measurement (D-071, option O2): dot with the rows imposed by us, as flow.js
  // imposes its columns. The tables are ordered (components of the drawn relations, largest first, each breadth-first
  // from its core table with the most relations; isolated tables last), cut into rows of `c` tables with `rank=same`,
  // the rows chained by invisible edges (invisible: Graphviz never emits them, so highlight and export never see them) and the
  // real edges `constraint=false`, which still order the tables inside a row. `c` aims at the area's own aspect.
  const SKEL_NODESEP = 0.3, SKEL_RANKSEP = 0.6;   // inches
  const areaAspect = () => (box.clientWidth && box.clientHeight ? Math.min(3, Math.max(0.5, box.clientWidth / box.clientHeight)) : 1.5);
  // a table's size in points, estimated from its text (never measured, as the universe does)
  function estimate(e, folded) {
    const keys = state.allColumns ? e.columns : e.columns.filter(c => c[2]), held = folded.has(e.id);
    const rows = keys.length + (!state.allColumns && e.columns.length > keys.length ? 1 : 0) + (held ? 1 : 0);
    const w = Math.max(titleOf(e).length * 9.4 + 20, ...keys.map(c => c[0].length * 8.4 + (c[1] || '').length * 7.4 + 34), held ? 190 : 0);
    return [w, 31 + 21 * rows];
  }
  function skeletonOrder(ids, rels) {
    const near = new Map([...ids].map(id => [id, new Set()]));
    rels.forEach(r => { near.get(r.child).add(r.parent); near.get(r.parent).add(r.child); });
    const walk = root => {   // breadth-first, neighbours by name then id
      const order = [root], got = new Set(order);
      for (let i = 0; i < order.length; i++) [...near.get(order[i])].sort(byName).forEach(n => { if (!got.has(n)) { got.add(n); order.push(n); } });
      return order;
    };
    const seen = new Set(), parts = [];
    [...ids].sort(byName).forEach(id => {
      if (seen.has(id)) return;
      const members = walk(id);
      members.forEach(m => seen.add(m));
      const weight = m => (ROLE(m) === 'core' ? 1e6 : 0) + near.get(m).size;
      parts.push(walk(members.slice().sort((a, b) => weight(b) - weight(a) || byName(a, b))[0]));
    });
    return parts.sort((a, b) => b.length - a.length).flat();
  }
  const mean = list => list.reduce((x, y) => x + y, 0) / (list.length || 1);
  // the first DOT sent to Graphviz goes to `cur.dot` (state())
  async function skeletonSvg(ids, folded, cur) {
    const rels = relsAmong(ids), order = skeletonOrder(ids, rels);
    const sizes = order.map(id => estimate(byId.get(id), folded));
    const rowH = mean(sizes.map(s => s[1])) + SKEL_RANKSEP * 72, cellW = mean(sizes.map(s => s[0])) + SKEL_NODESEP * 72;
    const perRow = Math.max(1, Math.round(Math.sqrt(order.length * areaAspect() * rowH / cellW)));
    const rows = [];
    for (let i = 0; i < order.length; i += perRow) rows.push(order.slice(i, i + perRow));
    const q = id => `"${dotStr(id)}"`;
    const out = ['digraph G {', `rankdir=TB; newrank=true; nodesep=${SKEL_NODESEP}; ranksep=${SKEL_RANKSEP}; bgcolor="transparent";`,
      NODE_ATTRS, EDGE_ATTRS + ' constraint=false];'];
    order.forEach(id => out.push(nodeDot(byId.get(id), null, folded)));
    rows.forEach(r => out.push(`{rank=same; ${r.map(q).join('; ')}}`));
    rows.slice(1).forEach((r, i) => out.push(`${q(rows[i][0])} -> ${q(r[0])} [id="skel-chain-${i}" style=invis constraint=true];`));
    rels.forEach(r => out.push(`${edgeDot(r)}];`));
    out.push('}');
    cur.dot = out.join('\n');
    return GRAPHVIZ.render(cur.dot);
  }

  // --- manual arrangement -----------------------------------------------------
  // Moved tables are saved per drawing (group, focus, columns, types; a skeleton has its own key, D-069). Graphviz's
  // dot lays everything out first; when some tables were moved, neato redraws with every table pinned, moved ones
  // where they were dropped, so links are routed around the new positions.
  const viewKey = () => [state.group, state.focus || '', state.focus ? state.depth : '', state.allColumns ? 'all' : 'keys',
    DATA.kinds.filter(k => state.kinds.has(k.key)).map(k => k.key).join(',')].join('|') + (skeleton ? '|skeleton' : '');

  // centre of each drawn table in Graphviz points (y up), from the polygons Graphviz drew for it
  function centres(svg) {
    const out = new Map();
    svg.querySelectorAll('g.node').forEach(g => {
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      g.querySelectorAll('polygon').forEach(p => p.getAttribute('points').trim().split(/\s+/).forEach(pt => {
        const [x, y] = pt.split(',').map(Number);
        x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
      }));
      if (x0 < Infinity) out.set(g.id, [(x0 + x1) / 2, -(y0 + y1) / 2]);
    });
    return out;
  }

  let justDragged = false;
  function startDrag(ev, g, svg) {
    if (ev.button) return;
    ev.stopPropagation(); ev.preventDefault();  // keep the zoom of the box from panning
    const ctm = g.parentNode.getScreenCTM(), x0 = ev.clientX, y0 = ev.clientY;
    let dx = 0, dy = 0;
    g.style.cursor = 'grabbing';
    const move = e => { dx = (e.clientX - x0) / ctm.a; dy = (e.clientY - y0) / ctm.d; g.setAttribute('transform', `translate(${dx},${dy})`); };
    const up = () => {
      window.removeEventListener('mousemove', move); window.removeEventListener('mouseup', up);
      g.style.cursor = '';
      if (Math.hypot(dx * ctm.a, dy * ctm.d) < 3) { g.removeAttribute('transform'); return; }
      justDragged = true; setTimeout(() => { justDragged = false; });
      const [cx, cy] = centres(svg).get(g.id), pinned = LAYOUT.get('detail', viewKey()) || {};
      pinned[g.id] = [Math.round(cx + dx), Math.round(cy - dy)];
      LAYOUT.set('detail', viewKey(), pinned);
      render(true);
    };
    window.addEventListener('mousemove', move); window.addEventListener('mouseup', up);
  }

  // keepView: redraw without moving the camera (after a drop)
  function render(keepView) {
    canExport(false);
    const t0 = tStart ?? performance.now(); tStart = null;
    const ids = visibleIds(), folded = foldedOf(ids);
    const heavy = ids.size > SKELETON_MIN && scopeFoldable;   // some table of the scope can fold, whatever the kind filters
    skeleton = foldOn && heavy;
    const rows = skeleton ? folded : new Map(), foldedList = [...rows.values()].flat();
    const gone = new Set(foldedList.map(e => e.id)), drawn = skeleton ? new Set([...ids].filter(id => !gone.has(id))) : ids;
    const { dot, relCount } = skeleton ? { dot: null, relCount: relsAmong(drawn).length } : buildDot(drawn, null, rows);
    const meta = skeleton
      ? `${num(ids.size)} / ${plural(scope.size, L.tables)} · ${plural(foldedList.length, L.foldedN)}${foldedList.length ? ` (${kindsText(kindPairs(foldedList))})` : ''} · ${plural(relCount, T.rels)}`
      : `${num(ids.size)} / ${plural(scope.size, L.tables)} · ${plural(relCount, T.rels)}`;
    $d('meta').textContent = meta + (state.group ? ` · ${T.foreign}` : '');
    const warn = !foldOn && heavy ? T.heavy(ids.size) : '';
    $d('fold-warn').textContent = warn;
    $d('focus-info').textContent = state.focus ? T.focused + titleOf(byId.get(state.focus)) : '';
    const cur = last = { drawn: [...drawn], folded: rows, rows: Object.fromEntries([...rows].map(([p, list]) => [p, foldText(list)])),
      meta: $d('meta').textContent, warn, layoutMs: 0, size: null, dot };
    const view = keepView && zv ? zv.get() : null;
    if (zv) { zv.destroy(); zv = null; }
    if (!ids.size) { box.innerHTML = `<div class="msg">${L.empty}</div>`; return; }
    if (!view) box.innerHTML = `<div class="msg">${L.computing}</div>`;
    const seq = ++renderSeq, pinned = LAYOUT.get('detail', viewKey()) || {}, current = () => seq === renderSeq;
    let svg = null;
    (skeleton ? skeletonSvg(drawn, rows, cur) : GRAPHVIZ.render(dot)).then(first => {
      if (![...drawn].some(id => pinned[id])) return first;
      const pos = centres(first);
      Object.entries(pinned).forEach(([id, p]) => { if (pos.has(id)) pos.set(id, p); });
      return GRAPHVIZ.render(buildDot(drawn, pos, rows).dot, { engine: 'neato' });
    }).then(made => {
      if (!current()) return null; // a newer render was requested while this one was laying out
      svg = made;
      const vb = (svg.getAttribute('viewBox') || '').split(/[\s,]+/).map(Number);
      cur.size = vb.length === 4 ? [vb[2], vb[3]] : null;
      return graphZoom(box, svg, current);
    }).then(mounted => {
      if (!mounted) return;
      zv = mounted;
      if (view) zv.set(view);
      cur.layoutMs = performance.now() - t0;
      wire(svg, rows);
      canExport(true);
      if (!keepView) announce(skeleton, ids.size, foldedList.length, drawn.size, warn);
    }).catch(err => { if (current()) box.innerHTML = `<div class="msg">${L.error}${esc(err)}</div>`; });
  }

  // screen readers: what a finished drawing holds, only when it is a skeleton or has just stopped being one
  function announce(isSkeleton, total, folded, drawn, warn) {
    const live = $d('live');
    if (isSkeleton) live.textContent = T.live(drawn, total, folded);
    else if (wasSkeleton && !warn) live.textContent = T.liveFull;
    else live.textContent = '';
    wasSkeleton = isSkeleton;
  }

  // `rows`: parent id -> its folded entities (skeleton only): a search for a folded table lights its entity
  function wire(svg, rows) {
    const nodes = [...svg.querySelectorAll('g.node')], edges = [...svg.querySelectorAll('g.edge')];
    const ends = e => e.querySelector('title').textContent.split('->');
    const reset = () => [...nodes, ...edges].forEach(x => x.classList.remove('dim'));
    function highlight(ids) {
      nodes.forEach(n => n.classList.toggle('dim', !ids.has(n.id)));
      edges.forEach(e => { const [a, b] = ends(e); e.classList.toggle('dim', !(ids.has(a) && ids.has(b))); });
    }
    nodes.forEach(n => {
      n.addEventListener('mousedown', ev => startDrag(ev, n, svg));
      n.addEventListener('click', ev => { ev.stopPropagation(); if (!justDragged) highlight(new Set([n.id, ...neighbours.get(n.id)])); });
      n.addEventListener('dblclick', ev => { ev.stopPropagation(); setFocus(n.id); });
    });
    svg.addEventListener('click', reset);
    const q = $d('q');
    q.oninput = () => {
      const s = q.value.trim().toLowerCase(), has = e => e.name.toLowerCase().includes(s);
      s ? highlight(new Set(nodes.filter(n => has(byId.get(n.id)) || (rows.get(n.id) || []).some(has)).map(n => n.id))) : reset();
    };
    if (q.value) q.oninput();
  }

  refreshControls();
  render();

  // state() and svgImage are for the browser tests; the page uses svgImage through the export buttons
  return {
    shown: () => { if (stale) { stale = false; render(); } else refit(); },
    relayout: () => render(),
    // show a table in its own group, focused with its direct links
    focus(id) {
      const e = byId.get(id);
      if (!e) return;
      if (groupSel.style.display !== 'none') { groupSel.value = e.group; state.group = e.group; computeScope(); }
      state.focus = id;
      refreshControls();
      render();
    },
    state: () => ({ group: state.group, focus: state.focus, depth: state.depth, fold: { available: !$d('fold').hidden, on: foldOn },
      skeleton, threshold: SKELETON_MIN, ...last, folded: Object.fromEntries([...(last.folded || [])].map(([p, list]) => [p, list.map(e => e.id)])) }),
    svgImage: scale => svgImage(box, zv, scale),
  };
}
