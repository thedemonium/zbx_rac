@echo off
set SrvcName="1C:Enterprise RAS"
set BinPath="C:\Program Files\1cv8\8.3.27.1688\bin\ras.exe cluster --service --port=1545"
set Desctiption="1C:Enterprise RAS"
sc stop %SrvcName%
sc delete %SrvcName%
sc create %SrvcName% binPath= %BinPath% start= auto displayname= %Desctiption%
sc start %SrvcName%