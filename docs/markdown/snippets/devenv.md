## `PYTHONPATH` automatically defined in `meson devenv`

`PYTHONPATH` now includes every directory where a python module is being
installed using [`python.install_sources()`](Python-module.md#install_sources)
and [`python.extension_module()`](Python-module.md#extension_module).

## Bash completion scripts sourced in `meson devenv`

If bash-completion scripts are being installed and the shell is bash, they will
be automatically sourced.
