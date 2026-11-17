// Schema tab (M9.4, D-092 to D-094): a scope drawn as entity-relationship sheets. Three parts: the sheet model (pure: sizes and
// positions in sheet units, `sheetModel`), the one SVG emitter of a sheet rectangle (`sheetSvg`: the screen, the image export
// and, in M9.5, the print document and its tiles) and the tab's controller (`startSchema`). Page-wide declarations like
// common.js: M9.5 reads `S`, `LOOK`, `sheetModel` and `sheetSvg` as they are. No Graphviz here.

// Sheet constants, in sheet units (u): 1 u = 1 CSS px at scale 1, row text is ROW_FONT, so scale 1 is the reading scale.
// Every computation reads this object (the look constants beyond sizes are in LOOK).
const S = {
  ROW_FONT: 11, HEAD_FONT: 13, ROW_H: 18, HEAD_H: 24, PAD_X: 8, MIN_W: 120, GAP: 16, GUTTER: 48, LANE_PAD: 24, TITLE_H: 28,
  CHIP_H: 20, CHIP_GAP: 4, CELL_ASPECT: 1.6, READ: 0.9, GREEK_PX: 5, ROW_HEAD_MIN: 96, ROW_HEAD_MAX: 180, ROW_MIN_H: 84, TYPE_MAX: 28,
  // D-094: relations between two cells are summarised as chips above either of these (set by the measurement of the large project)
  LANES_FULL_TABLES: 300, LANES_FULL_EDGES: 16,
};
// The look of a sheet (colours, rules, ends of a relation); the same values draw the screen, the exports and the print.
const LOOK = {
  font: 'Arial, Helvetica, sans-serif', ink: THEME.fg, muted: THEME.muted, surface: THEME.surface, accent: THEME.accent, accentSoft: THEME.accentSoft,
  edge: '#767c86', edgeAlpha: 1, edgeW: 1, litW: 2, crow: 8, crowSpread: 5, arrow: 7, arrowHalf: 3.5, ring: 3, dim: 0.25,
  rule: '#c4cad3', rowAlpha: 0.07, bar: 4, badgePx: 14, chipBorder: '#8a8f98', bars: '#9aa0a8',
};
LOOK.accentInk = CONTRAST.ink(LOOK.accent, LOOK.accentSoft);   // the accent as text on an expanded chip: 4.5:1 (D-037)
const SHEET_TEXT = { en: { outside: '(outside this scope)' }, fr: { outside: '(hors de ce périmètre)' } }[PAGE.lang];
const GRID = { gap: S.GAP, gutter: S.GUTTER, minAspect: 0.5, maxAspect: 3, sweeps: 6, scan: 60 };

// Text widths measured once per distinct string in the sheet's font (a printed name must not leave its box): common.js `measure`.
const fontOf = (size, weight = 400, italic = false) => `${italic ? 'italic ' : ''}${weight} ${size}px ${LOOK.font}`;
const textW = (text, size, weight, italic) => measure(text, fontOf(size, weight, italic));
const shortType = t => { const s = t == null ? '' : String(t); return s.length > S.TYPE_MAX ? s.slice(0, S.TYPE_MAX - 1) + '…' : s; };

// The rows a box draws at a Show level, with the number of columns it hides: names (header only), keys (key columns), all
// (key columns first, then the others in payload order). A table without columns is a header at every level.
function boxRows(n, level) {
  if (level === 'names') return { rows: [], hidden: 0 };
  const keys = n.cols.filter(c => c[2]), shown = level === 'all' ? [...keys, ...n.cols.filter(c => !c[2])] : keys;
  return { rows: shown.map(c => ({ name: c[0], type: shortType(c[1]), key: !!c[2] })), hidden: n.cols.length - shown.length };
}
// The box of a table at a level: { w, h, rows, note } (the one place a level decides what a box holds, D-092). `tag`: the kind tag
// a printed header carries (kindTags, D-095); its width is reserved, so a name never meets it.
function boxSize(n, level, tag) {
  const { rows, hidden } = boxRows(n, level), note = hidden > 0 && level === 'keys' ? `+ ${plural(hidden, L.columns)}` : '';
  let w = Math.max(S.MIN_W, textW(n.name, S.HEAD_FONT, 600) + 2 * S.PAD_X + (tag ? textW(tag, S.ROW_FONT, 600) + S.PAD_X : 0));
  rows.forEach(r => { w = Math.max(w, textW(r.name, S.ROW_FONT, r.key ? 600 : 400) + textW(r.type, S.ROW_FONT) + 3 * S.PAD_X); });
  if (note) w = Math.max(w, textW(note, S.ROW_FONT, 400, true) + 2 * S.PAD_X);
  return { w, h: S.HEAD_H + S.ROW_H * (rows.length + (note ? 1 : 0)), rows, note };
}
// A short tag for each table kind, so a printed header reads without colour (D-095): Map(kind key -> tag). Pure and deterministic:
// kinds in payload order, each takes the first of these not taken yet: the first letter of its label, the initials of its words,
// its first two letters, its first three, then "K" and its position. Hub H, Link L, Satellite S, Point in time PIT.
function kindTags(kinds) {
  const taken = new Set(), tags = new Map();
  kinds.forEach((kind, i) => {
    const label = String(labelOf(kind)).trim(), words = label.split(/[^\p{L}\p{N}]+/u).filter(Boolean), chars = [...words.join('')];
    const up = s => s.toLocaleUpperCase('en');
    const options = [up(chars[0] || ''), up(words.map(w => [...w][0]).join('')), up(chars.slice(0, 2).join('')), up(chars.slice(0, 3).join('')), `K${i + 1}`];
    const tag = options.find(t => t && !taken.has(t)) || `K${i + 1}`;
    taken.add(tag); tags.set(kind.key, tag);
  });
  return tags;
}
// The universe nodes of a scope: { kind: 'all' } | { kind: 'domain' | 'layer', key } | { kind: 'filter', ids }
function scopeTables(universe, scope) {
  const nodes = universe.nodes;
  if (scope.kind === 'domain') return nodes.filter(n => n.domain === scope.key);
  if (scope.kind === 'layer') return nodes.filter(n => n.layer === scope.key);
  if (scope.kind === 'filter') { const ids = new Set(scope.ids); return nodes.filter(n => ids.has(n.id)); }
  return nodes;
}
// Wraps a label onto at most two lines of at most `max` u (the second is cut with an ellipsis).
function wrapLabel(label, max, size, weight) {
  const lines = [''];
  label.split(/\s+/).forEach(word => {
    const line = lines[lines.length - 1], next = line ? line + ' ' + word : word;
    if (textW(next, size, weight) <= max || !line) lines[lines.length - 1] = next;
    else if (lines.length < 2) lines.push(word);
    else lines[1] = next;
  });
  return lines.map(l => ellipsis(l, max, fontOf(size, weight)));
}

