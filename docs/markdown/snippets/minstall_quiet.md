## New option `--quiet` to `meson install`

Now you can run `meson install --quiet` and meson will not verbosely print
every file as it is being installed. As before, the full log is always
available inside the builddir in `meson-logs/install-log.txt`.

When this option is passed, install scripts will have the environment variable
`MESON_INSTALL_QUIET` set.

Numerous speed-ups were also made for the install step, especially on Windows
where it is now 300% to 1200% faster than before depending on your workload.
