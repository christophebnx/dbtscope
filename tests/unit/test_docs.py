"""The user documents stay true: links and anchors, Mermaid diagrams, config keys, the example (M6.1).

M6.2 adds: every summary the guide shows is a real `--no-parse` run on the example (page sizes
included), the detail group counts match `expected.json`, the default layer order of how-it-works
names every `FLOW_PREFIXES` prefix in rank order, and `docs/images/README.md` lists its images.
Page sizes are compared as printed: a milestone that changes the page assets updates the guide's
summaries in the same commit.

The options table and the documented commands are checked in `test_cli.py`, next to the command.
External links are never fetched (invariant 5). `DBTSCOPE_MMDC` (a mermaid-cli command line, for
example `mmdc -p puppeteer.json`) turns on rendering every diagram, as `DBTSCOPE_DBT` does for D-033.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path

import pytest
import yaml
from conftest import EXAMPLE_EXPECTED, ROOT, USER_GUIDE, Block, blocks, page_of, prose, write_example

from dbtscope.domain.config import Config, UniverseSettings, merge_config
from dbtscope.domain.universe import FLOW_PREFIXES, UNRANKED

HOW_IT_WORKS = ROOT / "docs" / "how-it-works.md"
IMAGES = ROOT / "docs" / "images"
DOCS = [
    ROOT / "README.md",
    ROOT / "CLAUDE.md",
    USER_GUIDE,
    HOW_IT_WORKS,
    ROOT / "docs" / "architecture.md",
    ROOT / "docs" / "ui-spec.md",
    ROOT / "examples" / "acme_retail" / "README.md",
    ROOT / "docs" / "images" / "README.md",
]
DIAGRAM_STARTS = ("flowchart TD", "flowchart LR", "sequenceDiagram")
EXCERPT = re.compile(r"<!-- excerpt: (\S+) -->")
LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)\)")
IMAGE_MAX_BYTES, IMAGES_MAX_BYTES = 200_000, 1_200_000
SUMMARY_KEYS = ("universe:", "detail:", "page:", "config:")
GUIDE_PROJECT = re.compile(r"/home/ana/\S*?(?:acme_retail|shop-map)")  # the guide's sample project paths
# (heading of the guide, example with its dbt-erd.yml, extra arguments of each run shown in the block)
SUMMARIES = [
    ("### Live, in the project folder", True, [()]),
    ("### Try it on the example project", True, [()]),
    ("### Without dbt, from a copied manifest", False, [()]),
    ("### An offline page to share", True, [("--offline",)]),
    (
        "### Conventions: presets and preset files",
        False,
        [("--preset", "data_vault"), ("--preset", "star_schema")],
    ),
]


def slug(heading: str) -> str:
    """The anchor GitHub gives a heading: lower case, punctuation dropped, spaces to `-`."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def anchors(text: str) -> set[str]:
    """Every heading anchor of a Markdown text; a repeated slug gets `-1`, `-2`…"""
    seen: dict[str, int] = {}
    for heading in re.findall(r"^#{1,6}\s+(.+)$", prose(text), flags=re.MULTILINE):
        base = slug(heading)
        count = seen.get(base, 0)
        seen[base] = count + 1
        if count:
            seen[f"{base}-{count}"] = 1
    return set(seen)


def links(doc: Path) -> list[tuple[bool, str, str]]:
    """`(is_image, text, target)` of every Markdown link outside fenced blocks."""
    text = prose(doc.read_text(encoding="utf-8"))
    return [(bang == "!", label, target) for bang, label, target in LINK.findall(text)]


def section_block(doc: Path, heading: str, lang: str) -> Block:
    """The first fenced block of `lang` after the heading line `heading` of `doc`."""
    text = doc.read_text(encoding="utf-8")
    assert f"\n{heading}\n" in text, f"{doc.name} has no `{heading}`"
    found = [block for block in blocks(text.split(f"\n{heading}\n", 1)[1]) if block.lang == lang]
    assert found, f"no {lang} block under `{heading}` in {doc.name}"
    return found[0]


