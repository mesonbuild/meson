## `configure_file` accepts `'@MANDIR@'` for its `install_dir` keyword

Like `custom_target`, `configure_file` also accepts the `'@MANDIR@'` special
value to automatically calculate the install directory for generated man files.

```meson
configure_file(
    ...,
    output : 'manpage.1',
    install : true,
    install_dir : '@MANDIR@',
)
```
