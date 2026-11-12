# Install uv (when missing) and dbtscope for the current user.
# Windows PowerShell 5.1 and PowerShell 7. Design: docs/architecture/2026-11-12-m9.1-install-scripts.md (D-058).
#
# Run it in a PowerShell window opened in the folder that holds the wheel (docs/user-guide.md, Quick install).
param(
    [Parameter(Position = 0)][string]$Wheel,
    [switch]$FromGitHub,
    [string]$Ref,
    [switch]$SkipProfile,
    [string]$ProfilePath = $PROFILE.CurrentUserCurrentHost,
    [switch]$Help,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest
)

Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'

$GitHubUrl = 'https://github.com/christophebnx/dbtscope'
$UvInstallerUrl = 'https://astral.sh/uv/install.ps1'
$BeginMarker = '# >>> dbtscope install >>>'
$EndMarker = '# <<< dbtscope install <<<'
$IsWindowsHost = ($env:OS -eq 'Windows_NT')
$script:NativeOutput = @()
$OriginalGitPrompt = $env:GIT_TERMINAL_PROMPT

function Say([string]$Text) { [Console]::Out.WriteLine("dbtscope install: $Text") }

function Fail([string]$Text) {
    [Console]::Error.WriteLine("dbtscope install: error: $Text")
    exit 1
}

function Fail-Usage([string]$Text) {
    [Console]::Error.WriteLine("dbtscope install: error: $Text")
    [Console]::Error.WriteLine('dbtscope install: try: .\install.ps1 -Help')
    exit 2
}

function Show-Usage {
    @'
Install uv (when missing) and dbtscope for the current user.

Usage:
  .\install.ps1                         install the single dbtscope-*.whl next to this script
  .\install.ps1 -Wheel FILE             install this wheel (a lone FILE argument works too)
  .\install.ps1 -FromGitHub             install from https://github.com/christophebnx/dbtscope
  .\install.ps1 -FromGitHub -Ref TAG_OR_COMMIT

Options:
  -Wheel FILE     wheel to install
  -FromGitHub     install from the GitHub repository (needs git and read access)
  -Ref REF        with -FromGitHub: tag, branch or commit to install
  -SkipProfile    do not add the PATH block to your PowerShell profile
  -ProfilePath F  write the PATH block to this profile file (default: your current-host profile)
  -Help           show this help and exit

If PowerShell refuses to run this script, see docs/user-guide.md (Quick install) for the one-line fix.

Never asks a question. Exit codes: 0 installed, 1 an install step failed, 2 usage error.
'@ | ForEach-Object { [Console]::Out.WriteLine($_) }
}

# Run a native program: stderr is never redirected (PowerShell 5.1 would wrap it in red error records),
# the exit code is returned, and stdout is kept in $script:NativeOutput when -Capture is given.
function Invoke-Native([string]$Path, [string[]]$Arguments, [switch]$Capture) {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $PSNativeCommandUseErrorActionPreference = $false
    $global:LASTEXITCODE = $null
    $encoding = $null
    try {
        if ($Capture) {
            # uv writes UTF-8; Windows PowerShell 5.1 would decode it with the OEM code page.
            try {
                $encoding = [Console]::OutputEncoding
                [Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
            }
            catch { $encoding = $null }
            $script:NativeOutput = @(& $Path @Arguments)
        }
        else {
            & $Path @Arguments | Out-Host
        }
    }
    finally {
        $ErrorActionPreference = $previous
        if ($encoding) { try { [Console]::OutputEncoding = $encoding } catch { $null = $_ } }
    }
    if ($null -eq $global:LASTEXITCODE) { return 1 }
    return [int]$global:LASTEXITCODE
}

function Find-Program([string]$Name) {
    $command = Get-Command $Name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) { return $command.Source }
    return $null
}

# Reload the user and machine Path from the registry, keeping what the session already has.
function Sync-SessionPath {
    if (-not $IsWindowsHost) { return }
    $separator = [IO.Path]::PathSeparator
    $known = @($env:Path -split $separator | Where-Object { $_ })
    foreach ($scope in 'User', 'Machine') {
        $value = [Environment]::GetEnvironmentVariable('Path', $scope)
        if (-not $value) { continue }
        foreach ($entry in ($value -split $separator | Where-Object { $_ })) {
            if ($known -notcontains $entry) { $known += $entry }
        }
    }
    $env:Path = $known -join $separator
}