// The sheet model of a scope (pure; D-092, D-094). universe: the payload; nodes: the universe nodes of the scope; level: names |
// keys | all; opts.rels: [[child id, parent id]] of the whole project, opts.relColumns(child, parent) -> the FK columns known,
// opts.summarise: true | false to force the summarising of relations between cells (default: by S.LANES_FULL_*), opts.tags: the
// kindTags map of a print (headers then carry the tag; without it a box is the one of the screen).
// -> { W, H, columns, rows, cells, boxes, edges, chips, kinds, adj, summarised, interCell, stubs, ms, … }, all in sheet units.
function sheetModel(universe, nodes, level, opts = {}) {
  const t0 = performance.now(), { list } = domainOrder(universe), rels = opts.rels || [];
  const domRank = new Map(list.map((d, i) => [d.key, i])), layRank = new Map(universe.layers.map((l, i) => [l.key, i]));
  const domOf = new Map(universe.domains.map(d => [d.key, d])), layOf = new Map(universe.layers.map(l => [l.key, l]));
  const byId = new Map(nodes.map(n => [n.id, n])), all = new Map(universe.nodes.map(n => [n.id, n]));
  const colKeys = universe.layers.filter(l => nodes.some(n => n.layer === l.key)).map(l => l.key);
  const rowKeys = list.filter(d => nodes.some(n => n.domain === d.key)).map(d => d.key);
  const colAt = new Map(colKeys.map((k, i) => [k, i])), rowAt = new Map(rowKeys.map((k, i) => [k, i]));
  const showCols = colKeys.length > 1, showRows = rowKeys.length > 1, NC = colKeys.length;
  // sizes
  const sizes = new Map(), look = new Map();
  nodes.forEach(n => { const b = boxSize(n, level, opts.tags && opts.tags.get(n.kind)); look.set(n.id, b); sizes.set(n.id, [b.w, b.h]); });
  const kinds = new Map(universe.kinds.map(k => [k.key, { color: k.color, bg: k.bg || '#ffffff', head: CONTRAST.textOn(k.color),
    edge: CONTRAST.edge(k.color, THEME.bg), type: CONTRAST.ink(THEME.muted, k.bg || '#ffffff') }]));
  // cells
  const cells = new Map(), cellOf = new Map();
  nodes.forEach(n => {
    const key = rowAt.get(n.domain) * NC + colAt.get(n.layer);
    if (!cells.has(key)) cells.set(key, { key, row: rowAt.get(n.domain), col: colAt.get(n.layer), tables: [], ids: [], rels: [] });
    cells.get(key).tables.push(n); cells.get(key).ids.push(n.id); cellOf.set(n.id, key);
  });
  // relations: inside the scope (edges), or with one end outside it (stubs, chips only)
  const edges = [], stubs = [];
  rels.forEach(([child, parent]) => {
    if (child === parent) return;
    const c = byId.has(child), p = byId.has(parent);
    if (c && p) {
      edges.push({ child, parent, cc: cellOf.get(child), pc: cellOf.get(parent), intra: cellOf.get(child) === cellOf.get(parent) });
      if (edges[edges.length - 1].intra) cells.get(cellOf.get(child)).rels.push({ child, parent });
    } else if (c || p) stubs.push({ child, parent, inId: c ? child : parent, outId: c ? parent : child, childIn: c });
  });
  const interCell = edges.filter(e => !e.intra).length;
  const summarised = opts.summarise === undefined ? nodes.length > S.LANES_FULL_TABLES || interCell > S.LANES_FULL_EDGES : !!opts.summarise;
  edges.forEach(e => { e.drawn = e.intra || !summarised; e.col = (opts.relColumns ? opts.relColumns(e.child, e.parent) : [])[0] || ''; });
  // chips: one per (cell, other lane, direction); the side faces the other lane, the flow direction winning on a diagonal
  const chipMap = new Map();
  const addChip = (cell, other, to, out, rel, edge) => {
    const d = domRank.get(other.domain) ?? 0, l = layRank.get(other.layer) ?? 0, mine = cells.get(cell);
    const myD = domRank.get(rowKeys[mine.row]), myL = layRank.get(colKeys[mine.col]);
    const side = l !== myL ? (l > myL ? 'right' : 'left') : d > myD ? 'bottom' : 'top';
    const key = `${cell}|${other.domain}|${other.layer}|${to}|${out}`;
    if (!chipMap.has(key)) chipMap.set(key, { cell, otherDomain: other.domain, otherLayer: other.layer, to, out, side, n: 0, rels: [], order: [d, l], sameLayer: l === myL });
    const chip = chipMap.get(key);
    chip.n++; chip.rels.push({ ...rel, edge });
  };
  if (summarised) edges.forEach((e, i) => {
    if (e.intra) return;
    const c = byId.get(e.child), p = byId.get(e.parent), rel = { child: e.child, parent: e.parent, col: e.col };
    addChip(e.cc, p, true, false, { ...rel, otherId: e.parent }, i); addChip(e.pc, c, false, false, { ...rel, otherId: e.child }, i);
  });
  stubs.forEach(s => {
    const other = all.get(s.outId);
    if (other) addChip(cellOf.get(s.inId), other, s.childIn, true, { child: s.child, parent: s.parent, col: '', otherId: s.outId }, -1);
  });
  const chips = [...chipMap.values()].sort((a, b) => a.cell - b.cell || a.order[0] - b.order[0] || a.order[1] - b.order[1] || +b.to - +a.to || +a.out - +b.out);
  chips.forEach(ch => {
    const dom = domOf.get(ch.otherDomain), lay = layOf.get(ch.otherLayer), arrow = ch.to ? '→' : '←';
    ch.label = `${arrow} ${dom ? labelOf(dom) : ch.otherDomain}${ch.out ? ' ' + SHEET_TEXT.outside : ch.sameLayer ? '' : ' · ' + (lay ? labelOf(lay) : ch.otherLayer)}`;
    ch.count = num(ch.n);
    ch.w = Math.ceil(textW(`${ch.label}  ${ch.count}`, S.ROW_FONT) + 2 * S.PAD_X + 4);
  });
  // room for the chips on the cell borders: a strip on each side that has some, the chips never cover a box
  const pad = new Map(), need = new Map();
  cells.forEach(c => { pad.set(c.key, { l: S.LANE_PAD, r: S.LANE_PAD, t: S.LANE_PAD, b: S.LANE_PAD }); need.set(c.key, { w: 0, h: 0 }); });
  const bySide = new Map();
  chips.forEach(ch => { const k = ch.cell + ch.side; if (!bySide.has(k)) bySide.set(k, []); bySide.get(k).push(ch); });
  bySide.forEach((list2, k) => {
    const cell = list2[0].cell, side = list2[0].side, p = pad.get(cell), nd = need.get(cell);
    if (side === 'left' || side === 'right') {
      p[side === 'left' ? 'l' : 'r'] += Math.max(...list2.map(c => c.w)) + S.GAP;
      nd.h = Math.max(nd.h, list2.length * (S.CHIP_H + S.CHIP_GAP) - S.CHIP_GAP);
    } else {
      p[side === 'top' ? 't' : 'b'] += S.CHIP_H + S.GAP;
      nd.w = Math.max(nd.w, list2.reduce((s, c) => s + c.w + S.CHIP_GAP, -S.CHIP_GAP));
    }
  });
  // two passes (D-092): every cell for an aspect, then every cell of a row for the row's height
  const cellList = [...cells.values()].sort((a, b) => a.key - b.key);
  cellList.forEach(c => { c.deal = gridDeal(c.tables, c.rels, sizes, { aspect: S.CELL_ASPECT }, GRID); });
  const rowH = rowKeys.map(() => showRows ? S.ROW_MIN_H : 0);
  cellList.forEach(c => { const p = pad.get(c.key); rowH[c.row] = Math.max(rowH[c.row], p.t + Math.max(c.deal.height, need.get(c.key).h) + p.b); });
  cellList.forEach(c => {
    const p = pad.get(c.key);
    c.deal = gridDeal(c.tables, c.rels, sizes, { height: rowH[c.row] - p.t - p.b }, GRID);
    c.cw = c.deal.widths.reduce((s, w) => s + w, 0) + Math.max(0, c.deal.K - 1) * S.GUTTER;
    c.ch = c.deal.height;
  });
  const rowsH = rowKeys.map(() => showRows ? S.ROW_MIN_H : 0), colsW = colKeys.map(() => 0);
  cellList.forEach(c => {
    const p = pad.get(c.key), nd = need.get(c.key);
    rowsH[c.row] = Math.max(rowsH[c.row], p.t + Math.max(c.ch, nd.h) + p.b);
    colsW[c.col] = Math.max(colsW[c.col], p.l + Math.max(c.cw, nd.w) + p.r);
  });
  // lanes
  const heads = rowKeys.map(k => domOf.get(k)), headW = showRows
    ? Math.min(S.ROW_HEAD_MAX, Math.max(S.ROW_HEAD_MIN, ...heads.map(d => Math.min(textW(labelOf(d), S.HEAD_FONT, 600) + 2 * S.PAD_X + LOOK.bar, S.ROW_HEAD_MAX)))) : 0;
  const top = showCols ? S.TITLE_H : 0, count = (key, f) => nodes.filter(f).length;
  let x = headW, y = top;
  const columns = colKeys.map((k, i) => { const col = { key: k, label: labelOf(layOf.get(k)), x, w: colsW[i], n: count(k, n => n.layer === k) }; x += colsW[i]; return col; });
  const rows = rowKeys.map((k, i) => {
    const d = heads[i], row = { key: k, label: labelOf(d), color: d.color, x: 0, y, h: rowsH[i], n: count(k, n => n.domain === k),
      lines: wrapLabel(labelOf(d), headW - 2 * S.PAD_X - LOOK.bar, S.HEAD_FONT, 600) };
    y += rowsH[i];
    return row;
  });
  const W = x, H = y;
  // boxes: the cell's grid, columns left to right, each box centred in its column
  const boxes = new Map();
  cellList.forEach(c => {
    const p = pad.get(c.key), col = columns[c.col], row = rows[c.row];
    Object.assign(c, { x: col.x, y: row.y, w: col.w, h: row.h, n: c.tables.length });
    let cx = col.x + p.l;
    c.deal.rows.forEach((ids, ci) => {
      ids.forEach(id => {
        const b = look.get(id), n = byId.get(id), by = row.y + p.t + c.deal.y.get(id) - b.h / 2, bx = cx + (c.deal.widths[ci] - b.w) / 2;
        boxes.set(id, { id, name: n.name, kind: n.kind, tag: opts.tags ? opts.tags.get(n.kind) || '' : '', cell: c.key, x: bx, y: by, w: b.w, h: b.h, note: b.note,
          rows: b.rows.map((r, i) => ({ ...r, y: by + S.HEAD_H + i * S.ROW_H })) });
      });
      cx += c.deal.widths[ci] + S.GUTTER;
    });
  });
  // chips on the borders, stacked along their side in the other lane's order
  const along = new Map();
  chips.forEach(ch => {
    const c = cells.get(ch.cell), p = pad.get(ch.cell), k = ch.cell + ch.side, i = along.get(k) || 0;
    ch.h = S.CHIP_H;
    if (ch.side === 'left' || ch.side === 'right') {
      ch.x = ch.side === 'left' ? c.x + S.GAP / 2 : c.x + c.w - S.GAP / 2 - ch.w;
      ch.y = c.y + p.t + i * (S.CHIP_H + S.CHIP_GAP); along.set(k, i + 1);
    } else {
      ch.y = ch.side === 'top' ? c.y + S.GAP / 2 : c.y + c.h - S.GAP / 2 - S.CHIP_H;
      ch.x = c.x + p.l + i; along.set(k, i + ch.w + S.CHIP_GAP);
    }
  });
  // edges: the child end on the side facing the parent at its FK row (else the box's middle), the parent end at its first key row
  const adj = new Map(nodes.map(n => [n.id, []]));
  edges.forEach((e, i) => {
    const a = boxes.get(e.child), b = boxes.get(e.parent), same = a.x < b.x + b.w && b.x < a.x + a.w;
    const fk = a.rows.find(r => r.name === e.col), pk = b.rows.find(r => r.key);
    e.y1 = fk ? fk.y + S.ROW_H / 2 : a.y + a.h / 2; e.y2 = pk ? pk.y + S.ROW_H / 2 : b.y + S.HEAD_H / 2;
    if (same) { e.s1 = e.s2 = 1; e.x1 = a.x + a.w; e.x2 = b.x + b.w; e.bow = Math.max(e.x1, e.x2) + S.GUTTER / 2; }
    else if (b.x > a.x) { e.s1 = 1; e.s2 = -1; e.x1 = a.x + a.w; e.x2 = b.x; e.bow = 0; }
    else { e.s1 = -1; e.s2 = 1; e.x1 = a.x; e.x2 = b.x + b.w; e.bow = 0; }
    e.box = [Math.min(e.x1, e.x2), Math.min(e.y1, e.y2), Math.max(e.x1, e.x2, e.bow), Math.max(e.y1, e.y2)];
    adj.get(e.child).push(i); adj.get(e.parent).push(i);
  });
  return { W, H, unit: { rowFont: S.ROW_FONT, headFont: S.HEAD_FONT }, level, columns, rows,
    showCols, showRows, headW, top, cells: cellList, boxes, edges, stubs, chips, kinds, adj,
    summarised, interCell, tags: opts.tags || null, ms: performance.now() - t0 };
}

