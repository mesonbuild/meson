## Added support for LLVM's wasm-ld (WASM & WASI)

Added support for LLVM's wasm-ld (https://lld.llvm.org/WebAssembly.html), enabling the use of
the Clang + wasm-ld toolchain to build freestanding WebAssembly and hosted WASI modules.

Two cross files have been added, `cross/wasm32.txt` and `cross/wasm32-wasi.txt`, which cater to
both targets respectively. Additionally, `wasi` has been added as a stable system, whose executables
are appended the `.wasm` suffix.

Executables and static libraries are well supported. Shared libraries are supported too, but
note that, at the time of writing, there's no stable ABI yet.
(https://github.com/WebAssembly/tool-conventions/blob/main/DynamicLinking.md#llvm-implementation)

