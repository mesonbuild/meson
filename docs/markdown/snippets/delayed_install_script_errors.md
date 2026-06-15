## Delay install script errors to install time

Previously, `gnome.post_install` might've caused a configure to fail
due to tools such as `update-desktop-database` not being installed or
due to an `exe_wrapper` missing when cross-building glib. Those
errors will now be delayed to install time, or not emitted at all
if installing with `DESTDIR` set, since then they'll be skipped.
