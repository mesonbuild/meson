## Ninja version requirement bumped to 1.7

Meson now uses the [Implicit outputs](https://ninja-build.org/manual.html#ref_outputs)
feature of Ninja for some types of targets that have multiple outputs which may
not be listed on the command-line. This feature requires Ninja 1.7+.

Note that the latest version of [Ninja available in Ubuntu 16.04](https://packages.ubuntu.com/search?keywords=ninja-build&searchon=names&suite=xenial-backports&section=all)
(the oldest Ubuntu LTS at the time of writing) is 1.7.1. If your distro does
not ship with a new-enough Ninja, you can download the latest release from
Ninja's GitHub page: https://github.com/ninja-build/ninja/releases
