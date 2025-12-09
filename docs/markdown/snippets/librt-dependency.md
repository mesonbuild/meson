## New custom dependency for librt

```
dependency('rt')
```

will now check for the functionality of librt.so, but first check if it is
provided in the libc (for example in libc on OpenBSD or in musl libc on linux).
