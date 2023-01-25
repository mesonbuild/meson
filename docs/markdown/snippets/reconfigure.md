## Allow --reconfigure and --wipe of empty builddir

`meson setup --reconfigure builddir` and `meson setup --wipe builddir` are now
accepting `builddir/` to be empty or containing a previously failed setup attempt.
Note that in that case previously passed command line options must be repeated
as only a successful build saves configured options.

This is useful for example with scripts that always repeat all options,
`meson setup builddir --wipe -Dfoo=bar` will always work regardless whether
it is a first invocation or not.
