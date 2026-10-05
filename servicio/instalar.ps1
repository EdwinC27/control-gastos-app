# instalar.ps1
#
# Deja Control de Gastos corriendo solo:
#   1. crea una tarea programada que lo arranca al iniciar sesion
#   2. pone un acceso directo en el escritorio
#   3. lo arranca de una vez
#
# No necesita permisos de administrador. Se corre asi:
#
#   powershell -ExecutionPolicy Bypass -File .\servicio\instalar.ps1

$ErrorActionPreference = "Stop"

$raiz  = Split-Path -Parent $PSScriptRoot
$vbs   = Join-Path $PSScriptRoot "iniciar.vbs"
$tarea = "Control de Gastos"

Write-Host "Carpeta del proyecto: $raiz"

# --- 0. encontrar pythonw.exe ----------------------------------------
$python = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source

if (-not $python) {
    $consola = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    if ($consola) {
        $python = Join-Path (Split-Path -Parent $consola) "pythonw.exe"
        if (-not (Test-Path $python)) { $python = $consola }
    }
}

if (-not $python) {
    Write-Error "No encontre Python en el PATH. Instalalo desde python.org marcando 'Add Python to PATH' y vuelve a correr este script."
    exit 1
}

Set-Content -Path (Join-Path $PSScriptRoot "pythonw.txt") -Value $python -Encoding ASCII
Write-Host "Python: $python"

# --- 1. tarea programada --------------------------------------------
$accion = New-ScheduledTaskAction `
    -Execute "wscript.exe" `
    -Argument "`"$vbs`"" `
    -WorkingDirectory $raiz

$usuario = "$env:USERDOMAIN\$env:USERNAME"
$disparador = New-ScheduledTaskTrigger -AtLogOn -User $usuario

$opciones = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask `
    -TaskName $tarea `
    -Action $accion `
    -Trigger $disparador `
    -Settings $opciones `
    -Description "Arranca Control de Gastos en http://127.0.0.1:2004" `
    -Force | Out-Null

Write-Host "Tarea programada creada: $tarea"

# --- 2. acceso directo en el escritorio ------------------------------
$escritorio = [Environment]::GetFolderPath("Desktop")
$acceso = Join-Path $escritorio "Control de Gastos.url"
$icono = Join-Path $raiz "static\favicon.ico"

@"
[InternetShortcut]
URL=http://127.0.0.1:2004/
IconFile=$icono
IconIndex=0
"@ | Set-Content -Path $acceso -Encoding ASCII

Write-Host "Acceso directo en el escritorio: $acceso"

# --- 3. arrancar ahora -----------------------------------------------
Start-ScheduledTask -TaskName $tarea
Start-Sleep -Seconds 3

try {
    Invoke-WebRequest -Uri "http://127.0.0.1:2004/" -UseBasicParsing -TimeoutSec 5 | Out-Null
    Write-Host ""
    Write-Host "Listo: la app ya responde en http://127.0.0.1:2004/"
} catch {
    Write-Warning "La app todavia no responde. Revisa data\servidor.log en unos segundos."
}
