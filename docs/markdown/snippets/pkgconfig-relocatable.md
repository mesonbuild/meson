## Installed pkgconfig files can now be relocatable

The pkgconfig module now has a module option `pkgconfig.relocatable`.
When set to `true`, the pkgconfig files generated will have their
`prefix` variable set to be relative to their `install_dir`.

For example to enable it from the command line run:

```sh
meson setup builddir -Dpkgconfig.relocatable=true …
```

It will only work if the `install_dir` for the generated pkgconfig
files are located inside the install prefix of the package. Not doing
so will cause an error.

This should be useful on Windows or any other platform where
relocatable packages are desired.
