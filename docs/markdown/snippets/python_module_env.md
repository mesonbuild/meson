## New option to choose python installation environment

It is now possible to specify `-Dpython.install_env` and choose how python modules are installed.

- `venv`: assume that a virtualenv is active and install to that
- `system`: install to the global site-packages of the selected interpreter
  (the one that the venv module calls --system-site-packages)
- `prefix`: preserve existing behavior
- `auto`: autodetect whether to use venv or system
