## Allow custom install scripts to run with `--dry-run` option

An new `dry_run` keyword is added to `meson.add_install_script()`
to allow a custom install script to run when meson is invoked
with `meson install --dry-run`. 

In dry run mode, the `MESON_INSTALL_DRY_RUN` environment variable
is set.
