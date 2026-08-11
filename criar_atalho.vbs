Dim fso, oWS, scriptDir, sLinkFile, oLink

Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

Set oWS = CreateObject("WScript.Shell")
sLinkFile = oWS.SpecialFolders("Desktop") & "\Aplicativo de vendas.lnk"

Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = scriptDir & "\iniciar.bat"
oLink.WorkingDirectory = scriptDir
oLink.Description = "Aplicativo de Vendas"
oLink.Save

MsgBox "Atalho 'Aplicativo de vendas' criado na sua Area de Trabalho!"