// ---------------------------------------------------------------- the SVG emitter (screen, export, print)
// The lines a relation is drawn with, at its two ends: a crow's foot at the FK end, a filled arrowhead at the PK end.
function relationPath(e, simple) {
  const x1 = rounded(1, e.x1), y1 = rounded(1, e.y1), x2 = rounded(1, e.x2), y2 = rounded(1, e.y2);
  const line = e.bow ? `M${x1} ${y1}C${rounded(1, e.bow)} ${y1} ${rounded(1, e.bow)} ${y2} ${x2} ${y2}` : `M${x1} ${y1}L${x2} ${y2}`;
  if (simple) return { line, head: '', main: line };
  const c = LOOK.crow * e.s1, sp = LOOK.crowSpread, a = LOOK.arrow * e.s2, h = LOOK.arrowHalf;
  return { main: line, line: `${line}M${rounded(1, x1 + c)} ${y1}L${x1} ${rounded(1, y1 - sp)}M${rounded(1, x1 + c)} ${y1}L${x1} ${y1}M${rounded(1, x1 + c)} ${y1}L${x1} ${rounded(1, y1 + sp)}`,
    head: `M${x2} ${y2}L${rounded(1, x2 + a)} ${rounded(1, y2 - h)}L${rounded(1, x2 + a)} ${rounded(1, y2 + h)}Z` };
}
// The chips of each side of each cell, as one badge each (the simple form): { chips: indexes, n: their total, x, y: the middle of them }.
function sideBadges(model) {
  const sides = new Map();
  model.chips.forEach((ch, i) => {
    const key = ch.cell + ch.side;
    if (!sides.has(key)) sides.set(key, { chips: [], n: 0, x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity });
    const g = sides.get(key);
    g.chips.push(i); g.n += ch.n;
    g.x0 = Math.min(g.x0, ch.x); g.y0 = Math.min(g.y0, ch.y); g.x1 = Math.max(g.x1, ch.x + ch.w); g.y1 = Math.max(g.y1, ch.y + ch.h);
  });
  return [...sides].map(([key, g]) => ({ key, chips: g.chips, n: g.n, x: (g.x0 + g.x1) / 2, y: (g.y0 + g.y1) / 2 }));
}
// The markup of everything of the sheet that meets `rect` ({x, y, w, h}, sheet units), to put inside an <svg>: lanes and their
// titles, relations (<g class="edge" id="e<i>">), boxes (<g class="node" id="<unique_id>">) and chips. form: 'full' (text) or
// 'simple' (far zoom: boxes without row text). marks: { k (scale, for hairlines and text that would be unreadable), selected,
// hover, expanded: Set of chip indexes, hit: add a wide invisible stroke to each relation, ids: false for `data-id` in place of `id`
// (a print repeats boxes and relations on its tiles, ids must stay unique), bare: true for a map (no text, no chips) }. Names are
// untrusted: all through esc.
function sheetSvg(model, rect, form, marks = {}) {
  const simple = form === 'simple', k = marks.k || 1, out = [], bare = !!marks.bare, idAttr = marks.ids === false ? 'data-id' : 'id';
  const meets = (x, y, w, h) => x < rect.x + rect.w && x + w > rect.x && y < rect.y + rect.h && y + h > rect.y;
  const words = !bare && (k * S.HEAD_FONT) >= S.GREEK_PX, small = !bare && (k * S.ROW_FONT) >= S.GREEK_PX;
  const text = (x, y, size, fill, body, extra = '') => `<text x="${rounded(1, x)}" y="${rounded(1, y)}" font-size="${size}" fill="${fill}"${extra}>${esc(body)}</text>`;
  // lanes: the row tints, the separators, the titles
  model.rows.forEach((r, i) => {
    out.push(`<rect x="0" y="${r.y}" width="${model.W}" height="${r.h}" fill="${esc(CONTRAST.edge(r.color, THEME.bg))}" fill-opacity="${LOOK.rowAlpha}"/>`);
    if (i && model.showRows) out.push(`<path d="M0 ${r.y}H${model.W}" stroke="${LOOK.rule}" stroke-width="1" fill="none"/>`);
  });
  if (model.showRows) model.rows.forEach(r => {
    out.push(`<rect x="${S.PAD_X / 2}" y="${r.y + 8}" width="${LOOK.bar}" height="${Math.max(8, r.h - 16)}" fill="${esc(CONTRAST.edge(r.color, THEME.bg))}"/>`);
    if (words) {
      const ink = CONTRAST.ink(r.color, THEME.bg);
      r.lines.forEach((l, i) => out.push(text(S.PAD_X + LOOK.bar, r.y + 22 + i * 16, S.HEAD_FONT, ink, l, ' font-weight="600"')));
      out.push(text(S.PAD_X + LOOK.bar, r.y + 22 + r.lines.length * 16, S.ROW_FONT, LOOK.muted, num(r.n)));
    }
  });
  if (model.showCols) model.columns.forEach((c, i) => {
    if (i) out.push(`<path d="M${c.x} 0V${model.H}" stroke="${LOOK.rule}" stroke-width="1" fill="none"/>`);
    if (words) out.push(`<text x="${c.x + S.LANE_PAD}" y="19" font-size="${S.HEAD_FONT}" fill="${LOOK.ink}" font-weight="600">${esc(c.label)}<tspan fill="${LOOK.muted}" font-weight="400" dx="6">${esc(num(c.n))}</tspan></text>`);
  });
  // relations: the drawn ones, and those of a selected or hovered table or of an expanded chip
  const lit = new Set();
  [marks.selected, marks.hover].forEach(id => (model.adj.get(id) || []).forEach(i => lit.add(i)));
  (marks.expanded || []).forEach(ci => (model.chips[ci]?.rels || []).forEach(r => { if (r.edge >= 0) lit.add(r.edge); }));
  const related = new Set(marks.selected ? [marks.selected] : []);
  if (marks.selected) (model.adj.get(marks.selected) || []).forEach(i => { related.add(model.edges[i].child); related.add(model.edges[i].parent); });
  const width = Math.min(3, Math.max(LOOK.edgeW, 1 / k)), litIds = marks.selected ? new Set((model.adj.get(marks.selected) || [])) : null;
  model.edges.forEach((e, i) => {
    const on = lit.has(i);
    if (!(e.drawn || on) || !meets(e.box[0], e.box[1], e.box[2] - e.box[0], e.box[3] - e.box[1])) return;
    const { line, head, main } = relationPath(e, simple), dim = litIds && !litIds.has(i) && !on ? ` class="edge dim" opacity="${LOOK.dim}"` : ' class="edge"';
    const color = on ? LOOK.accent : LOOK.edge, w = on ? Math.max(LOOK.litW, width) : width, alpha = on ? 1 : LOOK.edgeAlpha;
    out.push(`<g${dim} ${idAttr}="e${i}"><path d="${line}" fill="none" stroke="${color}" stroke-width="${rounded(1, w)}" stroke-opacity="${alpha}"/>`
      + (head ? `<path d="${head}" fill="${color}" stroke="none"/>` : '')
      + (marks.hit ? `<path class="hit" d="${main}" fill="none" stroke="transparent" stroke-width="${rounded(1, 8 / k)}"/>` : '') + '</g>');
  });
  // boxes: through the cells that meet the rectangle
  model.cells.forEach(c => {
    if (!meets(c.x, c.y, c.w, c.h)) return;
    c.ids.forEach(id => {
      const b = model.boxes.get(id);
      if (!meets(b.x - 4, b.y - 4, b.w + 8, b.h + 8)) return;
      const st = model.kinds.get(b.kind) || { color: '#cccccc', bg: '#ffffff', head: '#000000', edge: '#888888', type: LOOK.muted };
      const dim = marks.selected && !related.has(id) ? ` class="node dim" opacity="${LOOK.dim}"` : ' class="node"';
      let g = `<g${dim} ${idAttr}="${esc(id)}"><rect x="${rounded(1, b.x)}" y="${rounded(1, b.y)}" width="${rounded(1, b.w)}" height="${b.h}" fill="${st.bg}" stroke="${st.edge}" stroke-width="1"/>`
        + `<rect x="${rounded(1, b.x)}" y="${rounded(1, b.y)}" width="${rounded(1, b.w)}" height="${S.HEAD_H}" fill="${st.color}" stroke="${st.edge}" stroke-width="1"/>`;
      if (!simple || words) g += text(b.x + S.PAD_X, b.y + S.HEAD_H / 2 + 4.5, S.HEAD_FONT, st.head, b.name, ' font-weight="600"');
      if (b.tag && (!simple || words)) g += text(b.x + b.w - S.PAD_X, b.y + S.HEAD_H / 2 + 4, S.ROW_FONT, st.head, b.tag, ' font-weight="600" text-anchor="end"');
      if (!simple) {
        b.rows.forEach(r => {
          g += text(b.x + S.PAD_X, r.y + S.ROW_H / 2 + 4, S.ROW_FONT, LOOK.ink, r.name, r.key ? ' font-weight="600"' : '')
            + (r.type ? text(b.x + b.w - S.PAD_X, r.y + S.ROW_H / 2 + 4, S.ROW_FONT, st.type, r.type, ' text-anchor="end"') : '');
        });
        if (model.level === 'all') {
          const first = b.rows.findIndex(r => !r.key);
          if (first > 0) g += `<path d="M${rounded(1, b.x)} ${b.rows[first].y}H${rounded(1, b.x + b.w)}" stroke="${st.edge}" stroke-width="1" stroke-opacity=".5" fill="none"/>`;
        }
        if (b.note) g += text(b.x + S.PAD_X, b.y + S.HEAD_H + b.rows.length * S.ROW_H + S.ROW_H / 2 + 4, S.ROW_FONT, st.type, b.note, ' font-style="italic"');
      } else if (b.rows.length) {
        g += `<path d="${b.rows.map(r => `M${rounded(1, b.x + S.PAD_X)} ${r.y + S.ROW_H / 2}h${rounded(1, (b.w - 2 * S.PAD_X) * 0.55)}`).join('')}" stroke="${LOOK.bars}" stroke-width="5" stroke-opacity=".6" fill="none"/>`;
      }
      if (id === marks.selected) g += `<rect class="ring" x="${rounded(1, b.x - 2.5)}" y="${rounded(1, b.y - 2.5)}" width="${rounded(1, b.w + 5)}" height="${b.h + 5}" fill="none" stroke="${LOOK.accent}" stroke-width="${LOOK.ring}"/>`;
      out.push(g + '</g>');
    });
  });
  // chips: a count at a cell border. From afar (simple form) the chips of one side of a cell would be a pixel high and a pile:
  // each side is one badge with their total, kept at a constant size on screen (LOOK.badgePx text), over the middle of its chips
  if (bare) { /* a map: no chips */ } else if (!simple) model.chips.forEach((ch, i) => {
    if (!meets(ch.x, ch.y, ch.w, ch.h)) return;
    const on = marks.expanded && marks.expanded.has(i), dash = ch.out ? ' stroke-dasharray="4 3"' : '';
    out.push(`<g class="chip" data-chip="${i}"><rect x="${ch.x}" y="${ch.y}" width="${ch.w}" height="${ch.h}" rx="10" fill="${on ? LOOK.accentSoft : LOOK.surface}" stroke="${on ? LOOK.accent : LOOK.chipBorder}" stroke-width="${on ? 2 : 1}"${dash}/>`
      + (small ? text(ch.x + 10, ch.y + 14, S.ROW_FONT, on ? LOOK.accentInk : LOOK.ink, `${on ? '▾ ' : ''}${ch.label}  ${ch.count}`) : '') + '</g>');
  });
  else sideBadges(model).forEach(g => {
    const k2 = LOOK.badgePx / (S.ROW_FONT * k), room = 40 / k;
    if (!meets(g.x - room, g.y - room, 2 * room, 2 * room)) return;
    const on = g.chips.some(i => marks.expanded && marks.expanded.has(i)), label = num(g.n), w = textW(label, S.ROW_FONT, 600) + 10;
    out.push(`<g class="chip" data-side="${esc(g.key)}" transform="translate(${rounded(1, g.x)} ${rounded(1, g.y)}) scale(${rounded(1, k2)})">`
      + `<rect x="${rounded(1, -w / 2)}" y="-9" width="${rounded(1, w)}" height="18" rx="9" fill="${on ? LOOK.accentSoft : LOOK.surface}" stroke="${on ? LOOK.accent : LOOK.chipBorder}" stroke-width="${on ? 2 : 1}"/>`
      + text(-w / 2 + 5, 4, S.ROW_FONT, on ? LOOK.accentInk : LOOK.ink, label, ' font-weight="600"') + '</g>');
  });
  return out.join('');
}

