Set objShell = CreateObject("WScript.Shell")
projectDir = objShell.CurrentDirectory

' Check for Python in known locations
pythonPath = ""
paths = Array( _
    objShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Python311\python.exe", _
    "C:\Python311\python.exe", _
    "C:\Python312\python.exe" _
)

For Each p In paths
    Set fso = CreateObject("Scripting.FileSystemObject")
    If fso.FileExists(p) Then
        pythonPath = p
        Exit For
    End If
Next

If pythonPath = "" Then
    MsgBox "Python 3.11 not found. Please install from python.org", 48, "Gaokao Agent"
    WScript.Quit 1
End If

' Build command
cmd = """" & pythonPath & """ -X utf8 -m src.main ui"

' Set environment
Set env = objShell.Environment("Process")
env("PYTHONIOENCODING") = "utf-8"
env("PYTHONUTF8") = "1"
env("PYTHONPATH") = projectDir

objShell.CurrentDirectory = projectDir
returnCode = objShell.Run(cmd, 1, True)
WScript.Quit returnCode