// Detail view: entity-relationship diagram with columns, laid out by Graphviz (Viz.js).
// Started the first time its tab is shown; the returned handle lets the universe view open a table here.
function startDetail(DATA, LAYOUT, EXPORT) {
  const $d = id => document.getElementById('d-' + id);
  const T = {
    en: { all: 'All groups', focus: 'Focus on a table…', d1: 'direct links', d2: '2 levels', d3: '3 levels', clear: 'Show all',
          cols: 'All columns', fit: 'Fit', q: 'Highlight…', focused: 'Focused: ', rels: ['relation', 'relations'],
          foreign: 'dashed: other group',
          computing: 'Laying out…', error: 'Render error: ', hGroup: 'Group', hDepth: 'Around the focused table',
          hCols: 'Columns', svg: 'SVG',
          pngTitle: 'Save the visible diagram as a PNG image (high resolution)',
          svgTitle: 'Save the visible diagram as an SVG image (vector, opens in any browser)',
          hint: 'Wheel: zoom · drag the background to pan · drag a table to move it · click: highlight links · double-click: focus' },
    fr: { all: 'Tous les groupes', focus: 'Cibler une table…', d1: 'liens directs', d2: '2 niveaux', d3: '3 niveaux', clear: 'Tout afficher',
          cols: 'Toutes les colonnes', fit: 'Recentrer', q: 'Surligner…', focused: 'Ciblé : ', rels: ['relation', 'relations'],
          foreign: 'pointillé : autre groupe',
          computing: 'Calcul du schéma…', error: 'Erreur de rendu : ', hGroup: 'Groupe', hDepth: 'Autour de la table ciblée',
          hCols: 'Colonnes', svg: 'SVG',
          pngTitle: 'Enregistrer le schéma visible en image PNG (haute résolution)',
          svgTitle: 'Enregistrer le schéma visible en image SVG (vectorielle, s\'ouvre dans tout navigateur)',
          hint: 'Molette : zoom · glisser le fond : déplacer la vue · glisser une table : la déplacer · clic : surligner ses liens · double-clic : cibler' },
  }[PAGE.lang];
  const KIND = Object.fromEntries(DATA.kinds.map(k => [k.key, k]));
  const byId = new Map(DATA.entities.map(e => [e.id, e]));
  const neighbours = new Map(DATA.entities.map(e => [e.id, new Set()]));
  DATA.relations.forEach(r => { neighbours.get(r.child).add(r.parent); neighbours.get(r.parent).add(r.child); });
  const GROUPS = [...new Set(DATA.entities.map(e => e.group))].filter(g => g).sort();

  const state = { group: '', kinds: new Set(DATA.kinds.map(k => k.key)), allColumns: false, focus: null, depth: 1 };
  const box = $d('graph');
  let pz = null, viz = new Viz(), renderSeq = 0;

  const dotStr = s => String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\r?\n/g, '\\n');

  // --- group scope ----------------------------------------------------------
  // A group shows its own tables plus the other-group parents its tables point to.
  let scope = new Set(byId.keys());
  function computeScope() {
    scope = new Set(DATA.entities.filter(e => !state.group || e.group === state.group).map(e => e.id));
    if (state.group) DATA.relations.forEach(r => { if (byId.get(r.child).group === state.group) scope.add(r.parent); });
  }
  const isForeign = e => state.group && e.group !== state.group;
  const labelOf = e => isForeign(e) ? `${e.group} · ${e.name}` : e.name;

  // --- controls -------------------------------------------------------------
  $d('focus').placeholder = T.focus;
  $d('depth').innerHTML = [T.d1, T.d2, T.d3].map((t, i) => `<option value="${i + 1}">${t}</option>`).join('');
  $d('clear').textContent = T.clear;
  $d('cols').textContent = T.cols;
  $d('fit').textContent = T.fit;
  $d('q').placeholder = T.q;
  $d('hint').textContent = T.hint;
  $d('h-group').textContent = T.hGroup; $d('h-depth').textContent = T.hDepth;
  $d('h-cols').textContent = T.hCols; $d('h-kinds').textContent = L.kinds;

  const groupSel = $d('group');
  if (DATA.grouped && GROUPS.length > 1) {
    groupSel.innerHTML = `<option value="">${T.all}</option>` + GROUPS.map(g => `<option value="${esc(g)}">${esc(g)}</option>`).join('');
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
    return DATA.entities.find(e => scope.has(e.id) && (labelOf(e).toLowerCase() === s || e.name.toLowerCase() === s));
  }
  function submitFocus() { const e = findEntity(focusInput.value); if (e) setFocus(e.id); }
  focusInput.addEventListener('change', submitFocus);
  focusInput.addEventListener('keydown', ev => { if (ev.key === 'Enter') submitFocus(); });
  $d('depth').onchange = ev => { state.depth = +ev.target.value; if (state.focus) render(); };
  $d('clear').onclick = () => setFocus(null);
  $d('cols').onclick = ev => { state.allColumns = !state.allColumns; ev.target.classList.toggle('on', state.allColumns); render(); };
  // refitting a hidden tab would compute a zero zoom, so wait until it is shown again
  function refit() { if (pz && box.clientWidth) { pz.resize(); pz.fit(); pz.center(); } }
  $d('fit').onclick = refit;
  window.addEventListener('resize', refit);
  sidePanel('d', refit);
  const pngBtn = $d('export-png'), svgBtn = $d('export-svg');
  $d('export-h').textContent = L.exportImage;
  pngBtn.textContent = L.png; pngBtn.title = T.pngTitle;
  svgBtn.textContent = T.svg; svgBtn.title = T.svgTitle;
  // enabled only while a diagram is drawn and svg-pan-zoom drives it
  function canExport(on) { pngBtn.disabled = svgBtn.disabled = !on; }
  pngBtn.onclick = () => EXPORT.save('detail', 'png', pngImage, pngBtn);
  svgBtn.onclick = () => EXPORT.save('detail', 'svg', async () => {
    const text = svgImage(1);
    return text && new Blob([text], { type: 'image/svg+xml' });
  }, svgBtn);

  // type checkboxes and the focus autocomplete follow the selected group
  function refreshControls() {
    const inScope = DATA.entities.filter(e => scope.has(e.id));
    const shown = DATA.kinds.map(k => [k, inScope.filter(e => e.kind === k.key).length]).filter(([, n]) => n);
    typesEl.replaceChildren(...shown.map(([k, n]) => filterRow(
      { label: k.label, color: k.color, count: n, checked: state.kinds.has(k.key) },
      on => { on ? state.kinds.add(k.key) : state.kinds.delete(k.key); render(); })));
    $d('tables').innerHTML = inScope.map(e => `<option value="${esc(labelOf(e))}">`).join('');
    focusInput.value = state.focus ? labelOf(byId.get(state.focus)) : '';
  }

  function setFocus(id) {
    state.focus = id;
    focusInput.value = id ? labelOf(byId.get(id)) : '';
    render();
  }

  // --- graph ----------------------------------------------------------------
  function visibleIds() {
    let ids = new Set(scope);
    if (state.focus) {
      ids = new Set([state.focus]);
      let frontier = [state.focus];
      for (let d = 0; d < state.depth; d++) {
        const next = [];
        frontier.forEach(id => neighbours.get(id).forEach(n => { if (scope.has(n) && !ids.has(n)) { ids.add(n); next.push(n); } }));
        frontier = next;
      }
    }
    return new Set([...ids].filter(id => id === state.focus || state.kinds.has(byId.get(id).kind)));
  }

  function nodeDot(e, pos) {
    const k = KIND[e.kind];
    // trailing spaces keep bold names (under-measured by Viz.js) clear of the type column
    // Graphviz rejects an empty <font>: a column without data_type gets an empty cell
    const row = (name, type) => `<tr><td align="left">${name}&#160;&#160;&#160;</td><td align="left">${type ? `<font color="#888888">${esc(type)}</font>` : ''}</td></tr>`;
    const keys = e.columns.filter(c => c[2]), rest = e.columns.filter(c => !c[2]);
    let rows = keys.map(([c, t]) => row(`<b>${esc(c)}</b>`, t)).join('');
    if (state.allColumns) rows += rest.map(([c, t]) => row(esc(c), t)).join('');
    else if (rest.length) rows += `<tr><td colspan="2" align="left"><font color="#999999"><i>+ ${plural(rest.length, L.columns)}</i></font></td></tr>`;
    const border = e.id === state.focus ? 4 : 1;
    const style = isForeign(e) ? ' style="dashed"' : '';
    const tip = [e.group, e.name].filter(Boolean).join(' · ') + (e.description ? '\n\n' + e.description : '');
    const pin = pos ? ` pos="${pos[0]},${pos[1]}!"` : '';
    const id = dotStr(e.id);
    return `"${id}" [id="${id}"${pin} tooltip="${dotStr(tip)}" label=<<table border="${border}" cellborder="0" cellspacing="0" cellpadding="5"${style} color="${esc(k.color)}" bgcolor="${esc(k.bg)}">` +
      `<tr><td colspan="2" bgcolor="${esc(k.color)}"><font color="white" point-size="16"><b>${esc(labelOf(e))}</b></font></td></tr>${rows}</table>>];`;
  }

  // positions: table id -> [x, y] in Graphviz points, every table pinned (for neato); none for dot's own layout
  function buildDot(ids, positions) {
    const rels = DATA.relations.filter(r => ids.has(r.child) && ids.has(r.parent));
    const out = ['digraph G {', 'rankdir=LR; nodesep=0.35; ranksep=1.4; bgcolor="transparent";',
      // neato reads pinned positions in inches unless told they are points
      positions ? 'splines=true; overlap=true; inputscale=72;' : '',
      // Viz.js sizes boxes with built-in Helvetica/Arial metrics; any other font overflows them
      'node [shape=plain fontname="Arial" fontsize=14];',
      'edge [color="#8a8f98" penwidth=1.4 arrowsize=0.8 dir=back arrowtail=crow];'];
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
  // Moved tables are saved per drawing (group, focus, columns, types). Graphviz's dot lays everything out
  // first; when some tables were moved, neato redraws with every table pinned, moved ones where they were
  // dropped, so links are routed around the new positions.
  const viewKey = () => [state.group, state.focus || '', state.focus ? state.depth : '', state.allColumns ? 'all' : 'keys',
    DATA.kinds.filter(k => state.kinds.has(k.key)).map(k => k.key).join(',')].join('|');

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
    ev.stopPropagation(); ev.preventDefault();  // keep svg-pan-zoom from panning
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
    const ids = visibleIds();
    const { dot, relCount } = buildDot(ids);
    $d('meta').textContent = `${ids.size} / ${plural(scope.size, L.tables)} · ${plural(relCount, T.rels)}` +
      (state.group ? ` · ${T.foreign}` : '');
    $d('focus-info').textContent = state.focus ? T.focused + labelOf(byId.get(state.focus)) : '';
    const view = keepView && pz ? { zoom: pz.getZoom(), pan: pz.getPan() } : null;
    // destroy() resets the zoom first, which throws if the old svg has no usable size yet
    if (pz) { try { pz.destroy(); } catch (e) { /* the svg is replaced below anyway */ } pz = null; }
    if (!ids.size) { box.innerHTML = `<div class="msg">${L.empty}</div>`; return; }
    if (!view) box.innerHTML = `<div class="msg">${T.computing}</div>`;
    const seq = ++renderSeq, pinned = LAYOUT.get('detail', viewKey()) || {};
    viz.renderSVGElement(dot).then(svg => {
      if (![...ids].some(id => pinned[id])) return svg;
      const pos = centres(svg);
      Object.entries(pinned).forEach(([id, p]) => { if (pos.has(id)) pos.set(id, p); });
      return viz.renderSVGElement(buildDot(ids, pos).dot, { engine: 'neato' });
    }).then(svg => {
      if (seq !== renderSeq) return; // a newer render was requested while this one was laying out
      box.innerHTML = ''; box.appendChild(svg);
      if (!svg.getAttribute('viewBox')) svg.setAttribute('viewBox', '0 0 ' + parseFloat(svg.getAttribute('width')) + ' ' + parseFloat(svg.getAttribute('height')));
      svg.setAttribute('width', '100%'); svg.setAttribute('height', '100%');
      // svg-pan-zoom fits to the drawing's bbox once and stays stuck at zoom 0 if that bbox is
      // still empty (page laid out in the background), so wait until the svg has a real size
      const init = () => {
        if (seq !== renderSeq) return;
        const bb = svg.getBBox();
        if (!(bb.width && bb.height && svg.clientWidth && svg.clientHeight)) return requestAnimationFrame(init);
        pz = svgPanZoom(svg, { zoomScaleSensitivity: 0.3, maxZoom: 40, fit: true, center: true, dblClickZoomEnabled: false });
        if (view) { pz.zoom(view.zoom); pz.pan(view.pan); }
        wire(svg);
        canExport(true);
      };
      init();
    }).catch(err => { viz = new Viz(); if (seq === renderSeq) box.innerHTML = `<div class="msg">${T.error}${esc(err)}</div>`; });
  }

  function wire(svg) {
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
      const s = q.value.trim().toLowerCase();
      s ? highlight(new Set(nodes.filter(n => byId.get(n.id).name.toLowerCase().includes(s)).map(n => n.id))) : reset();
    };
    if (q.value) q.oninput();
  }

  // --- image export -------------------------------------------------------------
  // CSS of page.css that changes how the diagram looks, inlined into the exported SVG when it differs from
  // its default (everything else is Graphviz presentation attributes). A new such #d-graph rule adds its
  // property here.
  const INLINE = { opacity: '1' };
  const XLINK = 'http://www.w3.org/1999/xlink', XMLNS = 'http://www.w3.org/2000/xmlns/';
  const overlaps = (a, b) => a.right > b.left && a.left < b.right && a.bottom > b.top && a.top < b.bottom;
  const pageBackground = () => getComputedStyle(document.body).backgroundColor;

  // The visible part of the diagram as a standalone SVG document, `scale` x its size on screen (the
  // drawing stays vector); null when nothing is drawn. Only what is shown: tables and links outside the
  // visible area, tooltips and svg-pan-zoom's own markup are left out; ids (dbt unique_ids) are kept.
  function svgImage(scale) {
    const svg = pz && box.querySelector('svg');
    if (!svg) return null;
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
    Object.entries({ x: a.x, y: a.y, width: w, height: h, fill: pageBackground() }).forEach(([k, v]) => bg.setAttribute(k, v));
    clone.insertBefore(bg, clone.firstChild);
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(clone);
  }

  // the same SVG rasterised at 2 x the screen resolution (a data: URL keeps the canvas untainted)
  async function pngImage() {
    const svg = pz && box.querySelector('svg');
    if (!svg) return null;
    const r = svg.getBoundingClientRect(), s = EXPORT.scale(r.width, r.height);
    const img = new Image();
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgImage(s));
    await img.decode();
    const c = document.createElement('canvas');
    c.width = Math.round(r.width * s); c.height = Math.round(r.height * s);
    const g = c.getContext('2d');
    g.fillStyle = pageBackground(); g.fillRect(0, 0, c.width, c.height);
    g.drawImage(img, 0, 0, c.width, c.height);
    return EXPORT.png(c);
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
    svgImage,
  };
}
