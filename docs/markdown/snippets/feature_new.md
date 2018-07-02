## Feature detection based on meson_version in project()

Meson will now print a `WARNING:` message during configuration if you use
a function or a keyword argument that was added in a meson version that's newer
than the version specified inside `project()`. For example:

```meson
project('featurenew', meson_version: '>=0.43')

cdata = configuration_data()
cdata.set('FOO', 'bar')
message(cdata.get_unquoted('FOO'))
```

This will output:

```
The Meson build system
Version: 0.47.0.dev1
Source dir: C:\path\to\srctree
Build dir: C:\path\to\buildtree
Build type: native build
Project name: featurenew
Project version: undefined
Build machine cpu family: x86_64
Build machine cpu: x86_64
WARNING: Project targetting '>=0.43' but tried to use feature introduced in '0.44.0': configuration_data.get_unquoted()
Message: bar
Build targets in project: 0
WARNING: Project specifies a minimum meson_version '>=0.43' which conflicts with:
 * 0.44.0: {'configuration_data.get_unquoted()'}
```
