[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$BundleDir = $PSScriptRoot,

    [Parameter(Mandatory = $false)]
    [string]$Root = ""
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

function Get-IsoUtc {
    return [DateTime]::UtcNow.ToString("o")
}

function Get-UtcStamp {
    return [DateTime]::UtcNow.ToString("yyyyMMdd'T'HHmmss'Z'")
}

function Normalize-PathString {
    param(
        [AllowNull()][string]$PathValue,
        [AllowNull()][string]$BaseDirectory = ""
    )

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return ""
    }

    $value = [Environment]::ExpandEnvironmentVariables($PathValue.Trim())
    $value = $value.Trim('"')

    if ($value -match '^[A-Za-z][A-Za-z0-9+.-]*://') {
        return $value
    }

    try {
        if (-not [System.IO.Path]::IsPathRooted($value) -and
            -not [string]::IsNullOrWhiteSpace($BaseDirectory)) {
            $value = Join-Path $BaseDirectory $value
        }
        $value = [System.IO.Path]::GetFullPath($value)
    } catch {
        # Keep the readable value if Windows cannot canonicalize it.
    }

    $value = $value.Replace('/', '\')
    if ($value.Length -gt 3) {
        $value = $value.TrimEnd('\')
    }
    return $value
}

function Paths-Equal {
    param([AllowNull()][string]$Left, [AllowNull()][string]$Right)

    $a = Normalize-PathString $Left
    $b = Normalize-PathString $Right
    return [string]::Equals($a, $b, [System.StringComparison]::OrdinalIgnoreCase)
}

function Test-PathInsideRoot {
    param([AllowNull()][string]$Candidate, [AllowNull()][string]$RootPath)

    $candidateNorm = Normalize-PathString $Candidate
    $rootNorm = Normalize-PathString $RootPath
    if ([string]::IsNullOrWhiteSpace($candidateNorm) -or
        [string]::IsNullOrWhiteSpace($rootNorm)) {
        return $false
    }
    if (Paths-Equal $candidateNorm $rootNorm) {
        return $true
    }
    return $candidateNorm.StartsWith(
        $rootNorm.TrimEnd('\') + '\',
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Get-Sha256Safe {
    param([string]$PathValue)

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
    param([string]$StartPath, [string]$ExplicitRoot)

    if (-not [string]::IsNullOrWhiteSpace($ExplicitRoot)) {
        $candidate = Normalize-PathString $ExplicitRoot
        if (Test-Path -LiteralPath $candidate -PathType Container) {
            return $candidate
        }
        throw "Explicit FOXAI root does not exist: $candidate"
    }

    $current = Normalize-PathString $StartPath
    for ($i = 0; $i -lt 10; $i++) {
        $hasCore = Test-Path -LiteralPath (Join-Path $current 'core') -PathType Container
        $hasLauncher = Test-Path -LiteralPath (Join-Path $current 'Launch FOXAI Workshop.bat') -PathType Leaf
        if ($hasCore -and $hasLauncher) {
            return $current
        }
        $parent = Split-Path -Parent $current
        if ([string]::IsNullOrWhiteSpace($parent) -or (Paths-Equal $parent $current)) {
            break
        }
        $current = $parent
    }

    $fallback = 'Z:\FOXAI'
    if ((Test-Path -LiteralPath (Join-Path $fallback 'core') -PathType Container) -and
        (Test-Path -LiteralPath (Join-Path $fallback 'Launch FOXAI Workshop.bat') -PathType Leaf)) {
        return $fallback
    }

    throw "FOXAI root was not found. Extract this bundle inside FOXAI or pass -Root X:\FOXAI."
}

function Get-ProtectedBaselineSnapshot {
    param([string]$FoxaiRoot, [hashtable]$ExpectedHashes)

    $items = @()
    foreach ($relative in ($ExpectedHashes.Keys | Sort-Object)) {
        $full = Join-Path $FoxaiRoot ($relative.Replace('/', '\'))
        $exists = Test-Path -LiteralPath $full -PathType Leaf
        $actual = Get-Sha256Safe $full
        $expected = [string]$ExpectedHashes[$relative]
        $items += [pscustomobject][ordered]@{
            path = $relative
            full_path = $full
            exists = [bool]$exists
            expected_sha256 = $expected
            actual_sha256 = $actual
            matches_expected = [bool]($exists -and $actual -eq $expected)
        }
    }
    return @($items)
}

function Get-BoundedShortcutFiles {
    param(
        [string]$SearchRoot,
        [string]$BundlePath,
        [int]$MaxDepth = 8
    )

    $skipNames = @(
        '.git', '.venv', '__pycache__', 'backups', 'backup', 'models', 'model',
        'runtime', 'wheelhouse', 'node_modules', 'output', 'outputs', 'temp',
        'tmp', 'mission archive', 'logs', 'reports', '$recycle.bin',
        'system volume information'
    )

    $results = New-Object System.Collections.ArrayList

    function Walk-Directory {
        param([string]$DirectoryPath, [int]$Depth)

        if ($Depth -gt $MaxDepth) {
            return
        }

        try {
            $files = Get-ChildItem -LiteralPath $DirectoryPath -File -Force -ErrorAction SilentlyContinue
            foreach ($file in $files) {
                $ext = $file.Extension.ToLowerInvariant()
                if ($ext -eq '.lnk' -or $ext -eq '.url') {
                    [void]$results.Add($file.FullName)
                }
            }
        } catch {
            # Continue with other reachable paths.
        }

        if ($Depth -eq $MaxDepth) {
            return
        }

        try {
            $dirs = Get-ChildItem -LiteralPath $DirectoryPath -Directory -Force -ErrorAction SilentlyContinue
            foreach ($dir in $dirs) {
                $nameLower = $dir.Name.ToLowerInvariant()
                if ($skipNames -contains $nameLower) {
                    continue
                }
                if (Test-PathInsideRoot $dir.FullName $BundlePath) {
                    continue
                }
                Walk-Directory -DirectoryPath $dir.FullName -Depth ($Depth + 1)
            }
        } catch {
            # Continue with other reachable paths.
        }
    }

    Walk-Directory -DirectoryPath $SearchRoot -Depth 0
    return @($results)
}

function Get-ExternalShortcutFiles {
    param([array]$SearchRoots)

    $results = New-Object System.Collections.ArrayList
    foreach ($entry in $SearchRoots) {
        $pathValue = [string]$entry.path
        if ([string]::IsNullOrWhiteSpace($pathValue) -or
            -not (Test-Path -LiteralPath $pathValue -PathType Container)) {
            continue
        }

        try {
            $files = Get-ChildItem -LiteralPath $pathValue -File -Force -Recurse -ErrorAction SilentlyContinue |
                Where-Object { $_.Extension.ToLowerInvariant() -eq '.lnk' }
            foreach ($file in $files) {
                [void]$results.Add($file.FullName)
            }
        } catch {
            # An unreadable optional host location does not stop the USB probe.
        }
    }
    return @($results)
}

function Parse-IconLocation {
    param(
        [AllowNull()][string]$RawIcon,
        [string]$ShortcutDirectory
    )

    if ([string]::IsNullOrWhiteSpace($RawIcon)) {
        return [pscustomobject][ordered]@{
            raw = ''
            path = ''
            index = $null
        }
    }

    $raw = $RawIcon.Trim()
    $pathPart = $raw
    $index = $null
    $lastComma = $raw.LastIndexOf(',')

    if ($lastComma -ge 0) {
        $suffix = $raw.Substring($lastComma + 1).Trim()
        $parsed = 0
        if ([int]::TryParse($suffix, [ref]$parsed)) {
            $pathPart = $raw.Substring(0, $lastComma).Trim()
            $index = $parsed
        }
    }

    $normalizedPath = ""
    if (-not [string]::IsNullOrWhiteSpace($pathPart)) {
        $normalizedPath = Normalize-PathString $pathPart $ShortcutDirectory
    }

    return [pscustomobject][ordered]@{
        raw = $raw
        path = $normalizedPath
        index = $index
    }
}

function Resolve-LnkRecord {
    param(
        [string]$ShortcutPath,
        [string]$FoxaiRoot,
        [string]$UsbVolumeRoot,
        [string]$ExpectedDesktopTarget,
        [string]$ExpectedWebTarget,
        [object]$WshShell
    )

    $shortcutDirectory = Split-Path -Parent $ShortcutPath
    $beforeHash = Get-Sha256Safe $ShortcutPath

    $record = [ordered]@{
        shortcut_type = 'lnk'
        shortcut_path = Normalize-PathString $ShortcutPath
        shortcut_name = [System.IO.Path]::GetFileName($ShortcutPath)
        shortcut_sha256_before = $beforeHash
        resolved = $false
        target_path_raw = ''
        target_path = ''
        target_exists = $false
        arguments = ''
        working_directory_raw = ''
        working_directory = ''
        working_directory_exists = $false
        icon_location_raw = ''
        icon_path = ''
        icon_index = $null
        icon_exists = $false
        shortcut_is_on_usb_volume = [bool](Test-PathInsideRoot $ShortcutPath $UsbVolumeRoot)
        target_is_on_usb_volume = $false
        target_inside_foxai_root = $false
        working_directory_is_on_usb_volume = $false
        working_directory_inside_foxai_root = $false
        icon_is_on_usb_volume = $false
        icon_inside_foxai_root = $false
        matches_desktop_target = $false
        matches_web_target = $false
        description = ''
        hotkey = ''
        window_style = $null
        resolution_error = $null
    }

    try {
        $shortcut = $WshShell.CreateShortcut($ShortcutPath)
        $targetRaw = [string]$shortcut.TargetPath
        $workingRaw = [string]$shortcut.WorkingDirectory
        $targetNorm = Normalize-PathString $targetRaw $shortcutDirectory
        $workingNorm = Normalize-PathString $workingRaw $shortcutDirectory
        $iconInfo = Parse-IconLocation ([string]$shortcut.IconLocation) $shortcutDirectory

        $record.resolved = $true
        $record.target_path_raw = $targetRaw
        $record.target_path = $targetNorm
        $record.target_exists = [bool](
            -not [string]::IsNullOrWhiteSpace($targetNorm) -and
            (Test-Path -LiteralPath $targetNorm)
        )
        $record.arguments = [string]$shortcut.Arguments
        $record.working_directory_raw = $workingRaw
        $record.working_directory = $workingNorm
        $record.working_directory_exists = [bool](
            -not [string]::IsNullOrWhiteSpace($workingNorm) -and
            (Test-Path -LiteralPath $workingNorm -PathType Container)
        )
        $record.icon_location_raw = [string]$iconInfo.raw
        $record.icon_path = [string]$iconInfo.path
        $record.icon_index = $iconInfo.index
        $record.icon_exists = [bool](
            -not [string]::IsNullOrWhiteSpace($record.icon_path) -and
            (Test-Path -LiteralPath $record.icon_path -PathType Leaf)
        )
        $record.target_is_on_usb_volume = [bool](Test-PathInsideRoot $targetNorm $UsbVolumeRoot)
        $record.target_inside_foxai_root = [bool](Test-PathInsideRoot $targetNorm $FoxaiRoot)
        $record.working_directory_is_on_usb_volume = [bool](Test-PathInsideRoot $workingNorm $UsbVolumeRoot)
        $record.working_directory_inside_foxai_root = [bool](Test-PathInsideRoot $workingNorm $FoxaiRoot)
        $record.icon_is_on_usb_volume = [bool](Test-PathInsideRoot $record.icon_path $UsbVolumeRoot)
        $record.icon_inside_foxai_root = [bool](Test-PathInsideRoot $record.icon_path $FoxaiRoot)
        $record.matches_desktop_target = [bool](Paths-Equal $targetNorm $ExpectedDesktopTarget)
        $record.matches_web_target = [bool](Paths-Equal $targetNorm $ExpectedWebTarget)
        $record.description = [string]$shortcut.Description
        $record.hotkey = [string]$shortcut.Hotkey
        $record.window_style = $shortcut.WindowStyle
    } catch {
        $record.resolution_error = $_.Exception.Message
    }

    $record.shortcut_sha256_after = Get-Sha256Safe $ShortcutPath
    $record.shortcut_hash_unchanged = [bool](
        $record.shortcut_sha256_before -eq $record.shortcut_sha256_after
    )

    return [pscustomobject]$record
}

function Resolve-UrlRecord {
    param(
        [string]$ShortcutPath,
        [string]$FoxaiRoot,
        [string]$UsbVolumeRoot
    )

    $beforeHash = Get-Sha256Safe $ShortcutPath
    $urlValue = ''
    $iconFile = ''
    $iconIndex = $null
    $errorMessage = $null

    try {
        foreach ($line in (Get-Content -LiteralPath $ShortcutPath -ErrorAction Stop)) {
            if ($line -match '^\s*URL\s*=(.*)$') {
                $urlValue = $Matches[1].Trim()
            } elseif ($line -match '^\s*IconFile\s*=(.*)$') {
                $iconFile = $Matches[1].Trim()
            } elseif ($line -match '^\s*IconIndex\s*=(-?\d+)\s*$') {
                $iconIndex = [int]$Matches[1]
            }
        }
    } catch {
        $errorMessage = $_.Exception.Message
    }

    $shortcutDirectory = Split-Path -Parent $ShortcutPath
    $iconNorm = Normalize-PathString $iconFile $shortcutDirectory

    $record = [ordered]@{
        shortcut_type = 'url'
        shortcut_path = Normalize-PathString $ShortcutPath
        shortcut_name = [System.IO.Path]::GetFileName($ShortcutPath)
        shortcut_sha256_before = $beforeHash
        resolved = [bool]([string]::IsNullOrWhiteSpace($errorMessage))
        target_path_raw = $urlValue
        target_path = $urlValue
        target_exists = $false
        arguments = ''
        working_directory_raw = ''
        working_directory = ''
        working_directory_exists = $false
        icon_location_raw = $iconFile
        icon_path = $iconNorm
        icon_index = $iconIndex
        icon_exists = [bool](
            -not [string]::IsNullOrWhiteSpace($iconNorm) -and
            (Test-Path -LiteralPath $iconNorm -PathType Leaf)
        )
        shortcut_is_on_usb_volume = [bool](Test-PathInsideRoot $ShortcutPath $UsbVolumeRoot)
        target_is_on_usb_volume = $false
        target_inside_foxai_root = $false
        working_directory_is_on_usb_volume = $false
        working_directory_inside_foxai_root = $false
        icon_is_on_usb_volume = [bool](Test-PathInsideRoot $iconNorm $UsbVolumeRoot)
        icon_inside_foxai_root = [bool](Test-PathInsideRoot $iconNorm $FoxaiRoot)
        matches_desktop_target = $false
        matches_web_target = $false
        description = ''
        hotkey = ''
        window_style = $null
        resolution_error = $errorMessage
    }

    $record.shortcut_sha256_after = Get-Sha256Safe $ShortcutPath
    $record.shortcut_hash_unchanged = [bool](
        $record.shortcut_sha256_before -eq $record.shortcut_sha256_after
    )

    return [pscustomobject]$record
}

function Get-RelevantTextEvidence {
    param([string]$FullPath, [string]$RelativePath)

    $exists = Test-Path -LiteralPath $FullPath -PathType Leaf
    $before = Get-Sha256Safe $FullPath
    $matchedLines = @()
    $readError = $null

    if ($exists) {
        try {
            $lineNumber = 0
            foreach ($line in (Get-Content -LiteralPath $FullPath -ErrorAction Stop)) {
                $lineNumber++
                if ($line -match '(?i)CreateShortcut|\.lnk|TargetPath|WorkingDirectory|IconLocation|Launch FOXAI|START_FOXAI|foxai_fixed|Desktop|foxai\.py|python') {
                    $matchedLines += [pscustomobject][ordered]@{
                        line = $lineNumber
                        text = $line
                    }
                }
            }
        } catch {
            $readError = $_.Exception.Message
        }
    }

    $after = Get-Sha256Safe $FullPath
    return [pscustomobject][ordered]@{
        path = $RelativePath
        full_path = $FullPath
        exists = [bool]$exists
        sha256_before = $before
        sha256_after = $after
        hash_unchanged = [bool]($before -eq $after)
        matched_lines = @($matchedLines)
        read_error = $readError
    }
}

function Get-FileEvidence {
    param([string]$FullPath, [string]$RelativePath)

    $exists = Test-Path -LiteralPath $FullPath -PathType Leaf
    $before = Get-Sha256Safe $FullPath
    $after = Get-Sha256Safe $FullPath
    return [pscustomobject][ordered]@{
        path = $RelativePath
        full_path = $FullPath
        exists = [bool]$exists
        sha256_before = $before
        sha256_after = $after
        hash_unchanged = [bool]($before -eq $after)
    }
}

function Test-RelevantShortcut {
    param([object]$Record)

    if ($Record.matches_desktop_target -or $Record.matches_web_target) {
        return $true
    }

    $name = ([string]$Record.shortcut_name).ToLowerInvariant()
    $target = ([string]$Record.target_path).ToLowerInvariant()
    $description = ([string]$Record.description).ToLowerInvariant()

    return (
        $name.Contains('foxai') -or
        $name.Contains('workshop') -or
        $name.Contains('kayock') -or
        $target.Contains('\foxai\') -or
        $description.Contains('foxai') -or
        $description.Contains('kayock')
    )
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

$created = Get-IsoUtc
$stamp = Get-UtcStamp
$bundlePath = Normalize-PathString $BundleDir
$foxaiRoot = Find-FoxaiRoot $bundlePath $Root
$usbVolumeRoot = [System.IO.Path]::GetPathRoot($foxaiRoot)
$expectedDesktopTarget = Join-Path $foxaiRoot 'Launch FOXAI Workshop.bat'
$expectedWebTarget = Join-Path $foxaiRoot 'START_FOXAI_WEB_PORTABLE.bat'

$outputRoot = Join-Path $bundlePath 'probe_output'
$outputDir = Join-Path $outputRoot $stamp
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

$failure = $null
$exitCode = 0
$beforeBaselines = @()
$afterBaselines = @()
$allSavedInventory = @()
$sourceEvidence = @()
$iconEvidence = @()
$hostScannedCount = 0
$usbFoundCount = 0
$resolvedCount = 0
$resolutionErrorCount = 0

try {
    $beforeBaselines = Get-ProtectedBaselineSnapshot $foxaiRoot $expectedHashes

    $specialRoots = @()
    $knownFolders = @(
        @{ label = 'Current user Desktop'; value = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop) },
        @{ label = 'Public Desktop'; value = [Environment]::GetFolderPath([Environment+SpecialFolder]::CommonDesktopDirectory) },
        @{ label = 'Current user Start Menu Programs'; value = [Environment]::GetFolderPath([Environment+SpecialFolder]::Programs) },
        @{ label = 'Common Start Menu Programs'; value = [Environment]::GetFolderPath([Environment+SpecialFolder]::CommonPrograms) }
    )

    $seenRoots = @{}
    foreach ($entry in $knownFolders) {
        $normalized = Normalize-PathString ([string]$entry.value)
        if (-not [string]::IsNullOrWhiteSpace($normalized)) {
            $key = $normalized.ToLowerInvariant()
            if (-not $seenRoots.ContainsKey($key)) {
                $seenRoots[$key] = $true
                $specialRoots += [pscustomobject][ordered]@{
                    label = [string]$entry.label
                    path = $normalized
                }
            }
        }
    }

    $usbFiles = @(Get-BoundedShortcutFiles $usbVolumeRoot $bundlePath 8)
    $usbFoundCount = $usbFiles.Count
    $hostFiles = @(Get-ExternalShortcutFiles $specialRoots)
    $hostScannedCount = $hostFiles.Count

    $dedup = @{}
    $combined = @()
    foreach ($pathValue in @($usbFiles + $hostFiles)) {
        $normalized = Normalize-PathString $pathValue
        $key = $normalized.ToLowerInvariant()
        if (-not $dedup.ContainsKey($key)) {
            $dedup[$key] = $true
            $combined += $normalized
        }
    }

    $wsh = New-Object -ComObject WScript.Shell

    foreach ($shortcutPath in ($combined | Sort-Object)) {
        $ext = [System.IO.Path]::GetExtension($shortcutPath).ToLowerInvariant()
        if ($ext -eq '.lnk') {
            $record = Resolve-LnkRecord `
                $shortcutPath `
                $foxaiRoot `
                $usbVolumeRoot `
                $expectedDesktopTarget `
                $expectedWebTarget `
                $wsh
        } else {
            $record = Resolve-UrlRecord $shortcutPath $foxaiRoot $usbVolumeRoot
        }

        if ($record.resolved) {
            $resolvedCount++
        } else {
            $resolutionErrorCount++
        }

        $physicallyOnUsb = [bool]$record.shortcut_is_on_usb_volume
        if ($physicallyOnUsb -or (Test-RelevantShortcut $record)) {
            $allSavedInventory += $record
        }
    }

    $textEvidencePaths = @(
        'Create Desktop Shortcut.ps1',
        'Memory\Create Desktop Shortcut.ps1',
        'Launch FOXAI Workshop.bat',
        'START_FOXAI_WEB_PORTABLE.bat',
        'foxai.py'
    )

    foreach ($relative in $textEvidencePaths) {
        $full = Join-Path $foxaiRoot $relative
        $sourceEvidence += Get-RelevantTextEvidence $full $relative
    }

    $iconCandidates = @(
        'Icons\foxai_fixed.ico',
        'assets\foxai_fixed.ico',
        'assets\foxai.ico',
        'Memory\assets\foxai.ico'
    )
    foreach ($relative in $iconCandidates) {
        $full = Join-Path $foxaiRoot $relative
        $iconEvidence += Get-FileEvidence $full $relative
    }

    $afterBaselines = Get-ProtectedBaselineSnapshot $foxaiRoot $expectedHashes
} catch {
    $failure = [pscustomobject][ordered]@{
        type = $_.Exception.GetType().FullName
        message = $_.Exception.Message
    }
    $exitCode = 1

    try {
        $afterBaselines = Get-ProtectedBaselineSnapshot $foxaiRoot $expectedHashes
    } catch {
        $afterBaselines = @()
    }
}

$baselineBeforePassed = [bool](
    $beforeBaselines.Count -eq $expectedHashes.Count -and
    (@($beforeBaselines | Where-Object { -not $_.matches_expected }).Count -eq 0)
)
$baselineAfterPassed = [bool](
    $afterBaselines.Count -eq $expectedHashes.Count -and
    (@($afterBaselines | Where-Object { -not $_.matches_expected }).Count -eq 0)
)
$savedShortcutHashesUnchanged = [bool](
    @($allSavedInventory | Where-Object { -not $_.shortcut_hash_unchanged }).Count -eq 0
)
$sourceHashesUnchanged = [bool](
    @($sourceEvidence | Where-Object { -not $_.hash_unchanged }).Count -eq 0
)
$iconHashesUnchanged = [bool](
    @($iconEvidence | Where-Object { -not $_.hash_unchanged }).Count -eq 0
)

$desktopMatches = @($allSavedInventory | Where-Object { $_.matches_desktop_target })
$webMatches = @($allSavedInventory | Where-Object { $_.matches_web_target })
$namedDesktopCandidates = @($allSavedInventory | Where-Object {
    $n = ([string]$_.shortcut_name).ToLowerInvariant()
    $n.Contains('foxai') -or $n.Contains('workshop') -or $n.Contains('kayock')
})
$usbShortcutRecords = @($allSavedInventory | Where-Object { $_.shortcut_is_on_usb_volume })

$desktopState = 'not_found'
if ($desktopMatches.Count -eq 1) {
    $desktopState = 'exact_match_found'
} elseif ($desktopMatches.Count -gt 1) {
    $desktopState = 'multiple_exact_matches'
} elseif ($namedDesktopCandidates.Count -gt 0) {
    $desktopState = 'named_candidates_only'
}

$webState = 'not_found'
if ($webMatches.Count -eq 1) {
    $webState = 'exact_match_found'
} elseif ($webMatches.Count -gt 1) {
    $webState = 'multiple_exact_matches'
}

$creatorEvidenceFound = [bool](
    @($sourceEvidence | Where-Object {
        $_.path -like '*Create Desktop Shortcut.ps1' -and
        $_.exists -and
        $_.matched_lines.Count -gt 0
    }).Count -gt 0
)

$verified = [bool](
    $null -eq $failure -and
    $baselineBeforePassed -and
    $baselineAfterPassed -and
    $savedShortcutHashesUnchanged -and
    $sourceHashesUnchanged -and
    $iconHashesUnchanged
)

if (-not $verified -and $exitCode -eq 0) {
    $exitCode = 2
}

$contractRecommendation = [ordered]@{
    desktop = [ordered]@{
        state = $desktopState
        expected_target = $expectedDesktopTarget
        exact_match_count = $desktopMatches.Count
        named_candidate_count = $namedDesktopCandidates.Count
        evidence = @($desktopMatches + $namedDesktopCandidates | Sort-Object shortcut_path -Unique)
        recommendation = if ($desktopMatches.Count -eq 1) {
            'Use the exact resolved shortcut as the protected desktop shortcut contract.'
        } elseif ($namedDesktopCandidates.Count -gt 0) {
            'Review the named candidates. Do not rewrite or replace them until the intended protected shortcut is confirmed.'
        } else {
            'No protected desktop shortcut was found in the bounded USB volume, Desktop, or Start Menu surfaces. Validate the launcher directly or confirm the shortcut was intentionally absent.'
        }
    }
    web = [ordered]@{
        state = $webState
        expected_target = $expectedWebTarget
        exact_match_count = $webMatches.Count
        evidence = @($webMatches)
        recommendation = if ($webMatches.Count -gt 0) {
            'A web shortcut exists and can be validated as an optional launch surface.'
        } else {
            'Do not require a web .lnk shortcut unless source evidence or an operator-approved design explicitly establishes one. Validate START_FOXAI_WEB_PORTABLE.bat directly.'
        }
    }
    shortcut_creator_evidence_found = $creatorEvidenceFound
    icon_contract_note = 'The earlier Phase 3B report assumed Icons\foxai_fixed.ico. This probe separately checks Icons and assets candidates rather than guessing.'
    phase3c_blocked = $true
}

$searchScope = @(
    [pscustomobject][ordered]@{
        label = 'USB volume bounded search'
        path = $usbVolumeRoot
        recursive = $true
        maximum_depth = 8
        skipped_heavy_directories = @(
            '.git', '.venv', '__pycache__', 'Backups', 'Models', 'Runtime',
            'Wheelhouse', 'node_modules', 'output', 'temp', 'Mission Archive',
            'Logs', 'Reports', '$RECYCLE.BIN', 'System Volume Information'
        )
    }
)
$searchScope += $specialRoots

$inventoryDocument = [ordered]@{
    created = Get-IsoUtc
    foxai_root = $foxaiRoot
    usb_volume_root = $usbVolumeRoot
    expected_targets = [ordered]@{
        desktop = $expectedDesktopTarget
        web = $expectedWebTarget
    }
    search_scope = $searchScope
    scanned_counts = [ordered]@{
        usb_shortcut_files_found = $usbFoundCount
        host_shortcut_files_scanned = $hostScannedCount
        relevant_records_saved = $allSavedInventory.Count
        resolved = $resolvedCount
        resolution_errors = $resolutionErrorCount
    }
    inventory = @($allSavedInventory | Sort-Object shortcut_path)
    source_evidence = @($sourceEvidence)
    icon_evidence = @($iconEvidence)
    contract_recommendation = $contractRecommendation
}

$receipt = [ordered]@{
    action = 'foxai_pdr3b_r2_usb_root_shortcut_contract_readonly_probe'
    created = $created
    state = if ($verified) { 'read_only_probe_complete' } else { 'stopped_fail_closed' }
    verified = $verified
    read_only = $true
    apply_capability_present = $false
    live_files_modified = $false
    shortcut_changes = $false
    launcher_changes = $false
    runtime_changes = $false
    package_install = $false
    network_access = $false
    desktop_gui_launched = $false
    foxai_root = $foxaiRoot
    usb_volume_root = $usbVolumeRoot
    bundle_dir = $bundlePath
    output_dir = $outputDir
    search_scope = $searchScope
    protected_baselines_before = $beforeBaselines
    protected_baselines_after = $afterBaselines
    baseline_before_passed = $baselineBeforePassed
    baseline_after_passed = $baselineAfterPassed
    saved_shortcut_hashes_unchanged = $savedShortcutHashesUnchanged
    source_hashes_unchanged = $sourceHashesUnchanged
    icon_hashes_unchanged = $iconHashesUnchanged
    scanned_counts = $inventoryDocument.scanned_counts
    contract_recommendation = $contractRecommendation
    next_safe_action = 'Review this evidence, correct the Phase 3B shortcut assumptions, and rerun the read-only Phase 3B design. Do not proceed to Phase 3C.'
    failure = $failure
}

$inventoryPath = Join-Path $outputDir 'USB_ROOT_SHORTCUT_CONTRACT_INVENTORY.json'
$receiptPath = Join-Path $outputDir 'USB_ROOT_SHORTCUT_CONTRACT_RECEIPT.json'
$reportPath = Join-Path $outputDir 'USB_ROOT_SHORTCUT_CONTRACT_REPORT.md'

$inventoryDocument | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $inventoryPath -Encoding UTF8
$receipt | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $receiptPath -Encoding UTF8

$report = New-Object System.Collections.Generic.List[string]
$report.Add('# FOXAI Portable Desktop Runtime Phase 3B-R2')
$report.Add('## USB-Root Shortcut Contract Evidence Probe')
$report.Add('')
$report.Add("- State: **$($receipt.state)**")
$report.Add("- Verified: **$verified**")
$report.Add("- Read only: **True**")
$report.Add("- Live files modified: **False**")
$report.Add("- Shortcuts changed: **False**")
$report.Add("- Launchers changed: **False**")
$report.Add("- Packages installed: **False**")
$report.Add("- Network access: **False**")
$report.Add("- FOXAI launched: **False**")
$report.Add('')
$report.Add('## Why this probe was needed')
$report.Add('')
$report.Add('Phase 3B-R1 searched inside the FOXAI folder and host shortcut surfaces, but it did not search the USB volume root. It also treated a blank `,0` icon location as a relative USB path. R2 corrects both diagnostic assumptions without changing anything.')
$report.Add('')
$report.Add('## Search summary')
$report.Add('')
$report.Add("- FOXAI root: `$foxaiRoot`")
$report.Add("- USB volume root: `$usbVolumeRoot`")
$report.Add("- USB shortcut files found: **$usbFoundCount**")
$report.Add("- Host shortcut files scanned: **$hostScannedCount**")
$report.Add("- Relevant records saved: **$($allSavedInventory.Count)**")
$report.Add("- Resolution errors: **$resolutionErrorCount**")
$report.Add('')
$report.Add('## Desktop shortcut contract')
$report.Add('')
$report.Add("- Expected target: `$expectedDesktopTarget`")
$report.Add("- State: **$desktopState**")
$report.Add("- Exact matches: **$($desktopMatches.Count)**")
$report.Add("- Named candidates: **$($namedDesktopCandidates.Count)**")
foreach ($item in ($contractRecommendation.desktop.evidence | Sort-Object shortcut_path -Unique)) {
    $report.Add("- Candidate: `$($item.shortcut_path)`")
    $report.Add("  - Target: `$($item.target_path)`")
    $report.Add("  - Working directory: `$($item.working_directory)`")
    $report.Add("  - Icon: `$($item.icon_path)`")
    $report.Add("  - Shortcut on USB: **$($item.shortcut_is_on_usb_volume)**")
    $report.Add("  - Target inside FOXAI: **$($item.target_inside_foxai_root)**")
    $report.Add("  - Hash unchanged: **$($item.shortcut_hash_unchanged)**")
}
$report.Add('')
$report.Add($contractRecommendation.desktop.recommendation)
$report.Add('')
$report.Add('## Web shortcut contract')
$report.Add('')
$report.Add("- Expected target: `$expectedWebTarget`")
$report.Add("- State: **$webState**")
$report.Add("- Exact matches: **$($webMatches.Count)**")
$report.Add('')
$report.Add($contractRecommendation.web.recommendation)
$report.Add('')
$report.Add('## Shortcut-creator and icon evidence')
$report.Add('')
$report.Add("- Shortcut creator evidence found: **$creatorEvidenceFound**")
foreach ($item in $sourceEvidence) {
    $report.Add("- `$($item.path)` — exists: **$($item.exists)**; hash unchanged: **$($item.hash_unchanged)**; relevant lines: **$($item.matched_lines.Count)**")
}
foreach ($item in $iconEvidence) {
    $report.Add("- `$($item.path)` — exists: **$($item.exists)**; hash unchanged: **$($item.hash_unchanged)**")
}
$report.Add('')
$report.Add('## Safety verification')
$report.Add('')
$report.Add("- Protected baselines passed before: **$baselineBeforePassed**")
$report.Add("- Protected baselines passed after: **$baselineAfterPassed**")
$report.Add("- Saved shortcut hashes unchanged: **$savedShortcutHashesUnchanged**")
$report.Add("- Source hashes unchanged: **$sourceHashesUnchanged**")
$report.Add("- Icon hashes unchanged: **$iconHashesUnchanged**")
$report.Add('')
$report.Add('## Next safe action')
$report.Add('')
$report.Add('**Review this evidence, correct the Phase 3B shortcut assumptions, and rerun the read-only Phase 3B design. Do not proceed to Phase 3C.**')
if ($null -ne $failure) {
    $report.Add('')
    $report.Add('## Failure')
    $report.Add('')
    $report.Add("- `$($failure.type): $($failure.message)`")
}

$report | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Host ""
Write-Host "Phase 3B-R2 read-only probe complete."
Write-Host "Output: $outputDir"
Write-Host "Verified: $verified"
Write-Host "Desktop state: $desktopState"
Write-Host "Web state: $webState"
Write-Host "Phase 3C remains blocked."

exit $exitCode
