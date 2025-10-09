## Override a program with a custom target

A program can now be generated using a [[custom_target]] and set an override
so subprojects can use it at compile time.

```meson
ct = custom_target(
  output : 'program',
  command: ['program_generator.py'],
  depends: my_pymod,
  install: true,
)
meson.override_find_program('program', ct)
```
