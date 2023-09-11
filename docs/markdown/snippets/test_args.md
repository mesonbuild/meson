## `test()`, `benchmark()` and `rust.test()` "args" kwarg replaced by positional arguments

For consistency with other functions, `test()`, `benchmark()` and `rust.test()`
now takes command argument together with the executable as positional arguments.
`test('something', exe, args: ['--foo'])` now becomes simply
`test('something', exe, '--foo')`.

In addition, more types are accepted both as executable and as arguments, to be
consistent with what `custom_target()`'s command keyword argument supports:
strings, build target, custom targets, index of custom targets, external programs
and files.
