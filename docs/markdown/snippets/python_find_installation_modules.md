## New modules kwarg for python.find_installation

This mirrors the modules argument that some kinds of dependencies (such as
qt, llvm, and cmake based dependencies) take, allowing you to check that a
particular module is available when getting a python version.

```meson
py = import('python').find_installation('python3', modules : ['numpy'])
```