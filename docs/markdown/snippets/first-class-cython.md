## Cython as as first class language

Meson now supports Cython as a first class language. This means you can write:

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

And avoid the step through a generator that was previously required.
