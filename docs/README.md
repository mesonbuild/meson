# Meson Documentation

## Build dependencies

Meson uses itself and [Sphinx](https://www.sphinx-doc.org/) for generating documentation.

Our custom Sphinx extensions require:
- [strictyaml](https://pypi.org/project/strictyaml)

## Building the documentation

From the Meson repository root dir:
```
$ cd docs/
$ meson setup built_docs/
$ ninja -C built_docs/
```
Now you should be able to open the documentation locally
```
built_docs/Meson documentation-doc/html/index.html
```
