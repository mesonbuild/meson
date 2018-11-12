## New keyword argument `is_default` to `add_test_setup()`

The keyword argument `is_default` may be used to set whether the test
setup should be used by default whenever `meson test` is run without
the `--setup` option.

```meson
add_test_setup('default', is_default: true, env: 'G_SLICE=debug-blocks')
add_test_setup('valgrind', env: 'G_SLICE=always-malloc', ...)
test('mytest', exe)
```

For the example above, running `meson test` and `meson test
--setup=default` is now equivalent.
