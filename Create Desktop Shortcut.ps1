$WScriptShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath("Desktop")
$Shortcut = $WScriptShell.CreateShortcut("$Desktop\FoxAI.lnk")
$Shortcut.TargetPath = "$PSScriptRoot\Start FoxAI.bat"
$Shortcut.WorkingDirectory = "$PSScriptRoot"
$Icon = "$PSScriptRoot\assets\foxai.ico"
if (Test-Path $Icon) { $Shortcut.IconLocation = $Icon }
$Shortcut.Save()
Write-Host "Created FoxAI desktop shortcut."
