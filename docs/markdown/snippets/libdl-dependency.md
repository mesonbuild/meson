## New custom dependency for libdl

```
dependency('dl')
```

will now check for the functionality of libdl.so, but first check if it is
provided in the libc (for example in libc on OpenBSD or in musl libc on linux).
