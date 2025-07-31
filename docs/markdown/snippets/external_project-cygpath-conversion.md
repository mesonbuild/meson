## The external_project module uses the cygpath command to convert paths

In previous versions, the external_project module on Windows used a Windows-style path (e.g., `C:/path/to/configure`) to execute the configure file, and a relative path from the drive root (e.g., `/path/to/prefix`) as the installation prefix.
However, since configure scripts are typically intended to be run in a POSIX-like environment (MSYS2, Cygwin, or GitBash), these paths were incompatible with some configure scripts.

The external_project module now uses the `cygpath` command to convert the configure command path and prefix to Unix-style paths (e.g., `/c/path/to/configure` for MSYS2 and `/cygdrive/c/path/to/configure` for Cygwin).
If the `cygpath` command is not found in the PATH, it will fall back to the previous behavior.
