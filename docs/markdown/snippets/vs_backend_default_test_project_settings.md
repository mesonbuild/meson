## Set a project's default working directory and arguments with the VS backend

With the Visual Studio backend, a project's default debug working directory and arguments will be set from the first matching configured `test()` using
that executable.

For example:

```
my_exe = executable(...)

test('Test1', my_exe, args: ['a', 'b'], workdir: meson.project_source_root())
test('Test2', my_exe, args: ['c'])
```

The VS project for `my_exe` will have the `LocalDebuggerWorkingDirectory` property set to `meson.project_source_root()` and
`LocalDebuggerCommandArguments` to `"a" "b"`.
