## Added preserve_path arg to install_data

The [[install_data]] function now has an optional argument `preserve_path`
that allows installing multi-directory data file structures that live
alongside source code with a single command.

This is also available in the specialized `py_installation.install_sources`
method.
