## Override python installation paths

The `python` module now has options to control where modules are installed:
- python.platlibdir: Directory for site-specific, platform-specific files.
- python.purelibdir: Directory for site-specific, non-platform-specific files.

Those options are used by python module methods `python.install_sources()` and
`python.get_install_dir()`. By default Meson tries to detect the correct installation
path, but make them relative to the installation `prefix`, which will often result
in installed python modules to not be found by the interpreter unless `prefix`
is `/usr` on Linux, or for example `C:\Python39` on Windows. These new options
can be absolute paths outside of `prefix`.