def diagrams() -> list[tuple[str, int, list[str]]]:
    """`(doc name, index, lines)` of every Mermaid block of the documents."""
    found = []
    for doc in DOCS:
        mermaid = [b for b in blocks(doc.read_text(encoding="utf-8")) if b.lang == "mermaid"]
        found += [(doc.name, i, block.lines) for i, block in enumerate(mermaid)]
    return found


@pytest.mark.parametrize("doc", DOCS, ids=lambda doc: doc.name)
def test_relative_links_and_anchors_exist(doc: Path) -> None:
    for _, _, target in links(doc):
        if re.match(r"[a-z]+:", target):
            continue  # http(s), mailto: never fetched
        path, _, anchor = target.partition("#")
        file = (doc.parent / path).resolve() if path else doc
        assert file.exists(), f"{doc.name}: {target} points at nothing"
        if anchor:
            assert anchor in anchors(file.read_text(encoding="utf-8")), f"{doc.name}: no heading for {target}"


def test_slug_follows_github() -> None:
    assert slug("Walkthrough: the example's dbt-erd.yml") == "walkthrough-the-examples-dbt-erdyml"
    assert slug("Run once without installing (uvx)") == "run-once-without-installing-uvx"
    assert anchors("# A\n## A\n```\n# B\n```\n## A\n") == {"a", "a-1", "a-2"}


@pytest.mark.parametrize(("doc", "index", "lines"), diagrams(), ids=lambda value: str(value)[:20])
def test_mermaid_blocks_follow_the_rules(doc: str, index: int, lines: list[str]) -> None:
    body = [line for line in lines if line.strip()]
    assert body[0].strip() in DIAGRAM_STARTS, f"{doc} diagram {index}"
    flowchart = body[0].startswith("flowchart")
    for line in body:
        assert "<" not in line and line.count('"') % 2 == 0, f"{doc} diagram {index}: {line}"
        if flowchart:
            assert not any(";" in label or "#" in label for label in re.findall(r'"([^"]*)"', line)), line
            assert not re.search(r"-->\s*end\b|^\s*end\b", line), f"{doc} diagram {index}: `end` as a node"


@pytest.mark.skipif(not os.environ.get("DBTSCOPE_MMDC"), reason="set DBTSCOPE_MMDC to a mermaid-cli command")
def test_mermaid_blocks_render(tmp_path: Path) -> None:
    command = shlex.split(os.environ["DBTSCOPE_MMDC"])
    for doc, index, lines in diagrams():
        source = tmp_path / f"{Path(doc).stem}-{index}.mmd"
        source.write_text("\n".join(lines) + "\n", encoding="utf-8")
        run = subprocess.run(
            [*command, "-i", str(source), "-o", str(source.with_suffix(".svg"))],
            capture_output=True,
            text=True,
            check=False,
        )
        assert run.returncode == 0, f"{doc} diagram {index}: {run.stderr}"


def test_config_reference_lists_every_key() -> None:
    block = section_block(USER_GUIDE, "### Every key", "yaml")
    reference = yaml.safe_load("\n".join(block.lines))
    assert set(reference) == set(Config.model_fields) | {"preset"}
    assert set(reference["universe"]) == set(UniverseSettings.model_fields)
    merge_config({}, {key: value for key, value in reference.items() if key != "preset"})


def summary_key(line: str) -> str | None:
    """What a line of a summary shows: `path` (the page, first line), a `SUMMARY_KEYS` entry, or None."""
    if line.startswith("<project>"):
        return "path"
    return next((key for key in SUMMARY_KEYS if line.startswith(f"  {key}")), None)


def run_summary(project: Path, args: tuple[str, ...], capsys: pytest.CaptureFixture[str]) -> list[str]:
    """The summary lines the CLI prints for `project`, its path written `<project>`."""
    capsys.readouterr()
    page_of(project, *args)
    lines = capsys.readouterr().out.replace(str(project), "<project>").splitlines()
    return [line for line in lines if summary_key(line)]


