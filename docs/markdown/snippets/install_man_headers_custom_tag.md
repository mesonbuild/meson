## install_man and install_headers: add support for install_tag kwarg

`install_man` and `install_headers` now support the `install_tag` keyword argument,
allowing selection of installed files via `meson install --tags`. Previously,
`install_man` always used the `man` tag and `install_headers` always used the
`devel` tag, with no way to override them.
