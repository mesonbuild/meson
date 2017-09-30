# wrap-svn

The [Wrap dependency system](Wrap-dependency-system-manual.md) now supports [Subversion](https://subversion.apache.org/) (svn).
This support is rudimentary. The repository url has to point to a specific (sub)directory containing the `meson.build` file (typically `trunk/`). However, providing a `revision` is supported.
