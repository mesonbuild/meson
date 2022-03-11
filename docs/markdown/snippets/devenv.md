## Bash completion scripts sourced in `meson devenv`

If bash-completion scripts are being installed and the shell is bash, they will
be automatically sourced.

## Setup GDB auto-load for `meson devenv`

When GDB helper scripts (*-gdb.py, *-gdb.gdb, and *-gdb.csm) are installed with
a library name that matches one being built, Meson adds the needed auto-load
commands into `<builddir>/.gdbinit` file. When running gdb from top build
directory, that file is loaded by gdb automatically.

## Print modified environment variables with `meson devenv --dump`

With `--dump` option, all envorinment variables that have been modified are
printed instead of starting an interactive shell. It can be used by shell
scripts that wish to setup their environment themself.

## New `method` and `separator` kwargs on `environment()` and `meson.add_devenv()`

It simplifies this common pattern:
```meson
env = environment()
env.prepend('FOO', ['a', 'b'], separator: ',')
meson.add_devenv(env)
```

becomes one line:
```meson
meson.add_devenv({'FOO': ['a', 'b']}, method: 'prepend', separator: ',')
```

or two lines:
```meson
env = environment({'FOO': ['a', 'b']}, method: 'prepend', separator: ',')
meson.add_devenv(env)
```
