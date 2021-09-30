## Force Visual Studio environment activation

Since `0.59.0`, meson automatically activates Visual Studio environment on Windows
for all its subcommands, but only if no other compilers (e.g. `gcc` or `clang`)
are found, and silently continue if Visual Studio activation fails.

`meson setup --vsenv` command line argument can now be used to force Visual Studio
activation even when other compilers are found. It also make Meson abort with an
error message when activation fails. This is especially useful for Github Action
because their Windows images have gcc in their PATH by default.

`--vsenv` is set by default when using `vs` backend.

Only `setup`, `compile`, `dist` and `devenv` subcommands now activate Visual Studio.
