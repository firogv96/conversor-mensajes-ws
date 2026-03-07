@echo off

echo Compilando con PyInstaller...
pyinstaller "Conversor de Mensajes.spec"

echo.
echo Compilacion finalizada. El ejecutable se encuentra en la carpeta dist.
pause
