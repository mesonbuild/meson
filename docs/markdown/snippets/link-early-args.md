## Added `link_early_args` to targets performing linking

Options passed to the linker using the `link_args` keyword argument
get placed on the command line after all objects and libraries. Some
linker options, like `-u` or `--defsym`, are only useful if placed
before objects and libraries as they control how the linker
manipulates those.

The new `link_early_args` keyword argument passes linker options which
are inserted into the command line before any objects and libraries
allowing applications to use these kinds of linker options with meson.

This is currently only supported when using the `ninja` backend.
