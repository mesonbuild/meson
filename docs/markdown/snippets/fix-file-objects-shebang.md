## File objects can now be used directly as commands with shebang detection

`File` objects from `files()` and `configure_file()` can now be used directly as
the first argument in `custom_target()` and `run_target()` commands without
needing the `find_program()` workaround.

```meson
codegen = configure_file(input: 'codegen.py.in', output: 'codegen.py', copy: true)
custom_target('generated-code', command: [codegen, '@INPUT@', '@OUTPUT@'], 
              input: 'template.h.in', output: 'generated.h')
```
