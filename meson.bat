@REM Reset error level before checking if Python is reachable
@set ERRORLEVEL=0
@where /q python.exe
@IF ERRORLEVEL 1 GOTO missingpython

@REM Locate Python and make sure Meson is installed correctly
@FOR /F "tokens=* USEBACKQ" %%F IN (`where python.exe`) DO @SET pythonloc=%%F
@IF NOT EXIST "%pythonloc:python.exe=Scripts\meson.py%" GOTO nomeson

@REM Launch Meson
@"%pythonloc%" "%pythonloc:python.exe=Scripts\meson.py%" %*
@GOTO exit

:missingpython
@echo Fatal: Couldm't find Python 3.x
@GOTO exit

:nomeson
@echo Fatal: Meson is not installed or installation is damaged.

:exit
@pause
@exit
