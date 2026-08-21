## Cuda dependency with cudart_none

The Cuda dependency can now be initialize as `dependency('cuda', modules : ['cudart_none'])`,
which will result in no runtime. This is equivalent to `--cudart none` on the command line.
