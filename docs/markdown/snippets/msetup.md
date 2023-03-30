## Update options with `meson setup <builddir> -Dopt=value`

If the build directory already exists, options are updated with their new value
given on the command line (`-Dopt=value`). Unless `--reconfigure` is also specified,
this won't reconfigure immediately. This has the same behaviour as
`meson configure <builddir> -Dopt=value`.

Previous Meson versions were simply a no-op.

## Clear persistent cache with `meson setup --clearcache`

Just like `meson configure --clearcache`, it is now possible to clear the cache
and reconfigure in a single command with `meson setup --clearcache --reconfigure <builddir>`.
