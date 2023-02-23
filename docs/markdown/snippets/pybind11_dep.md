## New pybind11 custom dependency

`dependency('pybind11')` works with pkg-config and cmake without any special
support, but did not handle the `pybind11-config` script.

This is useful because the config-tool will work out of the box when pybind11
is installed, but the pkg-config and cmake files are shoved into python's
site-packages, which makes it impossible to use in an out of the box manner.

