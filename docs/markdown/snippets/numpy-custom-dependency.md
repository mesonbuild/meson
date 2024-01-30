## New numpy custom dependency

Support for `dependency('numpy')` was added, via supporting the `numpy-config` tool and
pkg-config support, both of which are available since NumPy 2.0.0.

Config-tool support is useful because it will work out of the box when
``numpy`` is installed, while the pkg-config file is located inside python's
site-packages, which makes it impossible to use in an out of the box manner
without setting `PKG_CONFIG_PATH`.
