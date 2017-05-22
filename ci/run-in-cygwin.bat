if _%arch%_ == _x64_ set CYGWIN_ROOT=C:\cygwin64
if _%arch%_ == _x86_ set CYGWIN_ROOT=C:\cygwin

set PATH=%CYGWIN_ROOT%\bin;%SYSTEMROOT%\system32

env.exe -- %*
