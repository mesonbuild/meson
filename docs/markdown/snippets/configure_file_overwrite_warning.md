## Meson warns if two calls to configure_file() write to the same file

If two calls to [`configure_file()`](#Reference-manual.md#configure_file)
write to the same file Meson will print a `WARNING:` message during
configuration. For example:
```meson
project('configure_file', 'cpp')

configure_file(
      input: 'a.in',
      output: 'out',
      command: ['./foo.sh']
    )
configure_file(
  input: 'a.in',
  output: 'out',
  command: ['./foo.sh']
)

```

This will output:

```
The Meson build system
Version: 0.47.0.dev1
Source dir: /path/to/srctree
Build dir: /path/to/buildtree
Build type: native build
Project name: configure_file
Project version: undefined
Build machine cpu family: x86_64
Build machine cpu: x86_64
Configuring out with command
WARNING: Output file out for configure_file overwritten. First time written in line 3 now in line 8
Configuring out with command
Build targets in project: 0
Found ninja-1.8.2 at /usr/bin/ninja
```
