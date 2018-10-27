## Uninstalled pkg-config files

The `pkgconfig` module now generates uninstalled pc files as well. For any generated
`foo.pc` file, an extra `foo-uninstalled.pc` file is placed into
`<builddir>/meson-uninstalled`. They can be used to build applications against
libraries built by meson without installing them, by pointing `PKG_CONFIG_PATH`
to that directory. This is an experimental feature provided on a best-effort
basis, it might not work in all use-cases.
