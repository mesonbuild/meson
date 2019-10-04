## CUDA dependency

Native support for compiling and linking against the CUDA Toolkit using 
the `dependency` function: 

```meson
project('CUDA test', 'cpp', meson_version: '>= 0.53.0')
exe = executable('prog', 'prog.cc', dependencies: dependency('cuda'))
```

See [the CUDA dependency](Dependencies.md#cuda) for more information.
