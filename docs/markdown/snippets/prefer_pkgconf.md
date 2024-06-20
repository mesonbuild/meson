## Pkgconf is now the preferred pkg-config implementation

Previous versions of meson would not look for `pkgconf` unless it had a
`pkg-config` alias. Meson will now search for `pkgconf` first, as it is a
superior implementation, and then for `pkg-config` second, if `pkgconf` is
not found. For most OSes this will not result in any changes, as either
`pkgconf` is not installed, or `pkg-config` is an alias for `pkgconf`.
