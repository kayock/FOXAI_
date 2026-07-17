[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$BundleDir = $PSScriptRoot,

    [Parameter(Mandatory = $false)]
    [string]$Root = ""
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

function Get-UtcStamp {
    return [DateTime]::UtcNow.ToString("yyyyMMdd'T'HHmmss'Z'")
}

function Get-IsoUtc {
    return [DateTime]::UtcNow.ToString("o")
}

function Normalize-PathString {
    param([AllowNull()][string]$PathValue)

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return ""
    }

    $value = [Environment]::ExpandEnvironmentVariables($PathValue.Trim())
    $value = $value.Trim('"')
    try {
        $value = [System.IO.Path]::GetFullPath($value)
    } catch {
        # Preserve the readable raw value when Windows cannot canonicalize it.
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
    param([AllowNull()][string]$Candidate, [string]$RootPath)

    $candidateNorm = Normalize-PathString $Candidate
    $rootNorm = Normalize-PathString $RootPath
    if ([string]::IsNullOrWhiteSpace($candidateNorm)) {
        return $false
    }
    if (Paths-Equal $candidateNorm $rootNorm) {
        return $true
    }
    return $candidateNorm.StartsWith($rootNorm + '\', [System.StringComparison]::OrdinalIgnoreCase)
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
    for ($i = 0; $i -lt 8; $i++) {
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

    throw "FOXAI root was not found. Extract this bundle inside the FOXAI folder or pass -Root X:\FOXAI."
}

function Get-ProtectedBaselineSnapshot {
    param([string]$FoxaiRoot, [hashtable]$ExpectedHashes)

    $items = @()
    foreach ($relative in ($ExpectedHashes.Keys | Sort-Object)) {
        $full = Join-Path $FoxaiRoot ($relative.Replace('/', '\'))
        $exists = Test-Path -LiteralPath $full -PathType Leaf
        $actual = Get-Sha256Safe $full
        $expected = [string]$ExpectedHashes[$relative]
        $items += [ordered]@{
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

function Get-BoundedUsbShortcuts {
    param(
        [string]$FoxaiRoot,
        [string]$BundlePath,
        [int]$MaxDepth = 6
    )

    $skipNames = @(
        '.git', '.venv', '__pycache__', 'backups', 'models', 'model', 'runtime',
        'wheelhouse', 'node_modules', 'output', 'outputs', 'temp', 'tmp',
        'mission archive', 'logs', 'reports'
    )
    $results = New-Object System.Collections.ArrayList

    function Walk-ShortcutDirectory {
        param([string]$DirectoryPath, [int]$Depth)

        if ($Depth -gt $MaxDepth) {
            return
        }

        try {
            $files = Get-ChildItem -LiteralPath $DirectoryPath -File -Force -Filter '*.lnk' -ErrorAction SilentlyContinue
            foreach ($file in $files) {
                [void]$results.Add($file.FullName)
            }
        } catch {
            # Inventory errors are recorded by omission; the search scope remains bounded.
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
                Walk-ShortcutDirectory -DirectoryPath $dir.FullName -Depth ($Depth + 1)
            }
        } catch {
            # Keep the probe read-only and continue with other reachable directories.
        }
    }

    Walk-ShortcutDirectory -DirectoryPath $FoxaiRoot -Depth 0
    return @($results)
}

function Get-ExternalShortcutFiles {
    param([array]$SearchRoots)

    $results = New-Object System.Collections.ArrayList
    foreach ($entry in $SearchRoots) {
        $pathValue = [string]$entry.path
        if ([string]::IsNullOrWhiteSpace($pathValue) -or -not (Test-Path -LiteralPath $pathValue -PathType Container)) {
            continue
        }
        try {
            $files = Get-ChildItem -LiteralPath $pathValue -File -Force -Filter '*.lnk' -Recurse -ErrorAction SilentlyContinue
            foreach ($file in $files) {
                [void]$results.Add($file.FullName)
            }
        } catch {
            # Failure to read one optional host surface does not stop the USB probe.
        }
    }
    return @($results)
}

function Parse-IconLocation {
    param([AllowNull()][string]$RawIcon)

    if ([string]::IsNullOrWhiteSpace($RawIcon)) {
        return [ordered]@{ raw = ''; path = ''; index = $null }
    }

    $raw = $RawIcon.Trim()
    $pathPart = $raw
    $index = $null
    $lastComma = $raw.LastIndexOf(',')
    if ($lastComma -gt 0) {
        $suffix = $raw.Substring($lastComma + 1).Trim()
        $parsed = 0
        if ([int]::TryParse($suffix, [ref]$parsed)) {
            $pathPart = $raw.Substring(0, $lastComma).Trim()
            $index = $parsed
        }
    }

    return [ordered]@{
        raw = $raw
        path = Normalize-PathString $pathPart
        index = $index
    }
}

function Resolve-ShortcutRecord {
    param(
        [string]$ShortcutPath,
        [string]$FoxaiRoot,
        [string]$ExpectedDesktopTarget,
        [string]$ExpectedWebTarget,
        [object]$WshShell
    )

    $fileHash = Get-Sha256Safe $ShortcutPath
    $record = [ordered]@{
        shortcut_path = Normalize-PathString $ShortcutPath
        shortcut_name = [System.IO.Path]::GetFileName($ShortcutPath)
        shortcut_sha256_before = $fileHash
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
        target_is_usb_owned = $false
        working_directory_is_usb_owned = $false
        icon_is_usb_owned = $false
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
        $iconInfo = Parse-IconLocation ([string]$shortcut.IconLocation)
        $targetNorm = Normalize-PathString $targetRaw
        $workingNorm = Normalize-PathString $workingRaw

        $record.resolved = $true
        $record.target_path_raw = $targetRaw
        $record.target_path = $targetNorm
        $record.target_exists = [bool](-not [string]::IsNullOrWhiteSpace($targetNorm) -and (Test-Path -LiteralPath $targetNorm -PathType Leaf))
        $record.arguments = [string]$shortcut.Arguments
        $record.working_directory_raw = $workingRaw
        $record.working_directory = $workingNorm
        $record.working_directory_exists = [bool](-not [string]::IsNullOrWhiteSpace($workingNorm) -and (Test-Path -LiteralPath $workingNorm -PathType Container))
        $record.icon_location_raw = [string]$iconInfo.raw
        $record.icon_path = [string]$iconInfo.path
        $record.icon_index = $iconInfo.index
        $record.icon_exists = [bool](-not [string]::IsNullOrWhiteSpace($record.icon_path) -and (Test-Path -LiteralPath $record.icon_path -PathType Leaf))
        $record.target_is_usb_owned = [bool](Test-PathInsideRoot $targetNorm $FoxaiRoot)
        $record.working_directory_is_usb_owned = [bool](Test-PathInsideRoot $workingNorm $FoxaiRoot)
        $record.icon_is_usb_owned = [bool](Test-PathInsideRoot $record.icon_path $FoxaiRoot)
        $record.matches_desktop_target = [bool](Paths-Equal $targetNorm $ExpectedDesktopTarget)
        $record.matches_web_target = [bool](Paths-Equal $targetNorm $ExpectedWebTarget)
        $record.description = [string]$shortcut.Description
        $record.hotkey = [string]$shortcut.Hotkey
        $record.window_style = $shortcut.WindowStyle
    } catch {
        $record.resolution_error = $_.Exception.Message
    }

    return $record
}

function New-ContractSummary {
    param(
        [string]$Name,
        [string]$ExpectedTarget,
        [array]$Inventory,
        [string]$MatchProperty
    )

    $matches = @($Inventory | Where-Object { $_.$MatchProperty -eq $true })
    $nameHints = @($Inventory | Where-Object {
        $n = ([string]$_.shortcut_name).ToLowerInvariant()
        if ($Name -eq 'desktop') {
            return ($n.Contains('foxai') -or $n.Contains('workshop') -or $n.Contains('kayock'))
        }
        return ($n.Contains('foxai') -or $n.Contains('web') -or $n.Contains('kayock'))
    })

    $state = 'not_found'
    if ($matches.Count -eq 1) { $state = 'unique_target_match' }
    elseif ($matches.Count -gt 1) { $state = 'duplicate_target_matches' }

    return [ordered]@{
        name = $Name
        expected_target = $ExpectedTarget
        state = $state
        match_count = $matches.Count
        matches = @($matches)
        filename_hint_count = $nameHints.Count
        filename_hints = @($nameHints)
    }
}

function Write-Utf8NoBom {
    param([string]$PathValue, [string]$Text)
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($PathValue, $Text, $utf8)
}

$bundlePath = Normalize-PathString $BundleDir
$stamp = Get-UtcStamp
$outputRoot = Join-Path $bundlePath 'probe_output'
$outputDir = Join-Path $outputRoot $stamp
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

$receiptPath = Join-Path $outputDir 'SHORTCUT_INVENTORY_RECEIPT.json'
$inventoryJsonPath = Join-Path $outputDir 'SHORTCUT_INVENTORY.json'
$reportPath = Join-Path $outputDir 'SHORTCUT_INVENTORY_REPORT.md'

$receipt = [ordered]@{
    action = 'foxai_pdr3b_r1_shortcut_inventory_readonly_probe'
    created = Get-IsoUtc
    state = 'started'
    verified = $false
    read_only = $true
    apply_capability_present = $false
    live_files_modified = $false
    shortcut_changes = $false
    launcher_changes = $false
    runtime_changes = $false
    package_install = $false
    network_access = $false
    desktop_gui_launched = $false
    root = $null
    bundle_dir = $bundlePath
    output_dir = $outputDir
    search_scope = @()
    protected_baselines_before = @()
    protected_baselines_after = @()
    shortcut_inventory = @()
    shortcut_hashes_unchanged = $false
    contract_analysis = [ordered]@{}
    next_safe_action = ''
    failure = $null
}

$expectedHashes = @{
    'core/foxai_web.py' = 'ca45bfc72ce73a47df3ca11b1d1f0564b070cf70ae766a956fb1daaff3dfc2a7'
    'core/server.py' = '238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81'
    'core/security_containment.py' = '9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24'
    'core/engineer_agent.py' = 'f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19'
    'core/model_sources.py' = 'e00a861265eff8826c4d7eeb89b3765e719b88f349811a2e608525d8a3f91ea2'
    'Config/model_sources.json' = 'c17eb3b8b6c93734f7e117522213c95af6c105fe26400d0560768fe586e21c91'
    'tests/test_model_sources.py' = 'ec94f8b8d90d36f05385db74400dd99b436cd4e488b1b517bcb77442a16fc6f2'
    'tests/test_boundary_watch.py' = 'b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382'
    'ui/main_window.py' = '2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3'
    'START_FOXAI_WEB_PORTABLE.bat' = '834e129be2d41405be40e1ea5aeca6d7a96b4faaf3b72c906487e902a9dca3b1'
    'env/python/python314._pth' = '48d77ccee161647ef7053cb563d3b37b4053938d5ad92ae64ccedc2165bcd42d'
    'Config/fleet_registry.json' = '18745be73f67e073c002bb645a3c0eaad0a3090ebee1b3bb547ddcc2f147bdb6'
    'core/service_registry.py' = 'cc798df061a27a51c4ea1f64b3757d2a92724a9a5768e4c190846966efe0251b'
    'Launch FOXAI Workshop.bat' = '7f974eeeaa66c6fd331b6b3e8cb5f312d25a410761817ad35408ccb47acd4480'
}

$exitCode = 1
try {
    $foxaiRoot = Find-FoxaiRoot -StartPath $bundlePath -ExplicitRoot $Root
    $receipt.root = $foxaiRoot

    $expectedDesktopTarget = Join-Path $foxaiRoot 'Launch FOXAI Workshop.bat'
    $expectedWebTarget = Join-Path $foxaiRoot 'START_FOXAI_WEB_PORTABLE.bat'

    $receipt.protected_baselines_before = @(Get-ProtectedBaselineSnapshot -FoxaiRoot $foxaiRoot -ExpectedHashes $expectedHashes)

    $externalRoots = @()
    $desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
    $commonDesktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::CommonDesktopDirectory)
    $startMenu = [Environment]::GetFolderPath([Environment+SpecialFolder]::StartMenu)
    $commonStartMenu = [Environment]::GetFolderPath([Environment+SpecialFolder]::CommonStartMenu)

    if (-not [string]::IsNullOrWhiteSpace($desktop)) {
        $externalRoots += [ordered]@{ label = 'Current user Desktop'; path = Normalize-PathString $desktop }
    }
    if (-not [string]::IsNullOrWhiteSpace($commonDesktop)) {
        $externalRoots += [ordered]@{ label = 'Public Desktop'; path = Normalize-PathString $commonDesktop }
    }
    if (-not [string]::IsNullOrWhiteSpace($startMenu)) {
        $externalRoots += [ordered]@{ label = 'Current user Start Menu Programs'; path = Normalize-PathString (Join-Path $startMenu 'Programs') }
    }
    if (-not [string]::IsNullOrWhiteSpace($commonStartMenu)) {
        $externalRoots += [ordered]@{ label = 'Common Start Menu Programs'; path = Normalize-PathString (Join-Path $commonStartMenu 'Programs') }
    }

    $receipt.search_scope = @(
        [ordered]@{
            label = 'FOXAI USB bounded search'
            path = $foxaiRoot
            recursive = $true
            maximum_depth = 6
            skipped_heavy_directories = @('.git', '.venv', '__pycache__', 'Backups', 'Models', 'Runtime', 'Wheelhouse', 'node_modules', 'output', 'temp', 'Mission Archive', 'Logs', 'Reports')
        }
    ) + @($externalRoots | ForEach-Object {
        [ordered]@{ label = $_.label; path = $_.path; recursive = $true; maximum_depth = $null }
    })

    $candidatePaths = New-Object System.Collections.ArrayList
    foreach ($pathValue in (Get-BoundedUsbShortcuts -FoxaiRoot $foxaiRoot -BundlePath $bundlePath -MaxDepth 6)) {
        [void]$candidatePaths.Add($pathValue)
    }
    foreach ($pathValue in (Get-ExternalShortcutFiles -SearchRoots $externalRoots)) {
        [void]$candidatePaths.Add($pathValue)
    }

    $dedup = @{}
    foreach ($pathValue in $candidatePaths) {
        $normalized = Normalize-PathString ([string]$pathValue)
        if (-not [string]::IsNullOrWhiteSpace($normalized)) {
            $dedup[$normalized.ToLowerInvariant()] = $normalized
        }
    }
    $uniquePaths = @($dedup.Values | Sort-Object)

    $wsh = New-Object -ComObject WScript.Shell
    try {
        $inventory = @()
        foreach ($shortcutPath in $uniquePaths) {
            $inventory += Resolve-ShortcutRecord `
                -ShortcutPath $shortcutPath `
                -FoxaiRoot $foxaiRoot `
                -ExpectedDesktopTarget $expectedDesktopTarget `
                -ExpectedWebTarget $expectedWebTarget `
                -WshShell $wsh
        }
    } finally {
        if ($null -ne $wsh) {
            try { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($wsh) } catch {}
        }
    }

    $receipt.shortcut_inventory = @($inventory)
    $receipt.contract_analysis.desktop = New-ContractSummary `
        -Name 'desktop' `
        -ExpectedTarget $expectedDesktopTarget `
        -Inventory $inventory `
        -MatchProperty 'matches_desktop_target'
    $receipt.contract_analysis.web = New-ContractSummary `
        -Name 'web' `
        -ExpectedTarget $expectedWebTarget `
        -Inventory $inventory `
        -MatchProperty 'matches_web_target'

    $allShortcutHashesStable = $true
    foreach ($item in $inventory) {
        $afterHash = Get-Sha256Safe ([string]$item.shortcut_path)
        $item['shortcut_sha256_after'] = $afterHash
        $item['shortcut_hash_unchanged'] = [bool]($afterHash -eq $item.shortcut_sha256_before)
        if (-not $item.shortcut_hash_unchanged) {
            $allShortcutHashesStable = $false
        }
    }
    $receipt.shortcut_hashes_unchanged = [bool]$allShortcutHashesStable

    $receipt.protected_baselines_after = @(Get-ProtectedBaselineSnapshot -FoxaiRoot $foxaiRoot -ExpectedHashes $expectedHashes)

    $baselinesUnchanged = $true
    foreach ($before in $receipt.protected_baselines_before) {
        $after = @($receipt.protected_baselines_after | Where-Object { $_.path -eq $before.path })[0]
        if ($null -eq $after -or $before.actual_sha256 -ne $after.actual_sha256) {
            $baselinesUnchanged = $false
            break
        }
    }
    $baselineExpectedPass = (@($receipt.protected_baselines_before | Where-Object { -not $_.matches_expected }).Count -eq 0)
    $resolutionErrors = @($inventory | Where-Object { -not $_.resolved }).Count

    $receipt.live_files_modified = [bool](-not ($baselinesUnchanged -and $allShortcutHashesStable))
    $receipt.shortcut_changes = [bool](-not $allShortcutHashesStable)

    $desktopState = [string]$receipt.contract_analysis.desktop.state
    $webState = [string]$receipt.contract_analysis.web.state

    if ($desktopState -eq 'unique_target_match' -and $webState -eq 'unique_target_match') {
        $receipt.next_safe_action = 'Correct Phase 3B shortcut discovery to use the resolved inventory paths, then rerun Phase 3B design. Do not edit the protected shortcuts.'
    } elseif ($desktopState -eq 'duplicate_target_matches' -or $webState -eq 'duplicate_target_matches') {
        $receipt.next_safe_action = 'Review duplicate shortcut matches and designate the canonical protected shortcut without deleting or editing any shortcut. Then correct and rerun Phase 3B.'
    } else {
        $receipt.next_safe_action = 'Review filename-hint candidates and their resolved properties. Correct the expected shortcut contract or search logic only after confirming the real protected shortcut. Do not proceed to Phase 3C.'
    }

    $receipt.state = 'read_only_probe_complete'
    $receipt.verified = [bool]($baselinesUnchanged -and $allShortcutHashesStable -and $resolutionErrors -eq 0)

    $inventoryPayload = [ordered]@{
        created = Get-IsoUtc
        root = $foxaiRoot
        expected_targets = [ordered]@{
            desktop = $expectedDesktopTarget
            web = $expectedWebTarget
        }
        search_scope = $receipt.search_scope
        shortcut_count = $inventory.Count
        resolved_count = @($inventory | Where-Object { $_.resolved }).Count
        resolution_error_count = $resolutionErrors
        inventory = @($inventory)
        contract_analysis = $receipt.contract_analysis
    }
    Write-Utf8NoBom -PathValue $inventoryJsonPath -Text ($inventoryPayload | ConvertTo-Json -Depth 14)

    $lines = New-Object System.Collections.ArrayList
    [void]$lines.Add('# FOXAI Portable Desktop Runtime Phase 3B-R1')
    [void]$lines.Add('## Read-Only Shortcut Inventory and Resolution Probe')
    [void]$lines.Add('')
    [void]$lines.Add("- Created: **$($receipt.created)**")
    [void]$lines.Add("- Root: ``$foxaiRoot``")
    [void]$lines.Add("- State: **$($receipt.state)**")
    [void]$lines.Add("- Verified read-only execution: **$($receipt.verified)**")
    [void]$lines.Add("- Live files modified: **$($receipt.live_files_modified)**")
    [void]$lines.Add("- Shortcuts changed: **$($receipt.shortcut_changes)**")
    [void]$lines.Add("- Desktop launched: **False**")
    [void]$lines.Add("- Packages installed: **False**")
    [void]$lines.Add("- Network access: **False**")
    [void]$lines.Add('')
    [void]$lines.Add('## Inventory summary')
    [void]$lines.Add('')
    [void]$lines.Add("- Shortcut files found: **$($inventory.Count)**")
    [void]$lines.Add("- Successfully resolved: **$(@($inventory | Where-Object { $_.resolved }).Count)**")
    [void]$lines.Add("- Resolution errors: **$resolutionErrors**")
    [void]$lines.Add("- Shortcut hashes unchanged: **$allShortcutHashesStable**")
    [void]$lines.Add("- Protected baselines unchanged: **$baselinesUnchanged**")
    [void]$lines.Add("- Protected baselines match Phase 3B receipt: **$baselineExpectedPass**")
    [void]$lines.Add('')
    [void]$lines.Add('## Expected target contracts')
    [void]$lines.Add('')
    [void]$lines.Add("- Desktop: ``$expectedDesktopTarget``")
    [void]$lines.Add("  - State: **$desktopState**")
    [void]$lines.Add("  - Exact target matches: **$($receipt.contract_analysis.desktop.match_count)**")
    [void]$lines.Add("  - Filename-hint candidates: **$($receipt.contract_analysis.desktop.filename_hint_count)**")
    [void]$lines.Add("- Web: ``$expectedWebTarget``")
    [void]$lines.Add("  - State: **$webState**")
    [void]$lines.Add("  - Exact target matches: **$($receipt.contract_analysis.web.match_count)**")
    [void]$lines.Add("  - Filename-hint candidates: **$($receipt.contract_analysis.web.filename_hint_count)**")
    [void]$lines.Add('')
    [void]$lines.Add('## Resolved shortcuts')
    [void]$lines.Add('')

    if ($inventory.Count -eq 0) {
        [void]$lines.Add('_No `.lnk` files were found in the bounded FOXAI USB search or the standard Desktop/Start Menu surfaces._')
    } else {
        foreach ($item in $inventory) {
            [void]$lines.Add("### ``$($item.shortcut_path)``")
            [void]$lines.Add('')
            [void]$lines.Add("- Resolved: **$($item.resolved)**")
            [void]$lines.Add("- Target: ``$($item.target_path)``")
            [void]$lines.Add("- Target exists: **$($item.target_exists)**")
            [void]$lines.Add("- Arguments: ``$($item.arguments)``")
            [void]$lines.Add("- Working directory: ``$($item.working_directory)``")
            [void]$lines.Add("- Working directory exists: **$($item.working_directory_exists)**")
            [void]$lines.Add("- Icon: ``$($item.icon_location_raw)``")
            [void]$lines.Add("- Icon exists: **$($item.icon_exists)**")
            [void]$lines.Add("- Target USB-owned: **$($item.target_is_usb_owned)**")
            [void]$lines.Add("- Working directory USB-owned: **$($item.working_directory_is_usb_owned)**")
            [void]$lines.Add("- Icon USB-owned: **$($item.icon_is_usb_owned)**")
            [void]$lines.Add("- Desktop target match: **$($item.matches_desktop_target)**")
            [void]$lines.Add("- Web target match: **$($item.matches_web_target)**")
            [void]$lines.Add("- Shortcut hash unchanged: **$($item.shortcut_hash_unchanged)**")
            if (-not [string]::IsNullOrWhiteSpace([string]$item.resolution_error)) {
                [void]$lines.Add("- Resolution error: ``$($item.resolution_error)``")
            }
            [void]$lines.Add('')
        }
    }

    [void]$lines.Add('## Interpretation')
    [void]$lines.Add('')
    [void]$lines.Add('This diagnostic does not require either expected shortcut to exist. Its job is to reveal the real shortcut inventory and properties without changing anything.')
    [void]$lines.Add('')
    [void]$lines.Add('## Next safe action')
    [void]$lines.Add('')
    [void]$lines.Add("**$($receipt.next_safe_action)**")
    [void]$lines.Add('')
    [void]$lines.Add('Phase 3C remains blocked until the protected shortcut contract is resolved and Phase 3B is rerun successfully.')

    Write-Utf8NoBom -PathValue $reportPath -Text (($lines -join [Environment]::NewLine) + [Environment]::NewLine)
    Write-Utf8NoBom -PathValue $receiptPath -Text ($receipt | ConvertTo-Json -Depth 14)

    $exitCode = 0
} catch {
    $receipt.state = 'stopped_fail_closed'
    $receipt.verified = $false
    $receipt.failure = [ordered]@{
        type = $_.Exception.GetType().FullName
        message = $_.Exception.Message
        script_stack = $_.ScriptStackTrace
    }
    try {
        Write-Utf8NoBom -PathValue $receiptPath -Text ($receipt | ConvertTo-Json -Depth 14)
        $failureReport = @(
            '# FOXAI Portable Desktop Runtime Phase 3B-R1',
            '## Read-Only Shortcut Inventory and Resolution Probe',
            '',
            '- State: **stopped_fail_closed**',
            '- Verified: **False**',
            '- Live files modified: **False unless the receipt proves otherwise**',
            '- Desktop launched: **False**',
            '- Packages installed: **False**',
            '- Network access: **False**',
            '',
            '## Failure',
            '',
            ('- Type: `' + $receipt.failure.type + '`'),
            ('- Message: `' + $receipt.failure.message + '`'),
            '',
            'Do not proceed to Phase 3C.'
        ) -join [Environment]::NewLine
        Write-Utf8NoBom -PathValue $reportPath -Text ($failureReport + [Environment]::NewLine)
    } catch {}
    Write-Host "PROBE STOPPED FAIL-CLOSED: $($_.Exception.Message)" -ForegroundColor Red
    $exitCode = 1
}

Write-Host ""
Write-Host "Output folder: $outputDir"
Write-Host "Report: $reportPath"
Write-Host "Receipt: $receiptPath"
exit $exitCode
