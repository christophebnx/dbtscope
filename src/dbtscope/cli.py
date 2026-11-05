"""dbtscope: build the interactive map of a dbt project (universe + ERD) and open it.

The interface is a Typer command whose callback does no work: it returns the parsed `Options`,
which `run` acts on. `main(argv) -> int` is the only place that turns an outcome into an exit
code: 0 success, 1 error, 2 usage, 130 interrupted (D-004, D-029). stdout holds only the
success summary; progress, dbt's output, warnings and errors go to stderr, each failure as one
plain line `dbtscope: error: <what happened>; <what to do>`. Tests call `main([...])` in-process.
"""

from __future__ import annotations

import errno
import os
import re
import shutil
import subprocess
import sys
import webbrowser
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal, TextIO, get_args

import typer

from dbtscope import __version__
from dbtscope.domain.config import Config, View
from dbtscope.domain.detail import detail_data, select
from dbtscope.domain.errors import DomainError, in_words, lower_first
from dbtscope.domain.model import Project
from dbtscope.domain.payload import DetailPayload, UniversePayload
from dbtscope.domain.selectors import SelectorError
from dbtscope.domain.universe import universe_data
from dbtscope.render.page import render_page
from dbtscope.storage.files import (
    PathKind,
    atomic_write,
    is_name_too_long,
    os_reason,
    path_kind,
    refused_hint,
)
from dbtscope.storage.project_files import (
    CONFIG_HINT,
    config_source,
    load_config,
    preset_names,
    read_layout,
    read_manifest,
)

PROG = "dbtscope"
PRESETS = preset_names()
Preset = Literal[tuple(PRESETS)]  # type: ignore[valid-type]  # the choices, read once from the package
HELP = (
    "Build the interactive map of a dbt project from its manifest: "
    "one HTML page with the universe of domains and the ERD of tables."
)
EPILOG = (
    "Examples, from the dbt project folder:\n"
    "  dbtscope                                   parse, write the page, open it\n"
    "  dbtscope --preset data_vault               Data Vault conventions\n"
    "  dbtscope --no-parse --no-open -o map.html  CI: no dbt parse, no browser\n"
    "  dbtscope --project-dir ../shop --offline   page that works without network"
    "\n\n"
    "Relative paths in options are read from the current folder; the output and "
    "layout_file keys of the config, from the project folder; a preset path in the "
    "config, from the config file's folder. The page path and a "
    "summary go to stdout; progress, dbt's output, warnings and errors go to stderr. "
    "Exit codes: 0 done, 1 error, 2 wrong option, 130 interrupted."
)
USAGE_HINT = "see dbtscope --help"
LABEL_WIDTH = 10  # `universe: `, the longest summary label

app = typer.Typer(
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)


class RunError(Exception):
    """A failure only the CLI can judge (paths, dbt, output, empty result), in its final words."""


@dataclass(frozen=True)
class Options:
    """The parsed command line."""

    project_dir: str | None = None
    config: str | None = None
    preset: str | None = None
    output: str | None = None
    view: View | None = None
    manifest: str | None = None
    no_parse: bool = False
    no_open: bool = False
    dbt: str | None = None
    offline: bool = False
    preset_file: str | None = None


@dataclass(frozen=True)
class Inputs:
    """The paths of a run, resolved and checked; `dbt` is None when dbt does not run."""

    project: Path
    config: Path | None
    manifest: Path
    dbt: str | None
    preset_file: Path | None = None  # absolute; checked when read (`storage/project_files.read_preset_file`)


# --- interface ------------------------------------------------------------------------------


def _not_empty(value: str | None) -> str | None:
    """Refuse an empty path option (`-o ""`): a usage error, exit 2."""
    if value == "":
        raise typer.BadParameter("must not be empty")
    return value


def _show_version(value: bool) -> None:
    if value:
        _say(sys.stdout, f"{PROG} {__version__}")
        raise typer.Exit()


def _path_option(*names: str, metavar: str, panel: str, help: str) -> Any:
    return typer.Option(
        *names, metavar=metavar, rich_help_panel=panel, help=help, show_default=False, callback=_not_empty
    )


def _flag(name: str, panel: str, help: str) -> Any:
    return typer.Option(name, rich_help_panel=panel, help=help, show_default=False)