@pytest.mark.parametrize(("heading", "configured", "runs"), SUMMARIES, ids=[s[0][4:] for s in SUMMARIES])
def test_guide_summaries_are_a_real_run_on_the_example(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    heading: str,
    configured: bool,
    runs: list[tuple[str, ...]],
) -> None:
    project = write_example(tmp_path / ("acme_retail" if configured else "shop-map"))
    if not configured:
        (project / "dbt-erd.yml").unlink()
    block = section_block(USER_GUIDE, heading, "text").lines
    shown = [line for line in (GUIDE_PROJECT.sub("<project>", line) for line in block) if summary_key(line)]
    keys = {summary_key(line) for line in shown}
    real = [line for args in runs for line in run_summary(project, args, capsys) if summary_key(line) in keys]
    assert shown, f"no summary line found under {heading!r}"
    assert shown == real


def test_guide_quotes_the_example_detail_groups() -> None:
    text = prose(USER_GUIDE.read_text(encoding="utf-8"))
    paragraph = next(p for p in text.split("\n\n") if "one group per domain schema" in p)
    quoted = {name: int(count) for name, count in re.findall(r"`(\w+)` \((\d+)", paragraph)}
    assert quoted == EXAMPLE_EXPECTED["detail"]["groups"]


def test_how_it_works_names_the_default_layer_order() -> None:
    text = prose(HOW_IT_WORKS.read_text(encoding="utf-8"))
    start = text.index("Layers are ordered along the usual data flow")
    sentence = text[start : text.index(";", start)]  # up to "layers of the same rank…"
    words = re.findall(r"`(\w+)`|(any other name)", sentence)
    order = [UNRANKED if other else dict(FLOW_PREFIXES)[prefix] for prefix, other in words]
    assert {prefix for prefix, _ in words if prefix} == {prefix for prefix, _ in FLOW_PREFIXES}
    assert UNRANKED in order and order == sorted(order), sentence


def test_excerpts_are_copied_from_their_file() -> None:
    excerpts = [
        b for b in blocks(USER_GUIDE.read_text(encoding="utf-8")) if EXCERPT.fullmatch(b.before.strip())
    ]
    assert excerpts
    for block in excerpts:
        match = EXCERPT.fullmatch(block.before.strip())
        assert match
        source = (ROOT / match[1]).read_text(encoding="utf-8").splitlines()
        position = 0
        for line in (line for line in block.lines if line.strip()):
            assert line in source[position:], f"{match[1]}: not found in order: {line}"
            position = source.index(line, position) + 1


def test_images_are_described_referenced_and_small() -> None:
    used = set()
    for doc in DOCS:
        for is_image, text, target in links(doc):
            if is_image:
                assert text.strip(), f"{doc.name}: {target} has no alt text"
                path = (doc.parent / target).resolve()
                assert path.is_file(), f"{doc.name}: {target} points at nothing"
                used.add(path)
    files = [path for path in IMAGES.glob("*") if path.name != "README.md"] if IMAGES.is_dir() else []
    assert all(path.resolve() in used for path in files), "an image of docs/images is not referenced"
    listed = set(re.findall(r"`([\w-]+\.png)`", (IMAGES / "README.md").read_text(encoding="utf-8")))
    assert listed == {path.name for path in files}, "docs/images/README.md must list exactly its images"
    assert all(path.stat().st_size <= IMAGE_MAX_BYTES for path in files if path.suffix == ".png")
    assert sum(path.stat().st_size for path in files) <= IMAGES_MAX_BYTES


def test_readme_ci_sentence_follows_d053() -> None:
    """The README cites D-053 and tools/ci.py and names no OS the workflow does not run on."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    sentence = next(line for line in readme.splitlines() if "CI runs" in line)
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    runners = re.findall(r"runs-on:\s*(\S+)", workflow)
    assert "D-053" in sentence and "tools/ci.py" in sentence
    for name in ("Windows", "macOS"):
        assert name not in sentence or any(name.lower()[:3] in runner for runner in runners)
