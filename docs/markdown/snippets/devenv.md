## Developer environment

New method `meson.add_devenv()` adds an [`environment()`](#environment) object
to the list of environments that will be applied when using `meson devenv`
command line. This is useful for developpers who wish to use the project without
installing it, it is often needed to set for example the path to plugins
directory, etc. Alternatively, a list or dictionary can be passed as first
argument.

``` meson
devenv = environment()
devenv.set('PLUGINS_PATH', meson.current_build_dir())
...
meson.add_devenv(devenv)
```

New command line has been added: `meson devenv -C builddir [<command>]`.
It runs a command, or open interactive shell if no command is provided, with
environment setup to run project from the build directory, without installation.

These variables are set in environment in addition to those set using `meson.add_devenv()`:
- `MESON_DEVENV` is defined to `'1'`.
- `MESON_PROJECT_NAME` is defined to the main project's name.
- `PKG_CONFIG_PATH` includes the directory where Meson generates `-uninstalled.pc`
  files.
- `PATH` includes every directory where there is an executable that would be
  installed into `bindir`. On windows it also includes every directory where there
  is a DLL needed to run those executables.
- `LD_LIBRARY_PATH` includes every directory where there is a shared library that
  would be installed into `libdir`. This allows to run system application using
  custom build of some libraries. For example running system GEdit when building
  GTK from git. On OSX the environment variable is `DYLD_LIBRARY_PATH` and
  `PATH` on Windows.
- `GI_TYPELIB_PATH` includes every directory where a GObject Introspection
  typelib is built. This is automatically set when using `gnome.generate_gir()`.
