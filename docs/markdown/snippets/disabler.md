# Added disabler object

A disabler object is a new kind of object that has very specific
semantics. If it is used as part of any other operation such as an
argument to a function call, logical operations etc, it will cause the
operation to not be evaluated. Instead the return value of said
operation will also be the disabler object.

For example if you have an setup like this:

```meson
dep = dependency('foo')
lib = shared_library('mylib', 'mylib.c',
  dependencies : dep)
exe = executable('mytest', 'mytest.c',
  link_with : lib)
test('mytest', exe)
```

If you replace the dependency with a disabler object like this:

```meson
dep = disabler()
lib = shared_library('mylib', 'mylib.c',
  dependencies : dep)
exe = executable('mytest', 'mytest.c',
  link_with : lib)
test('mytest', exe)
```

Then the shared library, executable and unit test are not
created. This is a handy mechanism to cut down on the number of `if`
statements.
