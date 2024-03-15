## New custom dependency for atomic

```
dependency('atomic')
```

checks for the availability of the atomic operation library. First, it checks
if stdatomic is provided by compiler-rt (e.g. when using clang). If not, it
looks for the atomic library specifically.