// ---------------------------------------------------------------- the tab
// DATA: the universe payload; DETAIL: common.js detailIndex; EXPORT: boot.js; access: { location(), passingIds() } of the universe
// view (null while it is not started). Started the first time its tab is shown. Nothing of it is saved (D-092).
function startSchema(DATA, DETAIL, EXPORT, access) {
  const $s = id => document.getElementById('s-' + id);
  const T = {
    en: { scope: 'Scope', scopeAll: 'Whole project', scopeDomain: 'Domain', scopeSystems: 'Source systems', scopeLayer: 'Layer',
          scopeFilters: 'Current filters', scopeFiltersWhy: 'No filter is set in the Universe tab', show: 'Show',
          rels: ['relation', 'relations'], layersN: ['layer', 'layers'],
          noteSummarised: 'Relations between lanes are shown as counts; click a count to draw them.',
          noteHeavy: 'All columns of a large scope make a very large sheet; key columns read better.',
          crumbsAll: 'All domains', crumbsLayers: 'All layers', crumbsFilters: 'Current filters', noLayer: 'No layer',
          find: 'Find a table', sheet: 'Schema sheet', drawing: 'Drawing the sheet…', emptyScope: 'No table in this scope.',
          backAll: 'Show the whole project', popOut: 'Outside this scope', popClose: 'Close the list (Esc)', all: n => `Show all ${num(n)}`,
          pngTitle: 'Save the visible sheet as a PNG image (high resolution)',
          svgTitle: 'Save the visible sheet as an SVG image (vector, opens in any browser)',
          notInScope: name => `${name} is not in this scope`,
          chipAria: (a, b, n) => `Relations from ${a} to ${b}, ${num(n)}; show them`, chipAriaFrom: (a, b, n) => `Relations from ${b} to ${a}, ${num(n)}; show them`,
          popTitle: (a, b, n) => `${plural(n, ['relation', 'relations'])} from ${a} to ${b}`,
          popSide: (a, n) => `${plural(n, ['relation', 'relations'])} between ${a} and other lanes`,
          sideAria: (a, n) => `Relations between ${a} and other lanes, ${num(n)}; show them`,
          liveScope: (name, n, l) => `${name}: ${plural(n, L.tables)}, ${plural(l, ['layer', 'layers'])}`,
          liveSelect: (n, d, l, k, o, i) => `${n}: ${d} · ${l} · ${plural(k, ['key column', 'key columns'])} · references ${num(o)} · referenced by ${num(i)}`,
          liveChip: n => `${plural(n, ['relation', 'relations'])} drawn`, summary: 'Schema sheet',
          cellSummary: (l, d, n) => `${l} · ${d}: ${plural(n, L.tables)}`, countsSummary: (i, o) => `${plural(i, ['relation', 'relations'])} between lanes, ${plural(o, ['relation', 'relations'])} to tables outside this scope`,
          hintHead: 'This tab scrolls like a document',
          hintMouse: 'Wheel: scroll · Shift + wheel: scroll sideways · Ctrl + wheel or pinch: zoom · drag the background: pan · click a table: select it · click a count: draw its relations',
          hintKeys: 'Keys (sheet focused): arrows scroll · PgUp / PgDn: one screen · Home / End: corners · + / −: zoom · 0: fit · Esc: back',
          hintTouch: 'One finger: scroll · pinch: zoom · tap a table: select it · tap a count: draw its relations' },
    fr: { scope: 'Périmètre', scopeAll: 'Tout le projet', scopeDomain: 'Domaine', scopeSystems: 'Systèmes sources', scopeLayer: 'Couche',
          scopeFilters: 'Filtres actuels', scopeFiltersWhy: 'Aucun filtre n\'est posé dans l\'onglet Univers', show: 'Afficher',
          rels: ['relation', 'relations'], layersN: ['couche', 'couches'],
          noteSummarised: 'Les relations entre couloirs sont résumées par des nombres\u202f; cliquez sur un nombre pour les tracer.',
          noteHeavy: 'Toutes les colonnes d\'un grand périmètre donnent une très grande planche\u202f; les colonnes clés se lisent mieux.',
          crumbsAll: 'Tous les domaines', crumbsLayers: 'Toutes les couches', crumbsFilters: 'Filtres actuels', noLayer: 'Sans couche',
          find: 'Chercher une table', sheet: 'Planche du schéma', drawing: 'Dessin de la planche…', emptyScope: 'Aucune table dans ce périmètre.',
          backAll: 'Afficher tout le projet', popOut: 'Hors de ce périmètre', popClose: 'Fermer la liste (Échap)', all: n => `Afficher les ${num(n)}`,
          pngTitle: 'Enregistrer la planche visible en image PNG (haute résolution)',
          svgTitle: 'Enregistrer la planche visible en image SVG (vectorielle, s\'ouvre dans tout navigateur)',
          notInScope: name => `${name} n'est pas dans ce périmètre`,
          chipAria: (a, b, n) => `Relations de ${a} vers ${b}, ${num(n)}\u202f; les afficher`, chipAriaFrom: (a, b, n) => `Relations de ${b} vers ${a}, ${num(n)}\u202f; les afficher`,
          popTitle: (a, b, n) => `${plural(n, ['relation', 'relations'])} de ${a} vers ${b}`,
          popSide: (a, n) => `${plural(n, ['relation', 'relations'])} entre ${a} et d'autres couloirs`,
          sideAria: (a, n) => `Relations entre ${a} et d'autres couloirs, ${num(n)}\u202f; les afficher`,
          liveScope: (name, n, l) => `${name}\u00a0: ${plural(n, L.tables)}, ${plural(l, ['couche', 'couches'])}`,
          liveSelect: (n, d, l, k, o, i) => `${n}\u00a0: ${d} · ${l} · ${plural(k, ['colonne clé', 'colonnes clés'])} · référence ${num(o)} · référencée par ${num(i)}`,
          liveChip: n => `${plural(n, ['relation tracée', 'relations tracées'])}`, summary: 'Planche du schéma',
          cellSummary: (l, d, n) => `${l} · ${d}\u00a0: ${plural(n, L.tables)}`, countsSummary: (i, o) => `${plural(i, ['relation', 'relations'])} entre couloirs, ${plural(o, ['relation', 'relations'])} vers des tables hors de ce périmètre`,
          hintHead: 'Cet onglet défile comme un document',
          hintMouse: 'Molette\u00a0: défiler · Maj + molette\u00a0: défiler en largeur · Ctrl + molette ou pincement\u00a0: zoom · glisser le fond\u00a0: déplacer la vue · clic sur une table\u00a0: la sélectionner · clic sur un nombre\u00a0: tracer ses relations',
          hintKeys: 'Touches (planche active)\u00a0: flèches pour défiler · Pg. préc. / Pg. suiv.\u00a0: un écran · Début / Fin\u00a0: coins · + / −\u00a0: zoom · 0\u00a0: recadrer · Échap\u00a0: retour',
          hintTouch: 'Un doigt\u00a0: défiler · pincement\u00a0: zoom · toucher une table\u00a0: la sélectionner · toucher un nombre\u00a0: tracer ses relations' },
  }[PAGE.lang];
  const stage = $s('stage'), box = $s('graph'), tip = $s('tip'), live = $s('live'), empty = $s('empty'), backBtn = $s('back-all');
  const KIND = new Map(DATA.kinds.map(k => [k.key, k])), DOM = new Map(DATA.domains.map(d => [d.key, d])), LAY = new Map(DATA.layers.map(l => [l.key, l]));
  const NODE = new Map(DATA.nodes.map(n => [n.id, n]));
  const RELS = DATA.relations.map(([c, p]) => [DATA.nodes[c].id, DATA.nodes[p].id]);
  const { list: DOM_LIST, hasSystems, systemList } = domainOrder(DATA);
  const SYSTEM = new Set(systemList.map(d => d.key));
  const state = { scope: { kind: 'all' }, level: 'keys', selected: null, expanded: new Set(), hover: null, pop: null, all: false };
  const perf = { model: 0, emit: 0, firstFrame: 0, recull: 0, built: 0 };   // ms of the last of each; built counts the finished sheets
  let model = null, nodes = [], zv = null, layer = null, emitted = null, seq = 0, painting = 0, pendingSelect = null, filterKey = '';
  let mini = null, chipForm = null, units = [];   // units: what each chip button stands for (a chip, or in the simple form a side's chips)

  // --- static text and controls
  $s('h-scope').textContent = T.scope; $s('h-show').textContent = T.show;
  $s('scope').setAttribute('aria-labelledby', 's-h-scope'); $s('level').setAttribute('aria-labelledby', 's-h-show');
  fillSelect($s('level'), LEVELS(), state.level);
  $s('q').placeholder = T.find; $s('q').setAttribute('aria-label', T.find);
  $s('fit').textContent = L.fit;
  const help = $s('help-t');
  help.textContent = '?'; help.title = L.help; help.setAttribute('aria-label', L.help);
  dismissable(help.parentNode);
  const hint = $s('hint');
  hint.replaceChildren(Object.assign(document.createElement('b'), { textContent: T.hintHead }), document.createElement('br'),
    document.createTextNode(matchMedia('(pointer: coarse)').matches ? T.hintTouch : T.hintMouse));
  if (!matchMedia('(pointer: coarse)').matches) hint.append(document.createElement('br'), document.createTextNode(T.hintKeys));
  $s('crumbs').setAttribute('aria-label', L.location); box.setAttribute('aria-label', T.sheet); box.setAttribute('aria-describedby', 's-summary');
  $s('export-h').textContent = L.exportImage;
  const pngBtn = $s('export-png'), svgBtn = $s('export-svg');
  pngBtn.textContent = L.png; pngBtn.title = T.pngTitle; svgBtn.textContent = L.svg; svgBtn.title = T.svgTitle;
  // Print… (D-095) is disabled with its reason (title and the sr-only text it is described by) while the sheet computes or is empty
  const printBtn = $s('print-btn'), printWhy = $s('print-why');
  printBtn.textContent = L.print; printBtn.setAttribute('aria-describedby', 's-print-why');
  const canPrint = on => {
    const why = on ? '' : !nodes.length ? T.emptyScope : T.drawing;
    printBtn.disabled = !on; printBtn.title = why; printWhy.textContent = why;
  };
  const canExport = on => { pngBtn.disabled = svgBtn.disabled = !on; canPrint(on); };
  pngBtn.onclick = () => EXPORT.save('schema', 'png', () => pngImage(box, zv, EXPORT), pngBtn);
  svgBtn.onclick = () => EXPORT.save('schema', 'svg', () => svgFile(box, zv), svgBtn);
  const say = text => { live.textContent = ''; requestAnimationFrame(() => { live.textContent = text; }); };

  // --- scope
  const scopeValue = sc => (sc.kind === 'all' ? 'all' : sc.kind === 'filter' ? 'filters' : `${sc.kind}:${sc.key}`);
  const parseScope = v => {
    if (v === 'all') return { kind: 'all' };
    if (v === 'filters') {
      const ids = access.passingIds() || [];
      filterKey = ids.join(',');
      return { kind: 'filter', ids };
    }
    const [kind, ...rest] = v.split(':'), key = rest.join(':');
    const ok = kind === 'domain' ? DOM.has(key) : kind === 'layer' ? LAY.has(key) : false;
    return ok ? { kind, key } : { kind: 'all' };
  };
  function filtersAvailable() {
    const ids = access.passingIds();
    return !!ids && ids.length < DATA.nodes.length;
  }
  function fillScope() {
    const dom = d => [`domain:${d.key}`, labelOf(d)];
    const groups = hasSystems ? [[T.scopeDomain, DOM_LIST.filter(d => !SYSTEM.has(d.key)).map(dom)], [T.scopeSystems, DOM_LIST.filter(d => SYSTEM.has(d.key)).map(dom)]]
      : [[T.scopeDomain, DOM_LIST.map(dom)]];
    fillSelect($s('scope'), [['all', T.scopeAll], ...groups, [T.scopeLayer, DATA.layers.map(l => [`layer:${l.key}`, labelOf(l)])], ['filters', T.scopeFilters]], scopeValue(state.scope));
    syncFilters();
    $s('scope').value = scopeValue(state.scope);
  }
  // "Current filters" is disabled with its reason (D-085) while the universe has no filter set
  function syncFilters() {
    const ok = filtersAvailable(), o = $s('scope').querySelector('option[value=filters]');
    o.disabled = !ok && state.scope.kind !== 'filter';
    $s('scope-why').textContent = ok ? '' : T.scopeFiltersWhy;
  }
  const scopeName = () => state.scope.kind === 'domain' ? labelOf(DOM.get(state.scope.key)) : state.scope.kind === 'layer' ? labelOf(LAY.get(state.scope.key))
    : state.scope.kind === 'filter' ? T.scopeFilters : T.scopeAll;
  function setScope(scope, select) {
    state.scope = scope; state.selected = null; state.expanded = new Set(); state.pop = null; pendingSelect = select || null;
    $s('scope').value = scopeValue(scope);
    rebuild();
  }
  $s('scope').onchange = ev => setScope(parseScope(ev.target.value));
  $s('level').onchange = ev => { state.level = ev.target.value; state.expanded = new Set(); state.pop = null; pendingSelect = state.selected; rebuild(); };
  backBtn.textContent = T.backAll;
  backBtn.onclick = () => { $s('scope').focus(); setScope({ kind: 'all' }); };

  // --- crumbs, counts, notes
  function renderCrumbs() {
    const sel = state.selected && NODE.get(state.selected), kind = state.scope.kind, here = () => { if (zv) openView(); };
    const items = [{ label: kind === 'layer' ? T.crumbsLayers : T.crumbsAll, title: $s('meta').textContent, go: kind === 'all' ? here : () => setScope({ kind: 'all' }), current: kind === 'all' && !sel }];
    if (kind !== 'all') items.push({ label: scopeName(), go: here, current: !sel });
    if (sel) items.push({ label: sel.name, go: () => frame(sel.id), current: true });
    crumbs($s('crumbs'), items);
  }
  function renderMeta() {
    const ids = new Set(nodes.map(n => n.id)), rels = RELS.filter(([c, p]) => ids.has(c) && ids.has(p)).length;
    const doms = new Set(nodes.map(n => n.domain)).size, lays = new Set(nodes.map(n => n.layer)).size;
    $s('meta').textContent = [plural(nodes.length, L.tables), plural(rels, T.rels), plural(doms, L.domainsN), plural(lays, T.layersN)].join(' · ');
    const note = !model ? '' : model.summarised ? T.noteSummarised : state.level === 'all' && nodes.length > 1000 ? T.noteHeavy : '';
    $s('note').textContent = note; $s('note').hidden = !note;
  }
  function renderSummary() {
    const items = model.cells.map(c => `<li>${esc(T.cellSummary(labelOf(LAY.get(model.columns[c.col].key)), labelOf(DOM.get(model.rows[c.row].key)), c.n))}</li>`);
    $s('summary').innerHTML = `<h2>${esc(T.summary)}</h2><ul>${items.join('')}</ul><p>${esc(T.countsSummary(model.interCell, model.stubs.length))}</p>`;
  }

  // --- the screen: a virtualised SVG in one zoom layer
  const view = () => {
    const t = zv.get();
    return { x0: -t.x / t.k, y0: -t.y / t.k, w: box.clientWidth / t.k, h: box.clientHeight / t.k, k: t.k, tx: t.x, ty: t.y };
  };
  const formFor = k => (k * S.ROW_FONT >= S.GREEK_PX ? 'full' : 'simple');
  const marks = k => ({ k, selected: state.selected, hover: state.hover, expanded: state.expanded, hit: true });
  function paint(kind) {
    if (!zv || !model) return;
    const t0 = performance.now(), v = view(), rect = { x: v.x0 - v.w, y: v.y0 - v.h, w: 3 * v.w, h: 3 * v.h }, form = formFor(v.k);
    layer.innerHTML = sheetSvg(model, rect, form, marks(v.k));
    emitted = { rect, form, k: v.k };
    perf.emit = performance.now() - t0;
    if (kind === 'recull') perf.recull = perf.emit;
  }
  function stale(v) {
    if (!emitted) return true;
    const r = emitted.rect;
    return formFor(v.k) !== emitted.form || Math.abs(Math.log(v.k / emitted.k)) > 0.4 || v.x0 < r.x + v.w * 0.5 || v.y0 < r.y + v.h * 0.5
      || v.x0 + v.w > r.x + r.w - v.w * 0.5 || v.y0 + v.h > r.y + r.h - v.h * 0.5;
  }
  function repaint(kind) {
    if (painting) return;
    painting = requestAnimationFrame(() => { painting = 0; paint(kind); });
  }
  function onZoom() {
    if (!zv || !model) return;
    tip.style.display = 'none';
    const v = view();
    syncChips(v); syncHeads(v); syncMini(v);
    if (stale(v)) repaint('recull');
  }
  function mount() {
    if (zv) zv.destroy();
    box.innerHTML = '<svg width="100%" height="100%" aria-hidden="true"><g></g></svg>';
    layer = box.querySelector('g'); box.querySelector('svg').setAttribute('font-family', LOOK.font);
    emitted = null;
    zv = zoomHandle(box, layer, [model.W, model.H], onZoom, { scroll: true });
  }
  // the opening view (the document rule, D-093): the whole sheet when its rows then read at 10 px or more, else scale 1 at the first cell
  function openView() {
    const fit = Math.min(box.clientWidth / model.W, box.clientHeight / model.H);
    if (fit >= S.READ) {
      const k = Math.min(fit, 1.5);
      zv.set({ x: (box.clientWidth - model.W * k) / 2, y: (box.clientHeight - model.H * k) / 2, k });
    } else {
      const first = [...model.cells].sort((a, b) => a.row - b.row || a.col - b.col)[0];
      zv.set({ x: S.LANE_PAD - first.x, y: S.LANE_PAD - first.y, k: 1 });
    }
  }
  function frame(id, kMin = 1) {
    const b = model && model.boxes.get(id);
    if (!b || !zv) return;
    const k = Math.max(zv.get().k, kMin);
    zv.set({ x: box.clientWidth / 2 - (b.x + b.w / 2) * k, y: box.clientHeight / 2 - (b.y + b.h / 2) * k, k });
  }
  function showEmpty(message, again) {
    empty.hidden = !message; empty.replaceChildren();
    if (!message) return;
    empty.append(Object.assign(document.createElement('span'), { textContent: message }));
    backBtn.hidden = !again;
    if (again) empty.append(' ', backBtn);
  }
  function rebuild() {
    const mine = ++seq, t0 = performance.now();
    nodes = scopeTables(DATA, state.scope);
    renderMeta(); renderCrumbs(); fillTables(); canExport(false);
    if (!nodes.length) {
      if (zv) { zv.destroy(); zv = null; }
      box.replaceChildren(); model = null; stage.classList.remove('has-mini'); showEmpty(T.emptyScope, true);
      syncChips(null); syncHeads(null); syncMini(null);
      return;
    }
    showEmpty(T.drawing, false); empty.setAttribute('role', 'status');
    requestAnimationFrame(() => {
      if (mine !== seq) return;
      try {
        const m0 = performance.now();
        model = sheetModel(DATA, nodes, state.level, { rels: RELS, relColumns: DETAIL.relationColumns });
        perf.model = performance.now() - m0;
        renderMeta(); renderSummary(); buildChips(); buildMini();
        mount();
        const sel = pendingSelect && model.boxes.has(pendingSelect) ? pendingSelect : null;
        state.selected = sel; pendingSelect = null;
        openView();
        paint('first');
        showEmpty('');
        renderCrumbs(); onZoom();
        if (sel) { frame(sel); }
        canExport(true);
        say(T.liveScope(scopeName(), nodes.length, new Set(nodes.map(n => n.layer)).size));
        requestAnimationFrame(() => { perf.firstFrame = performance.now() - t0; perf.built++; });
      } catch (e) {
        showEmpty(L.error + e.message, false);
        throw e;
      }
    });
  }

  // --- chips: buttons over the SVG chips (HTML, never exported), their list, expansion
  const chipsEl = $s('chips'), pop = $s('pop');
  // One button per unit: a chip, or from afar (the simple form draws one badge per cell side) the chips of that side, so a
  // click reaches all of them and the Tab key stops once per badge. Rebuilt when the form changes.
  const domainOfChip = ch => DOM.get(model.rows[model.cells.find(c => c.key === ch.cell).row].key);
  function unitsFor(form) {
    if (form === 'simple') return sideBadges(model);
    return model.chips.map((ch, i) => ({ chips: [i], x: ch.x + ch.w / 2, y: ch.y + ch.h / 2 }));
  }
  function buildChips(form) {
    chipForm = form || null; units = form ? unitsFor(form) : [];
    chipsEl.replaceChildren(...units.map(u => {
      const first = model.chips[u.chips[0]], b = document.createElement('button'), mine = domainOfChip(first);
      b.type = 'button'; b.dataset.chip = u.chips[0]; b.setAttribute('aria-expanded', 'false');
      const a = labelOf(mine), other = DOM.get(first.otherDomain), o = other ? labelOf(other) : first.otherDomain;
      if (form === 'simple') b.dataset.side = u.key;
      b.setAttribute('aria-label', form === 'simple' ? T.sideAria(a, u.n) : first.to ? T.chipAria(a, o, first.n) : T.chipAriaFrom(a, o, first.n));
      b.onclick = () => toggleUnit(u.chips);
      b.onfocus = () => { stage.scrollLeft = stage.scrollTop = 0; keepInView(u.x, u.y); };
      return b;
    }));
  }
  function keepInView(cx, cy) {
    const v = view();
    if (cx > v.x0 && cx < v.x0 + v.w && cy > v.y0 && cy < v.y0 + v.h) return;
    zv.set({ x: box.clientWidth / 2 - cx * v.k, y: box.clientHeight / 2 - cy * v.k, k: v.k });
  }
  function syncChips(v) {
    if (!v || !model) { chipForm = null; return chipsEl.replaceChildren(); }
    const form = formFor(v.k);
    if (form !== chipForm) buildChips(form);
    const coarse = matchMedia('(pointer: coarse)').matches, min = coarse ? 44 : 24, simple = form === 'simple';
    [...chipsEl.children].forEach((b, j) => {
      const u = units[j], ch = model.chips[u.chips[0]];
      const w = simple ? Math.max(LOOK.badgePx * 2.2, min) : Math.max(ch.w * v.k, min), h = simple ? Math.max(LOOK.badgePx * 1.4, min) : Math.max(ch.h * v.k, min);
      b.style.width = w + 'px'; b.style.height = h + 'px';
      b.style.transform = `translate(${u.x * v.k + v.tx - w / 2}px,${u.y * v.k + v.ty - h / 2}px)`;
      b.setAttribute('aria-expanded', String(u.chips.every(i => state.expanded.has(i))));
    });
  }
  // press a chip, or a side's badge: every chip of it is drawn and listed in the one popover; pressed again, folded
  function toggleUnit(list) {
    if (list.every(i => state.expanded.has(i))) { collapse(list); closePop(false); }
    else { list.forEach(i => state.expanded.add(i)); openPop(list); say(T.liveChip(list.reduce((n, i) => n + model.chips[i].n, 0))); }
    syncChips(view());
    paint();
  }
  const collapse = list => list.forEach(i => state.expanded.delete(i));
  // the popover of a list of chips (the one #s-pop): a heading and items for each, at most 20 items in all, then "Show all N"
  function openPop(list, all) {
    state.pop = list;
    const chips = list.map(i => model.chips[i]), total = chips.reduce((n, c) => n + c.n, 0), first = chips[0];
    const mine = labelOf(domainOfChip(first)), close = document.createElement('button');
    close.type = 'button'; close.textContent = '×'; close.title = T.popClose; close.setAttribute('aria-label', T.popClose);
    close.onclick = () => { collapse(list); closePop(true); syncChips(view()); paint(); };
    const parts = [], title = c => { const other = DOM.get(c.otherDomain), o = other ? labelOf(other) : c.otherDomain; return c.to ? T.popTitle(mine, o, c.n) : T.popTitle(o, mine, c.n); };
    let budget = all ? Infinity : 20;
    chips.forEach(ch => {
      if (budget <= 0) return;
      const h = document.createElement('h3'), ul = document.createElement('ul');
      h.textContent = chips.length > 1 ? title(ch) : title(first);
      ch.rels.slice(0, budget).forEach(r => {
        const li = document.createElement('li'), b = document.createElement('button'), c = NODE.get(r.child), p = NODE.get(r.parent);
        b.type = 'button'; b.textContent = `${c.name}${r.col ? '.' + r.col : ''} → ${p.name}`;
        if (!model.boxes.has(r.otherId)) {
          b.disabled = true;
          li.append(b, Object.assign(document.createElement('small'), { textContent: T.popOut }));
        } else { b.onclick = () => { select(r.otherId, true); }; li.append(b); }
        ul.append(li);
      });
      budget -= Math.min(budget, ch.rels.length);
      parts.push(h, ul);
    });
    if (!all && total > 20) {
      const more = document.createElement('button');
      more.type = 'button'; more.textContent = T.all(total); more.onclick = () => { openPop(list, true); pop.querySelector('ul button')?.focus(); };
      parts.push(more);
    }
    const label = chips.length > 1 ? T.popSide(mine, total) : title(first);
    pop.replaceChildren(close, ...parts); pop.hidden = false; pop.setAttribute('aria-label', label);
    const at = units.find(u => u.chips[0] === list[0]) || first, ax = at.x - (at.chips ? 0 : 0), ay = at.y;
    pop.style.setProperty('--px', Math.min(Math.max(8, ax * view().k + view().tx), Math.max(8, stage.clientWidth - 330)) + 'px');
    pop.style.setProperty('--py', Math.min(Math.max(8, ay * view().k + view().ty + 16), Math.max(8, stage.clientHeight - 120)) + 'px');
  }
  function closePop(focus) {
    const list = state.pop;
    state.pop = null; pop.hidden = true; pop.replaceChildren();
    const j = list ? units.findIndex(u => u.chips.includes(list[0])) : -1;
    if (focus && j >= 0 && chipsEl.children[j]) chipsEl.children[j].focus();
  }

  // --- sticky lane headers (HTML, never exported)
  function syncHeads(v) {
    const el = $s('heads');
    if (!v || !model) return el.replaceChildren();
    const parts = [];
    const topOff = model.showCols && v.y0 > model.top, leftOff = model.showRows && v.x0 > 0;
    if (topOff) model.columns.forEach(c => {
      const x = c.x * v.k + v.tx, w = c.w * v.k;
      if (x + w < 0 || x > box.clientWidth) return;
      const d = document.createElement('div');
      d.className = 'colhead'; d.textContent = `${c.label} ${num(c.n)}`; d.title = d.textContent;
      d.style.left = Math.max(0, x) + 'px'; d.style.width = Math.max(0, Math.min(w, x + w, box.clientWidth - Math.max(0, x))) + 'px';
      parts.push(d);
    });
    if (leftOff) model.rows.forEach(r => {
      const y0 = r.y * v.k + v.ty, y1 = (r.y + r.h) * v.k + v.ty;
      if (y1 < 0 || y0 > box.clientHeight) return;
      const d = document.createElement('div'), dot = document.createElement('i');
      d.className = 'rowhead'; d.title = `${r.label} ${num(r.n)}`;
      d.append(paintDot(dot, r.color), document.createTextNode(r.label));
      d.style.top = Math.max(y0, topOff ? 28 : 0) + 4 + 'px';
      parts.push(d);
    });
    el.replaceChildren(...parts);
  }

  // --- minimap (a canvas, never exported)
  const miniEl = $s('mini');
  const miniSize = () => (stage.clientWidth < 900 ? [140, 94] : [180, 120]);
  function buildMini() {
    const [mw, mh] = miniSize(), s = Math.min(mw / model.W, mh / model.H), c = document.createElement('canvas');
    c.width = Math.max(1, Math.floor(model.W * s)); c.height = Math.max(1, Math.floor(model.H * s));
    const g = c.getContext('2d');
    model.rows.forEach(r => { g.fillStyle = CONTRAST.edge(r.color, THEME.bg); g.globalAlpha = 0.12; g.fillRect(0, r.y * s, c.width, r.h * s); });
    g.globalAlpha = 1;
    model.boxes.forEach(b => { g.fillStyle = (model.kinds.get(b.kind) || {}).color || '#999'; g.fillRect(b.x * s, b.y * s, Math.max(1, b.w * s), Math.max(1, b.h * s)); });
    mini = { canvas: c, s };
  }
  function syncMini(v) {
    const hidden = !v || !model || !mini || stage.clientWidth < 600 || (v.x0 <= 0 && v.y0 <= 0 && v.x0 + v.w >= model.W && v.y0 + v.h >= model.H);
    miniEl.hidden = hidden;
    if (hidden) return;
    const { canvas, s } = mini, dpr = window.devicePixelRatio || 1;
    miniEl.width = canvas.width * dpr; miniEl.height = canvas.height * dpr;
    miniEl.style.width = canvas.width + 'px'; miniEl.style.height = canvas.height + 'px';
    const g = miniEl.getContext('2d');
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, canvas.width, canvas.height);
    g.drawImage(canvas, 0, 0);
    const x = Math.max(0, v.x0) * s, y = Math.max(0, v.y0) * s, w = Math.min(model.W, v.x0 + v.w) * s - x, h = Math.min(model.H, v.y0 + v.h) * s - y;
    g.lineWidth = 3; g.strokeStyle = '#ffffff'; g.strokeRect(x, y, w, h);
    g.lineWidth = 2; g.strokeStyle = LOOK.accent; g.strokeRect(x, y, w, h);
  }
  miniEl.addEventListener('pointerdown', ev => {
    ev.preventDefault(); ev.stopPropagation();
    miniEl.setPointerCapture(ev.pointerId);
    const go = e => {
      const r = miniEl.getBoundingClientRect(), v = view(), wx = (e.clientX - r.left) / mini.s, wy = (e.clientY - r.top) / mini.s;
      zv.set({ x: box.clientWidth / 2 - wx * v.k, y: box.clientHeight / 2 - wy * v.k, k: v.k });
    };
    go(ev);
    miniEl.onpointermove = go;
    miniEl.onpointerup = miniEl.onpointercancel = () => { miniEl.onpointermove = null; };
  });

  // --- selection, hover, tooltip
  const selectedLive = n => {
    const rels = RELS.filter(([c, p]) => c !== p), kind = KIND.get(n.kind);
    return T.liveSelect(n.name, labelOf(kind), labelOf(DOM.get(n.domain)) + ' · ' + labelOf(LAY.get(n.layer)), n.cols.filter(c => c[2]).length,
      rels.filter(([c]) => c === n.id).length, rels.filter(([, p]) => p === n.id).length);
  };
  function select(id, framed) {
    state.selected = id;
    const n = id && NODE.get(id);
    if (n) { $s('q').value = n.name; say(selectedLive(n)); if (framed) frame(id); }
    renderCrumbs(); paint();
  }
  function tipFor(el) {
    const node = el.closest('g.node');
    if (node) {
      const n = NODE.get(node.id), d = DETAIL.entity(n.id);
      return { id: n.id, html: tableTip(DATA, n) + tableDesc(n, d && d.description) };
    }
    const edge = el.closest('g.edge');
    if (edge) {
      const e = model.edges[+edge.id.slice(1)];
      return { id: null, html: `<b>${esc(NODE.get(e.child).name)}${e.col ? '.' + esc(e.col) : ''} → ${esc(NODE.get(e.parent).name)}</b>` };
    }
    return null;
  }
  box.addEventListener('mousemove', ev => {
    if (!model || ev.buttons) return;
    const hit = tipFor(ev.target);
    if (!hit) { tip.style.display = 'none'; if (state.hover) { state.hover = null; repaint(); } return; }
    tip.innerHTML = hit.html; tip.style.display = 'block'; placeTooltip(tip, stage, ev);
    if (hit.id !== state.hover && layer.childElementCount < 3000) { state.hover = hit.id; repaint(); }
  });
  box.addEventListener('mouseleave', () => { tip.style.display = 'none'; if (state.hover) { state.hover = null; repaint(); } });
  // a tap or click selects: taken on pointer up (a repaint between press and release replaces the elements, and no `click`
  // is sent then), unless the pointer moved (a pan)
  let press = null;
  box.addEventListener('pointerdown', ev => { press = ev.button ? null : { x: ev.clientX, y: ev.clientY }; });
  box.addEventListener('pointerup', ev => {
    if (!model || !press || !ev.target.closest) return;
    const moved = Math.hypot(ev.clientX - press.x, ev.clientY - press.y) > 3, node = ev.target.closest('g.node');
    press = null;
    if (moved) return;
    if (node) select(node.id);
    else if (state.selected) select(null);
  });

  // --- search
  function findNode(text) {
    const s = text.trim().toLowerCase();
    return nodes.find(n => n.name.toLowerCase() === s || n.id.toLowerCase() === s || `${n.name} · ${n.id}`.toLowerCase() === s);
  }
  function fillTables() {
    const dup = new Set(), seen = new Set();
    nodes.forEach(n => { (seen.has(n.name) ? dup : seen).add(n.name); });
    $s('tables').replaceChildren(...nodes.map(n => Object.assign(document.createElement('option'), { value: dup.has(n.name) ? `${n.name} · ${n.id}` : n.name })));
  }
  function submitSearch() {
    const text = $s('q').value;
    if (!text.trim()) return;
    const n = findNode(text);
    if (n) { $s('q').title = ''; showMiss(''); select(n.id, true); }
    else { $s('q').title = T.notInScope(text); showMiss(T.notInScope(text)); say(T.notInScope(text)); }
  }
  // a search miss, also in plain sight next to the stage's top (the live region says it to screen readers)
  let missTimer = 0;
  function showMiss(text) {
    const el = $s('miss');
    clearTimeout(missTimer);
    el.textContent = text; el.hidden = !text;
    if (text) missTimer = setTimeout(() => showMiss(''), 8000);
  }
  $s('q').addEventListener('input', () => showMiss(''));
  $s('q').addEventListener('change', submitSearch);
  $s('q').addEventListener('keydown', ev => { if (ev.key === 'Enter') submitSearch(); });

  // --- keys, Esc
  const shownTab = () => document.getElementById('tab-schema').classList.contains('on');
  box.addEventListener('keydown', ev => {
    if (!zv || ev.altKey || ev.ctrlKey || ev.metaKey) return;
    const v = view(), page = box.clientHeight * 0.9, pageX = box.clientWidth * 0.9, STEP = 40;
    const moves = {
      ArrowUp: () => zv.by(0, -STEP), ArrowDown: () => zv.by(0, STEP), ArrowLeft: () => zv.by(-STEP, 0), ArrowRight: () => zv.by(STEP, 0),
      PageUp: () => (ev.shiftKey ? zv.by(-pageX, 0) : zv.by(0, -page)), PageDown: () => (ev.shiftKey ? zv.by(pageX, 0) : zv.by(0, page)),
      Home: () => zv.set({ x: 0, y: 0, k: v.k }), End: () => zv.set({ x: box.clientWidth - model.W * v.k, y: box.clientHeight - model.H * v.k, k: v.k }),
      '+': () => zv.scale(1.15), '=': () => zv.scale(1.15), '-': () => zv.scale(1 / 1.15), _: () => zv.scale(1 / 1.15), 0: () => fitAll(),
    };
    if (!moves[ev.key]) return;
    ev.preventDefault();
    moves[ev.key]();
  });
  const fitAll = () => { if (zv) zv.fit(); };
  $s('fit').onclick = fitAll;
  document.addEventListener('keydown', ev => {
    if (ev.key !== 'Escape' || !shownTab() || ev.defaultPrevented || ev.target.closest('input, select, textarea, dialog')) return;
    if (state.pop !== null) { collapse(state.pop); closePop(true); syncChips(view()); paint(); }
    else if (state.selected) select(null);
    else if (state.scope.kind !== 'all') setScope({ kind: 'all' });
    else return;
    ev.preventDefault();
  });
  window.addEventListener('resize', () => { if (zv && model) { onZoom(); } });
  new ResizeObserver(() => { if (zv && model && stage.clientWidth) { buildMini(); onZoom(); } }).observe(stage);
  sidePanel('s', () => { if (zv && model) onZoom(); });

  // the Print dialog (print.js, D-095): reads the scope, the level and the project's relations, saves nothing
  const printer = startPrint({ DATA, rels: RELS, relColumns: DETAIL.relationColumns, button: printBtn, say,
    nodes: () => nodes, level: () => state.level, scopeName, scope: () => state.scope, ready: () => !!model });
  fillScope();
  rebuild();
  return {
    // the tab became visible again: the filters may have changed in the Universe tab
    shown() {
      syncFilters();
      if (state.scope.kind === 'filter') {
        const ids = access.passingIds() || [], key = ids.join(',');
        if (key !== filterKey) { filterKey = key; state.scope = { kind: 'filter', ids }; rebuild(); }
      }
      if (zv && model) onZoom();
    },
    relayout() {},
    // follow the universe's location (D-089): an entered domain or layer preselects its scope, a selected table is framed
    follow(loc) {
      if (!loc) return;
      const scope = loc.inside ? parseScope(`${loc.by === 'layers' ? 'layer' : 'domain'}:${loc.inside}`) : { kind: 'all' };
      setScope(scope, loc.table);
    },
    sheet: () => model,
    view: () => ({ scope: state.scope, level: state.level, form: emitted ? emitted.form : null, k: zv ? zv.get().k : null,
      rendered: layer ? [...layer.querySelectorAll('g.node')].map(g => g.id) : [], selected: state.selected, expanded: [...state.expanded], pop: state.pop }),
    svgImage: scale => svgImage(box, zv, scale),
    perf: () => ({ ...perf }),
    // for the tests: the scope's tables, and a scope / selection / frame set from outside
    nodes: () => nodes.map(n => n.id),
    zoom: () => zv,
    print: printer,
  };
}
