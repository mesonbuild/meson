## ARM compiler(version 6) for C and CPP

Cross-compilation is now supported for ARM targets using ARM compiler version 6 - ARMCLANG.
The required ARMCLANG compiler options for building a shareable library are not included in the
current Meson implementation for ARMCLANG support, so it can not build shareable libraries.
This current Meson implementation for ARMCLANG support can not build assembly files with
arm syntax(we need to use armasm instead of ARMCLANG for the .s files with this syntax)
and only supports gnu syntax.
The default extension of the executable output is .axf.
The environment path should be set properly for the ARM compiler executables.
The '--target', '-mcpu' options with the appropriate values should be mentioned
in the cross file as shown in the snippet below.

```
[properties]
c_args      = ['--target=arm-arm-none-eabi', '-mcpu=cortex-m0plus']
cpp_args    = ['--target=arm-arm-none-eabi', '-mcpu=cortex-m0plus']

```

Note:
- The current changes are tested on Windows only.
- PIC support is not enabled by default for ARM,
  if users want to use it, they need to add the required arguments
  explicitly from cross-file(c_args/c++_args) or some other way.
