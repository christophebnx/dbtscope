#!/bin/sh
# Install uv (when missing) and dbtscope for the current user. macOS and Linux, POSIX sh.
# Usage: sh install.sh [--wheel FILE | FILE | --from-github [--ref REF]] [--help]
# Design: docs/architecture/2026-11-12-m8.1-install-scripts.md (D-058).
set -eu

GITHUB_URL="https://github.com/christophebnx/dbtscope"
UV_INSTALLER_URL="https://astral.sh/uv/install.sh"

say() { printf 'dbtscope install: %s\n' "$*"; }

fail() {
    printf 'dbtscope install: error: %s\n' "$*" >&2
    exit 1
}

usage_error() {
    printf 'dbtscope install: error: %s\n' "$*" >&2
    printf 'dbtscope install: try: sh install.sh --help\n' >&2
    exit 2
}

usage() {
    while IFS= read -r line; do printf '%s\n' "$line"; done <<'TEXT'
Install uv (when missing) and dbtscope for the current user.

Usage:
  sh install.sh                      install the single dbtscope-*.whl next to this script
  sh install.sh --wheel FILE         install this wheel (a lone FILE argument works too)
  sh install.sh --from-github        install from https://github.com/christophebnx/dbtscope
  sh install.sh --from-github --ref TAG_OR_COMMIT

Options:
  --wheel FILE      wheel to install
  --from-github     install from the GitHub repository (needs git and read access)
  --ref REF         with --from-github: tag, branch or commit to install
  -h, --help        show this help and exit

Never asks a question, never needs administrator rights. Exit codes: 0 installed,
1 an install step failed, 2 usage error.
TEXT
}

# Absolute path of an existing file (the folder is resolved with cd and pwd).
abs_path() {
    dir=${1%/*}
    if [ "$dir" = "$1" ]; then dir=.; fi
    dir=$(CDPATH= cd -- "$dir" && pwd) || return 1
    printf '%s/%s\n' "$dir" "${1##*/}"
}

# Set UV to the uv executable, from PATH or the default install locations.
find_uv() {
    if command -v uv >/dev/null 2>&1; then
        UV=$(command -v uv)
        return 0
    fi
    for dir in "${UV_INSTALL_DIR:-}" "${XDG_BIN_HOME:-}" "$HOME/.local/bin"; do
        if [ -n "$dir" ] && [ -x "$dir/uv" ]; then
            UV="$dir/uv"
            return 0
        fi
    done
    return 1
}

# Install uv with the official per-user installer, then look for it again.
install_uv() {
    say "uv not found; installing it with the official installer ($UV_INSTALLER_URL)"
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf "$UV_INSTALLER_URL" | sh || true
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- "$UV_INSTALLER_URL" | sh || true
    else
        fail "neither curl nor wget found; install uv by hand (docs/user-guide.md section Install uv) and run this script again"
    fi
    find_uv || fail "uv could not be installed; install it by hand (docs/user-guide.md section Install uv), a company proxy is the usual cause"
}

# The single wheel next to this script, else exit 2 (none, or several).
wheel_next_to_script() {
    here=$1
    found=""
    count=0
    for candidate in "$here"/dbtscope-*.whl; do
        if [ -f "$candidate" ]; then
            found=$candidate
            count=$((count + 1))
            list="${list:-}
  $candidate"
        fi
    done
    if [ "$count" -eq 0 ]; then
        usage_error "no wheel found next to the script ($here); pass a wheel path, or --from-github if you can read the GitHub repository"
    fi
    if [ "$count" -gt 1 ]; then
        usage_error "several wheels next to the script, pass the one to install with --wheel:$list"
    fi
    WHEEL=$found
}

# Check git and read access to the repository, without ever prompting.
check_github() {
    command -v git >/dev/null 2>&1 || fail "git not found; install it (macOS: xcode-select --install; Linux: your package manager) or install from a wheel file instead"
    GIT_TERMINAL_PROMPT=0 git ls-remote "$GITHUB_URL" >/dev/null ||
        fail "cannot read the repository $GITHUB_URL (git's message is above: private repository without access, or network); set up access (docs/user-guide.md section Access to the private repository) or install from a wheel file"
}

WHEEL=""
FROM_GITHUB=0
REF=""
while [ $# -gt 0 ]; do
    case $1 in
        -h | --help)
            usage
            exit 0
            ;;
        --wheel)
            [ $# -ge 2 ] || usage_error "--wheel needs a file"
            [ -z "$WHEEL" ] || usage_error "only one wheel can be given"
            WHEEL=$2
            shift
            ;;
        --from-github) FROM_GITHUB=1 ;;
        --ref)
            [ $# -ge 2 ] || usage_error "--ref needs a tag or a commit"
            REF=$2
            shift
            ;;
        -*) usage_error "unknown option: $1" ;;
        *)
            [ -z "$WHEEL" ] || usage_error "only one wheel can be given"
            WHEEL=$1
            ;;
    esac
    shift
done

if [ "$FROM_GITHUB" -eq 1 ] && [ -n "$WHEEL" ]; then usage_error "--wheel and --from-github cannot be used together"; fi
if [ "$FROM_GITHUB" -eq 0 ] && [ -n "$REF" ]; then usage_error "--ref needs --from-github"; fi
if [ -n "$WHEEL" ]; then
    case $WHEEL in
        *.whl) ;;
        *) usage_error "not a wheel file (expected a .whl): $WHEEL" ;;
    esac
    [ -f "$WHEEL" ] || usage_error "wheel not found: $WHEEL"
    WHEEL=$(abs_path "$WHEEL")
fi

case $0 in
    */*) script_dir=${0%/*} ;;
    *) script_dir=. ;;
esac
script_dir=$(CDPATH= cd -- "$script_dir" && pwd)

if [ "$FROM_GITHUB" -eq 0 ] && [ -z "$WHEEL" ]; then wheel_next_to_script "$script_dir"; fi

say "step 1/4: looking for uv"
UV=""
find_uv || install_uv
PATH="${UV%/*}:$PATH"
export PATH
say "using uv: $UV"

if [ "$FROM_GITHUB" -eq 1 ]; then
    check_github
    TARGET="git+$GITHUB_URL"
    if [ -n "$REF" ]; then TARGET="$TARGET@$REF"; fi
else
    TARGET=$WHEEL
fi

say "step 2/4: installing dbtscope from $TARGET"
GIT_TERMINAL_PROMPT=0 "$UV" tool install --reinstall "$TARGET" || fail "uv tool install failed (see uv's messages above)"

say "step 3/4: making dbtscope reachable"
"$UV" tool update-shell || say "warning: uv tool update-shell failed (see uv's messages above); PATH may need a manual change"
BIN=$("$UV" tool dir --bin) || fail "uv tool dir --bin failed (see uv's messages above)"

say "step 4/4: checking the install"
[ -x "$BIN/dbtscope" ] || fail "dbtscope was not installed in $BIN; run this script again, or see uv's messages above"
VERSION=$("$BIN/dbtscope" --version) || fail "$BIN/dbtscope --version failed; run this script again"
say "$VERSION"

if command -v dbt >/dev/null 2>&1; then
    say "dbt found: $(command -v dbt); live mode will run dbt parse with it"
else
    say "dbt not found on PATH: dbtscope can still map an existing manifest (--no-parse, --manifest); for live mode, install dbt with your project's adapter the way your team does"
fi

if command -v dbtscope >/dev/null 2>&1; then
    say "$VERSION is installed and ready in this terminal"
else
    say "$VERSION is installed; open a new terminal to use it (or run: export PATH=\"$BIN:\$PATH\")"
fi
