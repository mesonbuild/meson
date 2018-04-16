## ARM compiler for C and CPP

Cross-compilation is now supported for ARM targets using ARM compiler - ARMCC.
The current implementation does not support shareable libraries.
The default extension of the output is .axf.
The environment path should be set properly for the ARM compiler executables.
The '--cpu' option with the appropriate target type should be mentioned
in the cross file as shown in the snippet below.

```
[properties]
c_args      = ['--cpu=Cortex-M0plus']
cpp_args    = ['--cpu=Cortex-M0plus']

```
