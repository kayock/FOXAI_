param(
    [Parameter(Mandatory = $true)]
    [string]$RepoRoot
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Section {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 64) -ForegroundColor DarkCyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host ("=" * 64) -ForegroundColor DarkCyan
}

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [switch]$AllowFailure
    )

    $output = & git -C $script:Root @Arguments 2>&1
    $code = $LASTEXITCODE

    if (-not $AllowFailure -and $code -ne 0) {
        $message = ($output | Out-String).Trim()
        throw "git $($Arguments -join ' ') failed with code $code.`n$message"
    }

    [pscustomobject]@{
        Code = $code
        Output = @($output)
        Text = (($output | Out-String).Trim())
    }
}

$script:Root = [System.IO.Path]::GetFullPath($RepoRoot)
$stamp = Get-Date -Format "yyyyMMddTHHmmss"
$reportFolder = Join-Path $script:Root "Reports\GitHubUploads"
$reportPath = Join-Path $reportFolder "$stamp-source-upload.txt"
$temporaryIndex = Join-Path $env:TEMP "foxai-github-source-$stamp.index"
$previousIndex = $env:GIT_INDEX_FILE

New-Item -ItemType Directory -Path $reportFolder -Force | Out-Null

try {
    Write-Section "FOXAI SAFE GITHUB SOURCE UPLOAD"
    Write-Host "Repository: $script:Root"
    Write-Host "Mode: clean source snapshot"
    Write-Host "Live runtime files are never deleted or moved."
    Write-Host ""

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Git was not found in PATH."
    }

    $inside = Invoke-Git -Arguments @("rev-parse", "--is-inside-work-tree")
    if ($inside.Text -ne "true") {
        throw "Z:\FOXAI is not recognized as a Git repository."
    }

    $remote = Invoke-Git -Arguments @("remote", "get-url", "origin") -AllowFailure
    if ($remote.Code -ne 0 -or [string]::IsNullOrWhiteSpace($remote.Text)) {
        throw "Git remote 'origin' is not configured."
    }
    Write-Host "Remote: $($remote.Text)"

    $name = (Invoke-Git -Arguments @("config", "--get", "user.name") -AllowFailure).Text
    if ([string]::IsNullOrWhiteSpace($name)) {
        $name = Read-Host "Git author name"
        if ([string]::IsNullOrWhiteSpace($name)) {
            throw "A Git author name is required."
        }
        Invoke-Git -Arguments @("config", "user.name", $name) | Out-Null
    }

    $email = (Invoke-Git -Arguments @("config", "--get", "user.email") -AllowFailure).Text
    if ([string]::IsNullOrWhiteSpace($email)) {
        $email = Read-Host "Git author email"
        if ([string]::IsNullOrWhiteSpace($email)) {
            throw "A Git author email is required."
        }
        Invoke-Git -Arguments @("config", "user.email", $email) | Out-Null
    }

    Write-Section "CHECKING REMOTE MAIN"
    Invoke-Git -Arguments @("fetch", "origin", "main") -AllowFailure | Out-Null

    $parentCheck = Invoke-Git -Arguments @(
        "rev-parse",
        "--verify",
        "refs/remotes/origin/main"
    ) -AllowFailure

    $parent = $null
    if ($parentCheck.Code -eq 0 -and -not [string]::IsNullOrWhiteSpace($parentCheck.Text)) {
        $parent = $parentCheck.Text.Trim()
        Write-Host "Remote main exists. The new source snapshot will build on it."
    }
    else {
        Write-Host "Remote main does not exist yet. This will be the first source snapshot."
    }

    Write-Section "BUILDING CLEAN TEMPORARY SOURCE INDEX"
    if (Test-Path -LiteralPath $temporaryIndex) {
        Remove-Item -LiteralPath $temporaryIndex -Force
    }

    $env:GIT_INDEX_FILE = $temporaryIndex

    if ($parent) {
        Invoke-Git -Arguments @("read-tree", $parent) | Out-Null
        Invoke-Git -Arguments @(
            "rm",
            "-r",
            "--cached",
            "--ignore-unmatch",
            "."
        ) -AllowFailure | Out-Null
    }
    else {
        Invoke-Git -Arguments @("read-tree", "--empty") | Out-Null
    }

    Invoke-Git -Arguments @("add", "-A", "--", ".") | Out-Null

    $trackedResult = Invoke-Git -Arguments @("ls-files")
    $trackedFiles = @(
        $trackedResult.Output |
        ForEach-Object { "$_".Trim() } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )

    if ($trackedFiles.Count -eq 0) {
        throw "No source files remain after applying .gitignore."
    }

    $limitBytes = 95MB
    $largeFiles = New-Object System.Collections.Generic.List[object]
    $totalBytes = [int64]0

    foreach ($relative in $trackedFiles) {
        $full = Join-Path $script:Root $relative
        if (Test-Path -LiteralPath $full -PathType Leaf) {
            $item = Get-Item -LiteralPath $full -Force
            $totalBytes += [int64]$item.Length
            if ($item.Length -gt $limitBytes) {
                $largeFiles.Add(
                    [pscustomobject]@{
                        Path = $relative
                        Bytes = [int64]$item.Length
                        MiB = [math]::Round($item.Length / 1MB, 2)
                    }
                )
            }
        }
    }

    $summary = @(
        "FOXAI GitHub source snapshot check",
        "Created: $(Get-Date -Format o)",
        "Repository: $script:Root",
        "Remote: $($remote.Text)",
        "Files selected: $($trackedFiles.Count)",
        "Selected size MiB: $([math]::Round($totalBytes / 1MB, 2))",
        "Oversized files: $($largeFiles.Count)",
        ""
    )

    if ($largeFiles.Count -gt 0) {
        $summary += "BLOCKED FILES:"
        foreach ($file in $largeFiles) {
            $summary += "$($file.MiB) MiB`t$($file.Path)"
        }
        $summary | Set-Content -LiteralPath $reportPath -Encoding UTF8

        Write-Host ""
        Write-Host "UPLOAD BLOCKED BEFORE COMMIT OR PUSH." -ForegroundColor Red
        Write-Host "These source-selected files exceed the safe limit:"
        foreach ($file in $largeFiles) {
            Write-Host ("  {0,8} MiB  {1}" -f $file.MiB, $file.Path) -ForegroundColor Yellow
        }
        Write-Host ""
        Write-Host "Report: $reportPath"
        exit 20
    }

    $summary += "No oversized source-selected files were found."
    $summary | Set-Content -LiteralPath $reportPath -Encoding UTF8

    Write-Host "Files selected: $($trackedFiles.Count)"
    Write-Host "Selected size: $([math]::Round($totalBytes / 1MB, 2)) MiB"
    Write-Host "Oversized files: 0"
    Write-Host "Report: $reportPath"

    Write-Section "SOURCE SNAPSHOT PREVIEW"
    $status = Invoke-Git -Arguments @("status", "--short")
    if (-not [string]::IsNullOrWhiteSpace($status.Text)) {
        $previewLines = @($status.Output | Select-Object -First 80)
        $previewLines | ForEach-Object { Write-Host $_ }
        if ($status.Output.Count -gt 80) {
            Write-Host "... $($status.Output.Count - 80) additional changes"
        }
    }
    else {
        Write-Host "No source differences from remote main."
    }

    $message = Read-Host "Commit message (blank = FOXAI source snapshot $stamp)"
    if ([string]::IsNullOrWhiteSpace($message)) {
        $message = "FOXAI source snapshot $stamp"
    }

    $answer = Read-Host "Push this clean source snapshot to origin/main? [Y/N]"
    if ($answer -notmatch '^[Yy]') {
        Write-Host "Cancelled. No network push occurred."
        exit 0
    }

    Write-Section "CREATING SOURCE COMMIT"
    $tree = (Invoke-Git -Arguments @("write-tree")).Text.Trim()
    if ([string]::IsNullOrWhiteSpace($tree)) {
        throw "Git did not create a source tree."
    }

    $commitArguments = @("commit-tree", $tree, "-m", $message)
    if ($parent) {
        $commitArguments += @("-p", $parent)
    }

    $commit = (Invoke-Git -Arguments $commitArguments).Text.Trim()
    if ([string]::IsNullOrWhiteSpace($commit)) {
        throw "Git did not create a source commit."
    }

    Write-Host "Source commit: $commit"

    Write-Section "PUSHING SOURCE SNAPSHOT"
    Invoke-Git -Arguments @(
        "push",
        "origin",
        "$commit`:refs/heads/main"
    ) | Out-Null

    Add-Content -LiteralPath $reportPath -Encoding UTF8 -Value @(
        "",
        "Commit: $commit",
        "Push: successful",
        "Completed: $(Get-Date -Format o)"
    )

    Write-Host "SUCCESS: FOXAI source snapshot uploaded to origin/main." -ForegroundColor Green
    Write-Host ""
    Write-Host "Your current local branch, local history, runtime, models,"
    Write-Host "wheelhouse, DLLs, databases, and outputs were not altered."
    Write-Host "Report: $reportPath"
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Host ""
    Write-Host "UPLOAD STOPPED: $message" -ForegroundColor Red
    try {
        Add-Content -LiteralPath $reportPath -Encoding UTF8 -Value @(
            "",
            "Error: $message",
            "Stopped: $(Get-Date -Format o)"
        )
        Write-Host "Report: $reportPath"
    }
    catch {
    }
    exit 1
}
finally {
    if ($null -eq $previousIndex) {
        Remove-Item Env:\GIT_INDEX_FILE -ErrorAction SilentlyContinue
    }
    else {
        $env:GIT_INDEX_FILE = $previousIndex
    }

    if (Test-Path -LiteralPath $temporaryIndex) {
        Remove-Item -LiteralPath $temporaryIndex -Force -ErrorAction SilentlyContinue
    }
}
