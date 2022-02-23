## `PYTHONPATH` automatically defined in `meson devenv`

`PYTHONPATH` now includes every directory where a python module is being
installed using [`python.install_sources()`](Python-module.md#install_sources)
and [`python.extension_module()`](Python-module.md#extension_module).

## Bash completion scripts sourced in `meson devenv`

If bash-completion scripts are being installed and the shell is bash, they will
be automatically sourced.

## Setup GDB auto-load for `meson devenv`

When GDB helper scripts (*-gdb.py, *-gdb.gdb, and *-gdb.csm) are installed with
a library name that matches one being built, Meson adds the needed auto-load
commands into `<builddir>/.gdbinit` file. When running gdb from top build
directory, that file is loaded by gdb automatically.