@app.command(help=HELP, epilog=EPILOG)
def command(
    version: Annotated[
        bool,
        typer.Option("--version", is_eager=True, callback=_show_version, help="Show the version and exit."),
    ] = False,
    project_dir: Annotated[
        str | None,
        _path_option(
            "--project-dir",
            metavar="FOLDER",
            panel="Project",
            help="dbt project folder, holding dbt_project.yml. Default: the current folder.",
        ),
    ] = None,
    config: Annotated[
        str | None,
        _path_option(
            "--config",
            metavar="FILE",
            panel="Project",
            help="Config file. Default: dbt-erd.yml in the project folder, if present.",
        ),
    ] = None,
    preset: Annotated[
        Preset | None,
        typer.Option(
            "--preset",
            metavar="NAME",
            rich_help_panel="Project",
            show_default=False,
            help=f"Built-in conventions: {in_words(PRESETS)}.",
        ),
    ] = None,
    preset_file: Annotated[
        str | None,
        _path_option(
            "--preset-file",
            metavar="FILE",
            panel="Project",
            help="Conventions from a YAML file instead of a built-in --preset: "
            "the keys of dbt-erd.yml except output, layout_file and preset.",
        ),
    ] = None,
    no_parse: Annotated[
        bool,
        _flag("--no-parse", "dbt", "Do not run dbt parse; read target/manifest.json in the project folder."),
    ] = False,
    manifest: Annotated[
        str | None,
        _path_option(
            "--manifest",
            metavar="FILE",
            panel="dbt",
            help="Read this manifest.json instead of running dbt parse.",
        ),
    ] = None,
    dbt: Annotated[
        str | None,
        _path_option(
            "--dbt",
            metavar="PATH",
            panel="dbt",
            help="dbt executable, a name on PATH or a path. Default: dbt.",
        ),
    ] = None,
    output: Annotated[
        str | None,
        _path_option(
            "-o",
            "--output",
            metavar="FILE",
            panel="Output",
            help="HTML page to write. Default: the output key of the config, "
            "else erd_output/erd.html in the project folder.",
        ),
    ] = None,
    no_open: Annotated[bool, _flag("--no-open", "Output", "Do not open the page in the browser.")] = False,
    view: Annotated[
        View | None,
        typer.Option(
            "--view",
            metavar="VIEW",
            rich_help_panel="Page",
            show_default=False,
            help=f"Tab shown when the page opens: {in_words(get_args(View))}. "
            "Default: the view key of the config, else universe.",
        ),
    ] = None,
    offline: Annotated[
        bool,
        _flag(
            "--offline",
            "Page",
            "Embed the JavaScript libraries so that the page works without network "
            "(about 2.5 MB larger). Default: the offline key of the config, else off.",
        ),
    ] = False,
) -> Options:
    """The command line as `Options`; the work is done by `run`, called from `main`."""
    del version  # eager: handled by `_show_version`
    if preset is not None and preset_file is not None:
        raise typer.BadParameter("cannot be used together with --preset", param_hint="'--preset-file'")
    return Options(
        project_dir, config, preset, output, view, manifest, no_parse, no_open, dbt, offline, preset_file
    )


# --- paths ----------------------------------------------------------------------------------


def _kind(path: Path, option: str) -> PathKind:
    """`storage/files.path_kind`; a path the system refuses is a `RunError` naming `option`."""
    try:
        return path_kind(path)
    except OSError as error:  # e.g. ENAMETOOLONG, EACCES on a parent folder
        raise RunError(f"cannot use {path}: {os_reason(error)}; {refused_hint(error, option)}") from error


def _project(value: str | None) -> Path:
    project = Path(value or ".").resolve()
    kind = _kind(project, "--project-dir")
    if kind == "missing":
        raise RunError(f"project folder {project} does not exist; check --project-dir")
    if kind != "folder":
        raise RunError(
            f"--project-dir {project} is a file, not a folder; pass the folder that holds dbt_project.yml"
        )
    if _kind(project / "dbt_project.yml", "--project-dir") != "file":
        hint = (
            "dbt reads dbt_project.yml only, rename dbt_project.yaml"
            if _kind(project / "dbt_project.yaml", "--project-dir") == "file"
            else "run dbtscope from the dbt project folder or pass --project-dir"
        )
        raise RunError(f"no dbt_project.yml in {project}; {hint}")
    return project


def _config(value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value).resolve()
    kind = _kind(path, "--config")
    if kind == "missing":
        relative = (
            ""
            if Path(value).is_absolute()
            else " (it is relative to the current folder, not to --project-dir)"
        )
        raise RunError(f"{config_source(path)} not found; check --config{relative}")
    if kind == "folder":
        raise RunError(f"--config {path} is a folder; pass a YAML file")
    return path


