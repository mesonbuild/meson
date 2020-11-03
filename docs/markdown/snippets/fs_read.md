## Support for reading files at configuration time with the `fs` module

Reading text files during configuration is now supported. This can be done at
any time after `project` has been called

```meson
project(myproject', 'c')
license_text = run_command(
    find_program('python3'), '-c', 'print(open("COPYING").read())'
).stdout().strip()
about_header = configuration_data()
about_header.add('COPYRIGHT', license_text)
about_header.add('ABOUT_STRING', meson.project_name())
...
```

There are several problems with the above approach:
1. It's ugly and confusing
2. If `COPYING` changes after configuration, Meson won't correctly rebuild when
   configuration data is based on the data in COPYING
3. It has extra overhead

`fs.read` replaces the above idiom thus:
```meson
project(myproject', 'c')
fs = import('fs')
license_text = fs.read('COPYING').strip()
about_header = configuration_data()
about_header.add('COPYRIGHT', license_text)
about_header.add('ABOUT_STRING', meson.project_name())
...
```

They are not equivalent, though. Files read with `fs.read` create a
configuration dependency on the file, and so if the `COPYING` file is modified,
Meson will automatically reconfigure, guaranteeing the build is consistent. It
can be used for any properly encoded text files. It supports specification of
non utf-8 encodings too, so if you're stuck with text files in a different
encoding, it can be passed as an argument. See the [`meson`
object](Reference-manual.md#meson-object) documentation for details.
