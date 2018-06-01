## New keyword argument `output_format` for configure_file()

When called without an input file, `configure_file` generates a
C header file by default. A keyword argument was added to allow
specifying the output format, for example for use with nasm or yasm:

```
conf = configuration_data()
conf.set('FOO', 1)

configure_file('config.asm',
  configuration: conf,
  output_format: 'nasm')
```
