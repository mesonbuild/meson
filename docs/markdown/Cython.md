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

py = import('python').find_installation(pure: false)

py.extension_module(
    'foo',
    'foo.pyx',
)
```

You can pass arguments accepted by the `cython` CLI script with the
`cython_args` argument:

```meson
py.extension_module(
    'foo-bounds'
    'foo.pyx',
    cython_args : ['-Xboundscheck=False'],
)
```

## C++ intermediate support

*(New in 0.60.0)*

An option has been added to control this, called `cython_language`. This can be
either `'c'` or `'cpp'`.

For those coming from setuptools/distutils, note that meson ignores
`# distutils: ` inline directives in Cython source files, hence
`# distutils: language = c++` has no effect. The `override_options` keyword
should be used instead:

```meson
project('my project', 'cython')

py.extension_module(
    'foo',
    'foo_cpp.pyx',  # will be transpiled to C++
    override_options : ['cython_language=cpp'],
)
```