function Find-Uv {
    $found = Find-Program 'uv'
    if ($found) { return $found }
    $folders = @($env:UV_INSTALL_DIR, $env:XDG_BIN_HOME, (Join-Path $HOME '.local\bin'))
    if ($env:LOCALAPPDATA) { $folders += (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links') }
    foreach ($folder in $folders) {
        if (-not $folder) { continue }
        foreach ($name in 'uv.exe', 'uv') {
            $candidate = Join-Path $folder $name
            if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
        }
    }
    return $null
}

# Install uv with its official per-user installer (in a child PowerShell), winget as a fallback.
function Install-Uv {
    $hint = 'install uv by hand (docs/user-guide.md, section Install uv) and run this script again; a company proxy is the usual cause'
    if (-not $IsWindowsHost) { Fail "uv not found; run install.sh instead, or $hint" }
    Say "uv not found; installing it with the official installer ($UvInstallerUrl)"
    $tls = '[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12'
    $shell = (Get-Process -Id $PID).Path
    $null = Invoke-Native $shell @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', "$tls; irm $UvInstallerUrl | iex")
    Sync-SessionPath
    $uv = Find-Uv
    if (-not $uv -and (Find-Program 'winget')) {
        Say 'the installer did not work; trying winget'
        $null = Invoke-Native (Find-Program 'winget') @('install', '--id=astral-sh.uv', '-e', '--scope', 'user', '--accept-source-agreements', '--accept-package-agreements')
        Sync-SessionPath
        $uv = Find-Uv
    }
    if (-not $uv) { Fail "uv could not be installed; $hint" }
    return $uv
}

# The single wheel next to this script, else a usage error (none, or several).
function Get-WheelNextToScript {
    $found = @(Get-ChildItem -LiteralPath $PSScriptRoot -Filter 'dbtscope-*.whl' -File -ErrorAction SilentlyContinue)
    if ($found.Count -eq 0) {
        Fail-Usage "no wheel found next to the script ($PSScriptRoot); pass a wheel path, or -FromGitHub if you can read the GitHub repository"
    }
    if ($found.Count -gt 1) {
        $names = ($found | ForEach-Object { $_.FullName }) -join "`n  "
        Fail-Usage "several wheels next to the script, pass the one to install with -Wheel:`n  $names"
    }
    return $found[0].FullName
}

# Check git and read access to the repository, without ever prompting.
function Test-GitHubAccess {
    $git = Find-Program 'git'
    if (-not $git) {
        Fail 'git not found; install it (Windows: winget install --id Git.Git -e) or install from a wheel file instead'
    }
    $env:GIT_TERMINAL_PROMPT = '0'   # restored when the script ends; also covers uv's own git call
    $code = Invoke-Native $git @('ls-remote', $GitHubUrl) -Capture
    if ($code -ne 0) {
        Fail "cannot read the repository $GitHubUrl (git's message is above: private repository without access, or network); set up access (docs/user-guide.md, section Access to the private repository) or install from a wheel file"
    }
}

# The execution policy a new window will get (the Process scope is ignored on purpose).
function Get-NewWindowPolicy {
    foreach ($scope in 'MachinePolicy', 'UserPolicy', 'CurrentUser', 'LocalMachine') {
        $policy = [string](Get-ExecutionPolicy -Scope $scope)
        if ($policy -ne 'Undefined') { return $policy }
    }
    return 'Restricted'
}

# The bin folder as a profile line: under $HOME it is written relative to $HOME, which keeps the block ASCII.
function Get-BinDirExpression([string]$BinDir) {
    $home_ = $HOME.TrimEnd('\', '/')
    if ($BinDir.Length -gt $home_.Length + 1 -and $BinDir.StartsWith($home_ + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        $relative = $BinDir.Substring($home_.Length + 1).Replace("'", "''")
        return "Join-Path `$HOME '$relative'"
    }
    return "'" + $BinDir.Replace("'", "''") + "'"
}

function Get-ProfileBlock([string]$BinDir) {
    $lines = @(
        $BeginMarker,
        ('$dbtscopeBin = ' + (Get-BinDirExpression $BinDir)),
        'if ((Test-Path $dbtscopeBin) -and -not (($env:Path -split '';'') -contains $dbtscopeBin)) { $env:Path = "$dbtscopeBin;$env:Path" }',
        $EndMarker
    )
    return (($lines -join "`r`n") + "`r`n")
}

# Add or replace the marked block in the profile: bytes in, temp file, replace (the user's encoding is kept).
function Set-ProfileBlock([string]$BinDir) {
    $path = $ProfilePath
    $block = Get-ProfileBlock $BinDir
    $latin1 = [Text.Encoding]::GetEncoding(28591)
    $newFile = -not (Test-Path -LiteralPath $path -PathType Leaf)
    if ($block -match '[^\x00-\x7F]') {
        # a bin folder outside $HOME with non-ASCII characters: UTF-8 bytes (with a BOM in a new file, which 5.1 needs)
        $block = $latin1.GetString([Text.Encoding]::UTF8.GetBytes($block))
        if ($newFile) { $block = $latin1.GetString([byte[]](0xEF, 0xBB, 0xBF)) + $block }
    }
    $bytes = @()
    if (Test-Path -LiteralPath $path -PathType Leaf) { $bytes = [IO.File]::ReadAllBytes($path) }
    if ($bytes.Length -ge 2 -and (($bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) -or ($bytes[0] -eq 0xFE -and $bytes[1] -eq 0xFF))) {
        Say "your profile ($path) is UTF-16, so it was not changed; paste this block into it to keep dbtscope on PATH:"
        [Console]::Out.WriteLine($block)
        return
    }
    $text = $latin1.GetString($bytes)
    $start = $text.IndexOf($BeginMarker)
    $end = $text.IndexOf($EndMarker)
    if (($start -ge 0 -or $end -ge 0) -and ($start -lt 0 -or $end -lt $start)) {
        Fail "your profile ($path) has a dbtscope begin or end marker without its pair, so nothing was changed; fix or remove the marker lines ($BeginMarker, $EndMarker) and run this script again"
    }
    if ($start -ge 0) {
        $stop = $end + $EndMarker.Length
        while ($stop -lt $text.Length -and ($text[$stop] -eq "`r" -or $text[$stop] -eq "`n")) { $stop++ }
        $updated = $text.Substring(0, $start) + $block + $text.Substring($stop)
    }
    else {
        $gap = ''
        if ($text.Length -gt 0 -and -not $text.EndsWith("`n")) { $gap = "`r`n" }
        $updated = $text + $gap + $block
    }
    $folder = Split-Path -Parent $path
    if (-not (Test-Path -LiteralPath $folder)) { $null = New-Item -ItemType Directory -Force -Path $folder }
    $temporary = "$path.dbtscope.tmp"
    try {
        $stream = [IO.File]::Create($temporary)
        try {
            $data = $latin1.GetBytes($updated)
            $stream.Write($data, 0, $data.Length)
            $stream.Flush($true)
        }
        finally {
            $stream.Dispose()
        }
        if (-not $newFile) { [IO.File]::Replace($temporary, $path, [NullString]::Value) }
        else { Move-Item -LiteralPath $temporary -Destination $path }
    }
    finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue }
    }
    Say "PATH block written to your PowerShell profile ($path)"
}

function Add-ToSessionPath([string]$BinDir) {
    $separator = [IO.Path]::PathSeparator
    if (@($env:Path -split $separator) -notcontains $BinDir) { $env:Path = "$BinDir$separator$env:Path" }
}

function Update-Profile([string]$BinDir) {
    if ($SkipProfile) { return }
    $explicit = $PSBoundParameters.ContainsKey('ProfilePath')   # a path given by the caller is written as is (tests)
    if (-not $explicit -and -not $IsWindowsHost) { return }
    $policy = Get-NewWindowPolicy
    if (-not $explicit -and @('RemoteSigned', 'Unrestricted', 'Bypass') -notcontains $policy) {
        Say "execution policy is $policy, so your profile was not changed; a new terminal is needed, and if dbtscope is still not found, close and reopen Windows Terminal or VS Code"
        return
    }
    Set-ProfileBlock $BinDir
}

function Get-DbtscopeProgram([string]$BinDir) {
    foreach ($name in 'dbtscope.exe', 'dbtscope.cmd', 'dbtscope') {
        $candidate = Join-Path $BinDir $name
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    return $null
}

function Main {
    if ($Help -or @($Rest) -contains '-h' -or @($Rest) -contains '--help') { Show-Usage; exit 0 }
    if ($Wheel -and $Wheel.StartsWith('-')) {
        if (@('-h', '--help', '-?') -contains $Wheel) { Show-Usage; exit 0 }
        Fail-Usage "unknown option: $Wheel (options are written -Wheel, -FromGitHub, -Ref, -SkipProfile, -ProfilePath, -Help)"
    }
    foreach ($extra in @($Rest)) {
        if ($extra -and $extra.StartsWith('-')) { Fail-Usage "unknown option: $extra" }
        if ($extra) { Fail-Usage 'only one wheel can be given' }
    }
    if ($FromGitHub -and $Wheel) { Fail-Usage '-Wheel and -FromGitHub cannot be used together' }
    if ($Ref -and -not $FromGitHub) { Fail-Usage '-Ref needs -FromGitHub' }
    if ($Wheel) {
        if (-not $Wheel.EndsWith('.whl')) { Fail-Usage "not a wheel file (expected a .whl): $Wheel" }
        if (-not (Test-Path -LiteralPath $Wheel -PathType Leaf)) { Fail-Usage "wheel not found: $Wheel" }
        $Wheel = (Resolve-Path -LiteralPath $Wheel).ProviderPath
    }
    elseif (-not $FromGitHub) {
        $Wheel = Get-WheelNextToScript
    }

    Say 'step 1/4: looking for uv'
    $uv = Find-Uv
    if (-not $uv) { $uv = Install-Uv }
    Add-ToSessionPath (Split-Path -Parent $uv)
    Say "using uv: $uv"

    if ($FromGitHub) {
        Test-GitHubAccess
        $target = "git+$GitHubUrl"
        if ($Ref) { $target = "$target@$Ref" }
    }
    else {
        $target = $Wheel
    }

    Say "step 2/4: installing dbtscope from $target"
    if ((Invoke-Native $uv @('tool', 'install', '--reinstall', $target)) -ne 0) {
        Fail "uv tool install failed (see uv's messages above)"
    }

    Say 'step 3/4: making dbtscope reachable'
    if ((Invoke-Native $uv @('tool', 'update-shell')) -ne 0) {
        Say "warning: uv tool update-shell failed (see uv's messages above); PATH may need a manual change"
    }
    if ((Invoke-Native $uv @('tool', 'dir', '--bin') -Capture) -ne 0 -or $script:NativeOutput.Count -eq 0) {
        Fail "uv tool dir --bin failed (see uv's messages above)"
    }
    $binDir = ([string]$script:NativeOutput[0]).Trim()
    Add-ToSessionPath $binDir
    Update-Profile $binDir

    Say 'step 4/4: checking the install'
    $program = Get-DbtscopeProgram $binDir
    if (-not $program) { Fail "dbtscope was not installed in $binDir; run this script again, or see uv's messages above" }
    if ((Invoke-Native $program @('--version') -Capture) -ne 0 -or $script:NativeOutput.Count -eq 0) {
        Fail "$program --version failed; run this script again"
    }
    $version = ([string]$script:NativeOutput[0]).Trim()
    Say $version

    $dbt = Find-Program 'dbt'
    if ($dbt) {
        Say "dbt found: $dbt; live mode will run dbt parse with it"
    }
    else {
        Say "dbt not found on PATH: dbtscope can still map an existing manifest (--no-parse, --manifest); for live mode, install dbt with your project's adapter the way your team does"
    }

    if (Find-Program 'dbtscope') {
        Say "$version is installed and ready in this terminal"
    }
    else {
        Say "$version is installed; open a new terminal to use it (if dbtscope is still not found, close and reopen Windows Terminal or VS Code)"
    }
    exit 0
}

try {
    Main
}
catch {
    Fail "unexpected failure: $($_.Exception.Message); run this script again, or see docs/user-guide.md (Installation problems)"
}
finally {
    if ($null -eq $OriginalGitPrompt) { Remove-Item Env:GIT_TERMINAL_PROMPT -ErrorAction SilentlyContinue }
    else { $env:GIT_TERMINAL_PROMPT = $OriginalGitPrompt }
}
