## Developer environment improvements

When cross compiling, the developer environment now sets all environment
variables for the HOST machine. It now also sets `QEMU_LD_PREFIX` to the
`sys_root` value from cross file if property is defined. That means that cross
compiled executables can often be run transparently on the build machine, for
example when cross compiling for aarch64 linux from x86_64 linux.

A new argument `--workdir` has been added, by default it is set to build
directory. For example, `meson devenv -C builddir --workdir .` can be used to
remain in the current dir (often source dir) instead.

`--dump` now prints shell commands like `FOO="/prepend/path:$FOO:/append/path"`,
using the literal `$FOO` instead of current value of `FOO` from environment.
This makes easier to evaluate those expressions in a different environment.
