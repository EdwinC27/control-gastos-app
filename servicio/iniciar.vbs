' iniciar.vbs
' Lanza el servidor de Control de Gastos sin ventana de consola.
' Lo usa la tarea programada que corre al iniciar sesion.

Option Explicit

Dim fso, shell, carpetaServicio, raiz, python, archivoRuta, comando

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

carpetaServicio = fso.GetParentFolderName(WScript.ScriptFullName)
raiz = fso.GetParentFolderName(carpetaServicio)

shell.CurrentDirectory = raiz

' instalar.ps1 deja aqui la ruta exacta de pythonw.exe
archivoRuta = fso.BuildPath(carpetaServicio, "pythonw.txt")
python = "pythonw.exe"

If fso.FileExists(archivoRuta) Then
    python = Trim(fso.OpenTextFile(archivoRuta, 1).ReadAll())
End If

comando = """" & python & """ """ & fso.BuildPath(raiz, "servidor.py") & """"

' 0 = ventana oculta, False = no esperar a que termine
shell.Run comando, 0, False
