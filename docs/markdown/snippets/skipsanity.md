## Skip sanity tests when cross compiling

For certain cross compilation environments it is not possible to
compile a sanity check application. This can now be disabled by adding
the following entry to your cross file's `properties` section:

```
skip_sanity_check = true
```
