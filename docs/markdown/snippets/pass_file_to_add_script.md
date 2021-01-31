## The `add_*_script` methods now accept a File as the first argument

Meson now accepts `file` objects, including those produced by
`configure_file`, as the first parameter of the various
`add_*_script` methods

```meson
install_script = configure_file(
  configuration : conf,
  input : 'myscript.py.in',
  output : 'myscript.py',
)

meson.add_install_script(install_script, other, params)
```
