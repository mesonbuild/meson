## Generators have a new `depends` keyword argument

Generators can now specify extra dependencies with the `depends`
keyword argument. It matches the behaviour of the same argument in
other functions and specifies that the given targets must be built
before the generator can be run. This is used in cases such as this
one where you need to tell a generator to indirectly invoke a
different program.

```meson
exe = executable(...)
cg = generator(program_runner,
    output: ['@BASENAME@.c'],
    arguments: ['--use-tool=' + exe.full_path(), '@INPUT@', '@OUTPUT@'],
    depends: exe)
```
