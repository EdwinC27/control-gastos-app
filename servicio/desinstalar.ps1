# desinstalar.ps1
#
# Quita la tarea programada, el acceso directo y detiene el servidor.
#
#   powershell -ExecutionPolicy Bypass -File .\servicio\desinstalar.ps1

$ErrorActionPreference = "Continue"

$tarea = "Control de Gastos"

# --- detener lo que este escuchando en el puerto 2004 ----------------
try {
    $conexiones = Get-NetTCPConnection -LocalPort 2004 -State Listen -ErrorAction SilentlyContinue
    foreach ($conexion in $conexiones) {
        Stop-Process -Id $conexion.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Host "Servidor detenido (proceso $($conexion.OwningProcess))"
    }
} catch {
    Write-Warning "No se pudo revisar el puerto 2004: $_"
}

# --- quitar la tarea --------------------------------------------------
if (Get-ScheduledTask -TaskName $tarea -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $tarea -Confirm:$false
    Write-Host "Tarea programada eliminada: $tarea"
} else {
    Write-Host "No habia tarea programada que quitar."
}

# --- quitar el acceso directo ----------------------------------------
$acceso = Join-Path ([Environment]::GetFolderPath("Desktop")) "Control de Gastos.url"

if (Test-Path $acceso) {
    Remove-Item $acceso -Force
    Write-Host "Acceso directo eliminado."
}

Write-Host ""
Write-Host "Listo. Tus datos en data\ siguen intactos."
