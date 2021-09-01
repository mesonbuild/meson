## New custom dependency for iconv

```
dependency('iconv')
```

will now check for the functionality of libiconv.so, but first check if it is
provided in the libc (for example in glibc or musl libc on Linux).
