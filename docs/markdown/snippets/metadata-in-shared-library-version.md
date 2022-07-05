## Metadata support in shared library version

The shared library version now may contain build metadata specified
by adding `+` and a series of dot-separated identifiers after the
version string.

For example:
```meson
lib = shared_library('example', 'main.c', version : '1.1.0+master.g21a338e')
```
