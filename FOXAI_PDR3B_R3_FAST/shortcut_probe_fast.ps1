[CmdletBinding()]
param(
    [string]$BundleDir = $PSScriptRoot,
    [string]$Root = ""
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

function Normalize-PathValue {
    param([AllowNull()][string]$Value, [AllowNull()][string]$Base = "")

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ""
    }

    $v = [Environment]::ExpandEnvironmentVariables($Value.Trim().Trim('"'))
    try {
        if (-not [System.IO.Path]::IsPathRooted($v) -and
            -not [string]::IsNullOrWhiteSpace($Base)) {
            $v = Join-Path $Base $v
        }
        $v = [System.IO.Path]::GetFullPath($v)
    } catch {
        # Retain readable input if canonicalization fails.
    }

    $v = $v.Replace('/', '\')
    if ($v.Length -gt 3) {
        $v = $v.TrimEnd('\')
    }
    return $v
}

function Paths-Equal {
    param([AllowNull()][string]$A, [AllowNull()][string]$B)
    return [string]::Equals(
        (Normalize-PathValue $A),
        (Normalize-PathValue $B),
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Is-Inside {
    param([AllowNull()][string]$Candidate, [AllowNull()][string]$Parent)

    $c = Normalize-PathValue $Candidate
    $p = Normalize-PathValue $Parent
    if ([string]::IsNullOrWhiteSpace($c) -or
        [string]::IsNullOrWhiteSpace($p)) {
        return $false
    }
    if (Paths-Equal $c $p) {
        return $true
    }
    return $c.StartsWith(
        $p.TrimEnd('\') + '\',
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Get-HashSafe {
    param([AllowNull()][string]$PathValue)

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return $null
    }
    try {
        if (Test-Path -LiteralPath $PathValue -PathType Leaf) {
            return (Get-FileHash -LiteralPath $PathValue -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    } catch {
        return $null
    }
    return $null
}

function Find-FoxaiRoot {
    param([string]$Start, [string]$Explicit)

    if (-not [string]::IsNullOrWhiteSpace($Explicit)) {
        $candidate = Normalize-PathValue $Explicit
        if (Test-Path -LiteralPath $candidate -PathType Container) {
            return $candidate
        }
        throw "Explicit FOXAI root does not exist: $candidate"
    }

    $current = Normalize-PathValue $Start
    for ($i = 0; $i -lt 8; $i++) {
        if ((Test-Path -LiteralPath (Join-Path $current 'core') -PathType Container) -and
            (Test-Path -LiteralPath (Join-Path $current 'Launch FOXAI Workshop.bat') -PathType Leaf)) {
            return $current
        }
        $parent = Split-Path -Parent $current
        if ([string]::IsNullOrWhiteSpace($parent) -or (Paths-Equal $parent $current)) {
            break
        }
        $current = $parent
    }

    if ((Test-Path -LiteralPath 'Z:\FOXAI\core' -PathType Container) -and
        (Test-Path -LiteralPath 'Z:\FOXAI\Launch FOXAI Workshop.bat' -PathType Leaf)) {
        return 'Z:\FOXAI'
    }

    throw "FOXAI root was not found. Extract this folder inside FOXAI or pass -Root X:\FOXAI."
}

function Get-BaselineSnapshot {
    param([string]$FoxaiRoot, [hashtable]$Expected)

    $rows = @()
    foreach ($relative in ($Expected.Keys | Sort-Object)) {
        $full = Join-Path $FoxaiRoot ($relative.Replace('/', '\'))
        $hash = Get-HashSafe $full
        $exists = Test-Path -LiteralPath $full -PathType Leaf
        $rows += [pscustomobject][ordered]@{
            path = $relative
            exists = [bool]$exists
            expected_sha256 = [string]$Expected[$relative]
            actual_sha256 = $hash
            matches_expected = [bool]($exists -and $hash -eq [string]$Expected[$relative])
        }
    }
    return @($rows)
}

function Parse-Icon {
    param([AllowNull()][string]$Raw, [string]$Base)

    if ([string]::IsNullOrWhiteSpace($Raw)) {
        return [pscustomobject][ordered]@{ raw = ""; path = ""; index = $null }
    }

    $value = $Raw.Trim()
    $pathPart = $value
    $index = $null
    $comma = $value.LastIndexOf(',')

    if ($comma -ge 0) {
        $suffix = $value.Substring($comma + 1).Trim()
        $number = 0
        if ([int]::TryParse($suffix, [ref]$number)) {
            $pathPart = $value.Substring(0, $comma).Trim()
            $index = $number
        }
    }

    $iconPath = ""
    if (-not [string]::IsNullOrWhiteSpace($pathPart)) {
        $iconPath = Normalize-PathValue $pathPart $Base
    }

    return [pscustomobject][ordered]@{
        raw = $value
        path = $iconPath
        index = $index
    }
}

function Resolve-Shortcut {
    param(
        [string]$ShortcutPath,
        [string]$FoxaiRoot,
        [string]$UsbRoot,
        [string]$DesktopTarget,
        [string]$WebTarget,
        [object]$Shell
    )

    $before = Get-HashSafe $ShortcutPath
    $base = Split-Path -Parent $ShortcutPath

    $result = [ordered]@{
        shortcut_path = Normalize-PathValue $ShortcutPath
        shortcut_name = [System.IO.Path]::GetFileName($ShortcutPath)
        hash_before = $before
        resolved = $false
        target_raw = ""
        target = ""
        target_exists = $false
        arguments = ""
        working_directory_raw = ""
        working_directory = ""
        working_directory_exists = $false
        icon_raw = ""
        icon_path = ""
        icon_index = $null
        icon_exists = $false
        shortcut_on_usb = [bool](Is-Inside $ShortcutPath $UsbRoot)
        target_on_usb = $false
        target_inside_foxai = $false
        working_directory_inside_foxai = $false
        icon_on_usb = $false
        matches_desktop_target = $false
        matches_web_target = $false
        description = ""
        error = $null
    }

    try {
        $s = $Shell.CreateShortcut($ShortcutPath)
        $target = Normalize-PathValue ([string]$s.TargetPath) $base
        $working = Normalize-PathValue ([string]$s.WorkingDirectory) $base
        $icon = Parse-Icon ([string]$s.IconLocation) $base

        $result.resolved = $true
        $result.target_raw = [string]$s.TargetPath
        $result.target = $target
        $result.target_exists = [bool](
            -not [string]::IsNullOrWhiteSpace($target) -and
            (Test-Path -LiteralPath $target)
        )
        $result.arguments = [string]$s.Arguments
        $result.working_directory_raw = [string]$s.WorkingDirectory
        $result.working_directory = $working
        $result.working_directory_exists = [bool](
            -not [string]::IsNullOrWhiteSpace($working) -and
            (Test-Path -LiteralPath $working -PathType Container)
        )
        $result.icon_raw = [string]$icon.raw
        $result.icon_path = [string]$icon.path
        $result.icon_index = $icon.index
        $result.icon_exists = [bool](
            -not [string]::IsNullOrWhiteSpace($result.icon_path) -and
            (Test-Path -LiteralPath $result.icon_path -PathType Leaf)
        )
        $result.target_on_usb = [bool](Is-Inside $target $UsbRoot)
        $result.target_inside_foxai = [bool](Is-Inside $target $FoxaiRoot)
        $result.working_directory_inside_foxai = [bool](Is-Inside $working $FoxaiRoot)
        $result.icon_on_usb = [bool](Is-Inside $result.icon_path $UsbRoot)
        $result.matches_desktop_target = [bool](Paths-Equal $target $DesktopTarget)
        $result.matches_web_target = [bool](Paths-Equal $target $WebTarget)
        $result.description = [string]$s.Description
    } catch {
        $result.error = $_.Exception.Message
    }

    $result.hash_after = Get-HashSafe $ShortcutPath
    $result.hash_unchanged = [bool]($result.hash_before -eq $result.hash_after)
    return [pscustomobject]$result
}

function Get-DirectShortcuts {
    param([string]$DirectoryPath, [string]$Label)

    Write-Host "Checking: $Label"
    Write-Host "  $DirectoryPath"

    if (-not (Test-Path -LiteralPath $DirectoryPath -PathType Container)) {
        return @()
    }

    try {
        return @(
            Get-ChildItem -LiteralPath $DirectoryPath -File -Force -Filter '*.lnk' -ErrorAction Stop |
            Select-Object -ExpandProperty FullName
        )
    } catch {
        Write-Host "  Could not read this optional folder: $($_.Exception.Message)"
        return @()
    }
}

function Get-SourceEvidence {
    param([string]$FullPath, [string]$Relative)

    $exists = Test-Path -LiteralPath $FullPath -PathType Leaf
    $before = Get-HashSafe $FullPath
    $lines = @()
    $errorText = $null

    if ($exists) {
        try {
            $lineNo = 0
            foreach ($line in (Get-Content -LiteralPath $FullPath -ErrorAction Stop)) {
                $lineNo++
                if ($line -match '(?i)CreateShortcut|\.lnk|TargetPath|WorkingDirectory|IconLocation|Launch FOXAI|START_FOXAI|foxai_fixed|Desktop') {
                    $lines += [pscustomobject][ordered]@{
                        line = $lineNo
                        text = $line
                    }
                }
            }
        } catch {
            $errorText = $_.Exception.Message
        }
    }

    $after = Get-HashSafe $FullPath
    return [pscustomobject][ordered]@{
        path = $Relative
        exists = [bool]$exists
        hash_before = $before
        hash_after = $after
        hash_unchanged = [bool]($before -eq $after)
        matched_lines = @($lines)
        error = $errorText
    }
}

$expectedHashes = @{
    'Config/fleet_registry.json' = '18745be73f67e073c002bb645a3c0eaad0a3090ebee1b3bb547ddcc2f147bdb6'
    'Config/model_sources.json' = 'c17eb3b8b6c93734f7e117522213c95af6c105fe26400d0560768fe586e21c91'
    'core/engineer_agent.py' = 'f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19'
    'core/foxai_web.py' = 'ca45bfc72ce73a47df3ca11b1d1f0564b070cf70ae766a956fb1daaff3dfc2a7'
    'core/model_sources.py' = 'e00a861265eff8826c4d7eeb89b3765e719b88f349811a2e608525d8a3f91ea2'
    'core/security_containment.py' = '9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24'
    'core/server.py' = '238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81'
    'core/service_registry.py' = 'cc798df061a27a51c4ea1f64b3757d2a92724a9a5768e4c190846966efe0251b'
    'env/python/python314._pth' = '48d77ccee161647ef7053cb563d3b37b4053938d5ad92ae64ccedc2165bcd42d'
    'Launch FOXAI Workshop.bat' = '7f974eeeaa66c6fd331b6b3e8cb5f312d25a410761817ad35408ccb47acd4480'
    'START_FOXAI_WEB_PORTABLE.bat' = '834e129be2d41405be40e1ea5aeca6d7a96b4faaf3b72c906487e902a9dca3b1'
    'tests/test_boundary_watch.py' = 'b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382'
    'tests/test_model_sources.py' = 'ec94f8b8d90d36f05385db74400dd99b436cd4e488b1b517bcb77442a16fc6f2'
    'ui/main_window.py' = '2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3'
}

$started = [DateTime]::UtcNow
$bundlePath = Normalize-PathValue $BundleDir
$foxaiRoot = Find-FoxaiRoot $bundlePath $Root
$usbRoot = [System.IO.Path]::GetPathRoot($foxaiRoot)
$desktopTarget = Join-Path $foxaiRoot 'Launch FOXAI Workshop.bat'
$webTarget = Join-Path $foxaiRoot 'START_FOXAI_WEB_PORTABLE.bat'

$outputRoot = Join-Path $bundlePath 'probe_output'
$outputDir = Join-Path $outputRoot ([DateTime]::UtcNow.ToString("yyyyMMdd'T'HHmmss'Z'"))
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

Write-Host ""
Write-Host "FOXAI root: $foxaiRoot"
Write-Host "USB root:   $usbRoot"
Write-Host "This probe checks direct files only. No recursive drive scan."
Write-Host ""

$beforeBaselines = Get-BaselineSnapshot $foxaiRoot $expectedHashes
$failure = $null
$records = @()
$sourceEvidence = @()

try {
    $locations = @(
        [pscustomobject][ordered]@{ label = 'USB root'; path = $usbRoot },
        [pscustomobject][ordered]@{ label = 'FOXAI root'; path = $foxaiRoot },
        [pscustomobject][ordered]@{ label = 'FOXAI Memory folder'; path = (Join-Path $foxaiRoot 'Memory') },
        [pscustomobject][ordered]@{ label = 'Current user Desktop'; path = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop) },
        [pscustomobject][ordered]@{ label = 'Public Desktop'; path = [Environment]::GetFolderPath([Environment+SpecialFolder]::CommonDesktopDirectory) },
        [pscustomobject][ordered]@{ label = 'Current user Start Menu Programs'; path = [Environment]::GetFolderPath([Environment+SpecialFolder]::Programs) },
        [pscustomobject][ordered]@{ label = 'Common Start Menu Programs'; path = [Environment]::GetFolderPath([Environment+SpecialFolder]::CommonPrograms) }
    )

    $seenPaths = @{}
    $shortcutFiles = @()
    foreach ($location in $locations) {
        $normalizedLocation = Normalize-PathValue ([string]$location.path)
        if ([string]::IsNullOrWhiteSpace($normalizedLocation)) {
            continue
        }
        $locationKey = $normalizedLocation.ToLowerInvariant()
        if ($seenPaths.ContainsKey($locationKey)) {
            continue
        }
        $seenPaths[$locationKey] = $true

        foreach ($pathValue in (Get-DirectShortcuts $normalizedLocation ([string]$location.label))) {
            $shortcutKey = (Normalize-PathValue $pathValue).ToLowerInvariant()
            if (-not $seenPaths.ContainsKey("file:$shortcutKey")) {
                $seenPaths["file:$shortcutKey"] = $true
                $shortcutFiles += Normalize-PathValue $pathValue
            }
        }
    }

    Write-Host ""
    Write-Host "Resolving $($shortcutFiles.Count) directly discovered shortcut(s)..."

    $shell = New-Object -ComObject WScript.Shell
    foreach ($shortcutPath in ($shortcutFiles | Sort-Object)) {
        Write-Host "  $shortcutPath"
        $records += Resolve-Shortcut `
            $shortcutPath `
            $foxaiRoot `
            $usbRoot `
            $desktopTarget `
            $webTarget `
            $shell
    }

    $sourceCandidates = @(
        'Create Desktop Shortcut.ps1',
        'Memory\Create Desktop Shortcut.ps1',
        'Launch FOXAI Workshop.bat',
        'START_FOXAI_WEB_PORTABLE.bat'
    )

    Write-Host ""
    Write-Host "Reading existing shortcut-contract source evidence..."
    foreach ($relative in $sourceCandidates) {
        $sourceEvidence += Get-SourceEvidence (Join-Path $foxaiRoot $relative) $relative
    }
} catch {
    $failure = [pscustomobject][ordered]@{
        type = $_.Exception.GetType().FullName
        message = $_.Exception.Message
    }
}

$afterBaselines = Get-BaselineSnapshot $foxaiRoot $expectedHashes

$baselineBeforePassed = [bool](
    $beforeBaselines.Count -eq $expectedHashes.Count -and
    @($beforeBaselines | Where-Object { -not $_.matches_expected }).Count -eq 0
)
$baselineAfterPassed = [bool](
    $afterBaselines.Count -eq $expectedHashes.Count -and
    @($afterBaselines | Where-Object { -not $_.matches_expected }).Count -eq 0
)
$shortcutHashesUnchanged = [bool](
    @($records | Where-Object { -not $_.hash_unchanged }).Count -eq 0
)
$sourceHashesUnchanged = [bool](
    @($sourceEvidence | Where-Object { -not $_.hash_unchanged }).Count -eq 0
)

$desktopMatches = @($records | Where-Object { $_.matches_desktop_target })
$webMatches = @($records | Where-Object { $_.matches_web_target })
$namedCandidates = @($records | Where-Object {
    $nameLower = ([string]$_.shortcut_name).ToLowerInvariant()
    $nameLower.Contains('foxai') -or
    $nameLower.Contains('workshop') -or
    $nameLower.Contains('kayock')
})

$verified = [bool](
    $null -eq $failure -and
    $baselineBeforePassed -and
    $baselineAfterPassed -and
    $shortcutHashesUnchanged -and
    $sourceHashesUnchanged
)

$elapsed = [Math]::Round(([DateTime]::UtcNow - $started).TotalSeconds, 2)

$receipt = [ordered]@{
    action = 'foxai_pdr3b_r3_fast_shortcut_contract_probe'
    created_utc = $started.ToString("o")
    completed_utc = [DateTime]::UtcNow.ToString("o")
    elapsed_seconds = $elapsed
    state = if ($verified) { 'read_only_probe_complete' } else { 'stopped_fail_closed' }
    verified = $verified
    read_only = $true
    recursive_drive_scan = $false
    apply_capability_present = $false
    live_files_modified = $false
    shortcut_changes = $false
    launcher_changes = $false
    runtime_changes = $false
    package_install = $false
    network_access = $false
    desktop_gui_launched = $false
    phase3c_blocked = $true
    foxai_root = $foxaiRoot
    usb_root = $usbRoot
    expected_desktop_target = $desktopTarget
    expected_web_target = $webTarget
    protected_baselines_before = $beforeBaselines
    protected_baselines_after = $afterBaselines
    baseline_before_passed = $baselineBeforePassed
    baseline_after_passed = $baselineAfterPassed
    shortcut_hashes_unchanged = $shortcutHashesUnchanged
    source_hashes_unchanged = $sourceHashesUnchanged
    shortcut_count = $records.Count
    desktop_exact_matches = $desktopMatches.Count
    web_exact_matches = $webMatches.Count
    named_candidates = $namedCandidates.Count
    failure = $failure
}

$inventory = [ordered]@{
    created_utc = [DateTime]::UtcNow.ToString("o")
    foxai_root = $foxaiRoot
    usb_root = $usbRoot
    elapsed_seconds = $elapsed
    expected_targets = [ordered]@{
        desktop = $desktopTarget
        web = $webTarget
    }
    shortcuts = @($records | Sort-Object shortcut_path)
    desktop_matches = @($desktopMatches)
    web_matches = @($webMatches)
    named_candidates = @($namedCandidates)
    source_evidence = @($sourceEvidence)
}

$receipt | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath (Join-Path $outputDir 'FAST_PROBE_RECEIPT.json') -Encoding UTF8
$inventory | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath (Join-Path $outputDir 'FAST_SHORTCUT_INVENTORY.json') -Encoding UTF8

$report = @()
$report += '# FOXAI Phase 3B-R3 Fast Shortcut Probe'
$report += ''
$report += "State: $($receipt.state)"
$report += "Verified: $verified"
$report += "Elapsed seconds: $elapsed"
$report += "Recursive drive scan: False"
$report += "FOXAI root: $foxaiRoot"
$report += "USB root: $usbRoot"
$report += ''
$report += '## Results'
$report += ''
$report += "Direct shortcuts checked: $($records.Count)"
$report += "Desktop target exact matches: $($desktopMatches.Count)"
$report += "Web target exact matches: $($webMatches.Count)"
$report += "Named FOXAI or Kayock candidates: $($namedCandidates.Count)"
$report += ''
foreach ($item in ($namedCandidates | Sort-Object shortcut_path)) {
    $report += "Candidate: $($item.shortcut_path)"
    $report += "  Target: $($item.target)"
    $report += "  Working directory: $($item.working_directory)"
    $report += "  Icon: $($item.icon_path)"
    $report += "  Hash unchanged: $($item.hash_unchanged)"
}
$report += ''
$report += '## Safety'
$report += ''
$report += "Protected baselines passed before: $baselineBeforePassed"
$report += "Protected baselines passed after: $baselineAfterPassed"
$report += "Shortcut hashes unchanged: $shortcutHashesUnchanged"
$report += "Source hashes unchanged: $sourceHashesUnchanged"
$report += 'No shortcut, launcher, runtime, package, or live FOXAI file was changed.'
$report += 'Phase 3C remains blocked.'
if ($null -ne $failure) {
    $report += ''
    $report += '## Failure'
    $report += ''
    $report += "$($failure.type): $($failure.message)"
}

$report | Set-Content -LiteralPath (Join-Path $outputDir 'FAST_PROBE_REPORT.md') -Encoding UTF8

Write-Host ""
Write-Host "Fast probe complete in $elapsed second(s)."
Write-Host "Output: $outputDir"
Write-Host "Verified: $verified"
Write-Host "Desktop exact matches: $($desktopMatches.Count)"
Write-Host "Web exact matches: $($webMatches.Count)"
Write-Host "Phase 3C remains blocked."

if ($verified) {
    exit 0
}
exit 2
