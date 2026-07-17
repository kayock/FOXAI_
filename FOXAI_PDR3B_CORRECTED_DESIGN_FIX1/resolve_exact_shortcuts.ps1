[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$DesktopShortcut,
    [Parameter(Mandatory = $true)][string]$WebShortcut
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
        # Preserve the readable value if Windows cannot canonicalize it.
    }

    $v = $v.Replace('/', '\')
    if ($v.Length -gt 3) {
        $v = $v.TrimEnd('\')
    }
    return $v
}

function Get-HashSafe {
    param([string]$PathValue)
    if (Test-Path -LiteralPath $PathValue -PathType Leaf) {
        return (Get-FileHash -LiteralPath $PathValue -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    return $null
}

function Parse-Icon {
    param([AllowNull()][string]$Raw, [string]$Base)

    if ([string]::IsNullOrWhiteSpace($Raw)) {
        return [ordered]@{ raw = ""; path = ""; index = $null }
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

    return [ordered]@{
        raw = $value
        path = $iconPath
        index = $index
    }
}

function Resolve-One {
    param([string]$ShortcutPath, [object]$Shell)

    $before = Get-HashSafe $ShortcutPath
    $record = [ordered]@{
        shortcut_path = Normalize-PathValue $ShortcutPath
        exists = [bool](Test-Path -LiteralPath $ShortcutPath -PathType Leaf)
        hash_before = $before
        resolved = $false
        target_raw = ""
        target = ""
        arguments = ""
        working_directory_raw = ""
        working_directory = ""
        icon_raw = ""
        icon_path = ""
        icon_index = $null
        description = ""
        error = $null
    }

    if ($record.exists) {
        try {
            $base = Split-Path -Parent $ShortcutPath
            $s = $Shell.CreateShortcut($ShortcutPath)
            $icon = Parse-Icon ([string]$s.IconLocation) $base
            $record.resolved = $true
            $record.target_raw = [string]$s.TargetPath
            $record.target = Normalize-PathValue ([string]$s.TargetPath) $base
            $record.arguments = [string]$s.Arguments
            $record.working_directory_raw = [string]$s.WorkingDirectory
            $record.working_directory = Normalize-PathValue ([string]$s.WorkingDirectory) $base
            $record.icon_raw = [string]$icon.raw
            $record.icon_path = [string]$icon.path
            $record.icon_index = $icon.index
            $record.description = [string]$s.Description
        } catch {
            $record.error = $_.Exception.Message
        }
    }

    $record.hash_after = Get-HashSafe $ShortcutPath
    $record.hash_unchanged = [bool]($record.hash_before -eq $record.hash_after)
    return [pscustomobject]$record
}

$shell = New-Object -ComObject WScript.Shell
$result = [ordered]@{
    desktop = Resolve-One $DesktopShortcut $shell
    web = Resolve-One $WebShortcut $shell
}
$result | ConvertTo-Json -Depth 10 -Compress
