## Emscripten (emcc) now supports threads

In addition to properly setting the compile and linker arguments, a new meson
builtin has been added to control the PTHREAD_POOL_SIZE option,
`-D<lang>_thread_count`, which may be set to any integer value greater than 0.
If it set to 0 then the PTHREAD_POOL_SIZE option will not be passed.
