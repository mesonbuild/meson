## Add support for thin LTO

The `b_lto` option has been updated and now can be set to the value
`thin`. This enables [thin
LTO](https://clang.llvm.org/docs/ThinLTO.html) on all compilers where
it is supported. At the time of writing this means only Clang.

This change is potentially backwards incompatible. If you have
examined the value of `b_lto` in your build file, note that its type
has changed from a boolean to a string. Thus comparisons like this:

```meson
if get_option('b_lto')
...
endif
```

need to be changed to something like this instead:

```meson
if get_option('b_lto') == 'true'
...
endif
```

This should not affect any comman line invocations as configuring LTO
with `-Db_lto=true` still works and behaves the same way as before.
