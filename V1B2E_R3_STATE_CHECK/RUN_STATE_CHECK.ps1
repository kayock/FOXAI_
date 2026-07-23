$ErrorActionPreference = 'Stop'

$files = @(
    @{
        Name = 'director'
        Path = 'Z:\FOXAI\core\director.py'
        Old  = "    `"evidence`",`n"
        New  = "    `"ranked evidence`",`n"
    },
    @{
        Name = 'desktop'
        Path = 'Z:\FOXAI\ui\main_window.py'
        Old  = "            answer = f`"[Model: {model_used}]\n\n{answer}`"`n"
        New  = "            if not answer.lstrip().startswith(`"[Model:`"):`n                answer = f`"[Model: {model_used}]\n\n{answer}`"`n"
    }
)

Write-Host ''
Write-Host 'AGENT FOX V1B-2E R3 READ-ONLY STATE CHECK'
Write-Host '------------------------------------------------------------'

$rows = foreach ($file in $files) {
    $path = $file.Path
    if (-not (Test-Path -LiteralPath $path)) {
        [pscustomobject]@{
            Name     = $file.Name
            Status   = 'MISSING'
            Size     = '-'
            SHA256   = '-'
            OldCount = '-'
            NewCount = '-'
        }
        continue
    }

    $text = [IO.File]::ReadAllText($path).Replace("`r`n", "`n")
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
    $oldCount = ([regex]::Matches($text, [regex]::Escape($file.Old))).Count
    $newCount = ([regex]::Matches($text, [regex]::Escape($file.New))).Count

    $status = if ($oldCount -eq 1) {
        'OLD_PRESENT'
    } elseif ($newCount -eq 1) {
        'NEW_PRESENT'
    } else {
        'OTHER'
    }

    [pscustomobject]@{
        Name     = $file.Name
        Status   = $status
        Size     = (Get-Item -LiteralPath $path).Length
        SHA256   = $hash
        OldCount = $oldCount
        NewCount = $newCount
    }
}

$rows | Format-Table -AutoSize
Write-Host ''
Write-Host 'No files were changed. Copy the table above and return it to Sol.'
