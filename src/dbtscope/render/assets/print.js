// Print (M9.5, D-095, D-096): the Schema sheet on paper. Three parts, as schema.js: the plan (pure: the physical size of a sheet at a
// minimum text size, the papers, the tiles, the index), the document (pure: the pages as HTML / inline SVG, drawn by schema.js `sheetSvg`,
// the one emitter) and the dialog controller (`startPrint`). Page-wide declarations like schema.js; reads `S`, `LOOK`, `sheetModel`,
// `sheetSvg`, `kindTags`, `textW` at call time. Nothing here is saved (D-013), nothing but names, types and counts is printed (invariant 8).

const PRINT = {
  // portrait mm; a named paper is turned by the orientation
  PAPERS: { A4: [210, 297], A3: [297, 420], A2: [420, 594], A1: [594, 841], A0: [841, 1189] },
  FLOOR: 7, FLOOR_MIN: 5, FLOOR_MAX: 14,        // the minimum text size, pt: default and bounds
  MARGIN: 10, OVERLAP: 10, BAND: 24,            // mm: the band office printers cannot print in; the tiles' shared strip; a poster's title block
  // a PDF page side: Acrobat and most viewers stop at 14,400 pt = 200 in (PDF 1.x); Chromium's writer itself does not clamp (measured: pages
  // of 200 m are written with their true MediaBox), so the limit is the viewers' and a poster longer than this is not offered (D-095)
  MAX_SIDE: 5080, MIN_SIDE: 100, MIN_FIT: 120,  // mm; MIN_FIT: the narrowest fitted paper's drawing area, so the title and legend have room
  ALL_MAX: 300,                                 // the most tables whose all columns are offered outside a domain
  INDEX_FONT: 8, TITLE_FONT: 18, INFO_FONT: 9, FURNITURE_FONT: 7, NAME_FONT: 14, MAP_FONT: 8, // pt
  CROP: 4, TICK: 3, LEGEND_LINE: 26,
  EDGE: 5.5,   // mm: no furniture closer than this to a paper edge (office printers cannot print there); baselines and hints follow it
};
const PT_MM = 25.4 / 72;                        // mm per pt
const PX_MM = 96 / 25.4;                        // CSS px per mm
// mm of paper per sheet unit at which the smallest sheet text (a row, 11 u) is exactly `floor` pt: 7 pt -> 0.2245 mm
const mmPerUnit = floor => floor / S.ROW_FONT * PT_MM;
// "A1", "B3", "AA12": the column as letters (A..Z, AA..), the row as a number, both counted from the sheet's top left
function tileName(i, j) {
  let letters = '', n = i + 1;
  while (n > 0) { letters = String.fromCharCode(65 + (n - 1) % 26) + letters; n = Math.floor((n - 1) / 26); }
  return letters + (j + 1);
}
const NB = PAGE.lang === 'fr' ? '\u00a0' : ' ';
const PT = {
  en: {
    title: 'Print the schema', scopeLine: (name, n) => `${name} · ${plural(n, L.tables)}`, show: 'Show', floor: 'Minimum text size (pt)', floorUnit: 'pt',
    output: 'Output', oneSheet: 'One sheet', tiles: 'Tiles', paper: 'Paper', fitted: 'Fitted to the drawing', custom: 'Custom',
    widthMm: 'Width (mm)', heightMm: 'Height (mm)', orientation: 'Orientation', portrait: 'Portrait', landscape: 'Landscape',
    customErr: `Each side is between ${num(PRINT.MIN_SIDE)} and ${num(PRINT.MAX_SIDE)} mm`, floorErr: 'Between 5 and 14 pt',
    fittedFollows: 'The fitted paper follows the drawing', tilesNeedPaper: 'Tiles need a paper size', notPossible: 'Not possible: ',
    needs: (scope, level, dims, floor, area) => `${scope} with ${level} needs ${dims} at ${floor}${area}.`,
    oneSheetOf: dims => `One sheet of ${dims} (margins and title included)`,
    fitsOn: (paper, font) => `Fits on one ${paper} sheet at ${font}.`,
    tooSmall: (paper, font, floor) => `On one ${paper} sheet the text would be ${font}, under ${floor}: choose Tiles or the fitted paper.`,
    tooLong: (len, max) => `This sheet would be ${len} long; a PDF page stops at ${max}: choose Tiles, a smaller text size or a domain.`,
    tileCount: (nc, nr, paper, sheets, blank, index) => `${nc} × ${nr} tiles of ${paper}: ${plural(sheets, ['sheet', 'sheets'])} to print${blank ? ` (${num(blank)} blank skipped)` : ''}, plus ${plural(index, ['index page', 'index pages'])}`,
    recommend: (floor, paper) => `Smallest single sheet at ${floor}: ${paper}`,
    noneFits: (floor, width) => `No A-size sheet holds it at ${floor}: a print shop roll of ${width} width, or tiles`,
    allWhy: 'All columns print one domain at a time: choose a domain as the scope',
    printHint: 'In the print window choose Save as PDF or your printer, margins None, scale 100 %.',
    schemaOf: d => `Schema of ${d}`, printedOn: d => `Printed ${d}`, minText: f => `minimum text ${f}`,
    legend: 'Legend', tablesIndex: 'Tables and their tile', assembly: 'Assembly',
    ready: n => `Print document ready: ${plural(n, ['page', 'pages'])}`, calculating: 'Calculating…', preparing: 'Preparing…', cancel: 'Cancel', print: 'Print',
    keyRow: 'key column', keyHidden: 'columns not shown at this level', keyFk: 'foreign key side (the referencing table)',
    keyPk: 'key side (the referenced table)', keyChip: 'relations to another lane, counted, not drawn',
    keyOut: 'dashed: relations to tables outside this scope', keyLanes: 'columns: layers in data-flow order · rows: domains',
    drawingSize: (floor, dims, nc, nr, paper, orient, o) => `Minimum text ${floor} · drawing ${dims} · ${nc} × ${nr} tiles of ${paper} ${orient}, ${o} overlap`,
    hatched: 'Hatched: not printed (empty)', tileLoc: (title, scope, tile, c, nc, r, nr, page, pages) => `${title} · ${scope} · ${tile} (column ${c} of ${nc}, row ${r} of ${nr}) · page ${page} of ${pages}`,
    indexHead: (a, b) => `Tables and their tile: ${a} to ${b}`, indexFoot: (i, n, page, pages) => `Index page ${i} of ${n} · page ${page} of ${pages}`,
    sheetPage: (page, pages) => `page ${page} of ${pages}`,
  },
  fr: {
    title: 'Imprimer le schéma', scopeLine: (name, n) => `${name} · ${plural(n, L.tables)}`, show: 'Afficher', floor: 'Taille de texte minimale (pt)', floorUnit: 'pt',
    output: 'Sortie', oneSheet: 'Une seule feuille', tiles: 'Mosaïque', paper: 'Papier', fitted: 'Ajusté au dessin', custom: 'Personnalisé',
    widthMm: 'Largeur (mm)', heightMm: 'Hauteur (mm)', orientation: 'Orientation', portrait: 'Portrait', landscape: 'Paysage',
    customErr: `Chaque côté mesure entre ${num(PRINT.MIN_SIDE)} et ${num(PRINT.MAX_SIDE)}\u00a0mm`, floorErr: 'Entre 5 et 14\u00a0pt',
    fittedFollows: 'Le format ajusté suit le dessin', tilesNeedPaper: 'La mosaïque demande un format de papier', notPossible: 'Impossible\u00a0: ',
    needs: (scope, level, dims, floor, area) => `${scope} avec ${level} demande ${dims} à ${floor}${area}.`,
    oneSheetOf: dims => `Une seule feuille de ${dims} (marges et titre compris)`,
    fitsOn: (paper, font) => `Tient sur une feuille ${paper} à ${font}.`,
    tooSmall: (paper, font, floor) => `Sur une feuille ${paper} le texte ferait ${font}, sous ${floor}\u00a0: choisissez la mosaïque ou le format ajusté.`,
    tooLong: (len, max) => `Cette feuille mesurerait ${len}\u202f; une page PDF s'arrête à ${max}\u00a0: choisissez la mosaïque, un texte plus petit ou un domaine.`,
    tileCount: (nc, nr, paper, sheets, blank, index) => `${nc} × ${nr} tuiles ${paper}\u00a0: ${plural(sheets, ['feuille', 'feuilles'])} à imprimer${blank ? ` (${num(blank)} vides omises)` : ''}, plus ${plural(index, ['page d\'index', 'pages d\'index'])}`,
    recommend: (floor, paper) => `Plus petite feuille unique à ${floor}\u00a0: ${paper}`,
    noneFits: (floor, width) => `Aucun format A ne le contient à ${floor}\u00a0: un rouleau d'imprimeur de ${width} de large, ou la mosaïque`,
    allWhy: 'Toutes les colonnes s\'impriment domaine par domaine\u00a0: choisissez un domaine comme périmètre',
    printHint: 'Dans la fenêtre d\'impression, choisissez Enregistrer au format PDF ou votre imprimante, marges Aucune, échelle 100\u00a0%.',
    schemaOf: d => `Schéma du ${d}`, printedOn: d => `Imprimé le ${d}`, minText: f => `texte minimal ${f}`,
    legend: 'Légende', tablesIndex: 'Tables et leur tuile', assembly: 'Assemblage',
    ready: n => `Document d'impression prêt\u00a0: ${plural(n, ['page', 'pages'])}`, calculating: 'Calcul…', preparing: 'Préparation…', cancel: 'Annuler', print: 'Imprimer',
    keyRow: 'colonne clé', keyHidden: 'colonnes non affichées à ce niveau', keyFk: 'côté clé étrangère (la table qui référence)',
    keyPk: 'côté clé (la table référencée)', keyChip: 'relations vers un autre couloir, comptées, non tracées',
    keyOut: 'pointillé\u00a0: relations vers des tables hors de ce périmètre', keyLanes: 'colonnes\u00a0: couches dans l\'ordre du flux · lignes\u00a0: domaines',
    drawingSize: (floor, dims, nc, nr, paper, orient, o) => `Texte minimal ${floor} · dessin ${dims} · ${nc} × ${nr} tuiles ${paper} ${orient}, recouvrement ${o}`,
    hatched: 'Hachuré\u00a0: non imprimé (vide)', tileLoc: (title, scope, tile, c, nc, r, nr, page, pages) => `${title} · ${scope} · ${tile} (colonne ${c} sur ${nc}, ligne ${r} sur ${nr}) · page ${page} sur ${pages}`,
    indexHead: (a, b) => `Tables et leur tuile\u00a0: ${a} à ${b}`, indexFoot: (i, n, page, pages) => `Page d'index ${i} sur ${n} · page ${page} sur ${pages}`,
    sheetPage: (page, pages) => `page ${page} sur ${pages}`,
  },
}[PAGE.lang];

