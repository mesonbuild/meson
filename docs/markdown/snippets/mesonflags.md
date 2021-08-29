## MESONFLAGS environment

MESONFLAGS environment variable can be used to pass `-j`, `-l` and `-v` options
to `meson compile` command. Note that command line arguments always override the
value passed by environment. Example: `MESONFLAGS=-j10 meson compile -C builddir`.

