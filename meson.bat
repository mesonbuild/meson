@REM Locate Python
@REM Reset error level before each chheck of Python availability.

@REM No need to bother with Py launcher as it is still necessary to use relative/absolute path to run this script if Python
@REM is not in PATH. That's because this script is deployed with each Pypi installation of Meson.
@REM This is not a center-stage script that tries to run various versions of Python from an outside location.

@REM Check if Python is in PATH or current folder.
@set ERRORLEVEL=0
@where /q python.exe
@IF ERRORLEVEL 1 GOTO NotInPATHPython
@FOR /F "tokens=* USEBACKQ" %%F IN (`where python.exe`) DO @SET pythonloc=%%F
@set pythonloc="%pythonloc%"
@GOTO CheckMeson

:NotInPATHPython
@REM Check if Python is in parent folder as it is tipical for a Pypi installation. Last chance of finding Python.
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
