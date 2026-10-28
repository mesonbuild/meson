---
short-description: Notes and known issues for specific platforms
...

# Platform notes

This page collects information that is specific to a platform or to a toolchain.

## macOS deployment target

Programs can be compiled for older macOS versions than the one they are compiled on.  The
version of the build machine therefore does not tell which functions are available when the
program runs.

The deployment target is chosen by the compiler.  Either set the `MACOSX_DEPLOYMENT_TARGET`
environment variable before running Meson, or pass `-mmacosx-version-min` in both the compile
and the link arguments, for example in a native file:

```ini
[built-in options]
c_args = ['-mmacosx-version-min=10.11']
c_link_args = ['-mmacosx-version-min=10.11']
```

The checks that Meson runs use the same arguments, so they see the deployment target.

When detecting a function with `compiler.has_function()`, specify the header that declares it
in the `prefix` argument.  For example, `open_memstream` was introduced in macOS 10.13.  When
building on macOS 10.13 for macOS 10.11, the following check correctly reports the function as
missing:

```meson
cc.has_function('open_memstream', prefix : '#include <stdio.h>')
```

Without the header, the check lacks the availability information and incorrectly reports the
function as available.

## AIX and IBM i

Meson supports AIX with the GCC and OpenXL compilers.  IBM i is supported in the PASE
environment, which uses the AIX user space.  On both, `host_machine.system()` returns `'aix'`.
`host_machine.kernel()` returns `'aix'` or `'os400'` to tell them apart.

The AIX linker always links the whole contents of static libraries, so `link_with` is accepted
but has the same effect as `link_whole`.

## Windows

### MinGW, UCRT and MSVC

On Windows, Meson uses the compiler that it finds first in the environment, so the shell used
to run Meson selects the toolchain.  With MSYS2, this is the environment that was started
(`MINGW64`, `UCRT64`, `CLANG64`, and so on).

- `MINGW64` links to the old `msvcrt.dll` C runtime.
- `UCRT64` and `CLANG64` link to the Universal C Runtime (UCRT), which is the runtime used by
  current versions of MSVC.
- MSVC and clang-cl link to the UCRT as well, and `b_vscrt` selects between the dynamic (`/MD`)
  and the static (`/MT`) version.

Libraries built with MinGW and with MSVC can be mixed as long as they use the same C runtime,
for example UCRT64 with MSVC.  Mixing runtimes is likely to cause crashes, because each
runtime has its own heap and file descriptor table.

The two toolchains differ in how they name and export libraries.  See
[Library file names](#library-file-names) for the names, and the
[FAQ](FAQ.md#my-project-works-fine-on-linux-and-mingw-but-fails-to-link-with-msvc-due-to-a-missing-lib-file-fatal-error-lnk1181-why)
for the exported symbols.

### Search path for DLLs

Windows has no equivalent of an rpath or of `LD_LIBRARY_PATH`.  A program finds its DLLs in its
own directory and in the directories listed in `PATH`.  When Meson runs a program from the build
tree, it adds to `PATH` the directories of the DLLs that the program needs.  This applies to:

- tests and benchmarks, including the programs and targets listed in their `depends`;
- `meson devenv`, for the executables of the project;
- custom targets and generators that run an executable from the build tree.

The directories are:

- the directories of the `shared_library()` targets that the program links to, directly or
  transitively.  The output of a `custom_target()` is not included, even if it is a DLL;
- the directories of DLLs that the program links to outside the build tree, for example when
  they are found with `find_library()`;
- when cross compiling with MinGW, the `bin` directory of the toolchain and of the `sys_root`
  and `root` of the cross file, and the program and library directories of the compilers.

#### Wine

When running Windows executables on another operating system, `PATH` is not used to find DLLs.
Meson sets `WINEPATH` with the same directories in `meson devenv`, when the host machine is
Windows and the build machine is not.  `meson test` does the same for tests whose command is
`wine`, for example through an `exe_wrapper`.  The directories of the executables are added as
well, so that `wine foo.exe` works.

Wine limits the size of `WINEPATH` to 1024 bytes.  Meson shortens the paths if necessary, using
paths relative to the working directory and Windows short names, and prints a warning if the
result is still too long.

## Emscripten

Meson can use `emcc` and `em++` from Emscripten 1.39.19 or newer to build WebAssembly.  They can
only be used for cross compilation.  A minimal cross file is:

```ini
[binaries]
c = 'emcc'
cpp = 'em++'
ar = 'emar'

[host_machine]
system = 'emscripten'
cpu_family = 'wasm32'
cpu = 'wasm32'
endian = 'little'
```

The following behavior is specific to Emscripten:

- Executables have the `.js` suffix.  If a `.wasm` file is produced next to it, `meson install`
  installs it as well.
- The linker is detected as `ld.wasm`, the name that Meson uses for `wasm-ld`.
- The `c_thread_count` and `cpp_thread_count` options set `-sPTHREAD_POOL_SIZE` when a target
  uses threads.  The default is 4, and 0 does not pass the option.
- `compiler.find_library()` can look up JavaScript libraries.  The name must end with `.js`, and
  either be an absolute path or be searched in the directories passed with `dirs`.

```meson
glue_lib = cc.find_library('gluefuncs.js', dirs: meson.current_source_dir())
executable('prog', 'prog.c', dependencies: glue_lib)
```

Running the output requires `exe_wrapper`, for example `node`.  See
[running target programs](Cross-compilation.md#running-target-programs).

## QNX

Meson can detect and use `qcc` and `q++`, the C and C++ compiler drivers shipped with the QNX
Software Development Platform (SDP).  For cross compilation, point the `[binaries]` section of
the cross file at `qcc` and `q++`, including the required `-V` target selector, and set
`system = 'qnx'` in `[host_machine]`:

```ini
[binaries]
c = ['qcc', '-Vgcc_ntoaarch64le']
cpp = ['q++', '-Vgcc_ntoaarch64le']

[host_machine]
system = 'qnx'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
```

The following limitations apply:

1. ThinLTO incremental cache does not work.  `-Db_thinlto_cache=true` raises an error at
   configure time, while `-Db_lto=true` is unaffected.
2. Alternate linker selection is not supported.  Setting `c_ld` or `cpp_ld` (for example to
   `lld` or `gold`) raises an error.
3. If a header is deleted, stale entries remain in the dependency files, because `-MP` does not
   emit phony header rules.  A clean build is needed to recover.
4. There is no static sanitizer runtime, so `-static-libasan` is rejected and only the shared
   runtime can be linked.
5. The available sanitizers depend on the SDP version.  SDP 7.1 only provides `libubsan`, so
   `-Db_sanitize=address` and `-Db_sanitize=leak` fail to link there.  SDP 8.0 adds asan and
   lsan.  `-Db_sanitize=undefined` works on both, and tsan is not available on either.
6. C++20 named modules do not work.  With SDP 8.0, `-fmodules-ts` compiles but silently ignores
   `.cppm` and `.ixx` files.  With SDP 7.1, `-fmodules-ts` is rejected for C++ sources.  Plain
   `-fmodules` is rejected on both.  This only affects projects that enable modules through
   `cpp_args`.
7. Relinking is avoided for unchanged shared libraries only on native QNX builds.  When
   cross compiling to QNX, shared libraries are always relinked.
