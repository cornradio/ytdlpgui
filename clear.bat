@echo off
echo cleaning temp files...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "ytdlpgui.spec" del /f /q "ytdlpgui.spec"
echo clear done
pause 