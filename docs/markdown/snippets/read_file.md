## Support for reading files at configuration time with `meson.read_file`

Reading text files during configuration is now supported. This can be done at
any time and enables several useful idioms previously awkward:

```meson
project(
  'myproject',
  'c',
  version: run_command(
    find_program(
      'python3', '-c', 'print(open("VERSION").read())'
    ).stdout.strip()
  )
)
```

There are several problems with the above approach:
1. It's ugly and confusing
2. If `VERSION` changes after configuration, meson won't correctly rebuild when
   configuration data is based on the data project version
3. It has extra overhead

`meson.read_file` replaces the above idiom thus:
```meson
project(
  'myproject',
  'c',
  version: meson.read_file('VERSION').strip()
)
```
They are not equivalent, though. Files read with `meson.read_file` create a
configuration dependency on the file, and so if the `VERSION` file is modified,
meson will automatically reconfigure, guaranteeing the build is consistent. It
can be used for any properly encoded text files. It supports specification of
non utf-8 encodings too, so if you're stuck with text files in a different
encoding, it can be passed as an argument. See the [meson
object](Reference-manual.md#meson-object) documentation for details.
