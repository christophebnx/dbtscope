"""Measures of the print preparation on the large Data Vault project (M9.5, design note, plan): the
size a scope needs, the plan, the document and its layout, and the PDF Chromium writes. Timings are taken in
the page around the pure functions (`printPlan`, `printDocument`). Printed with `-s`; the budgets are the open
budget of the page (3 s) and, for the PDF, a regression guard."""

from __future__ import annotations

import time
from statistics import median
from typing import Any

import pytest

from browser.conftest import Page
from browser.test_print import count_pages, open_schema, pdf, print_media

pytestmark = pytest.mark.browser

RUNS = 5
PLAN_BUDGET_MS = 100
OPEN_BUDGET_MS = 3000  # the page's open budget (brief § 4)
PDF_BUDGET_S = 30  # Vehicle at keys in A4 tiles, headless Chromium: a regression guard, not the page's budget
SCOPES = {
    "whole project": {"kind": "all"},
    "Raw vault layer": None,  # found by its label
    "Vehicle": {"kind": "domain", "key": "vehicle"},
    "one source system": None,  # the first domain the payload marks as a source system
}
CASE = """async ({ scope, level, mode, paper }) => {
  const U = PAGE.universe, rels = U.relations.map(([c, p]) => [U.nodes[c].id, U.nodes[p].id]),
    nodes = scopeTables(U, scope), doc = document.getElementById('print-doc');
  const now = () => performance.now(), meta = { title: PAGE.title, scope: 'x', generated: PAGE.generatedAt,
    printed: new Date() };
  let t = now();
  const model = sheetModel(U, nodes, level, { rels, relColumns: DETAIL_INDEX.relationColumns,
    tags: kindTags(U.kinds) });
  const tModel = now() - t; t = now();
  const plan = printPlan(model, { floor: 7, mode, paper, meta });
  const tPlan = now() - t; t = now();
  const html = printDocument(model, plan, meta);
  const tDoc = now() - t; t = now();
  doc.hidden = false; doc.innerHTML = html; document.documentElement.classList.add('printing');
  doc.getBoundingClientRect(); doc.firstElementChild.getBoundingClientRect();
  const tLayout = now() - t;
  doc.replaceChildren(); doc.hidden = true; document.documentElement.classList.remove('printing');
  return { tables: nodes.length, w: plan.drawing.w / 1000, h: plan.drawing.h / 1000, cols: plan.cols,
    rows: plan.rows, printed: plan.printed, blank: plan.blank,
    indexPages: plan.indexPages, pages: plan.pages, fits: plan.fits, tModel, tPlan, tDoc, tLayout,
      kb: html.length / 1024 };
}"""


def case(p: Page, scope: dict[str, Any], level: str, mode: str, paper: str) -> dict[str, float]:
    return p.page.evaluate(CASE, {"scope": scope, "level": level, "mode": mode, "paper": paper})


def scope_of(name: str, data: dict[str, Any]) -> dict[str, Any]:
    """The scope of a case; the Raw vault layer and a source system are found in the payload."""
    if SCOPES[name]:
        return SCOPES[name]
    if name == "one source system":
        return {"kind": "domain", "key": next(d["key"] for d in data["universe"]["domains"] if d["system"])}
    layers = data["universe"]["layers"]
    key = next(
        (x["key"] for x in layers if (x["label"] or x["key"]).lower().startswith("raw")), layers[0]["key"]
    )
    return {"kind": "layer", "key": key}


@pytest.fixture
def large(large_page: tuple[Any, dict[str, Any]], open_page: Any) -> tuple[Page, dict[str, Any]]:
    p = open_page(large_page[0], display=False)
    open_schema(p)
    return p, large_page[1]


@pytest.mark.parametrize("name", list(SCOPES))
@pytest.mark.parametrize("level", ["names", "keys", "all"])
@pytest.mark.parametrize(("mode", "paper"), [("sheet", "fitted"), ("tiles", "A4")])
def test_print_preparation_by_scope_level_and_output(
    large: tuple[Page, dict[str, Any]], name: str, level: str, mode: str, paper: str
) -> None:
    p, data = large
    scope = scope_of(name, data)
    if level == "all" and scope["kind"] == "layer":
        pytest.skip("all columns are offered per domain only")
    runs = [case(p, scope, level, mode, paper) for _ in range(RUNS)]
    one = runs[0]
    med = {k: median(r[k] for r in runs) for k in ("tModel", "tPlan", "tDoc", "tLayout", "kb")}
    print(
        f"{name:18} {level:5} {mode:5} {one['tables']:5} tables {one['w']:.2f} x {one['h']:.2f} m "
        f"tiles {one['printed']} (+{one['blank']} blank) of {one['cols']}x{one['rows']} index "
        f"{one['indexPages']} pages {one['pages']}: "
        f"model {med['tModel']:.0f} plan {med['tPlan']:.0f} doc {med['tDoc']:.0f} layout "
        f"{med['tLayout']:.0f} ms, {med['kb']:.0f} kB"
    )
    assert med["tPlan"] < PLAN_BUDGET_MS or (mode == "tiles" and name == "whole project" and level == "all")
    if name == "whole project" and level == "keys" and mode == "tiles":
        assert med["tModel"] + med["tPlan"] + med["tDoc"] + med["tLayout"] < OPEN_BUDGET_MS


@pytest.mark.parametrize(
    ("name", "mode", "paper"),
    [("Vehicle", "tiles", "A4"), ("whole project", "sheet", "fitted"), ("whole project", "tiles", "A4")],
)
def test_the_pdf_chromium_writes(
    large: tuple[Page, dict[str, Any]], name: str, mode: str, paper: str
) -> None:
    p, data = large
    scope = scope_of(name, data)
    built = p.page.evaluate("views.schema.perf().built")
    p.page.select_option("#s-scope", "all" if scope["kind"] == "all" else f"{scope['kind']}:{scope['key']}")
    p.page.wait_for_function(
        "n => views.schema.perf().built > n && document.getElementById('s-empty').hidden",
        arg=built,
        timeout=60_000,
    )
    t = time.perf_counter()
    plan = p.page.evaluate(
        "o => { const x = views.schema.print.build(o); return { pages: x.pages, cols: x.cols, rows: "
        "x.rows }; }",
        {"mode": mode, "paper": paper, "level": "keys", "floor": 7},
    )
    built_s = time.perf_counter() - t
    print_media(p)
    t = time.perf_counter()
    data = pdf(p)
    took = time.perf_counter() - t
    print(
        f"PDF {name} {mode} {paper}: {count_pages(data)} pages, {len(data) / 1e6:.1f} MB, build+insert "
        f"{built_s:.2f} s, page.pdf {took:.1f} s"
    )
    assert count_pages(data) == plan["pages"]
    if name == "Vehicle":
        assert took < PDF_BUDGET_S
