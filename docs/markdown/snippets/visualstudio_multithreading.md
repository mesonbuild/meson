## Visual Studio Multiprocessor Compilation support

The `backend_multithreaded` option can now be set for Visual Studio backends
to set the `/MP` flag, speeding up compilation for targets with a lot of
source files. Defaults to true.