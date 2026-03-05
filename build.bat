@echo off
title FW LUA Script - Build EXE
color 0B

echo.
echo  =========================================
echo   FW LUA Script - Build to EXE
echo  =========================================
echo.

:: ── Python ───────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install Python 3.10+ and add to PATH.
    pause & exit /b 1
)

:: ── PyInstaller ───────────────────────────────────────────────
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo  [*] Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo  [ERROR] Failed to install PyInstaller.
        pause & exit /b 1
    )
)

:: ── Verificar arquivos necessarios ───────────────────────────
echo  [*] Verificando arquivos...
set MISSING=0

if exist icon.ico (
    echo      icon.ico       OK
    set ICON_FLAG=--icon=icon.ico
    set ICON_DATA=--add-data "icon.ico;."
) else (
    echo      icon.ico       NAO ENCONTRADO - build sem icone
    set ICON_FLAG=
    set ICON_DATA=
    set MISSING_ICON=1
)

if exist unluac.jar (
    echo      unluac.jar     OK - sera incluido no .exe
    set UNLUAC_DATA=--add-data "unluac.jar;."
) else (
    echo      unluac.jar     NAO ENCONTRADO
    echo      [!] Compile o unluac.jar primeiro com build_unluac.bat
    set MISSING=1
)

if exist luac.exe (
    echo      luac.exe       OK - sera incluido no .exe
    set LUAC_DATA=--add-data "luac.exe;."
) else (
    echo      luac.exe       NAO ENCONTRADO
    echo      [!] Coloque o luac.exe aqui antes de buildar
    set MISSING=1
)

:: Verificar DLLs do Lua (opcionais mas recomendadas)
set DLL_DATA=
if exist lua51.dll (
    echo      lua51.dll      OK - sera incluida no .exe
    set DLL_DATA=%DLL_DATA% --add-data "lua51.dll;."
) else (
    echo      lua51.dll      nao encontrada ^(opcional^)
)
if exist lua5.1.dll (
    echo      lua5.1.dll     OK - sera incluida no .exe
    set DLL_DATA=%DLL_DATA% --add-data "lua5.1.dll;."
)

echo.
if %MISSING%==1 (
    echo  [ERROR] Arquivos obrigatorios em falta. Veja mensagens acima.
    pause & exit /b 1
)

:: ── Build ─────────────────────────────────────────────────────
echo  [*] Building...
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "FW LUA Script" ^
    --clean ^
    %ICON_FLAG% ^
    %ICON_DATA% ^
    %UNLUAC_DATA% ^
    %LUAC_DATA% ^
    %DLL_DATA% ^
    fw_lua_script.py

if errorlevel 1 (
    echo.
    echo  [ERROR] Build falhou. Veja erros acima.
    pause & exit /b 1
)

echo.
echo  =========================================
echo   Build completo!
echo   Output: dist\FW LUA Script.exe
echo.
echo   O .exe ja contem:
echo     - unluac.jar
echo     - luac.exe
if exist lua51.dll echo     - lua51.dll
if exist lua5.1.dll echo     - lua5.1.dll
if exist icon.ico echo     - icon.ico
echo  =========================================
echo.

if exist dist\ explorer dist\
pause
