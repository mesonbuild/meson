## `gnome.post_install()`

Post-install update of various system wide caches. Each script will be executed
only once even if `gnome.post_install()` is called multiple times from multiple
subprojects. If `DESTDIR` is specified during installation all scripts will be
skipped.

Currently supports `glib-compile-schemas`, `gio-querymodules`, and
`gtk-update-icon-cache`.
