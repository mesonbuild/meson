## New `python.dist_info_install_dir()` method

The `python` module gains a `dist_info_install_dir(subdir)` method on
the installation object. It returns an install directory pointing at a
subdirectory of the wheel's `.dist-info/` metadata directory, intended
for files defined by Python packaging PEPs such as PEP 770 SBOMs
(`sboms`) and PEP 639 license files (`licenses`).

```meson
py = import('python').find_installation()

install_data('sboms/component.cdx.json',
  install_dir: py.dist_info_install_dir('sboms'))
```

Python wheel build backends (e.g. `meson-python`) recognise the returned
placeholder and route the file into the wheel's
`<distname>-<version>.dist-info/<subdir>/` directory. When invoked via
`meson install` directly, the path expands to a PEP-491-compatible
location under `{purelib}`.
