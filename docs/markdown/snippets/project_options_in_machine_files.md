## Project and built-in options can be set in native or cross files

A new set of sections has been added to the cross and native files, `[project
options]` and `[<subproject_name>:project options]`, where `subproject_name`
is the name of a subproject. Any options that are allowed in the project can
be set from this section. They have the lowest precedent, and will be
overwritten by command line arguments.


```meson
option('foo', type : 'string', value : 'foo')
```

```ini
[project options]
foo = 'other val'
```

```console
meson build --native-file my.ini
```

Will result in the option foo having the value `other val`,

```console
meson build --native-file my.ini -Dfoo='different val'
```

Will result in the option foo having the value `different val`,


Subproject options are assigned like this:

```ini
[zlib:project options]
foo = 'some val'
```

Additionally meson level options can be set in the same way, using the
`[built-in options]` section.

```ini
[built-in options]
c_std = 'c99'
```

These options can also be set on a per-subproject basis, although only
`default_library` and `werror` can currently be set:
```ini
[zlib:built-in options]
default_library = 'static'
```