def _manifest(value: str) -> Path:
    path = Path(value).resolve()
    kind = _kind(path, "--manifest")
    if kind == "missing":
        raise RunError(f"manifest {path} not found; check --manifest")
    if kind == "folder":
        raise RunError(f"--manifest {path} is a folder; pass the manifest.json file")
    return path


def _dbt(value: str | None) -> str:
    """The dbt command to run, absolute when given as a relative path (it runs in the project)."""
    found = shutil.which(value or "dbt")
    if found:
        return str(Path(found).absolute())
    if value is None:
        raise RunError(
            "dbt not found on PATH; install dbt, pass --dbt <path>, "
            "or use --no-parse with an existing manifest"
        )
    if any(sep and sep in value for sep in (os.sep, os.altsep)):
        raise RunError(f"--dbt {Path(value).resolve()} does not exist or is not executable; check the path")
    raise RunError(f"--dbt {value} not found on PATH; check the name or pass its path")


def _resolve(options: Options) -> Inputs:
    """Resolve and check the project, config, manifest and dbt given on the command line.

    `--preset-file` is only resolved here: `load_config` checks it, as it checks the file's
    `preset` key (one implementation, D-030).
    """
    project = _project(options.project_dir)
    config = _config(options.config)
    preset_file = Path(options.preset_file).resolve() if options.preset_file is not None else None
    if options.manifest is not None:
        return Inputs(project, config, _manifest(options.manifest), None, preset_file)
    manifest = project / "target" / "manifest.json"
    return Inputs(project, config, manifest, None if options.no_parse else _dbt(options.dbt), preset_file)


def _output(value: str | None, project: Path, config: Config) -> Path:
    """The page to write: `-o` (from the current folder) or the config's `output` (from the project)."""
    output = Path(value).resolve() if value is not None else (project / config.output).resolve()
    kind = _kind(output, "--output")
    if kind == "folder":
        raise RunError(
            f"output {output} is a folder; pass a file name such as {output / 'erd.html'} with --output"
        )
    if kind == "other":
        raise RunError(f"output {output} is not a regular file; choose a file path with --output")
    return output


# --- steps ----------------------------------------------------------------------------------


def _say(stream: TextIO, line: str) -> None:
    """Write one line of ours; a closed stderr is ignored, a closed stdout is left to `main`."""
    try:
        stream.write(line + "\n")
        stream.flush()
    except BrokenPipeError:
        if stream is not sys.stderr:
            raise


def _warn(message: str) -> None:
    _say(sys.stderr, f"{PROG}: warning: {message}")


def _run_reason(error: OSError, command: str) -> str:
    """Why `command` could not run; ENOENT on an existing file means its `#!` interpreter is missing."""
    if isinstance(error, FileNotFoundError) and _kind(Path(command), "--dbt") == "file":
        return "its interpreter was not found (check its first line)"
    return os_reason(error)


def _dbt_parse(dbt: str, project: Path) -> None:
    """Run `dbt parse` in `project`, its output on our stderr (D-029)."""
    _say(sys.stderr, f"Running dbt parse in {project}...")
    env = None
    if not sys.stderr.isatty() and "DBT_USE_COLORS" not in os.environ:
        env = {**os.environ, "DBT_USE_COLORS": "false"}
    try:
        # on Ctrl-C (or any exception) `run` kills dbt before re-raising: no dbt is left behind
        result = subprocess.run([dbt, "parse"], cwd=project, stdout=2, env=env, check=False)
    except OSError as error:
        raise RunError(f"cannot run {dbt}: {_run_reason(error, dbt)}; check --dbt") from error
    if result.returncode != 0:
        raise RunError(
            f"dbt parse failed with exit code {result.returncode} (see its messages above); "
            "fix the project, or pass --no-parse to map the existing manifest"
        )


def _check_manifest(inputs: Inputs, ran_dbt: bool) -> None:
    """The default manifest exists once dbt has run (or was asked not to)."""
    if _kind(inputs.manifest, "--project-dir") == "file":
        return
    if ran_dbt:
        raise RunError(
            f"dbt parse did not write {inputs.manifest}; if dbt_project.yml sets target-path, "
            "pass --manifest <that folder>/manifest.json"
        )
    raise RunError(
        f"manifest {inputs.manifest} not found; run without --no-parse so that dbt parse writes it"
    )