// ---------------------------------------------------------------- numbers, text and dates (pure)
const withUnit = (v, unit) => `${v}${NB}${unit}`;
const ptText = v => withUnit(num(Math.round(v * 10) / 10), 'pt');
// the size of a drawing: one unit for both sides, chosen by the longer: metres with two decimals (and the area) from one metre, else whole centimetres
function sizeText(wMm, hMm) {
  if (Math.max(wMm, hMm) >= 1000) {
    return { dims: `${withUnit(num(wMm / 1000, 2), 'm')} × ${withUnit(num(hMm / 1000, 2), 'm')}`, plain: `${num(wMm / 1000, 2)} × ${withUnit(num(hMm / 1000, 2), 'm')}`,
      area: ` (${withUnit(num(wMm * hMm / 1e6, 2), 'm²')})` };
  }
  return { dims: `${withUnit(num(Math.round(wMm / 10)), 'cm')} × ${withUnit(num(Math.round(hMm / 10)), 'cm')}`, plain: `${num(Math.round(wMm / 10))} × ${withUnit(num(Math.round(hMm / 10)), 'cm')}`, area: '' };
}
const lengthText = mm => (mm >= 1000 ? withUnit(num(mm / 1000, 2), 'm') : withUnit(num(Math.round(mm / 10)), 'cm'));
// the width of `text` in mm at `pt` points in the sheet's font, and the text cut with an ellipsis to fit `widthMm`
const textMm = (text, pt, weight) => textW(text, pt * 96 / 72, weight) / PX_MM;
const fitText = (text, widthMm, pt, weight) => ellipsis(text, widthMm * PX_MM, fontOf(pt * 96 / 72, weight));
// the words of `parts` (joined by " · ") on as few lines as fit `widthMm`
function wrapParts(parts, widthMm, pt) {
  const lines = [''];
  parts.forEach(p => {
    const line = lines[lines.length - 1], next = line ? `${line} · ${p}` : p;
    if (!line || textMm(next, pt) <= widthMm) lines[lines.length - 1] = next; else lines.push(p);
  });
  return lines.map(l => fitText(l, widthMm, pt));
}
// "YYYY-MM-DD..." read from the manifest's own timestamp, written in the page language; '' when it cannot be read (no clock, no parsing of more)
function schemaDate(generatedAt) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(typeof generatedAt === 'string' ? generatedAt : '');
  if (!m) return '';
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  if (d.getUTCMonth() !== +m[2] - 1 || d.getUTCDate() !== +m[3]) return '';
  return new Intl.DateTimeFormat(PAGE.lang, { dateStyle: 'long', timeZone: 'UTC' }).format(d);
}
const printedDate = date => new Intl.DateTimeFormat(PAGE.lang, { dateStyle: 'long' }).format(date);
const paperName = paper => (PRINT.PAPERS[paper.key] ? paper.key : `${num(paper.w)} × ${num(paper.h)}${NB}mm`);
// the Show level's label, from the one list of the page (common.js LEVELS)
const levelLabel = level => new Map(LEVELS()).get(level);
const orientName = o => (o === 'landscape' ? PT.landscape : PT.portrait).toLowerCase();

