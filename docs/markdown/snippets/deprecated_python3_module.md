## python3 module is deprecated

A generic module `python` has been added in Meson `0.46.0` and has a superset of
the features implemented by the previous `python3` module.

In most cases, it is a simple matter of renaming:
```meson
py3mod = import('python3')
python = py3mod.find_python()
```

becomes

```meson
pymod = import('python')
python = pymod.find_installation()
```