def _write_page(output: Path, page_bytes: bytes) -> None:
    """Write the page atomically; an `OSError` names the output, never the temp file."""
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        folder = error.filename or output.parent
        raise RunError(
            f"cannot create folder {folder}: {os_reason(error)}; choose another --output"
        ) from error
    try:
        atomic_write(output, page_bytes)
    except OSError as error:
        hint = (
            "choose a shorter --output"
            if is_name_too_long(error)
            else "free some space or choose another --output"
            if error.errno == errno.ENOSPC
            else "choose another --output"
        )
        raise RunError(f"cannot write {output}: {os_reason(error)}; {hint}") from error


def _open_browser(output: Path) -> None:
    """Open the page; a browser that cannot be opened is a warning, not an error."""
    _say(sys.stderr, "Opening the page in the browser...")
    uri = output.as_uri()
    try:
        opened = webbrowser.open(uri)
    except (webbrowser.Error, OSError):
        opened = False
    if not opened:
        _warn(f"could not open a browser; open {uri} yourself")


# --- summary --------------------------------------------------------------------------------


def _count(number: int, noun: str) -> str:
    return f"{number:,} {noun}{'' if number == 1 else 's'}"


def _size(size: int) -> str:
    """`95 kB` below 1 MB once rounded (999,600 bytes is `1.0 MB`, not `1000 kB`), else `1.4 MB`."""
    kilobytes = round(size / 1000)
    return f"{kilobytes} kB" if kilobytes < 1000 else f"{size / 1e6:.1f} MB"


def _saved(saved_at: object) -> str:
    """`, saved 2026-11-01 10:00 UTC` from the layout's `savedAt`; its raw value if it does not parse."""
    if saved_at is None:
        return ""
    try:
        moment = datetime.fromisoformat(str(saved_at))
    except ValueError:
        return f", saved {saved_at}"
    if moment.tzinfo is not None:
        moment = moment.astimezone(UTC)
    return f", saved {moment:%Y-%m-%d %H:%M} UTC"


@dataclass(frozen=True)
class Report:
    """What the summary tells about a written page."""

    output: Path
    config: Config
    config_path: Path | None
    preset: str | Path | None  # the preset applied: a built-in name or a preset file
    page_size: int
    layout_path: Path | None  # None when no layout is embedded
    saved_at: object = None  # the layout's `savedAt`


def _summary(report: Report, detail: DetailPayload, universe: UniversePayload) -> str:
    """The success summary: the page path, then one aligned line per view, page, config, layout."""
    entities = detail.entities
    counts = ", ".join(f"{sum(e.kind == k.key for e in entities):,} {k.label}" for k in detail.kinds)
    kinds = f" ({counts})" if entities and counts else ""
    config = report.config
    libraries = "offline, libraries embedded" if config.offline else "libraries from CDNs"
    rows = {
        "universe": f"{_count(len(universe.nodes), 'table')} in {_count(len(universe.domains), 'domain')}, "
        f"{_count(len(universe.relations), 'relation')}, {_count(len(universe.lineage), 'lineage link')}",
        "detail": f"{_count(len(entities), 'table')}{kinds}, {_count(len(detail.relations), 'relation')}",
        "page": f"opens on {config.view}, {config.language}, {libraries} ({_size(report.page_size)})",
        "config": f"{report.config_path or 'none (built-in defaults)'}"
        + (f", preset {report.preset}" if report.preset else ""),
    }
    if report.layout_path is not None:
        rows["layout"] = f"{report.layout_path}{_saved(report.saved_at)}"
    return "\n".join([str(report.output), *(f"  {f'{k}:':<{LABEL_WIDTH}}{v}" for k, v in rows.items())])


# --- run ------------------------------------------------------------------------------------


def _config_label(config_path: Path | None, preset: str | Path | None) -> str:
    """How messages name the config of the run: its file, the preset applied, or the defaults."""
    if config_path is not None:
        return config_source(config_path)
    return f"preset {preset}" if preset else "the default config"


def _views(parsed: Project, config: Config, label: str) -> tuple[DetailPayload, UniversePayload]:
    """Both views; a selector error names the config it comes from."""
    try:
        tables, relations = select(parsed.tables, parsed.relations, config, parsed.root)
        return detail_data(tables, relations, config), universe_data(parsed, config)
    except SelectorError as error:
        raise SelectorError(f"{label}: {error}; {CONFIG_HINT}") from error


