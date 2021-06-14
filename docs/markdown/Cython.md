---
title: Cython
short-description: Support for Cython in Meson
...

# Cython

Meson provides native support for cython programs starting with version 0.59.0.
This means that you can include it as a normal language, and create targets like
any other supported language:

```meson
lib = static_library(
    'foo',
    'foo.pyx',
)
```

Generally Cython is most useful when combined with the python module's
extension_module method:

```meson
project('my project', 'cython')

py = import('python').find_installation()
dep_py = py.dependency()

py.extension_module(
    'foo',
    'foo.pyx',
    dependencies : dep_py,
)
```
