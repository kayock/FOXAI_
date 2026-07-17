param(
    [Parameter(Mandatory=$true)][string]$UsbRoot,
    [Parameter(Mandatory=$true)][string]$OutputPath
)

$ErrorActionPreference = "Stop"
$names = @(
    "Launch FOXAI Workshop.bat - Shortcut.lnk",
    "START_FOXAI_WEB_PORTABLE.bat - Shortcut.lnk"
)

$shell = New-Object -ComObject WScript.Shell
$items = @()

foreach ($name in $names) {
    $path = Join-Path $UsbRoot $name
    $item = [ordered]@{
        name = $name
        path = $path
        exists = Test-Path -LiteralPath $path -PathType Leaf
        target_path = $null
        arguments = $null
        working_directory = $null
        icon_location = $null
        window_style = $null
        hotkey = $null
        description = $null
        error = $null
    }

    if ($item.exists) {
        try {
            $shortcut = $shell.CreateShortcut($path)
            $item.target_path = $shortcut.TargetPath
            $item.arguments = $shortcut.Arguments
            $item.working_directory = $shortcut.WorkingDirectory
            $item.icon_location = $shortcut.IconLocation
            $item.window_style = $shortcut.WindowStyle
            $item.hotkey = $shortcut.Hotkey
            $item.description = $shortcut.Description
        }
        catch {
            $item.error = $_.Exception.Message
        }
    }

    $items += [pscustomobject]$item
}

$result = [ordered]@{
    action = "foxai_phase3f_shortcut_read_only_probe"
    created_utc = [DateTime]::UtcNow.ToString("o")
    usb_root = $UsbRoot
    items = $items
}

$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
