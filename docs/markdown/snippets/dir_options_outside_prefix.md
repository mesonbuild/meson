## All directory options now support paths outside of prefix

Previously, Meson only allowed most directory options to be relative to prefix.
This restriction has been now lifted, bringing us in line with Autotools and
CMake. It is also useful for platforms like Nix, which install projects into
multiple independent prefixes.

As a consequence, `get_option` might return absolute paths for any
directory option, if a directory outside of prefix is passed. This
is technically a backwards incompatible change but its effect
should be minimal, thanks to widespread use of `join_paths`/
`/` operator and pkg-config generator module.
