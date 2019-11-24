## Scalapack

added in **0.53.0**:

```meson
scalapack = dependency('scalapack')
```

Historically and through today, typical Scalapack setups have broken and incomplete pkg-config or
FindScalapack.cmake. Meson handles finding Scalapack on setups including:

* Linux: Intel MKL or OpenMPI + Netlib
* MacOS: Intel MKL or OpenMPI + Netlib
* Windows: Intel MKL (OpenMPI not available on Windows)