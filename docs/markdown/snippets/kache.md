## Added support for kache

Meson now recognizes [kache](https://github.com/kunobi-ninja/kache) as
a compiler wrapper, so setting e.g. `CC="kache cc"` works like it
already does for Ccache and sccache. Unlike those, kache is not
auto-detected, because it must be invoked with a compiler subcommand
(`kache cc`, `kache c++`, ...) rather than in front of an arbitrary
compiler.
