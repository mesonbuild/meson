## Allow using Python bindings to libpkgconf

If `pypkgconf` module can be imported, it is used as pkg-config implementation,
unless the machine files are pointing to a different pkg-config version.

Using libpkgconf as a Python module removes the overhead of calling pkg-config
as a subprocess, and greatly improve performances, especially on Windows
platform.
