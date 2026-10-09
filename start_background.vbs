Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath

' Tenta usar o pythonw do .venv se existir, senão usa pythonw global
If fso.FileExists(strPath & "\.venv\Scripts\pythonw.exe") Then
    WshShell.Run """" & strPath & "\.venv\Scripts\pythonw.exe"" main.py", 0, False
Else
    WshShell.Run "pythonw main.py", 0, False
End If
