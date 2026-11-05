// Flow view (M5.3, D-036): the trajectory of one table drawn left to right by Graphviz, upstream on the
// left, the start, downstream on the right. An overlay of the Universe tab, started by boot.js on first
// use; it reads the universe payload, never changes the universe and saves nothing (no layout, D-013).

function startFlow(DATA, EXPORT, close) {
  const FLOW_MAX = 150;          // tables drawn at most, start included: the one knob of the render time
  const FLOW_MIN_SCALE = 0.75;   // a smaller initial scale makes names unreadable: zoom to it on the start
  const START_RING = { gap: 6, width: 3, glow: 10 };   // screen pixels: the start's ring and glow at every zoom
  const $f = id => document.getElementById('f-' + id);
  const T = {
    en: { flowOf: 'Flow of', back: 'Universe', backTitle: 'Back to the universe (Esc)', fitTitle: 'Show the whole flow',
          clickFlow: 'Click: show its flow', levelsN: ['level', 'levels'], closed: 'Flow closed',
          capDepth: (e, total) => `Depth reduced to ${plural(e, T.levelsN)}: the chosen depth has ${plural(total, L.tables)}, a flow draws at most ${num(FLOW_MAX)}`,
          capCut: (shown, total) => `Only ${num(shown)} of the ${plural(total, L.tables)} at level 1 are drawn (at most ${num(FLOW_MAX)} per flow)`,
          pngTitle: 'Save the visible flow as a PNG image (high resolution)',
          svgTitle: 'Save the visible flow as an SVG image (vector, opens in any browser)',
          startTitle: 'Centre the view on the start table' },
    fr: { flowOf: 'Flux de', back: 'Univers', backTitle: 'Revenir à l\'univers (Échap)', fitTitle: 'Afficher tout le flux',
          clickFlow: 'Clic\u00a0: afficher son flux', levelsN: ['niveau', 'niveaux'], closed: 'Flux fermé',
          capDepth: (e, total) => `Profondeur réduite à ${plural(e, T.levelsN)}\u00a0: la profondeur choisie compte ${plural(total, L.tables)}, un flux en dessine au plus ${num(FLOW_MAX)}`,
          capCut: (shown, total) => `Seules ${num(shown)} des ${plural(total, L.tables)} du niveau 1 sont dessinées (au plus ${num(FLOW_MAX)} par flux)`,
          pngTitle: 'Enregistrer le flux visible en image PNG (haute résolution)',
          svgTitle: 'Enregistrer le flux visible en image SVG (vectorielle, s\'ouvre dans tout navigateur)',
          startTitle: 'Centrer la vue sur la table de départ' },
  }[PAGE.lang];
  const N = DATA.nodes, INDEX = new Map(N.map((n, i) => [n.id, i]));
  const byKey = list => Object.fromEntries(list.map((x, pos) => [x.key, { ...x, pos }]));
  const DOM = byKey(DATA.domains), KIND = byKey(DATA.kinds), LAYER = byKey(DATA.layers);
  const MINUS = '−';
  const view = $f('view'), box = $f('graph'), tip = $f('tip'), live = $f('live');
  const dirSel = $f('dir'), depthSel = $f('depth'), domains = $f('domains');
  const pngBtn = $f('export-png'), svgBtn = $f('export-svg');
  // st: the drawn flow (start, direction, requested depth, then what prepare() computed);
  // ring: the drawn start's node, its ring group (.f-halo) and its cached bounding box
  let st = null, zv = null, ring = null, renderSeq = 0, isOpen = false;

  // ---------------------------------------------------------------- controls
  $f('back-t').textContent = T.back; $f('back').title = T.backTitle;
  $f('of').textContent = T.flowOf;
  $f('start').title = T.startTitle;
  $f('start').onclick = () => locateStart();
  $f('h-dir').textContent = L.direction; $f('h-depth').textContent = L.depth;
  $f('fit').textContent = L.fit; $f('fit').title = T.fitTitle;
  $f('export-h').textContent = L.exportImage;
  pngBtn.textContent = L.png; pngBtn.title = T.pngTitle;
  svgBtn.textContent = L.svg; svgBtn.title = T.svgTitle;
  fillSelect(dirSel, ['both', 'up', 'down'].map(v => [v, L[v]]));
  dirSel.onchange = () => { st.direction = dirSel.value; update(false); };
  depthSel.onchange = () => { st.depth = depthSel.value === 'dall' ? Infinity : +depthSel.value.slice(1); update(false); };
  $f('back').onclick = () => close();
  // a resized window keeps the user's zoom and pan (the zoom is relative to the box's top-left corner);
  // Fit shows the whole flow again
  $f('fit').onclick = () => zv && zv.fit();
  // the Domains list stays inside the window: shifted left when its summary is near the right edge
  domains.addEventListener('toggle', () => {
    const list = $f('dom-list');
    list.style.left = '';
    if (!domains.open) return;
    const over = list.getBoundingClientRect().right - (document.documentElement.clientWidth - 8);
    if (over > 0) list.style.left = -over + 'px';
  });
  const canExport = on => { pngBtn.disabled = svgBtn.disabled = !on; };
  pngBtn.onclick = () => EXPORT.save('flow', 'png', () => pngImage(box, zv, EXPORT), pngBtn);
  svgBtn.onclick = () => EXPORT.save('flow', 'svg', () => svgFile(box, zv), svgBtn);

  // ---------------------------------------------------------------- what is drawn
  // The trajectory at the requested depth, reduced to at most FLOW_MAX tables: the deepest level that
  // fits, or the first FLOW_MAX - 1 tables of level 1 (upstream first, then by domain, then by name).
  function prepare() {
    const t0 = performance.now(), { start, direction, depth } = st;
    const all = trajectory(DATA.lineage, start, direction, depth);
    const near = new Map();   // table -> its shortest distance, upstream or downstream
    [all.up, all.down].forEach(m => m.forEach((d, i) => near.set(i, Math.min(d, near.get(i) ?? Infinity))));
    const perLevel = [];
    near.forEach(d => { perLevel[d] = (perLevel[d] || 0) + 1; });
    let e = 0, kept = 1;
    while (e + 1 < perLevel.length && kept + perLevel[e + 1] <= FLOW_MAX) kept += perLevel[++e];
    const total = near.size + 1, capped = e + 1 < perLevel.length;
    let keep = () => true, cap = capped ? T.capDepth(e, total) : '';
    if (capped && e === 0) {
      const first = [...near].filter(([, d]) => d === 1).map(([i]) => i).sort(levelOneOrder(all.up));
      const chosen = new Set(first.slice(0, FLOW_MAX - 1));
      keep = i => chosen.has(i); e = 1;
      cap = T.capCut(chosen.size, first.length);
    }
    const side = m => new Map([...m].filter(([i, d]) => d <= e && keep(i)));
    const up = side(all.up), dn = side(all.down);
    const edges = trajectoryEdges(DATA.lineage, start, up, dn);
    const members = [start, ...new Set([...up.keys(), ...dn.keys()])];
    const { rank, back } = flowRanks(members, edges.map(([c, p]) => [p, c]), i => LAYER[N[i].layer].pos);
    Object.assign(st, { effective: e, capped, cap, up, down: dn, edges, members, rank, back });
    st.dot = buildDot();
    st.prepareMs = performance.now() - t0;
  }
  const domainLabel = i => DOM[N[i].domain].label;
  const byPlace = (a, b) => domainLabel(a).localeCompare(domainLabel(b)) || N[a].name.localeCompare(N[b].name);
  const levelOneOrder = up => (a, b) => (up.has(a) ? 0 : 1) - (up.has(b) ? 0 : 1) || byPlace(a, b);

  // "−2", "+1", "−1 / +3" (a table on both sides), or the bold word start
  function depthLabel(i) {
    if (i === st.start) return dotText(L.lgStart);
    return [st.up.has(i) ? MINUS + num(st.up.get(i)) : '', st.down.has(i) ? '+' + num(st.down.get(i)) : ''].filter(Boolean).join(' / ');
  }
  // a table: domain band on the left edge, name on the kind colour (in an ink that reaches AA, D-037),
  // then its depth and layer
  function nodeDot(i) {
    const n = N[i], id = dotStr(n.id);
    const frame = i === st.start ? `border="3" color="${THEME.fg}"` : 'border="1" color="#c3c9d2"';
    return `"${id}" [id="${id}" label=<<table ${frame} cellborder="0" cellspacing="0" cellpadding="4" bgcolor="white">` +
      `<tr><td rowspan="2" width="6" bgcolor="${esc(CONTRAST.edge(DOM[n.domain].color, THEME.bg))}"></td>` +
      `<td align="left" bgcolor="${esc(KIND[n.kind].color)}"${dotEdge(KIND[n.kind].color)}><font color="${esc(CONTRAST.textOn(KIND[n.kind].color))}"><b>${dotText(n.name)}</b>&#160;&#160;&#160;</font></td></tr>` +
      `<tr><td align="left"><font color="${THEME.fg}" point-size="12"><b>${depthLabel(i)}</b></font>` +
      `<font color="${THEME.muted}" point-size="12">&#160;&#160;·&#160;&#160;${dotText(LAYER[n.layer].label)}</font></td></tr></table>>];`;
  }
  // columns imposed on dot: one rank=same group per column, each edge as long as its columns apart
  function buildDot() {
    const { members, rank, back } = st, quoted = i => `"${dotStr(N[i].id)}"`;
    const order = [...members].sort((a, b) => rank.get(a) - rank.get(b) || byPlace(a, b));
    const out = ['digraph G {', 'rankdir=LR; newrank=true; nodesep=0.25; ranksep=0.9; bgcolor="transparent";',
      // Viz.js sizes boxes with built-in Helvetica/Arial metrics; any other font overflows them
      'node [shape=plain fontname="Arial" fontsize=14];', 'edge [penwidth=1.4 arrowsize=0.8];'];
    order.forEach(i => out.push(nodeDot(i)));
    const columns = new Map();
    order.forEach(i => { const r = rank.get(i); columns.set(r, [...(columns.get(r) || []), quoted(i)]); });
    columns.forEach(ids => out.push(`{rank=same; ${ids.join('; ')};}`));
    st.edges.forEach(([c, p, dir]) => {
      const how = back.has(p + ',' + c) ? ' style=dotted constraint=false'
        : `${dir === 'up' ? ' style=dashed' : ''} minlen=${rank.get(c) - rank.get(p)}`;
      out.push(`${quoted(p)} -> ${quoted(c)} [color="${TRAJ_COLORS[dir]}"${how}];`);
    });
    out.push('}');
    return out.join('\n');
  }

  // ---------------------------------------------------------------- header
  const levelText = i => trajectoryLevels(st, i).map(([, text]) => text).join(', ');
  const countsText = () => (st.up.size + st.down.size ? `${plural(st.members.length, L.tables)} · ${trajectoryCounts(st.direction, st.up.size, st.down.size)}`
    : noTrajectory(st.direction));
  function header() {
    const n = N[st.start];
    paintDot($f('dot'), KIND[n.kind].color);
    $f('name').textContent = n.name; $f('name').title = n.name;
    dirSel.value = st.direction;
    const value = !st.capped && st.depth === Infinity ? 'dall' : 'd' + (st.capped ? st.effective : st.depth);
    const levels = ['dall', 'd1', 'd2', 'd3'].map(v => [v, L[v]]);
    if (!levels.some(([v]) => v === value)) levels.push([value, plural(+value.slice(1), T.levelsN)]);
    fillSelect(depthSel, levels, value);
    $f('counts').textContent = countsText();
    $f('cap').textContent = st.cap; $f('cap').hidden = !st.cap;
    domainList();
  }
  const dot = color => paintDot(document.createElement('i'), color);
  function row(mark, label, count) {
    const li = document.createElement('li'), text = document.createElement('span');
    text.textContent = label; li.append(mark, text);
    if (count !== undefined) { const small = document.createElement('small'); small.textContent = count; li.append(small); }
    return li;
  }
  function legendMark(kind) { const s = document.createElement('span'); s.className = 'fmk ' + kind; return s; }
  // the Domains list: the line legend, then each domain of the flow with its colour and table count
  function domainList() {
    const rows = [...countByDomain(N, st.members)].map(([k, c]) => ({ d: DOM[k], c })).sort((a, b) => b.c - a.c || a.d.label.localeCompare(b.d.label));
    const sum = $f('dom-sum'), count = document.createElement('span');
    count.textContent = plural(rows.length, L.domainsN);
    sum.replaceChildren(...rows.slice(0, 6).map(r => { const i = dot(r.d.color); i.setAttribute('aria-hidden', 'true'); return i; }), count);
    sum.title = rows.map(r => `${r.d.label}${L.colon}${num(r.c)}`).join('\n');
    const sep = document.createElement('li');
    sep.className = 'sep'; sep.setAttribute('role', 'separator');
    $f('dom-list').replaceChildren(row(legendMark('start'), L.lgStart), row(legendMark('up'), L.up),
      row(legendMark('down'), L.down), sep, ...rows.map(r => row(dot(r.d.color), r.d.label, num(r.c))));
  }

  // ---------------------------------------------------------------- drawing
  function update(keyboard) {
    prepare();
    header();
    live.textContent = `${T.flowOf} ${N[st.start].name}${L.colon}${countsText()}.` + (st.cap ? ` ${st.cap}.` : '');
    render(keyboard);
  }
  // keyboard: the recentre came from a focused table, so the focus follows to the new start
  function render(keyboard) {
    canExport(false); hideTip();
    if (zv) { zv.destroy(); zv = null; }
    ring = null;
    box.innerHTML = `<div class="msg">${L.computing}</div>`;
    const seq = ++renderSeq, current = () => seq === renderSeq && isOpen, source = st.dot;
    let svg = null;
    // one frame first, so "Laying out…" is painted before Graphviz holds the main thread
    requestAnimationFrame(() => {
      if (!current()) return;
      GRAPHVIZ.render(source).then(drawn => {
        if (!current()) return null;
        svg = drawn; tidy(svg);
        return graphZoom(box, svg, current, t => { hideTip(); ringStart(t.k); });
      }).then(mounted => {
        if (!mounted) return;
        zv = mounted;
        initialView(svg);
        wire(svg, keyboard);
        canExport(true);
      }).catch(err => { if (current()) box.innerHTML = `<div class="msg">${L.error}${esc(err)}</div>`; });
    });
  }
  const startNode = svg => [...svg.querySelectorAll('g.node')].find(g => g.id === N[st.start].id);
  // no native tooltip (Graphviz titles hold raw ids); each table is a button named by its name and level
  function tidy(svg) {
    svg.querySelectorAll('title').forEach(t => t.remove());
    // a group of buttons, not one image: screen readers reach each table
    svg.setAttribute('role', 'group'); svg.setAttribute('aria-label', `${T.flowOf} ${N[st.start].name}`);
    svg.querySelectorAll('g.node').forEach(g => {
      const i = INDEX.get(g.id);
      g.setAttribute('tabindex', '0');
      g.setAttribute('aria-label', `${N[i].name}, ${levelText(i)}`);
      if (i === st.start) g.setAttribute('aria-current', 'true'); else g.setAttribute('role', 'button');
    });
    addRing(svg);
  }
  // the start ring: a glow and a ring under every table and arrow (first in Graphviz's graph group),
  // presentation attributes only, so the exported images show it as the screen does
  function addRing(svg) {
    const NS = 'http://www.w3.org/2000/svg', node = startNode(svg), graph = node.parentNode;
    const halo = document.createElementNS(NS, 'g'), glow = document.createElementNS(NS, 'rect'), line = document.createElementNS(NS, 'rect');
    halo.setAttribute('class', 'f-halo'); halo.setAttribute('aria-hidden', 'true');
    glow.setAttribute('fill', THEME.fg); glow.setAttribute('fill-opacity', '0.14');
    line.setAttribute('fill', 'white'); line.setAttribute('stroke', THEME.fg);
    halo.append(glow, line);
    graph.insertBefore(halo, graph.querySelector(':scope > g.node, :scope > g.edge'));
    ring = { node, halo, bb: null };
  }
  // sizes the ring for zoom scale k: the same screen size whatever k (the start's box read once per render)
  function ringStart(k) {
    if (!ring) return;
    const bb = ring.bb || (ring.bb = ring.node.getBBox()), u = 1 / k, [glow, line] = ring.halo.children;
    const grow = (el, pad, extra) => Object.entries({ x: bb.x - pad, y: bb.y - pad, width: bb.width + 2 * pad,
      height: bb.height + 2 * pad, rx: pad, ...extra }).forEach(([name, v]) => el.setAttribute(name, v));
    const { gap, width } = START_RING;
    grow(line, (gap + width / 2) * u, { 'stroke-width': width * u });
    grow(glow, (gap + width + START_RING.glow) * u, {});
  }
  // the header's start button: the start in the middle of the area, at the current scale or FLOW_MIN_SCALE
  // if smaller; nothing while laying out or after a render error
  function locateStart(node = ring && ring.node) {
    if (zv && node) zv.centre(node.getBoundingClientRect(), Math.max(zv.get().k, FLOW_MIN_SCALE));
  }
  // the whole flow when readable (graphZoom fits it), else FLOW_MIN_SCALE centred on the start
  function initialView(svg) {
    if (zv.get().k < FLOW_MIN_SCALE) locateStart(startNode(svg));
  }
  function wire(svg, keyboard) {
    svg.querySelectorAll('g.node').forEach(g => {
      const i = INDEX.get(g.id);
      // a pan that ends on a table is not a click on it: graphZoom's clickDistance swallows that click
      g.addEventListener('click', () => recentre(i, false));
      g.addEventListener('keydown', ev => {
        if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); recentre(i, true); }
      });
      g.addEventListener('mousemove', ev => showTip(i, ev.clientX, ev.clientY));
      g.addEventListener('mouseleave', hideTip);
      g.addEventListener('focus', () => {
        if (!g.matches(':focus-visible')) return;
        const r = g.getBoundingClientRect(), b = box.getBoundingClientRect();
        if (r.left < b.left || r.right > b.right || r.top < b.top || r.bottom > b.bottom) zv.centre(r);
        const at = g.getBoundingClientRect();
        showTip(i, at.right, at.bottom);
      });
      g.addEventListener('blur', hideTip);
    });
    if (keyboard) { const g = startNode(svg); if (g) g.focus(); }
  }
  function recentre(i, keyboard) {
    if (i === st.start) return;
    st.start = i;
    update(keyboard);
  }

  // ---------------------------------------------------------------- tooltip
  function showTip(i, x, y) {
    if (matchMedia('(hover: none)').matches) return;   // touch: no hover, the tap recentres
    const n = N[i];
    tip.innerHTML = tableTip(DATA, n) + trajectoryTip(st, i)
      + tableDesc(n)
      + (i === st.start ? '' : `<div class="a">${T.clickFlow}</div>`);
    tip.style.display = 'block';
    const b = box.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
    let left = x - b.left + 14, top = y - b.top + 14;
    if (left + w > b.width - 8) left = x - b.left - 14 - w;   // flips left, then up, near the edges
    if (top + h > b.height - 8) top = y - b.top - 14 - h;
    tip.style.left = Math.max(8, left) + 'px'; tip.style.top = Math.max(8, top) + 'px';
  }
  function hideTip() { tip.style.display = 'none'; }

  // ---------------------------------------------------------------- open, close, Esc
  // Esc, only while open and shown: closes the Domains list first, does nothing on a select (it belongs
  // to its list, and never reaches the universe under the overlay), else closes the flow; the universe's own Esc then sees defaultPrevented and keeps its trajectory
  function onKey(ev) {
    if (ev.key !== 'Escape' || !document.getElementById('tab-universe').classList.contains('on')) return;
    if (domains.open) { domains.open = false; $f('dom-sum').focus(); }
    else if (ev.target.tagName === 'SELECT') { ev.stopPropagation(); return; }   // nor the universe's Esc
    else close();
    ev.preventDefault(); ev.stopPropagation();
  }
  function open(id, direction, depth) {
    const i = INDEX.get(id);
    if (i === undefined) return;
    st = { start: i, direction, depth };
    if (!isOpen) { isOpen = true; view.hidden = false; document.addEventListener('keydown', onKey, true); }
    update(false);
  }
  // hides the overlay; boot's closeFlow then uncovers the universe and puts the focus back on Flow.
  // "Flow closed" is said in the universe's live region, since #f-live is hidden with the overlay.
  function hide() {
    if (!isOpen) return;
    isOpen = false; renderSeq++;
    view.hidden = true; domains.open = false; hideTip();
    document.removeEventListener('keydown', onKey, true);
    document.getElementById('u-tj-live').textContent = T.closed;
  }
  // read-only view of the flow, for the browser tests; ids are dbt unique_ids
  function state() {
    if (!st || !st.members) return { open: isOpen };
    const ids = m => Object.fromEntries([...m].map(([i, d]) => [N[i].id, d]));
    const level = d => (d === Infinity ? 'all' : d);
    return { open: isOpen, start: N[st.start].id, direction: st.direction, depth: level(st.depth),
      effectiveDepth: st.capped ? st.effective : level(st.depth), capped: st.capped, prepareMs: st.prepareMs,
      up: ids(st.up), down: ids(st.down), edges: st.edges.map(([c, p, dir]) => [N[p].id, N[c].id, dir]),
      ranks: ids(st.rank), max: FLOW_MAX };
  }

  // state and svgImage are for the browser tests; the page uses the export buttons
  return { open, close: hide, isOpen: () => isOpen,
    state, svgImage: scale => svgImage(box, zv, scale) };
}
