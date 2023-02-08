## Unit test executables now only built when needed

Requires `ninja` as a backend
Unit tests and benchmark tests are now separate from the `all` build
target. To build them explicitly, use the targets `meson-test-prereq`
and `meson-benchmark-prereq` respectively.
