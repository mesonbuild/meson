## Property support emscripten's wasm-ld

Before 0.54.0 we treated emscripten as both compiler and linker, which isn't
really true. It does have a linker, called wasm-ld (meson's name is ld.wasm).
This is a special version of clang's lld. This will now be detected properly.
