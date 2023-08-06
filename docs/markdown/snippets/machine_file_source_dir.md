## `@GLOBAL_SOURCE_ROOT@` and `@DIRNAME@` in machine files

Some tokens are now replaced in the machine file before parsing it:
- `@GLOBAL_SOURCE_ROOT@`: the absolute path to the project's source tree
- `@DIRNAME@`: the absolute path to the machine file's parent directory.

It can be used, for example, to have paths relative to the source directory, or
relative to toolchain's installation directory.
```ini
[binaries]
c = '@DIRNAME@/toolchain/gcc'
exe_wrapper = '@GLOBAL_SOURCE_ROOT@' / 'build-aux' / 'my-exe-wrapper.sh'
```
