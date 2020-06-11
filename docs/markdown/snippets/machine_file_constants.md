## Machine file constants

Native and cross files now support string and list concatenation using the `+`
operator, and joining paths using the `/` operator.
Entries defined in the `[constants]` section can be used in any other section.
An entry defined in any other section can be used only within that same section and only
after it has been defined.

```ini
[constants]
toolchain = '/toolchain'
common_flags = ['--sysroot=' + toolchain + '/sysroot']

[properties]
c_args = common_flags + ['-DSOMETHING']
cpp_args = c_args + ['-DSOMETHING_ELSE']

[binaries]
c = toolchain + '/gcc'
```