def _check_views(detail: DetailPayload, universe: UniversePayload, label: str) -> None:
    """Both views empty is an error; one empty view is a warning."""
    if not detail.entities and not universe.nodes:
        raise RunError(
            f"no table matches the selection of {label}; check select, exclude and universe.select"
        )
    if not detail.entities:
        _warn(f"the detail view is empty; check select and exclude of {label}")
    if not universe.nodes:
        _warn(f"the universe view is empty; check universe.select and universe.exclude of {label}")


def run(options: Options) -> None:
    """Parse the project, build both views, write the page, print the summary, open the browser."""
    inputs = _resolve(options)
    config, config_path, preset = load_config(
        inputs.project, inputs.config, inputs.preset_file or options.preset
    )
    overrides: dict[str, object] = {"view": options.view} if options.view else {}
    if options.offline:
        overrides["offline"] = True
    config = config.model_copy(update=overrides)  # the command line last
    output = _output(options.output, inputs.project, config)
    if inputs.dbt is not None:
        _dbt_parse(inputs.dbt, inputs.project)
    _check_manifest(inputs, ran_dbt=inputs.dbt is not None)

    parsed = read_manifest(inputs.manifest)
    if not parsed.tables:
        raise RunError(
            f"manifest {inputs.manifest} holds no model, seed, snapshot or source; "
            "check that it is the manifest of your dbt project"
        )
    label = _config_label(config_path, preset)
    detail, universe = _views(parsed, config, label)
    _check_views(detail, universe, label)
    layout_path = (inputs.project / config.layout_file).resolve()
    layout = read_layout(layout_path)
    page_bytes = render_page(detail, universe, config, layout, offline=config.offline).encode("utf-8")
    _write_page(output, page_bytes)
    embedded = layout_path if layout is not None else None
    saved_at = layout.get("savedAt") if layout is not None else None
    report = Report(output, config, config_path, preset, len(page_bytes), embedded, saved_at)
    _say(sys.stdout, _summary(report, detail, universe))
    if not options.no_open:
        _open_browser(output)


# --- exit codes -----------------------------------------------------------------------------


def _usage_message(error: typer.TyperException) -> str:
    """click's usage error as one lower-case line with our hint."""
    text = error.format_message().strip().rstrip(".")
    text = re.sub(
        r"\(Possible options?: (.+)\)$", lambda m: f"(did you mean {in_words(m[1].split(', '))}?)", text
    )
    text = lower_first(text)
    if getattr(error, "param", None) is not None and error.param.name == "preset":  # a file goes elsewhere
        text += " (or use --preset-file for a preset file)"
    if text.startswith("got unexpected extra argument"):
        return f"{text}; pass the project folder with --project-dir"
    return f"{text}; {USAGE_HINT}"


def _fail(message: str, code: int) -> int:
    """Print the error line, whitespace of any inserted text collapsed (the one place), and return `code`."""
    _say(sys.stderr, f"{PROG}: error: {' '.join(message.split())}")
    return code


def _silence_stdout() -> None:
    """Point stdout at the null device so that the flush at exit cannot fail again (Python docs)."""
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    except (OSError, ValueError):  # no file descriptor (an in-memory stream, in tests)
        pass


def main(argv: Sequence[str] | None = None) -> int:
    """Parse the command line, run, and map every outcome to an exit code."""
    try:
        parsed = typer.main.get_command(app).main(
            args=list(sys.argv[1:] if argv is None else argv), prog_name=PROG, standalone_mode=False
        )
        if parsed == 130:  # Ctrl-C while the command line is parsed (Typer's own exit code)
            return _fail("interrupted", 130)
        if not isinstance(parsed, Options):  # --help / --version: the exit code
            return int(parsed or 0)
        run(parsed)
    except typer.TyperException as error:  # unknown option, bad choice, extra argument, empty value
        return _fail(_usage_message(error), error.exit_code)
    except (RunError, DomainError) as error:
        return _fail(str(error), 1)
    except (KeyboardInterrupt, typer.Abort):
        return _fail("interrupted", 130)
    except BrokenPipeError:
        _silence_stdout()
        return 1
    except SystemExit as error:  # click's own exit when stdout closes during --help / --version
        _silence_stdout()
        return error.code if isinstance(error.code, int) else 1
    except OSError as error:  # the system refused something we did not expect: not a bug of ours
        where = f" ({error.filename})" if error.filename else ""
        return _fail(f"{os_reason(error)}{where}; check the installation", 1)
    except Exception as error:  # a bug: still one line, never a traceback
        return _fail(
            f"internal error ({type(error).__name__}: {error}); please report it with the command you ran", 1
        )
    return 0