// ---------------------------------------------------------------- the legend (pure): the marks of the sheet and what they mean
// The legend of a sheet as markup in sheet units, wrapped to `widthU`: { h, svg }. Drawn with the sheet's own marks at the sheet's own text size.
function legendLayout(model, widthU) {
  const LH = PRINT.LEGEND_LINE, GAP = 20, items = [], tags = model.tags, ink = LOOK.ink;
  const text = (x, y, body, extra = '', fill = ink) => `<text x="${rounded(2, x)}" y="${rounded(2, y + 4)}" font-size="${S.ROW_FONT}" fill="${fill}"${extra}>${esc(body)}</text>`;
  const counts = new Map(), labels = new Map(PAGE.universe.kinds.map(k => [k.key, labelOf(k)]));
  model.boxes.forEach(b => counts.set(b.kind, (counts.get(b.kind) || 0) + 1));
  model.kinds.forEach((st, key) => {
    const n = counts.get(key);
    if (!n) return;
    const tag = (tags && tags.get(key)) || '', label = labels.get(key) ?? key, sw = Math.max(24, textW(tag, S.ROW_FONT, 600) + 12), count = num(n);
    items.push({ w: sw + 6 + textW(label, S.ROW_FONT) + 5 + textW(count, S.ROW_FONT, 600), draw: (x, y) => `<rect x="${rounded(2, x)}" y="${y - 8}" width="${rounded(2, sw)}" height="16" fill="${st.color}" stroke="${st.edge}" stroke-width="1"/>`
      + (tag ? text(x + sw / 2, y, tag, ' font-weight="600" text-anchor="middle"', st.head) : '')
      + `<text x="${rounded(2, x + sw + 6)}" y="${y + 4}" font-size="${S.ROW_FONT}" fill="${ink}">${esc(label)}<tspan dx="5" font-weight="600">${esc(count)}</tspan></text>` });
  });
  const key = (gw, glyph, label) => items.push({ w: gw + 6 + textW(label, S.ROW_FONT), draw: (x, y) => glyph(x, y) + text(x + gw + 6, y, label) });
  const anyRows = [...model.boxes.values()].some(b => b.rows.length), anyNote = [...model.boxes.values()].some(b => b.note);
  const anyEdge = model.edges.some(e => e.drawn), chip = model.chips.find(c => !c.out) || model.chips[0], outChip = model.chips.find(c => c.out);
  if (anyRows) key(textW('id', S.ROW_FONT, 600), (x, y) => text(x, y, 'id', ' font-weight="600"'), PT.keyRow);
  if (anyNote) { const sample = `+ ${plural(5, L.columns)}`; key(textW(sample, S.ROW_FONT, 400, true), (x, y) => text(x, y, sample, ' font-style="italic"', LOOK.muted), PT.keyHidden); }
  const edge = x => ({ s1: 1, s2: -1, x1: x, y1: 0, x2: x + 32, y2: 0, bow: 0 });
  const rel = (y, e, parts) => `<g transform="translate(0 ${y})">${parts(relationPath(e, false))}</g>`;
  if (anyEdge) {
    key(32, (x, y) => rel(y, edge(x), p => `<path d="${p.line}" fill="none" stroke="${LOOK.edge}" stroke-width="${LOOK.edgeW}"/>`), PT.keyFk);
    key(32, (x, y) => rel(y, edge(x), p => `<path d="${p.main}" fill="none" stroke="${LOOK.edge}" stroke-width="${LOOK.edgeW}"/><path d="${p.head}" fill="${LOOK.edge}"/>`), PT.keyPk);
  }
  const pill = (c, dash) => { const t = `${c.label}  ${c.count}`, gw = Math.ceil(textW(t, S.ROW_FONT) + 2 * S.PAD_X + 4); return { gw, draw: (x, y) => `<rect x="${rounded(2, x)}" y="${y - 10}" width="${gw}" height="20" rx="10" fill="${LOOK.surface}" stroke="${LOOK.chipBorder}" stroke-width="1"${dash ? ' stroke-dasharray="4 3"' : ''}/>${text(x + 10, y, t)}` }; };
  if (chip && !chip.out) { const p = pill(chip, false); key(p.gw, p.draw, PT.keyChip); }
  if (outChip) { const p = pill(outChip, true); key(p.gw, p.draw, PT.keyOut); }
  if (model.showCols || model.showRows) items.push({ w: textW(PT.keyLanes, S.ROW_FONT), draw: (x, y) => text(x, y, PT.keyLanes) });
  let x = 0, line = 0;
  const out = items.map(it => {
    if (x > 0 && x + it.w > widthU) { line++; x = 0; }
    const svg = it.draw(x, line * LH + LH / 2);
    x += it.w + GAP;
    return svg;
  });
  return { h: (line + 1) * LH, svg: out.join('') };
}

// ---------------------------------------------------------------- the head of a one-sheet page (pure): title, info lines, legend
function headLayout(model, aw, floor, meta) {
  const tf = Math.max(PRINT.TITLE_FONT, 2.5 * floor), inf = Math.max(PRINT.INFO_FONT, floor), su = inf * PT_MM / S.ROW_FONT;
  const parts = [meta.scope, levelLabel(model.level), PT.minText(ptText(floor))];
  const dated = schemaDate(meta.generated);
  if (dated) parts.push(PT.schemaOf(dated));
  parts.push(PT.printedOn(printedDate(meta.printed)));
  const info = wrapParts(parts, aw, inf), lh = inf * PT_MM * 1.35, titleH = tf * PT_MM * 1.25;
  const headH = Math.max(PRINT.BAND, titleH + 1.5 + info.length * lh + 1.5), legend = legendLayout(model, aw / su);
  return { tf, inf, su, title: fitText(meta.title, aw, tf, 600), titleH, info, lh, headH, legend, legendH: legend.h * su, band: headH + legend.h * su + 3 };
}

// ---------------------------------------------------------------- the plan (pure)
// The segments the drawing holds, as arrays of points (relations: drawn ones only), for deciding which tile is blank
function contentOf(model) {
  const rects = [], lines = [];
  model.boxes.forEach(b => rects.push([b.x, b.y, b.w, b.h]));
  model.chips.forEach(c => rects.push([c.x, c.y, c.w, c.h]));
  if (model.showCols) model.columns.forEach(c => rects.push([c.x, 0, c.w, S.TITLE_H]));
  if (model.showRows) model.rows.forEach(r => rects.push([0, r.y, model.headW, 24 + (r.lines.length + 1) * 16]));
  model.edges.forEach(e => {
    if (!e.drawn) return;
    if (!e.bow) return lines.push([[e.x1, e.y1], [e.x2, e.y2]]);
    const pts = [];
    for (let i = 0; i <= 8; i++) {   // the cubic M x1 y1 C bow y1 bow y2 x2 y2
      const t = i / 8, a = (1 - t) ** 3, b = 3 * (1 - t) ** 2 * t, c = 3 * (1 - t) * t * t, d = t ** 3;
      pts.push([a * e.x1 + (b + c) * e.bow + d * e.x2, (a + b) * e.y1 + (c + d) * e.y2]);
    }
    lines.push(pts);
  });
  return { rects, lines };
}
// does the segment (x0, y0)-(x1, y1) meet the rectangle? (Liang-Barsky)
function segmentMeets(x0, y0, x1, y1, r) {
  let t0 = 0, t1 = 1;
  const dx = x1 - x0, dy = y1 - y0;
  for (const [p, q] of [[-dx, x0 - r.x], [dx, r.x + r.w - x0], [-dy, y0 - r.y], [dy, r.y + r.h - y0]]) {
    if (p === 0) { if (q < 0) return false; } else {
      const t = q / p;
      if (p < 0) { if (t > t1) return false; t0 = Math.max(t0, t); } else { if (t < t0) return false; t1 = Math.min(t1, t); }
    }
  }
  return t0 <= t1;
}
const meetsContent = (content, r) => content.rects.some(([x, y, w, h]) => x < r.x + r.w && x + w > r.x && y < r.y + r.h && y + h > r.y)
  || content.lines.some(pts => pts.some((p, i) => i && segmentMeets(pts[i - 1][0], pts[i - 1][1], p[0], p[1], r)));

