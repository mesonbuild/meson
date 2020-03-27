## meson dist --no-tests

`meson dist` has a new option `--no-tests` to skip build and tests of generated
packages. It can be used to not waste time for example when done in CI that
already does its own testing.
