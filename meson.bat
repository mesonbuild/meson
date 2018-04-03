@REM Locate Python
@REM Reset error level before checking if Python is reachable
@set ERRORLEVEL=0
@where /q python.exe
@IF ERRORLEVEL 1 GOTO NotInPATHPython
@FOR /F "tokens=* USEBACKQ" %%F IN (`where python.exe`) DO @SET pythonloc=%%F
@set pythonloc="%pythonloc%"
@GOTO CheckMeson

:NotInPATHPython
@set pythonloc="%~dp0
@if NOT "%pythonloc:~-1%"=="\" pythonloc=%pythonloc%\
@set pythonloc=%pythonloc%..\python.exe"
@IF NOT EXIST %pythonloc% GOTO missingpython

:CheckMeson
@REM Make sure Meson is installed correctly
@IF NOT EXIST %pythonloc:python.exe=Scripts\meson.py% GOTO nomeson

@REM Launch Meson
@%pythonloc% %pythonloc:python.exe=Scripts\meson.py% %*
@GOTO exit

:missingpython
@echo Fatal: Couldn't find Python 3.x
@GOTO exit

:nomeson
@echo Fatal: Meson is not installed or installation is damaged.

:exit
@pause
