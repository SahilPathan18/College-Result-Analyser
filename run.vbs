Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\projects\result-analyzer"
WshShell.Run """D:\projects\result-analyzer\venv\Scripts\pythonw.exe"" src\main.py", 0, False
