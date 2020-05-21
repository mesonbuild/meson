## Added ability to specify targets in `meson compile`

It's now possible to specify targets in `meson compile`, which will result in building only the requested targets.

Usage: `meson compile [TARGET [TARGET...]]`
`TARGET` has the following syntax: `[PATH/]NAME[:TYPE]`.
`NAME`: name of the target from `meson.build` (e.g. `foo` from `executable('foo', ...)`).
`PATH`: path to the target relative to the root `meson.build` file. Note: relative path for a target specified in the root `meson.build` is `./`.
`TYPE`: type of the target (e.g. `shared_library`, `executable` and etc)

`PATH` and/or `TYPE` can be ommited if the resulting `TARGET` can be used to uniquely identify the target in `meson.build`.

For example targets from the following code:
```meson
shared_library('foo', ...)
static_library('foo', ...)
executable('bar', ...)
```
can be invoked with `meson compile foo:shared_library foo:static_library bar`.
