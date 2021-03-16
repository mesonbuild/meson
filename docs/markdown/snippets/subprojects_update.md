## `meson subprojects update --reset` now re-extract tarballs

When using `--reset` option, the source tree of `[wrap-file]` subprojects is now
deleted and re-extracted from cached tarballs, or re-downloaded. This is because
Meson has no way to know if the source tree or the wrap file has been modified,
and `--reset` should guarantee that latest code is being used on next reconfigure.

Use `--reset` with caution if you do local changes on non-git subprojects.
