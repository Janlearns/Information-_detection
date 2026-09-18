$ErrorActionPreference = 'Stop'
$projectPath = $PSScriptRoot
$pythonPath = Join-Path $projectPath '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Python proyek belum terpasang.' }
$extensions = @('.txt', '.md', '.srt', '.vtt', '.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff', '.mp4', '.mkv', '.webm', '.mov', '.avi', '.m4v')
foreach ($extension in $extensions) {
    $menuPath = 'HKCU:\Software\Classes\SystemFileAssociations\' + $extension + '\shell\CekFaktaScan'
    New-Item -Path $menuPath -Force | Out-Null
    Set-Item -LiteralPath $menuPath -Value 'Scan dengan CekFakta'
    New-ItemProperty -LiteralPath $menuPath -Name 'MultiSelectModel' -Value 'Single' -PropertyType String -Force | Out-Null
    $commandPath = Join-Path $menuPath 'command'
    New-Item -Path $commandPath -Force | Out-Null
    $launcherPath = Join-Path $projectPath 'scan-local-file.py'
    Set-Item -LiteralPath $commandPath -Value ('"' + $pythonPath + '" "' + $launcherPath + '" --file "%1"')
    $registeredCommand = (Get-Item -LiteralPath $commandPath).GetValue('')
    if (-not $registeredCommand.Contains($launcherPath)) { throw ('Verifikasi menu gagal: ' + $extension) }
}
Write-Host ('Menu Scan dengan CekFakta terpasang dan terverifikasi untuk ' + $extensions.Count + ' format file pada akun ' + [Environment]::UserName + '.')
