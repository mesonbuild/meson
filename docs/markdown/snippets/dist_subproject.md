## Packaging a subproject

The `meson dist` command can now create a distribution tarball for a subproject
in the same git repository as the main project. This can be useful if parts of
the project (e.g. libraries) can be built and distributed separately. In that
case they can be moved into `subprojects/mysub` and running `meson dist` in that
directory will now create a tarball containing only the source code from that
subdir and not the rest of the main project or other subprojects.

For example:
```sh
git clone https://github.com/myproject
cd myproject/subprojects/mysubproject
meson builddir
meson dist -C builddir
```