// The paper of a choice: { key, w, h, orientation } in mm (w, h null for the fitted paper, known once the drawing is), valid or not
function paperOf(opts) {
  const orientation = opts.orientation === 'landscape' ? 'landscape' : 'portrait', key = opts.paper || 'fitted';
  if (key === 'fitted') return { key, w: null, h: null, orientation, valid: true };
  const named = PRINT.PAPERS[key], [a, b] = key === 'custom' ? [Math.round(+opts.w), Math.round(+opts.h)] : named || PRINT.PAPERS.A4;
  const valid = key !== 'custom' || [a, b].every(v => v >= PRINT.MIN_SIDE && v <= PRINT.MAX_SIDE);   // NaN fails both comparisons
  const [short, long] = [Math.min(a, b), Math.max(a, b)];
  return { key: named || key === 'custom' ? key : 'A4', w: orientation === 'landscape' ? long : short, h: orientation === 'landscape' ? short : long, orientation, valid };
}
const PAPER_ORDER = Object.keys(PRINT.PAPERS);
// The smallest named paper, in either orientation, on which one sheet holds the scope at the floor: { key, orientation } or null
function recommendPaper(model, floor, meta) {
  const options = PAPER_ORDER.flatMap(key => ['portrait', 'landscape'].map(orientation => ({ key, orientation })));
  return options.find(o => onePage(model, floor, paperOf({ paper: o.key, orientation: o.orientation }), meta).fits) || null;
}
// One sheet on a paper: the paper, the head and the scale of the drawing. fits: the text is at least the floor.
function onePage(model, floor, paper, meta) {
  const mm = mmPerUnit(floor), m = PRINT.MARGIN, D = { w: model.W * mm, h: model.H * mm };
  if (paper.key === 'fitted') {
    const aw = Math.max(D.w, PRINT.MIN_FIT), head = headLayout(model, aw, floor, meta);
    const w = aw + 2 * m, h = D.h + head.band + 2 * m, long = Math.max(w, h);
    return { paper: { ...paper, w: rounded(2, w), h: rounded(2, h) }, head, scale: mm, font: floor, fits: long <= PRINT.MAX_SIDE, long, aw, ah: D.h };
  }
  const aw = paper.w - 2 * m, head = headLayout(model, aw, floor, meta), ah = paper.h - 2 * m - head.band;
  const scale = aw > 0 && ah > 0 ? Math.min(aw / model.W, ah / model.H) : 0, font = scale / mm * floor;
  return { paper, head, scale, font, fits: scale >= mm * (1 - 1e-9), long: Math.max(paper.w, paper.h), aw, ah };
}
// Which tile (i, j) holds the box's name: the tile whose step rectangle holds the point where the name reads (D-096)
const tileAt = (x, y, sx, sy, nc, nr) => [Math.min(nc - 1, Math.max(0, Math.floor(x / sx))), Math.min(nr - 1, Math.max(0, Math.floor(y / sy)))];

// The plan of a print (pure). model: a sheetModel (with tags); opts: { floor, mode: sheet | tiles, paper: fitted | A4.. | custom, w, h,
// orientation, meta: { title, scope, generated, printed } }. -> { floor, mmPerU, level, mode, paper, drawing: { w, h } (mm), scale (mm per unit used),
// font (pt of 11 u at that scale), fits, why, recommend, text: { size, verdict, recommend }, valid, band, head, tiles, cols, rows, printed, blank,
// index, indexLayout, indexPages, pages }. Never throws on a valid model.
function printPlan(model, opts) {
  const floor = Math.min(PRINT.FLOOR_MAX, Math.max(PRINT.FLOOR_MIN, Number.isFinite(+opts.floor) ? +opts.floor : PRINT.FLOOR)), mm = mmPerUnit(floor), mode = opts.mode === 'tiles' ? 'tiles' : 'sheet';
  const meta = opts.meta || { title: PAGE.title, scope: '', generated: null, printed: new Date() }, m = PRINT.MARGIN;
  const drawing = { w: model.W * mm, h: model.H * mm }, { dims, area } = sizeText(drawing.w, drawing.h);
  const levelWords = levelLabel(model.level);
  const recommend = recommendPaper(model, floor, meta);
  const plan = { floor, mmPerU: mm, level: model.level, mode, paper: paperOf(opts), drawing, scale: mm, font: floor, fits: false, why: '', valid: true,
    recommend, band: 0, head: null, tiles: [], cols: 0, rows: 0, printed: 0, blank: 0, index: [], indexLayout: null, indexPages: 0, pages: 0, meta,
    text: { size: PT.needs(meta.scope, levelWords, dims, ptText(floor), area), verdict: '', recommend: '' } };
  if (mode === 'sheet') plan.text.recommend = recommend ? PT.recommend(ptText(floor), `${recommend.key} ${orientName(recommend.orientation)}`)
    : PT.noneFits(ptText(floor), lengthText(Math.min(drawing.w, drawing.h) + 2 * m));
  const refuse = why => { plan.fits = false; plan.why = why; plan.text.verdict = PT.notPossible + why; return plan; };
  if (!plan.paper.valid) { plan.valid = false; return refuse(PT.customErr); }
  if (mode === 'tiles') {
    if (plan.paper.key === 'fitted') return refuse(PT.tilesNeedPaper);
    return tilePlan(model, plan, meta);
  }
  const page = onePage(model, floor, plan.paper, meta);
  Object.assign(plan, { paper: page.paper, head: page.head, band: page.head.band, scale: page.scale, font: page.font, pages: 1 });
  if (plan.paper.key === 'fitted') {
    if (!page.fits) return refuse(PT.tooLong(lengthText(page.long), lengthText(PRINT.MAX_SIDE)));
    plan.fits = true; plan.text.verdict = PT.oneSheetOf(sizeText(page.paper.w, page.paper.h).dims);
  } else if (page.fits) {
    plan.fits = true; plan.text.verdict = PT.fitsOn(paperName(plan.paper), ptText(page.font));
  } else return refuse(PT.tooSmall(paperName(plan.paper), ptText(page.font), ptText(floor)));
  return plan;
}
// The tiles of a plan (D-096): the grid, the blank tiles, the index of the tables, the index pages
function tilePlan(model, plan, meta) {
  const { mmPerU: mm } = plan, m = PRINT.MARGIN, o = PRINT.OVERLAP, { w, h } = plan.paper;
  const cw = w - 2 * m, ch = h - 2 * m, sx = cw - o, sy = ch - o, D = plan.drawing;
  const nc = Math.max(1, Math.ceil((D.w - o) / sx)), nr = Math.max(1, Math.ceil((D.h - o) / sy)), content = contentOf(model);
  for (let j = 0; j < nr; j++) for (let i = 0; i < nc; i++) {
    const step = { x: i * sx / mm, y: j * sy / mm, w: sx / mm, h: sy / mm };
    plan.tiles.push({ name: tileName(i, j), i, j, rect: { x: i * sx / mm, y: j * sy / mm, w: cw / mm, h: ch / mm }, step, blank: !meetsContent(content, step) });
  }
  plan.cols = nc; plan.rows = nr; plan.blank = plan.tiles.filter(t => t.blank).length; plan.printed = plan.tiles.length - plan.blank;
  const rank = (a, b) => (a.name.toLowerCase() > b.name.toLowerCase()) - (a.name.toLowerCase() < b.name.toLowerCase()) || (a.name > b.name) - (a.name < b.name) || (a.id > b.id) - (a.id < b.id);
  const dup = new Set(), seen = new Set();
  model.boxes.forEach(b => { (seen.has(b.name) ? dup : seen).add(b.name); });
  plan.index = [...model.boxes.values()].map(b => {
    const [i, j] = tileAt(b.x * mm, (b.y + S.HEAD_H / 2) * mm, sx, sy, nc, nr);
    return { id: b.id, name: b.name, tile: tileName(i, j), dup: dup.has(b.name) };
  }).sort(rank);
  plan.indexLayout = indexLayout(model, plan, meta);
  plan.indexPages = plan.indexLayout.pages.length;
  plan.pages = plan.indexPages + plan.printed;
  plan.fits = true;
  plan.text.verdict = PT.tileCount(num(nc), num(nr), paperName(plan.paper), plan.printed, plan.blank, plan.indexPages);
  return plan;
}

