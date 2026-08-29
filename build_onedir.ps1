$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$FinalName = -join ([char[]](0x50, 0x44, 0x46, 0x8F6C, 0x57, 0x6F, 0x72, 0x64, 0x542F, 0x52A8, 0x5668))
$BuildName = "pdf2word_launcher"
$VenvDir = Join-Path $ProjectRoot ".build-venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$BuiltDir = Join-Path $ProjectRoot ("dist\{0}" -f $BuildName)
$FinalDir = Join-Path $ProjectRoot ("dist\{0}" -f $FinalName)
$BuiltExe = Join-Path $BuiltDir ("{0}.exe" -f $BuildName)
$FinalExe = Join-Path $FinalDir ("{0}.exe" -f $FinalName)

if (-not (Test-Path $VenvPython)) {
    python -m venv $VenvDir
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt

if (Test-Path $FinalDir) {
    throw "Final output already exists: $FinalDir. Rename or remove it before rebuilding."
}

& $VenvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name $BuildName `
    --contents-directory "_internal" `
    --hidden-import "fitz" `
    --hidden-import "pymupdf" `
    --exclude-module "matplotlib" `
    --exclude-module "pandas" `
    --exclude-module "scipy" `
    --exclude-module "PyQt5" `
    --exclude-module "PyQt6" `
    --exclude-module "PySide2" `
    --exclude-module "PySide6" `
    --distpath "dist" `
    --workpath "build" `
    "pdf2word_gui.py"

Rename-Item -LiteralPath $BuiltDir -NewName $FinalName
Rename-Item -LiteralPath (Join-Path $FinalDir ("{0}.exe" -f $BuildName)) -NewName ("{0}.exe" -f $FinalName)

New-Item -ItemType Directory -Force -Path (Join-Path $FinalDir "logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $FinalDir "outputs") | Out-Null
 
# --- Post-build verification: ensure Tcl/Tk DLL versions match scripts ---
$TclDll = Join-Path $FinalDir "_internal\tcl86t.dll"
$TkDll  = Join-Path $FinalDir "_internal\tk86t.dll"
$InitTcl = Join-Path $FinalDir "_internal\_tcl_data\init.tcl"

if (Test-Path $TclDll -and (Test-Path $InitTcl)) {
    $TclVer = (Get-Item $TclDll).VersionInfo.ProductVersion
    $TkVer  = (Get-Item $TkDll).VersionInfo.ProductVersion
    $NeedVer = if (Select-String -Path $InitTcl -Pattern "package require -exact Tcl (\S+)" -AllMatches) { $Matches[1] } else { $null }

    if ($NeedVer -and $TclVer -ne $NeedVer) {
        Write-Host ""
        Write-Host "WARNING: tcl86t.dll version ($TclVer) does not match init.tcl requirement ($NeedVer)." -ForegroundColor Yellow
        Write-Host "Copying correct tcl86t.dll from system Python..." -ForegroundColor Yellow
        $PythonTcl = Join-Path (Split-Path (Split-Path (Get-Command python).Source)) "Library\bin\tcl86t.dll"
        if (Test-Path $PythonTcl) {
            Copy-Item -LiteralPath $PythonTcl -Destination $TclDll -Force
            Write-Host "Fixed tcl86t.dll -> $((Get-Item $TclDll).VersionInfo.ProductVersion)" -ForegroundColor Green
        } else {
            Write-Host "ERROR: could not find correct tcl86t.dll at $PythonTcl. Build may be broken." -ForegroundColor Red
        }
    }
    if ($TkVer -ne $NeedVer) {
        Write-Host "WARNING: tk86t.dll version ($TkVer) does not match init.tcl requirement ($NeedVer)." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host ("Build complete: {0}" -f $FinalDir)
Write-Host ("Launcher: {0}" -f $FinalExe)
Write-Host ("Runtime: {0}" -f (Join-Path $FinalDir "_internal"))
Write-Host ("Logs: {0}" -f (Join-Path $FinalDir "logs"))
Write-Host ("Default outputs: {0}" -f (Join-Path $FinalDir "outputs"))
