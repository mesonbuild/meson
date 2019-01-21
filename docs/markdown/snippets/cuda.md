## Cuda support

Compiling Cuda source code is now supported, though only with the
Ninja backend. This has been tested only on Linux for now.

Because NVidia's Cuda compiler does not produce `.d` dependency files,
dependency tracking does not work.