// The index pages (pure): the exact lines each holds, so the page count is known before printing (D-096). -> { pages: [{ from, to,
// y (list top, mm), lines, first }], cols, colW, gap, fi, lh, map, legend, head }
function indexLayout(model, plan, meta) {
  const m = PRINT.MARGIN, cw = plan.paper.w - 2 * m, ch = plan.paper.h - 2 * m, F = Math.max(PRINT.INDEX_FONT, plan.floor), fi = F * PT_MM, lh = 1.4 * fi;
  const tf = Math.max(PRINT.TITLE_FONT, 2.5 * plan.floor), titleH = tf * PT_MM * 1.25, su = F * PT_MM / S.ROW_FONT, gap = 6;
  const legend = legendLayout(model, cw / su), legendH = legend.h * su, D = plan.drawing;
  const sx = cw - PRINT.OVERLAP, sy = ch - PRINT.OVERLAP, EW = Math.max(plan.cols * sx, D.w), EH = Math.max(plan.rows * sy, D.h);
  const longest = Math.max(0, ...plan.index.map(e => textMm(e.name, F) + (e.dup ? textMm(` · ${e.id}`, F * 0.9) : 0) + textMm(e.tile, F, 600) + 4));
  const colW = Math.min(cw, Math.max(48, Math.min(longest, 56))), cols = Math.max(1, Math.floor((cw + gap) / (colW + gap)));
  const caption = plan.blank ? lh : 0;
  let y = titleH + 3 * lh + fi;
  const afterMap = y + lh + fi, rest = lh + legendH + fi + lh + 4 * lh + caption;
  const fit = reserve => Math.min(cw / EW, Math.max(0, Math.min(0.5 * ch, ch - afterMap - rest - reserve)) / EH);
  const denseAt = r0 => sx * r0 < 8 || sy * r0 < 8;
  let r = fit(0), axis = 0;
  if (denseAt(r)) { axis = PRINT.FURNITURE_FONT * PT_MM + 1.5; r = fit(axis); }   // a dense map names its tiles on axes above and left: room under the heading
  const mapW = EW * r, mapH = EH * r, map = { x: 0, y: afterMap + axis, axis, dense: axis > 0, w: mapW, h: mapH, r, EW, EH, sx, sy };
  y = afterMap + axis + mapH + (caption ? lh : 0) + fi;
  const legendY = y + lh;
  y = legendY + legendH + fi;
  const listY = y + lh, first = Math.max(0, Math.floor((ch - listY) / lh)), rest2 = Math.max(1, Math.floor((ch - 1.5 * lh) / lh)), pages = [];
  const n = plan.index.length;
  let from = 0;
  pages.push({ from: 0, to: Math.min(n, first * cols), y: listY, lines: first, first: true });
  from = pages[0].to;
  while (from < n) { pages.push({ from, to: Math.min(n, from + rest2 * cols), y: 1.5 * lh, lines: rest2, first: false }); from = pages[pages.length - 1].to; }
  return { pages, cols, colW, gap, fi, lh, F, tf, titleH, su, map, legend, legendY, legendH, caption };
}

// ---------------------------------------------------------------- the document (pure)
const pageSvg = (w, h, body) => `<svg xmlns="http://www.w3.org/2000/svg" width="${rounded(2, w)}mm" height="${rounded(2, h)}mm" viewBox="0 0 ${rounded(2, w)} ${rounded(2, h)}" font-family="${esc(LOOK.font)}">${body}</svg>`;
const section = (w, h, svg, extra = '') => `<section class="pp"${extra} style="width:${rounded(2, w)}mm;height:${rounded(2, h)}mm">${svg}</section>`;
const mtext = (x, y, pt, body, extra = '', fill = LOOK.ink) => `<text x="${rounded(2, x)}" y="${rounded(2, y)}" font-size="${rounded(3, pt * PT_MM)}" fill="${fill}"${extra}>${esc(body)}</text>`;

