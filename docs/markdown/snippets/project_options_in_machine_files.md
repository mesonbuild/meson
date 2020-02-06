## Project options can be set in native or cross files

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
