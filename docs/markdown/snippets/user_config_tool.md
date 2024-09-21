## New user-specified config tool support

The `method` keyword for `dependency()` can now take an external program as
an argument:

```meson
config_tool = find_program('my-config-tool')
dep = dependency('some-dep', method: config_tool)

# or pass required arguments to it
dep = dependency('some-dep', method: [config_tool, '--package', '@NAME'])
```