// The marks of a drawing at a print scale (px per unit): the screen's emitter, clean (no selection or hover), unique ids
const printMarks = scale => ({ k: scale * PX_MM, ids: false });
// A one-sheet page: title, info, legend, drawing
function posterPage(model, plan, meta) {
  const m = PRINT.MARGIN, { w, h } = plan.paper, head = plan.head, aw = w - 2 * m;
  const s = plan.scale, dw = model.W * s, dh = model.H * s, rect = { x: 0, y: 0, w: model.W, h: model.H };
  let y = m, body = mtext(m, y + head.tf * PT_MM, head.tf, head.title, ' font-weight="600"');
  y += head.titleH + 1.5;
  head.info.forEach((line, i) => { body += mtext(m, y + head.inf * PT_MM * 0.95 + i * head.lh, head.inf, line); });
  y = m + head.headH;
  body += `<svg class="legend" x="${m}" y="${rounded(2, y)}" width="${rounded(2, aw)}" height="${rounded(2, head.legendH)}" viewBox="0 0 ${rounded(2, aw / head.su)} ${rounded(2, head.legend.h)}">${head.legend.svg}</svg>`;
  y += head.legendH + 3;
  body += `<svg class="drawing" x="${rounded(2, m + (aw - dw) / 2)}" y="${rounded(2, y)}" width="${rounded(2, dw)}" height="${rounded(2, dh)}" viewBox="0 0 ${rounded(2, model.W)} ${rounded(2, model.H)}">${sheetSvg(model, rect, 'full', printMarks(s))}</svg>`;
  return section(w, h, pageSvg(w, h, body), ' data-page="sheet"');
}
// The furniture of a tile page: crop marks, overlap ticks, neighbours, name and place
function tileFurniture(plan, t, printedAt, pageNo) {
  const m = PRINT.MARGIN, o = PRINT.OVERLAP, { w, h } = plan.paper, cw = w - 2 * m, ch = h - 2 * m, hair = rounded(3, 0.25 * PT_MM), tickW = rounded(3, 0.5 * PT_MM);
  const line = (cls, x0, y0, x1, y1, sw) => `<path class="${cls}" d="M${rounded(2, x0)} ${rounded(2, y0)}L${rounded(2, x1)} ${rounded(2, y1)}" stroke="#000" stroke-width="${sw}" fill="none"/>`;
  let g = '';
  [[m, m, -1, -1], [m + cw, m, 1, -1], [m, m + ch, -1, 1], [m + cw, m + ch, 1, 1]].forEach(([cx, cy, dx, dy]) => {
    g += line('crop', cx + dx, cy, cx + dx * (1 + PRINT.CROP), cy, hair) + line('crop', cx, cy + dy, cx, cy + dy * (1 + PRINT.CROP), hair);
  });
  const at = (i, j) => (i < 0 || j < 0 || i >= plan.cols || j >= plan.rows ? null : plan.tiles[j * plan.cols + i]);
  const sides = [['up', 0, -1], ['down', 0, 1], ['left', -1, 0], ['right', 1, 0]];
  sides.forEach(([side, di, dj]) => {
    const n = at(t.i + di, t.j + dj);
    if (!n) return;
    const T0 = PRINT.TICK;
    if (side === 'left' || side === 'right') {
      const x = side === 'left' ? m + o : m + cw - o;
      g += line('tick', x, m - 1, x, m - 1 - T0, tickW) + line('tick', x, m + ch + 1, x, m + ch + 1 + T0, tickW);
    } else {
      const y = side === 'up' ? m + o : m + ch - o;
      g += line('tick', m - 1, y, m - 1 - T0, y, tickW) + line('tick', m + cw + 1, y, m + cw + 1 + T0, y, tickW);
    }
    if (n.blank) return;
    const pt = PRINT.FURNITURE_FONT, tri = (pts) => `<path class="hint-arrow" d="M${pts.map(p => `${rounded(2, p[0])} ${rounded(2, p[1])}`).join('L')}Z" fill="#000"/>`, tw = textMm(n.name, pt);
    if (side === 'up') { const x = m + cw / 2 - tw / 2 - 1.5; g += tri([[x, m - 2.4], [x + 1.6, m - 2.4], [x + 0.8, m - 4.4]]) + mtext(x + 2.4, m - 2.3, pt, n.name, ' data-hint="up"'); }
    if (side === 'down') { const x = m + cw / 2 - tw / 2 - 1.5, y = m + ch + 2.1; g += tri([[x, y], [x + 1.6, y], [x + 0.8, y + 2]]) + mtext(x + 2.4, y + 2.1, pt, n.name, ' data-hint="down"'); }
    // the side hints read bottom to top in the margin's inner half (5.5 to 10 mm from the edge): arrow outside, name inside
    const turned = (x, y) => ` transform="rotate(-90 ${rounded(2, x)} ${rounded(2, y)})" text-anchor="middle"`;
    if (side === 'left') { const y = m + ch / 2, e = PRINT.EDGE; g += tri([[e, y], [e + 1.4, y - 0.8], [e + 1.4, y + 0.8]]) + mtext(m - 0.6, y, pt, n.name, ` data-hint="left"${turned(m - 0.6, y)}`); }
    if (side === 'right') { const y = m + ch / 2, e = w - PRINT.EDGE; g += tri([[e, y], [e - 1.4, y - 0.8], [e - 1.4, y + 0.8]]) + mtext(w - m + 3.2, y, pt, n.name, ` data-hint="right"${turned(w - m + 3.2, y)}`); }
  });
  const nameW = textMm(t.name, PRINT.NAME_FONT, 600);
  const place = PT.tileLoc(PAGE.title, plan.meta.scope, t.name, t.i + 1, plan.cols, t.j + 1, plan.rows, pageNo, plan.pages);
  g += mtext(w - m - 3, h - PRINT.EDGE - 0.8, PRINT.NAME_FONT, t.name, ' font-weight="600" text-anchor="end" class="tile-name"');
  g += mtext(m + 3, h - PRINT.EDGE - 0.3, PRINT.FURNITURE_FONT, fitText(place, w - 2 * m - 6 - nameW - 4, PRINT.FURNITURE_FONT), ' class="tile-place"');
  return `<g class="furniture">${g}</g>`;
}
function tilePage(model, plan, t, pageNo) {
  const m = PRINT.MARGIN, { w, h } = plan.paper, cw = w - 2 * m, ch = h - 2 * m, r = t.rect;
  const drawing = `<svg class="tile" data-tile="${esc(t.name)}" x="${m}" y="${m}" width="${rounded(2, cw)}" height="${rounded(2, ch)}" viewBox="${rounded(3, r.x)} ${rounded(3, r.y)} ${rounded(3, r.w)} ${rounded(3, r.h)}" overflow="hidden">${sheetSvg(model, r, 'full', printMarks(plan.mmPerU))}</svg>`;
  return section(w, h, pageSvg(w, h, drawing + tileFurniture(plan, t, plan.meta.printed, pageNo)), ` data-page="tile" data-tile="${esc(t.name)}"`);
}
// The index page `k` (0 based): head and assembly map on the first, a running head on the others, the table list, the footer
function indexPage(model, plan, k) {
  const m = PRINT.MARGIN, { w, h } = plan.paper, cw = w - 2 * m, ch = h - 2 * m, L2 = plan.indexLayout, pg = L2.pages[k], { fi, lh, F } = L2, meta = plan.meta;
  const entries = plan.index.slice(pg.from, pg.to), ink = LOOK.ink, muted = LOOK.muted;
  let body = '';
  const txt = (x, y, pt, s, extra = '', fill = ink) => mtext(m + x, m + y, pt, s, extra, fill);
  if (pg.first) {
    body += txt(0, L2.tf * PT_MM * 0.95, L2.tf, fitText(meta.title, cw, L2.tf, 600), ' font-weight="600"');
    const dated = schemaDate(meta.generated), lines = [
      `${meta.scope} · ${levelLabel(model.level)}`,
      PT.drawingSize(ptText(plan.floor), sizeText(plan.drawing.w, plan.drawing.h).plain, num(plan.cols), num(plan.rows), paperName(plan.paper), orientName(plan.paper.orientation), withUnit(num(PRINT.OVERLAP), 'mm')),
      [dated ? PT.schemaOf(dated) : '', PT.printedOn(printedDate(meta.printed))].filter(Boolean).join(' · '),
    ];
    lines.forEach((l, i) => { body += txt(0, L2.titleH + (i + 1) * lh - lh * 0.3, F, fitText(l, cw, F)); });
    body += mapMarkup(model, plan, m);
    const ly = L2.legendY;
    body += txt(0, ly - lh * 0.3, F, PT.legend, ' font-weight="600"');
    body += `<svg class="legend" x="${m}" y="${rounded(2, m + ly)}" width="${rounded(2, cw)}" height="${rounded(2, L2.legendH)}" viewBox="0 0 ${rounded(2, cw / L2.su)} ${rounded(2, L2.legend.h)}">${L2.legend.svg}</svg>`;
    body += txt(0, pg.y - lh * 0.3, F, PT.tablesIndex, ' font-weight="600"');
  } else if (entries.length) {
    body += txt(0, lh, F, fitText(PT.indexHead(entries[0].name, entries[entries.length - 1].name), cw, F, 600), ' font-weight="600"');
  }
  entries.forEach((e, n) => {
    const col = Math.floor(n / pg.lines), row = n % pg.lines, x = col * (L2.colW + L2.gap), y = pg.y + row * lh + fi, right = x + L2.colW;
    const tw = textMm(e.tile, F, 600), idPart = e.dup ? ` · ${e.id}` : '', idW = e.dup ? textMm(idPart, F * 0.9) : 0, avail = L2.colW - tw - 3;
    const name = fitText(e.name, Math.max(8, avail - idW), F), shown = name === e.name && idW + textMm(name, F) <= avail;
    const nameW = textMm(name, F) + (shown ? idW : 0);
    body += `<text x="${rounded(2, m + x)}" y="${rounded(2, m + y)}" font-size="${rounded(3, F * PT_MM)}" fill="${ink}">${esc(name)}${shown ? `<tspan fill="${muted}" font-size="${rounded(3, F * 0.9 * PT_MM)}">${esc(idPart)}</tspan>` : ''}</text>`;
    if (right - tw - 1 > x + nameW + 2) body += `<path d="M${rounded(2, m + x + nameW + 1.5)} ${rounded(2, m + y - fi * 0.25)}H${rounded(2, m + right - tw - 1.5)}" stroke="#666" stroke-width="0.22" stroke-dasharray="0.01 0.9" stroke-linecap="round" fill="none"/>`;
    body += txt(right, y, F, e.tile, ' font-weight="600" text-anchor="end"');
  });
  const pageNo = k + 1;
  body += mtext(m, h - PRINT.EDGE - 0.3, PRINT.FURNITURE_FONT, PT.indexFoot(k + 1, L2.pages.length, pageNo, plan.pages), ' class="index-foot"');
  return section(w, h, pageSvg(w, h, body), ` data-page="index" data-index="${k + 1}"`);
}
// The assembly map: the whole sheet as a thumbnail, the tile grid over it, blank tiles hatched, tile names in the cells (on the axes when dense)
function mapMarkup(model, plan, m) {
  const L2 = plan.indexLayout, mp = L2.map, r = mp.r, mm = plan.mmPerU, { sx, sy } = mp, dense = mp.dense, nm = PRINT.MAP_FONT / r * PT_MM;
  if (!(r > 0)) return '';
  const hair = rounded(3, 0.5 * PT_MM / r), tiles = plan.tiles;
  let g = `<defs><pattern id="print-hatch" width="2" height="2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><path d="M0 0V2" stroke="#444" stroke-width="0.25"/></pattern></defs>`;
  g += `<svg x="0" y="0" width="${rounded(2, model.W * mm)}" height="${rounded(2, model.H * mm)}" viewBox="0 0 ${rounded(2, model.W)} ${rounded(2, model.H)}">${sheetSvg(model, { x: 0, y: 0, w: model.W, h: model.H }, 'simple', { k: mm * r * PX_MM, ids: false, bare: true })}</svg>`;
  tiles.forEach(t => {
    const x = t.i * sx, y = t.j * sy, w = Math.min(sx, mp.EW - x), h = Math.min(sy, mp.EH - y);
    g += `<rect class="cell${t.blank ? ' blank' : ''}" x="${rounded(2, x)}" y="${rounded(2, y)}" width="${rounded(2, w)}" height="${rounded(2, h)}" fill="${t.blank ? 'url(#print-hatch)' : 'none'}" stroke="#666" stroke-width="${hair}"/>`;
    if (dense) return;
    const label = t.name, cx = x + w / 2, cy = y + h / 2 + nm * 0.35;
    g += `<text x="${rounded(2, cx)}" y="${rounded(2, cy)}" font-size="${rounded(3, nm)}" text-anchor="middle" fill="${t.blank ? '#666' : '#000'}" stroke="#fff" stroke-width="${rounded(3, nm * 0.35)}" paint-order="stroke">${esc(label)}</text>`;
  });
  if (dense) {
    const ax = PRINT.FURNITURE_FONT / r * PT_MM;
    for (let i = 0; i < plan.cols; i++) g += `<text x="${rounded(2, i * sx + sx / 2)}" y="${rounded(3, -ax * 0.3)}" font-size="${rounded(3, ax)}" text-anchor="middle" fill="#000">${esc(tileName(i, 0).replace(/\d+$/, ''))}</text>`;
    for (let j = 0; j < plan.rows; j++) g += `<text x="${rounded(3, -ax * 0.3)}" y="${rounded(2, j * sy + sy / 2 + ax * 0.35)}" font-size="${rounded(3, ax)}" text-anchor="end" fill="#000">${j + 1}</text>`;
  }
  const caption = plan.blank ? mtext(m, m + mp.y + mp.h + L2.lh * 0.8, PRINT.INDEX_FONT, PT.hatched, ' class="map-caption"', LOOK.muted) : '';
  const head = mtext(m, m + mp.y - mp.axis - L2.lh * 0.3, L2.F, PT.assembly, ' font-weight="600"');
  // the axes of a dense map sit outside its box: give them room through an overflow-visible nested svg
  return head + `<svg class="map" overflow="visible" x="${m}" y="${rounded(2, m + mp.y)}" width="${rounded(2, mp.w)}" height="${rounded(2, mp.h)}" viewBox="0 0 ${rounded(2, mp.EW)} ${rounded(2, mp.EH)}">${g}</svg>` + caption;
}

