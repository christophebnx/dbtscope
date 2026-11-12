// Detail view: entity-relationship diagram with columns, laid out by Graphviz (Viz.js).
// Started the first time its tab is shown; the returned handle lets the universe view open a table here.
function startDetail(DATA, LAYOUT, EXPORT) {
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
          foldedShort: ['folded', 'folded'], foldedMeta: 'folded', keysN: ['key', 'keys'],
          foldFocused: 'A focus draws every table',
          foldWarn: n => `${plural(n, L.tables)}${L.colon}the drawing will be hard to read`,
          foldLiveOn: n => `Descriptive tables folded${L.colon}${plural(n, L.tables)} drawn`,
          passNote: kinds => `Passing through ${kinds} costs no level` },
    fr: { all: 'Tous les groupes', focus: 'Cibler une table…', d1: 'liens directs', d2: '2 niveaux', d3: '3 niveaux', clear: 'Tout afficher',
          cols: 'Toutes les colonnes', q: 'Surligner…', focused: 'Ciblé\u00a0: ', rels: ['relation', 'relations'],
          foreign: 'pointillé\u00a0: autre groupe',
          hGroup: 'Groupe', hDepth: 'Autour de la table ciblée', hCols: 'Colonnes',
          pngTitle: 'Enregistrer le schéma visible en image PNG (haute résolution)',
          svgTitle: 'Enregistrer le schéma visible en image SVG (vectorielle, s\'ouvre dans tout navigateur)',
          hint: 'Molette ou pincement\u00a0: zoom · glisser le fond\u00a0: déplacer la vue · glisser une table\u00a0: la déplacer · '
              + 'clic\u00a0: surligner ses liens · double-clic\u00a0: cibler',
          touchHint: 'Pincement\u00a0: zoom · glisser\u00a0: déplacer la vue · toucher une table\u00a0: surligner ses liens',
          foldedShort: ['repliée', 'repliées'], foldedMeta: 'repliées', keysN: ['clé', 'clés'],
          foldFocused: 'Une table ciblée affiche toutes les tables',
          foldWarn: n => `${plural(n, L.tables)}${L.colon}le schéma sera difficile à lire`,
          foldLiveOn: n => `Tables descriptives repliées${L.colon}${plural(n, ['table dessinée', 'tables dessinées'])}`,
          passNote: kinds => `Passer par ${kinds} ne coûte aucun niveau` },
  }[PAGE.lang];
  const KIND = Object.fromEntries(DATA.kinds.map(k => [k.key, k]));
  const byId = new Map(DATA.entities.map(e => [e.id, e]));
  const neighbours = new Map(DATA.entities.map(e => [e.id, new Set()]));
  DATA.relations.forEach(r => { neighbours.get(r.child).add(r.parent); neighbours.get(r.parent).add(r.child); });
  const GROUPS = [...new Set(DATA.entities.map(e => e.group))].filter(g => g).sort();

  // Skeleton (M8.5, D-073): a large group is drawn with its descriptive tables folded into their parents.
  // `e.parent` (an id, from the universe's computation, D-062) and the kinds' roles come with the payload.
  const SKELETON_MIN = 60;   // scope tables above which a group may be drawn as a skeleton: a drawing rule, as FLOW_MAX
  const PARENT = new Map(DATA.entities.filter(e => e.parent && byId.has(e.parent)).map(e => [e.id, e.parent]));
  const ROLE = Object.fromEntries(DATA.kinds.map(k => [k.key, k.role]));
  const KIND_POS = new Map(DATA.kinds.map((k, i) => [k.key, i]));
  // the viewer's fold choice: its own memory, never in the layout, never exported (D-073)
  const foldMemory = viewerMemory('dbtscope-detail-fold', ['folded', 'shown']);
  const state = { group: '', kinds: new Set(DATA.kinds.map(k => k.key)), allColumns: false, focus: null, depth: 1,
                  fold: foldMemory.get() !== 'shown' };
  const box = $d('graph');
  let zv = null, renderSeq = 0;

  // --- group scope ----------------------------------------------------------
  // A group shows its own tables plus the other-group parents its tables point to.
  let scope = new Set(byId.keys()), eligible = false;
  // eligible: the scope is large enough and holds a table whose parent is in it, so the skeleton is possible
  const parentInScope = id => PARENT.has(id) && scope.has(PARENT.get(id));
  function computeScope() {
    scope = new Set(DATA.entities.filter(e => !state.group || e.group === state.group).map(e => e.id));
    if (state.group) DATA.relations.forEach(r => { if (byId.get(r.child).group === state.group) scope.add(r.parent); });
    eligible = scope.size > SKELETON_MIN && [...scope].some(parentInScope);
  }
  computeScope();
  const isForeign = e => state.group && e.group !== state.group;
  const entityName = e => isForeign(e) ? `${e.group} · ${e.name}` : e.name;

  // --- controls -------------------------------------------------------------
  $d('focus').placeholder = T.focus;
  fillSelect($d('depth'), [T.d1, T.d2, T.d3].map((t, i) => [String(i + 1), t]));
  $d('clear').textContent = T.clear;
  $d('cols').textContent = T.cols;
  $d('fit').textContent = L.fit;
  $d('q').placeholder = T.q;
  // on touch a drag on a table pans (tables move with the mouse only): a hint of its own
  $d('hint').textContent = matchMedia('(pointer: coarse)').matches ? T.touchHint : T.hint;
  $d('h-group').textContent = T.hGroup; $d('h-depth').textContent = T.hDepth;
  $d('h-cols').textContent = T.hCols; $d('h-kinds').textContent = L.kinds;
  $d('h-fold').textContent = L.foldH;
  // the fold control (D-073): shown for a group that can be a skeleton; its own memory, applied when the focus is cleared
  function setFold(on) {
    state.fold = on;
    foldMemory.set(on ? 'folded' : 'shown', 'folded');
    render();
    // the warning is a live region of its own: announce the choice only when it says nothing
    $d('live').textContent = on ? T.foldLiveOn(cur.drawn.size) : $d('fold-warn').textContent ? '' : L.foldLiveOff;
  }
  $d('fold-box').onchange = ev => setFold(ev.target.checked);
  // the warning's action: the same choice as the checkbox, which keeps the focus (the button hides with the warning)
  $d('fold-now').textContent = L.foldRow;
  $d('fold-now').onclick = () => { $d('fold-box').focus(); setFold(true); };
  function refreshFold(visibleCount) {
    $d('fold').hidden = !eligible;
    if (!eligible) return;
    const kinds = DATA.kinds.filter(k => ROLE[k.key] === 'descriptive' && [...scope].some(id => byId.get(id).kind === k.key && parentInScope(id)));
    $d('fold-label').textContent = foldLabel(kinds);
    $d('fold-n').textContent = num([...scope].filter(parentInScope).length);
    $d('fold-box').checked = state.fold;
    $d('fold-box').disabled = !!state.focus;
    $d('fold-row').title = state.focus ? T.foldFocused : L.foldTitle;
    const warn = !state.fold && !state.focus && visibleCount > SKELETON_MIN;
    $d('fold-warn').textContent = warn ? T.foldWarn(visibleCount) : '';
    $d('fold-now').hidden = !warn;
  }

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
    return DATA.entities.find(e => scope.has(e.id) && (entityName(e).toLowerCase() === s || e.name.toLowerCase() === s));
  }
  function submitFocus() { const e = findEntity(focusInput.value); if (e) setFocus(e.id); }
  focusInput.addEventListener('change', submitFocus);
  focusInput.addEventListener('keydown', ev => { if (ev.key === 'Enter') submitFocus(); });
  $d('depth').onchange = ev => { state.depth = +ev.target.value; if (state.focus) render(); };
  $d('clear').onclick = () => setFocus(null);
  $d('cols').onclick = ev => { state.allColumns = !state.allColumns; ev.target.classList.toggle('on', state.allColumns); render(); };
  // refitting a hidden tab would compute a zero zoom, so wait until it is shown again
  const refit = () => { metaTitle(); if (zv) zv.fit(); };
  // the meta line is one line cut with an ellipsis: when it is cut and says nothing more, its title holds it whole
  function metaTitle() {
    const m = $d('meta');
    if (!m.title && m.scrollWidth > m.clientWidth) m.title = m.textContent;
  }
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
    $d('tables').innerHTML = inScope.map(e => `<option value="${esc(entityName(e))}">`).join('');
    focusInput.value = state.focus ? entityName(byId.get(state.focus)) : '';
    // a connector kind of the group costs no level around a focused table (D-076)
    const passing = DATA.kinds.filter(k => ROLE[k.key] === 'connector' && inScope.some(e => e.kind === k.key));
    $d('depth-note').hidden = !passing.length;
    $d('depth-note').textContent = passing.length ? T.passNote(passing.map(labelOf).join(' · ')) : '';
  }

  function setFocus(id) {
    state.focus = id;
    focusInput.value = id ? entityName(byId.get(id)) : '';
    render();
  }

  // --- graph ----------------------------------------------------------------
  // The tables around the focus: a breadth-first walk over relations inside the scope, `state.depth` levels. A
  // connector (a kind of role `connector`, D-059) that the walk reaches is a passage: its neighbours join the same
  // level (D-076), so a hub at "direct links" also shows the hubs across its links. The kind filter applies after.
  function visibleIds() {
    let ids = new Set(scope);
    if (state.focus) {
      ids = new Set([state.focus]);
      let frontier = [state.focus];
      for (let d = 0; d < state.depth; d++) {
        const next = [], queue = [...frontier];
        for (let id = queue.shift(); id !== undefined; id = queue.shift()) {
          neighbours.get(id).forEach(n => {
            if (!scope.has(n) || ids.has(n)) return;
            ids.add(n);
            (ROLE[byId.get(n).kind] === 'connector' ? queue : next).push(n);
          });
        }
        frontier = next;
      }
    }
    return new Set([...ids].filter(id => id === state.focus || state.kinds.has(byId.get(id).kind)));
  }

  // The skeleton (D-073): no focus, a scope over SKELETON_MIN with a parent in it, and the viewer's choice "folded".
  const skeleton = () => eligible && state.fold && !state.focus;
  // The shown drawing of such a scope (the viewer unfolded it, or the filters left no table to fold) over the
  // threshold is laid out on the same grid: dot alone would make a strip of it (D-078).
  const gridShown = drawn => eligible && !state.focus && drawn.size > SKELETON_MIN;
  // `cur`: what the last render drew, set before the layout starts. visible: the tables that pass the filters and the
  // focus; folded: those whose parent is visible, in a skeleton only; drawn: visible minus folded; held: parent id ->
  // its folded tables, in name order.
  let cur = { skeleton: false, grid: false, folded: new Set(), drawn: new Set(), held: new Map(), cols: null, positions: null, splines: '', scope: 0, size: [0, 0], layoutMs: 0, prepMs: 0 };
  function drawingSets(visible, sk) {
    const folded = new Set(), held = new Map();
    if (sk) DATA.entities.forEach(e => {
      const p = PARENT.get(e.id);
      if (!visible.has(e.id) || !p || !visible.has(p)) return;
      folded.add(e.id);
      if (!held.has(p)) held.set(p, []);
      held.get(p).push(e.id);
    });
    return { folded, held, drawn: new Set([...visible].filter(id => !folded.has(id))) };
  }
  // "+ 3 folded tables · Satellite", "+ 4 folded tables · Satellite 3 · PIT 1": the kind labels in Types order, each
  // with its count only when several kinds are folded (config labels are singular nouns, never pluralised)
  function foldedText(ids) {
    const kinds = [...d3.rollup(ids, v => v.length, id => byId.get(id).kind)].sort((a, b) => KIND_POS.get(a[0]) - KIND_POS.get(b[0]));
    const list = kinds.map(([k, n]) => (kinds.length > 1 ? `${labelOf(KIND[k])} ${num(n)}` : labelOf(KIND[k])));
    return `+ ${plural(ids.length, L.foldedN)} · ${list.join(' · ')}`;
  }
  // a table's tooltip in a skeleton: its folded tables (`foldedLines`) and its column count
  function skeletonTip(e, heldIds) {
    const keys = e.columns.filter(c => c[2]).length;
    return [heldIds.length ? foldedLines(heldIds.map(id => ({ name: byId.get(id).name, kind: labelOf(KIND[byId.get(id).kind]) }))).join('\n') : '',
      `${plural(e.columns.length, L.columns)} · ${plural(keys, T.keysN)}`].filter(Boolean).join('\n\n');
  }

  function nodeDot(e, pos) {
    const k = KIND[e.kind], head = esc(CONTRAST.textOn(k.color)), grey = esc(CONTRAST.ink(THEME.muted, k.bg));
    // names on the kind colour and grey text on its tint reach AA whatever the colour (D-037);
    // the table border and the header's outline reach 3:1 on the page (D-042)
    // trailing spaces keep bold names (under-measured by Viz.js) clear of the type column
    // Graphviz rejects an empty <font>: a column without data_type gets an empty cell
    const row = (name, type) => `<tr><td align="left">${name}&#160;&#160;&#160;</td><td align="left">${type ? `<font color="${grey}">${dotText(type)}</font>` : ''}</td></tr>`;
    const note = text => `<tr><td colspan="2" align="left"><font color="${grey}"><i>${text}</i></font></td></tr>`;
    const heldIds = cur.held.get(e.id) || [];
    let rows = '';
    // a skeleton table draws no column rows at the keys level (its focus draws them); "All columns" draws every one
    if (!cur.skeleton || state.allColumns) {
      const keys = e.columns.filter(c => c[2]), rest = e.columns.filter(c => !c[2]);
      rows = keys.map(([c, t]) => row(`<b>${dotText(c)}</b>`, t)).join('');
      if (state.allColumns) rows += rest.map(([c, t]) => row(dotText(c), t)).join('');
      else if (rest.length) rows += note(`+ ${plural(rest.length, L.columns)}`);
    }
    if (heldIds.length) rows += note(dotText(foldedText(heldIds)));
    const border = e.id === state.focus ? 4 : 1;
    const style = isForeign(e) ? ' style="dashed"' : '';
    const tip = [[e.group, e.name].filter(Boolean).join(' · ') + (e.description ? '\n\n' + e.description : ''),
      cur.skeleton ? skeletonTip(e, heldIds) : ''].filter(Boolean).join('\n\n');
    const pin = pos ? ` pos="${pos[0]},${pos[1]}!"` : '';
    const id = dotStr(e.id);
    return `"${id}" [id="${id}"${pin} tooltip="${dotStr(tip)}" label=<<table border="${border}" cellborder="0" cellspacing="0" cellpadding="5"${style} color="${esc(CONTRAST.edge(k.color, THEME.bg))}" bgcolor="${esc(k.bg)}">` +
      `<tr><td colspan="2" bgcolor="${esc(k.color)}"${dotEdge(k.color)}><font color="${head}" point-size="16"><b>${dotText(entityName(e))}</b></font></td></tr>${rows}</table>>];`;
  }

  // --- grid layout (D-074) ------------------------------------------------------
  // Dot alone makes a strip of the hubs (one column) beside the links, and every relation that crosses columns adds
  // a virtual node to each column it crosses. A large drawing (the skeleton, or the shown tables of a group over the
  // threshold) is laid out on a grid instead, in K columns that come in pairs [hubs | links]: the referenced tables
  // are dealt over the hub columns, each referencing table goes to the link column beside its first (highest-degree)
  // parent, so a relation stays inside its pair. K is chosen so that the drawing has the aspect of the drawing area;
  // the rows are then ordered and aligned by barycentre sweeps, and neato only routes the relations around the
  // pinned tables, as after a drag. Sizes are estimated in points (never measured, as the universe's boxes, D-040);
  // everything here is deterministic.
  // routed: neato routes the relations around the tables up to this many tables x relations; above, they are
  // straight lines, as Viz.js's 16 MB heap aborts the routing of 277 pinned tables
  const SK = { gap: 16, gutter: 70, minAspect: 0.5, maxAspect: 3, sweeps: 6, scan: 60, routed: 5000 };
  const splinesFor = (ids, rels) => (ids.size * rels.length > SK.routed ? 'line' : 'true');
  function sizeOf(e) {
    const heldIds = cur.held.get(e.id) || [];
    // the rows a table draws: none in a skeleton (but the folded row), else its keys and a "+ N columns" row, or all
    const shown = cur.skeleton && !state.allColumns ? [] : state.allColumns ? e.columns : e.columns.filter(c => c[2]);
    const extra = !cur.skeleton && !state.allColumns && shown.length < e.columns.length ? 1 : 0;
    let w = Math.max(entityName(e).length * 7.3 + 22, heldIds.length ? foldedText(heldIds).length * 6.1 + 18 : 0);
    let h = 32 + (heldIds.length ? 26 : 0) + 24 * (shown.length + extra);
    if (shown.length) w = Math.max(w, ...shown.map(c => (c[0].length + c[1].length) * 7 + 40));
    return [w, h];
  }
  const byNameId = (a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
  // The centre y of the tables of a column, in this order, as near as possible to `want` while keeping their gaps
  // (pool adjacent violators: the least squares fit of non-decreasing offsets).
  function stack(ids, size, want) {
    const off = ids.map(() => 0), blocks = [];
    for (let i = 1; i < ids.length; i++) off[i] = off[i - 1] + (size.get(ids[i - 1])[1] + size.get(ids[i])[1]) / 2 + SK.gap;
    ids.forEach((id, i) => {
      blocks.push({ sum: want[i] - off[i], n: 1 });
      while (blocks.length > 1 && blocks[blocks.length - 2].sum / blocks[blocks.length - 2].n >= blocks[blocks.length - 1].sum / blocks[blocks.length - 1].n) {
        const top = blocks.pop(), under = blocks[blocks.length - 1];
        under.sum += top.sum; under.n += top.n;
      }
    });
    return blocks.flatMap(bl => Array.from({ length: bl.n }, () => bl.sum / bl.n)).map((v, i) => v + off[i]);
  }
  // tables: the drawn entities; rels: the drawn relations. Returns { K, rows: the table ids of each column from top to
  // bottom, y: id -> centre y (down, from 0), widths, height, size: id -> [w, h] }.
  function skeletonColumns(tables, rels) {
    const size = new Map(tables.map(e => [e.id, sizeOf(e)]));
    const degree = new Map(tables.map(e => [e.id, 0])), parentsOf = new Map(tables.map(e => [e.id, []]));
    const near = new Map(tables.map(e => [e.id, []]));
    rels.forEach(r => {
      degree.set(r.child, degree.get(r.child) + 1); degree.set(r.parent, degree.get(r.parent) + 1);
      parentsOf.get(r.child).push(r.parent); near.get(r.child).push(r.parent); near.get(r.parent).push(r.child);
    });
    const byDegree = (a, b) => degree.get(b.id) - degree.get(a.id) || byNameId(a, b);
    const asChild = new Set(rels.map(r => r.child));
    let hubs = tables.filter(e => !asChild.has(e.id)).sort(byDegree), links = tables.filter(e => asChild.has(e.id)).sort(byNameId);
    if (!hubs.length) [hubs, links] = [links.sort(byDegree), []];   // only cycles: no side to tell
    const paired = links.length > 0;
    for (const ps of parentsOf.values()) ps.sort((a, b) => byDegree(byId.get(a), byId.get(b)));
    const target = Math.log(Math.min(SK.maxAspect, Math.max(SK.minAspect, box.clientWidth / Math.max(1, box.clientHeight) || 1.6)));
    // P pairs [hubs | links] (P plain columns of hubs when nothing references a table)
    function deal(P) {
      const K = paired ? 2 * P : P, rows = Array.from({ length: K }, () => []), pair = new Map();
      const heights = new Array(K).fill(0), widths = new Array(K).fill(0), col = new Map();
      const put = (e, c) => {
        const [w, h] = size.get(e.id);
        col.set(e.id, c); rows[c].push(e.id); heights[c] += h + SK.gap; widths[c] = Math.max(widths[c], w);
      };
      hubs.forEach((e, i) => {   // the highest degrees first, dealt in a snake: 0..P-1, P-1..0, 0..P-1...
        const p = Math.floor(i / P) % 2 ? P - 1 - i % P : i % P;
        pair.set(e.id, p); put(e, paired ? 2 * p : p);
      });
      let pending = links;
      while (pending.length) {
        const rest = pending.filter(e => {
          const anchor = parentsOf.get(e.id)[0];
          if (!pair.has(anchor)) return true;
          pair.set(e.id, pair.get(anchor)); put(e, 2 * pair.get(anchor) + 1);
          return false;
        });
        if (rest.length === pending.length) {   // a cycle of links: the first one goes to the shortest link column
          const c = [...Array(P).keys()].reduce((a, b) => (heights[2 * b + 1] < heights[2 * a + 1] ? b : a));
          pair.set(rest[0].id, c); put(rest[0], 2 * c + 1); rest.shift();
        }
        pending = rest;
      }
      const w = widths.reduce((x, y) => x + y, 0) + (K - 1) * SK.gutter;
      return { K, rows, col, widths, ratio: w / Math.max(1, ...heights) };
    }
    let best = null;
    const most = paired ? Math.min(hubs.length, SK.scan / 2) : Math.min(hubs.length, SK.scan);
    for (let P = 1; P <= most; P++) {
      const d = deal(P), score = Math.abs(Math.log(d.ratio) - target);
      if (!best || score < best.score - 1e-9) best = { ...d, score };
    }
    if (!best) return { K: 0, rows: [], widths: [], height: 0, y: new Map(), size };
    // the rows: every column packed and centred on 0, then barycentre sweeps: the hubs by the mean y of the tables
    // across their relations, then the links by the mean y of theirs, each column stacked as near as it can to its
    // wish; the last step settles the links on their hubs, so a long relation runs in the gap between rows
    const y = new Map(), rows = best.rows;
    const settle = (c, order, want) => { rows[c] = order; stack(order, size, order.map(want)).forEach((v, i) => y.set(order[i], v)); };
    rows.forEach((ids, c) => settle(c, ids, () => 0));
    const wish = (c, id) => { const ns = near.get(id).filter(n => best.col.get(n) !== c); return ns.length ? d3.mean(ns, n => y.get(n)) : y.get(id); };
    const sweep = cols => cols.forEach(c => {
      const keyed = rows[c].map(id => [wish(c, id), id]).sort((p, q) => p[0] - q[0] || (p[1] < q[1] ? -1 : 1));
      settle(c, keyed.map(k => k[1]), id => wish(c, id));
    });
    const side = first => rows.map((r, c) => c).filter(c => !paired || c % 2 === first);
    for (let i = 0; i < SK.sweeps; i++) { sweep(side(0)); if (paired) sweep(side(1)); }
    const top = Math.min(...tables.map(e => y.get(e.id) - size.get(e.id)[1] / 2));
    const bottom = Math.max(...tables.map(e => y.get(e.id) + size.get(e.id)[1] / 2));
    tables.forEach(e => y.set(e.id, y.get(e.id) - top));
    return { K: best.K, rows, widths: best.widths, height: bottom - top, y, size };
  }
  // the centre of every table of the grid, in Graphviz points (y up): columns left to right
  function skeletonPositions(grid) {
    const pos = new Map();
    let x = 0;
    grid.rows.forEach((ids, c) => {
      ids.forEach(id => pos.set(id, [Math.round(x + grid.widths[c] / 2), -Math.round(grid.y.get(id))]));
      x += grid.widths[c] + SK.gutter;
    });
    return pos;
  }
  const drawnRelations = ids => DATA.relations.filter(r => ids.has(r.child) && ids.has(r.parent));

  // positions: table id -> [x, y] in Graphviz points, every table pinned (for neato); none for dot's own layout
  function buildDot(ids, positions, splines = 'true') {
    // straight lines, once the tables are placed well, are a quiet grey: a long relation is a hint, not a wall
    const rels = drawnRelations(ids);
    const out = ['digraph G {', 'rankdir=LR; nodesep=0.35; ranksep=1.4; bgcolor="transparent";',
      // neato reads pinned positions in inches unless told they are points
      positions ? `splines=${splines}; overlap=true; inputscale=72;` : '',
      // Viz.js sizes boxes with built-in Helvetica/Arial metrics; any other font overflows them
      'node [shape=plain fontname="Arial" fontsize=14];',
      `edge [color="${splines === 'line' ? '#8a8f9880' : '#8a8f98'}" penwidth=1.4 arrowsize=0.8 dir=back arrowtail=crow];`];
    DATA.entities.filter(e => ids.has(e.id)).forEach(e => out.push(nodeDot(e, positions && positions.get(e.id))));
    // Tables nothing else references (links, satellites, facts) all land in the last column; dozens
    // of them make one endless column, so spread them over 3, as Graphviz's `unflatten -l 3` would.
    const parents = new Set(rels.map(r => r.parent));
    const sinks = [...new Set(rels.map(r => r.child))].filter(id => !parents.has(id));
    const column = new Map(sinks.length > 12 ? sinks.map((id, i) => [id, 1 + i % 3]) : []);
    // parent -> child with dir=back puts referenced tables on the left, referencing ones on the right
    rels.forEach(r => {
      const minlen = column.has(r.child) ? ` minlen=${column.get(r.child)}` : '';
      out.push(`"${dotStr(r.parent)}" -> "${dotStr(r.child)}" [tooltip="${dotStr(`${byId.get(r.child).name}.${r.column} → ${byId.get(r.parent).name}`)}"${minlen}];`);
    });
    out.push('}');
    return { dot: out.join('\n'), relCount: rels.length };
  }

  // --- manual arrangement -----------------------------------------------------
  // Moved tables are saved per drawing (group, focus, columns, types; a skeleton adds `fold`, D-075: its dot
  // coordinates come from another layout). Graphviz's dot lays everything out first; when some tables were moved,
  // neato redraws with every table pinned, moved ones where they were dropped, so links are routed around the new
  // positions.
  const viewKey = () => [state.group, state.focus || '', state.focus ? state.depth : '', state.allColumns ? 'all' : 'keys',
    DATA.kinds.filter(k => state.kinds.has(k.key)).map(k => k.key).join(','), ...(cur.skeleton ? ['fold'] : cur.grid ? ['grid'] : [])].join('|');

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
      // neato moves its drawing to the origin: a gridded drawing's pins are kept in the frame of the positions it was given
      const given = cur.positions ? cur.positions.get(g.id) : null, [sx, sy] = given ? [cx - given[0], cy - given[1]] : [0, 0];
      pinned[g.id] = [Math.round(cx + dx - sx), Math.round(cy - dy - sy)];
      LAYOUT.set('detail', viewKey(), pinned);
      render(true);
    };
    window.addEventListener('mousemove', move); window.addEventListener('mouseup', up);
  }

  // The tables of a set counted per kind in Types order, "Hub 70 · Link 66" (the title of the meta line)
  const tally = ids => DATA.kinds.map(k => [k, [...ids].filter(id => byId.get(id).kind === k.key).length])
    .filter(([, n]) => n).map(([k, n]) => `${labelOf(k)} ${num(n)}`).join(' · ');

  // keepView: redraw without moving the camera (after a drop)
  function render(keepView) {
    canExport(false);
    const t0 = performance.now(), visible = visibleIds(), sk = skeleton(), sets = drawingSets(visible, sk);
    const gridded = sk || gridShown(sets.drawn);
    const mine = cur = { skeleton: sk, grid: gridded, ...sets, cols: null, positions: null, splines: '', scope: scope.size, size: [0, 0], layoutMs: 0, prepMs: 0 };
    const ids = mine.drawn;
    const pinned = LAYOUT.get('detail', viewKey()) || {};
    // a large drawing is laid out on a grid (neato only routes the relations); a moved table keeps its place on it
    let grid = null;
    if (gridded) {
      const rels = drawnRelations(ids);
      mine.cols = skeletonColumns(DATA.entities.filter(e => ids.has(e.id)), rels);
      grid = mine.positions = skeletonPositions(mine.cols);
      Object.entries(pinned).forEach(([id, p]) => { if (grid.has(id)) grid.set(id, p); });
      mine.splines = splinesFor(ids, rels);
    }
    const { dot, relCount } = buildDot(ids, grid, gridded ? mine.splines : undefined);
    mine.prepMs = performance.now() - t0;
    refreshFold(visible.size);
    const foreign = state.group ? ` · ${T.foreign}` : '', rels = plural(relCount, T.rels), all = plural(scope.size, L.tables);
    $d('meta').textContent = sk ? `${num(ids.size)} / ${all} · ${plural(mine.folded.size, T.foldedShort)} · ${rels}${foreign}`
      : `${num(ids.size)} / ${all} · ${rels}${foreign}`;
    $d('meta').title = sk ? tally(ids) + (mine.folded.size ? ` · ${T.foldedMeta}${L.colon}${tally(mine.folded)}` : '') : '';
    metaTitle();
    $d('focus-info').textContent = state.focus ? T.focused + entityName(byId.get(state.focus)) : '';
    const view = keepView && zv ? zv.get() : null;
    if (zv) { zv.destroy(); zv = null; }
    if (!ids.size) { box.innerHTML = `<div class="msg">${L.empty}</div>`; return; }
    if (!view) box.innerHTML = `<div class="msg">${L.computing}</div>`;
    const seq = ++renderSeq, current = () => seq === renderSeq, t1 = performance.now();
    let svg = null;
    (grid ? GRAPHVIZ.render(dot, { engine: 'neato' }) : GRAPHVIZ.render(dot).then(first => {
      if (![...ids].some(id => pinned[id])) return first;
      const pos = centres(first);
      Object.entries(pinned).forEach(([id, p]) => { if (pos.has(id)) pos.set(id, p); });
      return GRAPHVIZ.render(buildDot(ids, pos, splinesFor(ids, drawnRelations(ids))).dot, { engine: 'neato' });
    })).then(drawn => {
      if (!current()) return null; // a newer render was requested while this one was laying out
      svg = drawn;
      mine.layoutMs = performance.now() - t1;
      mine.size = [svg.viewBox.baseVal.width, svg.viewBox.baseVal.height];
      return graphZoom(box, svg, current);
    }).then(mounted => {
      if (!mounted) return;
      zv = mounted;
      if (view) zv.set(view);
      wire(svg);
      canExport(true);
    }).catch(err => { if (current()) box.innerHTML = `<div class="msg">${L.error}${esc(err)}</div>`; });
  }

  function wire(svg) {
    // the anchors of a skeleton's columns are no table
    const nodes = [...svg.querySelectorAll('g.node')].filter(n => byId.has(n.id)), edges = [...svg.querySelectorAll('g.edge')];
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
      const s = q.value.trim().toLowerCase();
      // a table is lit when its name matches, or the name of one of its folded tables does
      const hit = id => [id, ...(cur.held.get(id) || [])].some(t => byId.get(t).name.toLowerCase().includes(s));
      s ? highlight(new Set(nodes.filter(n => hit(n.id)).map(n => n.id))) : reset();
    };
    if (q.value) q.oninput();
  }

  refreshControls();
  render();

  // svgImage is for the browser tests; the page uses it through the export buttons
  return {
    shown: refit,
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
    svgImage: scale => svgImage(box, zv, scale),
    // what the last render drew, for the browser tests: the skeleton, its fold choice, the drawn and folded ids,
    // the scope size, the number of columns, the SVG size in points, the layout and preparation times (ms)
    drawing: () => ({ skeleton: cur.skeleton, grid: cur.grid, fold: state.fold, drawn: [...cur.drawn], folded: [...cur.folded], scope: cur.scope,
      columns: cur.cols ? cur.cols.K : 0, splines: cur.splines, size: cur.size, layoutMs: cur.layoutMs, prepMs: cur.prepMs }),
  };
}