// The print document of a plan: every page as a <section class="pp"> of the paper's exact size, as one HTML string. Pages: the index pages, then
// the printed tiles row by row; or the one sheet. meta: { title, scope, generated, printed } (defaults to the plan's own).
function printDocument(model, plan, meta) {
  plan.meta = meta || plan.meta;
  if (plan.mode === 'sheet') return posterPage(model, plan, plan.meta);
  const pages = [];
  plan.indexLayout.pages.forEach((_, k) => pages.push(indexPage(model, plan, k)));
  plan.tiles.filter(t => !t.blank).forEach((t, k) => pages.push(tilePage(model, plan, t, plan.indexPages + k + 1)));
  return pages.join('');
}

// ---------------------------------------------------------------- the dialog and the print run
// access: { DATA, rels, relColumns, button (the toolbar's Print…), say, nodes(), level(), scopeName(), scope(), ready() } of the Schema tab.
// Returns { open, close, plan(opts), build(opts, now), clear(), choices() }. Nothing is saved: the choices live while the page is open (D-013).
function startPrint(access) {
  const $p = id => document.getElementById('p-' + id), dlg = document.getElementById('s-print'), btn = access.button;
  const doc = document.getElementById('print-doc'), pageStyle = document.getElementById('print-page'), html = document.documentElement;
  const choice = { level: 'keys', floor: PRINT.FLOOR, mode: 'sheet', paper: 'fitted', w: PRINT.PAPERS.A1[0], h: PRINT.PAPERS.A1[1], orientation: 'portrait' };
  const tags = kindTags(access.DATA.kinds);
  let cur = null, seq = 0, timer = 0, lastScope = null, busy = false;
  const meta = (now = new Date()) => ({ title: PAGE.title, scope: access.scopeName(), generated: PAGE.generatedAt, printed: now });
  // the print model: the scope's sheet with kind tags, recomputed only when the scope or the level changes
  function modelFor(level) {
    const nodes = access.nodes();
    if (!cur || cur.nodes !== nodes || cur.level !== level) {
      cur = { nodes, level, model: sheetModel(access.DATA, nodes, level, { rels: access.rels, relColumns: access.relColumns, tags }) };
    }
    return cur.model;
  }
  const allowed = () => access.scope().kind === 'domain' || access.nodes().length <= PRINT.ALL_MAX;
  const planFor = (opts, now) => printPlan(modelFor(opts.level), { ...opts, meta: meta(now) });
  function defaults(level, floor) {
    const model = modelFor(level), mt = meta(), rec = recommendPaper(model, floor, mt);
    if (rec) return { mode: 'sheet', paper: rec.key, orientation: rec.orientation };
    return onePage(model, floor, paperOf({ paper: 'fitted' }), mt).fits ? { mode: 'sheet', paper: 'fitted', orientation: 'portrait' } : { mode: 'tiles', paper: 'A4', orientation: 'portrait' };
  }

  // --- static text
  $p('title').textContent = PT.title; $p('h-level').textContent = PT.show; $p('h-floor').textContent = PT.floor; $p('floor-unit').textContent = PT.floorUnit;
  $p('h-out').textContent = PT.output; $p('out-sheet').textContent = PT.oneSheet; $p('out-tiles').textContent = PT.tiles;
  $p('h-paper').textContent = PT.paper; $p('h-custom').textContent = PT.custom; $p('h-orient').textContent = PT.orientation;
  $p('orient-portrait').textContent = PT.portrait; $p('orient-landscape').textContent = PT.landscape; $p('hint').textContent = PT.printHint;
  $p('w').setAttribute('aria-label', PT.widthMm); $p('h').setAttribute('aria-label', PT.heightMm);
  $p('cancel').textContent = PT.cancel; $p('go').textContent = PT.print;
  const radio = (name, value) => dlg.querySelector(`input[name=${name}][value=${value}]`);
  const needsText = plan => { $p('size').textContent = plan.text.size; $p('verdict').textContent = plan.text.verdict; $p('recommend').textContent = plan.text.recommend; };
  const setText = (el, text) => { if (el.textContent !== text) el.textContent = text; };

  // --- the dialog follows the choices
  function sync() {
    const floorOk = Number.isFinite(+choice.floor) && +choice.floor >= PRINT.FLOOR_MIN && +choice.floor <= PRINT.FLOOR_MAX;
    const all = allowed();
    fillSelect($p('level'), LEVELS(), choice.level);
    $p('level').querySelector('option[value=all]').disabled = !all; $p('level-why').textContent = all ? '' : PT.allWhy;
    const model = modelFor(choice.level), mt = meta();
    const fittedPlan = printPlan(model, { floor: floorOk ? choice.floor : PRINT.FLOOR, mode: 'sheet', paper: 'fitted', meta: mt });
    const fittedOk = choice.mode === 'sheet' && fittedPlan.fits;
    if (choice.paper === 'fitted' && choice.mode === 'sheet' && !fittedPlan.fits) Object.assign(choice, { mode: 'tiles', paper: 'A4', orientation: 'portrait' });
    if (choice.mode === 'tiles' && choice.paper === 'fitted') Object.assign(choice, { paper: 'A4', orientation: 'portrait' });
    const named = Object.keys(PRINT.PAPERS).map(k => [k, k]);
    fillSelect($p('paper'), [['fitted', PT.fitted], ...named, ['custom', PT.custom]], choice.paper);
    $p('paper').querySelector('option[value=fitted]').disabled = !fittedOk && choice.paper !== 'fitted';
    $p('paper').value = choice.paper;
    radio('p-out', choice.mode).checked = true; radio('p-orient', choice.orientation).checked = true;
    const fitted = choice.paper === 'fitted';
    dlg.querySelectorAll('input[name=p-orient]').forEach(r => { r.disabled = fitted; });
    $p('custom').hidden = choice.paper !== 'custom';
    if (document.activeElement !== $p('floor')) $p('floor').value = String(choice.floor);
    if (document.activeElement !== $p('w')) $p('w').value = String(choice.w);
    if (document.activeElement !== $p('h')) $p('h').value = String(choice.h);
    const customOk = choice.paper !== 'custom' || paperOf(choice).valid;
    setText($p('floor-err'), floorOk ? '' : PT.floorErr); $p('floor').setAttribute('aria-invalid', String(!floorOk));
    setText($p('custom-err'), customOk ? '' : PT.customErr);
    ['w', 'h'].forEach(k => $p(k).setAttribute('aria-invalid', String(!customOk)));
    // the reasons under Paper: a Fitted that is off, or an Orientation that cannot turn
    const why = fitted ? PT.fittedFollows : choice.mode === 'tiles' ? PT.tilesNeedPaper : !fittedPlan.fits ? fittedPlan.why : '';
    setText($p('paper-why'), why);
    const plan = printPlan(model, { ...choice, floor: floorOk ? choice.floor : PRINT.FLOOR, meta: mt });
    if (customOk && floorOk) needsText(plan); else { $p('size').textContent = plan.text.size; $p('verdict').textContent = PT.notPossible + (floorOk ? PT.customErr : PT.floorErr); $p('recommend').textContent = plan.text.recommend; }
    const go = $p('go');
    go.disabled = !(plan.fits && floorOk && customOk) || busy;
    $p('needs').removeAttribute('aria-busy');
    return plan;
  }
  // update after a change: the model may take a second on a large scope (level change), so the block says so first
  function refresh(immediate) {
    clearTimeout(timer);
    const mine = ++seq, stale = !cur || cur.nodes !== access.nodes() || cur.level !== choice.level;
    if (stale) { $p('needs').setAttribute('aria-busy', 'true'); $p('go').disabled = true; $p('verdict').textContent = PT.calculating; }
    timer = setTimeout(() => { if (mine === seq && dlg.open) sync(); }, immediate || stale ? 0 : 150);
  }
  const onInput = fn => ev => { fn(ev); refresh(); };
  $p('level').onchange = onInput(ev => { choice.level = ev.target.value; });
  $p('floor').oninput = onInput(ev => { choice.floor = ev.target.value === '' ? NaN : +ev.target.value; });
  dlg.querySelectorAll('input[name=p-out]').forEach(r => { r.onchange = onInput(() => { choice.mode = r.value; }); });
  dlg.querySelectorAll('input[name=p-orient]').forEach(r => { r.onchange = onInput(() => { choice.orientation = r.value; }); });
  $p('paper').onchange = onInput(ev => { choice.paper = ev.target.value; });
  $p('w').oninput = onInput(ev => { choice.w = +ev.target.value; });
  $p('h').oninput = onInput(ev => { choice.h = +ev.target.value; });

  // --- the print document and the print run
  function clear() {
    html.classList.remove('printing');
    doc.replaceChildren(); doc.hidden = true; pageStyle.textContent = '';
  }
  // builds the plan and the document into #print-doc, with its @page rule, and puts the page in print mode; returns the plan
  function build(opts = {}, now = new Date()) {
    const all = { ...choice, ...opts }, model = modelFor(all.level), plan = printPlan(model, { ...all, meta: meta(now) });
    if (!plan.fits) throw new Error(plan.why);
    const markup = printDocument(model, plan, plan.meta);
    pageStyle.textContent = `@page { size: ${rounded(2, plan.paper.w)}mm ${rounded(2, plan.paper.h)}mm; margin: 0 }`;
    doc.innerHTML = markup; doc.hidden = false;
    html.classList.add('printing');
    return plan;
  }
  const frames = n => new Promise(res => { const step = i => (i ? requestAnimationFrame(() => step(i - 1)) : res()); step(n); });
  async function run() {
    const go = $p('go');
    busy = true; go.disabled = true; go.textContent = PT.preparing; $p('needs').setAttribute('aria-busy', 'true'); $p('cancel').focus();
    await frames(2);
    let plan;
    try { plan = build(); } catch (e) {
      clear(); busy = false; go.textContent = PT.print; $p('needs').removeAttribute('aria-busy');
      $p('verdict').textContent = L.error + e.message; return;
    }
    busy = false; go.textContent = PT.print; $p('needs').removeAttribute('aria-busy');
    access.say(PT.ready(plan.pages));
    close();
    await frames(2);
    try { window.print(); } finally { clear(); btn.focus(); }
  }
  window.addEventListener('afterprint', () => { if (html.classList.contains('printing')) { clear(); btn.focus(); } });
  $p('form').onsubmit = ev => { ev.preventDefault(); if (!$p('go').disabled) run(); };
  $p('cancel').onclick = () => close();
  // Esc closes a modal dialog by itself; the focus returns to the button either way
  dlg.addEventListener('close', () => { clearTimeout(timer); seq++; if (!busy) btn.focus(); });
  dlg.addEventListener('cancel', () => { busy = false; });

  function open() {
    if (access.nodes().length === 0 || !access.ready()) return;
    clear();
    const nodes = access.nodes(), scopeKey = JSON.stringify(access.scope()), fresh = lastScope !== scopeKey, mine = ++seq;
    choice.level = access.level();
    if (choice.level === 'all' && !allowed()) choice.level = 'keys';
    $p('scope').textContent = PT.scopeLine(access.scopeName(), nodes.length);
    dlg.showModal();
    $p('needs').setAttribute('aria-busy', 'true'); $p('go').disabled = true; $p('verdict').textContent = PT.calculating;
    setTimeout(() => {   // the sheet of a large scope takes a moment: the dialog shows first
      if (mine !== seq || !dlg.open) return;
      if (fresh) {   // a new scope: the best paper for it (the viewer's own choices are kept while the scope stays)
        Object.assign(choice, defaults(choice.level, Number.isFinite(+choice.floor) && +choice.floor >= PRINT.FLOOR_MIN ? +choice.floor : PRINT.FLOOR));
        lastScope = scopeKey;
      }
      sync();
    }, 0);
  }
  function close() { if (dlg.open) dlg.close(); }
  btn.addEventListener('click', open);
  return { open, close, plan: (opts = {}) => planFor({ ...choice, ...opts }), build, clear, choices: () => ({ ...choice }), model: level => modelFor(level || choice.level) };
}
